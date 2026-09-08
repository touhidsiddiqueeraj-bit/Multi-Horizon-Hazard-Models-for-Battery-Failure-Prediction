"""Conference Fig. 1: framework overview. Rendered at final physical size
(3.45 in wide) with short labels and verified no-overlap layout."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

W, H = 100, 124          # canvas units (1 unit = 0.0345 in)
fig, ax = plt.subplots(figsize=(3.45, 3.45))
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis("off")
ax.set_position([0, 0, 1, 1])

BLUE, GRAY, RED = "#e8eef7", "#f5f5f5", "#fbeeea"


def box(cx, cy, w, h, lines, fc=BLUE, ec="#333333", fs=6.5):
    ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                                boxstyle="round,pad=0.5",
                                fc=fc, ec=ec, lw=0.9))
    n = len(lines)
    for i, line in enumerate(lines):
        dy = (n - 1) * 3.4 / 2 - i * 3.4
        ax.text(cx, cy + dy, line, ha="center", va="center",
                fontsize=fs, linespacing=1.25)


def arrow(x0, y0, x1, y1, color="#333333", ls="-"):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>",
                                 mutation_scale=7, lw=0.9, color=color, ls=ls))


# Row 1 -- datasets (y 108-120)
box(24, 117, 46, 10, ["LCO training", "NASA (37) + CALCE (7)"], fc=GRAY, fs=6.2)
box(76, 117, 46, 10, ["LFP transfer targets", "Oxford (5) + Severson (141)"],
    fc=GRAY, fs=6.2)

# Row 2 -- features + label (full width)
box(50, 99.5, 90, 15,
    ["per-cycle features and composite label",
     "SOH $\\leq$ 0.80 or voltage sag within horizon $H$",
     "SOH is on both sides of the label:",
     "with-SOH results are upper bounds"])


# Row 3 -- models (full width)
box(50, 76, 90, 10,
    ["XGBoost + LightGBM + Random Forest + GRU",
     "trees: full or common features; GRU: $w=10$, 3 seeds"], fs=6.2)

# Row 4 -- classifiers (full width)
box(50, 63.5, 90, 10,
    ["four independent fixed-horizon classifiers",
     "$P_{\\mathrm{fail}}(t, H)$, $H \\in \\{10, 20, 30, 50\\}$, no monotonicity"], fs=6.2)

# Row 5 -- calibration (full width)
box(50, 51, 90, 10,
    ["cross-fitted calibration (leakage-free)",
     "Platt / isotonic / temperature, out-of-fold source scores"], fs=6.2)

# Row 6 -- evaluation (two boxes)
box(24, 37.5, 46, 13,
    ["within-dataset evaluation", "cell-disjoint CV (LOCO)",
     "cell-level bootstrap CIs"], fc=GRAY, fs=6.2)
box(76, 37.5, 46, 13,
    ["transfer evaluation", "per target cell + SOH ablation",
     "endpoint + same-chemistry controls"], fc=GRAY, fs=6.2)

# Row 7 -- verdict (full width)
box(50, 21.5, 90, 11,
    ["validity verdict",
     "apparent transfer $\\approx$ SOH shortcut,",
     "not transferable degradation knowledge"], fc=RED, ec="#c0392b", fs=6.2)

# arrows (straight, centered, no crossings)
arrow(24, 112, 32, 107.2)
arrow(76, 112, 68, 107.2)
arrow(50, 93.5, 50, 81.2)
arrow(50, 71, 50, 68.7)
arrow(50, 58.5, 50, 56.2)
arrow(38, 46, 30, 44.2)
arrow(62, 46, 70, 44.2)
arrow(24, 31, 38, 27.3)
arrow(76, 31, 62, 27.3)

for txt in ax.texts:
    if "both sides" in txt.get_text() or "upper bounds" in txt.get_text():
        txt.set_color("#c0392b")
        txt.set_style("italic")

fig.savefig("figs/fig_framework.png", dpi=300, bbox_inches="tight",
            facecolor="white", pad_inches=0.02)
print("wrote figs/fig_framework.png")
