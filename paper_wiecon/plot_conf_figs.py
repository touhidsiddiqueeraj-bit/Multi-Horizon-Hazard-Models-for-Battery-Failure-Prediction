"""Conference figures rendered at FINAL physical size (IEEE columnwidth
= 3.5 in) so fonts are true-size and readable at 100% zoom."""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_HERE = os.path.dirname(os.path.abspath(__file__))
_RES = os.path.join(_HERE, "..", "results_v2")
FIGS = os.path.join(_HERE, "figs")
CW = 3.5  # IEEE column width in inches

plt.rcParams.update({
    "font.size": 7, "axes.titlesize": 7.5, "axes.labelsize": 7,
    "xtick.labelsize": 6.5, "ytick.labelsize": 6.5, "legend.fontsize": 6,
})

trees = pd.read_csv(os.path.join(_RES, "within_trees.csv"))
gru = pd.read_csv(os.path.join(_RES, "gru_within.csv"))
transfer = pd.read_csv(os.path.join(_RES, "transfer_trees.csv"))
gru_t = pd.read_csv(os.path.join(_RES, "gru_transfer.csv"))

# ---------------------------------------------------- 1) within AUC vs H
fig, axes = plt.subplots(1, 2, figsize=(CW, 1.65), sharey=True)
for ax, ds, name in [(axes[0], "nasa", "NASA 18650"), (axes[1], "calce", "CALCE CX2")]:
    for model, color in [("xgboost", "#E24A33"), ("lightgbm", "#348ABD"),
                         ("random_forest", "#988ED5")]:
        sub = trees[(trees.dataset == ds) & (trees.model == model) &
                    (trees.method == "platt")].sort_values("H")
        ax.plot(sub.H, sub.AUC_fold_mean, marker="o", ms=3, color=color,
                label=model.replace("_", " ").title())
    sub = gru[(gru.dataset == ds) & (gru.method == "platt")].sort_values("H")
    ax.plot(sub.H, sub.AUC_fold_mean, marker="s", ms=3, color="#2ECC40",
            label="GRU", ls="--")
    ax.axhline(0.85, color="gray", ls=":", lw=0.7)
    ax.set_title(name)
    ax.set_xlabel("horizon $H$ (cycles)", labelpad=1.5)
    ax.set_xticks([10, 20, 30, 50])
    ax.set_ylim(0.82, 1.0)
axes[0].set_ylabel("fold-mean Platt AUC")
axes[0].legend(frameon=False, loc="lower left", handlelength=1.4,
               borderaxespad=0.2, labelspacing=0.25)
fig.tight_layout(pad=0.4, w_pad=1.0)
fig.savefig(os.path.join(FIGS, "fig_within_horizons.png"), dpi=300,
            bbox_inches="tight", pad_inches=0.02)
plt.close(fig)

# ---------------------------------------------------- 2) reliability diagrams
from pipeline_core import load_preds
from stats_utils import reliability_curve, ece as ece_fn

fig, axes = plt.subplots(1, 2, figsize=(CW, 1.95))
panels = [
    (axes[0], load_preds("within_calce_xgboost_H20.csv"),
     "(a) within CALCE, XGB, $H{=}20$"),
    (axes[1], load_preds("transfer_severson_nasa+calce_no_soh_xgboost_H20.csv"),
     "(b) ALL-LCO$\\to$Severson, no SOH"),
]
for ax, d, title in panels:
    y = d["y"].to_numpy()
    for col, label, color in [("p_raw", "raw", "#555555"),
                              ("p_platt", "Platt", "#1f77b4"),
                              ("p_iso", "isotonic", "#ff7f0e")]:
        pts = reliability_curve(y, d[col].to_numpy(), 10)
        ax.plot([p[0] for p in pts], [p[1] for p in pts], "o-", ms=2.5,
                lw=1.0, color=color,
                label=f"{label} (ECE {ece_fn(y, d[col].to_numpy()):.2f})")
    ax.plot([0, 1], [0, 1], "k--", lw=0.6)
    ax.set_title(title, fontsize=6.8)
    ax.set_xlabel("mean predicted $p$", labelpad=1.5)
    ax.tick_params(labelsize=6)
axes[0].set_ylabel("observed frequency")
axes[0].legend(frameon=False, fontsize=5.4, loc="upper left",
               borderaxespad=0.2, labelspacing=0.2, handlelength=1.2)
fig.tight_layout(pad=0.4, w_pad=1.2)
fig.savefig(os.path.join(FIGS, "fig_reliability_v2.png"), dpi=300,
            bbox_inches="tight", pad_inches=0.02)
plt.close(fig)

# ---------------------------------------------------- 3) collapse map
rows = ["xgboost", "lightgbm", "random_forest", "gru"]
row_labels = ["XGBoost", "LightGBM", "Random Forest", "GRU"]
cols = [(s, t) for s in ["nasa", "calce", "nasa+calce"] for t in ["oxford", "severson"]]
col_labels = [f"{a}$\\to${b}" for a, b in
              [("NASA", "Ox"), ("NASA", "Sev"), ("CALCE", "Ox"), ("CALCE", "Sev"),
               ("ALL", "Ox"), ("ALL", "Sev")]]
M = np.full((len(rows), len(cols)), np.nan)
for i, model in enumerate(rows):
    for j, (src, tgt) in enumerate(cols):
        if model == "gru":
            w = gru_t[(gru_t.source == src) & (gru_t.target == tgt) &
                      (gru_t.feature_set == "common_with_soh") & (gru_t.H == 20)]["raw_AUC"].mean()
            n = gru_t[(gru_t.source == src) & (gru_t.target == tgt) &
                      (gru_t.feature_set == "common_no_soh") & (gru_t.H == 20)]["raw_AUC"].mean()
        else:
            w = transfer[(transfer.source == src) & (transfer.target == tgt) &
                         (transfer.model == model) & (transfer.feature_set == "with_soh") &
                         (transfer.H == 20)]["raw_AUC"].mean()
            n = transfer[(transfer.source == src) & (transfer.target == tgt) &
                         (transfer.model == model) & (transfer.feature_set == "no_soh") &
                         (transfer.H == 20)]["raw_AUC"].mean()
        if np.isfinite(w) and np.isfinite(n):
            M[i, j] = w - n

fig, ax = plt.subplots(figsize=(CW, 1.85))
im = ax.imshow(M, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
ax.set_xticks(range(len(cols)), col_labels, rotation=25, ha="right", fontsize=6)
ax.set_yticks(range(len(rows)), row_labels, fontsize=6)
for i in range(len(rows)):
    for j in range(len(cols)):
        if np.isfinite(M[i, j]):
            ax.text(j, i, f"{M[i, j]:+.2f}", ha="center", va="center", fontsize=6,
                    color="white" if abs(M[i, j]) > 0.6 else "black")
cb = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.015)
cb.ax.tick_params(labelsize=6)
cb.set_label("$\\Delta$AUC", fontsize=6.5)
fig.tight_layout(pad=0.3)
fig.savefig(os.path.join(FIGS, "fig_collapse_map.png"), dpi=300,
            bbox_inches="tight", pad_inches=0.02)
plt.close(fig)
print("wrote column-size conference figures")
