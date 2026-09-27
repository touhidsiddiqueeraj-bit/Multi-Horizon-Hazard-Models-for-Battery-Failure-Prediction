# Battery Archive chemistry extension — pre-registered protocol

Decisions frozen **before** any model was run on the new data. They are
implemented in `src/loader_batteryarchive.py` and `src/benchmark_cv.py`
(`within_ba` / `transfer_ba` / `ablation_tests_ba`).

Source: `batteryarchive_cycle_test_data_CSVs/` (75 cells, 218 238 cycle rows),
exported from the batteryarchive.org "Cycle Test Data" dashboard on 2026-09-21,
verified against the rendered charts and the raw API (0 mismatches).

## 1. Which cells are admitted

| Group | Chem. | Cells | Admitted | Reason for exclusion |
|---|---|---|---|---|
| HNEI 18650 NMC/LCO, 25 °C, 0-100 % | NMC | 15 | 15 | — |
| SNL 18650 NCA, 15/25/35 °C, 0-100 % | NCA | 18 | 18 | — |
| SNL 18650 NCA, 25 °C, 20-80 / 40-60 % | NCA | 6 | 0 | `soc_window_mixed` |
| SNL 18650 NMC, 15/25 °C, 0-100 % | NMC | 6 | 6 | — |
| SNL 18650 LFP, 15/25/35 °C, 0-100 % | LFP | 21 | 21 | — |
| SNL 18650 LFP, 25 °C, 20-80 / 40-60 % | LFP | 9 | 0 | `soc_window_mixed` |

The 15 SOC-windowed cells are excluded because they cycle inside a partial SOC
window while periodically running full-window reference cycles; their
capacity-based SOH is therefore not comparable across a trajectory (after
naive normalisation their late-life SOH reaches 1.2-3.9). No SOC-window claim
is made anywhere in the paper.

## 2. Cleaning rules (applied per cell, in this order)

1. **Formation/partial cycles.** Drop leading cycles whose coulombic efficiency
   departs from 1 by more than 0.25 (at most the first 10 cycles). HNEI cycle 1
   is a partial discharge (CE ≈ 0.35); without this rule *every* HNEI cell
   "fails" at cycle 1.
2. **Hampel despike on discharge capacity** (11-cycle centred window, k = 6,
   tolerance floored at 5 % of the local median) — removes check-up spikes and
   the runaway capacity tails of four HNEI cells.
3. **Sustained level-shift truncation.** Cut the trajectory at the first cycle,
   after the first quarter of the record, where the 21-cycle rolling-median SOH
   stays above its own minimum by > 0.05 while reaching > 0.10 over it. This is
   check-up/RPT contamination, not degradation.
4. **Voltage validity.** Drop rows with `voltage_min_V ≤ 0.5 V` or
   `voltage_min_V > voltage_max_V` (a handful of artefacts in the export).
5. Cells with fewer than 20 retained cycles are dropped (none of the admitted
   cells are affected).

SOH and RUL then follow the **paper's existing convention** unchanged: SOH is
the discharge capacity over the mean capacity of the first ten *retained*
cycles (Eq. 1), and RUL is the distance to the first cycle with SOH ≤ 0.80 (or
to the end of the trajectory when the cell is right-censored).

## 3. Known properties of the admitted data (reported in the paper)

- **No per-cycle current and no temperature** are exported. `avg_current` and
  `avg_temp` are therefore empty and zero-imputed downstream, exactly as CALCE
  already is. The paper's *common* feature set (`cycle`, `avg_voltage`,
  `min_voltage`, `SOH`) is fully available and is the primary setting for the
  new datasets; the full-set runs are reported only as a transparency row,
  because a constant-zero column can act as a dataset identifier.
- **Nominal chamber temperature** (15/25/35 °C) is recoverable from the cell id
  and is kept as metadata for the condition-shift control, not as a feature.
- **The voltage-sag endpoint never fires first** on any admitted cell: the
  composite label is effectively SOH-only for these groups, so `volt_only`
  results are not claimed for them.
- **SNL LFP is mostly right-censored**: 5 of 21 cells reach SOH ≤ 0.80 inside
  the released window (the rest stop near SOH 0.85-0.93), so its label
  prevalence at H = 20 is ~0.03. It is therefore run at H = 20 only, and its
  per-cell statistics are read with that censoring in mind.

## 4. Evaluation settings

- Group keys: `ba_nmc_hnei` (15), `ba_nca_snl` (18), `ba_nmc_snl` (6),
  `ba_lfp_snl` (21). Sources additionally include `nmc_all` (HNEI + SNL NMC)
  and `ba_all`; targets are Oxford, Severson and the four new groups.
- Horizons: {10, 20, 30, 50} for the three small groups, {20} for SNL LFP.
- Inner cross-fitting folds: 4 (3 for the two smallest groups).
- Cell-disjoint splits everywhere; calibrators are never fitted in-sample
  (identical protocol to the original pipeline).
- Headline ablation: with-SOH vs without-SOH, paired cell-level bootstrap, plus
  the unfitted distance-to-threshold rule `0.80 - SOH`.

## 5. Robustness check (mandatory, reported even if unfavourable)

The initial-capacity convention is the one lever that changes how many SNL LFP
cells count as failing. The alternative baseline `median(capacity, first 20
retained cycles)` is recorded per cell in `data/ba_audit.csv` (`base_med20`
next to `base10`) so the sensitivity of the censoring count can be quoted
without re-running the pipeline.
