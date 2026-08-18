"""Plot recalibration-cross-chemistry results (recovery experiment).

Reads results/recalibration/recalibration_reduced.csv (or RECALIBRATION_CSV) and emits:
  paper_ieee_access/figs/fig_recal_auc_vs_k.png   Fig R1 (Arm B AUC vs k)
  paper_ieee_access/figs/fig_recal_ece_vs_k.png   Fig R2 (Arm A ECE vs k)
  paper_ieee_access/figs/fig_recal_heatmap.png    Fig R3 (AUC heatmap, ceiling_type keyed)
  tables_journal/TableR1_ArmA_Recalibration.csv   ECE/Brier recovery (zero-shot vs iso/platt/temp)
  tables_journal/TableR2_ArmB_Recovery.csv        AUC + DeLong + LCO retention
Prints a summary block of headline numbers for the paper text.
"""
import os
import sys

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(REPO, "results", "recalibration")
CSV = os.environ.get("RECALIBRATION_CSV", os.path.join(RESULTS_DIR, "recalibration_reduced.csv"))
FIGDIR = os.path.join(REPO, "paper_ieee_access", "figs")
TABDIR = os.path.join(REPO, "tables_journal")

MODELS = ["xgboost", "lightgbm", "random_forest"]
MODEL_LABEL = {"xgboost": "XGBoost", "lightgbm": "LightGBM", "random_forest": "RandomForest"}
ARM_A_METHODS = ["iso", "platt", "temp"]
A_METHOD_LABEL = {"iso": "Isotonic", "platt": "Platt", "temp": "Temp-scaling"}
COLORS = {"xgboost": "#b51d0a", "lightgbm": "#0a3d62", "random_forest": "#2d6a2f"}
CEILING_LABEL = {"within_lco": "within-LCO ceiling (no-SOH)",
                 "full_lfp": "full-LFP retrain ceiling", "none": "no ceiling"}


def load():
    df = pd.read_csv(CSV)
    return df


def mean_std(x):
    x = x.dropna()
    if len(x) == 0:
        return np.nan, np.nan
    return x.mean(), x.std()


def fig_r1(df, out):
    d = df[(df.target == "severson") & (df.H == 20) & (df.features == "no_soh") & (df.arm == "arm_b")]
    ks = sorted(d.k.unique())
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.4), sharey=True)
    for source, ax in zip(["nasa", "calce", "nasa+calce"], axes):
        for model in MODELS:
            sub = d[(d.source == source) & (d.model == model)]
            means, stds = [], []
            for k in ks:
                m, s = mean_std(sub[sub.k == k].auc_pooled)
                means.append(m)
                stds.append(s)
            ax.plot(ks, means, "-o", color=COLORS[model], label=MODEL_LABEL[model])
            ax.fill_between(ks, np.array(means) - np.array(stds),
                            np.array(means) + np.array(stds),
                            color=COLORS[model], alpha=0.15)
        zero = d[(d.source == source) & (d.arm == "zeroshot")].auc_pooled.mean()
        ceil = d[(d.source == source) & (d.arm == "zeroshot")].auc_ceiling_within_lco.mean()
        full = d[(d.source == source) & (d.arm == "zeroshot")].auc_ceiling_full_lfp.mean()
        ax.axhline(zero, ls="--", color="#555", lw=1, label="zero-shot (no update)")
        if not np.isnan(ceil):
            ax.axhline(ceil, ls=":", color="#b51d0a", lw=1.2, label="within-LCO ceiling")
        if not np.isnan(full):
            ax.axhline(full, ls=":", color="#0a3d62", lw=1.2, label="full-LFP retrain")
        ax.set_title(f"source = {source}", fontsize=11)
        ax.set_xlabel("recalibration cells k")
        ax.set_xticks(ks)
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("pooled AUC (Arm B, no-SOH, H=20)")
    axes[0].legend(fontsize=8, loc="lower right")
    fig.suptitle("Cross-chemistry AUC recovery via warm-start continuation on LFP sample", fontsize=12)
    fig.tight_layout()
    fig.savefig(out, dpi=300)
    plt.close(fig)
    print(f"[Fig R1] {out}")


def fig_r2(df, out):
    d = df[(df.target == "severson") & (df.H == 20) & (df.features == "no_soh") & (df.arm == "arm_a")]
    ks = sorted(d.k.unique())
    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    for method in ARM_A_METHODS:
        sub = d[d.method == method]
        means, stds = [], []
        for k in ks:
            m, s = mean_std(sub[sub.k == k].ece)
            means.append(m)
            stds.append(s)
        ax.plot(ks, means, "-o", label=A_METHOD_LABEL[method])
        ax.fill_between(ks, np.array(means) - np.array(stds),
                        np.array(means) + np.array(stds), alpha=0.15)
    zero = df[(df.target == "severson") & (df.H == 20) & (df.features == "no_soh") & (df.arm == "zeroshot")]
    m, s = mean_std(zero.ece)
    ax.axhline(m, ls="--", color="#555", lw=1, label=f"zero-shot ECE ({m:.3f})")
    ax.set_xlabel("recalibration cells k")
    ax.set_ylabel("ECE (10-bin)")
    ax.set_xticks(ks)
    ax.set_title("Arm A: calibration-only recovery of calibration error", fontsize=11)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out, dpi=300)
    plt.close(fig)
    print(f"[Fig R2] {out}")


def fig_r3(df, out):
    d = df[(df.target == "severson") & (df.H == 20) & (df.arm == "arm_b")]
    rows = []
    for (source, model, features), g in d.groupby(["source", "model", "features"]):
        row = {"source": source, "model": model, "features": features}
        for k in sorted(g.k.unique()):
            row[k] = g[g.k == k].auc_pooled.mean()
        ct = g.auc_ceiling_within_lco.mean()
        row["ceiling_type"] = "within_lco" if not np.isnan(ct) else "full_lfp"
        rows.append(row)
    tab = pd.DataFrame(rows).sort_values(["source", "model", "features"])
    labels = [f"{r.source}\n{r.model}\n{r.features}" for _, r in tab.iterrows()]
    ks = [k for k in sorted(d.k.unique())]
    vals = tab[ks].values.astype(float)
    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    im = ax.imshow(vals, cmap="RdYlGn", vmin=0.5, vmax=1.0, aspect="auto")
    for i in range(vals.shape[0]):
        for j in range(vals.shape[1]):
            v = vals[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v:.3f}", ha="center", va="center", fontsize=8)
    ax.set_xticks(range(len(ks)))
    ax.set_xticklabels([f"k={k}" for k in ks])
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=8)
    cbar = fig.colorbar(im, ax=ax, shrink=0.85)
    cbar.set_label("pooled AUC (Arm B)")
    ax.set_title("Arm B AUC by source/model/featureset — " + CEILING_LABEL["within_lco"]
                 + " defines recovery_ratio\n(k = recalibration cells; H=20, Severson)", fontsize=10)
    fig.tight_layout()
    fig.savefig(out, dpi=300)
    plt.close(fig)
    print(f"[Fig R3] {out}")


def tables(df):
    os.makedirs(TABDIR, exist_ok=True)
    z = df[(df.target == "severson") & (df.arm == "zeroshot")]
    a = df[(df.target == "severson") & (df.arm == "arm_a")]
    b = df[(df.target == "severson") & (df.arm == "arm_b")]
    t1 = []
    for (features, model, k), g in a.groupby(["features", "model", "k"]):
        zrow = z[(z.features == features) & (z.model == model) & (z.k == k)]
        zec, zbr = zrow.ece.mean(), zrow.brier.mean()
        row = {"features": features, "model": model, "k": k, "zeroshot_ece": round(zec, 4),
               "zeroshot_brier": round(zbr, 4)}
        for method in ARM_A_METHODS:
            m = g[g.method == method]
            row[f"{method}_ece"] = round(m.ece.mean(), 4)
            row[f"{method}_brier"] = round(m.brier.mean(), 4)
            row[f"{method}_auc"] = round(m.auc_pooled.mean(), 4)
        t1.append(row)
    t2 = []
    for (features, model, k), g in b.groupby(["features", "model", "k"]):
        zrow = z[(z.features == features) & (z.model == model) & (z.k == k)]
        row = {"features": features, "model": model, "k": k,
               "zeroshot_auc": round(zrow.auc_pooled.mean(), 4),
               "within_lco_ceiling": round(zrow.auc_ceiling_within_lco.mean(), 4),
               "full_lfp_ceiling": round(zrow.auc_ceiling_full_lfp.mean(), 4),
               "arm_b_auc": round(g.auc_pooled.mean(), 4),
               "recovery_ratio": round(g.recovery_ratio.mean(), 3),
               "retrain_proximity": round(g.retrain_proximity.mean(), 3),
               "delong_p": g.delong_p_vs_zeroshot.mean(),
               "lco_ret_before": round(zrow.auc_lco_holdout_before.mean(), 4),
               "lco_ret_after": round(g.auc_lco_holdout_after.mean(), 4)}
        t2.append(row)
    p1, p2 = os.path.join(TABDIR, "TableR1_ArmA_Recalibration.csv"), os.path.join(TABDIR, "TableR2_ArmB_Recovery.csv")
    pd.DataFrame(t1).to_csv(p1, index=False)
    pd.DataFrame(t2).to_csv(p2, index=False)
    print(f"[tables] {p1}\n[tables] {p2}")


def summarize(df):
    d = df[(df.target == "severson") & (df.features == "no_soh") & (df.H == 20)]
    b = d[d.arm == "arm_b"]
    print("\n=== headline (no-SOH, H=20, Severson, seeds: %d) ===" % df.seed.nunique())
    for source in ["nasa", "calce", "nasa+calce"]:
        for model in MODELS:
            sub = b[(b.source == source) & (b.model == model)]
            if len(sub) == 0:
                continue
            k5 = sub[sub.k == 5]
            z5 = d[(d.source == source) & (d.model == model) & (d.arm == "zeroshot") & (d.k == 5)]
            print(f"{source:10s} {model:12s} k=5: zero {z5.auc_pooled.mean():.3f} "
                  f"-> armB {k5.auc_pooled.mean():.3f} ratio {k5.recovery_ratio.mean():+.2f} "
                  f"p={k5.delong_p_vs_zeroshot.mean():.3f} "
                  f"lco {z5.auc_lco_holdout_before.mean():.3f}->{k5.auc_lco_holdout_after.mean():.3f}")
    a = d[d.arm == "arm_a"]
    for method in ARM_A_METHODS:
        sub = a[a.method == method]
        k5 = sub[sub.k == 5]
        print(f"arm_a {method:9s} k=5: zero {d[d.arm=='zeroshot'].ece.mean():.3f} -> ece {k5.ece.mean():.3f} "
              f"auc {k5.auc_pooled.mean():.3f} tie_delta {k5.tie_delta_mean.max():.4f}")


def main():
    df = load()
    if df.empty:
        sys.exit("recalibration CSV empty — run recalibrate_cross_chem.py first")
    os.makedirs(FIGDIR, exist_ok=True)
    fig_r1(df, os.path.join(FIGDIR, "fig_recal_auc_vs_k.png"))
    fig_r2(df, os.path.join(FIGDIR, "fig_recal_ece_vs_k.png"))
    fig_r3(df, os.path.join(FIGDIR, "fig_recal_heatmap.png"))
    tables(df)
    summarize(df)


if __name__ == "__main__":
    main()
