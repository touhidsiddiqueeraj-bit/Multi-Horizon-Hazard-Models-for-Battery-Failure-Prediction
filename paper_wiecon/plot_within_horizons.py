"""Conference figure: within-dataset fold-mean Platt AUC vs horizon."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

_RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results_v2")
trees = pd.read_csv(os.path.join(_RES, "within_trees.csv"))
gru = pd.read_csv(os.path.join(_RES, "gru_within.csv"))

fig, axes = plt.subplots(1, 2, figsize=(6.8, 2.4), sharey=True)
for ax, ds, name in [(axes[0], "nasa", "NASA 18650"), (axes[1], "calce", "CALCE CX2")]:
    for model, color in [("xgboost", "#E24A33"), ("lightgbm", "#348ABD"),
                         ("random_forest", "#988ED5")]:
        sub = trees[(trees.dataset == ds) & (trees.model == model) &
                    (trees.method == "platt")].sort_values("H")
        ax.plot(sub.H, sub.AUC_fold_mean, marker="o", ms=3.5, color=color,
                label=model.replace("_", " ").title())
    sub = gru[(gru.dataset == ds) & (gru.method == "platt")].sort_values("H")
    ax.plot(sub.H, sub.AUC_fold_mean, marker="s", ms=3.5, color="#2ECC40",
            label="GRU", ls="--")
    ax.axhline(0.85, color="gray", ls=":", lw=0.7)
    ax.set_title(name, fontsize=9)
    ax.set_xticks([10, 20, 30, 50])
    ax.set_xlabel("horizon $H$ (cycles)", fontsize=8)
    ax.tick_params(labelsize=7.5)
    ax.set_ylim(0.82, 1.0)
axes[0].set_ylabel("fold-mean Platt AUC", fontsize=8)
axes[0].legend(fontsize=6.5, frameon=False, loc="lower left")
fig.tight_layout(pad=0.8)
fig.savefig("figs/fig_within_horizons.png", dpi=150, bbox_inches="tight")
print("wrote figs/fig_within_horizons.png")
