# Loader notes — how this export is turned into modelling rows

Implemented in `src/loader_batteryarchive.py` (`python3 loader_batteryarchive.py`).
Decisions are pre-registered in `study_materials/batteryarchive_protocol.md`.

## Outputs

| File | Content |
|---|---|
| `data/ba_clean.csv` | 106 787 rows / 60 admitted cells, pipeline column contract (`cycle, capacity, avg_voltage, min_voltage, avg_current, avg_temp, duration, SOH, RUL, cell`) plus `dataset, lab, chem, chem_label, temp_C, window, rate` |
| `data/ba_audit.csv` | all 75 cells: admitted flag, exclusion reason, rows kept, both initial-capacity conventions (`base10`, `base_med20`), EOL cycle, first-failure cycle per endpoint, SOH range |

`avg_current` and `avg_temp` are written empty on purpose: the dashboard export
carries no per-cycle current and no temperature. The pipeline zero-imputes them,
exactly as it already does for CALCE. The nominal chamber temperature (15/25/35 °C)
is recoverable from the cell id and kept as the `temp_C` metadata column for the
condition-shift control — never as a model feature (it is constant per cell and
would act as a cell identifier).

## Admitted groups

| dataset key | Source group | Cells | Rows | Cells reaching SOH ≤ 0.80 |
|---|---|---|---|---|
| `ba_nmc_hnei` | HNEI 18650 NMC/LCO, 25 °C, 0-100 % | 15 | 15 685 | 15 |
| `ba_nca_snl` | SNL 18650 NCA, 15/25/35 °C, 0-100 % | 18 | 11 812 | 18 |
| `ba_nmc_snl` | SNL 18650 NMC, 15/25 °C, 0-100 % | 6 | 2 997 | 6 |
| `ba_lfp_snl` | SNL 18650 LFP, 15/25/35 °C, 0-100 % | 21 | 76 293 | 5 |

The 15 SOC-windowed cells (20-80 / 40-60 %) are excluded (`soc_window_mixed`):
they alternate partial-window cycling with full-window reference cycles, so
their capacity-based SOH is not comparable along a trajectory (naively
normalised late-life SOH reaches 1.2-3.9).

## Verified properties

* The voltage-sag endpoint never fires before the SOH endpoint on any admitted
  cell → the composite label is effectively SOH-only for these groups, so
  `volt_only` results are not claimed for them.
* Label prevalence at H = 20: NMC-HNEI 0.745, NCA-SNL 0.428, NMC-SNL 0.596,
  LFP-SNL 0.031 (mostly right-censored).
* Cleaning removes, per cell: the leading partial/formation cycle (HNEI cycle 1
  has coulombic efficiency ≈ 0.35, which otherwise makes all 15 HNEI cells
  "fail" at cycle 1), isolated high-capacity check-up spikes, and the runaway
  check-up tails of four HNEI cells (raw discharge capacity up to 11 Ah in a
  2.4 Ah cell).
* `data/ba_audit.csv` keeps both initial-capacity conventions so the censoring
  sensitivity of the SNL LFP group can be quoted without re-running anything.

Data courtesy of batteryarchive.org; underlying experiments by the Hawaii
Natural Energy Institute (HNEI) and Sandia National Laboratories (SNL).
