# Arduino Firmware — Battery Health Predictor

Single-sketch firmware for ESP32-S3 with embedded XGBoost, LightGBM, and Random Forest models for battery failure prediction.

## Files

| File | Description |
|------|-------------|
| `src/battery_predictor.ino` | Main sketch (1055 lines) |
| `src/models_data.h` | Auto‑generated PROGMEM model data (372 KB) |
| `bin2c.py` | Converts `trees.bin` → `src/models_data.h` |
| `partitions.csv` | 16 MB partition table (4 MB app + 12 MB LittleFS) |
| `platformio.ini` | PlatformIO build configuration |

## Quick Start

```bash
# 1. Generate model data header from existing trees.bin
python bin2c.py

# 2. Build and upload
pio run -t upload

# 3. Monitor
pio monitor
```

## WiFi Setup

1. **First boot**: ESP creates AP `Battery-Predictor-Setup`
2. Connect to AP, open `http://192.168.4.1`
3. Enter WiFi credentials
4. Device reboots in STA mode

Or pre‑configure by writing `/wifi.json` to LittleFS:
```json
{"ssid":"YourSSID","pass":"YourPassword"}
```

## Access

- **mDNS**: `http://battery-predictor.local`
- **Dashboard**: Full telemetry, live sensors, prediction chart, cycle log download
- **Model switch**: Dropdown in dashboard
- **API**: `/api/status`, `/api/model`, `/api/download`

## Hardware

| Sensor | Bus | Pin(s) |
|--------|-----|--------|
| Voltage divider (3:1) | ADC | GPIO1 |
| INA219 current | I2C | GPIO8/9 |
| DS18B20 temperature | OneWire | GPIO10 |
| DS3231 RTC | I2C | GPIO8/9 |

## Calibration

Auto‑detects charge/discharge via INA219 current sign. First 10 discharge cycles establish SOH baseline.
