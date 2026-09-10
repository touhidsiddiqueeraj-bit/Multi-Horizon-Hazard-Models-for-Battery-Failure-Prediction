r"""IJPHM-specific restyles of three paper figures, written to paper_ijphm/figs/
(which \graphicspath searches before ../paper_ieee_access/figs/, so only the
IJPHM build picks these up).

Restyles requested by the author:
  fig_reliability_v2.png  legend moved below the panels, single line
  fig_prauc_horizon.png   legend moved below the axes, single line
  fig_netbenefit.png      larger in-figure text, legend below in one line
"""
import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from pipeline_core import load_preds
from stats_utils import reliability_curve

_RES = os.path.join(_HERE, "..", "results_v2")
_FIGS = os.path.join(_HERE, "..", "paper_ijphm", "figs")
os.makedirs(_FIGS, exist_ok=True)

plt.rcParams.update({
    "font.size": 10,
    "axes.titlesize": 10,
    "axes.labelsize": 9.5,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 8.5,
    "figure.dpi": 200,
})

TREE_ORDER = ["xgboost", "lightgbm", "random_forest"]
TREE_LABEL = {"xgboost": "XGBoost", "lightgbm": "LightGBM",
              "random_forest": "Random Forest"}


def _reliab(ax, y, p, color, n_bins=10):
    pts = reliability_curve(y, p, n_bins)
    xs = [a for a, _, _ in pts]
    ys = [b for _, b, _ in pts]
    ax.plot(xs, ys, "o-", ms=3.5, color=color)
    return ax


def reliability():
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.0))
    series = [("raw", "tab:gray"), ("Platt", "tab:blue"),
              ("isotonic", "tab:orange"), ("temperature", "tab:green")]

    ax = axes[0]
    d = load_preds("within_calce_xgboost_H20.csv")
    y = d["y"].to_numpy()
    _reliab(ax, y, d["p_raw"].to_numpy(), "tab:gray")
    _reliab(ax, y, d["p_platt"].to_numpy(), "tab:blue")
    _reliab(ax, y, d["p_iso"].to_numpy(), "tab:orange")
    _reliab(ax, y, d["p_temp"].to_numpy(), "tab:green")
    ax.plot([0, 1], [0, 1], "k--", lw=0.7)
    ax.set_xlabel("mean predicted probability")
    ax.set_ylabel("observed failure frequency")
    ax.set_title("(a) Within CALCE, XGBoost, $H{=}20$ (cross-fitted)")

    ax = axes[1]
    d = load_preds("transfer_severson_nasa+calce_no_soh_xgboost_H20.csv")
    y = d["y"].to_numpy()
    _reliab(ax, y, d["p_raw"].to_numpy(), "tab:gray")
    _reliab(ax, y, d["p_platt"].to_numpy(), "tab:blue")
    _reliab(ax, y, d["p_iso"].to_numpy(), "tab:orange")
    ax.plot([0, 1], [0, 1], "k--", lw=0.7)
    ax.set_xlabel("mean predicted probability")
    ax.set_ylabel("observed failure frequency")
    ax.set_title("(b) ALL LCO $\\to$ Severson, no SOH, $H{=}20$")

    handles = [Line2D([], [], color=c, marker="o", ms=4, label=n)
               for n, c in series]
    fig.legend(handles=handles, loc="lower center", ncol=4, frameon=False,
               bbox_to_anchor=(0.5, -0.005))
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(os.path.join(_FIGS, "fig_reliability_v2.png"),
                bbox_inches="tight")
    plt.close(fig)
    print("wrote fig_reliability_v2.png (IJPHM restyle)")


def prauc_horizon():
    w = pd.read_csv(os.path.join(_RES, "within_trees.csv"))
    fig, ax = plt.subplots(figsize=(3.6, 2.75))
    colors = {"xgboost": "tab:red", "lightgbm": "tab:blue",
              "random_forest": "tab:green"}
    for model in TREE_ORDER:
        for ds, ls in [("nasa", "-"), ("calce", "--")]:
            sub = w[(w.dataset == ds) & (w.model == model)
                    & (w.method == "raw")].sort_values("H")
            if len(sub) == 0:
                continue
            ax.plot(sub.H, sub.PRAUC, ls, marker="o", ms=3.5,
                    color=colors[model])
    ax.set_xlabel("horizon $H$ (cycles)")
    ax.set_ylabel("PR-AUC (raw scores)")
    handles = [Line2D([], [], color=colors[m], marker="o", ms=4,
                      label=TREE_LABEL[m]) for m in TREE_ORDER]
    handles += [Line2D([], [], color="k", ls="-", label="NASA"),
                Line2D([], [], color="k", ls="--", label="CALCE")]
    fig.legend(handles=handles, loc="lower center", ncol=5, frameon=False,
               fontsize=7.5, bbox_to_anchor=(0.5, -0.005),
               columnspacing=0.9, handletextpad=0.4)
    fig.tight_layout(rect=(0, 0.09, 1, 1))
    fig.savefig(os.path.join(_FIGS, "fig_prauc_horizon.png"),
                bbox_inches="tight")
    plt.close(fig)
    print("wrote fig_prauc_horizon.png (IJPHM restyle)")


def netbenefit():
    d = pd.read_csv(os.path.join(_RES, "net_benefit_curves.csv"))
    fig, ax = plt.subplots(figsize=(3.6, 2.75))
    for method, color, label in [("raw", "tab:gray", "raw"),
                                 ("platt", "tab:blue", "Platt"),
                                 ("iso", "tab:orange", "isotonic")]:
        s = d[d.method == method].sort_values("threshold")
        ax.plot(s.threshold, s.net_benefit, marker="o", ms=3, color=color,
                label=label)
    ax.axhline(0, color="k", lw=0.6, ls="--")
    ax.set_xlabel("threshold $p_t$")
    ax.set_ylabel("net benefit")
    handles = [Line2D([], [], color=c, marker="o", ms=4, label=l)
               for l, c in [("raw", "tab:gray"), ("Platt", "tab:blue"),
                            ("isotonic", "tab:orange")]]
    fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False,
               bbox_to_anchor=(0.5, -0.005))
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(os.path.join(_FIGS, "fig_netbenefit.png"),
                bbox_inches="tight")
    plt.close(fig)
    print("wrote fig_netbenefit.png (IJPHM restyle)")


if __name__ == "__main__":
    reliability()
    prauc_horizon()
    netbenefit()
