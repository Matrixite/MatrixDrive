/* SPDX-License-Identifier: MIT */
#include "board_pins.h"
#include "fat16.h"
#include "msc_disk.h"
#include "parallel_nor.h"
#include "rom_installer.h"
#include "spi_nor.h"
#include "status.h"
#include "hardware/adc.h"
#include "pico/stdlib.h"
#include "tusb.h"

#define USB_PRESENT_ADC_MIN 1800u
#define BUTTON_ADC_MAX       500u

static uint16_t sense_read(void) {
    adc_select_input(ADC_USB_PROGRAM_CH);
    return adc_read();
}

static bool button_edge(void) {
    static bool was_down;
    static absolute_time_t changed;
    const bool down = sense_read() < BUTTON_ADC_MAX && tud_mounted();
    const bool stable = absolute_time_diff_us(changed, get_absolute_time()) > 30000;
    bool pressed = false;
    if (down != was_down && stable) {
        was_down = down;
        changed = get_absolute_time();
        pressed = down;
    }
    return pressed;
}

static void show_install_result(install_result_t result) {
    if (result == INSTALL_OK) status_set(STATUS_SUCCESS);
    else if (result == INSTALL_NO_IMAGE || result == INSTALL_BAD_IMAGE)
        status_set(STATUS_BAD_IMAGE);
    else status_set(STATUS_FLASH_ERROR);
}

int main(void) {
    parallel_nor_console_safe_state();
    status_init();
    adc_init();
    adc_gpio_init(PIN_USB_PROGRAM_ADC);
    sleep_ms(2u);

    /* Console mode needs no MCU intervention: the CPLD feeds active NOR/FRAM. */
    if (sense_read() < USB_PRESENT_ADC_MIN) {
        while (true) {
            status_task();
            tight_loop_contents();
        }
    }

    if (!storage_init() || !fat16_format_if_needed()) {
        status_set(STATUS_FLASH_ERROR);
        while (true) status_task();
    }

    tusb_init();
    while (true) {
        tud_task();
        status_task();

        if (button_edge() && !msc_request_manual_install())
            status_set(STATUS_FLASH_ERROR);

        if (msc_take_install_request())
            show_install_result(rom_install_from_staging());
    }
}
