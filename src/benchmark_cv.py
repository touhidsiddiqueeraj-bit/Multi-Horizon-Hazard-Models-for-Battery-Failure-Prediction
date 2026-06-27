import os
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

from composite_label import make_composite_fail_in_H
from stats_utils import delong_roc_test

_HERE = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.join(_HERE, "..", "data")

FEATURES = ["cycle", "avg_voltage", "min_voltage", "avg_current", "avg_temp", "duration", "SOH"]
FEATURES_CROSS_CHEM = ["cycle", "avg_voltage", "min_voltage", "avg_current", "avg_temp", "duration"]
REQUIRED_COLS = ["cycle", "SOH", "cell", "RUL"]
H_LIST = [10, 20, 30, 50]
N_SPLITS = 5

DATASETS = {
    "nasa": os.path.join(_DATA_DIR, "nasa_clean_filtered.csv"),
    "calce": os.path.join(_DATA_DIR, "calce_clean.csv"),
}


def get_models():
    return {
        "xgboost": XGBClassifier(
            max_depth=4, learning_rate=0.05,
            n_estimators=300, subsample=0.8,
            colsample_bytree=0.8, min_child_weight=5,
            objective="binary:logistic",
            eval_metric="logloss",
            random_state=42, verbosity=0
        ),
        "lightgbm": LGBMClassifier(
            max_depth=4, learning_rate=0.05,
            n_estimators=300, subsample=0.8,
            colsample_bytree=0.8, min_child_samples=20,
            random_state=42, verbosity=-1
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=300, max_depth=6,
            random_state=42, n_jobs=-1
        ),
    }


def safe_auc(y_true, p):
    return roc_auc_score(y_true, p) if len(np.unique(y_true)) > 1 else np.nan


def clean_df(df):
    cols_available = [c for c in FEATURES if c in df.columns]
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=REQUIRED_COLS).copy()
    df = df[(df["SOH"] > 0) & (df["SOH"] < 1.2)].copy()
    df = df[df["RUL"] >= 0].copy()
    df = df.sort_values(["cell", "cycle"]).copy()
    df[cols_available] = df[cols_available].fillna(0)
    return df


def run_cv(df, model, H, return_preds=False):
    y = make_composite_fail_in_H(df, H)
    cols_available = [c for c in FEATURES if c in df.columns]
    X = df[cols_available].values
    groups = df["cell"].values
    n_splits = min(N_SPLITS, df["cell"].nunique())
    gkf = GroupKFold(n_splits=n_splits)

    auc_raw, auc_iso, auc_platt = [], [], []
    brier_iso, brier_platt = [], []
    y_te_list, p_raw_list = [], []

    for tr, te in gkf.split(X, y, groups):
        X_tr, X_te = X[tr], X[te]
        y_tr, y_te = y[tr], y[te]

        m = clone(model)
        m.fit(X_tr, y_tr)

        p_raw = m.predict_proba(X_te)[:, 1]
        p_tr = m.predict_proba(X_tr)[:, 1]
        a_raw = safe_auc(y_te, p_raw)

        # Isotonic calibration
        if len(np.unique(y_tr)) < 2:
            p_cal_iso = p_raw.copy()
        else:
            iso = IsotonicRegression(out_of_bounds="clip")
            iso.fit(p_tr, y_tr)
            p_cal_iso = iso.transform(p_raw)

        a_iso = safe_auc(y_te, p_cal_iso)
        b_iso = brier_score_loss(y_te, p_cal_iso)

        # Platt (sigmoid) calibration — logistic regression on m's scores (same base model as isotonic)
        if len(np.unique(y_tr)) < 2:
            p_cal_platt = p_raw.copy()
        else:
            platt_lr = LogisticRegression(C=1e10, solver="lbfgs", random_state=42)
            platt_lr.fit(p_tr.reshape(-1, 1), y_tr)
            p_cal_platt = platt_lr.predict_proba(p_raw.reshape(-1, 1))[:, 1]

        a_platt = safe_auc(y_te, p_cal_platt)
        b_platt = brier_score_loss(y_te, p_cal_platt)

        if not np.isnan(a_raw):
            auc_raw.append(a_raw)
        if not np.isnan(a_iso):
            auc_iso.append(a_iso)
        if not np.isnan(a_platt):
            auc_platt.append(a_platt)
        if not np.isnan(b_iso):
            brier_iso.append(b_iso)
        if not np.isnan(b_platt):
            brier_platt.append(b_platt)
        y_te_list.append(y_te)
        p_raw_list.append(p_raw)

    result = {
        "AUC_raw": np.mean(auc_raw) if auc_raw else np.nan,
        "AUC_cal_iso": np.mean(auc_iso) if auc_iso else np.nan,
        "AUC_cal_platt": np.mean(auc_platt) if auc_platt else np.nan,
        "Brier_cal_iso": np.mean(brier_iso),
        "Brier_cal_platt": np.mean(brier_platt),
    }
    if return_preds and auc_raw:
        result["y_true"] = np.concatenate(y_te_list)
        result["p_pred"] = np.concatenate(p_raw_list)
    return result


def run_cross_chem(train_df, test_df, model, H, features=None, return_preds=False):
    """Train on one set, test on another (no folds)."""
    if features is None:
        features = FEATURES_CROSS_CHEM
    y_train = make_composite_fail_in_H(train_df, H)
    y_test = make_composite_fail_in_H(test_df, H)
    cols_available = [c for c in features if c in train_df.columns]
    X_train = train_df[cols_available].values
    X_test = test_df[cols_available].values

    if len(np.unique(y_test)) < 2:
        return {"AUC_raw": np.nan, "AUC_cal_iso": np.nan, "AUC_cal_platt": np.nan,
                "Brier_cal_iso": np.nan, "Brier_cal_platt": np.nan}

    m = clone(model)
    m.fit(X_train, y_train)

    p_raw = m.predict_proba(X_test)[:, 1]
    p_tr = m.predict_proba(X_train)[:, 1]
    a_raw = safe_auc(y_test, p_raw)

    # Isotonic
    if len(np.unique(y_train)) < 2:
        p_cal_iso = p_raw.copy()
    else:
        iso = IsotonicRegression(out_of_bounds="clip")
        iso.fit(p_tr, y_train)
        p_cal_iso = iso.transform(p_raw)

    a_iso = safe_auc(y_test, p_cal_iso)
    b_iso = brier_score_loss(y_test, p_cal_iso)

    # Platt — logistic regression on m's scores (same base model as isotonic)
    if len(np.unique(y_train)) < 2:
        p_cal_platt = p_raw.copy()
    else:
        platt_lr = LogisticRegression(C=1e10, solver="lbfgs", random_state=42)
        platt_lr.fit(p_tr.reshape(-1, 1), y_train)
        p_cal_platt = platt_lr.predict_proba(p_raw.reshape(-1, 1))[:, 1]

    a_platt = safe_auc(y_test, p_cal_platt)
    b_platt = brier_score_loss(y_test, p_cal_platt)

    result = {
        "AUC_raw": a_raw,
        "AUC_cal_iso": a_iso,
        "AUC_cal_platt": a_platt,
        "Brier_cal_iso": b_iso,
        "Brier_cal_platt": b_platt,
    }
    if return_preds:
        result["y_true"] = y_test
        result["p_pred"] = p_raw
    return result


def run_cross_chem_per_cell(train_df, test_df, model, H, features=None):
    """Cross-chem transfer with per-cell evaluation on test cells.

    Trains once on LCO-only data, scores each test cell independently.
    Returns mean +/- std across cells for all metrics, preserving the
    same key names as run_cross_chem for backward compatibility.
    """
    cells = test_df["cell"].unique()
    per_cell = {k: [] for k in
                ["AUC_raw", "AUC_cal_iso", "AUC_cal_platt", "Brier_cal_iso", "Brier_cal_platt"]}
    cell_tags = []

    for cell in cells:
        test_cell = test_df[test_df["cell"] == cell]
        res = run_cross_chem(train_df, test_cell, model, H, features=features)
        cell_tags.append(cell)
        for k in per_cell:
            per_cell[k].append(res[k])

    result = {}
    for k in per_cell:
        arr = np.array(per_cell[k], dtype=float)
        valid = arr[np.isfinite(arr)]
        result[k] = np.mean(valid) if len(valid) > 0 else np.nan
        result[f"{k}_std"] = np.std(valid) if len(valid) > 0 else np.nan

    result["cell_aucs_raw"] = str(
        [f"{c}:{r:.4f}" for c, r in zip(cell_tags, per_cell["AUC_raw"])])
    result["cell_aucs_platt"] = str(
        [f"{c}:{r:.4f}" for c, r in zip(cell_tags, per_cell["AUC_cal_platt"])])
    return result


def main():
    os.makedirs(_DATA_DIR, exist_ok=True)
    all_rows = []

    # --- Within-dataset CV ---
    for ds_name, ds_path in DATASETS.items():
        if not os.path.exists(ds_path):
            print(f"SKIPPING {ds_name} — file not found: {ds_path}")
            continue

        df = clean_df(pd.read_csv(ds_path))
        n_cells = df["cell"].nunique()
        if n_cells < 2:
            print(f"SKIPPING {ds_name} — only {n_cells} cells (need >= 2)")
            continue

        print(f"\n=== Dataset: {ds_name} | {n_cells} cells, {len(df)} rows ===")

        for model_name, model in get_models().items():
            for H in H_LIST:
                y = make_composite_fail_in_H(df, H)
                if len(np.unique(y)) < 2:
                    print(f"  {model_name} H={H} ... SKIP (no failures)")
                    continue

                print(f"  {model_name} H={H} ...", end=" ", flush=True)
                res = run_cv(df, model, H)
                print(f"iso={res['AUC_cal_iso']:.3f}/{res['Brier_cal_iso']:.3f} "
                      f"platt={res['AUC_cal_platt']:.3f}/{res['Brier_cal_platt']:.3f}")

                for method in ["iso", "platt"]:
                    all_rows.append({
                        "dataset": ds_name,
                        "model": model_name,
                        "H": H,
                        "method": method,
                        "eval": "within",
                        "AUC_raw": res["AUC_raw"],
                        "AUC_cal": res[f"AUC_cal_{method}"],
                        "Brier_cal": res[f"Brier_cal_{method}"],
                    })

    # --- Cross-chemistry transfer: LCO → LFP ---
    nasa_path = DATASETS["nasa"]
    calce_path = DATASETS["calce"]
    oxford_path = os.path.join(_DATA_DIR, "oxford_clean.csv")
    severson_path = os.path.join(_DATA_DIR, "severson_clean.csv")

    if os.path.exists(oxford_path):
        test_df = clean_df(pd.read_csv(oxford_path))
        transfer_sets = {
            "nasa": clean_df(pd.read_csv(nasa_path)),
            "calce": clean_df(pd.read_csv(calce_path)),
        }
        combined = pd.concat(
            [clean_df(pd.read_csv(nasa_path)), clean_df(pd.read_csv(calce_path))],
            ignore_index=True
        )
        transfer_sets["nasa+calce"] = combined

        for features, feat_label in [(FEATURES, "with_soh"), (FEATURES_CROSS_CHEM, "no_soh")]:
            print(f"\n=== Cross-chemistry transfer [{feat_label}]: LCO → LFP ===")
            for train_name, train_df in transfer_sets.items():
                n_cells = train_df["cell"].nunique()
                print(f"  Train: {train_name} ({n_cells} cells) → Test: Oxford (per-cell eval)")

                for model_name, model in get_models().items():
                    for H in H_LIST:
                        y_test = make_composite_fail_in_H(test_df, H)
                        if len(np.unique(y_test)) < 2:
                            print(f"    {model_name} H={H} ... SKIP (no failures on test)")
                            continue

                        print(f"    {model_name} H={H} ...", end=" ", flush=True)
                        res = run_cross_chem_per_cell(train_df, test_df, model, H, features=features)
                        print(f"iso={res['AUC_cal_iso']:.3f}±{res['AUC_cal_iso_std']:.3f} "
                              f"platt={res['AUC_cal_platt']:.3f}±{res['AUC_cal_platt_std']:.3f}")

                        for method in ["iso", "platt"]:
                            all_rows.append({
                                "dataset": "oxford",
                                "model": model_name,
                                "H": H,
                                "method": method,
                                "eval": f"train_{train_name}_{feat_label}",
                                "AUC_raw": res["AUC_raw"],
                                "AUC_cal": res[f"AUC_cal_{method}"],
                                "AUC_cal_std": res[f"AUC_cal_{method}_std"],
                                "Brier_cal": res[f"Brier_cal_{method}"],
                                "Brier_cal_std": res[f"Brier_cal_{method}_std"],
                            })
    else:
        print(f"SKIPPING cross-chemistry — Oxford file not found: {oxford_path}")

    # --- Cross-chemistry transfer: LCO → Severson (LFP) ---
    if os.path.exists(severson_path):
        test_df = clean_df(pd.read_csv(severson_path))
        transfer_sets = {
            "nasa": clean_df(pd.read_csv(nasa_path)),
            "calce": clean_df(pd.read_csv(calce_path)),
        }
        combined = pd.concat(
            [clean_df(pd.read_csv(nasa_path)), clean_df(pd.read_csv(calce_path))],
            ignore_index=True
        )
        transfer_sets["nasa+calce"] = combined

        for features, feat_label in [(FEATURES, "with_soh"), (FEATURES_CROSS_CHEM, "no_soh")]:
            print(f"\n=== Cross-chemistry transfer [{feat_label}]: LCO → Severson LFP ===")
            for train_name, train_df in transfer_sets.items():
                n_cells = train_df["cell"].nunique()
                print(f"  Train: {train_name} ({n_cells} cells) → Test: Severson (per-cell eval)")

                for model_name, model in get_models().items():
                    for H in H_LIST:
                        y_test = make_composite_fail_in_H(test_df, H)
                        if len(np.unique(y_test)) < 2:
                            print(f"    {model_name} H={H} ... SKIP (no failures on test)")
                            continue

                        print(f"    {model_name} H={H} ...", end=" ", flush=True)
                        res = run_cross_chem_per_cell(train_df, test_df, model, H, features=features)
                        print(f"iso={res['AUC_cal_iso']:.3f}±{res['AUC_cal_iso_std']:.3f} "
                              f"platt={res['AUC_cal_platt']:.3f}±{res['AUC_cal_platt_std']:.3f}")

                        for method in ["iso", "platt"]:
                            all_rows.append({
                                "dataset": "severson",
                                "model": model_name,
                                "H": H,
                                "method": method,
                                "eval": f"train_{train_name}_{feat_label}",
                                "AUC_raw": res["AUC_raw"],
                                "AUC_cal": res[f"AUC_cal_{method}"],
                                "AUC_cal_std": res[f"AUC_cal_{method}_std"],
                                "Brier_cal": res[f"Brier_cal_{method}"],
                                "Brier_cal_std": res[f"Brier_cal_{method}_std"],
                            })
    else:
        print(f"SKIPPING Severson cross-chemistry — file not found: {severson_path}")

    results = pd.DataFrame(all_rows)
    results.to_csv(os.path.join(_DATA_DIR, "benchmark_results.csv"), index=False)
    print(f"\nSaved: benchmark_results.csv ({len(results)} rows)")
    print(results.groupby(["eval", "dataset", "method"]).agg(
        AUC_cal=("AUC_cal", "mean"), Brier_cal=("Brier_cal", "mean")
    ).round(3).to_string())

    # --- DeLong significance tests ---
    print("\n" + "=" * 60)
    print("DeLong AUC comparison tests")
    print("=" * 60)
    delong_rows = []

    # Within-dataset: pairwise model comparisons at H=20
    model_pairs = [
        ("xgboost", "lightgbm"),
        ("xgboost", "random_forest"),
        ("lightgbm", "random_forest"),
    ]
    for ds_name, ds_path in DATASETS.items():
        df_clean = clean_df(pd.read_csv(ds_path))
        models = get_models()
        preds = {}
        for m_name, m in models.items():
            if m_name not in {p[0] for p in model_pairs} | {p[1] for p in model_pairs}:
                continue
            res = run_cv(df_clean, m, 20, return_preds=True)
            if "y_true" in res:
                preds[m_name] = res

        for m_a, m_b in model_pairs:
            if m_a not in preds or m_b not in preds:
                continue
            if len(preds[m_a]["y_true"]) != len(preds[m_b]["y_true"]):
                continue
            d = delong_roc_test(preds[m_a]["y_true"], preds[m_a]["p_pred"], preds[m_b]["p_pred"])
            d_row = {"dataset": ds_name, "model_a": m_a, "model_b": m_b,
                     "H": 20, "setting": "within",
                     "AUC_a": d["auc_a"], "AUC_b": d["auc_b"],
                     "p_value": d["p_value"], "significant_0.05": d["significant_0.05"]}
            delong_rows.append(d_row)
            sig = " *" if d["significant_0.05"] else ""
            print(f"  {ds_name:6s} | {m_a:14s} vs {m_b:14s} | "
                  f"AUC={d['auc_a']:.3f} vs {d['auc_b']:.3f} | "
                  f"p={d['p_value']:.4f}{sig}")

    # Cross-chemistry: with-SOH vs without-SOH per model, + model vs model
    if os.path.exists(oxford_path):
        oxford_df = clean_df(pd.read_csv(oxford_path))
        nasa_df = clean_df(pd.read_csv(nasa_path))
        calce_df = clean_df(pd.read_csv(calce_path))
        combined_lco = pd.concat([nasa_df, calce_df], ignore_index=True)

        for train_name, train_df in [("nasa+calce", combined_lco)]:
            y_test_h20 = make_composite_fail_in_H(oxford_df, 20)
            if len(np.unique(y_test_h20)) < 2:
                continue

            # Collect predictions per model per feature set
            preds_with = {}
            preds_no = {}
            for m_name, m in get_models().items():
                res_with = run_cross_chem(train_df, oxford_df, m, 20,
                                          features=FEATURES, return_preds=True)
                if "y_true" in res_with and not np.isnan(res_with["AUC_raw"]):
                    preds_with[m_name] = res_with
                res_no = run_cross_chem(train_df, oxford_df, m, 20,
                                        features=FEATURES_CROSS_CHEM, return_preds=True)
                if "y_true" in res_no and not np.isnan(res_no["AUC_raw"]):
                    preds_no[m_name] = res_no

            # with-SOH vs without-SOH for each model
            for m_name in preds_with:
                if m_name not in preds_no:
                    continue
                d = delong_roc_test(preds_with[m_name]["y_true"],
                                    preds_with[m_name]["p_pred"],
                                    preds_no[m_name]["p_pred"])
                d_row = {"dataset": "oxford", "model_a": f"{m_name}_with_soh",
                         "model_b": f"{m_name}_no_soh", "H": 20,
                         "setting": "cross_chem_soh_ablation",
                         "AUC_a": d["auc_a"], "AUC_b": d["auc_b"],
                         "p_value": d["p_value"], "significant_0.05": d["significant_0.05"]}
                delong_rows.append(d_row)
                sig = " *" if d["significant_0.05"] else ""
                print(f"  oxford | {m_name:14s} with-SOH vs no-SOH | "
                      f"AUC={d['auc_a']:.3f} vs {d['auc_b']:.3f} | "
                      f"p={d['p_value']:.4f}{sig}")

            # Model-vs-model on with-SOH predictions
            for m_a, m_b in model_pairs:
                if m_a not in preds_with or m_b not in preds_with:
                    continue
                d = delong_roc_test(preds_with[m_a]["y_true"],
                                    preds_with[m_a]["p_pred"],
                                    preds_with[m_b]["p_pred"])
                d_row = {"dataset": "oxford", "model_a": m_a, "model_b": m_b,
                         "H": 20, "setting": "cross_chem_with_soh",
                         "AUC_a": d["auc_a"], "AUC_b": d["auc_b"],
                         "p_value": d["p_value"], "significant_0.05": d["significant_0.05"]}
                delong_rows.append(d_row)
                sig = " *" if d["significant_0.05"] else ""
                print(f"  oxford | {m_a:14s} vs {m_b:14s} (with SOH) | "
                      f"AUC={d['auc_a']:.3f} vs {d['auc_b']:.3f} | "
                      f"p={d['p_value']:.4f}{sig}")

    # Cross-chemistry DeLong: Severson LFP
    if os.path.exists(severson_path):
        severson_df = clean_df(pd.read_csv(severson_path))
        nasa_df = clean_df(pd.read_csv(nasa_path))
        calce_df = clean_df(pd.read_csv(calce_path))
        combined_lco = pd.concat([nasa_df, calce_df], ignore_index=True)

        for train_name, train_df in [("nasa+calce", combined_lco)]:
            y_test_h20 = make_composite_fail_in_H(severson_df, 20)
            if len(np.unique(y_test_h20)) < 2:
                continue

            # Collect predictions per model per feature set
            preds_with = {}
            preds_no = {}
            for m_name, m in get_models().items():
                res_with = run_cross_chem(train_df, severson_df, m, 20,
                                          features=FEATURES, return_preds=True)
                if "y_true" in res_with and not np.isnan(res_with["AUC_raw"]):
                    preds_with[m_name] = res_with
                res_no = run_cross_chem(train_df, severson_df, m, 20,
                                        features=FEATURES_CROSS_CHEM, return_preds=True)
                if "y_true" in res_no and not np.isnan(res_no["AUC_raw"]):
                    preds_no[m_name] = res_no

            # with-SOH vs without-SOH for each model
            for m_name in preds_with:
                if m_name not in preds_no:
                    continue
                d = delong_roc_test(preds_with[m_name]["y_true"],
                                    preds_with[m_name]["p_pred"],
                                    preds_no[m_name]["p_pred"])
                d_row = {"dataset": "severson", "model_a": f"{m_name}_with_soh",
                         "model_b": f"{m_name}_no_soh", "H": 20,
                         "setting": "cross_chem_soh_ablation",
                         "AUC_a": d["auc_a"], "AUC_b": d["auc_b"],
                         "p_value": d["p_value"], "significant_0.05": d["significant_0.05"]}
                delong_rows.append(d_row)
                sig = " *" if d["significant_0.05"] else ""
                print(f"  severson | {m_name:14s} with-SOH vs no-SOH | "
                      f"AUC={d['auc_a']:.3f} vs {d['auc_b']:.3f} | "
                      f"p={d['p_value']:.4f}{sig}")

            # Model-vs-model on with-SOH predictions
            for m_a, m_b in model_pairs:
                if m_a not in preds_with or m_b not in preds_with:
                    continue
                d = delong_roc_test(preds_with[m_a]["y_true"],
                                    preds_with[m_a]["p_pred"],
                                    preds_with[m_b]["p_pred"])
                d_row = {"dataset": "severson", "model_a": m_a, "model_b": m_b,
                         "H": 20, "setting": "cross_chem_with_soh",
                         "AUC_a": d["auc_a"], "AUC_b": d["auc_b"],
                         "p_value": d["p_value"], "significant_0.05": d["significant_0.05"]}
                delong_rows.append(d_row)
                sig = " *" if d["significant_0.05"] else ""
                print(f"  severson | {m_a:14s} vs {m_b:14s} (with SOH) | "
                      f"AUC={d['auc_a']:.3f} vs {d['auc_b']:.3f} | "
                      f"p={d['p_value']:.4f}{sig}")

    if delong_rows:
        delong_df = pd.DataFrame(delong_rows)
        tables_dir = os.path.join(_DATA_DIR, "..", "tables_journal")
        os.makedirs(tables_dir, exist_ok=True)
        delong_path = os.path.join(tables_dir, "DeLong_AUC_comparisons.csv")
        delong_df.to_csv(delong_path, index=False)
        print(f"\nSaved: {delong_path} ({len(delong_df)} comparisons)")


if __name__ == "__main__":
    main()
