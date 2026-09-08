/**
 * @file sensors.h
 * @brief Battery sensor abstraction for ESP32-S3
 *
 * Pin assignments and cycle-level data aggregation for:
 *   - Voltage divider (ADC1_CH0, GPIO1)
 *   - INA219 current sensor (I2C, addr 0x40)
 *   - DS18B20 temperature sensor (OneWire, GPIO10)
 *   - DS3231 RTC (I2C, addr 0x68)
 *
 * Usage:
 * @code
 *   sensors_init();
 *   while (discharging) {
 *       sensors_start_cycle();      // new discharge detected
 *       while (still_discharging) {
 *           sensors_sample();       // 10 Hz
 *       }
 *       cycle_data_t cd = sensors_end_cycle();  // aggregated data
 *       float prob = tree_engine_predict(...);
 *   }
 * @endcode
 */
#ifndef SENSORS_H
#define SENSORS_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ── Pin assignments (ESP32-S3 DevKit) ────────────────────────────────── */
#define PIN_VOLTAGE_ADC   ADC_CHANNEL_0  /* GPIO1  — voltage divider */
#define PIN_CURRENT_SDA   GPIO_NUM_8     /* I2C SDA — INA219 + DS3231 */
#define PIN_CURRENT_SCL   GPIO_NUM_9     /* I2C SCL */
#define PIN_TEMP_ONEWIRE  GPIO_NUM_10    /* OneWire — DS18B20 (RMT TX) */
#define INA219_ADDR       0x40           /* I2C address */
#define DS3231_ADDR       0x68           /* I2C address */

/**
 * @brief Per-cycle sensor data (one record per discharge cycle)
 */
typedef struct {
    uint32_t cycle_num;          /**< Cycle counter */
    float    voltage_avg;        /**< V — average during discharge */
    float    voltage_min;        /**< V — minimum during discharge */
    float    current_avg;        /**< A — average during discharge */
    float    temp_avg;           /**< °C — average during discharge */
    float    duration_sec;       /**< s — discharge duration */
    float    capacity_ah;        /**< Ah — Coulomb count for this cycle */
    float    soh;                /**< State of Health (current/nominal) */
} cycle_data_t;

/**
 * @brief Initialize all sensor drivers.
 * Configures ADC, I2C (INA219 + DS3231), and OneWire (DS18B20 via RMT).
 */
void sensors_init(void);

/**
 * @brief Begin a new discharge cycle.
 * Resets internal accumulators and records the start timestamp from RTC.
 */
void sensors_start_cycle(void);

/**
 * @brief Sample all sensors and accumulate into cycle data.
 * Call at ~10 Hz during discharge. Records voltage, current, temperature
 * and performs Coulomb counting (dt = 100 ms assumed).
 */
void sensors_sample(void);

/**
 * @brief End discharge cycle, compute aggregates.
 * @return cycle_data_t with averaged/minimum values, capacity, SOH.
 */
cycle_data_t sensors_end_cycle(void);

/* ── SOH calibration helpers ──────────────────────────────────────────── */

/** @brief Set nominal battery capacity in Ah (default: 2.0 for 18650) */
void   soh_set_nominal_capacity(float capacity_ah);

/** @return Current nominal capacity in Ah */
float  soh_get_nominal_capacity(void);

/** @return true if calibration window (10 cycles) is complete */
bool   soh_is_calibrated(void);

/** @return Number of calibration cycles remaining */
uint32_t soh_calibration_cycles_remaining(void);

#ifdef __cplusplus
}
#endif

#endif /* SENSORS_H */
