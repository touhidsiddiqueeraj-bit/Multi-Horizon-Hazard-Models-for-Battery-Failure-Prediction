# Architecture

System design and data flow for the Multi-Horizon Battery Failure Prediction project — from research training through embedded deployment.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        RESEARCH TRACK                               │
│                                                                     │
│  NASA (.mat) ──→ loader.py ──→ nasa_clean_filtered.csv              │
│  CALCE (.zip) ──→ loader_calce.py ──→ calce_clean.csv               │
│  Oxford (.mat) ──→ loader_oxford.py ──→ oxford_clean.csv            │
│                                       │                              │
│                                       ▼                              │
│  ┌────────────────────────────────────────────────────┐             │
│  │  benchmark_cv.py — 5-fold GroupKFold CV            │             │
│  │  • XGBoost / LightGBM / Random Forest / GRU       │             │
│  │  • H ∈ {10, 20, 30, 50}                           │             │
│  │  • Within-dataset + cross-chemistry transfer      │             │
│  │  • Isotonic vs Platt calibration                  │             │
│  └─────────┬──────────────────────────────────────────┘             │
│            │                                                        │
│            ▼                                                        │
│  benchmark_results.csv — all metrics (AUC, Brier)                  │
│            │                                                        │
│            ▼                                                        │
│  plot_*.py ──→ data/Fig*.png                                        │
│  generate_paper.py ──→ paper/paper.docx                            │
│  generate_presentation.py ──→ presentation/*.pptx                  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │ export_esp32_models.py
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      DEPLOYMENT TRACK                               │
│                                                                     │
│  Trained models ──→ export_esp32_models.py ──→ trees.bin (372 KB)  │
│                                                    │                │
│                          ┌─────────────────────────┼──────────┐     │
│                          │                         │          │     │
│                          ▼                         ▼          ▼     │
│                   esp32_firmware/          arduino_firmware/        │
│                   (ESP-IDF, C)            (Arduino, .ino)          │
│                                                                     │
│  Both load trees.bin via:                                          │
│    tree_engine_init() → tree_engine_select() → tree_engine_predict()│
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Research Architecture

### Data Loaders

Three loaders normalize disparate battery cycling data into a shared feature space.

| Dataset | Loader | Format | Cells | Chemistry |
|---------|--------|--------|------:|:---------:|
| NASA 18650 | `loader.py` | `.mat` (struct arrays) | 37 | LCO |
| CALCE LCO/CX2 | `loader_calce.py` | `.zip` → `.xlsx` per cell | 7 | LCO |
| Oxford LFP | `loader_oxford.py` | `.mat` (single file) | 5 | LFP |

Each loader outputs a flat CSV with columns: `cell`, `cycle`, `avg_voltage`, `min_voltage`, `avg_current`, `avg_temp`, `duration`, `SOH`, `RUL`.

### Composite Failure Label (`composite_label.py`)

A cycle at position *t* is labelled positive if failure occurs within [*t*, *t+H*) cycles, where failure is defined as:

```
SOH ≤ 0.80  OR  avg_voltage_sag < 0.94 × baseline_avg_voltage
```

The voltage sag baseline is the mean `min_voltage` over the first 10 cycles of each cell.

### Benchmark CV (`benchmark_cv.py`)

Two evaluation modes:

1. **Within-dataset**: 5-fold GroupKFold (grouped by cell — no cell leaks across folds). Each fold: train on 80% of cells, evaluate on held-out 20%.
2. **Cross-chemistry**: Train on all LCO cells (NASA + CALCE, or either alone), test on all Oxford LFP cells (single train/test split).

For each fold, both isotonic and Platt calibrators are fit on training-fold scores (not a held-out set). This is a deliberate fairness choice — `CalibratedClassifierCV(cv=3)` would give an unfair 3-model ensemble advantage.

### Model Hyperparameters

| Model | Parameters | Source |
|-------|-----------|--------|
| XGBoost | `max_depth=4, n_estimators=300, lr=0.05, subsample=0.8, colsample_bytree=0.8, min_child_weight=5` | Paper match |
| LightGBM | `max_depth=4, n_estimators=300, lr=0.05, subsample=0.8, colsample_bytree=0.8, min_child_samples=20` | Paper match |
| Random Forest | `max_depth=6, n_estimators=300` | Paper match |
| GRU | 1 layer, 8 hidden units, W=10 window, BCEWithLogits loss, Adam lr=0.005, patience=10 | Paper match |

---

## Deployment Architecture

### Model Export Pipeline (`scripts/export_esp32_models.py`)

```
┌──────────────┐    ┌──────────────────┐    ┌────────────────┐
│ Train models │───→│ Extract tree     │───→│ Serialize to   │
│ on NASA H=20 │    │ structures from  │    │ packed binary  │
│              │    │ sklearn/xgboost/ │    │ (trees.bin)    │
│              │    │ lightgbm objects │    │                │
└──────────────┘    └──────────────────┘    └────────────────┘
       │                      │                      │
       ▼                      ▼                      ▼
  model.fit(X, y)     For each tree:            Binary layout:
  predict_proba()     walk internal nodes,      [header][offset
  for 50-row          extract feature_idx,      table][model 0
  verification        threshold, children,      trees][model 1
                      leaf_value                trees][model 2
                                                trees][checksum]
```

Three extractors handle library-specific tree representations:

- **XGBoost**: `trees_to_dataframe()` → map string IDs to flat indices, extract `Yes`/`No` children + `Gain` leaves
- **LightGBM**: `model_to_string()` → parse `Tree=`, `split_feature`, `threshold`, `leaf_value` from text dump; LightGBM uses negative child values for leaf references (resolved by `-(child + 1)` → flat index)
- **RF**: `estimator_.tree_` → sklearn's `children_left/right`, `threshold`, `feature`, `value` arrays

Each extractor converts the library's tree representation into a flat array of `treenode_t` structs.

### Binary Format Specification

```
┌─────────────────────────────────────────────────────────────────┐
│  Offset  │ Size │ Field                                         │
├──────────┼──────┼───────────────────────────────────────────────┤
│  0       │ 4    │ magic = 0x54524545 ("EERT" as LE)            │
│  4       │ 4    │ version = 1                                   │
│  8       │ 4    │ n_models = 3                                  │
│  12      │ 4×3  │ offset table: byte offset to each model      │
├──────────┼──────┼───────────────────────────────────────────────┤
│  Model N (at offset[N]):                                       │
│  +0      │ 2    │ model_type (0=XGBoost, 1=LightGBM, 2=RF)    │
│  +2      │ 4    │ n_trees (300)                                │
│  +6      │ 4    │ init_score (logit bias or 0)                 │
│  +10     │ 1    │ comparison_type (0=≤, 1=<)                   │
│  +11     │ 3    │ padding                                      │
├──────────┼──────┼───────────────────────────────────────────────┤
│  Tree T (within model):                                        │
│  +0      │ 4    │ n_nodes in this tree                         │
│  +4      │ N×14 │ treenode_t entries (see below)                │
└──────────┴──────┴───────────────────────────────────────────────┘

treenode_t (14 bytes, packed):
┌──────────┬────────┬──────────────┬───────────────┬────────────┐
│ feature  │ thresh │ left_child   │ right_child   │ leaf_value │
│ _idx     │ old    │ (int16)      │ (int16)       │ (float32)  │
│ (int16)  │ (float)│              │               │            │
├──────────┼────────┼──────────────┼───────────────┼────────────┤
│ -1=leaf  │ N/A    │ -1           │ -1            │ leaf score │
│ ≥0       │ split  │ flat index   │ flat index    │ 0.0        │
│          │ val    │ to child     │ to child      │            │
└──────────┴────────┴──────────────┴───────────────┴────────────┘
```

**Key details:**

- `init_score`: XGBoost uses `log(p/(1-p))` of the training prior (≈ −0.488 for 38% positive rate). LightGBM bakes the bias into tree leaf values (init_score = 0). RF uses simple average (init_score = 0).
- `comparison_type`: XGBoost uses strict `<` (COMPARISON_LT=1); LightGBM and RF use `≤` (COMPARISON_LE=0). The C engine applies the operator on float32 values for all three model types; the Python walker casts to float64 for LightGBM/RF.
- Child indices are flat offsets within the tree's node array (not byte offsets).

**File sizes:**

| Component | Bytes |
|-----------|------:|
| Header (magic+version+n_models) | 12 |
| Offset table (3 × 4 bytes, at byte 12) | 12 |
| Unused (4 bytes after offset table) | 4 |
| XGBoost (14 B model hdr + 300×4 B tree hdrs + 3,242×14 B nodes) | 46,602 |
| LightGBM (14 B model hdr + 300×4 B tree hdrs + 7,000×14 B nodes) | 99,214 |
| Random Forest (14 B model hdr + 300×4 B tree hdrs + 16,064×14 B nodes) | 226,110 |
| Checksum | 4 |
| **Total** | **371,958** |

Per-model byte count = `14 (model header) + 4 × n_trees (tree headers) + 14 × n_nodes`.

### C Tree Engine (`tree_engine.c` / `tree_engine.h`)

The inference engine is ~150 lines of C. Core predict function (simplified — see `tree_engine.c` for the authoritative implementation):

```c
float tree_engine_predict(const float features[N_FEATURES]) {
    const model_data_t *md = &g_models[g_active];
    const model_header_t *hdr = md->header;
    int use_lt = (hdr->comparison_type == COMPARISON_LT);

    double total = (hdr->model_type == MODEL_RANDOM_FOREST) ? 0.0 : (double)hdr->init_score;

    for (uint32_t t = 0; t < hdr->n_trees; t++) {
        const treenode_t *nodes = md->trees[t];
        int32_t node = 0;
        // Loop until a leaf is reached — no depth cap (current trees max_depth ≤ 6,
        // but the loop tolerates arbitrary depth).
        while (node >= 0 && nodes[node].feature_idx >= 0) {
            float fv = features[nodes[node].feature_idx];   // float32
            float thr = nodes[node].threshold;              // float32
            int cond = use_lt ? (fv < thr) : (fv <= thr);
            node = cond ? nodes[node].left_child : nodes[node].right_child;
        }
        if (node >= 0) total += (double)nodes[node].leaf_value;
    }

    if (hdr->model_type == MODEL_RANDOM_FOREST)
        return (float)(total / (double)hdr->n_trees);          // RF: mean of leaf votes
    return 1.0f / (1.0f + expf(-(float)total));                 // XGBoost/LightGBM: sigmoid
}
```

> ℹ️ **Pseudocode vs. implementation.** Earlier versions of this document showed a depth-limited loop (`while (depth++ < 20)`) and bit-level `uint32_t*` casts for XGBoost / `double` casts for LightGBM+RF. The actual `tree_engine.c` loops until a leaf is reached and uses plain `float < float` / `float <= float` comparisons for all three model types. The Python walkers in `pc_validation/generate_reference.py` and `pc_validation/full_validate.py` cast LightGBM/RF comparisons to `float(...)` (Python float64) — functionally equivalent for tree thresholds that are exactly representable in float32. If you change the C engine's precision, regenerate `trees.bin` and re-run `make -C pc_validation validate`.

### Comparison Operators (Critical Detail)

| Model | Comparison | Precision used in C engine | Precision used in Python walker |
|-------|-----------|---------------------------|----------------------------------|
| XGBoost | `fv < threshold` | float32 | float32 (`as_f32()` cast) |
| LightGBM | `fv ≤ threshold` | float32 | float64 (`float()` cast) |
| Random Forest | `fv ≤ threshold` | float32 | float64 (`float()` cast) |

The Python walker casts LightGBM/RF comparisons to float64 to mirror the upstream library's behaviour. The C engine uses float32 for all three model types (the `feature` array is `float[N_FEATURES]` and `treenode_t.threshold` is `float32`). In practice, tree thresholds from XGBoost/LightGBM/sklearn are exactly representable in float32, so the two implementations agree to within the 1e-5 validation tolerance. If a future model produces thresholds outside the float32 representable range, the C engine should be updated to cast LightGBM/RF comparisons to `double`.

The Python tree walker in `generate_reference.py` and `full_validate.py` mirrors the operator choice (`<` for XGBoost, `≤` for LightGBM+RF).

### Output Transforms

| Model | Formula |
|-------|---------|
| XGBoost | `σ(init_score + Σ leaf_scores)` |
| LightGBM | `σ(Σ leaf_scores)` |
| Random Forest | `mean(leaf_scores)` |

Where `σ(x) = 1 / (1 + e⁻ˣ)`.

### Sensor Pipeline

```
┌──────────────┐    ┌──────────────────┐    ┌───────────────────┐
│  Charging    │    │  Discharging     │    │  Feature          │
│  (I > +0.05A)│───→│  (I < -0.05A)   │───→│  Extraction       │
│              │    │                  │    │                   │
│  Idle: no    │    │  Sample at 10Hz: │    │  7 features →     │
│  accumulation│    │  V_sum, V_min,   │    │  tree_engine_     │
│              │    │  I_sum, T_sum,   │    │  predict()        │
│              │    │  Coulomb count   │    │                   │
└──────────────┘    └──────────────────┘    └───────────────────┘
                          │
                          ▼
                    SOH = cycle_capacity / baseline_avg
                    (baseline = mean of first 10 cycles)
```

#### Individual Sensor Drivers

| Sensor | Bus | Driver | Key Implementation Detail |
|--------|:---:|--------|--------------------------|
| Voltage divider | ADC | `voltage_divider.c` (ESP-IDF) / `battery_predictor.ino` (Arduino) | ESP-IDF: 10 kΩ + 10 kΩ divider, `VOLTAGE_DIVIDER_FACTOR = 2.0f`, `ADC_ATTEN_DB_12` (≈11 dB, 0–3.3 V range). Arduino: `VOLTAGE_DIVIDER_RATIO = 3.0f`, `ADC_11db`. **The two firmware variants use different divider factors — verify resistor values against your wiring before flashing.** |
| INA219 | I2C | `current_sensor.c` (ESP-IDF) / `battery_predictor.ino` (Arduino) | I2C address 0x40. ESP-IDF configures 32 V / 320 mA range (calibration register = 8192). Arduino uses Adafruit's `setCalibration_32V_2A()` (32 V / 2 A range). The two ranges differ — 320 mA will saturate on a real 18650 discharge (~2 A). |
| DS18B20 | OneWire | `temp_sensor.c` | **RMT TX** (not bit-bang) for reset + presence pulse + ROM commands; GPIO polling for read slots. Immune to scheduler preemption. |
| DS3231 | I2C | `rtc_sensor.c` | I2C address 0x68, BCD-to-binary conversion, 24h mode |

### Firmware State Machine (ESP-IDF)

```
     ┌──────────┐
     │   INIT   │  Load trees.bin from partition, init sensors
     └────┬─────┘
          │
          ▼
┌──────────────────┐     I < -0.05A     ┌──────────────────────┐
│ CALIBRATE_CHARGE │───────────────────→│ CALIBRATE_DISCHARGE  │
│ (I > +0.05A)     │                    │ (record 10 cycles)   │
└──────────────────┘                    └──────────┬───────────┘
                                                   │ after 10 cycles
                                                   ▼
                                          ┌──────────────────┐
                                          │     MONITOR      │
                                          │ continuous 10Hz  │
                                          │ prediction every │
                                          │ discharge cycle  │
                                          └──────────────────┘
```

The Arduino firmware uses the same state machine with auto-detection of charge/discharge via INA219 current sign.

### Arduino Firmware (`battery_predictor.ino`)

The Arduino variant adds a web server stack on top of the same state machine:

```
┌─────────────────────────────────────────────────────────────────┐
│  battery_predictor.ino                                          │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌──────────────┐  │
│  │ Tree     │  │ Sensors  │  │ WiFi +    │  │ Web Server   │  │
│  │ Engine   │  │ (4)      │  │ Captive   │  │ + WebSocket  │  │
│  │          │  │          │  │ Portal    │  │ + Dashboard  │  │
│  └──────────┘  └──────────┘  └───────────┘  └──────────────┘  │
│       │             │              │               │           │
│       ▼             ▼              ▼               ▼           │
│  PROGMEM       I2C, ADC,    LittleFS          Async HTTP       │
│  (372 KB)      OneWire      /wifi.json        port 80          │
│                             /calibration.json                   │
│                             /cycle_log.csv     mDNS:            │
│                                                battery-         │
│                             DNSServer          predictor.local  │
│                             (captive portal)                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Validation Architecture

### Three-Stage Validation

```
Stage 1: Inside export_esp32_models.py (50 rows)
  model.predict_proba()  vs  Python tree walker on extracted trees
  → Verifies tree extraction is correct

Stage 2: pc_validation/full_validate.py (ALL 1028 rows)
  model.predict_proba()  vs  Python tree walker  vs  C tree engine
  → Verifies binary serialization + C engine against ground truth

Stage 3: pc_validation/test_engine.c + generate_reference.py
  C tree engine  vs  Python tree walker (both on trees.bin)
  → Verifies C reads the binary correctly (bit-exact match)
```

### Stage 2 is the Key Innovation

Most embedded ML validations compare against a Python re-implementation of the same binary reader — a circular validation that proves only that both implementations share the same bugs. Our `full_validate.py` breaks this cycle by comparing C predictions directly against the **original trained model**:

```
trained_model.predict_proba()  ←── C tree_engine_predict()
         │                                │
         └── both compared ───────────────┘
         Result: 0 errors on 1028 rows
```

---

## Memory & Performance

### Binary Size

| Component | Size |
|-----------|-----:|
| trees.bin (flash) | 372 KB (371,958 bytes) |
| In PSRAM (parsed) | ~360 KB (26,306 nodes × 14 B + per-tree headers) |
| ESP32-S3 PSRAM | 8 MB octal |
| Utilization | ~5% |

### Inference Latency

| Model | PC (gcc -O2) | ESP32-S3 (est.) | Trees | Nodes per tree |
|-------|:------------:|:---------------:|:-----:|:--------------:|
| XGBoost | 7.6 μs | ~200 μs | 300 | 10.8 |
| LightGBM | 5.1 μs | ~150 μs | 300 | 23.3 |
| RF | 8.1 μs | ~250 μs | 300 | 53.5 |

**Projection method:** ESP32-S3 at 240 MHz with PSRAM latency ≈ 15× slower than PC with L2 cache. Budget: 100 ms → ~100× margin.

---

## Key Design Decisions

### 1. Binary Format: Flat Array, Not Linked List

Trees are stored as flat node arrays with integer child indices rather than pointers. This allows the entire binary to reside in PSRAM and be traversed with array lookups — no pointer chasing, no relocation, no per-model memory allocation.

### 2. Bug-Compatible Offset Table

The offset table starts at byte 12 in the binary — overwriting what would be the `reserved` field of a 16-byte header. The writer (`export_esp32_models.py`) packs a 16-byte header then writes the offset table at byte 12, leaving 4 unused bytes (bytes 24–27) before model 0 begins at byte 28. Both writer and reader agree on byte 12 as the offset-table position, making it a stable (if unusual) convention. Total preamble before model 0 is 28 bytes.

### 3. RMT for DS18B20, Not Bit-Bang

Bit-bang OneWire timing relies on nanosecond-accurate GPIO toggling. Under FreeRTOS, scheduler preemption corrupts the timing. The RMT peripheral (ESP32's remote control module) generates the precise 1–60 μs pulses in hardware. Read slots still use GPIO polling but with margins that tolerate preemption.

### 4. XGBoost Uses `strict <` with float32

XGBoost internally uses strict `<` comparisons; LightGBM and sklearn use `≤`. Using the wrong operator produces prediction differences up to ~5×10⁻⁴. The C engine stores the operator choice per-model in the `comparison_type` byte of `model_header_t` (`COMPARISON_LT` for XGBoost, `COMPARISON_LE` for LightGBM/RF). Precision in the C engine is float32 for all models; the Python walker casts LightGBM/RF to float64. In practice tree thresholds are exactly representable in float32 so the two agree within the 1e-5 validation tolerance.

### 5. PROGMEM for Model Data (Arduino)

The Arduino firmware embeds the 372 KB model binary as a `const uint8_t[] PROGMEM` array. On ESP32, flash is memory-mapped into the CPU address space, so PROGMEM data is readable via regular pointers — no `pgm_read_byte` needed. This keeps the Arduino firmware as a single `.ino` file without external storage dependencies.

### 6. Single Binary, Runtime Model Switch

All three models are packed into one `trees.bin`. The C engine parses all three at init and stores their offsets. `tree_engine_select(model_id)` switches between them with zero additional I/O. The ESP-IDF firmware uses UART commands; the Arduino firmware uses a web dashboard dropdown.

---

## Project Directory Map

```
Root
├── src/              Research: ML training, CV, plotting, paper gen
├── scripts/          Model export: train + export trees.bin
├── pc_validation/    C vs Python validation suite
├── esp32_firmware/   ESP-IDF firmware (production)
├── arduino_firmware/ Arduino firmware (web dashboard)
├── data/             Cleaned CSVs, benchmark results, figures
├── hardware validation/  Self-contained hardware docs (separate repo)
├── paper/            Generated paper.docx
├── presentation/     Generated PPTX decks
├── figs_journal_clean/     Publication-quality figures
├── figs_journal_editable/  Editable figure sources (SVG/PDF/PPTX)
├── tables_journal/   Journal-ready CSV tables
├── study_materials/  Primer, discrepancy note, figure annotations
└── opendesign/       OpenDesign viewer
```
