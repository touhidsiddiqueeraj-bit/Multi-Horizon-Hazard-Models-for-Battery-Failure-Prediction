"""Monotonicity analysis (review points 3 and 19).

Fixed-horizon classifiers make no guarantee that cumulative predictions
respect P10 <= P20 <= P30 <= P50. This script measures how often they
violate it, using the saved pooled predictions (row-aligned across H by
construction: deterministic splits + stable row order).

The survival-product hazard model satisfies monotonicity by construction;
its violation rate is reported as 0 for reference.
"""
import re
import numpy as np
import pandas as pd

from pipeline_core import load_preds, _PREDS_DIR, results_path
from stats_utils import monotonicity_violation_rate
import os

H_LIST = [10, 20, 30, 50]


def violations_for(pred_files_by_H):
    frames = {H: load_preds(f) for H, f in pred_files_by_H.items()}
    base = frames[H_LIST[0]]
    for H, f in frames.items():
        assert len(f) == len(base), "row count mismatch across horizons"
        assert (f["cell"].to_numpy() == base["cell"].to_numpy()).all(), \
            "cell order mismatch across horizons"
    rates = {}
    col = "p_raw"
    rates["rate"], _ = monotonicity_violation_rate(
        {H: f[col].to_numpy() for H, f in frames.items()})
    # per-model extras: platt columns exist for non-hazard models
    if "p_platt" in base.columns:
        rates["rate_platt"], _ = monotonicity_violation_rate(
            {H: f["p_platt"].to_numpy() for H, f in frames.items()})
    return rates


def collect(pattern_fn, label):
    rows = []
    for name in sorted(os.listdir(_PREDS_DIR)):
        m = pattern_fn(name)
        if not m:
            continue
        ds, model = m
        files = {}
        try:
            for H in H_LIST:
                fname = name.replace("H20", f"H{H}")
                if fname == name and H != 20:
                    continue
                if not os.path.exists(os.path.join(_PREDS_DIR, fname)):
                    break
                files[H] = fname
        except FileNotFoundError:
            continue
        if len(files) < 2:
            continue
        rates = violations_for(files)
        rows.append({"setting": label, "dataset": ds, "model": model,
                     "monotonicity_violation_rate": rates.get("rate", np.nan),
                     "monotonicity_violation_rate_platt": rates.get("rate_platt", np.nan)})
    return rows


def main():
    rows = []
    # within: within_<ds>_<model>_H{H}.csv (xgboost saved for all H; all models H20 only)
    rows += collect(
        lambda n: (lambda m: (m.group(1), m.group(2)) if m else None)(
            re.match(r"within_([a-z]+)_(xgboost)_H20\.csv$", n)),
        "within")
    rows += collect(
        lambda n: (lambda m: (m.group(1), m.group(2)))(
            re.match(r"within_([a-z]+)_gru_H20\.csv$", n)) if re.match(r"within_([a-z]+)_gru_H20\.csv$", n) else None,
        "within")
    # transfer LCO->targets: transfer_<target>_<source>_with_soh_<model>_H{H}.csv
    pat = re.compile(r"transfer_(oxford|severson)_(nasa|calce|nasa\+calce)_with_soh_([a-z_]+)_H20\.csv$")
    for name in sorted(os.listdir(_PREDS_DIR)):
        m = pat.match(name)
        if not m:
            continue
        tgt, src, model = m.groups()
        files = {}
        for H in H_LIST:
            fname = name.replace("H20", f"H{H}")
            if os.path.exists(os.path.join(_PREDS_DIR, fname)):
                files[H] = fname
        if len(files) < 2:
            continue
        rates = violations_for(files)
        rows.append({"setting": f"transfer_{src}", "dataset": tgt, "model": model,
                     "monotonicity_violation_rate": rates.get("rate", np.nan),
                     "monotonicity_violation_rate_platt": rates.get("rate_platt", np.nan)})
    # hazard model: monotone by construction; verify on saved H20 preds vs H10
    pat_h = re.compile(r"transfer_(oxford|severson)_(nasa|calce|nasa\+calce)_(hazard_xgb|hazard_logistic)_H20\.csv$")
    for name in sorted(os.listdir(_PREDS_DIR)):
        m = pat_h.match(name)
        if not m:
            continue
        tgt, src, model = m.groups()
        f10 = name.replace("H20", "H10")
        if not os.path.exists(os.path.join(_PREDS_DIR, f10)):
            continue
        d20, d10 = load_preds(name), load_preds(f10)
        rate = float(np.mean(d20["p_raw"].to_numpy() < d10["p_raw"].to_numpy() - 1e-12))
        rows.append({"setting": f"transfer_{src}", "dataset": tgt, "model": model,
                     "monotonicity_violation_rate": rate,
                     "monotonicity_violation_rate_platt": np.nan})
    df = pd.DataFrame(rows).drop_duplicates()
    df.to_csv(results_path("monotonicity.csv"), index=False)
    print(df.to_string(index=False))
    print("saved results_v2/monotonicity.csv", flush=True)


if __name__ == "__main__":
    main()
