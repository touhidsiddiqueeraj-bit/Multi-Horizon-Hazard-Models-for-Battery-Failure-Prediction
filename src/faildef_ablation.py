"""E5: failure-definition ablation (review points 1 and 14).

Retrains with three label definitions:
  combined  SOH <= 0.80 OR voltage sag   (original protocol)
  soh_only  SOH <= 0.80 only
  volt_only voltage sag only
and measures how much of the with-SOH feature advantage survives when SOH
does NOT define the label. That difference makes the label-circularity
concern measurable. XGBoost, H=20, transfer to both LFP targets plus
within-dataset CV.
"""
import numpy as np
import pandas as pd

from pipeline_core import get_models, load_clean, results_path
from benchmark_cv import run_transfer, run_within

ENDPOINTS = ["combined", "soh_only", "volt_only"]
FEATURE_SETS_USE = ["with_soh", "no_soh"]


def run():
    model = get_models()["xgboost"]
    rows = []
    for endpoint in ENDPOINTS:
        for target_name in ["oxford", "severson"]:
            for source_key in ["nasa", "calce", "nasa+calce"]:
                for fs in FEATURE_SETS_USE:
                    res = run_transfer(source_key, target_name, model, 20, fs,
                                       endpoint=endpoint, return_pooled=True)
                    if res is None:
                        continue
                    out, pooled = res
                    out["model"] = "xgboost"
                    out["endpoint"] = endpoint
                    rows.append(out)
                    print(f"  {endpoint:9s} {source_key:10s}->{target_name:8s} {fs:8s}: "
                          f"raw={out['raw_AUC']:.3f} [{out['raw_AUC_lo']:.3f},{out['raw_AUC_hi']:.3f}]",
                          flush=True)
        for ds_name in ["nasa", "calce"]:
            df = load_clean(ds_name)
            for fs in FEATURE_SETS_USE:
                res = run_within("xgboost", model, df, 20, endpoint=endpoint, feature_set=fs)
                if res is None:
                    continue
                _, _, _, sub_rows, _ = res
                for method, r in sub_rows:
                    r["dataset"] = ds_name
                    r["endpoint"] = endpoint
                    r["feature_set"] = fs
                    r["H"] = 20
                    r["model"] = "xgboost"
                    rows.append(r)
                print(f"  {endpoint:9s} within {ds_name} {fs:8s}: raw={sub_rows[0][1]['AUC']:.3f}",
                      flush=True)
    pd.DataFrame(rows).to_csv(results_path("faildef_ablation.csv"), index=False)
    print("saved results_v2/faildef_ablation.csv", flush=True)


if __name__ == "__main__":
    run()
