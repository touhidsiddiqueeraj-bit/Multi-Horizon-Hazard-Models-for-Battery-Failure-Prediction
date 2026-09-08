#include "sensors.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "esp_log.h"

static const char *TAG = "voltage";
static adc_oneshot_unit_handle_t adc_handle = NULL;
static adc_cali_handle_t cali_handle = NULL;
static bool cali_done = false;

/* Voltage divider: R1=10k, R2=10k → factor = (R1+R2)/R2 = 2.0 */
#define VOLTAGE_DIVIDER_FACTOR  2.0f

/* ADC attenuation for 0–3.3V input range */
#define ADC_ATTEN  ADC_ATTEN_DB_12

void voltage_init(void) {
    adc_oneshot_unit_init_cfg_t unit_cfg = {
        .unit_id = ADC_UNIT_1,
    };
    ESP_ERROR_CHECK(adc_oneshot_new_unit(&unit_cfg, &adc_handle));

    adc_oneshot_chan_cfg_t chan_cfg = {
        .atten = ADC_ATTEN,
        .bitwidth = ADC_BITWIDTH_12,
    };
    ESP_ERROR_CHECK(adc_oneshot_config_channel(adc_handle, PIN_VOLTAGE_ADC, &chan_cfg));

    /* Calibration (curve fitting or eFuse) */
    adc_cali_curve_fitting_config_t cali_cfg = {
        .unit_id = ADC_UNIT_1,
        .atten = ADC_ATTEN,
        .bitwidth = ADC_BITWIDTH_12,
    };
    esp_err_t ret = adc_cali_create_scheme_curve_fitting(&cali_cfg, &cali_handle);
    cali_done = (ret == ESP_OK);
    if (!cali_done) {
        ESP_LOGW(TAG, "ADC calibration not available, using raw conversion");
    }
}

float voltage_read(void) {
    int raw = 0;
    ESP_ERROR_CHECK(adc_oneshot_read(adc_handle, PIN_VOLTAGE_ADC, &raw));

    float voltage_mv;
    if (cali_done) {
        ESP_ERROR_CHECK(adc_cali_raw_to_voltage(cali_handle, raw, (int *)&voltage_mv));
    } else {
        /* Raw estimate: raw * 3.3V / 4095 * 1000 */
        voltage_mv = (float)raw * 3300.0f / 4095.0f;
    }
    return voltage_mv / 1000.0f * VOLTAGE_DIVIDER_FACTOR;
}
