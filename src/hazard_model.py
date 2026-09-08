"""E2: true discrete-time hazard/survival model (review point 3).

For each observed cycle t and each offset l in {1..L}, define the
discrete-time hazard conditional on the features AT t (operational: no
future measurements):

    h_l(t) = P(T_f = t + l | T_f >= t + l, x_t)

One pooled classifier (XGBoost or logistic regression) is fit on the
offset-expanded at-risk training rows (offset l is an input feature).
Cumulative failure risk over horizon H is the survival product

    R(t, H) = 1 - prod_{l=1..H} (1 - h_l(t)),

which is monotone non-decreasing in H by construction (unlike four
independent fixed-horizon classifiers).

Training rows are restricted to the risk set (t + l <= T_f). Evaluation
scores every row exactly like the fixed-horizon classifiers (including
rows at/after failure, which the fixed-horizon labels mark positive).
No post-hoc calibration is applied to R; discrimination is the readout.
"""
import argparse
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from composite_label import composite_fail_cycle, make_composite_fail_in_H
from stats_utils import bootstrap_cis_methods, safe_auc
from pipeline_core import (get_models, load_clean, load_source, summarize,
                           save_preds, results_path, FULL_FEATURES, H_LIST)

L_MAX = 50
MODELS = {
    "hazard_xgb": lambda: get_models()["xgboost"],
    "hazard_logistic": lambda: make_pipeline(
        StandardScaler(), LogisticRegression(max_iter=2000, C=1.0)),
}


def build_offset_frame(df, features, endpoint="combined"):
    """Offset-expanded at-risk training rows. Returns X, y."""
    df = df.reset_index(drop=True)
    fail = composite_fail_cycle(df, endpoint=endpoint)
    xs, ys = [], []
    fvals = df[features].values.astype(np.float32)
    for _, g in df.groupby("cell", sort=False):
        pos = g.index.to_numpy()
        cycles = g["cycle"].to_numpy().astype(float)
        cell_fail = float(fail.loc[pos].iloc[0])
        if not np.isfinite(cell_fail):
            for l in range(1, L_MAX + 1):
                xs.append(np.column_stack([fvals[pos], np.full(len(pos), l, dtype=np.float32)]))
                ys.append(np.zeros(len(pos), dtype=np.int8))
            continue
        for l in range(1, L_MAX + 1):
            m = cycles + l <= cell_fail
            if not m.any():
                continue
            sel = pos[m]
            xs.append(np.column_stack([fvals[sel], np.full(m.sum(), l, dtype=np.float32)]))
            ys.append((cycles[m] + l == cell_fail).astype(np.int8))
    return np.vstack(xs), np.concatenate(ys)


def predict_R(model, df, features, H_list):
    """Cumulative risk R(t, H) for each H from one hazard pass to L_MAX."""
    fvals = df[features].values.astype(np.float32)
    n = len(df)
    surv = {H: np.ones(n, dtype=np.float64) for H in H_list}
    for l in range(1, L_MAX + 1):
        X = np.column_stack([fvals, np.full(n, l, dtype=np.float32)])
        h = model.predict_proba(X)[:, 1]
        for H in H_list:
            if l <= H:
                surv[H] *= (1.0 - h)
    return {H: 1.0 - s for H, s in surv.items()}


def monotonicity_violation_rate(pred_by_H):
    Hs = sorted(pred_by_H)
    viol, n = 0, 0
    for a, b in zip(Hs[:-1], Hs[1:]):
        viol += int(np.sum(pred_by_H[b] < pred_by_H[a] - 1e-12))
        n += len(pred_by_H[a])
    return viol / n if n else np.nan


def boot_n(y):
    return 400 if len(y) > 20000 else 1000


def attach_ci(y, p, cells, r):
    _, lo, hi = bootstrap_cis_methods(y, {"s": p}, cells, methods=["s"],
                                      n_boot=boot_n(y))["s"]
    r["AUC_lo"], r["AUC_hi"] = lo, hi
    return r


def run_within():
    rows = []
    for ds_name in ["nasa", "calce"]:
        df = load_clean(ds_name)
        cells = df["cell"].to_numpy()
        uniq = pd.unique(cells)
        outer_k = len(uniq) if len(uniq) <= 8 else 5
        gkf = GroupKFold(n_splits=outer_k)
        folds = list(gkf.split(np.zeros((len(df), 1)), groups=cells))
        te_all = np.concatenate([te for _, te in folds])
        for mname, mfactory in MODELS.items():
            preds_by_fold = {H: [] for H in H_LIST}
            fold_aucs = {H: [] for H in H_LIST}
            for tr, te in folds:
                X_tr, y_tr = build_offset_frame(df.iloc[tr], FULL_FEATURES)
                if len(np.unique(y_tr)) < 2:
                    continue
                mdl = mfactory()
                mdl.fit(X_tr, y_tr)
                p_all_folds = predict_R(mdl, df, FULL_FEATURES, H_LIST)
                for H in H_LIST:
                    preds_by_fold[H].append(p_all_folds[H][te])
                    y_fold = make_composite_fail_in_H(df, H)[te]
                    a = safe_auc(y_fold, p_all_folds[H][te])
                    if np.isfinite(a):
                        fold_aucs[H].append(a)
            cs_all = cells[te_all]
            for H in H_LIST:
                if not preds_by_fold[H]:
                    continue
                y_all = make_composite_fail_in_H(df, H)[te_all]
                p_all = np.concatenate(preds_by_fold[H])
                if len(np.unique(y_all)) < 2:
                    continue
                r = summarize(y_all, p_all, cs_all)
                r = attach_ci(y_all, p_all, cs_all, r)
                r.update(dataset=ds_name, model=mname, H=H, method="raw",
                         AUC_fold_mean=float(np.mean(fold_aucs[H])) if fold_aucs[H] else np.nan,
                         AUC_fold_std=float(np.std(fold_aucs[H], ddof=1)) if len(fold_aucs[H]) > 1 else np.nan)
                rows.append(r)
                print(f"  within {ds_name} {mname} H={H}: AUC={r['AUC']:.3f} "
                      f"[{r['AUC_lo']:.3f},{r['AUC_hi']:.3f}]", flush=True)
                if H == 20:
                    save_preds(f"within_{ds_name}_{mname}_H20.csv",
                               pd.DataFrame({"cell": cs_all, "y": y_all, "p_raw": p_all}))
    pd.DataFrame(rows).to_csv(results_path("hazard_within.csv"), index=False)
    print("saved hazard_within.csv", flush=True)


def run_transfer():
    rows = []
    for target_name in ["oxford", "severson"]:
        test_df = load_clean(target_name)
        cells = test_df["cell"].to_numpy()
        for source_key in ["nasa", "calce", "nasa+calce"]:
            train_df = load_source(source_key)
            for mname, mfactory in MODELS.items():
                X_tr, y_tr = build_offset_frame(train_df, FULL_FEATURES)
                mdl = mfactory()
                mdl.fit(X_tr, y_tr)
                preds = predict_R(mdl, test_df, FULL_FEATURES, H_LIST)
                for H in H_LIST:
                    y_te = make_composite_fail_in_H(test_df, H)
                    if len(np.unique(y_te)) < 2:
                        continue
                    r = summarize(y_te, preds[H], cells)
                    r = attach_ci(y_te, preds[H], cells, r)
                    r.update(source=source_key, target=target_name, model=mname,
                             H=H, method="raw")
                    rows.append(r)
                    print(f"  {source_key:10s}->{target_name:8s} {mname} H={H}: "
                          f"AUC={r['AUC']:.3f} [{r['AUC_lo']:.3f},{r['AUC_hi']:.3f}]", flush=True)
                    if H == 20:
                        save_preds(f"transfer_{target_name}_{source_key}_{mname}_H20.csv",
                                   pd.DataFrame({"cell": cells, "y": y_te, "p_raw": preds[H]}))
    pd.DataFrame(rows).to_csv(results_path("hazard_transfer.csv"), index=False)
    print("saved hazard_transfer.csv", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["within", "transfer", "all"])
    args = ap.parse_args()
    if args.cmd in ("within", "all"):
        run_within()
    if args.cmd in ("transfer", "all"):
        run_transfer()


if __name__ == "__main__":
    main()
