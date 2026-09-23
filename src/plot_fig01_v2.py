"""Regenerate the within-dataset AUC heatmap from the v2 pipeline
(fold-mean Platt AUC, mean over horizons) so it matches Table 2."""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_HERE = os.path.dirname(os.path.abspath(__file__))
_RES = os.path.join(_HERE, "..", "results_v2")
_FIGS = os.path.join(_HERE, "..", "paper_ieee_access", "figs")

trees = pd.read_csv(os.path.join(_RES, "within_trees.csv"))
trees_ba = pd.read_csv(os.path.join(_RES, "within_trees_ba.csv"))

BA_COLS = ["ba_nmc_hnei", "ba_nca_snl", "ba_nmc_snl", "ba_lfp_snl"]
BA_LABEL = {"ba_nmc_hnei": "HNEI NMC", "ba_nca_snl": "SNL NCA",
            "ba_nmc_snl": "SNL NMC", "ba_lfp_snl": "SNL LFP"}
# Trees only: GRU and hazard models were never evaluated on the BA groups,
# so including them would fill the figure with empty cells.
rows = [("XGBoost", trees, "xgboost", "platt"),
        ("LightGBM", trees, "lightgbm", "platt"),
        ("Random Forest", trees, "random_forest", "platt")]
cols = ["nasa", "calce"] + BA_COLS
M = np.full((len(rows), len(cols)), np.nan)
for i, (label, df, model, method) in enumerate(rows):
    sub = df[(df.model == model) & (df.method == method)]
    for j, ds in enumerate(cols):
        if ds in BA_COLS:
            v = trees_ba[(trees_ba.model == model) &
                         (trees_ba.method == method) &
                         (trees_ba.dataset == ds)]["AUC_fold_mean"].mean()
        else:
            v = sub[sub.dataset == ds]["AUC_fold_mean"].mean()
        if np.isfinite(v):
            M[i, j] = v
assert np.isfinite(M).all(), f"heatmap has blank cells: {M!r}"

fig, ax = plt.subplots(figsize=(7.0, 2.2))
im = ax.imshow(M, cmap="viridis", vmin=0.8, vmax=1.0, aspect="auto")
ax.set_xticks(range(len(cols)), ["NASA 18650", "CALCE"] + [BA_LABEL[c] for c in BA_COLS],
              rotation=18, ha="right", fontsize=10)
ax.set_yticks(range(len(rows)), [r[0] for r in rows], fontsize=10)
for i in range(len(rows)):
    for j in range(len(cols)):
        ax.text(j, i, f"{M[i, j]:.3f}", ha="center", va="center", fontsize=10,
                color="white" if M[i, j] < 0.93 else "black")
ax.set_title("Fold-mean AUC, mean over horizons\n(Platt-calibrated)", fontsize=11)
fig.colorbar(im, ax=ax, fraction=0.046, label="AUC")
fig.tight_layout()
fig.savefig(os.path.join(_FIGS, "Fig01_Within_Dataset_AUC.png"), bbox_inches="tight", dpi=150)
print("wrote Fig01_Within_Dataset_AUC.png")
