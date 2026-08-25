/* SPDX-License-Identifier: MIT */
#include "parallel_nor.h"
#include "board_pins.h"
#include "pico/stdlib.h"

#define UNLOCK_ADDR_1 0x555u
#define UNLOCK_ADDR_2 0x2aau

static void set_group_direction(unsigned first, unsigned count, bool output) {
    for (unsigned i = 0; i < count; ++i) gpio_set_dir(first + i, output);
}

static void put_address(uint32_t value) {
    for (unsigned bit = 0; bit < PIN_ROM_A_COUNT; ++bit)
        gpio_put(PIN_ROM_A_FIRST + bit, (value >> bit) & 1u);
}

static void put_data(uint16_t value) {
    for (unsigned bit = 0; bit < PIN_ROM_D_COUNT; ++bit)
        gpio_put(PIN_ROM_D_FIRST + bit, (value >> bit) & 1u);
}

static uint16_t get_data(void) {
    uint16_t value = 0u;
    for (unsigned bit = 0; bit < PIN_ROM_D_COUNT; ++bit)
        if (gpio_get(PIN_ROM_D_FIRST + bit)) value |= (uint16_t)(1u << bit);
    return value;
}

void parallel_nor_console_safe_state(void) {
    for (unsigned pin = PIN_ROM_A_FIRST; pin <= PIN_ROM_WE_N; ++pin) {
        gpio_init(pin);
        gpio_disable_pulls(pin);
        gpio_set_dir(pin, GPIO_IN);
    }
}

void parallel_nor_enter_programming(void) {
    for (unsigned pin = PIN_ROM_A_FIRST; pin <= PIN_ROM_WE_N; ++pin)
        gpio_init(pin);
    put_address(0u);
    put_data(0xffffu);
    gpio_put(PIN_ROM_CE_N, true);
    gpio_put(PIN_ROM_OE_N, true);
    gpio_put(PIN_ROM_WE_N, true);
    set_group_direction(PIN_ROM_A_FIRST, PIN_ROM_A_COUNT, true);
    set_group_direction(PIN_ROM_D_FIRST, PIN_ROM_D_COUNT, true);
    gpio_set_dir(PIN_ROM_CE_N, GPIO_OUT);
    gpio_set_dir(PIN_ROM_OE_N, GPIO_OUT);
    gpio_set_dir(PIN_ROM_WE_N, GPIO_OUT);
}

void parallel_nor_leave_programming(void) {
    gpio_put(PIN_ROM_CE_N, true);
    gpio_put(PIN_ROM_OE_N, true);
    gpio_put(PIN_ROM_WE_N, true);
    parallel_nor_console_safe_state();
}

static void write_cycle(uint32_t word_address, uint16_t value) {
    gpio_put(PIN_ROM_CE_N, true);
    gpio_put(PIN_ROM_OE_N, true);
    gpio_put(PIN_ROM_WE_N, true);
    set_group_direction(PIN_ROM_D_FIRST, PIN_ROM_D_COUNT, true);
    put_address(word_address);
    put_data(value);
    sleep_us(1u);
    gpio_put(PIN_ROM_CE_N, false);
    gpio_put(PIN_ROM_WE_N, false);
    sleep_us(1u);
    gpio_put(PIN_ROM_WE_N, true);
    gpio_put(PIN_ROM_CE_N, true);
    sleep_us(1u);
}

uint16_t parallel_nor_read_word(uint32_t word_address) {
    gpio_put(PIN_ROM_CE_N, true);
    gpio_put(PIN_ROM_OE_N, true);
    gpio_put(PIN_ROM_WE_N, true);
    put_address(word_address);
    set_group_direction(PIN_ROM_D_FIRST, PIN_ROM_D_COUNT, false);
    gpio_put(PIN_ROM_CE_N, false);
    gpio_put(PIN_ROM_OE_N, false);
    sleep_us(1u);
    const uint16_t value = get_data();
    gpio_put(PIN_ROM_OE_N, true);
    gpio_put(PIN_ROM_CE_N, true);
    put_data(0xffffu);
    set_group_direction(PIN_ROM_D_FIRST, PIN_ROM_D_COUNT, true);
    return value;
}

static void unlock(void) {
    write_cycle(UNLOCK_ADDR_1, 0x00aau);
    write_cycle(UNLOCK_ADDR_2, 0x0055u);
}

static bool wait_toggle_complete(uint32_t word_address, uint32_t timeout_ms) {
    absolute_time_t deadline = make_timeout_time_ms(timeout_ms);
    uint16_t previous = parallel_nor_read_word(word_address);
    do {
        const uint16_t current = parallel_nor_read_word(word_address);
        if (((previous ^ current) & 0x0040u) == 0u) return true;
        if ((current & 0x0020u) != 0u) {
            const uint16_t final = parallel_nor_read_word(word_address);
            return ((current ^ final) & 0x0040u) == 0u;
        }
        previous = current;
    } while (!time_reached(deadline));
    return false;
}

bool parallel_nor_chip_erase(void) {
    unlock();
    write_cycle(UNLOCK_ADDR_1, 0x0080u);
    unlock();
    write_cycle(UNLOCK_ADDR_1, 0x0010u);
    return wait_toggle_complete(0u, 180000u) &&
           parallel_nor_read_word(0u) == 0xffffu;
}

bool parallel_nor_program_word(uint32_t word_address, uint16_t value) {
    if (word_address >= ACTIVE_ROM_BYTES / 2u) return false;
    if (value == 0xffffu) return true;
    unlock();
    write_cycle(UNLOCK_ADDR_1, 0x00a0u);
    write_cycle(word_address, value);
    return wait_toggle_complete(word_address, 5u) &&
           parallel_nor_read_word(word_address) == value;
}

