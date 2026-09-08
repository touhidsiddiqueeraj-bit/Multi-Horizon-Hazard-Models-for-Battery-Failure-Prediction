# WIECON-ECE 2026 conference paper (review-response revision)

Rebuilt in LaTeX (IEEEtran conference class) because the original Word
source ("IEEE_WIECON_2026_corrected_TAS version.docx") no longer exists on
disk -- only the exported PDF it produced.

## Build
    make_conference_numbers.py   # emits generated/*.tex tables from results_v2
    plot_within_horizons.py      # emits figs/fig_within_horizons.png
    pdflatex main.tex  (x3)

Requires the same TeX env as the journal paper (TEXMFCNF + -progname, see
AGENTS.md). IEEEtran.cls is bundled here.

## Content notes
All numbers come from results_v2 (leakage-clean pipeline): cross-fitted
out-of-fold calibration, leave-one-cell-out CALCE, cell-level bootstrap
CIs, DeLong demoted to secondary evidence. Review points addressed:
Failure-Risk rename (title + body), honest fixed-horizon statement
(no hazard/survival product, monotonicity not enforced, violations ~46%),
SOH label circularity + endpoint framing, Oxford horizon-invariance
caveat, dataset-shift-vs-chemistry controls, distance-to-threshold
baseline (0.912 Severson), GRU seed instability, zero-imputation and GRU
feature-confound notes.
