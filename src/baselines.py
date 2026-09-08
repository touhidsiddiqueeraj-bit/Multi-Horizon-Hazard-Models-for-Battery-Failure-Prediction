"""E3: Minimal baselines (review point 12).

Answers: how much of the apparent performance is reproducible by trivial
health-threshold proxies?
  soh_dist    score = 0.80 - SOH   (no fitting; distance to the label threshold)
  soh_only    logistic on SOH
  cycle_only  logistic on cycle index
  soh_cycle   logistic on SOH + cycle
  sensors     logistic on voltage/current/temp/duration (no SOH, no cycle)
  full        logistic on all seven features

Logistic models are fit per training split (within: per outer fold;
transfer: on all source cells). Discrimination + Brier reported with
cell-level bootstrap CIs on pooled rows.
"""
import argparse
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from composite_label import make_composite_fail_in_H
from stats_utils import bootstrap_cis_methods
from pipeline_core import (load_clean, load_source, summarize, save_preds,
                           results_path, FEATURE_SETS, SENSOR_FEATURES,
                           FULL_FEATURES, H_LIST)

BASELINES = {
    "soh_dist": None,  # rule-based, no fitting
    "soh_only": ["SOH"],
    "cycle_only": ["cycle"],
    "soh_cycle": ["SOH", "cycle"],
    "sensors": SENSOR_FEATURES,
    "full": FULL_FEATURES,
}


def score_dispatch(name, features):
    if name == "soh_dist":
        return None
    return make_pipeline(StandardScaler(),
                         LogisticRegression(max_iter=1000, C=1.0))


def predict_scores(name, model, X):
    if name == "soh_dist":
        # X columns: [SOH]; distance below the 0.80 threshold
        return 0.80 - X[:, 0]
    return model.predict_proba(X)[:, 1]


def boot_n(y):
    return 400 if len(y) > 20000 else 1000


def eval_pool(y, p, cells, tag_rows):
    s = summarize(y, p, cells)
    _, lo, hi = bootstrap_cis_methods(y, {"s": p}, cells, methods=["s"], n_boot=boot_n(y))["s"]
    s["AUC_lo"], s["AUC_hi"] = lo, hi
    return s


def cmd_within():
    rows = []
    for ds_name in ["nasa", "calce"]:
        df = load_clean(ds_name)
        cells = df["cell"].to_numpy()
        uniq = pd.unique(cells)
        outer_k = len(uniq) if len(uniq) <= 8 else 5
        gkf = GroupKFold(n_splits=outer_k)
        for bname, feats in BASELINES.items():
            cols = [c for c in (feats or ["SOH"]) if c in df.columns]
            X = df[cols].values
            # loop horizons inside baseline, reusing deterministic splits
            for H in H_LIST:
                y = make_composite_fail_in_H(df, H)
                if len(np.unique(y)) < 2:
                    continue
                py, pp, pc = [], [], []
                for tr, te in gkf.split(X, groups=cells):
                    if len(np.unique(y[tr])) < 2:
                        continue
                    mdl = score_dispatch(bname, cols)
                    if mdl is not None:
                        mdl.fit(X[tr], y[tr])
                    py.append(y[te])
                    pp.append(predict_scores(bname, mdl, X[te]))
                    pc.append(cells[te])
                y_all, p_all, c_all = np.concatenate(py), np.concatenate(pp), np.concatenate(pc)
                r = eval_pool(y_all, p_all, c_all, None)
                r.update(dataset=ds_name, baseline=bname, H=H, model=f"logistic_{bname}")
                rows.append(r)
                print(f"  within {ds_name} {bname:10s} H={H}: AUC={r['AUC']:.3f} "
                      f"[{r['AUC_lo']:.3f},{r['AUC_hi']:.3f}]", flush=True)
                if H == 20:
                    save_preds(f"within_{ds_name}_base_{bname}_H20.csv",
                               pd.DataFrame({"cell": c_all, "y": y_all, "p_raw": p_all}))
    pd.DataFrame(rows).to_csv(results_path("baselines_within.csv"), index=False)
    print("saved baselines_within.csv", flush=True)


def cmd_transfer():
    rows = []
    sources = ["nasa", "calce", "nasa+calce"]
    targets = ["oxford", "severson"]
    for target_name in targets:
        test_df = load_clean(target_name)
        for source_key in sources:
            train_df = load_source(source_key)
            for bname, feats in BASELINES.items():
                cols = [c for c in (feats or ["SOH"])
                        if c in train_df.columns and c in test_df.columns]
                X_tr = train_df[cols].values
                X_te = test_df[cols].values
                for H in H_LIST:
                    y_tr = make_composite_fail_in_H(train_df, H)
                    y_te = make_composite_fail_in_H(test_df, H)
                    if len(np.unique(y_te)) < 2 or len(np.unique(y_tr)) < 2:
                        continue
                    mdl = score_dispatch(bname, cols)
                    if mdl is not None:
                        mdl.fit(X_tr, y_tr)
                    p = predict_scores(bname, mdl, X_te)
                    cells = test_df["cell"].to_numpy()
                    r = eval_pool(y_te, p, cells, None)
                    r.update(source=source_key, target=target_name, baseline=bname,
                             H=H, model=f"logistic_{bname}")
                    rows.append(r)
                    print(f"  transfer {source_key}->{target_name} {bname:10s} H={H}: "
                          f"AUC={r['AUC']:.3f} [{r['AUC_lo']:.3f},{r['AUC_hi']:.3f}]", flush=True)
                    if H == 20:
                        save_preds(f"transfer_{target_name}_{source_key}_base_{bname}_H20.csv",
                                   pd.DataFrame({"cell": cells, "y": y_te, "p_raw": p}))
    pd.DataFrame(rows).to_csv(results_path("baselines_transfer.csv"), index=False)
    print("saved baselines_transfer.csv", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["within", "transfer", "all"])
    args = ap.parse_args()
    if args.cmd in ("within", "all"):
        cmd_within()
    if args.cmd in ("transfer", "all"):
        cmd_transfer()


if __name__ == "__main__":
    main()
