/**
 * DS18B20 temperature sensor driver using RMT TX + GPIO polling.
 *
 * RMT TX generates precise OneWire timing pulses immune to FreeRTOS
 * scheduler preemption. GPIO input reads device response bits.
 *
 * Pin: GPIO_NUM_10 (open-drain with 4.7kΩ pullup to 3.3V)
 *
 * ESP-IDF v5.x RMT API used (driver/rmt_tx.h + driver/gpio.h)
 */
#include "sensors.h"
#include "driver/rmt_tx.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "temp";
static bool ds18b20_present = false;

/* RMT TX channel handle */
static rmt_channel_handle_t tx_chan = NULL;
static rmt_encoder_handle_t copy_encoder = NULL;

/* RMT resolution: 1 MHz → 1 μs per tick */
#define RMT_RES_HZ 1000000

/* OneWire timing (μs) */
#define OW_RESET_LOW_US   480
#define OW_RESET_HIGH_US  480
#define OW_SLOT_US         60
#define OW_WRITE1_LOW_US    6
#define OW_WRITE1_HIGH_US  64
#define OW_WRITE0_LOW_US   60
#define OW_WRITE0_HIGH_US   6
#define OW_READ_LOW_US      6
#define OW_READ_SAMPLE_US   8

static void ow_gpio_init(void) {
    gpio_config_t cfg = {
        .pin_bit_mask = 1ULL << PIN_TEMP_ONEWIRE,
        .mode = GPIO_MODE_INPUT_OUTPUT_OD,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&cfg);
    gpio_set_level(PIN_TEMP_ONEWIRE, 1);
}

static void ow_rmt_tx_init(void) {
    rmt_tx_channel_config_t tx_cfg = {
        .gpio_num = PIN_TEMP_ONEWIRE,
        .clk_src = RMT_CLK_SRC_DEFAULT,
        .resolution_hz = RMT_RES_HZ,
        .mem_block_symbols = 64,
        .trans_queue_depth = 4,
        .flags.invert_out = false,
        .flags.with_dma = false,
        .flags.io_loop_back = false,
        .flags.io_od_mode = true,  /* open-drain */
    };
    ESP_ERROR_CHECK(rmt_new_tx_channel(&tx_cfg, &tx_chan));

    rmt_copy_encoder_config_t enc_cfg = {};
    ESP_ERROR_CHECK(rmt_new_copy_encoder(&enc_cfg, &copy_encoder));

    ESP_ERROR_CHECK(rmt_enable(tx_chan));
}

static void ow_send_items(const rmt_symbol_word_t *items, size_t count, TickType_t wait_ticks) {
    rmt_transmit_config_t cfg = {
        .loop_count = -1,  /* no loop */
        .flags.eot_level = 1,  /* bus idle high */
    };
    ESP_ERROR_CHECK(rmt_transmit(tx_chan, copy_encoder, items, count * sizeof(rmt_symbol_word_t), &cfg));
    ESP_ERROR_CHECK(rmt_tx_wait_all_done(tx_chan, wait_ticks));
}

static void ow_blocking_write_byte(uint8_t byte) {
    rmt_symbol_word_t items[8];

    for (int i = 0; i < 8; i++) {
        if (byte & (1 << i)) {
            /* Write-1 slot */
            items[i] = (rmt_symbol_word_t){
                .duration0 = OW_WRITE1_LOW_US,
                .level0 = 0,
                .duration1 = OW_WRITE1_HIGH_US,
                .level1 = 1,
            };
        } else {
            /* Write-0 slot */
            items[i] = (rmt_symbol_word_t){
                .duration0 = OW_WRITE0_LOW_US,
                .level0 = 0,
                .duration1 = OW_WRITE0_HIGH_US,
                .level1 = 1,
            };
        }
    }

    ow_send_items(items, 8, pdMS_TO_TICKS(10));
}

static uint8_t ow_blocking_read_byte(void) {
    uint8_t result = 0;

    for (int i = 0; i < 8; i++) {
        /* Send read-pulse via RMT */
        rmt_symbol_word_t read_pulse = {
            .duration0 = OW_READ_LOW_US,
            .level0 = 0,
            .duration1 = 1,
            .level1 = 1,
        };
        ow_send_items(&read_pulse, 1, pdMS_TO_TICKS(1));

        /* Small delay then sample on GPIO */
        esp_rom_delay_us(OW_READ_SAMPLE_US);
        int bit = gpio_get_level(PIN_TEMP_ONEWIRE);

        if (bit) {
            result |= (1 << i);
        }

        /* Wait for remaining slot time */
        esp_rom_delay_us(OW_SLOT_US - OW_READ_LOW_US - OW_READ_SAMPLE_US);
    }

    return result;
}

static bool ow_reset(void) {
    rmt_symbol_word_t reset_pulse = {
        .duration0 = OW_RESET_LOW_US,
        .level0 = 0,
        .duration1 = OW_RESET_HIGH_US,
        .level1 = 1,
    };
    ow_send_items(&reset_pulse, 1, pdMS_TO_TICKS(2));

    /* Sample presence pulse: device pulls low within ~70μs of release */
    esp_rom_delay_us(70);
    int presence = (gpio_get_level(PIN_TEMP_ONEWIRE) == 0);

    esp_rom_delay_us(OW_RESET_HIGH_US - 70);
    return presence;
}

void temp_init(void) {
    ow_gpio_init();
    ow_rmt_tx_init();

    ds18b20_present = ow_reset();
    if (ds18b20_present) {
        ESP_LOGI(TAG, "DS18B20 detected via RMT");
    } else {
        ESP_LOGW(TAG, "DS18B20 not found");
    }
}

float temp_read_celsius(void) {
    if (!ds18b20_present) return 25.0f;

    /* Start conversion (skip ROM) */
    ow_reset();
    ow_blocking_write_byte(0xCC);  /* Skip ROM */
    ow_blocking_write_byte(0x44);  /* Start conversion */

    /* Wait for conversion: DS18B20 takes up to 750ms at 12-bit */
    vTaskDelay(pdMS_TO_TICKS(800));

    /* Read scratchpad */
    ow_reset();
    ow_blocking_write_byte(0xCC);  /* Skip ROM */
    ow_blocking_write_byte(0xBE);  /* Read scratchpad */

    uint8_t lsb = ow_blocking_read_byte();
    uint8_t msb = ow_blocking_read_byte();

    int16_t raw = (int16_t)((msb << 8) | lsb);
    return (float)raw * 0.0625f;
}
