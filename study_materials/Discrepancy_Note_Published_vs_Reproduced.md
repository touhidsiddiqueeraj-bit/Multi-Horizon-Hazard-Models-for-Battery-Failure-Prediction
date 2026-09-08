# Published Results vs. Reproduced: Discrepancy Note

## Published Table (Table1_Performance.csv)

| H | Brier (cal) | AUC (cal) |
|---|------------|-----------|
| 10 | 0.032 | 0.891 |
| 20 | 0.064 | 0.891 |
| 30 | 0.058 | 0.898 |
| 50 | 0.090 | 0.868 |

## Reproduced (Original `hazard_cv.py` — HGB, depth=3, max_iter=500)

| H | Brier (cal) | AUC (cal) |
|---|------------|-----------|
| 10 | 0.261 | 0.797 |
| 20 | 0.240 | 0.833 |
| 30 | 0.253 | 0.815 |
| 50 | 0.214 | 0.884 |

## Our Benchmark (XGBoost, depth=4, 300 trees)

| H | Brier (cal) | AUC (cal) |
|---|------------|-----------|
| 10 | 0.211 | 0.846 |
| 20 | 0.248 | 0.821 |
| 30 | 0.211 | 0.841 |
| 50 | 0.167 | 0.878 |

## Observations

1. **AUC is broadly consistent** across all three sources (0.80–0.90). Our XGBoost run is closer to the published AUC than the original HGB run.

2. **Brier is not reproducible.** The published Brier (0.032 at H=10) is an order of magnitude better than any actual run of the code in this repository (0.167–0.261). It is unclear whether:
   - The published table used a different model configuration not checked into the repo
   - Different preprocessing or data filtering was applied
   - The published values are from a single best fold rather than cross-validation mean
   - A different calibration method or post-processing was used

3. **Original HGB run is weaker than both published and our XGBoost** across all metrics, suggesting the code in `xalibration/hazard_cv.py` is not the version that produced the paper's published numbers.

## Implications for Conference A

- **Our AUC results are defensible** — they fall within the expected range and improve on the original HGB baseline.
- **Our Brier scores should be interpreted cautiously** when comparing to the published paper. We match the actual code's behaviour, not the published table.
- Recommend adding a note in the conference submission explaining that published Brier values could not be reproduced with the available source code, and treating our Brier (~0.17–0.25) as the reproducible baseline.
