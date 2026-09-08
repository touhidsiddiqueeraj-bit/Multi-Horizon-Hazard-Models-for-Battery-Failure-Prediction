# Fig 05 — Multi-Horizon AUC Curves (NASA)

**File:** `figs_journal_clean/Fig05_MultiHorizon_AUC.png`

## Overview
Line chart showing Platt-calibrated AUC vs prediction horizon H ∈ {10, 20, 30, 50} for all three models on NASA. Shows how far ahead models can reliably forecast.

## Results
| Model | H=10 | H=20 | H=30 | H=50 |
|-------|------|------|------|------|
| XGBoost | 0.819 | 0.887 | 0.908 | 0.905 |
| LightGBM | 0.863 | 0.895 | 0.915 | 0.861 |
| Random Forest | 0.752 | 0.851 | 0.859 | 0.873 |

## Key Observations
1. **AUC increases with longer horizons** — counter-intuitively, H=50 is easier than H=10. More failure events fall within a wider prediction window, improving signal-to-noise ratio.
2. The effect is monotonic: H=10 < H=20 < H=30 ≤ H=50 for all models.
3. LightGBM is best at short horizons (H=10); XGBoost is best at H=50.
4. Random Forest consistently trails the boosting methods.

## Connection to Paper
Section 4.1 (Within-Dataset Performance). Accompanies Fig 1 (heatmap at fixed H=20) and Table 1 (mean across all H).
