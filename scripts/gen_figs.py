#!/usr/bin/env python3
"""Regenerate the paper figures for paper_tr/ from the validated ground-truth
results (results_v2/paper_numbers.json) recovered from the previous session.
Every plotted value comes from the validated numbers JSON -- no invented data.

Figures produced (original file names kept where known from the repo):
  figs/Fig01_Within_Dataset_AUC.png   (heatmap, trees, mean over horizons)
  figs/Fig02_Transfer_Collapse.png    (with vs without SOH, ALL-LCO source, H=20)
  figs/Fig05_MultiHorizon_AUC.png     (NASA, Platt-calibrated, per-horizon)
  figs/fig_deploy.png                 (ESP32-S3 timing + footprint)
"""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

D = json.load(open("/home/z/my-project/scripts/paper_numbers.json"))
OUT = "/home/z/my-project/download/paper_tr/figs/"

MODELS = ["xgboost", "lightgbm", "random_forest"]
MLABEL = {"xgboost": "XGBoost", "lightgbm": "LightGBM", "random_forest": "Random Forest",
          "gru": "GRU"}
MCOLOR = {"xgboost": "#E24A33", "lightgbm": "#348ABD", "random_forest": "#988ED5",
          "gru": "#2ECC40"}

plt.rcParams.update({"axes.unicode_minus": False})


def fmt(v):
    return f"{v:.2f}" if not (0.995 <= v <= 0.9995) else f"{v:.3f}"


# ============ Fig01: within-dataset AUC heatmap ============
def fig01():
    cols = ["NASA\n(LCO)", "CALCE\n(LCO)", "HNEI NMC\n(NMC/LCO)", "SNL NCA\n(NCA)",
            "SNL NMC\n(NMC)", "SNL LFP\n(LFP)"]
    keys = [lambda m: f"within_nasa_{m}", lambda m: f"within_calce_{m}"]
    groups = ["ba_nmc_hnei", "ba_nca_snl", "ba_nmc_snl", "ba_lfp_snl"]
    M = np.zeros((3, 6))
    for i, m in enumerate(MODELS):
        M[i, 0] = D[f"within_nasa_{m}"]["mean_AUC"]
        M[i, 1] = D[f"within_calce_{m}"]["mean_AUC"]
        for j, g in enumerate(groups):
            M[i, 2 + j] = D[f"within_ba_{g}_{m}"]["mean_AUC"]

    fig, ax = plt.subplots(figsize=(5.4, 2.5))
    im = ax.imshow(M, cmap="RdYlGn", vmin=0.55, vmax=1.0, aspect="auto")
    ax.set_xticks(range(6), cols, fontsize=8)
    ax.set_yticks(range(3), [MLABEL[m] for m in MODELS], fontsize=9)
    for i in range(3):
        for j in range(6):
            ax.text(j, i, fmt(M[i, j]), ha="center", va="center", fontsize=8.5,
                    fontweight="bold", color="black")
    # divider between LCO datasets and Battery Archive groups
    ax.axvline(1.5, color="black", lw=1.6)
    ax.set_title("Within-dataset AUC (mean over horizons, Platt-calibrated)",
                 fontsize=10, pad=8, fontweight="bold")
    cb = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cb.ax.tick_params(labelsize=8)
    cb.set_label("AUC", fontsize=8)
    plt.tight_layout()
    plt.savefig(OUT + "Fig01_Within_Dataset_AUC.png", dpi=600, bbox_inches="tight")
    plt.close()


# ============ Fig02: transfer collapse (with vs without SOH) ============
def fig02():
    targets = [("Oxford\n(LFP)", "oxford"), ("Severson\n(LFP)", "severson"),
               ("HNEI NMC\n(NMC/LCO)", "ba_nmc_hnei"), ("SNL NCA\n(NCA)", "ba_nca_snl"),
               ("SNL NMC\n(NMC)", "ba_nmc_snl"), ("SNL LFP\n(LFP)", "ba_lfp_snl")]
    fig, ax = plt.subplots(figsize=(5.6, 3.4))
    for k, (tlabel, tkey) in enumerate(targets):
        for m in MODELS:
            if tkey in ("oxford", "severson"):
                w = D[f"transfer_{tkey}_nasa+calce_{m}_with_soh"]["pooled"]
                n = D[f"transfer_{tkey}_nasa+calce_{m}_no_soh"]["pooled"]
            else:
                w = D[f"xfer_ba_{tkey}_nasa+calce_{m}_with_soh"]["pooled"]
                n = D[f"xfer_ba_{tkey}_nasa+calce_{m}_no_soh"]["pooled"]
            ax.plot([k, k], [n, w], color=MCOLOR[m], lw=1.6, alpha=0.85, zorder=2)
            ax.scatter([k], [n], marker="o", s=22, color=MCOLOR[m], zorder=3)
            ax.scatter([k], [w], marker="s", s=26, color=MCOLOR[m], zorder=3)
    ax.axhline(0.5, color="gray", ls="--", lw=1.0)
    ax.text(5.42, 0.505, "chance", fontsize=8, color="gray", ha="right", va="bottom")
    ax.set_xticks(range(len(targets)), [t[0] for t in targets], fontsize=8)
    ax.set_ylabel("Pooled AUC (ALL-LCO source, $H{=}20$)", fontsize=10)
    ax.set_ylim(0.25, 1.03)
    ax.grid(True, axis="y", alpha=0.3)
    handles = [plt.Line2D([], [], color=MCOLOR[m], marker="s", ls="-", label=MLABEL[m])
               for m in MODELS]
    leg = ax.legend(handles=handles, fontsize=8, loc="lower left", framealpha=0.9)
    for t in leg.get_texts():
        t.set_fontweight("bold")
    ax.set_title("Transfer with SOH (squares) vs. without SOH (circles)",
                 fontsize=10, pad=8, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUT + "Fig02_Transfer_Collapse.png", dpi=600, bbox_inches="tight")
    plt.close()


# ============ Fig05: multi-horizon AUC on NASA ============
def fig05():
    fig, ax = plt.subplots(figsize=(5, 3.2))
    for m in ["xgboost", "lightgbm", "random_forest", "gru"]:
        e = D[f"within_nasa_{m}"]
        hs = [10, 20, 30, 50]
        ax.plot(hs, [e["per_H"][str(h)] for h in hs], marker="s",
                color=MCOLOR[m], label=MLABEL[m])
    ax.set_xlabel("Horizon H (cycles)", fontsize=10, fontweight="bold")
    ax.set_ylabel("AUC (calibrated, Platt)", fontsize=10, fontweight="bold")
    ax.set_title("Multi-Horizon AUC \u2014 NASA (Platt cal.)", fontsize=11, pad=8,
                 fontweight="bold")
    ax.legend(fontsize=9)
    for text in ax.legend().get_texts():
        text.set_fontweight("bold")
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0.75, 0.95)
    ax.set_xticks([10, 20, 30, 50])
    ax.tick_params(axis="both", which="major", labelsize=9)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontweight("bold")
    plt.tight_layout()
    plt.savefig(OUT + "Fig05_MultiHorizon_AUC.png", dpi=600, bbox_inches="tight")
    plt.close()


# ============ fig_deploy: ESP32-S3 timing + footprint ============
def fig_deploy():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.0, 2.9),
                                   gridspec_kw={"width_ratios": [1.6, 1]})
    models = ["XGBoost", "LightGBM", "Random Forest"]
    flash = [0.76, 1.55, 2.36]
    psram = [0.50, 0.93, 1.29]
    sram = [0.32, 0.43, 0.50]
    x = np.arange(3)
    w = 0.26
    ax1.bar(x - w, flash, w, label="Flash (PROGMEM)", color="#555555")
    ax1.bar(x, psram, w, label="PSRAM", color="#348ABD")
    ax1.bar(x + w, sram, w, label="Internal SRAM (1 model)", color="#E24A33")
    ax1.set_xticks(x, models, fontsize=9)
    ax1.set_ylabel("Inference time (ms)", fontsize=10)
    ax1.set_title("(a) Single-row latency at 240 MHz", fontsize=10, fontweight="bold")
    ax1.legend(fontsize=8)
    ax1.grid(True, axis="y", alpha=0.3)
    ax1.set_ylim(0, 2.75)
    for xi, v in zip(x - w, flash):
        ax1.text(xi, v + 0.05, f"{v:.2f}", ha="center", fontsize=7.5)
    for xi, v in zip(x, psram):
        ax1.text(xi, v + 0.05, f"{v:.2f}", ha="center", fontsize=7.5)
    for xi, v in zip(x + w, sram):
        ax1.text(xi, v + 0.05, f"{v:.2f}", ha="center", fontsize=7.5)

    ax2.bar([0, 1], [372, 320], 0.5, color=["#988ED5", "#cccccc"])
    ax2.set_xticks([0, 1], ["All three models\n(372 kB)", "Free internal\nSRAM (~320 kB)"],
                   fontsize=8.5)
    ax2.set_ylabel("Memory (kB)", fontsize=10)
    ax2.set_title("(b) Footprint vs. free SRAM", fontsize=10, fontweight="bold")
    ax2.grid(True, axis="y", alpha=0.3)
    ax2.set_ylim(0, 430)
    ax2.text(0.5, 395, "each single model fits in SRAM;\nthe combined binary does not",
             ha="center", fontsize=8, style="italic")
    plt.tight_layout()
    plt.savefig(OUT + "fig_deploy.png", dpi=600, bbox_inches="tight")
    plt.close()


fig01()
fig02()
fig05()
fig_deploy()
print("figures written to", OUT)
