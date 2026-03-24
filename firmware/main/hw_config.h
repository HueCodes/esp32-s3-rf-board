/**
 * @file hw_config.h
 * @brief Hardware pin and peripheral definitions for ESP32-S3 RF Dev Board v1.0
 *
 * All GPIO assignments match the net names in esp32-s3-rf-board.kicad_pcb.
 * Change only here if the PCB is revised — do not scatter pin numbers through
 * application code.
 */

#ifndef HW_CONFIG_H
#define HW_CONFIG_H

#ifdef __cplusplus
extern "C" {
#endif

/* ---------------------------------------------------------------------------
 * LEDs
 * D1: Red status LED, active-high, 330R series resistor to GPIO48
 * D2: Green power LED, always-on via R2 1k from 3.3V (no GPIO needed)
 * --------------------------------------------------------------------------- */
#define GPIO_LED_STATUS     48

/* ---------------------------------------------------------------------------
 * Buttons
 * SW1 (Reset): connected to EN pin — handled by hardware, not GPIO
 * SW2 (Boot):  active-low, internal pull-up required
 * --------------------------------------------------------------------------- */
#define GPIO_BTN_BOOT        0

/* ---------------------------------------------------------------------------
 * UART0 — routed to CP2102 USB-UART bridge (U3) and J3 header
 *
 * At 115200 baud the CP2102 appears as a virtual COM port over USB (J1).
 * The same signals break out on J3 for direct 3.3V TTL access.
 * --------------------------------------------------------------------------- */
#define UART_DEBUG_PORT      UART_NUM_0
#define UART_DEBUG_BAUD      115200
#define UART_DEBUG_TX_PIN    43   /* ESP32-S3 UART0 TX default */
#define UART_DEBUG_RX_PIN    44   /* ESP32-S3 UART0 RX default */

/* ---------------------------------------------------------------------------
 * I2C — J4 header (SDA, SCL, 3V3, GND)
 * --------------------------------------------------------------------------- */
#define I2C_PORT             I2C_NUM_0
#define I2C_SDA_PIN          8
#define I2C_SCL_PIN          9
#define I2C_FREQ_HZ          400000   /* 400 kHz fast mode */

/* ---------------------------------------------------------------------------
 * SPI — J5 header (MOSI, MISO, CLK, CS, 3V3, GND)
 * --------------------------------------------------------------------------- */
#define SPI_HOST             SPI2_HOST
#define SPI_MOSI_PIN         11
#define SPI_MISO_PIN         13
#define SPI_CLK_PIN          12
#define SPI_CS_PIN           10
#define SPI_FREQ_HZ          (10 * 1000 * 1000)   /* 10 MHz default */

/* ---------------------------------------------------------------------------
 * RF
 * Note: SPI pins 10-13 overlap with Octal SPI flash/PSRAM on some ESP32-S3
 * modules. Safe here because this is a bare QFN56 chip design.
 * --------------------------------------------------------------------------- */
#define RF_TX_POWER_QUARTER_DBM  40   /* 10 dBm in 0.25 dBm units */

#ifdef __cplusplus
}
#endif

#endif /* HW_CONFIG_H */
