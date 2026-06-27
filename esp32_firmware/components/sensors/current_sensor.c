#include "sensors.h"
#include "driver/i2c.h"
#include "esp_log.h"

static const char *TAG = "current";
static bool i2c_ok = false;

/* INA219 registers */
#define INA219_REG_CONFIG  0x00
#define INA219_REG_SHUNT   0x01  /* mV shunt voltage */
#define INA219_REG_BUS     0x02  /* mV bus voltage */
#define INA219_REG_POWER   0x03
#define INA219_REG_CURRENT 0x04  /* mA */
#define INA219_REG_CALIB   0x05

/* INA219 config: 32V bus range, ±2A shunt range (matches Arduino firmware's
 * setCalibration_32V_2A). The previous 32V/320mA range saturated on real
 * 18650 discharges (~2A). 32V/2A uses config 0x2000 | shunt_adc_12bit
 * (12-bit, 532us conversion) = 0x219F for the CONFIG register, and a
 * calibration register of 4096 to give 0.1mA per LSB on a 0.1Ω shunt. */
#define INA219_CONFIG_VAL  0x219F
#define INA219_CALIB_VAL   4096

/* I2C master config */
#define I2C_MASTER_FREQ_HZ 100000
#define I2C_TIMEOUT_MS     100

static esp_err_t i2c_write_reg(uint8_t addr, uint8_t reg, uint16_t val) {
    uint8_t buf[3] = {reg, (uint8_t)(val >> 8), (uint8_t)(val & 0xFF)};
    return i2c_master_write_to_device(I2C_NUM_0, addr, buf, 3, I2C_TIMEOUT_MS / portTICK_PERIOD_MS);
}

static esp_err_t i2c_read_reg(uint8_t addr, uint8_t reg, uint16_t *val) {
    esp_err_t ret = i2c_master_write_to_device(I2C_NUM_0, addr, &reg, 1, I2C_TIMEOUT_MS / portTICK_PERIOD_MS);
    if (ret != ESP_OK) return ret;
    uint8_t buf[2];
    ret = i2c_master_read_from_device(I2C_NUM_0, addr, buf, 2, I2C_TIMEOUT_MS / portTICK_PERIOD_MS);
    if (ret == ESP_OK) *val = ((uint16_t)buf[0] << 8) | buf[1];
    return ret;
}

void current_init(void) {
    i2c_config_t conf = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = PIN_CURRENT_SDA,
        .scl_io_num = PIN_CURRENT_SCL,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = I2C_MASTER_FREQ_HZ,
    };
    ESP_ERROR_CHECK(i2c_param_config(I2C_NUM_0, &conf));
    ESP_ERROR_CHECK(i2c_driver_install(I2C_NUM_0, I2C_MODE_MASTER, 0, 0, 0));

    /* Configure INA219 */
    esp_err_t ret = i2c_write_reg(INA219_ADDR, INA219_REG_CONFIG, INA219_CONFIG_VAL);
    if (ret == ESP_OK) {
        /* Calibration for ±2A range (matches Arduino firmware). */
        i2c_write_reg(INA219_ADDR, INA219_REG_CALIB, INA219_CALIB_VAL);
        i2c_ok = true;
        ESP_LOGI(TAG, "INA219 detected (32V/2A range)");
    } else {
        ESP_LOGW(TAG, "INA219 not found (I2C 0x%02X)", INA219_ADDR);
    }
}

float current_read_amps(void) {
    if (!i2c_ok) return 0.0f;
    uint16_t raw;
    esp_err_t ret = i2c_read_reg(INA219_ADDR, INA219_REG_CURRENT, &raw);
    if (ret != ESP_OK) return 0.0f;
    /* INA219 current register: mA, signed int16 */
    int16_t ma = (int16_t)raw;
    return (float)ma / 1000.0f;
}

float voltage_read_bus(void) {
    if (!i2c_ok) return 0.0f;
    uint16_t raw;
    esp_err_t ret = i2c_read_reg(INA219_ADDR, INA219_REG_BUS, &raw);
    if (ret != ESP_OK) return 0.0f;
    /* Bus voltage: mV, 4mV per LSB (shift right 3) */
    return (float)(raw >> 3) * 0.004f;
}
