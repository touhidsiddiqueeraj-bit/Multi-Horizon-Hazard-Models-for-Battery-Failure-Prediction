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
gru = pd.read_csv(os.path.join(_RES, "gru_within.csv"))
haz = pd.read_csv(os.path.join(_RES, "hazard_within.csv"))

rows = [("XGBoost", trees, "xgboost", "platt"),
        ("LightGBM", trees, "lightgbm", "platt"),
        ("Random Forest", trees, "random_forest", "platt"),
        ("GRU", gru, None, "platt"),
        ("Hazard XGBoost", haz, "hazard_xgb", "raw"),
        ("Hazard logistic", haz, "hazard_logistic", "raw")]
cols = ["nasa", "calce"]
M = np.full((len(rows), len(cols)), np.nan)
for i, (label, df, model, method) in enumerate(rows):
    sub = df[df.method == method] if model is None else \
        df[(df.model == model) & (df.method == method)]
    for j, ds in enumerate(cols):
        v = sub[sub.dataset == ds]["AUC_fold_mean"].mean()
        if np.isfinite(v):
            M[i, j] = v
assert np.isfinite(M).all(), f"heatmap has blank cells: {M!r}"

fig, ax = plt.subplots(figsize=(3.6, 3.0))
im = ax.imshow(M, cmap="viridis", vmin=0.8, vmax=1.0, aspect="auto")
ax.set_xticks(range(len(cols)), ["NASA 18650", "CALCE"])
ax.set_yticks(range(len(rows)), [r[0] for r in rows], fontsize=8)
for i in range(len(rows)):
    for j in range(len(cols)):
        if np.isfinite(M[i, j]):
            ax.text(j, i, f"{M[i, j]:.3f}", ha="center", va="center", fontsize=8,
                    color="white" if M[i, j] < 0.93 else "black")
ax.set_title("Fold-mean AUC, mean over horizons\n(Platt-calibrated)", fontsize=9)
fig.colorbar(im, ax=ax, fraction=0.046, label="AUC")
fig.tight_layout()
fig.savefig(os.path.join(_FIGS, "Fig01_Within_Dataset_AUC.png"), bbox_inches="tight", dpi=150)
print("wrote Fig01_Within_Dataset_AUC.png")
