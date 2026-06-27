/**
 * ESP32 Battery Failure Predictor — Tree Model Inference
 *
 * State machine:
 *   INIT → CALIBRATE (10 cycles) → MONITOR (continuous)
 *
 * UART commands (115200 baud):
 *   "MODEL 0" — XGBoost
 *   "MODEL 1" — LightGBM
 *   "MODEL 2" — Random Forest
 *   "STATUS"  — current model + calibration state
 *   "P_THRESHOLD 0.5" — set alert threshold (0.0–1.0)
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/uart.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "esp_partition.h"
#include "esp_spi_flash.h"

#include "components/tree_engine/tree_engine.h"
#include "components/sensors/sensors.h"
#include "components/feature_extractor/feature_extractor.h"
#include "model_manifest.h"  /* Compile-time model metadata for sanity checks */

static const char *TAG = "predictor";

/* ── UART config ──────────────────────────────────────────────────────── */
#define UART_PORT   UART_NUM_0
#define BUF_SIZE    256

static void uart_init(void) {
    uart_config_t cfg = {
        .baud_rate = 115200,
        .data_bits = UART_DATA_8_BITS,
        .parity    = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
    };
    uart_param_config(UART_PORT, &cfg);
    uart_driver_install(UART_PORT, BUF_SIZE, 0, 0, NULL, 0);
}

static void uart_puts(const char *s) {
    uart_write_bytes(UART_PORT, s, strlen(s));
    uart_write_bytes(UART_PORT, "\r\n", 2);
}

static void uart_printf(const char *fmt, ...) {
    char buf[256];
    va_list args;
    va_start(args, fmt);
    vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);
    uart_puts(buf);
}

/* ── State machine ────────────────────────────────────────────────────── */
typedef enum {
    STATE_INIT,
    STATE_CALIBRATE,
    STATE_MONITOR,
} state_t;

static state_t state = STATE_INIT;
static uint32_t cycle_count = 0;
static model_id_t active_model = MODEL_XGBOOST;
static float alert_threshold = 0.5f;  /* P_THRESHOLD-controllable alert level */

/* ── Load trees.bin from flash partition ──────────────────────────────── */
static int load_model_binary(void) {
    const esp_partition_t *part = esp_partition_find_first(
        ESP_PARTITION_TYPE_DATA, ESP_PARTITION_SUBTYPE_ANY, "model");
    if (!part) {
        ESP_LOGE(TAG, "Model partition not found");
        return -1;
    }

    uint8_t *buf = heap_caps_malloc(part->size, MALLOC_CAP_SPIRAM);
    if (!buf) {
        ESP_LOGE(TAG, "Failed to allocate %lu bytes in PSRAM", (unsigned long)part->size);
        return -1;
    }

    esp_err_t ret = esp_partition_read(part, 0, buf, part->size);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to read model partition: %s", esp_err_to_name(ret));
        heap_caps_free(buf);
        return -1;
    }

    ret = tree_engine_init(buf, part->size);
    if (ret != 0) {
        ESP_LOGE(TAG, "tree_engine_init failed: %d", ret);
        heap_caps_free(buf);
        return -1;
    }

    /* Sanity check: verify the binary's per-model metadata matches the
     * compile-time manifest in model_manifest.h. Catches stale trees.bin
     * flashed against a newer firmware (or vice versa). */
    for (int m = 0; m < MANIFEST_N_MODELS; m++) {
        tree_engine_select((model_id_t)m);
        unsigned int n_trees = tree_engine_n_trees();
        if (n_trees != MODEL_META[m].n_trees) {
            ESP_LOGW(TAG, "Manifest mismatch for model %d: binary has %u trees, manifest expects %u",
                     m, n_trees, MODEL_META[m].n_trees);
        }
    }
    tree_engine_select(active_model);  /* restore */

    ESP_LOGI(TAG, "Model loaded: %lu bytes in PSRAM", (unsigned long)part->size);
    return 0;
}

/* ── Process UART commands ────────────────────────────────────────────── */
static void process_uart(void) {
    uint8_t data[BUF_SIZE];
    int len = uart_read_bytes(UART_PORT, data, BUF_SIZE - 1, 0);
    if (len <= 0) return;

    data[len] = '\0';
    char *line = (char *)data;

    /* Remove trailing newline */
    size_t sl = strlen(line);
    while (sl > 0 && (line[sl-1] == '\n' || line[sl-1] == '\r')) line[--sl] = '\0';

    if (strncmp(line, "MODEL ", 6) == 0) {
        int m = atoi(line + 6);
        if (m >= MODEL_XGBOOST && m <= MODEL_RANDOM_FOREST) {
            active_model = (model_id_t)m;
            tree_engine_select(active_model);
            uart_printf("SWITCHED TO %s", tree_engine_model_name());
        } else {
            uart_printf("INVALID MODEL %d (use 0=XGBoost, 1=LightGBM, 2=RF)", m);
        }
    } else if (strncmp(line, "P_THRESHOLD ", 12) == 0) {
        float t = strtof(line + 12, NULL);
        if (t >= 0.0f && t <= 1.0f) {
            alert_threshold = t;
            uart_printf("P_THRESHOLD=%.4f", alert_threshold);
        } else {
            uart_printf("INVALID P_THRESHOLD %.4f (must be in [0,1])", t);
        }
    } else if (strcmp(line, "STATUS") == 0) {
        uart_printf("MODEL=%s CYCLE=%lu STATE=%s CALIBRATED=%s P_THRESHOLD=%.4f",
                     tree_engine_model_name(),
                     (unsigned long)cycle_count,
                     state == STATE_CALIBRATE ? "CALIBRATE" : "MONITOR",
                     soh_is_calibrated() ? "YES" : "NO",
                     alert_threshold);
        if (!soh_is_calibrated()) {
            uart_printf("CALIBRATION_REMAINING=%lu",
                        (unsigned long)soh_calibration_cycles_remaining());
        }
    }
}

/* ── Main application task ────────────────────────────────────────────── */
static void predictor_task(void *arg) {
    uart_puts("Battery Failure Predictor v1.0");
    uart_puts("Models: XGBoost, LightGBM, Random Forest — 300 trees each");
    uart_puts("Send MODEL 0/1/2 to switch, STATUS for info");
    uart_puts("---");

    while (1) {
        process_uart();

        switch (state) {
            case STATE_INIT: {
                /* Wait for first discharge cycle detection */
                /* In practice: INA219 detects discharge by negative current */
                sensors_start_cycle();
                state = STATE_CALIBRATE;
                uart_puts("STATE=CALIBRATE (first 10 cycles for SOH baseline)");
                break;
            }

            case STATE_CALIBRATE:
            case STATE_MONITOR: {
                /* Simulate per-cycle sampling */
                /* In real use: IRQ or periodic task calls sensors_sample()
                 * during discharge, then sensors_end_cycle() when discharge ends.
                 * For this simulation, we call it as a single cycle. */

                /* Simulate a discharge cycle */
                for (int sample = 0; sample < 10; sample++) {
                    sensors_sample();
                    vTaskDelay(pdMS_TO_TICKS(100)); /* 10 Hz sampling */
                }

                /* End the cycle and accumulate sensor readings. */
                cycle_data_t cycle = sensors_end_cycle();
                cycle.cycle_num = ++cycle_count;

                /* Record this cycle's capacity BEFORE extract_features() reads
                 * SOH. Previously, sensors_end_cycle() called soh_get_value()
                 * internally to populate cycle.soh, and soh_record_cycle() was
                 * called afterwards — so every prediction used the *previous*
                 * cycle's SOH. Calling soh_record_cycle() first ensures
                 * extract_features() sees the current cycle's SOH. */
                soh_record_cycle(cycle.capacity_ah);
                cycle.soh = soh_get_value();  /* refresh cached value */

                /* Build features and predict */
                model_features_t feats = extract_features(&cycle);
                float prob = tree_engine_predict((float[7]){
                    feats.cycle, feats.avg_voltage, feats.min_voltage,
                    feats.avg_current, feats.avg_temp, feats.duration, feats.SOH
                });

                /* Report */
                uint32_t cal_rem = soh_calibration_cycles_remaining();
                uart_printf("CYCLE %lu | MODEL %s | P=%.6f | SOH=%.4f | V=%.3f | I=%.3f | T=%.1f | CAL_REM=%lu",
                            (unsigned long)cycle_count,
                            tree_engine_model_name(),
                            prob,
                            cycle.soh,
                            cycle.voltage_avg,
                            cycle.current_avg,
                            cycle.temp_avg,
                            (unsigned long)cal_rem);

                /* Threshold-based alert */
                if (state == STATE_MONITOR && prob >= alert_threshold) {
                    uart_printf("ALERT: P=%.6f >= threshold %.4f (cycle %lu)",
                                prob, alert_threshold, (unsigned long)cycle_count);
                }

                /* Transition to MONITOR after calibration */
                if (state == STATE_CALIBRATE && soh_is_calibrated()) {
                    state = STATE_MONITOR;
                    uart_puts("STATE=MONITOR (SOH calibrated, full operation)");
                }

                /* Start next cycle */
                sensors_start_cycle();
                break;
            }
        }

        vTaskDelay(pdMS_TO_TICKS(1000)); /* Wait between cycles */
    }
}

/* ── Entry point ──────────────────────────────────────────────────────── */
void app_main(void) {
    uart_init();
    ESP_LOGI(TAG, "Starting...");

    /* Initialize sensors */
    sensors_init();

    /* Load model binary from flash */
    if (load_model_binary() != 0) {
        ESP_LOGE(TAG, "Failed to load model, halting");
        return;
    }

    /* Set nominal capacity (adjust per battery type) */
    soh_set_nominal_capacity(2.0f); /* 18650 typical */

    /* Start prediction task */
    xTaskCreate(predictor_task, "predictor", 8192, NULL, 5, NULL);
}
