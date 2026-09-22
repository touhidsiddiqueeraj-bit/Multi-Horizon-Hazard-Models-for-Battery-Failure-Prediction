"""Tree-model benchmark: within-dataset CV and LCO->LFP / same-chemistry
transfer with cell-disjoint splits and cross-fitted (leakage-clean)
calibration.

Outputs (results_v2/):
  within_trees.csv        pooled fold metrics per (dataset, model, H, method)
  transfer_trees.csv      per-cell-mean metrics per (source, target, model, H, feature_set)
  soh_ablation_tests.csv  paired cell-bootstrap + DeLong (secondary) for with/without SOH
  preds/*.csv             pooled test predictions (for figures, bootstrap, costs)

CLI:  python benchmark_cv.py within|transfer|ablation_tests|all
"""
import sys
import argparse
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold
from sklearn.base import clone

from composite_label import make_composite_fail_in_H
from stats_utils import (metric_bundle, bootstrap_cis_methods,
                         paired_cell_bootstrap_delta, delong_roc_test)
from pipeline_core import (
    get_models, load_clean, load_source, inner_cell_splits, fit_calibrators,
    apply_calibrators, cross_fitted_oof, summarize, save_preds, load_preds,
    results_path, FEATURE_SETS, H_LIST, LCO_SOURCES, BA_DATASETS,
    TRANSFER_SOURCES, BA_TARGETS,
)

TARGETS = ["oxford", "severson"]
TRANSFER_FEATURE_SETS = ["with_soh", "no_soh", "common_with_soh", "common_no_soh"]
INNER_K = {"nasa": 4, "calce": 3, "nasa+calce": 5, "severson": 5, "oxford": 4,
           # Battery Archive sources: cells are few, protocols uniform, so a
           # small inner split is enough for the cross-fitted calibrators.
           "ba_lfp_snl": 4, "ba_nca_snl": 4, "ba_nmc_hnei": 4,
           "ba_nmc_snl": 3, "nmc_all": 4, "ba_all": 5}
BOOT_METHODS = ["raw", "platt"]

# Sources used for the chemistry-extension SOH-ablation tests: the original
# pooled LCO source plus the two same-chemistry Battery Archive sources.
BA_TEST_SOURCES = ["nasa+calce", "ba_lfp_snl", "nmc_all"]

# The 21-cell / 76k-row SNL LFP group is only partly degraded (most cells stay
# above SOH 0.80 inside the released window), so it is run at the headline
# horizon only; the three smaller groups use the full horizon grid.
BA_H_GRID = {"ba_lfp_snl": [20]}
BA_INNER_K = {"ba_nmc_hnei": 4, "ba_nca_snl": 4, "ba_nmc_snl": 3, "ba_lfp_snl": 3}


def boot_n(y):
    """Scale bootstrap draws to pool size (Severson's 117k rows are the cost driver)."""
    return 400 if len(y) > 20000 else 1000


# ---------------------------------------------------------------- within-dataset
def run_within(model_name, model, df, H, endpoint="combined", feature_set="with_soh",
               inner_k=None):
    """Outer GroupKFold (or LOCO when few cells) over cells.

    Per outer fold: model trains on train cells; calibrators fit on
    inner-cross-fitted OOF scores of the train cells; test cells untouched.
    `inner_k` overrides the legacy pooled value; the original grids leave it
    unset so their numbers stay reproducible.
    """
    features = FEATURE_SETS[feature_set]
    y = make_composite_fail_in_H(df, H, endpoint=endpoint)
    if len(np.unique(y)) < 2:
        return None
    cells = df["cell"].to_numpy()
    n_cells = len(np.unique(cells))
    outer_k = n_cells if n_cells <= 8 else 5  # LOCO for CALCE (7 cells)
    X = df[features].values

    methods = ["raw", "iso", "platt", "temp"]
    pooled = {m: [] for m in methods}
    ys, cs = [], []
    fold_aucs = {m: [] for m in methods}

    gkf = GroupKFold(n_splits=outer_k)
    for tr, te in gkf.split(X, y, groups=cells):
        tr_df = df.iloc[tr]
        oof, y_tr, _ = cross_fitted_oof(
            tr_df, model, features, H, endpoint=endpoint,
            inner_k=inner_k or INNER_K.get("nasa+calce", 4))
        cal = fit_calibrators(oof, y_tr)
        if len(np.unique(y_tr)) < 2 or cal is None:
            continue
        m = clone(model)
        m.fit(X[tr], y_tr)
        p_raw = m.predict_proba(X[te])[:, 1]
        preds = apply_calibrators(cal, p_raw)
        for name in methods:
            pooled[name].append(preds[name])
        ys.append(y[te])
        cs.append(cells[te])
        for name in methods:
            a = metric_bundle(y[te], preds[name])["AUC"]
            if np.isfinite(a):
                fold_aucs[name].append(a)

    y_all = np.concatenate(ys)
    c_all = np.concatenate(cs)
    preds_by_method = {}
    for name in methods:
        preds_by_method[name] = np.concatenate(pooled[name])
    cis = bootstrap_cis_methods(y_all, preds_by_method, c_all,
                                methods=BOOT_METHODS, n_boot=boot_n(y_all))
    rows = []
    for name in methods:
        r = summarize(y_all, preds_by_method[name], c_all)
        if name in cis:
            _, r["AUC_lo"], r["AUC_hi"] = cis[name]
        rows.append((name, r))
    return y_all, c_all, preds_by_method, rows, fold_aucs


def _within_grid(ds_names, out_file, preds_prefix="within", inner_k_by_ds=None,
                 h_grid=None):
    """Cell-disjoint within-dataset grid; shared by the original and the
    Battery Archive chemistry extension so both paths are identical."""
    models = get_models()
    out_rows = []
    for ds_name in ds_names:
        df = load_clean(ds_name)
        h_list = (h_grid or {}).get(ds_name, H_LIST)
        ik = (inner_k_by_ds or {}).get(ds_name)
        print(f"=== within [{ds_name}] {df['cell'].nunique()} cells, {len(df)} rows ===", flush=True)
        for model_name, model in models.items():
            for H in h_list:
                res = run_within(model_name, model, df, H, inner_k=ik)
                if res is None:
                    print(f"  {model_name} H={H}: skipped (single class)", flush=True)
                    continue
                y_all, c_all, preds, rows, fold_aucs = res
                for method, r in rows:
                    r["dataset"] = ds_name
                    r["model"] = model_name
                    r["H"] = H
                    r["method"] = method
                    r["AUC_fold_mean"] = float(np.mean(fold_aucs[method])) if fold_aucs[method] else np.nan
                    r["AUC_fold_std"] = float(np.std(fold_aucs[method], ddof=1)) if len(fold_aucs[method]) > 1 else np.nan
                    out_rows.append(r)
                if model_name == "xgboost" or H == 20:
                    save_preds(f"{preds_prefix}_{ds_name}_{model_name}_H{H}.csv",
                               pd.DataFrame({"cell": c_all, "y": y_all,
                                             "p_raw": preds["raw"], "p_iso": preds["iso"],
                                             "p_platt": preds["platt"], "p_temp": preds["temp"]}))
                print(f"  {model_name} H={H}: raw={rows[0][1]['AUC']:.3f} "
                      f"platt={rows[2][1]['AUC']:.3f} "
                      f"[{rows[2][1]['AUC_lo']:.3f},{rows[2][1]['AUC_hi']:.3f}] "
                      f"ECE={rows[2][1]['ECE10']:.3f} PRAUC={rows[0][1]['PRAUC']:.3f}", flush=True)
    pd.DataFrame(out_rows).to_csv(results_path(out_file), index=False)
    print(f"saved {out_file}", flush=True)


def cmd_within():
    _within_grid(["nasa", "calce"], "within_trees.csv")


def cmd_within_ba():
    """Within-dataset reliability on the Battery Archive chemistry extension."""
    _within_grid(BA_DATASETS, "within_trees_ba.csv", preds_prefix="ba_within",
                 inner_k_by_ds=BA_INNER_K, h_grid=BA_H_GRID)


# ---------------------------------------------------------------- transfer
def run_transfer(source_key, target_name, model, H, feature_set,
                 endpoint="combined", return_pooled=False):
    """Train once on all source cells; calibrators fit on source OOF scores;
    per-cell evaluation on the untouched target."""
    train_df = load_source(source_key)
    test_df = load_clean(target_name)
    features = FEATURE_SETS[feature_set]
    features = [c for c in features if c in train_df.columns and c in test_df.columns]

    y_test = make_composite_fail_in_H(test_df, H, endpoint=endpoint)
    if len(np.unique(y_test)) < 2:
        return None

    oof, y_src, _ = cross_fitted_oof(train_df, model, features, H, endpoint=endpoint,
                                     inner_k=INNER_K[source_key])
    cal = fit_calibrators(oof, y_src)
    if cal is None:
        return None

    m = clone(model)
    m.fit(train_df[features].values, y_src)
    p_raw = m.predict_proba(test_df[features].values)[:, 1]
    preds = apply_calibrators(cal, p_raw)

    cells = test_df["cell"].to_numpy()
    out = {"source": source_key, "target": target_name, "H": H,
           "feature_set": feature_set, "model": model.__class__.__name__}
    for method in ["raw", "iso", "platt", "temp"]:
        r = summarize(y_test, preds[method], cells)
        for k, v in r.items():
            out[f"{method}_{k}"] = v
    cis = bootstrap_cis_methods(y_test, preds, cells, methods=BOOT_METHODS, n_boot=boot_n(y_test))
    for method, (_, lo, hi) in cis.items():
        out[f"{method}_AUC_lo"], out[f"{method}_AUC_hi"] = lo, hi
    if return_pooled:
        pooled = pd.DataFrame({
            "cell": cells, "y": y_test,
            "p_raw": preds["raw"], "p_iso": preds["iso"],
            "p_platt": preds["platt"], "p_temp": preds["temp"],
        })
        return out, pooled
    return out


def cmd_transfer():
    models = get_models()
    out_rows = []
    for target_name in TARGETS:
        print(f"=== transfer -> {target_name} ===", flush=True)
        for source_key in LCO_SOURCES:
            for feature_set in TRANSFER_FEATURE_SETS:
                for model_name, model in models.items():
                    for H in H_LIST:
                        res = run_transfer(source_key, target_name, model, H, feature_set,
                                           return_pooled=True)
                        if res is None:
                            continue
                        out, pooled = res
                        out["model"] = model_name
                        out_rows.append(out)
                        save_preds(f"transfer_{target_name}_{source_key}_{feature_set}_{model_name}_H{H}.csv",
                                   pooled)
                        print(f"  {source_key:10s} {feature_set:16s} {model_name:13s} H={H}: "
                              f"raw={out['raw_AUC']:.3f} platt={out['platt_AUC']:.3f} "
                              f"percell={out['raw_AUC_percell_mean']:.3f}", flush=True)
    pd.DataFrame(out_rows).to_csv(results_path("transfer_trees.csv"), index=False)
    print("saved transfer_trees.csv", flush=True)


# ---------------------------------------------------------------- SOH-ablation tests
def cmd_ablation_tests():
    """Primary: paired cell-level bootstrap for with-SOH vs without-SOH.
    Secondary: cycle-level DeLong (pseudoreplication caveat applies)."""
    models = get_models()
    rows = []
    for target_name in TARGETS:
        for source_key in ["nasa+calce"]:
            for model_name, model in models.items():
                for H in H_LIST:
                    f_with = f"transfer_{target_name}_{source_key}_with_soh_{model_name}_H{H}.csv"
                    f_no = f"transfer_{target_name}_{source_key}_no_soh_{model_name}_H{H}.csv"
                    try:
                        d_with = load_preds(f_with)
                        d_no = load_preds(f_no)
                    except FileNotFoundError:
                        continue
                    assert (d_with["y"].to_numpy() == d_no["y"].to_numpy()).all()
                    y = d_with["y"].to_numpy()
                    cells = d_with["cell"].to_numpy()
                    delta, lo, hi = paired_cell_bootstrap_delta(
                        y, d_with["p_raw"].to_numpy(), d_no["p_raw"].to_numpy(),
                        cells, n_boot=boot_n(y))
                    d = delong_roc_test(y, d_with["p_raw"].to_numpy(), d_no["p_raw"].to_numpy())
                    rows.append({
                        "target": target_name, "source": source_key, "model": model_name, "H": H,
                        "auc_with": d["auc_a"], "auc_without": d["auc_b"],
                        "delta_bootstrap": delta, "delta_lo": lo, "delta_hi": hi,
                        "delong_p_cyclelevel": d["p_value"],
                    })
                    print(f"  {target_name} {model_name} H={H}: dAUC={delta:.3f} [{lo:.3f},{hi:.3f}] "
                          f"delong_p={d['p_value']:.2e}", flush=True)
    pd.DataFrame(rows).to_csv(results_path("soh_ablation_tests.csv"), index=False)
    print("saved soh_ablation_tests.csv", flush=True)


def run_transfer_multi(source_key, target_names, model, H, feature_set,
                       endpoint="combined"):
    """Train once on the source, evaluate the fitted model on several targets.

    Identical protocol to run_transfer -- calibrators fitted on the source's
    cross-fitted out-of-fold scores, targets untouched -- but the source fit
    (the expensive part) is shared across targets. Targets whose cells appear
    in the source are skipped so no training cell can be scored.
    """
    train_df = load_source(source_key)
    features = FEATURE_SETS[feature_set]
    oof, y_src, _ = cross_fitted_oof(train_df, model, features, H, endpoint=endpoint,
                                     inner_k=INNER_K[source_key])
    cal = fit_calibrators(oof, y_src)
    if cal is None:
        return []
    features = [c for c in features if c in train_df.columns]
    m = clone(model)
    m.fit(train_df[features].values, y_src)
    skip = set(TRANSFER_SOURCES[source_key])
    results = []
    for target_name in target_names:
        if target_name in skip:
            continue
        test_df = load_clean(target_name)
        feats = [c for c in features if c in test_df.columns]
        y_test = make_composite_fail_in_H(test_df, H, endpoint=endpoint)
        if len(np.unique(y_test)) < 2:
            print(f"  {source_key}->{target_name} H={H} {feature_set}: single-class target",
                  flush=True)
            continue
        p_raw = m.predict_proba(test_df[feats].values)[:, 1]
        preds = apply_calibrators(cal, p_raw)
        cells = test_df["cell"].to_numpy()
        out = {"source": source_key, "target": target_name, "H": H,
               "feature_set": feature_set, "model": model.__class__.__name__}
        for method in ["raw", "iso", "platt", "temp"]:
            for k, v in summarize(y_test, preds[method], cells).items():
                out[f"{method}_{k}"] = v
        cis = bootstrap_cis_methods(y_test, preds, cells, methods=BOOT_METHODS,
                                    n_boot=boot_n(y_test))
        for method, (_, lo, hi) in cis.items():
            out[f"{method}_AUC_lo"], out[f"{method}_AUC_hi"] = lo, hi
        pooled = pd.DataFrame({"cell": cells, "y": y_test, "p_raw": preds["raw"],
                               "p_iso": preds["iso"], "p_platt": preds["platt"],
                               "p_temp": preds["temp"]})
        results.append((out, pooled))
    return results


def cmd_transfer_ba():
    """Chemistry-extension transfer grid.

    Sources: the original LCO sources plus the Battery Archive sources
    (SNL LFP, SNL NCA, HNEI NMC, pooled NMC, pooled Battery Archive).
    Targets: Oxford, Severson and the four Battery Archive groups.
    """
    models = get_models()
    out_rows = []
    for source_key in TRANSFER_SOURCES:
        for feature_set in TRANSFER_FEATURE_SETS:
            for model_name, model in models.items():
                for H in H_LIST:
                    targets = [t for t in BA_TARGETS if H in BA_H_GRID.get(t, H_LIST)]
                    if not targets:
                        continue
                    res = run_transfer_multi(source_key, targets, model, H, feature_set)
                    for out, pooled in res:
                        out["model"] = model_name
                        out_rows.append(out)
                        save_preds(f"ba_transfer_{out['target']}_{source_key}_"
                                   f"{feature_set}_{model_name}_H{H}.csv", pooled)
                        print(f"  {source_key:11s} {feature_set:16s} {model_name:13s} "
                              f"H={H:2d} -> {out['target']:12s}: raw={out['raw_AUC']:.3f} "
                              f"[{out['raw_AUC_lo']:.3f},{out['raw_AUC_hi']:.3f}] "
                              f"percell={out['raw_AUC_percell_mean']:.3f}", flush=True)
                    pd.DataFrame(out_rows).to_csv(results_path("transfer_ba.csv"), index=False)
    print("saved transfer_ba.csv", flush=True)


def cmd_ablation_tests_ba():
    """Paired with/without-SOH cell bootstrap for the Battery Archive targets."""
    models = get_models()
    rows = []
    for target_name in BA_TARGETS:
        for source_key in BA_TEST_SOURCES:
            if target_name in TRANSFER_SOURCES[source_key]:
                continue
            for model_name, model in models.items():
                for H in H_LIST:
                    f_with = (f"ba_transfer_{target_name}_{source_key}_with_soh_"
                              f"{model_name}_H{H}.csv")
                    f_no = (f"ba_transfer_{target_name}_{source_key}_no_soh_"
                            f"{model_name}_H{H}.csv")
                    try:
                        d_with = load_preds(f_with)
                        d_no = load_preds(f_no)
                    except FileNotFoundError:
                        continue
                    assert (d_with["y"].to_numpy() == d_no["y"].to_numpy()).all()
                    y = d_with["y"].to_numpy()
                    cells = d_with["cell"].to_numpy()
                    delta, lo, hi = paired_cell_bootstrap_delta(
                        y, d_with["p_raw"].to_numpy(), d_no["p_raw"].to_numpy(),
                        cells, n_boot=boot_n(y))
                    d = delong_roc_test(y, d_with["p_raw"].to_numpy(), d_no["p_raw"].to_numpy())
                    rows.append({
                        "target": target_name, "source": source_key, "model": model_name, "H": H,
                        "auc_with": d["auc_a"], "auc_without": d["auc_b"],
                        "delta_bootstrap": delta, "delta_lo": lo, "delta_hi": hi,
                        "delong_p_cyclelevel": d["p_value"],
                    })
                    print(f"  {source_key}->{target_name} {model_name} H={H}: "
                          f"dAUC={delta:.3f} [{lo:.3f},{hi:.3f}]", flush=True)
    pd.DataFrame(rows).to_csv(results_path("soh_ablation_tests_ba.csv"), index=False)
    print("saved soh_ablation_tests_ba.csv", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["within", "transfer", "ablation_tests", "all",
                                    "within_ba", "transfer_ba", "ablation_tests_ba",
                                    "all_ba"])
    args = ap.parse_args()
    if args.cmd in ("within", "all"):
        cmd_within()
    if args.cmd in ("transfer", "all"):
        cmd_transfer()
    if args.cmd in ("ablation_tests", "all"):
        cmd_ablation_tests()
    if args.cmd in ("within_ba", "all_ba"):
        cmd_within_ba()
    if args.cmd in ("transfer_ba", "all_ba"):
        cmd_transfer_ba()
    if args.cmd in ("ablation_tests_ba", "all_ba"):
        cmd_ablation_tests_ba()


if __name__ == "__main__":
    main()
