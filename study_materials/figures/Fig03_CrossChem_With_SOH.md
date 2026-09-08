# Fig 03 — Cross-Chemistry Transfer with SOH

**File:** `figs_journal_clean/Fig03_CrossChem_With_SOH.png`

## Overview
3×3 heatmap showing cross-chemistry transfer AUC when SOH is included as a feature. Models trained on LCO cells (NASA, CALCE, or both) are tested on Oxford LFP cells.

## Results
| Model | NASA→LFP | CALCE→LFP | ALL→LFP |
|-------|----------|-----------|---------|
| XGBoost | 0.945 | 0.874 | 0.970 |
| LightGBM | 0.992 | 0.929 | 0.935 |
| Random Forest | 1.000 | 0.703 | 0.994 |

## Key Observations
1. AUC range: 0.703–1.000. These values appear to demonstrate strong cross-chemistry generalization.
2. **NASA→LFP transfers best** — 37 cells with diverse random-walk degradation profiles provide the richest training signal.
3. **CALCE→LFP is weakest** — only 7 cells with slow, uniform degradation. The model sees less diversity in failure modes.
4. **Combined training (ALL) doesn't beat NASA alone** — adding 7 CALCE cells to 37 NASA cells provides no benefit for LFP transfer.

## ⚠️ Caution
These results are misleading. The model is using SOH as a chemistry-specific lookup table, not learning transferable features. See Fig 04 (without SOH) for the honest comparison.

## Connection to Paper
Section 4.3 (Cross-Chemistry Transfer: With SOH). This figure is placed first in the subsection, directly above Fig 04 for immediate visual contrast.
