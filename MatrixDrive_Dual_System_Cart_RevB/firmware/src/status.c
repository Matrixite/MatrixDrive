/* SPDX-License-Identifier: MIT */
#include "status.h"
#include "board_pins.h"
#include "pico/stdlib.h"

static status_mode_t current_mode;
static absolute_time_t last_tick;
static bool phase;
static unsigned error_phase;

static void leds(bool green, bool amber, bool red) {
    gpio_put(PIN_LED_GREEN, green);
    gpio_put(PIN_LED_AMBER, amber);
    gpio_put(PIN_LED_RED, red);
}

void status_init(void) {
    const unsigned pins[] = { PIN_LED_GREEN, PIN_LED_AMBER, PIN_LED_RED };
    for (unsigned i = 0; i < 3u; ++i) {
        gpio_init(pins[i]);
        gpio_set_dir(pins[i], GPIO_OUT);
    }
    current_mode = STATUS_OFF;
    last_tick = get_absolute_time();
    phase = false;
    error_phase = 0u;
    leds(false, false, false);
}

void status_set(status_mode_t mode) {
    current_mode = mode;
    phase = false;
    error_phase = 0u;
    last_tick = get_absolute_time();
    if (mode == STATUS_PROGRAMMING) leds(false, true, false);
    else if (mode == STATUS_SUCCESS) leds(true, false, false);
    else if (mode == STATUS_FLASH_ERROR) leds(false, false, true);
    else leds(false, false, false);
}

status_mode_t status_get(void) {
    return current_mode;
}

void status_task(void) {
    uint32_t interval_ms = 0u;
    if (current_mode == STATUS_USB_MOUNTED) interval_ms = 600u;
    else if (current_mode == STATUS_USB_WRITING) interval_ms = 90u;
    else if (current_mode == STATUS_BAD_IMAGE) interval_ms = 180u;
    else return;

    if (absolute_time_diff_us(last_tick, get_absolute_time()) <
        (int64_t)interval_ms * 1000) return;
    last_tick = get_absolute_time();

    if (current_mode == STATUS_USB_MOUNTED) {
        phase = !phase;
        leds(phase, false, false);
    } else if (current_mode == STATUS_USB_WRITING) {
        phase = !phase;
        leds(false, phase, false);
    } else {
        /* Repeating two-red-blink code with a longer dark gap. */
        error_phase = (error_phase + 1u) % 6u;
        leds(false, false, error_phase == 0u || error_phase == 2u);
    }
}

