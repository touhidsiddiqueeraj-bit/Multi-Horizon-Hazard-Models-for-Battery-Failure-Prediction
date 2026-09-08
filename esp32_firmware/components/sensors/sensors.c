#include "sensors.h"
#include <math.h>
#include "esp_log.h"

static const char *TAG = "sensors";
/* External sensor driver functions */
extern void voltage_init(void);
extern float voltage_read(void);
extern void current_init(void);
extern float current_read_amps(void);
extern void temp_init(void);
extern float temp_read_celsius(void);
extern void rtc_init(void);
extern bool rtc_get_time(uint32_t *seconds);
extern void soh_record_cycle(float capacity_ah);
extern float soh_get_value(void);
extern void soh_record_cycle(float capacity_ah);
extern float soh_get_value(void);

/* Per-cycle accumulation */
static struct {
    bool    active;
    uint32_t start_time;
    float   voltage_sum;
    float   voltage_min;
    float   current_sum;
    float   temp_sum;
    int     sample_count;
    float   capacity_ah;   /* Coulomb count */
} cycle = {0};

/* Previous current for discharge detection */
static float prev_current = 0.0f;

void sensors_init(void) {
    voltage_init();
    current_init();
    temp_init();
    rtc_init();
    ESP_LOGI(TAG, "All sensors initialized");
}

void sensors_start_cycle(void) {
    cycle.active = true;
    rtc_get_time(&cycle.start_time);
    cycle.voltage_sum = 0.0f;
    cycle.voltage_min = 999.0f;
    cycle.current_sum = 0.0f;
    cycle.temp_sum = 0.0f;
    cycle.sample_count = 0;
    cycle.capacity_ah = 0.0f;
}

void sensors_sample(void) {
    if (!cycle.active) return;

    float v = voltage_read();
    float i = current_read_amps();
    float t = temp_read_celsius();

    cycle.voltage_sum += v;
    if (v < cycle.voltage_min) cycle.voltage_min = v;
    cycle.current_sum += i;
    cycle.temp_sum += t;
    cycle.sample_count++;

    /* Coulomb counting: i * dt (assuming 100ms between samples) */
    cycle.capacity_ah += i * (100.0f / 3600.0f); /* 100ms in hours */
}

cycle_data_t sensors_end_cycle(void) {
    uint32_t end_time = 0;
    rtc_get_time(&end_time);

    cycle_data_t result = {0};

    if (cycle.sample_count > 0) {
        result.voltage_avg = cycle.voltage_sum / (float)cycle.sample_count;
        result.voltage_min = cycle.voltage_min;
        result.current_avg = cycle.current_sum / (float)cycle.sample_count;
        result.temp_avg    = cycle.temp_sum / (float)cycle.sample_count;
        result.capacity_ah = fabsf(cycle.capacity_ah);  /* Absolute value */
    }

    result.duration_sec = (float)(end_time - cycle.start_time);
    result.cycle_num = 0;  /* Set by caller */
    result.soh = soh_get_value();

    cycle.active = false;
    return result;
}
