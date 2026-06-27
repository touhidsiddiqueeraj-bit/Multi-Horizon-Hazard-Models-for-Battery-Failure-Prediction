#include "sensors.h"
#include "driver/i2c.h"
#include "esp_log.h"

static const char *TAG = "rtc";
static bool rtc_ok = false;

/* DS3231 registers */
#define DS3231_REG_SEC   0x00
#define DS3231_REG_MIN   0x01
#define DS3231_REG_HOUR  0x02

#define I2C_TIMEOUT_MS   100

static uint8_t bcd2bin(uint8_t bcd) {
    return (bcd >> 4) * 10 + (bcd & 0x0F);
}

void rtc_init(void) {
    /* I2C is already initialized by current_init() */
    /* Verify DS3231 presence */
    uint8_t reg = DS3231_REG_SEC;
    esp_err_t ret = i2c_master_write_to_device(I2C_NUM_0, DS3231_ADDR, &reg, 1,
                                                I2C_TIMEOUT_MS / portTICK_PERIOD_MS);
    rtc_ok = (ret == ESP_OK);
    if (rtc_ok) {
        ESP_LOGI(TAG, "DS3231 detected");
    } else {
        ESP_LOGW(TAG, "DS3231 not found");
    }
}

bool rtc_get_time(uint32_t *seconds) {
    if (!rtc_ok) return false;
    uint8_t reg = DS3231_REG_SEC;
    uint8_t buf[3];
    esp_err_t ret = i2c_master_write_read_device(I2C_NUM_0, DS3231_ADDR, &reg, 1,
                                                  buf, 3, I2C_TIMEOUT_MS / portTICK_PERIOD_MS);
    if (ret != ESP_OK) return false;

    uint8_t sec = bcd2bin(buf[0]);
    uint8_t min = bcd2bin(buf[1]);
    uint8_t hour = bcd2bin(buf[2]);
    *seconds = (uint32_t)hour * 3600 + (uint32_t)min * 60 + sec;
    return true;
}
