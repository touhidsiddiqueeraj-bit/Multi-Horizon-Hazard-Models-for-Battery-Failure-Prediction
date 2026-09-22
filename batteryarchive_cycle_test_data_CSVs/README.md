# Battery Archive — Cycle Test Data (CSV Export)

Source dashboard: **"Cycle Test Data"** on database.batteryarchive.org (Redash public dashboard)
URL: https://database.batteryarchive.org/public/dashboards/61PzyYn9u56njtPDOh37VVBFasGusUlxc7WZ1FSj
(org_slug=default, with the full 75-cell list and step-cycle parameters 100/1000/5000 exactly as in the original link)

Retrieved: 2026-09-21 (18:30-19:00 UTC) — via the same API endpoints the dashboard's own charts call
(`/api/queries/26,28,30,31,40/results`, authenticated with the dashboard's public token),
forcing fresh query execution (max_age=0) so the values reflect the live source.

## Scope — 75 cells

| Group | Cells | Count |
|---|---|---|
| HNEI 18650 NMC/LCO, 25C, 0-100% SOC, 0.5/1.5C | a b c d e f g j l m n o p s t | 15 |
| SNL 18650 LFP (15C / 25C / 35C; SOC windows 0-100, 20-80, 40-60; rates 0.5C-3C) | see cell_id column | 30 |
| SNL 18650 NCA (15C / 25C / 35C; SOC windows 0-100, 20-80, 40-60; rates 0.5C-2C) | see cell_id column | 24 |
| SNL 18650 NMC (15C / 25C; 0-100% SOC; 0.5C-2C) | see cell_id column | 6 |

Full cell list: see the `cell_id` column values in any CSV below.

## Files (one CSV per dashboard data category)

### 01_energy_and_capacity_decay.csv
Backs the dashboard widgets **"Cycle Index Data – Energy and Capacity Decay"** and
**"Time Series Data – Energy and Capacity Decay"** (both render this same dataset;
one with Cycle Index on x, one with Time (s) on x).
One row per cell per cycle. Columns:
- `cell_id` — cell identifier as used on batteryarchive.org
- `cycle_index` — cycle number
- `test_time_s` — seconds from start of test
- `charge_capacity_Ah` (source metric `ah_c`), `discharge_capacity_Ah` (`ah_d`)
- `charge_energy_Wh` (`e_c`), `discharge_energy_Wh` (`e_d`)

### 02_efficiencies.csv
Backs the dashboard widget **"Efficiencies"** (Energy and Coulombic Efficiencies vs Cycle Index).
- `coulombic_efficiency` (source metric `ah_eff`), `energy_efficiency` (`e_eff`) — ratios
- Note: the dashboard is configured to display missing values as 0
  (missingValuesAsZero=true); the 14 such points are left EMPTY here to stay
  faithful to the raw data (they are NaN in the source query result).

### 03_max_min_mean_voltage_by_cycle.csv
Backs the dashboard widget **"Cycle Index Data – Max and Min Voltage by Cycle"**.
- `voltage_max_V` (`v_max`), `voltage_min_V` (`v_min`)
- `charge_voltage_mean_V` (`v_c_mean`), `discharge_voltage_mean_V` (`v_d_mean`)

### 04_charge_voltage_by_step.csv
Backs the dashboard widget **"Charge voltage by step"** (Voltage vs Cycle Time).
One row per (cell, cycle, time sample), for cycles 100, 1000 and 5000 (the dashboard's parameters).
- `cycle_number` — the cycle the curve belongs to (parsed from the chart series label)
- `time_in_cycle_s` — seconds within that cycle
- `voltage_V` — measured voltage
- `source_label` — original chart series label (e.g. "SNL_18650_LFP_25C_20-80_0.5/0.5C_a 100.0")

### 05_discharge_voltage_by_step.csv
Backs the dashboard widget **"Discharge voltage by step"**. Same columns as 04.

## Data notes
- Values are exported verbatim from the source query results (full float precision,
  no rounding, no unit conversion).
- Cell `HNEI_18650_NMC_LCO_25C_0-100_0.5/1.5C_m` has no charge/discharge step-voltage
  curves at cycles 100/1000/5000 in the source, so it is absent from files 04 and 05
  (it IS present in files 01-03).
- Some efficiency values are extreme (e.g. ~1e9 when capacity approaches zero) and some
  voltage points are out of the normal range; these artifacts exist in the source data
  and are reproduced as-is.
- Raw API coverage matches the exports: q26 872,746 rows; q28 437,356; q30 13,877;
  q31 8,421; q40 874,203.

## Verification (see VERIFICATION_REPORT.txt)
1. **Rendered charts vs CSV**: all six dashboard graphs were loaded live in a browser for
   every cell group; every plotted data point (3,089,349 points total) was extracted from
   the rendered charts and compared against the CSVs — 100% exact match.
2. **CSV vs raw API**: every CSV value (673,131 rows) was compared byte-faithfully against
   the raw JSON returned by the source API — 0 mismatches.

## Attribution
Data courtesy of batteryarchive.org — a community battery testing data repository.
The underlying experiments were conducted by the Hawaii Natural Energy Institute (HNEI)
and Sandia National Laboratories (SNL). If you publish work using this data, please cite
batteryarchive.org and the original dataset sources.
