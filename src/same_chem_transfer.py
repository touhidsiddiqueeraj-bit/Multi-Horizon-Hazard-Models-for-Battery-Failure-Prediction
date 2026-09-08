"""E6: same-chemistry cross-dataset controls (review point 9).

The LCO->LFP shift changes chemistry AND laboratory/protocol/sampling
simultaneously. These controls change the dataset WITHOUT changing
chemistry:
  NASA -> CALCE      (LCO -> LCO)
  CALCE -> NASA      (LCO -> LCO)
  Severson -> Oxford (LFP -> LFP)
  Oxford -> Severson (LFP -> LFP)
If collapse-without-SOH also happens same-chemistry, the effect is
dataset shift, not chemistry-specific loss. Full and common feature sets
are both run: full features on CALCE as target exercise the zero-imputed
temperature/duration columns (dataset-identifier risk, review point 11).
XGBoost, H=20.
"""
import numpy as np
import pandas as pd

from pipeline_core import get_models, results_path
from benchmark_cv import run_transfer

PAIRS = [("nasa", "calce"), ("calce", "nasa"),
         ("severson", "oxford"), ("oxford", "severson")]
FEATURE_SETS_USE = ["with_soh", "no_soh", "common_with_soh", "common_no_soh"]


def run():
    model = get_models()["xgboost"]
    rows = []
    for src, tgt in PAIRS:
        for fs in FEATURE_SETS_USE:
            res = run_transfer(src, tgt, model, 20, fs, return_pooled=True)
            if res is None:
                print(f"  {src}->{tgt} {fs}: skipped (single-class target)", flush=True)
                continue
            out, pooled = res
            out["model"] = "xgboost"
            rows.append(out)
            print(f"  {src:8s}->{tgt:8s} {fs:16s}: raw={out['raw_AUC']:.3f} "
                  f"[{out['raw_AUC_lo']:.3f},{out['raw_AUC_hi']:.3f}] "
                  f"percell={out['raw_AUC_percell_mean']:.3f}", flush=True)
    pd.DataFrame(rows).to_csv(results_path("same_chem.csv"), index=False)
    print("saved results_v2/same_chem.csv", flush=True)


if __name__ == "__main__":
    run()
