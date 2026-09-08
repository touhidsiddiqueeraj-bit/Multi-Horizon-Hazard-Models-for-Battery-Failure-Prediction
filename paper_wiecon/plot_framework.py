"""Conference Fig. 1: overview of the multi-horizon failure-risk framework."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

fig, ax = plt.subplots(figsize=(3.5, 3.0))
ax.set_xlim(0, 100)
ax.set_ylim(0, 128)
ax.axis("off")
ax.set_position([0, 0, 1, 1])

BLUE = "#eef2f7"
GRAY = "#f7f7f7"


def box(cx, cy, w, h, lines, fc=BLUE, fs=6.8, bold_first=False, ec="#333333"):
    ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                                boxstyle="round,pad=0.6",
                                fc=fc, ec=ec, lw=0.9))
    for i, line in enumerate(lines):
        weight = "bold" if (bold_first and i == 0) else "normal"
        dy = (len(lines) - 1) * 3.1 / 2 - i * 3.1
        ax.text(cx, cy + dy, line, ha="center", va="center",
                fontsize=fs, fontweight=weight, linespacing=1.3)


def arrow(x0, y0, x1, y1, color="#333333", ls="-"):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>",
                                 mutation_scale=7, lw=0.9, color=color, ls=ls))


# Row 1: datasets
box(25, 112, 46, 9.5, ["LCO training cells", "NASA 18650 (37) + CALCE CX2 (7)"],
    fc=GRAY, bold_first=True)
box(75, 112, 46, 9.5, ["LFP transfer targets", "Oxford (5) + Severson (141)"],
    fc=GRAY, bold_first=True)

# Row 2: features + label
box(50, 96.5, 92, 11,
    ["per-cycle features  $x_t = \\{\\mathrm{SOH},\\ \\bar{V},\\ I,\\ T,\\ \\mathrm{dur},\\ t\\}$",
     "label: SOH $\\leq 0.80$ or voltage sag within horizon $H$"])

# warning band
ax.text(50, 96, "SOH is on both sides of the label: with-SOH results are upper bounds",
        ha="center", fontsize=6.2, color="#c0392b", style="italic")

# Row 3: models
box(25, 79, 46, 11, ["tree ensembles", "XGBoost + LightGBM + Random Forest",
                       "full | common feature set"])
box(75, 79, 46, 11, ["GRU baseline", "8 units, $w=10$ window",
                       "common features, 3 seeds"], fc=GRAY)

# Row 4: classifiers
box(50, 63.5, 92, 10.5,
    ["four independent fixed-horizon classifiers $P_{\\mathrm{fail}}(t, H)$",
     "no monotonicity $P_{10} \\leq P_{20} \\leq P_{30} \\leq P_{50}$"])

# Row 5: calibration
box(50, 49, 92, 10.5,
    ["cross-fitted calibration (leakage-free)",
     "Platt + isotonic + temperature on out-of-fold source scores"])

# Row 6: evaluation
box(25, 33, 46, 13, ["within-dataset evaluation", "cell-disjoint CV (GroupKFold / LOCO)",
                     "reliability + cell-level bootstrap", "95% CIs"], fc=GRAY)
box(75, 33, 46, 13, ["transfer evaluation", "per target cell + SOH ablation",
                     "endpoint + same-chemistry controls",
                     "DeLong test (secondary)"], fc=GRAY, bold_first=True)

# Row 7: outcome
box(50, 24, 92, 10,
    ["validity verdict",
     "apparent transfer $\\approx$ SOH shortcut, not degradation knowledge"],
    fc="#fbeeea", ec="#c0392b")

# arrows
arrow(25, 116, 25, 109.7)
arrow(75, 116, 75, 109.7)
arrow(50, 98.4, 50, 92)
arrow(25, 81.4, 38, 76.3)
arrow(75, 81.4, 62, 76.3)
arrow(25, 81.4, 50, 76.3)
arrow(50, 66.9, 50, 62.7)
arrow(50, 51.9, 50, 46.2)
arrow(30, 34.9, 30, 29.2)
arrow(70, 34.9, 70, 29.2)
# transfer path (dashed): targets feed the transfer-evaluation lane
arrow(93, 116, 93, 47.2, color="#888888", ls="--")
ax.text(95.5, 74, "transfer", fontsize=6, color="#888888", rotation=90,
        va="center", ha="center")

fig.savefig("figs/fig_framework.png", dpi=200, bbox_inches="tight",
            facecolor="white", pad_inches=0.03)
print("wrote figs/fig_framework.png")
