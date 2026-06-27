# Multi-Horizon Hazard Models for Battery Failure Prediction

## What This Study Does

Extends the multi-horizon hazard classification framework from Shikdar and Laaksonen [1] — originally on NASA 18650 cells with HGB only — to two additional datasets (CALCE LCO/CX2, Oxford LFP), four model classes (XGBoost, LightGBM, Random Forest, GRU), and cross-chemistry transfer from LCO to LFP with controlled SOH ablation.

Target outlet: **IEEE Open Access** (single-column IEEE-styled .docx).

## Paper Additions (Recent)

- **IEEE single-column formatting**: Times New Roman 10pt, 0.75" margins, justified body, centered bold section headings, left bold-italic subsection headings
- **Index Terms**: battery failure prediction, multi-horizon hazard, cross-chemistry transfer, calibration, SHAP, lithium-ion
- **Required statements**: no funding received, no conflicts of interest, code available upon reasonable request
- **300 DPI figures**: all 11 PNGs regenerated at 300 DPI
- **Stale Fig06_SHAP_Importance.png removed**: replaced by three individual model SHAP figures (6a, 6b, 6c)

## The Composite Failure Label

Two criteria — either triggers "failure" for cycle t if failure occurs within [t, t+H):

1. **SOH ≤ 0.80** — capacity degraded to 80% of initial
2. **Voltage sag** — average discharge voltage < 94% of baseline (first 10 cycles)

Once triggered, label stays positive for all subsequent cycles.

## Datasets

| Dataset | Chemistry | Cells | Cycles | Characteristics |
|---------|-----------|-------|--------|-----------------|
| **NASA 18650** [4] | LCO/18650 | 37 | ~1,000 | Random-walk aging, diverse failure |
| **CALCE LCO/CX2** [5] | LCO/pouch | 7 | ~8,700 | Long slow degradation, ~92% failure rate; avg_temp + duration always NaN |
| **Oxford LFP** [6] | LFP/pouch | 5 | ~300 | Flat voltage plateau, stable degradation; voltage sag uninformative |

## Models

| Model | Key Hyperparameters | Notes |
|-------|---------------------|-------|
| **XGBoost** | max_depth=4, n_estimators=300, lr=0.05 | Matched to [1] |
| **LightGBM** | max_depth=4, n_estimators=300, lr=0.05 | Matched to [1] |
| **Random Forest** | max_depth=6, n_estimators=300 | Matched to [1] |
| **GRU** | 1 layer, 8 hidden, W=10 window | 8 units chosen deliberately — 32/64 units overfit on 7–37 cells |

Tree features: `cycle`, `avg_voltage`, `min_voltage`, `avg_current`, `avg_temp`, `duration`, `SOH`.

GRU features: sliding 10-cycle window. Cross-chemistry variant drops avg_current (A vs mA unit mismatch), avg_temp + duration (always NaN for CALCE).

## Key Findings

### 1. Within-Dataset Reliability (Fig 1, Fig 2)
- Platt-calibrated AUC ≥ 0.85 on 31/32 model–horizon–dataset combinations
- XGBoost and LightGBM comparable; Random Forest slightly behind
- GRU competitive on both NASA (mean AUC=0.886) and CALCE (mean AUC=0.949)
- AUC improves from H=10 → H=50 (more failure events in longer windows)

### 2. Platt vs Isotonic Calibration (Fig 3, Table 2)
- Platt universally outperforms isotonic — AUC gap is substantial (NASA: 0.889 vs 0.844; CALCE: 0.915 vs 0.715)
- Brier scores comparable (~0.001–0.002 diff) because isotonic trades ranking for calibration
- Fair comparison: both use same base-model scores, not cross-validated ensemble

### 3. Cross-Chemistry with SOH — Pseudo-Transfer (Fig 4, Table 3a)
- Raw AUC 0.84–1.00 for tree models (NASA→Oxford: 0.957–1.000)
- **This is an artifact**: SOH acts as a chemistry-specific lookup table
- Tree models exploit SOH via isolated hard splits that transfer perfectly
- GRU AUC 0.26–0.40: distributed hidden state entangles SOH with voltage/cycle features, partially corrupting the signal under shift

### 4. SOH Removal — Genuine Transfer Fails (Fig 5, Table 3b)
- Raw AUC collapses to 0.33–0.62 across all model classes
- No model — tree-based or sequence-aware — achieves above-chance discrimination
- Voltage/current/temperature alone carry no chemistry-invariant degradation signal

### 5. SHAP Confirms SOH Dominance (Fig 6a–6c)
- SOH dominates tree-model split decisions by a wide margin in cross-chemistry configurations
- Cycle number is a distant second; voltage/current/temperature contribute negligibly
- Consistent across XGBoost, LightGBM, and Random Forest

### 6. Calibration Fails Under Distribution Shift (Table 3a iso column)
- Isotonic systematically destroys cross-chemistry AUC: e.g., XGBoost ALL→Oxford with SOH drops from 0.979 to 0.510
- Mechanism: isotonic bins test scores by training-set distribution; under covariate shift, multiple test scores land in the same bin, creating ties that penalize AUC
- Raw (uncalibrated) scores are the primary metric for cross-chemistry comparisons

## Evaluation Protocol

- Within-dataset: 5-fold GroupKFold stratified by cell (no cell leaks across folds)
- Horizons: H ∈ {10, 20, 30, 50}
- Metrics: AUC + Brier score (calibrated)
- Cross-chemistry: single train/test split by dataset (all LCO → all LFP); raw AUC primary

## Figures

| Figure | Description | DPI |
|--------|-------------|-----|
| Fig01 | Within-dataset AUC heatmap (H=20) | 300 |
| Fig02 | Multi-horizon AUC curves (NASA, Platt-calibrated) | 300 |
| Fig03 | Calibration comparison (isotonic vs Platt) | 300 |
| Fig04 | Cross-chemistry transfer with SOH | 300 |
| Fig05 | Cross-chemistry transfer without SOH | 300 |
| Fig06a | SHAP — XGBoost (NASA→Oxford, H=20, with SOH) | 300 |
| Fig06b | SHAP — LightGBM | 300 |
| Fig06c | SHAP — Random Forest | 300 |

## Practical Implications

- Within-chemistry hazard monitoring is reliable (AUC ≥ 0.85) with standard features + Platt calibration
- Cross-chemistry transfer requires chemistry-specific feature engineering or retraining
- SOH is a lookup key, not a transferable invariant
- Model architecture determines exploitation mechanism: tree models isolate SOH splits; GRU entangles
- Post-hoc calibration should not be naively applied under distribution shift
- All code available upon reasonable request

## References

[1] T. A. Shikdar and H. Laaksonen, "Learning when not to use a battery: Multihorizon failure intelligence," Int. Trans. Electr. Energy Syst., vol. 2026, art. 6000810, 2026. doi:10.1155/etep/6000810.
[2] B. Zadrozny and C. Elkan, "Transforming classifier scores into accurate multiclass probability estimates," in Proc. ACM SIGKDD, 2002.
[3] J. Platt, "Probabilistic outputs for support vector machines and comparisons to regularized likelihood methods," in Advances in Large Margin Classifiers, 1999.
[4] B. Saha and K. Goebel, "Battery Data Set," NASA Ames Prognostics Data Repository, 2007.
[5] CALCE Battery Research Group, "Battery aging datasets," University of Maryland, 2023.
[6] Oxford Battery Degradation Dataset, "LFP pouch cell cycling data," University of Oxford, 2021.
[10] S. M. Lundberg and S.-I. Lee, "A unified approach to interpreting model predictions," in Proc. NeurIPS, 2017.
