# Fig 04 — Cross-Chemistry Transfer without SOH

**File:** `figs_journal_clean/Fig04_CrossChem_No_SOH.png`

## Overview
3×3 heatmap showing cross-chemistry transfer AUC when SOH is **removed** from the feature set. Same layout as Fig 03 for direct visual comparison.

## Results
| Model | NASA→LFP | CALCE→LFP | ALL→LFP |
|-------|----------|-----------|---------|
| XGBoost | 0.508 | 0.514 | 0.512 |
| LightGBM | 0.539 | 0.510 | 0.510 |
| Random Forest | 0.541 | 0.510 | 0.541 |

## Key Observations
1. **AUC collapses to 0.51–0.54** — near-random across all 9 model/training combinations.
2. This is the central finding of the entire study: SOH drives all apparent cross-chemistry generalization.
3. Voltage, current, and temperature features alone carry no transferable signal between LCO and LFP chemistries.

## Interpretation
The SOH-as-lookup-table mechanism:
- When SOH is available, the model learns "SOH=X means ~Y cycles to failure" from LCO data.
- LFP cells traverse similar SOH trajectories, so the model applies the same mapping.
- This looks like successful transfer but is actually memorization of a chemistry-specific capacity→RUL relationship.
- Removing SOH forces the model to rely on voltage/current/temperature patterns, which do not generalize.

## Connection to Paper
Section 4.4 (Cross-Chemistry Transfer: Without SOH). Positioned directly below or beside Fig 03 so the contrast is immediate. This is the paper's headline result.
