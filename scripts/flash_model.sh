#!/usr/bin/env bash
# Flashes trees.bin to the ESP32-S3 model partition (offset 0x810000, size 6MB)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BIN="${PROJECT_DIR}/esp32_firmware/main/trees.bin"
PORT="${1:-/dev/ttyACM0}"

if [ ! -f "$BIN" ]; then
    echo "ERROR: $BIN not found. Run 'python scripts/export_esp32_models.py' first."
    exit 1
fi

echo "Flashing $BIN to $PORT at 0x810000..."
esptool.py --chip esp32s3 --port "$PORT" --baud 921600 \
    write_flash 0x810000 "$BIN"
echo "Done."
