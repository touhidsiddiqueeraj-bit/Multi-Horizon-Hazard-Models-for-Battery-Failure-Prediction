#!/usr/bin/env bash
# End-to-end reproduction of ESP32 battery failure predictor pipeline.
# Usage: ./run_all.sh
set -euo pipefail

VENV=/tmp/venv
PROJECT="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$VENV/bin/python3"

echo "============================================"
echo " Battery Failure Predictor — Full Pipeline"
echo "============================================"

# 1. Ensure deps
if [ ! -f "$VENV/bin/python3" ]; then
    echo "Creating venv..."
    python3 -m venv "$VENV"
    $VENV/bin/pip install -q -r "$PROJECT/requirements.txt"
fi

# 2. Train models + export trees.bin
echo ""
echo "--- Step 1: Train models & export trees.bin ---"
 $PYTHON "$PROJECT/scripts/export_esp32_models.py"

# 3. Generate reference CSV
echo ""
echo "--- Step 2: Generate Python reference predictions ---"
 $PYTHON "$PROJECT/pc_validation/generate_reference.py"

# 4. Compile and run C validation + benchmark
echo ""
echo "--- Step 3: Validate C engine vs Python ---"
make -C "$PROJECT/pc_validation" clean
make -C "$PROJECT/pc_validation" benchmark

# 5. Print summary
echo ""
echo "============================================"
echo " Pipeline complete."
echo " Files:"
echo "   trees.bin   : $(ls -lh $PROJECT/esp32_firmware/main/trees.bin | awk '{print $5}')"
echo "   model_manifest.h: ready"
echo "   reference.csv: $(ls -lh $PROJECT/pc_validation/reference.csv | awk '{print $5}')"
echo "============================================"
