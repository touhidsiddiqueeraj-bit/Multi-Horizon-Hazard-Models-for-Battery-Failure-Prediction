import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

df = pd.read_csv("../data/benchmark_results.csv")

df20 = df[df["H"] == 20].copy()

pivot = df20.pivot(index="model", columns="dataset", values="AUC_cal")

model_order = ["xgboost", "lightgbm", "random_forest", "gru"]
ds_order = [c for c in ["nasa", "calce", "oxford"] if c in pivot.columns]
pivot = pivot.reindex(index=model_order, columns=ds_order)

fig, ax = plt.subplots(figsize=(7, 4))
sns.heatmap(
    pivot,
    annot=True, fmt=".3f",
    cmap="YlOrRd",
    vmin=0.75, vmax=1.0,
    linewidths=0.5,
    ax=ax,
    cbar_kws={"label": "AUC (calibrated)"}
)

ax.set_title("Cross-Dataset AUC (H=20, Calibrated)", fontsize=13, pad=12)
ax.set_xlabel("Dataset", fontsize=11)
ax.set_ylabel("Model", fontsize=11)
labels = []
for ds in ds_order:
    mapping = {"nasa": "NASA 18650", "calce": "CALCE LCO", "oxford": "Oxford LFP"}
    labels.append(mapping.get(ds, ds))
ax.set_xticklabels(labels, fontsize=10)
ax.set_yticklabels(["XGBoost", "LightGBM", "Random Forest", "GRU"], fontsize=10, rotation=0)

plt.tight_layout()
plt.savefig("../data/auc_heatmap_H20.png", dpi=150, bbox_inches="tight")
print("Saved: ../data/auc_heatmap_H20.png")

print("\nFull results summary (mean across H):")
summary = df.groupby(["model", "dataset"])[["AUC_cal", "Brier_cal"]].mean().round(3)
print(summary.to_string())
