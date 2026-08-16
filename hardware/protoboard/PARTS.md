# Parts List — Battery Predictor Prototype (Breadboard, ৳2,404 / ~$20)

No PCB. Everything plugs into a half-size breadboard around an
ESP32-S3-DevKitC-1. Prices are Bangladesh retail (BDT), current as of
Aug 2026; see `parts_bd.csv` for store links.

## Required

| Ref | Part | Qty | Purpose | ~Price (BDT) |
|-----|------|:---:|---------|-------------:|
| U0 | ESP32-S3-DevKitC-1 (N16R8) | 1 | Main board (WiFi + BLE, 240 MHz, PSRAM) | 1,250 |
| U1 | INA219 current sensor breakout | 1 | Current (I2C addr 0x40, 0.1 Ω shunt) | 214 |
| U2 | DS3231 RTC breakout | 1 | Timestamps (I2C addr 0x68, coin-cell holder) | 250 |
| U3 | DS18B20 (TO-92) | 1 | Temperature (OneWire) | 95 |
| R1, R2 | 10 kΩ resistor, 1/4 W | 2 | 2:1 voltage divider | 15 (pack of 10) |
| R3 | 4.7 kΩ resistor, 1/4 W | 1 | OneWire pull-up to 3V3 | 15 (pack of 10) |
| BB | Breadboard, half-size (400 tie) | 1 | Prototype base | 90 |
| JW | Jumper wires M–M 40 pcs + a few M–F | 1 set | Wiring | 100 |
| C1, C2 | 100 nF + 100 µF 16 V caps | 1 each | 3V3 rail decoupling (optional) | 20 |
| BT | CR2032 coin cell | 1 | DS3231 backup (usually included) | 40 |
| BATT | 18650 cell + single holder | 1 | Battery under test (or lab supply) | 300 |

**Total ≈ ৳2,404 (~$20)** — matches the paper's "~$25" budget once
shipping and a spare cell are included.

## Optional

| Ref | Part | Purpose |
|-----|------|---------|
| — | LED 3 mm + 1 kΩ resistor | Power indicator |

## Notes

- **Board variant.** BD retailers mostly stock the **N16R8** DevKitC-1
  (16 MB flash / 8 MB PSRAM). Both N8R8 and N16R8 work with the firmware.
- **Breakout modules carry their own I2C pull-ups.** Do not add extra
  4.7 kΩ on SDA/SCL — only the DS18B20 data line needs its 4.7 kΩ pull-up.
- **Divider.** 10 kΩ + 10 kΩ (2:1). Battery+ 4.2 V → 2.1 V at GPIO1 ADC.
  This matches the firmware (`VOLTAGE_DIVIDER_RATIO = 2.0`).
- **Coin cell.** The common DS3231 module (ZS-042) uses a CR2032 holder.
  The earlier BOM listed CR1220; CR2032 is the standard fit.
- **18650.** Any ~3.7 V cell works as the device under test; for the SOH
  baseline a known-good ~2000 mAh+ cell is preferable. The 0.1 Ω shunt in
  the INA219 sets a ~3.2 A max — fine for 1C–2C 18650 discharge.
