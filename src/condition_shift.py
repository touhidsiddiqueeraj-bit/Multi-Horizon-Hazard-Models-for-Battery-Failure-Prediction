"""Condition-shift control (Battery Archive chemistry extension).

The journal paper attributes the failure to transfer to *dataset shift* at
least as much as to chemistry, using same-chemistry cross-laboratory controls.
The Battery Archive export makes a strictly stronger control possible: inside
one dataset -- one chemistry, one laboratory, one cell model -- several
operating conditions are represented (chamber temperature, C-rate). Holding out
*conditions* rather than randomly held-out cells changes the operating regime
while chemistry, laboratory and instrumentation are fixed.

Protocol
--------
* Split: leave-one-condition-out. Every cell of the held-out condition goes to
  the test side, so the split is still cell-disjoint, and neither the cells nor
  the operating conditions of the test set were seen during training.
* Calibrators are fitted on the training cells' cross-fitted out-of-fold scores
  (the same leakage-clean protocol as every other result in the paper).
* Reference: an ordinary 5-fold cell-grouped split of the same dataset, i.e.
  random cells but mixed conditions. Reference AUC minus condition-shift AUC is
  the part of the shortfall attributable to the operating regime alone.
* Baselines per fold: with-SOH vs without-SOH trees, plus the unfitted
  distance-to-threshold rule on SOH, 0.80 - SOH.

Output: results_v2/condition_shift.csv
"""
import os
import sys

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.model_selection import GroupKFold

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from composite_label import make_composite_fail_in_H  # noqa: E402
from stats_utils import metric_bundle, safe_auc, cell_bootstrap_auc_ci  # noqa: E402
from pipeline_core import (  # noqa: E402
    load_clean, get_models, cross_fitted_oof, fit_calibrators, apply_calibrators,
    results_path, FEATURE_SETS,
)

# HNEI NMC/LCO cycles under a single condition (25 C, 0.5/1.5C), so it carries
# no condition variation and is absent here by construction.
# The 76 k-row SNL LFP group is restricted to the headline horizon and the two
# headline feature sets; its cells are mostly right-censored, so its
# condition-shift numbers are supporting rather than headline evidence.
DS_CONFIG = {
    "ba_nca_snl": {"H": [10, 20, 30, 50], "fs": ["with_soh", "no_soh",
                                                "common_with_soh", "common_no_soh"]},
    "ba_nmc_snl": {"H": [10, 20, 30, 50], "fs": ["with_soh", "no_soh",
                                                "common_with_soh", "common_no_soh"]},
    "ba_lfp_snl": {"H": [20], "fs": ["with_soh", "common_no_soh"]},
}
DATASETS = list(DS_CONFIG)
MODES = {"temp_rate": ["temp_C", "rate"], "temp": ["temp_C"], "rate": ["rate"]}
INNER_K = 3
BOOT_N = 400


def condition_key(df, cols):
    return df[cols].astype(str).agg("|".join, axis=1)


def fit_score(train_df, test_df, features, model, H, endpoint="combined"):
    """Leakage-clean source fit, then scores on the untouched test cells."""
    oof, y_tr, _ = cross_fitted_oof(train_df, model, features, H,
                                    endpoint=endpoint, inner_k=INNER_K)
    cal = fit_calibrators(oof, y_tr)
    if cal is None:
        return None
    y_te = make_composite_fail_in_H(test_df, H, endpoint=endpoint)
    if len(np.unique(y_te)) < 2:
        return None
    m = clone(model)
    m.fit(train_df[features].values, y_tr)
    p_raw = m.predict_proba(test_df[features].values)[:, 1]
    preds = apply_calibrators(cal, p_raw)
    return y_te, preds, test_df["cell"].to_numpy(), test_df["SOH"].to_numpy()


def _row(dataset, mode, setting, held_out, feature_set, model_name, H,
         y, preds, cells, soh):
    out = {"dataset": dataset, "mode": mode, "setting": setting,
           "held_out": held_out, "feature_set": feature_set,
           "model": model_name, "H": H,
           "rows": int(len(y)), "n_cells": int(len(np.unique(cells))),
           "n_pos": int(np.asarray(y).sum())}
    for method in ("raw", "platt"):
        out[f"AUC_{method}"] = metric_bundle(y, preds[method])["AUC"]
    out["AUC_dist_rule"] = safe_auc(y, 0.80 - np.asarray(soh, dtype=float))
    return out


def _pooled(parts, dataset, mode, setting, held_out, feature_set, model_name, H,
            n_boot=BOOT_N):
    """Concatenate fold results into one pooled row (+ cell bootstrap CI)."""
    if not parts:
        return None
    y = np.concatenate([p[0] for p in parts])
    preds = {m: np.concatenate([p[1][m] for p in parts])
             for m in ("raw", "iso", "platt", "temp")}
    cells = np.concatenate([p[2] for p in parts])
    soh = np.concatenate([p[3] for p in parts])
    row = _row(dataset, mode, setting, held_out, feature_set, model_name, H,
               y, preds, cells, soh)
    _, lo, hi = cell_bootstrap_auc_ci(y, preds["raw"], cells, n_boot=n_boot)
    row["AUC_raw_lo"], row["AUC_raw_hi"] = lo, hi
    return row


def run_dataset(ds_name, model_name="xgboost", n_boot=BOOT_N):
    df = load_clean(ds_name)
    model = get_models()[model_name]
    cfg = DS_CONFIG[ds_name]
    rows = []
    for mode, cols in MODES.items():
        cond = condition_key(df, cols)
        df_mode = df.assign(_cond=cond)
        for feature_set in cfg["fs"]:
            features = FEATURE_SETS[feature_set]
            for H in cfg["H"]:
                parts = []
                for value, test_df in df_mode.groupby("_cond", sort=True):
                    train_df = df_mode[df_mode["_cond"] != value].reset_index(drop=True)
                    if train_df["cell"].nunique() < 2:
                        continue
                    res = fit_score(train_df, test_df.reset_index(drop=True),
                                    features, model, H)
                    if res is None:
                        continue
                    parts.append(res)
                    if mode == "temp_rate":
                        rows.append(_row(ds_name, mode, "leave_condition_out", value,
                                         feature_set, model_name, H, *res))
                pooled = _pooled(parts, ds_name, mode, "leave_condition_out_pooled",
                                 "|".join(str(v) for v in
                                          df_mode["_cond"].unique()), feature_set,
                                 model_name, H, n_boot=n_boot)
                if pooled is not None:
                    rows.append(pooled)
    # reference: ordinary cell-grouped folds, conditions mixed
    for feature_set in cfg["fs"]:
        features = FEATURE_SETS[feature_set]
        for H in cfg["H"]:
            parts = []
            gkf = GroupKFold(n_splits=5)
            dummy = np.zeros((len(df), 1))
            for tr, te in gkf.split(dummy, groups=df["cell"].to_numpy()):
                res = fit_score(df.iloc[tr].reset_index(drop=True),
                                df.iloc[te].reset_index(drop=True), features, model, H)
                if res is not None:
                    parts.append(res)
            pooled = _pooled(parts, ds_name, "mixed", "within_cells_grouped", "all",
                             feature_set, model_name, H, n_boot=n_boot)
            if pooled is not None:
                rows.append(pooled)
    return rows


def run():
    rows = []
    for ds_name in DATASETS:
        print(f"=== condition shift [{ds_name}] ===", flush=True)
        ds_rows = run_dataset(ds_name)
        rows.extend(ds_rows)
        keep = [r for r in ds_rows if r["H"] == 20
                and r["feature_set"] in ("with_soh", "no_soh")
                and r["setting"].endswith("pooled")]
        for r in keep:
            print(f"  {r['mode']:10s} leave-condition-out {r['feature_set']:8s} "
                  f"H=20: raw={r['AUC_raw']:.3f} dist_rule={r['AUC_dist_rule']:.3f} "
                  f"cells={r['n_cells']} pos={r['n_pos']}", flush=True)
    out = pd.DataFrame(rows)
    out.to_csv(results_path("condition_shift.csv"), index=False)
    print("saved results_v2/condition_shift.csv", flush=True)


if __name__ == "__main__":
    run()
