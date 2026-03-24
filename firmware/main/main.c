/**
 * @file main.c
 * @brief ESP32-S3 RF Dev Board — bring-up firmware
 *
 * Validates the board is functional after assembly:
 *   - Status LED blinks at 1 Hz (CPU alive, GPIO path working)
 *   - WiFi station-mode scan every 10 s (RF path working)
 *   - Scan results printed via UART (CP2102 bridge / J3 header)
 *
 * Build with ESP-IDF v5.x:
 *   idf.py set-target esp32s3
 *   idf.py build
 *   idf.py -p /dev/ttyUSB0 flash monitor
 */

#include <stdlib.h>
#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"

#include "driver/gpio.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_wifi.h"
#include "nvs_flash.h"
#include "esp_netif.h"

#include "hw_config.h"

static const char *TAG = "rf-board";

/* Maximum AP records to retrieve per scan. */
#define SCAN_LIST_SIZE  20

/* ---------------------------------------------------------------------------
 * WiFi scan
 * --------------------------------------------------------------------------- */

static void wifi_scan_task(void *arg)
{
    wifi_scan_config_t cfg = {
        .ssid        = NULL,
        .bssid       = NULL,
        .channel     = 0,       /* Scan all channels */
        .show_hidden = false,
        .scan_type   = WIFI_SCAN_TYPE_ACTIVE,
    };

    /* Heap-allocate scan results once to avoid stack pressure */
    wifi_ap_record_t *records = malloc(sizeof(wifi_ap_record_t) * SCAN_LIST_SIZE);
    if (!records) {
        ESP_LOGE(TAG, "Failed to allocate scan result buffer");
        vTaskDelete(NULL);
        return;
    }

    while (1) {
        ESP_LOGI(TAG, "Starting WiFi scan...");
        /* Blocks until scan completes. Results consumed directly below. */
        esp_err_t err = esp_wifi_scan_start(&cfg, true);
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "esp_wifi_scan_start failed: %s", esp_err_to_name(err));
            esp_wifi_clear_ap_list();
            vTaskDelay(pdMS_TO_TICKS(10000));
            continue;
        }

        uint16_t count = SCAN_LIST_SIZE;
        err = esp_wifi_scan_get_ap_records(&count, records);
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "esp_wifi_scan_get_ap_records failed: %s", esp_err_to_name(err));
            esp_wifi_clear_ap_list();
            vTaskDelay(pdMS_TO_TICKS(10000));
            continue;
        }

        ESP_LOGI(TAG, "--- WiFi scan: %u network(s) found ---", count);
        for (uint16_t i = 0; i < count; i++) {
            ESP_LOGI(TAG, "  [%2u] RSSI %4d dBm  CH %2u  BSSID %02x:%02x:%02x:%02x:%02x:%02x  %s",
                     i + 1,
                     records[i].rssi,
                     records[i].primary,
                     records[i].bssid[0], records[i].bssid[1], records[i].bssid[2],
                     records[i].bssid[3], records[i].bssid[4], records[i].bssid[5],
                     (char *)records[i].ssid);
        }

        vTaskDelay(pdMS_TO_TICKS(10000));
    }
}

/* ---------------------------------------------------------------------------
 * Status LED
 * 1 Hz blink: 100 ms on, 900 ms off — visible at a glance during bring-up
 * --------------------------------------------------------------------------- */

static void led_task(void *arg)
{
    gpio_config_t io_cfg = {
        .pin_bit_mask = BIT64(GPIO_LED_STATUS),
        .mode         = GPIO_MODE_OUTPUT,
        .pull_up_en   = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type    = GPIO_INTR_DISABLE,
    };
    esp_err_t gpio_err = gpio_config(&io_cfg);
    if (gpio_err != ESP_OK) {
        ESP_LOGE("led", "GPIO config failed: %s", esp_err_to_name(gpio_err));
        vTaskDelete(NULL);
        return;
    }

    while (1) {
        gpio_set_level(GPIO_LED_STATUS, 1);
        vTaskDelay(pdMS_TO_TICKS(100));
        gpio_set_level(GPIO_LED_STATUS, 0);
        vTaskDelay(pdMS_TO_TICKS(900));
    }
}

/* ---------------------------------------------------------------------------
 * app_main
 * --------------------------------------------------------------------------- */

void app_main(void)
{
    ESP_LOGI(TAG, "ESP32-S3 RF Board - firmware v1.0.0");
    ESP_LOGI(TAG, "UART debug on GPIO%d/%d (115200 8N1) via CP2102 or J3",
             UART_DEBUG_TX_PIN, UART_DEBUG_RX_PIN);

    /* NVS is required by the WiFi driver for calibration data. */
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_LOGW(TAG, "NVS partition invalid, erasing...");
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    /* TCP/IP adapter and default event loop required before WiFi init. */
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());

    /* Create default STA netif — required by ESP-IDF v5.x before esp_wifi_start() */
    esp_netif_create_default_wifi_sta();

    /* Initialise WiFi in station mode.  No connection is attempted — station
     * mode is the minimum required to issue active probe requests. */
    wifi_init_config_t wifi_cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&wifi_cfg));
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_start());

    /* Set TX power to known level for RF path validation (10 dBm = 40 quarter-dBm) */
    ESP_ERROR_CHECK(esp_wifi_set_max_tx_power(RF_TX_POWER_QUARTER_DBM));

    /* LED task: pinned to core 0, low stack — pure GPIO toggling. */
    xTaskCreatePinnedToCore(led_task, "led", 2048, NULL, 5, NULL, 0);

    /* Scan task: pinned to core 1 so WiFi stack (core 0) has headroom. */
    xTaskCreatePinnedToCore(wifi_scan_task, "scan", 4096, NULL, 4, NULL, 1);
}
