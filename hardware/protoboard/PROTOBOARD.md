# Protoboard Prototype — Build Guide

Real-hardware build of the battery predictor on a protoboard with the
ESP32-S3-DevKitC-1. No PCB fabrication required. This is the deployment
validated in Section IV-H of the paper.

## Parts to Order (~$25)

| Item | Qty | Est. cost | Notes |
|------|:---:|:---------:|-------|
| ESP32-S3-DevKitC-1 (N8R8) | 1 | $12 | Main board, plugs into breadboard |
| INA219 current sensor module (breakout) | 1 | $3 | I2C, addr 0x40, 0.1 Ω shunt on board |
| DS3231 RTC module (breakout) | 1 | $3 | I2C, addr 0x68, has backup-battery holder |
| DS18B20 TO-92 + 4.7 kΩ resistor | 1 | $2 | OneWire temp |
| 10 kΩ resistors | 2 | $1 | 2:1 voltage divider (10k+10k) |
| 100 nF ceramic, 100 µF 16V electrolytic | 1+1 | $1 | Decoupling |
| Protoboard (half-size 830 tie-point stripboard), jumper wires | 1 | $2 | |
| CR1220 coin cell | 1 | $1 | RTC backup |
| 18650 cell (or lab supply) | 1 | — | Battery under test |

Total ≈ $25–26. All parts available from Amazon/Adafruit/RPiShop-style
retail — no JLCPCB assembly needed for the prototype.

> Skip the DS3231 module if you only need short-run data: the firmware warns
> but continues without it. Needed for timestamps in the CSV log.

## Wiring (DevKitC 2×19 header)

Use the 3.3 V rail only. Do **not** apply 5 V to GPIOs.

| From (DevKitC pin) | To | Wire |
|--------------------|----|------|
| `3V3` | INA219 VCC, DS3231 VCC, DS18B20 VDD | red |
| `GND` | INA219 GND, DS3231 GND, DS18B20 GND, divider bottom, caps | black |
| `GPIO1` (ADC1_C2, pin 6) | divider midpoint (10 kΩ→battery+, 10 kΩ→GND) | white |
| `GPIO8` (I2C SDA, pin 13) | INA219 SDA, DS3231 SDA | yellow |
| `GPIO9` (I2C SCL, pin 14) | INA219 SCL, DS3231 SCL | green |
| `GPIO10` (pin 15) | DS18B20 data (4.7 kΩ pull-up to 3V3) | blue |
| INA219 `VIN+`/`VIN−` | in series with battery positive lead | thick |
| Battery `−` | DevKitC GND (common ground) | black |
| DS3231 `VBAT`/`BAT+` | CR1220 + | |
| 100 nF | 3V3–GND near header; 100 µF across power rails | |

Pin numbers (13/14/15) are DevKitC header positions; the names `GPIO8/9/10`
are what the firmware uses. Verify with the silkscreen on the devkit.

Battery voltage 4.2 V max → 2.1 V at ADC after 2:1 divider, safely inside
the 0–3.3 V range (`ADC_ATTEN 11db` in firmware).

## Build Order

1. Solder header pins on prototyping side of the protoboard if using a
   breakout-friendly board; otherwise insert DevKitC directly.
2. Mount both I2C breakouts + DS18B20; wire 3V3/GND rails first.
3. I2C bus: join SDA (GPIO8) and SCL (GPIO9) to both modules. The breakouts
   carry their own pull-ups; do not add extra 4.7 kΩ on I2C.
4. OneWire: data line on GPIO10, 4.7 kΩ pull-up to 3V3.
5. Divider: 10 kΩ from battery+ (VIN+ node) to GPIO1, 10 kΩ from GPIO1 to GND.
6. Power: INA219 VIN+ ← battery +, VIN− ← battery −; battery − also to
   DevKitC GND.

## Firmware

Arduino variant (`arduino_firmware/`, PlatformIO, web dashboard):

```sh
cd arduino_firmware
pio run -t upload
```

AP mode fallback: device creates `battery-predictor-XXXX` SSID; web
dashboard at `http://192.168.4.1` or mDNS `http://battery-predictor.local`.

The firmware now times inference and reports it:

- Serial at end of each cycle: inference is in the cycle log line.
- Web/JSON endpoint `GET /status` returns `infer_us` — single-inference
  latency in microseconds.
- Re-calibrate button starts a fresh 10-cycle SOH baseline.

## Validation Protocol (paper Section IV-H)

1. Connect battery; let 10 calibration cycles complete (auto-detected by
   current sign) so SOH baseline is set.
2. Discharge the cell; collect at least 50 cycles or 3 h of data.
3. Record per-inference latency from `GET /status` (`infer_us`) for each of
   the three models (swap via UART command or dashboard button).
4. Download the CSV log from the dashboard. Compare predictions V~S~
   pyTorch-free reference from `pc_validation/full_validate.py` output to
   confirm the C engine matches within 1×10⁻⁶.
5. Report the measured inference latency in Table V (replacing the
   "(proj.)" column) and the end-to-end cycle-loop time (sensor read +
   feature build + inference) from the serial log as the real deployment
   overhead.

Expected: ~5–8 µs per single-row inference (P~C~ numbers in the paper are
PC-only; the ESP32-S3 runs at 240 MHz so single-row latency should be well
under 600 µs of runtime per 1,028-row batch equivalent — measure, don't
assume).