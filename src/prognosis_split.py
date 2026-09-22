"""Phase-1 review response: detection-vs-prognosis decomposition (no retraining).

For each saved pooled-prediction file, join the scoring rows positionally
(per cell, cycle order) to the clean frame's current-cycle SOH and report
pooled AUC on ALL rows vs rows with SOH_at_score > 0.80 (prognosis-only:
cells not already below the failure threshold when scored).

Tree preds are row-aligned to the test frame; GRU preds drop the first
WINDOW_WIDTH-1 cycles per cell (window label = last row). Alignment is
validated by matching the saved y against a recomputed label; any file
that fails validation is skipped loudly.

Output: results_v2/prognosis_split.csv
"""
import os
import sys

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from pipeline_core import load_clean, results_path, _PREDS_DIR, per_cell_aucs
from composite_label import make_composite_fail_in_H
from stats_utils import bootstrap_cis_methods, safe_auc

GRU_WINDOW = 10  # must match gru_cv.WINDOW_WIDTH
SOH_THRESH = 0.80
_done = set()  # files already processed (resume)


def load_pred(name):
    path = os.path.join(_PREDS_DIR, name)
    if not os.path.exists(path):
        return None
    return pd.read_csv(path)


def align_soh(pred, df, H, is_gru=False):
    """Current-cycle SOH per pred row; validates y against recomputed labels."""
    y_row = make_composite_fail_in_H(df.reset_index(drop=True), H)
    df = df.reset_index(drop=True)
    soh, ok_y = [], []
    for cell, g in df.groupby("cell", sort=False):
        g = g.sort_values("cycle")
        p = pred[pred.cell == cell]
        if is_gru:
            g = g.iloc[GRU_WINDOW - 1:]
        if len(p) != len(g):
            return None, f"length mismatch cell {cell}: {len(p)} vs {len(g)}"
        soh.append(g["SOH"].to_numpy())
        ok_y.append((p["y"].to_numpy() == y_row[g.index].ravel()).all())
    if not all(ok_y):
        return None, "y mismatch"
    return np.concatenate(soh), None


def metrics(y, p, cells, with_ci=True):
    if with_ci:
        n_boot = 200 if len(y) > 20000 else 1000
        cis = bootstrap_cis_methods(y, {"raw": p}, cells, methods=["raw"],
                                    n_boot=n_boot)
        auc, lo, hi = cis["raw"]
    else:
        auc, lo, hi = safe_auc(y, p), np.nan, np.nan
    pc = np.array([a for _, a in per_cell_aucs(y, p, cells)], dtype=float)
    valid = pc[np.isfinite(pc)]
    return {
        "auc": float(auc), "lo": float(lo), "hi": float(hi),
        "percell": float(valid.mean()) if len(valid) else np.nan,
        "percell_std": float(valid.std(ddof=1)) if len(valid) > 1 else np.nan,
        "n_valid": int(len(valid)), "n_rows": int(len(y)),
        "prev": float(np.mean(y)),
    }


def run_case(name, target, H, is_gru=False, score_col="p_raw", with_ci=False):
    if name in _done:
        return None  # already in rows (loaded from previous CSV)
    pred = load_pred(name)
    if pred is None:
        print(f"  SKIP missing {name}", flush=True)
        return None
    df = load_clean(target)
    # BA groups share one clean file keyed by dataset column
    if target.startswith("ba_"):
        df = df[df.dataset == target].reset_index(drop=True)
    soh, err = align_soh(pred, df, H, is_gru)
    if err is not None:
        print(f"  SKIP {name}: {err}", flush=True)
        return None
    y = pred["y"].to_numpy()
    if score_col not in pred.columns:  # schema variants: raw/iso/platt/temp
        for cand in ["raw", "p_raw"]:
            if cand in pred.columns:
                score_col = cand
                break
    p = pred[score_col].to_numpy()
    cells = pred["cell"].to_numpy()
    m_all = metrics(y, p, cells, with_ci)
    m = {"file": name, "target": target, "H": H}
    for k, v in m_all.items():
        m[f"all_{k}"] = v
    keep = soh > SOH_THRESH
    m["frac_above"] = float(keep.mean())
    if keep.sum() > 0 and len(np.unique(y[keep])) > 1:
        for k, v in metrics(y[keep], p[keep], cells[keep], with_ci).items():
            m[f"prog_{k}"] = v
    else:
        for k in ["auc", "lo", "hi", "percell", "percell_std",
                  "n_valid", "n_rows", "prev"]:
            m[f"prog_{k}"] = np.nan
    print(f"  {name}: all={m_all['auc']:.3f} "
          f"prog={m['prog_auc']:.3f} (frac_above={m['frac_above']:.2f})", flush=True)
    return m


def main():
    rows = []
    done = set()
    prev = os.path.join(os.path.dirname(results_path("x")), "prognosis_split.csv")
    if os.path.exists(prev):  # resume: skip files already processed
        done = set(pd.read_csv(prev)["file"].tolist())
        rows = pd.read_csv(prev).to_dict("records")
        print(f"resuming: {len(done)} files already done", flush=True)
    global _done
    _done = done
    trees = ["xgboost", "lightgbm", "random_forest"]
    # Severson transfer, all horizons, all LCO sources
    for src in ["nasa", "calce", "nasa+calce"]:
        for fs in ["with_soh", "no_soh"]:
            for model in trees:
                for H in [10, 20, 30, 50]:
                    r = run_case(f"transfer_severson_{src}_{fs}_{model}_H{H}.csv",
                                 "severson", H,
                                 with_ci=(src == "nasa+calce" and H == 20))
                    if r:
                        rows.append({**r, "source": src, "fs": fs, "model": model})
    # Severson GRU (common sets, H20 headline + others as present)
    for fs in ["common_with_soh", "common_no_soh"]:
        for H in [10, 20, 30, 50]:
            r = run_case(f"transfer_severson_nasa+calce_{fs}_gru_H{H}.csv",
                         "severson", H, is_gru=True)
            if r:
                rows.append({**r, "source": "nasa+calce", "fs": fs, "model": "gru"})
    # Severson distance-rule + soh-only baselines (H20)
    for base in ["soh_dist", "soh_only"]:
        r = run_case(f"transfer_severson_nasa+calce_base_{base}_H20.csv",
                     "severson", 20)
        if r:
            rows.append({**r, "source": "nasa+calce", "fs": f"base_{base}",
                         "model": "logreg"})
    # BA targets, ALL-LCO source, H20
    for tgt in ["ba_nmc_hnei", "ba_nca_snl", "ba_nmc_snl", "ba_lfp_snl"]:
        for fs in ["with_soh", "no_soh"]:
            for model in trees:
                r = run_case(f"ba_transfer_{tgt}_nasa+calce_{fs}_{model}_H20.csv",
                             tgt, 20, with_ci=True)
                if r:
                    rows.append({**r, "source": "nasa+calce", "fs": fs, "model": model})
    # Within NASA / CALCE, H20
    for ds in ["nasa", "calce"]:
        for model in trees:
            r = run_case(f"within_{ds}_{model}_H20.csv", ds, 20)
            if r:
                rows.append({**r, "source": ds, "fs": "with_soh", "model": model})
    out = pd.DataFrame(rows)
    out.to_csv(results_path("prognosis_split.csv"), index=False)
    print(f"saved prognosis_split.csv ({len(out)} rows)", flush=True)


if __name__ == "__main__":
    main()
