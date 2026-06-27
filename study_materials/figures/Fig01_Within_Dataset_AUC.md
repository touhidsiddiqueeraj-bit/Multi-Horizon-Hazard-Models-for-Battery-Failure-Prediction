# Fig 01 — Within-Dataset AUC Heatmap

**File:** `figs_journal_clean/Fig01_Within_Dataset_AUC.png`

## Overview
3×2 heatmap (3 models × 2 datasets) showing Platt-calibrated AUC at H=20. This is the main within-dataset performance result.

## Results
| Model | NASA 18650 | CALCE LCO/CX2 |
|-------|-----------|---------------|
| XGBoost | 0.887 | 0.916 |
| LightGBM | 0.895 | 0.923 |
| Random Forest | 0.868 | 0.894 |

## Key Observations
1. Both datasets show AUC ≥ 0.85 across all models — the hazard classification framework works robustly on multiple LCO chemistries and cycling protocols.
2. CALCE AUC (0.89–0.92) is slightly higher than NASA (0.87–0.89), likely due to CALCE's larger per-cell training sets (775–1952 cycles vs ~300 for NASA).
3. LightGBM and XGBoost are comparable; Random Forest trails by ~0.02–0.03 AUC.

## Connection to Paper
Section 4.1 (Within-Dataset Performance). Accompanied by Table 1 (mean AUC/Brier across all H) and Fig 5 (multi-horizon AUC curves).
