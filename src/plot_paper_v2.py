"""Paper figures for the revised study (reads results_v2/preds + CSVs).

Emits into paper_ieee_access/figs/:
  fig_collapse_map.png     Delta-AUC (with-SOH minus without-SOH) heatmap
  fig_reliability_v2.png   reliability diagrams: within CALCE + transfer Severson
  fig_prauc_horizon.png    within-dataset PR-AUC vs horizon (+ prevalence)
  fig_netbenefit.png       decision-curve analysis, ALL-LCO -> Severson, no SOH
"""
import os
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pipeline_core import load_preds
from stats_utils import reliability_curve, ece as ece_fn

_HERE = os.path.dirname(os.path.abspath(__file__))
_RES = os.path.join(_HERE, "..", "results_v2")
_FIGS = os.path.join(_HERE, "..", "paper_ieee_access", "figs")
os.makedirs(_FIGS, exist_ok=True)

plt.rcParams.update({"font.size": 9, "axes.titlesize": 10, "figure.dpi": 150})

TREE_ORDER = ["xgboost", "lightgbm", "random_forest"]
TREE_LABEL = {"xgboost": "XGBoost", "lightgbm": "LightGBM", "random_forest": "Random Forest",
              "gru": "GRU"}
SRC_LABEL = {"nasa": "NASA", "calce": "CALCE", "nasa+calce": "ALL LCO"}
TGT_LABEL = {"oxford": "Oxford", "severson": "Severson"}


def collapse_map():
    tr = pd.read_csv(os.path.join(_RES, "transfer_trees.csv"))
    gru = pd.read_csv(os.path.join(_RES, "gru_transfer.csv"))
    rows = TREE_ORDER + ["gru"]
    cols = [(s, t) for s in ["nasa", "calce", "nasa+calce"] for t in ["oxford", "severson"]]
    M = np.full((len(rows), len(cols)), np.nan)
    for i, model in enumerate(rows):
        for j, (s, t) in enumerate(cols):
            if model == "gru":
                w = gru[(gru.source == s) & (gru.target == t) &
                        (gru.feature_set == "common_with_soh") & (gru.H == 20)]["raw_AUC"].mean()
                n = gru[(gru.source == s) & (gru.target == t) &
                        (gru.feature_set == "common_no_soh") & (gru.H == 20)]["raw_AUC"].mean()
            else:
                w = tr[(tr.source == s) & (tr.target == t) & (tr.model == model) &
                       (tr.feature_set == "with_soh") & (tr.H == 20)]["raw_AUC"].mean()
                n = tr[(tr.source == s) & (tr.target == t) & (tr.model == model) &
                       (tr.feature_set == "no_soh") & (tr.H == 20)]["raw_AUC"].mean()
            if np.isfinite(w) and np.isfinite(n):
                M[i, j] = w - n
    fig, ax = plt.subplots(figsize=(7.2, 2.4))
    im = ax.imshow(M, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(range(len(cols)),
                  [f"{SRC_LABEL[s]}$\\to${TGT_LABEL[t]}" for s, t in cols], rotation=20, ha="right")
    ax.set_yticks(range(len(rows)), [TREE_LABEL[m] for m in rows])
    for i in range(len(rows)):
        for j in range(len(cols)):
            if np.isfinite(M[i, j]):
                ax.text(j, i, f"{M[i, j]:+.2f}", ha="center", va="center", fontsize=8,
                        color="white" if abs(M[i, j]) > 0.6 else "black")
    ax.set_title(r"$\Delta$AUC from removing SOH (with-SOH $-$ without-SOH), $H{=}20$")
    fig.colorbar(im, ax=ax, fraction=0.02, label=r"$\Delta$AUC")
    fig.tight_layout()
    fig.savefig(os.path.join(_FIGS, "fig_collapse_map.png"), bbox_inches="tight")
    plt.close(fig)
    print("wrote fig_collapse_map.png")


def _reliab(ax, y, p, label, color, n_bins=10):
    pts = reliability_curve(y, p, n_bins)
    xs = [a for a, _, _ in pts]
    ys = [b for _, b, _ in pts]
    ax.plot(xs, ys, "o-", ms=3, label=f"{label} (ECE {ece_fn(y, p):.3f})", color=color)
    return ax


def reliability():
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0))
    ax = axes[0]
    d = load_preds("within_calce_xgboost_H20.csv")
    y = d["y"].to_numpy()
    _reliab(ax, y, d["p_raw"].to_numpy(), "raw", "tab:gray")
    _reliab(ax, y, d["p_platt"].to_numpy(), "Platt", "tab:blue")
    _reliab(ax, y, d["p_iso"].to_numpy(), "isotonic", "tab:orange")
    _reliab(ax, y, d["p_temp"].to_numpy(), "temperature", "tab:green")
    ax.plot([0, 1], [0, 1], "k--", lw=0.7)
    ax.set_xlabel("mean predicted probability")
    ax.set_ylabel("observed failure frequency")
    ax.set_title("(a) Within CALCE, XGBoost, $H{=}20$\n(cross-fitted calibration)")
    ax.legend(fontsize=7, loc="upper left")
    ax = axes[1]
    d = load_preds("transfer_severson_nasa+calce_no_soh_xgboost_H20.csv")
    y = d["y"].to_numpy()
    _reliab(ax, y, d["p_raw"].to_numpy(), "raw", "tab:gray")
    _reliab(ax, y, d["p_platt"].to_numpy(), "Platt", "tab:blue")
    _reliab(ax, y, d["p_iso"].to_numpy(), "isotonic", "tab:orange")
    ax.plot([0, 1], [0, 1], "k--", lw=0.7)
    ax.set_xlabel("mean predicted probability")
    ax.set_ylabel("observed failure frequency")
    ax.set_title("(b) ALL LCO $\\to$ Severson, no SOH, $H{=}20$\n(calibration does not transfer)")
    ax.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    fig.savefig(os.path.join(_FIGS, "fig_reliability_v2.png"), bbox_inches="tight")
    plt.close(fig)
    print("wrote fig_reliability_v2.png")


def prauc_horizon():
    w = pd.read_csv(os.path.join(_RES, "within_trees.csv"))
    fig, ax = plt.subplots(figsize=(3.6, 2.7))
    Hs = [10, 20, 30, 50]
    for model, color in zip(TREE_ORDER, ["tab:red", "tab:blue", "tab:green"]):
        for ds, ls in [("nasa", "-"), ("calce", "--")]:
            sub = w[(w.dataset == ds) & (w.model == model) & (w.method == "raw")].sort_values("H")
            if len(sub) == 0:
                continue
            ax.plot(sub.H, sub.PRAUC, ls, marker="o", ms=3, color=color,
                    label=f"{TREE_LABEL[model]}, {'NASA' if ds=='nasa' else 'CALCE'}")
    ax.set_xlabel("horizon $H$ (cycles)")
    ax.set_ylabel("PR-AUC (raw scores)")
    ax.set_title("Within-dataset PR-AUC vs horizon")
    ax.legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(os.path.join(_FIGS, "fig_prauc_horizon.png"), bbox_inches="tight")
    plt.close(fig)
    print("wrote fig_prauc_horizon.png")


def netbenefit():
    p = os.path.join(_RES, "net_benefit_curves.csv")
    if not os.path.exists(p):
        print("skip netbenefit: no data")
        return
    d = pd.read_csv(p)
    fig, ax = plt.subplots(figsize=(3.6, 2.7))
    for method, color in [("raw", "tab:gray"), ("platt", "tab:blue"), ("iso", "tab:orange")]:
        s = d[d.method == method].sort_values("threshold")
        ax.plot(s.threshold, s.net_benefit, marker="o", ms=2.5, color=color, label=method)
    ax.axhline(0, color="k", lw=0.6, ls="--")
    ax.set_xlabel("threshold $p_t$")
    ax.set_ylabel("net benefit")
    ax.set_title("Decision curve, ALL LCO$\\to$Severson, no SOH, $H{=}20$")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(_FIGS, "fig_netbenefit.png"), bbox_inches="tight")
    plt.close(fig)
    print("wrote fig_netbenefit.png")


if __name__ == "__main__":
    import os as _os
    if _os.path.exists(os.path.join(_RES, "gru_transfer.csv")):
        collapse_map()
    else:
        print("skip collapse_map: gru_transfer.csv pending")
    reliability()
    prauc_horizon()
    netbenefit()
