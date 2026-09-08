# Fig 02 — Isotonic vs Platt Calibration Comparison

**File:** `figs_journal_clean/Fig02_Calibration_Comparison.png`

## Overview
2-panel line chart comparing isotonic (dashed) vs Platt (solid) calibration Brier scores across all four horizons (H=10, 20, 30, 50), for all three models.

## Description
- **Left panel:** NASA dataset
- **Right panel:** CALCE dataset
- X-axis: Horizon H (cycles)
- Y-axis: Brier score (calibrated), lower is better
- Dashed lines = isotonic, solid lines = Platt
- Colors: red = XGBoost, blue = LightGBM, purple = Random Forest

## Key Observations
1. **Platt universally beats isotonic** — every colored solid line is below its dashed counterpart.
2. **CALCE gap is dramatic** — isotonic Brier ~0.10 vs Platt ~0.07 (30% reduction). The isotonic step function overcorrects on CALCE's long-tailed SOH distribution.
3. **NASA gap is modest** — isotonic ~0.22 vs Platt ~0.20 (11% reduction). NASA's smaller per-cell cycle count produces less calibration noise.
4. Cross-chemistry no-SOH panel was removed from this figure to keep the comparison clean.

## Connection to Paper
Section 4.2 (Platt vs Isotonic Calibration). Accompanied by Table 2 (mean Brier by dataset and method).
