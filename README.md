# Multi-Horizon Failure-Risk Models for Battery Failure Prediction

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![ESP32-S3](https://img.shields.io/badge/target-ESP32--S3-E7352C.svg)](https://www.espressif.com)

Multi-horizon failure-risk classification for lithium-ion cells: instead of
remaining-useful-life regression, predict whether a cell fails within the next
H cycles. The study's central contribution is a **validity analysis** — apparent
cross-dataset, cross-chemistry transfer is largely a **State-of-Health (SOH)
shortcut**, reproducible by an unfitted threshold rule, not transferable
degradation knowledge. Plus a complete ESP32-S3 embedded deployment.

> **Status.** The deliverable paper is `paper_ieee_access/main_access.pdf`
> (IEEE Access, generated — see [Paper build](#paper-build)). A condensed
> Journal of Energy Storage submission package lives in `paper_jest/`
> (manuscript + supplement). Numbers below are headline values; every number
> in the paper is generated from `results_v2/` — see [Reproduction](#reproduction).

---

## Headline results

- **Within-dataset:** fold-mean AUC 0.90–0.96 across tree ensembles (XGBoost,
  LightGBM, Random Forest) under cell-disjoint evaluation with leakage-free
  (cross-fitted out-of-fold) calibration.
- **SOH ablation (transfer):** ALL-LCO → Severson (141 LFP cells) at H=20 —
  pooled AUC **0.896 with SOH → 0.750 without** (XGBoost); the SOH
  distance-to-threshold rule alone reaches 0.912.
- **Diagnosis vs prognosis:** the label window includes the scoring cycle, so
  with-SOH numbers mix concurrent detection with prediction. Restricting to
  rows scored while SOH > 0.80 gives **0.838** on Severson — the remainder is
  near-threshold ranking, priced by the failure-definition ablation
  (voltage-sag-only relabeling cuts with-SOH transfer 0.90 → 0.72).
- **Battery Archive replication (60 new cells, pre-registered):** with-SOH
  transfer spans 0.77–1.00 pooled AUC, collapsing to 0.36–0.91 outside the
  single-condition HNEI NMC group, where full no-SOH transfer stays ≈0.99
  (narrow stereotyped protocols transfer; diverse ones do not).
- **Calibration:** Platt preserves discrimination best at comparable error;
  isotonic fails under shift; target recalibration repairs ECE but not ranking.
- **Deployment:** three ensembles (900 trees, 26,336 nodes) in a ~372 kB flat
  binary on a $12 ESP32-S3 — under 1 ms per inference for a single
  SRAM-resident model, reproducing `predict_proba()` to within 1.1×10⁻⁶.

Because SOH enters the failure label itself, **all with-SOH transfer numbers
are diagnostic-proximity upper bounds, not pure prognosis** — stated in the
abstract, methods, results, and conclusion.

---

## Datasets

| # | Dataset | Cells | Chemistry | Cycles / rows | Notes |
|---|---------|------:|:---------:|--------------:|-------|
| 1 | NASA 18650 | 37 | LCO | 1,028 cleaned rows (~28/cell) | Randomized profiles, diverse failures |
| 2 | CALCE LCO/CX2 | 7 | LCO | ~8,700 rows | temp + duration unlogged (zero-imputed) |
| 3 | Oxford | 5 | LFP | 320 rows, ~100-cycle spacing | Labels horizon-invariant; Cell5 has 1 positive row |
| 4 | MIT–Stanford Severson | 141 | LFP | ~117k rows, 101–2,237/cell | Fast-charging protocol |
| 5 | HNEI (Battery Archive) | 15 | NMC/LCO | 15,685 rows | 25 °C, single condition, all reach EOL |
| 6 | SNL NCA (Battery Archive) | 18 | NCA | 11,812 rows | 15–35 °C, mixed C-rates |
| 7 | SNL NMC (Battery Archive) | 6 | NMC | 2,997 rows | 15–25 °C |
| 8 | SNL LFP (Battery Archive) | 21 | LFP | 76,293 rows | 15–35 °C, mostly censored (3% prevalence) |

Failure label (composite): SOH ≤ 0.80 **or** average voltage sag beyond 6%
within `[t, t+H)`, H ∈ {10, 20, 30, 50}. The window includes the scoring
cycle and the label stays 1 afterwards. Groups 5–8 come from the Battery
Archive "Cycle Test Data" export (Sept 2026; SNL matrix per Preger et
al. 2020); 60 of 75 downloaded cells admitted under a pre-registered
cleaning rule (`data/ba_audit.csv`, protocol in
`study_materials/batteryarchive_protocol.md`).

---

## Repository layout

```
├── src/                    # Research pipeline (see table below)
├── scripts/                # Paper assembly + gates (make_paper_v2, make_jest, check_overflow)
├── paper/                  # Templates (paper_v2_template_part{1,2}.tex) — EDIT THESE, not the output
├── paper_ieee_access/      # Generated main_access.tex/.pdf + figs/
├── paper_jest/             # JES submission: condensed manuscript + supplement + cover letter
├── results_v2/             # All experiment CSVs, paper_numbers.json, tex_fragments/
│   └── preds/              # Pooled prediction files (~7.5 GB, intentionally untracked)
├── data/                   # Cleaned CSVs (ba_clean.csv 19 MB, ba_audit.csv, *_clean.csv)
├── batteryarchive_cycle_test_data_CSVs/  # Raw BA export + provenance notes
├── esp32_firmware/         # ESP-IDF production firmware
├── arduino_firmware/       # Arduino firmware (web dashboard)
├── pc_validation/          # C-vs-Python validation suite
├── study_materials/        # Protocol, discrepancy note, hazard framework, primer
└── requirements.txt        # Python deps (torch installed separately, CPU or CUDA)
```

### Research modules (`src/`)

| Module | Role | Output |
|---|---|---|
| `pipeline_core.py` | Cell-disjoint splits, OOF calibration, feature sets, loaders | shared |
| `composite_label.py` | Failure labels (`combined`\|`soh_only`\|`volt_only`) | labels |
| `benchmark_cv.py` | Trees: `within` \| `transfer` \| `ablation_tests` | `*_trees.csv`, `transfer_ba.csv`, `*_ba.csv` |
| `gru_cv.py` | GRU (8-unit, 3 seeds): `within` \| `transfer` | `gru_*.csv` |
| `baselines.py` | Distance rule, SOH/cycle/sensor/full logistic regs | `baselines_*.csv` |
| `feature_ablation.py` | 2³−1 grid over {SOH, cycle, sensors} | `feature_ablation*.csv` |
| `faildef_ablation.py` | Single-endpoint relabeling | `faildef_ablation.csv` |
| `same_chem_transfer.py` | Same-chemistry cross-lab controls | `same_chem.csv` |
| `hazard_model.py` | Discrete-time survival model | `hazard_*.csv` |
| `operational_metrics.py` | 20:1 cost model, 10% FPR thresholds | `operational_costs.csv`, `net_benefit_curves.csv` |
| `monotonicity_check.py` | p₁₀≤p₂₀≤p₃₀≤p₅₀ violation rates | `monotonicity.csv` |
| `condition_shift.py` | Leave-condition-out (SNL groups) | `condition_shift.csv` |
| `prognosis_split.py` | All-rows vs SOH>0.80-at-score AUC (no retraining) | `prognosis_split.csv` |
| `loader_batteryarchive.py` + `make_tables_ba.py` | BA loading, audit, BA tables | `data/ba_*.csv`, BA fragments |
| `make_tables_v2.py` | Aggregates everything → `paper_numbers.json` + `tex_fragments/` | 552 keys, 20 fragments |
| `plot_paper_v2.py`, `plot_fig01_v2.py`, `plot_shap.py`, `plot_ba_quality.py`, `plot_fig_deploy_v2.py` | Figures → `paper_ieee_access/figs/` | PNGs |

---

## Reproduction

### Environment

```bash
pip install -r requirements.txt
# torch separately (GRU only): pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### 1. Experiments → CSVs

```bash
cd src
python3 benchmark_cv.py within && python3 benchmark_cv.py transfer
python3 benchmark_cv.py ablation_tests   # includes BA transfer/ablation
python3 gru_cv.py within && python3 gru_cv.py transfer
python3 baselines.py && python3 feature_ablation.py && python3 faildef_ablation.py
python3 same_chem_transfer.py
python3 hazard_model.py within && python3 hazard_model.py transfer
python3 operational_metrics.py && python3 monotonicity_check.py
python3 condition_shift.py && python3 prognosis_split.py
```

> ⚠️ **Two load-bearing contracts.** (1) Keep `n_jobs=1` for Random Forest
> (≤2 for boosters) — `n_jobs=4` deadlocks under nested CV. (2)
> `make_composite_fail_in_H` returns labels in the *input frame's* row order —
> `reset_index(drop=True)` frames before positional slicing.

### 2. Aggregate → assemble

```bash
cd src && python3 make_tables_v2.py        # → results_v2/paper_numbers.json + tex_fragments/
cd .. && python3 scripts/make_paper_v2.py  # fills every @@TOKEN@@ (fails loudly on gaps)
```

### 3. Compile (IEEE Access)

```bash
export TEXMFCNF=/usr/share/texmf-dist/web2c:
export TEXINPUTS=<texflow>/data/ieee//:$PWD/paper_ieee_access/figs//:/usr/share/texmf-dist/tex//:
export TEXFONTS=<texflow>/data/ieee//:/usr/share/texmf-dist/fonts//:
export FONTMAP=<texflow>/data/ieee//:
cd paper_ieee_access && pdflatex -progname=pdflatex main_access.tex  # twice
```

The `-progname` flag and `TEXMFCNF` are required (AppImage `argv[0]` breaks
kpathsea); xelatex does not work. Never hand-edit `main_access.tex` — it
regenerates on every assembly.

### 4. JES package

```bash
python3 scripts/make_jest.py --condensed   # main_condensed + supplement (.tex/.pdf)
```

### 5. Gates (must pass before commit)

```bash
python3 scripts/check_overflow.py paper_ieee_access/main_access.pdf   # CLEAN if max ≤ 0.94
python3 scripts/check_overflow.py paper_jest/main_condensed.pdf
```

Zero `pdflatex` errors, zero undefined refs/cites, no leftover `@@TOKENS@@`,
no dangling `\ref`s (check both docs after any template edit).

---

## Paper outputs

| File | What |
|---|---|
| `paper_ieee_access/main_access.pdf` | Full paper, 23pp IEEE Access (generated) |
| `paper_jest/main_condensed.pdf` | JES submission manuscript, 7 tables + 3 figs (generated) |
| `paper_jest/supplement.pdf` | 15 tables + 11 figs omitted for length (generated) |
| `paper_jest/main_jest.pdf` | Full-length elsarticle port (record only, not for submission) |
| `paper_jest/{highlights.txt,cover_letter.txt}` | Submission files (author details are placeholders) |

JES guidance is ideally ≤6,000 words / 8–10 floats; the condensed manuscript
is ~7,700 words at exactly 10 floats — disclosed in the cover letter with a
further-condensation offer. See `paper_jest/README.md`.

---

## Firmware & validation (summary)

Three tree ensembles export to one ~372 kB flat binary (`scripts/export_esp32_models.py`),
run by a hand-written C tree walker on ESP32-S3 (ESP-IDF production firmware in
`esp32_firmware/`, Arduino dashboard variant in `arduino_firmware/`).
Three validation stages (Python walker → x86 C binary → on-device) must agree
within 1e-5 (`pc_validation/`, `make validate`). Sensor wiring: INA219 +
DS3231 on I2C (GPIO8/9), DS18B20 on OneWire (GPIO10), voltage divider on ADC
GPIO1. See `esp32_firmware/` and `arduino_firmware/README.md` for build/flash
details (`run_all.sh` runs the end-to-end deployment pipeline).

> Note: the paper's prototype-wiring figure was removed (hardware unbuilt);
> on-device measurement claims in §III-M are retained as stated — verify
> against hardware before citing them externally.

---

## Methodological contracts (read before extending)

- **Cell-disjoint everything.** Train, calibration, and test never share a
  cell. Calibrators fit only on cross-fitted out-of-fold source scores.
- **Cell = experimental unit.** Headline evidence is cell-level bootstrap CIs;
  DeLong p-values are cycle-level, pseudoreplication-inflated, secondary only.
- **Oxford caveats.** 5 cells at ~100-cycle spacing → labels identical across
  horizons (pooled detection, not horizon-resolved); Cell5 has one positive row.
- **SNL LFP** is mostly censored (3% prevalence) — supporting evidence only.
- **Zero-imputation confound.** Missing current/temperature columns are
  zero-filled (CALCE + BA); a constant-zero column acts as a dataset identifier
  in pooled training — conclusions rest on the common unit-safe feature set.
- **`results_v2/preds/` (~7.5 GB) is intentionally untracked.** Do not commit
  it; the CSVs + `paper_numbers.json` reproduce every table.

---

## Citation

```bibtex
@inproceedings{siddiquee2026multi,
  title={Multi-Horizon Hazard Models for Battery Failure Prediction: Within-Dataset Reliability and Cross-Chemistry Transferability},
  author={Siddiquee, Hussain Touhid and Islam, Syeda Salsabil and Islam, Ariya Jasimul and Eshica, Chowdhury Farzana Hoque},
  year={2026}
}
```

Key data sources: NASA Ames Prognostics Repository (Saha & Goebel 2007),
CALCE (Univ. Maryland), Oxford Battery Degradation Dataset 1 (Birkl & Howey
2017), Severson et al., *Nature Energy* 2019 (+ Attia et al., *Nature* 2020),
Battery Archive "Cycle Test Data" (HNEI + SNL; SNL matrix per Preger et
al., *J. Electrochem. Soc.* 2020). Full 25-entry bibliography is in the paper.
