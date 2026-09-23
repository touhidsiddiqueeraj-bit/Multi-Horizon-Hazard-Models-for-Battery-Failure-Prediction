"""Data-quality figure for the Battery Archive chemistry extension.

Emits paper_ieee_access/figs/fig_ba_quality.png (also copied to
paper_ijphm/figs/) with three panels:

  (a) cleaned SOH trajectories of the 60 admitted cells, coloured by group
      (censored cells dashed);
  (b) admitted vs excluded cells per group, with the exclusion reason;
  (c) what the cleaning removes, on one cell: raw discharge capacity with the
      formation cycle, Hampel-flagged spikes and the truncated check-up tail
      marked.

Reads data/ba_clean.csv, data/ba_audit.csv and the raw export CSVs.
"""
import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from loader_batteryarchive import (  # noqa: E402
    SRC_DIR, CAP_CSV, load_raw, clean_cell, cell_meta,
)

_BA = os.path.join(_HERE, "..", "data")
_FIG_IEE = os.path.join(_HERE, "..", "paper_ieee_access", "figs")
_FIG_IJ = os.path.join(_HERE, "..", "paper_ijphm", "figs")

plt.rcParams.update({"font.size": 9, "axes.titlesize": 9.5, "figure.dpi": 200})

GROUP_LABEL = {"ba_nmc_hnei": "HNEI NMC (15)", "ba_nca_snl": "SNL NCA (18)",
               "ba_nmc_snl": "SNL NMC (6)", "ba_lfp_snl": "SNL LFP (21)"}
GROUP_COLOR = {"ba_nmc_hnei": "#1b6ca8", "ba_nca_snl": "#c0392b",
               "ba_nmc_snl": "#e67e22", "ba_lfp_snl": "#27ae60"}
DEMO_CELL = "HNEI_18650_NMC_LCO_25C_0-100_0.5/1.5C_n"


def panel_a(ax, clean):
    for ds, sub in clean.groupby("dataset"):
        for i, (cell, g) in enumerate(sub.groupby("cell")):
            censored = g["SOH"].min() > 0.8
            ax.plot(g["cycle"], g["SOH"], lw=0.7, alpha=0.85,
                    color=GROUP_COLOR[ds], ls=":" if censored else "-",
                    label=GROUP_LABEL[ds] if i == 0 else None)
    ax.axhline(0.8, color="k", lw=0.7, ls="--")
    ax.set_xlabel("Cycle")
    ax.set_ylabel("SOH (cleaned)")
    ax.set_title("(a) admitted cells after cleaning")
    ax.set_ylim(0, 1.15)
    ax.legend(fontsize=7.5, loc="lower left", frameon=True, framealpha=0.9)
    ax.grid(alpha=0.25, lw=0.4)


def panel_b(ax, audit):
    groups = ["ba_nmc_hnei", "ba_nca_snl", "ba_nmc_snl", "ba_lfp_snl"]
    reason_label = {"": "admitted", "soc_window_mixed": "SOC-window cells"}
    admitted = [int((audit["dataset"] == g).sum()) for g in groups]
    dropped = [int(((audit["dataset"] == g) & (~audit["admitted"])).sum()) for g in groups]
    x = np.arange(len(groups))
    ax.bar(x - 0.19, admitted, 0.36, color="#2c7fb8", label="admitted")
    ax.bar(x + 0.19, dropped, 0.36, color="#d9d9d9", hatch="//",
           label="excluded (mixed SOC window)")
    for xi, (a, d) in enumerate(zip(admitted, dropped)):
        ax.text(xi - 0.19, a + 0.3, str(a), ha="center", fontsize=8)
        if d:
            ax.text(xi + 0.19, d + 0.3, str(d), ha="center", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels([GROUP_LABEL[g].split(" (")[0] for g in groups], fontsize=8)
    ax.set_ylabel("Cells")
    ax.set_title("(b) cell accounting")
    ax.legend(fontsize=7.5, frameon=False)
    ax.grid(alpha=0.25, axis="y", lw=0.4)


def panel_c(ax, raw):
    g = raw[raw["cell"] == DEMO_CELL].sort_values("cycle")
    meta = cell_meta(DEMO_CELL)
    gc, reason, _ = clean_cell(g)
    kept = set(gc["cycle"]) if gc is not None else set()
    q = g["discharge_capacity_Ah"].to_numpy(dtype=float)
    cyc = g["cycle"].to_numpy(dtype=float)
    dropped = ~np.isin(cyc, list(kept))
    ax.plot(cyc, q, lw=0.7, color="#4d4d4d", label="raw export")
    ax.plot(cyc[~dropped], q[~dropped], lw=0.7, color="#1b6ca8", label="retained")
    ax.scatter(cyc[dropped & (cyc > 5)], q[dropped & (cyc > 5)], s=2.5,
               color="#c0392b", zorder=3, label="removed (spike / check-up)")
    ax.annotate("formation cycle",
                xy=(cyc[0], q[0]), xytext=(cyc[0] + 120, min(q) * 1.6),
                fontsize=7.5, arrowprops=dict(arrowstyle="->", lw=0.5))
    ax.set_xlabel("Cycle")
    ax.set_ylabel("Discharge capacity (Ah)")
    ax.set_title(f"(c) cleaning effect: {meta['lab']} {meta['chem_label']} cell")
    top = float(np.nanmax(q[~dropped])) if (~dropped).any() else float(np.nanmax(q))
    ax.set_ylim(0, top * 1.45)
    ax.annotate("check-up tail removed\n(up to %.1f Ah)" % np.nanmax(q),
                xy=(cyc.max(), ax.get_ylim()[1] * 0.97),
                xytext=(cyc.max() * 0.45, ax.get_ylim()[1] * 0.78),
                fontsize=7.5, arrowprops=dict(arrowstyle="->", lw=0.5))
    ax.legend(fontsize=7.5, frameon=False, loc="center left")
    ax.grid(alpha=0.25, lw=0.4)


def main():
    clean = pd.read_csv(os.path.join(_BA, "ba_clean.csv"))
    audit = pd.read_csv(os.path.join(_BA, "ba_audit.csv"))
    raw = load_raw(SRC_DIR)
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.6))
    panel_a(axes[0], clean)
    panel_b(axes[1], audit)
    panel_c(axes[2], raw)
    fig.tight_layout(pad=0.6)
    out_dirs = [_FIG_IEE]
    if os.path.isdir(os.path.join(_HERE, "..", "paper_ijphm")):
        out_dirs.append(_FIG_IJ)
    for out_dir in out_dirs:
        os.makedirs(out_dir, exist_ok=True)
        fig.savefig(os.path.join(out_dir, "fig_ba_quality.png"), bbox_inches="tight")
    print(f"wrote fig_ba_quality.png to {_FIG_IEE} and {_FIG_IJ}")


if __name__ == "__main__":
    main()
