"""Generate Fig01, Fig03, Fig04 as separate heatmaps from benchmark_results.csv

   Fig01 (within-dataset):      calibrated AUC (best method)
   Fig03 (cross-chem with SOH): raw AUC — trees at H=20, GRU mean(H=10–50)
   Fig04 (cross-chem no SOH):   raw AUC — trees at H=20, GRU mean(H=10–50)

   Both Fig03 and Fig04 include columns for Oxford LFP and Severson LFP.
"""
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from plot_utils import build_cross_chem_pivot

df = pd.read_csv("../data/benchmark_results.csv")

model_order = ["xgboost", "lightgbm", "random_forest", "gru"]
model_labels = ["XGBoost", "LightGBM", "Random Forest", "GRU"]

raw = df.groupby(["eval", "model", "H", "dataset"], as_index=False).first()

heatmap_kw = dict(annot=True, fmt=".3f", cmap="YlOrRd", linewidths=0.5, cbar_kws={"label": "AUC"})

# --- Within-dataset ---
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

within = h20_cal[h20_cal["eval"] == "within"]
p_within = within.pivot(index="model", columns="dataset", values="AUC_cal").reindex(index=model_order)
p_within = p_within[[c for c in ["nasa", "calce"] if c in p_within.columns]]

fig, ax = plt.subplots(figsize=(4, 2.5))
sns.heatmap(p_within, **heatmap_kw, ax=ax)
ax.set_title("Within-Dataset AUC (H=20, best cal.)", fontsize=10, pad=8)
ax.set_xlabel(""); ax.set_ylabel("")
ax.set_xticklabels(["NASA 18650", "CALCE LCO"], fontsize=9)
ax.set_yticklabels(model_labels, fontsize=9, rotation=0)
plt.tight_layout()
plt.savefig("../data/Fig01_Within_Dataset_AUC.png", dpi=300, bbox_inches="tight")
print("Saved: Fig01_Within_Dataset_AUC.png")


def short_col(col):
    m = {"nasa": "N", "calce": "C", "nasa+calce": "A",
         "oxford": "Oxf", "severson": "Sev"}
    parts = col.split("\u2192")
    return m.get(parts[0], parts[0]) + "\u2192" + m.get(parts[1], parts[1])


# ===== Fig03: Cross-chem WITH SOH =====
p = build_cross_chem_pivot(raw, "_with_soh", model_order)

fig, ax = plt.subplots(figsize=(7.0, 2.5))
sns.heatmap(p, **heatmap_kw, ax=ax)
ax.set_title("Cross-Chem LCO->LFP with SOH\n(trees H=20, GRU mean H=10-50, raw scores)", fontsize=10, pad=8)
ax.set_xlabel(""); ax.set_ylabel("")
ax.set_xticklabels([short_col(c) for c in p.columns], fontsize=8, rotation=35, ha="right")
ax.set_yticklabels(model_labels, fontsize=9, rotation=0)
if "nasa+calce\u2192oxford" in p.columns:
    idx = list(p.columns).index("nasa+calce\u2192oxford")
    ax.axvline(idx + 0.5, color='white', linewidth=2)
plt.tight_layout()
plt.savefig("../data/Fig03_CrossChem_With_SOH.png", dpi=300, bbox_inches="tight")
print("Saved: Fig03_CrossChem_With_SOH.png")


# ===== Fig04: Cross-chem NO SOH =====
p = build_cross_chem_pivot(raw, "_no_soh", model_order)

fig, ax = plt.subplots(figsize=(7.0, 2.5))
sns.heatmap(p, vmin=0.30, vmax=0.70, **{k: v for k, v in heatmap_kw.items() if k != "cbar_kws"},
            cbar_kws={"label": "AUC"}, ax=ax)
ax.set_title("Cross-Chem LCO\u2192LFP without SOH\n(trees H=20, GRU mean H=10\u201350, raw scores)", fontsize=10, pad=8)
ax.set_xlabel(""); ax.set_ylabel("")
ax.set_xticklabels([short_col(c) for c in p.columns], fontsize=8, rotation=35, ha="right")
ax.set_yticklabels(model_labels, fontsize=9, rotation=0)
if "nasa+calce\u2192oxford" in p.columns:
    idx = list(p.columns).index("nasa+calce\u2192oxford")
    ax.axvline(idx + 0.5, color='white', linewidth=2)
plt.tight_layout()
plt.savefig("../data/Fig04_CrossChem_No_SOH.png", dpi=300, bbox_inches="tight")
print("Saved: Fig04_CrossChem_No_SOH.png")
