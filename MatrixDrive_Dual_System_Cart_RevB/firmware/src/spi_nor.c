/* SPDX-License-Identifier: MIT */
#include "spi_nor.h"
#include "board_pins.h"
#include "hardware/spi.h"
#include "pico/stdlib.h"
#include <string.h>

#define CMD_READ_DATA       0x03u
#define CMD_PAGE_PROGRAM    0x02u
#define CMD_SECTOR_ERASE    0x20u
#define CMD_WRITE_ENABLE    0x06u
#define CMD_READ_STATUS1    0x05u
#define CMD_READ_JEDEC_ID   0x9fu
#define STATUS_BUSY         0x01u
#define ERASE_BYTES         4096u
#define PAGE_BYTES          256u

static uint8_t erase_cache[ERASE_BYTES];
static uint32_t cached_base = UINT32_MAX;
static bool cache_dirty;
static uint32_t detected_id;

static inline void select_flash(void) { gpio_put(PIN_STAGE_CS_N, false); }
static inline void deselect_flash(void) { gpio_put(PIN_STAGE_CS_N, true); }

static void send_address(uint32_t address) {
    uint8_t bytes[3] = {
        (uint8_t)(address >> 16),
        (uint8_t)(address >> 8),
        (uint8_t)address
    };
    spi_write_blocking(spi1, bytes, 3);
}

static void write_enable(void) {
    const uint8_t command = CMD_WRITE_ENABLE;
    select_flash();
    spi_write_blocking(spi1, &command, 1);
    deselect_flash();
}

static bool wait_ready(uint32_t timeout_ms) {
    absolute_time_t deadline = make_timeout_time_ms(timeout_ms);
    do {
        const uint8_t command = CMD_READ_STATUS1;
        uint8_t status = 0xffu;
        select_flash();
        spi_write_blocking(spi1, &command, 1);
        spi_read_blocking(spi1, 0xffu, &status, 1);
        deselect_flash();
        if ((status & STATUS_BUSY) == 0u) return true;
        tight_loop_contents();
    } while (!time_reached(deadline));
    return false;
}

static bool raw_read(uint32_t address, uint8_t *destination, size_t length) {
    if (address > STAGE_FLASH_BYTES || length > STAGE_FLASH_BYTES - address)
        return false;
    const uint8_t command = CMD_READ_DATA;
    select_flash();
    spi_write_blocking(spi1, &command, 1);
    send_address(address);
    spi_read_blocking(spi1, 0xffu, destination, length);
    deselect_flash();
    return true;
}

static bool raw_erase_4k(uint32_t address) {
    write_enable();
    const uint8_t command = CMD_SECTOR_ERASE;
    select_flash();
    spi_write_blocking(spi1, &command, 1);
    send_address(address);
    deselect_flash();
    return wait_ready(1000u);
}

static bool raw_program_page(uint32_t address, const uint8_t *source, size_t length) {
    if (length == 0u || length > PAGE_BYTES ||
        ((address & (PAGE_BYTES - 1u)) + length) > PAGE_BYTES) return false;
    write_enable();
    const uint8_t command = CMD_PAGE_PROGRAM;
    select_flash();
    spi_write_blocking(spi1, &command, 1);
    send_address(address);
    spi_write_blocking(spi1, source, length);
    deselect_flash();
    return wait_ready(20u);
}

bool storage_flush(void) {
    if (!cache_dirty || cached_base == UINT32_MAX) return true;
    if (!raw_erase_4k(cached_base)) return false;
    for (size_t offset = 0; offset < ERASE_BYTES; offset += PAGE_BYTES) {
        if (!raw_program_page(cached_base + (uint32_t)offset,
                              erase_cache + offset, PAGE_BYTES)) return false;
    }
    cache_dirty = false;
    return true;
}

static bool load_cache(uint32_t base) {
    if (cached_base == base) return true;
    if (!storage_flush()) return false;
    if (!raw_read(base, erase_cache, sizeof erase_cache)) return false;
    cached_base = base;
    return true;
}

bool storage_init(void) {
    gpio_init(PIN_STAGE_CS_N);
    gpio_set_dir(PIN_STAGE_CS_N, GPIO_OUT);
    deselect_flash();
    spi_init(spi1, 20000000u);
    gpio_set_function(PIN_STAGE_MISO, GPIO_FUNC_SPI);
    gpio_set_function(PIN_STAGE_SCK, GPIO_FUNC_SPI);
    gpio_set_function(PIN_STAGE_MOSI, GPIO_FUNC_SPI);
    cached_base = UINT32_MAX;
    cache_dirty = false;

    const uint8_t command = CMD_READ_JEDEC_ID;
    uint8_t id[3] = {0};
    select_flash();
    spi_write_blocking(spi1, &command, 1);
    spi_read_blocking(spi1, 0xffu, id, 3);
    deselect_flash();
    detected_id = ((uint32_t)id[0] << 16) | ((uint32_t)id[1] << 8) | id[2];
    /* Winbond W25Q128 is EF 40 18. Reject open bus and wrong capacity. */
    return detected_id == 0xef4018u;
}

uint32_t storage_jedec_id(void) { return detected_id; }

bool storage_read_bytes(uint32_t address, void *destination, size_t length) {
    uint8_t *out = (uint8_t *)destination;
    while (length != 0u) {
        const uint32_t base = address & ~(ERASE_BYTES - 1u);
        const size_t within = (size_t)(address - base);
        size_t chunk = ERASE_BYTES - within;
        if (chunk > length) chunk = length;
        if (base == cached_base) memcpy(out, erase_cache + within, chunk);
        else if (!raw_read(address, out, chunk)) return false;
        address += (uint32_t)chunk;
        out += chunk;
        length -= chunk;
    }
    return true;
}

bool storage_write_bytes(uint32_t address, const void *source, size_t length) {
    const uint8_t *in = (const uint8_t *)source;
    if (address > STAGE_FLASH_BYTES || length > STAGE_FLASH_BYTES - address)
        return false;
    while (length != 0u) {
        const uint32_t base = address & ~(ERASE_BYTES - 1u);
        const size_t within = (size_t)(address - base);
        size_t chunk = ERASE_BYTES - within;
        if (chunk > length) chunk = length;
        if (!load_cache(base)) return false;
        memcpy(erase_cache + within, in, chunk);
        cache_dirty = true;
        address += (uint32_t)chunk;
        in += chunk;
        length -= chunk;
    }
    return true;
}

