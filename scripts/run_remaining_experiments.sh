#!/usr/bin/env zsh
# Runs the remaining review-response experiments sequentially.
# Usage: ./scripts/run_remaining_experiments.sh
set -e
cd "$(dirname "$0")/../src"
echo "=== E4 feature ablation (within + transfer) ==="
python3 feature_ablation.py within
python3 feature_ablation.py transfer
echo "=== E5 failure-definition ablation ==="
python3 faildef_ablation.py
echo "=== E6 same-chemistry controls ==="
python3 same_chem_transfer.py
echo "=== E2 discrete-time hazard model ==="
python3 hazard_model.py within
python3 hazard_model.py transfer
echo "=== E9 operational metrics ==="
python3 operational_metrics.py
echo "=== monotonicity analysis ==="
python3 monotonicity_check.py
echo "ALL_REMAINING_DONE"
