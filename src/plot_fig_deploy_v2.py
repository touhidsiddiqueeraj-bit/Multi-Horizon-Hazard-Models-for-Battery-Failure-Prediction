"""Regenerate the deployment trade-offs figure from the measured numbers in
Table (tab:deploy): (a) on-device single-row latency per memory tier,
(b) model footprint as a share of the ESP32-S3's ~320 kB free internal SRAM."""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_FIGS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "paper_ieee_access", "figs")

models = ["XGBoost", "LightGBM", "Random Forest"]
colors = ["#E24A33", "#348ABD", "#988ED5"]
flash = [0.76, 1.55, 2.36]
psram = [0.50, 0.93, 1.29]
sram = [0.32, 0.43, 0.50]
all_flash, all_psram = 4.7, 2.7
kb = [46, 98, 225]
FREE_SRAM = 320.0

fig, axes = plt.subplots(1, 2, figsize=(8.0, 3.4))
ax = axes[0]
x = np.arange(3)
w = 0.26
for k, (vals, tier) in enumerate([(flash, "flash"), (psram, "PSRAM"), (sram, "SRAM")]):
    ax.bar(x + (k - 1) * w, vals, w, label=tier,
           color=["#bbbbbb", "#666666", "#E24A33"][k])
ax.axhline(2.7, color="#348ABD", ls="--", lw=0.8)
from matplotlib.lines import Line2D
handles, labels_ = ax.get_legend_handles_labels()
handles.append(Line2D([0], [0], color="#348ABD", ls="--", lw=0.8))
labels_.append("all three, PSRAM")
ax.legend(handles, labels_, fontsize=6.5, frameon=False, loc="upper left")
ax.set_xticks(x, ["XGBoost", "LightGBM", "Rand.\nForest"], fontsize=8)
ax.set_ylabel("single-row inference (ms)", fontsize=8)
ax.set_title("(a) ESP32-S3 latency at 240 MHz", fontsize=9)
ax.legend(handles, labels_, fontsize=6.5, frameon=False, loc="upper left")
ax.tick_params(axis="y", labelsize=7)
for i in range(3):
    for k, vals in enumerate([flash, psram, sram]):
        ax.text(i + (k - 1) * w, vals[i] + 0.04, f"{vals[i]:.2f}",
                ha="center", fontsize=5.6)

ax = axes[1]
shares = [v / FREE_SRAM * 100 for v in kb] + [sum(kb) / FREE_SRAM * 100]
labels = ["XGBoost", "LightGBM", "Rand.\nForest", "All three"]
barcolors = colors + ["#888888"]
bars = ax.bar(np.arange(4), shares, 0.55, color=barcolors)
ax.axhline(100, color="black", ls="--", lw=0.9)
ax.text(-0.42, 104, "free SRAM limit (320 kB)", fontsize=6.5, va="bottom")
for i, (b, v) in enumerate(zip(bars, shares)):
    inside = v > 55
    ax.text(b.get_x() + b.get_width() / 2,
            (v - 6) if inside else (v + 3),
            f"{v:.0f}%\n({kb[i] if i < 3 else 372} kB)",
            ha="center", fontsize=6.2,
            va="top" if inside else "bottom",
            color="white" if inside else "black")
ax.set_xticks(np.arange(4), labels, fontsize=7.5)
ax.set_ylabel("share of ~320 kB free SRAM (%)", fontsize=8)
ax.set_ylim(0, 132)
ax.set_title("(b) binary footprint vs. SRAM budget", fontsize=9)
ax.tick_params(axis="y", labelsize=7)
fig.tight_layout(pad=1.4, rect=(0, 0.02, 1, 1))
fig.savefig(os.path.join(_FIGS, "fig_deploy.png"), bbox_inches="tight", dpi=150)
print("wrote fig_deploy.png")
