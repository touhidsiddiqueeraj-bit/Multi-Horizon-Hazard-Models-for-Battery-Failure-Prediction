"""E9: operational cost analysis (review point 18).

For a BMS, false negatives (missed failures) cost more than false alarms.
For each cost ratio C_FN:C_FP in {20:1, 5:1}:
  1. choose the decision threshold on SOURCE out-of-fold scores by
     minimizing expected cost (operational: the threshold must be picked
     before target data is seen);
  2. apply that threshold to the shifted target scores;
  3. report expected cost, FN rate, FP rate, and alert rate for raw,
     Platt, isotonic, and temperature-scaled scores.

Also emits net-benefit curve data (decision-curve analysis) for the
ALL-LCO -> Severson case. Source OOF scores are recomputed here via the
same cross-fitting used by the transfer pipeline.
"""
import numpy as np
import pandas as pd
from sklearn.base import clone

from pipeline_core import (get_models, load_clean, load_source,
                           fit_calibrators, apply_calibrators, cross_fitted_oof,
                           results_path, FEATURE_SETS)
from composite_label import make_composite_fail_in_H
from stats_utils import expected_cost, net_benefit
import os

SOURCE_KEY = "nasa+calce"
FPR_BUDGET = 0.10  # source-side false-alarm budget for threshold selection


def source_oof_scores(model, features, H):
    train_df = load_source(SOURCE_KEY)
    oof, y_src, _ = cross_fitted_oof(train_df, model, features, H, inner_k=5)
    return oof, y_src


def threshold_at_fpr_budget(y_src, p_src, budget=FPR_BUDGET):
    """Smallest threshold whose SOURCE false-positive rate stays within budget."""
    neg = np.asarray(p_src)[np.asarray(y_src) == 0]
    return float(np.quantile(neg, 1.0 - budget))


def run():
    models = get_models()
    rows = []
    nb_rows = []
    for target_name in ["oxford", "severson"]:
        test_df = load_clean(target_name)
        for model_name, model in models.items():
            for fs in ["with_soh", "no_soh"]:
                features = [c for c in FEATURE_SETS[fs]
                            if c in test_df.columns]
                H = 20
                oof, y_src = source_oof_scores(model, features, H)
                cal = fit_calibrators(oof, y_src)
                if cal is None:
                    continue
                m = clone(model)
                m.fit(load_source(SOURCE_KEY)[features].values, y_src)
                oof_cal = apply_calibrators(cal, oof)
                y_te = make_composite_fail_in_H(test_df, H)
                if len(np.unique(y_te)) < 2:
                    continue
                p_te = apply_calibrators(cal, m.predict_proba(test_df[features].values)[:, 1])
                for method in ["raw", "platt", "iso", "temp"]:
                    thr = threshold_at_fpr_budget(y_src, oof_cal[method])
                    pred = (p_te[method] >= thr).astype(int)
                    fn = np.sum((y_te == 1) & (pred == 0))
                    fp = np.sum((y_te == 0) & (pred == 1))
                    rows.append({
                        "target": target_name, "model": model_name, "feature_set": fs,
                        "fpr_budget": FPR_BUDGET, "method": method,
                        "thr": thr,
                        "src_fpr": np.sum((y_src == 0) & (oof_cal[method] >= thr)) / max((1 - y_src).sum(), 1),
                        "tgt_fnr": fn / max(y_te.sum(), 1),
                        "tgt_fpr": fp / max((1 - y_te).sum(), 1),
                        "alert_rate": pred.mean(),
                        "cost_20to1": expected_cost(y_te, p_te[method], thr, 20.0, 1.0),
                    })
                print(f"  {target_name} {model_name} {fs}: raw FNR="
                      f"{rows[-4]['tgt_fnr']:.3f} FPR={rows[-4]['tgt_fpr']:.3f} | "
                      f"platt FNR={rows[-3]['tgt_fnr']:.3f}", flush=True)
                # net-benefit curve data for one representative config
                if target_name == "severson" and model_name == "xgboost" and fs == "no_soh":
                    grid = np.round(np.arange(0.05, 0.96, 0.05), 2)
                    for method in ["raw", "platt", "iso"]:
                        nb = net_benefit(y_te, p_te[method], grid)
                        for t, v in zip(grid, nb):
                            nb_rows.append({"target": target_name, "model": model_name,
                                            "feature_set": fs, "method": method,
                                            "threshold": t, "net_benefit": v})
    pd.DataFrame(rows).to_csv(results_path("operational_costs.csv"), index=False)
    pd.DataFrame(nb_rows).to_csv(results_path("net_benefit_curves.csv"), index=False)
    print("saved results_v2/operational_costs.csv and net_benefit_curves.csv", flush=True)


if __name__ == "__main__":
    run()
