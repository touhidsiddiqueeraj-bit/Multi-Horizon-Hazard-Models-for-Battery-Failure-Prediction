"""E4: factorial feature ablation (review point 13) -- {SOH, cycle, sensors}.

All 7 non-empty combos, XGBoost, transfer at H=20 for every source and
target, plus within-dataset CV on NASA/CALCE across all horizons.
Uses the same leakage-clean calibration and bootstrap machinery as the
main pipeline.
"""
import argparse
import numpy as np
import pandas as pd

from pipeline_core import get_models, load_clean
from benchmark_cv import run_transfer, run_within, boot_n
from stats_utils import bootstrap_cis_methods
from pipeline_core import save_preds, results_path

ABLATION_SETS = ["full", "no_soh", "no_cycle", "no_soh_no_cycle",
                 "soh_only", "cycle_only", "sensors_only"]


def cmd_transfer():
    model = get_models()["xgboost"]
    rows = []
    for target_name in ["oxford", "severson"]:
        for source_key in ["nasa", "calce", "nasa+calce"]:
            for fs in ABLATION_SETS:
                res = run_transfer(source_key, target_name, model, 20, fs, return_pooled=True)
                if res is None:
                    continue
                out, pooled = res
                out["model"] = "xgboost"
                rows.append(out)
                save_preds(f"abl20_{target_name}_{source_key}_{fs}_xgboost_H20.csv", pooled)
                print(f"  {source_key:10s}->{target_name:8s} {fs:16s}: raw={out['raw_AUC']:.3f} "
                      f"platt={out['platt_AUC']:.3f} [{out['raw_AUC_lo']:.3f},{out['raw_AUC_hi']:.3f}]",
                      flush=True)
    pd.DataFrame(rows).to_csv(results_path("feature_ablation.csv"), index=False)
    print("saved feature_ablation.csv", flush=True)


def cmd_within():
    model = get_models()["xgboost"]
    rows = []
    for ds_name in ["nasa", "calce"]:
        df = load_clean(ds_name)
        for fs in ABLATION_SETS:
            for H in [10, 20, 30, 50]:
                res = run_within("xgboost", model, df, H, feature_set=fs)
                if res is None:
                    continue
                y_all, c_all, preds, sub_rows, _ = res
                for method, r in sub_rows:
                    r["dataset"] = ds_name
                    r["feature_set"] = fs
                    r["H"] = H
                    r["model"] = "xgboost"
                    rows.append(r)
                print(f"  within {ds_name} {fs:16s} H={H}: raw={sub_rows[0][1]['AUC']:.3f}",
                      flush=True)
    pd.DataFrame(rows).to_csv(results_path("feature_ablation_within.csv"), index=False)
    print("saved feature_ablation_within.csv", flush=True)


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
