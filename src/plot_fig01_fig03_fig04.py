"""Generate Fig01, Fig03a/b, Fig04a/b as separate heatmaps from benchmark_results.csv

   Fig01 (within-dataset):      calibrated AUC (best method)
   Fig03a (cross-chem with SOH, Oxford): raw AUC
   Fig03b (cross-chem with SOH, Severson): raw AUC
   Fig04a (cross-chem no SOH, Oxford): raw AUC
   Fig04b (cross-chem no SOH, Severson): raw AUC
"""
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from plot_utils import build_cross_chem_pivot

df = pd.read_csv("../data/benchmark_results.csv")

model_order = ["xgboost", "lightgbm", "random_forest", "gru"]
model_labels = ["XGBoost", "LightGBM", "Random Forest", "GRU"]

# For tree cross-chem heatmaps: use platt method (has AUC_raw); GRU has no raw split
platt_df = df[df["method"] == "platt"]

heatmap_kw = dict(annot=True, fmt=".3f", cmap="YlOrRd", linewidths=0.5, cbar_kws={"label": "AUC"})

# --- Within-dataset: mean-across-H, best-method-by-Brier ---
best_by_brier = df.loc[df.groupby(["eval", "dataset", "model", "H"])["Brier_cal"].idxmin()]
within = best_by_brier[best_by_brier["eval"] == "within"]
within_mean = within.groupby(["model", "dataset"])["AUC_cal"].mean().reset_index()
p_within = within_mean.pivot(index="model", columns="dataset", values="AUC_cal").reindex(index=model_order)
p_within = p_within[[c for c in ["nasa", "calce"] if c in p_within.columns]]

fig, ax = plt.subplots(figsize=(4, 2.5))
sns.heatmap(p_within, **heatmap_kw, ax=ax)
ax.set_title("Within-Dataset AUC (mean H=10–50, best cal.)", fontsize=10, pad=8, fontweight="bold")
ax.set_xlabel(""); ax.set_ylabel("")
ax.set_xticklabels(["NASA 18650", "CALCE LCO"], fontsize=9, fontweight="bold")
ax.set_yticklabels(model_labels, fontsize=9, rotation=0, fontweight="bold")
ax.figure.axes[-1].yaxis.label.set_fontweight("bold")
plt.tight_layout()
plt.savefig("../data/Fig01_Within_Dataset_AUC.png", dpi=600, bbox_inches="tight")
print("Saved: Fig01_Within_Dataset_AUC.png")


def short_col(col):
    m = {"nasa": "N", "calce": "C", "nasa+calce": "A",
         "oxford": "Oxf", "severson": "Sev"}
    parts = col.split("\u2192")
    return m.get(parts[0], parts[0]) + "\u2192" + m.get(parts[1], parts[1])


def _split_pivot(p, target_suffix):
    """Return only columns where the target (after →) matches target_suffix."""
    cols = [c for c in p.columns if c.endswith("\u2192" + target_suffix)]
    return p[cols]


def _save_heatmap(p, title, fname, vmin=None, vmax=None):
    fig, ax = plt.subplots(figsize=(5.0, 2.5))
    kw = dict(heatmap_kw)
    if vmin is not None and vmax is not None:
        kw["vmin"] = vmin
        kw["vmax"] = vmax
    sns.heatmap(p, **kw, ax=ax)
    ax.set_title(title, fontsize=10, pad=8, fontweight="bold")
    ax.set_xlabel(""); ax.set_ylabel("")
    ax.set_xticklabels([short_col(c) for c in p.columns], fontsize=8, rotation=35, ha="right", fontweight="bold")
    ax.set_yticklabels(model_labels, fontsize=9, rotation=0, fontweight="bold")
    ax.figure.axes[-1].yaxis.label.set_fontweight("bold")
    plt.tight_layout()
    plt.savefig(fname, dpi=600, bbox_inches="tight")
    print(f"Saved: {fname}")


# ===== Fig03: Cross-chem WITH SOH =====
p_with = build_cross_chem_pivot(platt_df, "_with_soh", model_order)

p_with_oxf = _split_pivot(p_with, "oxford")
p_with_sev = _split_pivot(p_with, "severson")

_save_heatmap(p_with_oxf, "Cross-Chem LCO→LFP with SOH — Oxford\n(mean H=10–50, raw scores)",
              "../data/Fig03a_CrossChem_With_SOH_Oxford.png")
_save_heatmap(p_with_sev, "Cross-Chem LCO→LFP with SOH — Severson\n(mean H=10–50, raw scores)",
              "../data/Fig03b_CrossChem_With_SOH_Severson.png")


# ===== Fig04: Cross-chem NO SOH =====
p_no = build_cross_chem_pivot(platt_df, "_no_soh", model_order)

p_no_oxf = _split_pivot(p_no, "oxford")
p_no_sev = _split_pivot(p_no, "severson")

_save_heatmap(p_no_oxf, "Cross-Chem LCO→LFP without SOH — Oxford\n(mean H=10–50, raw scores)",
              "../data/Fig04a_CrossChem_No_SOH_Oxford.png", vmin=0.30, vmax=0.70)
_save_heatmap(p_no_sev, "Cross-Chem LCO→LFP without SOH — Severson\n(mean H=10–50, raw scores)",
              "../data/Fig04b_CrossChem_No_SOH_Severson.png", vmin=0.30, vmax=0.70)
