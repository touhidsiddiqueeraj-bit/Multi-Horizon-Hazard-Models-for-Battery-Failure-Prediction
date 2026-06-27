#include "sensors.h"
#include "esp_log.h"

static const char *TAG = "soh";

#define CALIBRATION_CYCLES  10  /* First N cycles to establish baseline */
#define NOMINAL_CAPACITY_AH 2.0f /* Default nominal capacity (adjust per battery) */

static float nominal_capacity_ah = NOMINAL_CAPACITY_AH;
static float baseline_sum = 0.0f;
static uint32_t baseline_count = 0;
static float current_soh = 1.0f;

void soh_set_nominal_capacity(float capacity_ah) {
    nominal_capacity_ah = capacity_ah;
    ESP_LOGI(TAG, "Nominal capacity set to %.3f Ah", capacity_ah);
}

float soh_get_nominal_capacity(void) {
    return nominal_capacity_ah;
}

bool soh_is_calibrated(void) {
    return baseline_count >= CALIBRATION_CYCLES;
}

uint32_t soh_calibration_cycles_remaining(void) {
    if (baseline_count >= CALIBRATION_CYCLES) return 0;
    return CALIBRATION_CYCLES - baseline_count;
}

void soh_record_cycle(float capacity_ah) {
    if (baseline_count < CALIBRATION_CYCLES) {
        baseline_sum += capacity_ah;
        baseline_count++;
        ESP_LOGI(TAG, "Calibration cycle %lu/%d: capacity=%.3f Ah",
                 (unsigned long)baseline_count, CALIBRATION_CYCLES, capacity_ah);
    }

    /* Use the actual number of accumulated baseline cycles as the divisor so
     * SOH is correctly normalised during the first CALIBRATION_CYCLES-1 cycles.
     * Previously this always divided by CALIBRATION_CYCLES, which made the
     * baseline artificially low (and thus SOH artificially high) during the
     * early calibration window. */
    if (baseline_count == 0) return;
    float baseline = baseline_sum / (float)baseline_count;
    if (baseline > 0.0f) {
        current_soh = capacity_ah / baseline;
        if (current_soh > 1.2f) current_soh = 1.2f;
        if (current_soh < 0.0f) current_soh = 0.0f;
    }
}

float soh_get_value(void) {
    return current_soh;
}
