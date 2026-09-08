# Multi-Horizon Hazard Models for Battery Failure Prediction

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![C](https://img.shields.io/badge/C-99-555555.svg)]()
[![ESP32-S3](https://img.shields.io/badge/target-ESP32--S3-E7352C.svg)](https://www.espressif.com)
[![PlatformIO](https://img.shields.io/badge/PlatformIO-IDE-orange.svg)](https://platformio.org)
[![Arduino](https://img.shields.io/badge/Arduino-compatible-00979D.svg)](https://arduino.cc)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Within-dataset reliability, cross-chemistry transferability, and **embedded deployment** of multi-horizon hazard models for battery failure prediction. Extends the framework of [Shikdar & Laaksonen (2026)](https://doi.org/10.1155/etep/6000810).

**Three tree ensemble models** (XGBoost, LightGBM, Random Forest — 300 trees each) trained on NASA battery data and **deployed on an ESP32-S3 microcontroller** (~$12 ESP32-S3 only, ~$25 full system). The C inference engine reproduces Python predictions with **sub-microsecond numerical precision** (maximum absolute error 1.1×10⁻⁶ across all 1028 data rows).

---

## Abstract

This project spans two tracks:

**Research track.** Evaluates whether hazard-based battery failure models trained on LCO generalize to LFP. Benchmarks four model classes (XGBoost, LightGBM, Random Forest, GRU) across four public datasets (NASA 18650, CALCE LCO/CX2, Oxford LFP, and MIT-Stanford Severson LFP). Compares isotonic vs Platt calibration under a fairness-corrected protocol.

**Deployment track.** Exports trained tree models to a compact binary format (372 KB) and deploys them on an ESP32-S3 with four sensors (voltage divider, INA219 current, DS18B20 temperature, DS3231 RTC). A C tree engine walks 900 trees (26,336 nodes), with runtime model switching via UART or web dashboard. Two firmware variants are provided: ESP-IDF (production) and Arduino (web dashboard with captive portal).

---

## Results

### Finding 1: Within-Dataset Reliability

All models achieve Platt-calibrated AUC ≥ 0.85 on 30 of 32 model–horizon–dataset combinations. The exceptions are GRU on CALCE at H=20 (0.779) and H=30 (0.768).

| Dataset | Model | Mean AUC (Platt) | Range |
|---------|-------|-----------------:|------:|
| NASA | XGBoost | 0.907 | 0.899–0.918 |
| NASA | LightGBM | 0.903 | 0.892–0.912 |
| NASA | Random Forest | 0.913 | 0.901–0.927 |
| NASA | GRU | 0.889 | 0.868–0.930 |
| CALCE | XGBoost | 0.913 | 0.899–0.926 |
| CALCE | LightGBM | 0.909 | 0.886–0.924 |
| CALCE | Random Forest | 0.883 | 0.864–0.895 |
| CALCE | GRU | 0.844 | 0.768–0.944 |

Means across all four horizons (H=10, 20, 30, 50). All within-dataset evaluation uses 5-fold GroupKFold stratified by cell — no cell leaks across folds.

### Finding 2: Platt Calibration Outperforms Isotonic

| Dataset | Mean AUC (isotonic) | Mean AUC (Platt) | Mean Brier (iso) | Mean Brier (Platt) |
|---------|-------------------:|-----------------:|-----------------:|-------------------:|
| NASA | 0.838 | 0.903 | 0.209 | 0.212 |
| CALCE | 0.713 | 0.887 | 0.107 | 0.105 |

Tree-model means across all H. The AUC gap is genuine — isotonic's step function degrades discrimination on long-tailed degradation data by collapsing scores into degenerate bins. Platt's sigmoid preserves the model's original ranking. Brier scores are comparable because both methods produce similarly calibrated probabilities on average, but isotonic achieves this at the cost of ranking quality. This is a fair comparison: both calibrators use the same underlying classifier's raw outputs, not a cross-validated ensemble.

### Finding 3: Cross-Chemistry Transfer Collapses Without SOH

**Per-cell evaluation**: models are trained on all LCO cells and evaluated independently on each test cell. Reported as **mean ± std** across cells, capturing per-cell variability. Two LFP test targets: Oxford (5 cells) and MIT-Stanford Severson (141 cells).

**Tree models at H=20 (AUC_raw, mean ± std across cells):**

| Training → Test | With SOH (model-mean range) | Without SOH (model-mean range) | Test Cells |
|-----------------|:---------------------------:|:------------------------------:|:----------:|
| NASA → Oxford | 0.959–1.000 (σ=0.02) | 0.442–0.519 (σ=0.04) | 5 |
| CALCE → Oxford | 0.763–0.837 (σ=0.04) | 0.360–0.435 (σ=0.04) | 5 |
| ALL LCO → Oxford | 0.826–0.992 (σ=0.09) | 0.316–0.608 (σ=0.15) | 5 |
| NASA → Severson | 0.992–0.999 (σ=0.00) | 0.535–0.836 (σ=0.15) | 141 |
| CALCE → Severson | 0.952–0.996 (σ=0.02) | 0.806–0.870 (σ=0.03) | 141 |
| ALL LCO → Severson | 0.993–0.996 (σ=0.00) | 0.808–0.876 (σ=0.04) | 141 |

> A σ near 0.00 indicates degenerate predictions where the model assigns nearly identical scores to all 5 Oxford cells regardless of ground truth — consistent with the SOH-as-lookup-table mechanism.

GRU cross-chemistry results are not reported in tabular form because per-horizon AUC swings span 0.011–0.986 within the same training configuration (e.g., NASA→Oxford with SOH: H=10=0.017, H=20=0.077, H=30=0.539, H=50=0.978), making point estimates unreliable. A qualitative discussion of GRU behaviour under distribution shift is provided in the paper (Section 4.4).

SOH acts as a chemistry-specific lookup key, not a transferable feature. With SOH, the model learns a chemistry-specific SOH-to-RUL mapping (e.g., "SOH=0.85 means ~50 cycles to failure" for LCO) and applies it to LFP regardless of whether the relationship holds. Without SOH, voltage/current/temperature features carry no chemistry-invariant failure signal — no tested model class achieves above-chance discrimination.

The GRU's distributed hidden state entangles SOH with voltage and cycle trends across the 10-timestep window, partially corrupting the SOH signal under distribution shift. Tree-based models exploit SOH through isolated hard splits that transfer perfectly — an architecture-specific advantage, not genuine generalization.

### Finding 4: Statistical Significance of SOH Ablation (DeLong Test)

The DeLong nonparametric test [7] compares paired AUC values for the with-SOH vs without-SOH conditions across all three tree-based models (H=20):

**ALL LCO → Oxford (5 cells):**

| Model | With-SOH AUC | Without-SOH AUC | p-value | Significant (α=0.05) |
|-------|:-----------:|:--------------:|:-------:|:--------------------:|
| XGBoost | 0.917 | 0.429 | 7.2×10⁻⁵¹ | ✅ |
| LightGBM | 0.971 | 0.332 | 2.6×10⁻⁶⁴ | ✅ |
| Random Forest | 0.989 | 0.581 | 6.5×10⁻³⁶ | ✅ |

**ALL LCO → Severson (141 cells):**

| Model | With-SOH AUC | Without-SOH AUC | p-value | Significant (α=0.05) |
|-------|:-----------:|:--------------:|:-------:|:--------------------:|
| XGBoost | 0.896 | 0.750 | <10⁻¹⁰⁰ | ✅ |
| LightGBM | 0.882 | 0.718 | <10⁻¹⁰⁰ | ✅ |
| Random Forest | 0.889 | 0.746 | <10⁻¹⁰⁰ | ✅ |

p-values span 10⁻³⁶ to far below 10⁻¹⁰⁰ — **decisive evidence** that the SOH-ablation AUC gap is not due to chance, now validated on two independent LFP test sets (5 Oxford cells + 141 Severson cells). Within-dataset model comparisons show mixed significance: XGBoost vs LightGBM reaches p=0.014 on NASA (only significant pair), while CALCE has sufficient degrees of freedom for all model pairs to reach p<10⁻⁵.

### Finding 5: Calibration Methods Fail Under Distribution Shift

Under cross-chemistry covariate shift, isotonic regression systematically collapses AUC:

| Training Config | AUC_raw → AUC_iso (loss) |
|-----------------|-------------------------:|
| NASA → Oxford with SOH | 0.959–1.000 → 0.773–0.969 (0.03–0.19 loss) |
| CALCE → Oxford with SOH | 0.763–0.837 → 0.510–0.513 (0.25–0.33 loss) |
| ALL → Oxford with SOH | 0.826–0.992 → 0.510–0.572 (0.32–0.42 loss) |

Isotonic fits a step function to the training-score distribution. Under shift, multiple test scores fall into the same bin and receive identical calibrated probabilities, creating ties that penalize AUC. This is a failure mode independent of the SOH lookup-table mechanism: even when raw scores carry transferable signal (as they do with SOH), post-hoc calibration destroys it.

### Finding 6: SHAP Comparison — With SOH vs Without SOH

Six SHAP summary plots are generated in `paper_ieee_access/figs/` (Figs. 6a–f). Figs. 6a–c (with SOH) show SOH dominating feature importance across XGBoost, LightGBM, and Random Forest for NASA→Oxford transfer at H=20. Figs. 6d–f (without SOH) show all remaining features collapsing to near-zero SHAP spread — a direct visual confirmation that no other feature carries transferable LCO→LFP signal. The contrast between Fig 6a and 6d (XGBoost), 6b and 6e (LightGBM), and 6c and 6f (Random Forest) provides an intuitive demonstration of the SOH-as-lookup-table mechanism.

### Finding 7: Few-Shot Target-Chemistry Adaptation Is Conditional

The resumable H=20 recalibration experiment uses labeled target cells, not a random percentage of individual rows. Severson uses `k={5,10,20,40}` of 141 cells (3.5%, 7.1%, 14.2%, and 28.4%); Oxford exhaustively uses `k={1,2}` of 5 cells (20% and 40%).

Arm A, calibration only, reduces Severson no-SOH ECE from 0.817 to 0.044 with isotonic and 0.045 with Platt at k=5, but can damage AUC through ties or rank reversals. Arm B, model updating, improves NASA-trained XGBoost from AUC 0.637 to 0.818 and LightGBM from 0.514 to 0.774 at k=5. The effect is source/model dependent: NASA Random Forest falls from 0.744 to 0.726 while LCO retention falls from 0.959 to 0.368. Treat target adaptation as conditional and retain a source-retention guard.

---

## Datasets

| Dataset | Cells | Chemistry | Cycles/Cell | Notes |
|---------|------:|:---------:|------------:|-------|
| NASA 18650 [4] | 37 | LCO | ~1,000 | Random-walk aging, diverse failure patterns |
| CALCE LCO/CX2 [5] | 7 | LCO | 775–1,952 | 1C/1C, ~92% failure rate; avg_temp + duration always NaN |
| Oxford LFP [6] | 5 | LFP | ~300 | Flat voltage plateau → voltage sag feature uninformative |
| MIT-Stanford (Severson) [8] | 141 | LFP | 534–2,237 | Fast-charging protocol (4C discharge), ~117K total cycles. See `data/severson/README.md` for download & processing. |

**Failure label:** composite — SOH ≤ 0.80 **or** average voltage sag < 94% of first-10-cycle baseline. The 0.94 threshold is a fixed heuristic applied uniformly across chemistries without chemistry-specific tuning.

> **Note on SOH > 1.0.** SOH is defined as current capacity ÷ mean capacity of the first 10 cycles. Due to normal early-cycle variability (batteries may take several cycles to reach peak capacity), SOH can exceed 1.0 — up to ~1.2 in NASA and ~1.1 in CALCE. These values represent healthy cells above the failure threshold and do not affect any experimental results.

---

## Models

| Model | Hyperparameters |
|-------|----------------|
| XGBoost | max_depth=4, n_estimators=300, lr=0.05, subsample=0.8, colsample_bytree=0.8, min_child_weight=5 |
| LightGBM | max_depth=4, n_estimators=300, lr=0.05, subsample=0.8, colsample_bytree=0.8, min_child_samples=20 |
| Random Forest | max_depth=6, n_estimators=300 |
| GRU | 1 layer, 8 hidden units, W=10 window, BCEWithLogits loss, Adam lr=0.005, patience=10, `torch.manual_seed(0)` |

Tree hyperparameters matched to the original Shikdar & Laaksonen study.

> ⚠️ **CALCE missing features.** avg_temp and duration are 100% NaN for CALCE, filled with 0 in preprocessing. These physically impossible values (0 °C, 0 s discharge) are constant across all CALCE rows, so tree-based models cannot exploit them as informative splits — but the zero fill acts as a dataset fingerprint that does not transfer.

---

## Calibration

Two post-hoc calibration methods compared under a **fairness-corrected protocol**:

- **Isotonic regression** — `IsotonicRegression(out_of_bounds="clip")` fit on the base model's training-set scores
- **Platt (sigmoid)** — `LogisticRegression(C=1e10, solver="lbfgs")` fit on the same base model's scores, **not** `CalibratedClassifierCV(cv=3)` which would create an unfair 3-model ensemble advantage

> **Note.** Both calibrators are fit on training-fold scores rather than a held-out calibration set. The comparison between methods is fair (same training scores), but absolute calibrated metrics may be optimistic.

---

## Cross-Chemistry Transfer Protocol

- **Training:** all LCO cells (NASA, CALCE, or both combined)
- **Testing:** each of the 5 Oxford LFP cells independently (per-cell evaluation); reported as **mean ± std** across the 5 cells
- **Ablation:** with SOH vs without SOH as a feature
- **Horizons:** H ∈ {10, 20, 30, 50} — label positive if failure within [t, t+H)
- **GRU cross-chem features:** [cycle, avg_voltage, min_voltage] without SOH; + [SOH] with SOH. Excludes avg_current (unit mismatch A vs mA), avg_temp and duration (always NaN for CALCE)
- **Statistical testing:** DeLong test [7] compares paired AUC values within each dataset and across SOH ablation, reported in tables_journal/DeLong_AUC_comparisons.csv

> ⚠️ **Oxford LFP Horizon Caveat.** The Oxford dataset is recorded at ~100-cycle intervals (5 cells, 46–78 rows each). The multi-horizon label function operates on raw cycle numbers, so H = 10, 20, 30, and 50 produce identical positive labels (76 rows, 23.8% rate). Oxford multi-horizon figures in this paper should be interpreted as single-horizon results. The core finding — cross-chemistry transfer collapses without SOH — is unaffected because all horizon variants collapse to the same binary label.

---

## ESP32-S3 Hardware Deployment

Three trained tree models (XGBoost, LightGBM, Random Forest — 300 trees each, depth 4–6) are exported to a compact binary format and deployed on an ESP32-S3. Two firmware variants are provided.

### Validation: C Engine Matches Python

| Model | Trees | Nodes | Max Error (1028 rows) | Status |
|-------|------:|------:|----------------------:|:------:|
| XGBoost | 300 | 3,242 | 1.80 × 10⁻⁷ | ✅ Pass |
| LightGBM | 300 | 7,000 | 1.25 × 10⁻⁹ | ✅ Pass |
| Random Forest | 300 | 16,064 | 2.04 × 10⁻⁹ | ✅ Pass |

The C engine reproduces the trained libraries' `predict_proba()` output with sub‑microsecond precision on every single data row. The validation pipeline compares the C tree walker directly against the original scikit-learn / xgboost / lightgbm models — not just against a Python re‑walk of the same binary.

### Binary Format (`trees.bin`, 372 KB)

All three models are packed into a single binary with per‑tree node counts for sequential walking:

```
[12-byte header] [3×4-byte offset table] [for each model: 14-byte header + for each tree: 4-byte n_nodes + n_nodes × 14-byte treenode_t]
```

Each `treenode_t` (14 bytes): `feature_idx (int16)` | `threshold (float32)` | `left_child (int16)` | `right_child (int16)` | `leaf_value (float32)`.

Total: 26,336 nodes across 900 trees ≈ 411 KB in PSRAM.

### Performance

| Model | PC (gcc -O2) | ESP32-S3 (projected) |
|-------|:------------:|:--------------------:|
| XGBoost | 7.6 μs | ~200 μs |
| LightGBM | 5.1 μs | ~150 μs |
| Random Forest | 8.1 μs | ~250 μs |
| **All 3** | **20.8 μs** | **~600 μs** |

Target inference budget: 100 ms → **~100× margin**.

### Firmware Variants

#### 1. ESP-IDF Firmware (`esp32_firmware/`)

Production‑grade C firmware using ESP-IDF v5.x and PlatformIO. Components:

| Component | Description |
|-----------|-------------|
| `tree_engine/` | Binary parser + tree walker + sigmoid/avg output transforms |
| `sensors/` | Voltage divider (ADC), INA219 (I2C), DS18B20 (RMT), DS3231 (I2C), SOH calibrator |
| `feature_extractor/` | Extracts 7 features from cycle data |
| `main/main.c` | State machine (INIT → CALIBRATE → MONITOR), UART protocol |

**Build:**
```bash
cd esp32_firmware && pio run -t upload
```

**UART protocol:**
```
MODEL 0|1|2     → Switch model (XGBoost/LightGBM/RF)
STATUS          → Report state, cycle, active model
P_THRESHOLD 0.5 → Set alert threshold
```

#### 2. Arduino Firmware (`arduino_firmware/`)

Single‑sketch firmware with embedded models (PROGMEM), web dashboard, and captive portal.

| Feature | Implementation |
|---------|---------------|
| Web dashboard | Async HTTP server with Chart.js prediction chart, live V/I/T/SOH |
| WiFi manager | Captive portal on first boot (AP: `Battery-Predictor-Setup`) |
| mDNS | `http://battery-predictor.local` |
| Persistent storage | LittleFS: WiFi config, calibration data, cycle log (append‑only CSV) |
| Runtime model switch | Dashboard dropdown or `POST /api/model` |
| Calibration | Auto‑detect charge/discharge via INA219 current sign; 10‑cycle SOH baseline |

**Build:**
```bash
cd arduino_firmware && python bin2c.py && pio run -t upload
```

Dashboard screenshot:
```
┌──────────────────────────────────────────────────┐
│  🔋 Battery Health Predictor                     │
│  battery-predictor.local                         │
├──────────────┬───────────────────────────────────┤
│ State: MONITOR │ ╭─ Prediction Chart ───╮       │
│ Model: XGBoost │ │  ╱╲    ╱╲             │       │
│ SOH: 0.97      │ │ ╱  ╲  ╱  ╲            │       │
│ Cycle: 142     │ ╰───────────────────────╯       │
│ Pred: 3.2%     │ [Download Log] [Re-calibrate]   │
│ Live: 3.98V    │                                  │
│      -0.52A    │                                  │
│      27.4°C    │                                  │
└──────────────┴───────────────────────────────────┘
```

### Hardware Bill of Materials (~$25)

| Component | Qty | Cost |
|-----------|:---:|:----:|
| ESP32-S3‑DevKitC‑1 | 1 | $12 |
| INA219 current sensor module | 1 | $3 |
| DS18B20 + 4.7 kΩ resistor | 1 | $2 |
| DS3231 RTC module | 1 | $3 |
| Resistors, protoboard, wiring | 1 set | $5 |

### Sensor Connections

| Sensor | Bus | Pin | Notes |
|--------|:---:|:---:|-------|
| Voltage divider (3:1) | ADC | GPIO1 | 10 kΩ + 1 kΩ → 4.2 V → 1.05 V max |
| INA219 | I2C | GPIO8/9 | Shared I2C bus, addr 0x40 |
| DS3231 RTC | I2C | GPIO8/9 | Shared I2C bus, addr 0x68 |
| DS18B20 | OneWire | GPIO10 | RMT TX + GPIO polling (not bit‑bang) |

### 7 Input Features

| Feature | Unit | Source |
|---------|:----:|--------|
| `cycle` | — | Discharge cycle counter |
| `avg_voltage` | V | Mean voltage during discharge |
| `min_voltage` | V | Minimum voltage (sag) during discharge |
| `avg_current` | A | Mean discharge current (INA219) |
| `avg_temp` | °C | Mean temperature (DS18B20) |
| `duration` | s | Discharge duration |
| `SOH` | — | Coulomb capacity / 10‑cycle baseline |

---

## Validation

Three independent validation stages confirm the deployment pipeline:

### Stage 1: Tree Extraction (`export_esp32_models.py`)
Trains models on NASA (H=20) and verifies that manual tree‑walk predictions match `model.predict_proba()` for every extracted tree. Aborts on any mismatch > 1e‑5.

### Stage 2: Full 1028‑Row Validation (`full_validate.py`)
Trains fresh models, runs `predict_proba()` on all 1028 data rows, loads `trees.bin`, and compares the Python tree walker against the trained model. **0 errors across all 3 models** (tolerance 1e‑5).

### Stage 3: C Engine Comparison (`test_engine.c`)
Compiles the C tree engine, loads `trees.bin`, and compares C predictions against the trained models' `predict_proba()` on all 1028 rows. **0 errors across all 3 models.**

```bash
# Run the full validation suite
make -C pc_validation validate
```

---

## Reproducibility

### Dependencies

```
python >= 3.10
pandas
numpy
scipy
openpyxl
scikit-learn>=1.2
xgboost
lightgbm
torch>=2.0
matplotlib
seaborn
python-docx
python-pptx
shap==0.52.0
```

> **Note:** `torch` must be installed separately — the `requirements.txt` pins all other dependencies but PyTorch's installer varies by platform (CPU vs CUDA). On systems without a GPU, use `pip install torch --index-url https://download.pytorch.org/whl/cpu`. The GRU experiments require torch; all tree-model experiments and document generation run without it.

### Research Pipeline

```bash
# 1. Run all experiments (tree models ~30 min, GRU ~45 min)
python src/run.py

# 2. Regenerate figures individually (optional — run.py covers all)
python src/plot_fig01_fig03_fig04.py
python src/plot_dual_heatmap.py
python src/plot_calibration_comparison.py
python src/plot_fig02.py
python src/plot_fig05.py
python src/plot_shap.py

# Target-chemistry adaptation results (uses the resumable reduced CSV)
python src/plot_recalibration.py

# 3. Build papers and presentations
python src/generate_paper.py               # paper/paper.docx
python src/generate_paper_ieee.py           # paper/paper_ieee.docx
python src/generate_paper_ieee_edge.py      # paper/Paper_IEEE.docx (edge deployment)
python src/generate_paper_methodology.py    # paper/paper_methodology_results.docx
python src/generate_presentation.py
python src/generate_presentation_simple.py
```

Outputs:
- `paper/paper.docx`, `paper/paper_ieee.docx`, `paper/Paper_IEEE.docx`, `paper/paper_methodology_results.docx`
- `presentation/presentation.pptx` (18 slides, detailed)
- `presentation/presentation_simple.pptx` (18 slides, simplified)
- `data/Fig*.png` — legacy benchmark figures
- `paper_ieee_access/figs/` — paper-ready figures

### Deployment Pipeline

```bash
# Full end-to-end: train, export, validate, benchmark
bash run_all.sh

# Or step by step:
pip install -r requirements.txt
python scripts/export_esp32_models.py      # Train + export trees.bin
python pc_validation/generate_reference.py # Generate Python reference
make -C pc_validation run                  # C vs Python comparison
make -C pc_validation benchmark           # Inference speed benchmark
```

### Reproducibility Note

Published Brier scores from the original Shikdar & Laaksonen study (~0.032) could not be reproduced from the available source code (~0.17–0.26 in our runs). Our AUC values (0.80–0.90) are consistent with the published range. See [`study_materials/Discrepancy_Note_Published_vs_Reproduced.md`](study_materials/Discrepancy_Note_Published_vs_Reproduced.md) for full discussion.

**Training is deterministic:** `random_state=42` produces identical models across runs. The `trees.bin` binary at `esp32_firmware/main/trees.bin` can be regenerated by running `python scripts/export_esp32_models.py`.

---

## Repository Structure

```
Multi-Horizon-Hazard-Models-for-Battery-Failure-Prediction/
│
├── .gitignore
├── README.md
├── ARCHITECTURE.md              # <-- System architecture (this file)
├── requirements.txt             # Python dependencies
├── run_all.sh                   # End-to-end deployment pipeline
│
├── src/                         # RESEARCH: ML pipeline (Python)
│   ├── run.py                   #   Orchestrator — runs all experiments + generates all outputs
│   ├── benchmark_cv.py          #   XGBoost/LightGBM/RF — within-dataset + cross-chem CV
│   ├── gru_cv.py                #   GRU sequence classifier (1 layer, 8 hidden, W=10)
│   ├── composite_label.py       #   Failure label: SOH≤0.80 OR voltage sag<94% baseline
│   ├── loader.py                #   NASA dataset loader (.mat)
│   ├── loader_calce.py          #   CALCE dataset loader (.zip/.xlsx)
│   ├── loader_oxford.py         #   Oxford dataset loader (.mat)
│   ├── loader_severson.py       #   MIT-Stanford Severson loader
│   ├── plot_*.py                #   8 plotting scripts for all figures
│   └── generate_*.py            #   Paper + presentation generators
│
├── scripts/                     # DEPLOYMENT: model export
│   ├── export_esp32_models.py   #   Train 3 models, export trees.bin + model_manifest.h
│   └── flash_model.sh           #   Flash trees.bin to ESP32 model partition
│
├── pc_validation/               # VALIDATION: C vs Python
│   ├── test_engine.c            #   C tree engine validation + benchmark
│   ├── generate_reference.py    #   Python tree walker on trees.bin
│   ├── full_validate.py         #   1028-row full validation against trained models
│   ├── reference.csv            #   Reference predictions
│   └── Makefile                 #   Build: make run / make validate / make benchmark
│
├── esp32_firmware/              # DEPLOYMENT: ESP-IDF firmware (C, production)
│   ├── platformio.ini           #   PlatformIO build config
│   ├── partitions_model.csv     #   8MB app + 6MB model partition
│   ├── main/
│   │   ├── main.c               #   State machine + UART protocol
│   │   ├── model_manifest.h     #   Model metadata
│   │   └── trees.bin            #   372 KB binary (all 3 models)
│   └── components/
│       ├── tree_engine/         #   C inference engine
│       ├── sensors/             #   ADC, INA219, DS18B20, DS3231, SOH
│       └── feature_extractor/   #   7-feature extraction
│
├── arduino_firmware/            # DEPLOYMENT: Arduino firmware (web dashboard)
│   ├── platformio.ini
│   ├── partitions.csv           #   4MB app + 12MB LittleFS
│   ├── bin2c.py                 #   trees.bin → PROGMEM header converter
│   └── src/
│       ├── battery_predictor.ino   # Single sketch (1055 lines)
│       └── models_data.h           # Auto-generated PROGMEM model array
│
├── data/                        # Cleaned CSVs and legacy research assets
│   ├── nasa_clean_filtered.csv  #   37 LCO cells, 1028 cycles
│   ├── calce_clean.csv          #   7 LCO cells, ~8700 cycles
│   ├── oxford_clean.csv         #   5 LFP cells, ~300 cycles
│   ├── benchmark_results.csv    #   All experiment results
│   └── Fig*.png                 #   Legacy benchmark figures
│
├── results/recalibration/       # Resumable target-chemistry adaptation run
│   ├── recalibration_reduced.csv
│   ├── recalibration_reduced.db
│   └── README.md

├── paper_ieee_access/           # IEEE Access source, PDF, and paper figures
│   ├── main_access.tex
│   ├── main_access.pdf
│   └── figs/
│
├── paper/                       # Generated paper.docx
├── presentation/                # Generated PPTX slide decks
├── hardware validation/         # Self-contained hardware docs + circuit diagram (separate git repo)
├── figs_journal_clean/          # Publication-quality figure PNGs
├── figs_journal_editable/       # Editable source SVGs/PDFs/PPTXs
├── tables_journal/              # Journal-ready CSV tables
├── study_materials/             # Primer, discrepancy note, figure annotations
└── opendesign/                  # OpenDesign viewer
```

---

## Paper and Journal Outputs

- **`paper_ieee_access/main_access.pdf`** — rebuilt IEEE Access paper with organized result plates.
- **`paper_ieee_access/figs/`** — figures embedded by the IEEE Access source, including recalibration figures.
- **`results/recalibration/`** — resumable CSV/SQLite state and logs for the 1,047-row reduced run.
- **`tables_journal/TableR1_ArmA_Recalibration.csv`** and **`TableR2_ArmB_Recovery.csv`** — recalibration tables.

- **`figs_journal_clean/`** — Publication-quality PNGs (16 figures, 600 DPI)
- **`figs_journal_editable/`** — Source files in SVG, PPTX, and PDF (6 figures, 18 files) for journal submission or revision
- **`tables_journal/`** — Cross-dataset AUC table (H=20, Platt-calibrated) as CSV for direct inclusion in manuscripts

---

## Citation

```bibtex
@inproceedings{siddiquee2026multi,
  title={Multi-Horizon Hazard Models for Battery Failure Prediction: Within-Dataset Reliability and Cross-Chemistry Transferability},
  author={Siddiquee, Hussain Touhid and Islam, Syeda Salsabil and Islam, Ariya Jasimul and Eshica, Chowdhury Farzana Hoque},
  year={2026}
}
```

---

## References

[1] T. A. Shikdar and H. Laaksonen, "Learning when not to use a battery: Multihorizon failure intelligence," *Int. Trans. Electr. Energy Syst.*, vol. 2026, art. 6000810, 2026. doi:10.1155/etep/6000810.

[2] B. Zadrozny and C. Elkan, "Transforming classifier scores into accurate multiclass probability estimates," in *Proc. ACM SIGKDD*, 2002.

[3] J. Platt, "Probabilistic outputs for support vector machines and comparisons to regularized likelihood methods," in *Advances in Large Margin Classifiers*, 1999.

[4] B. Saha and K. Goebel, "Battery Data Set," NASA Ames Prognostics Data Repository, 2007.

[5] CALCE Battery Research Group, "Battery aging datasets," University of Maryland, 2023.

[6] Oxford Battery Degradation Dataset, "LFP pouch cell cycling data," University of Oxford, 2021.

[7] E. R. DeLong, D. M. DeLong, and D. L. Clarke-Pearson, "Comparing the areas under two or more correlated receiver operating characteristic curves: a nonparametric approach," *Biometrics*, vol. 44, no. 3, pp. 837–845, 1988.

[8] K. A. Severson, P. M. Attia, N. Jin, et al., "Data-driven prediction of battery cycle life before capacity degradation," *Nature Energy*, vol. 4, pp. 383–391, 2019. doi:10.1038/s41560-019-0356-8. Kaggle mirror: https://www.kaggle.com/datasets/itshpark/data-driven-prediction-of-battery-cycle
