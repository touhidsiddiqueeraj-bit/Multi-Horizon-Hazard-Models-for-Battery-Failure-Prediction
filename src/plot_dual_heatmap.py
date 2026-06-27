"""3-panel dual heatmap: within-dataset (calibrated), cross-chem (raw AUC) with Oxford + Severson LFP."""
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from plot_utils import build_cross_chem_pivot

df = pd.read_csv("../data/benchmark_results.csv")

model_order = ["xgboost", "lightgbm", "random_forest", "gru"]
model_labels = ["XGBoost", "LightGBM", "Random Forest", "GRU"]

raw = df.groupby(["eval", "model", "H", "dataset"], as_index=False).first()

# --- Within-dataset: best calibrated method ---
best_methods = {}
for (eval_type, ds), g in df.groupby(["eval", "dataset"]):
    means = g.groupby("method")["AUC_cal"].mean()
    best_methods[(eval_type, ds)] = means.idxmax()
best_rows = []
for (eval_type, ds, method), g in df.groupby(["eval", "dataset", "method"]):
    if method == best_methods.get((eval_type, ds)):
        best_rows.append(g)
best_df = pd.concat(best_rows, ignore_index=True)
h20_cal = best_df[best_df["H"] == 20].copy()

within = h20_cal[h20_cal["eval"] == "within"].copy()
p_within = within.pivot(index="model", columns="dataset", values="AUC_cal").reindex(index=model_order)
p_within = p_within[[c for c in ["nasa", "calce"] if c in p_within.columns]]

p_cross_with = build_cross_chem_pivot(raw, "_with_soh", model_order)
p_cross_no = build_cross_chem_pivot(raw, "_no_soh", model_order)


def short_col(col):
    m = {"nasa": "N", "calce": "C", "nasa+calce": "A",
         "oxford": "Oxf", "severson": "Sev"}
    parts = col.split("\u2192")
    return m.get(parts[0], parts[0]) + "\u2192" + m.get(parts[1], parts[1])


fig, axes = plt.subplots(1, 3, figsize=(17, 3.5))

# Panel 1: Within-dataset
sns.heatmap(p_within, annot=True, fmt=".3f", cmap="YlOrRd",
            vmin=0.70, vmax=1.0, linewidths=0.5, ax=axes[0],
            cbar_kws={"label": "AUC"})
axes[0].set_title("Within-Dataset (H=20)", fontsize=11, pad=10)
axes[0].set_xlabel(""); axes[0].set_ylabel("")
ds_map = {"nasa": "NASA 18650", "calce": "CALCE LCO"}
axes[0].set_xticklabels([ds_map.get(c, c) for c in p_within.columns], fontsize=9)
axes[0].set_yticklabels(model_labels, fontsize=9, rotation=0)

# Panel 2: Cross-chem WITH SOH
sns.heatmap(p_cross_with, annot=True, fmt=".3f", cmap="YlOrRd",
            vmin=0.70, vmax=1.0, linewidths=0.5, ax=axes[1],
            cbar_kws={"label": "AUC"})
axes[1].set_title("LCO\u2192LFP with SOH\n(trees H=20, GRU mean H=10\u201350)", fontsize=11, pad=10)
axes[1].set_xlabel(""); axes[1].set_ylabel("")
axes[1].set_xticklabels([short_col(c) for c in p_cross_with.columns], fontsize=8, rotation=45, ha="right")
axes[1].set_yticklabels(model_labels, fontsize=9, rotation=0)
if "nasa+calce\u2192oxford" in p_cross_with.columns:
    idx0 = list(p_cross_with.columns).index("nasa+calce\u2192oxford")
    axes[1].axvline(idx0 + 0.5, color='white', linewidth=2)

# Panel 3: Cross-chem NO SOH
sns.heatmap(p_cross_no, annot=True, fmt=".3f", cmap="YlOrRd",
            vmin=0.30, vmax=0.70, linewidths=0.5, ax=axes[2],
            cbar_kws={"label": "AUC"})
axes[2].set_title("LCO\u2192LFP without SOH\n(trees H=20, GRU mean H=10\u201350)", fontsize=11, pad=10)
axes[2].set_xlabel(""); axes[2].set_ylabel("")
axes[2].set_xticklabels([short_col(c) for c in p_cross_no.columns], fontsize=8, rotation=45, ha="right")
axes[2].set_yticklabels(model_labels, fontsize=9, rotation=0)
if "nasa+calce\u2192oxford" in p_cross_no.columns:
    idx0 = list(p_cross_no.columns).index("nasa+calce\u2192oxford")
    axes[2].axvline(idx0 + 0.5, color='white', linewidth=2)

plt.tight_layout()
plt.savefig("../data/auc_dual_heatmap_H20.png", dpi=300, bbox_inches="tight")
print("Saved: ../data/auc_dual_heatmap_H20.png")
