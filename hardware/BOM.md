# BOM — Battery Predictor Sensor Shield

## Required Components

| Ref | Part | Package | Qty | Notes |
|-----|------|---------|-----|-------|
| R1, R2 | 10kΩ 1% | Axial THT (or 0805) | 2 | Voltage divider |
| R3, R4, R5 | 4.7kΩ 5% | Axial THT | 3 | I2C + OneWire pullups |
| RS | 0.1Ω 1% 1W | Axial THT (or 2512) | 1 | Current shunt |
| RLED | 1kΩ 5% | Axial THT | 1 | LED current limit |
| C1, C3 | 100nF ceramic | 5mm pitch THT | 2 | Bypass caps |
| C2 | 100μF 16V electrolytic | 5mm radial THT | 1 | Bulk decoupling |
| D1 | LED 3mm green | 3mm THT | 1 | Power indicator |
| U1 | INA219 | SOIC-8 | 1 | Current sensor |
| U2 | DS3231 | SOIC-16W | 1 | RTC |
| U3 | DS18B20 | TO-92 | 1 | Temperature sensor |
| Y1 | 32.768kHz crystal | 3.2×1.5mm SMD | 1 | DS3231 timekeeping |
| BT1 | CR1220 holder | SMD | 1 | RTC backup battery |
| J1 | 2×19 female header | 2.54mm pitch | 1 | ESP32-S3-DevKitC-1 connector |
| J2, J3 | 2-pin screw terminal | 5.08mm pitch | 2 | Battery in, load out |
| J4 | 3-pin screw terminal | 5.08mm pitch | 1 | External temp probe |

## Also Needed

| Item | Notes |
|------|-------|
| ESP32-S3-DevKitC-1 | Plugs into J1 |
| CR1220 battery | RTC backup |
| 18650 battery (or test cell) | Battery under test |
| DS18B40 probe (optional) | External temp sensor |
| Jumper wires or 2.54mm header pins | If not using DevKit directly |

## Optional

| Item | Notes |
|------|-------|
| 4× M3 nylon standoffs + screws | Mounting |
