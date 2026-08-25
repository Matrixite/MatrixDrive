/* Host-side tests for MD/SMS validation, lock-on mirroring and x16 packing. */
#include "rom_installer.h"
#include "fat16.h"
#include "parallel_nor.h"
#include "spi_nor.h"
#include "status.h"
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define LOCK_ON_ROM_WORDS ((2u * 1024u * 1024u) / 2u)

static uint8_t image[32768];
static uint32_t image_size;
static const char *image_name;
static uint16_t words[LOCK_ON_ROM_WORDS];
static uint32_t word_count;
static unsigned erase_count;

bool storage_flush(void) { return true; }
bool storage_init(void) { return true; }
bool storage_read_bytes(uint32_t a, void *d, size_t n) {
    (void)a; (void)d; (void)n; return false;
}
bool storage_write_bytes(uint32_t a, const void *s, size_t n) {
    (void)a; (void)s; (void)n; return false;
}
uint32_t storage_jedec_id(void) { return 0; }

bool fat16_find_first_rom(fat16_file_t *file) {
    memset(file, 0, sizeof *file);
    file->size = image_size;
    strncpy(file->name, image_name, sizeof file->name - 1u);
    return true;
}
bool fat16_read_at(const fat16_file_t *file, uint32_t offset,
                   void *destination, size_t length) {
    (void)file;
    if (offset > image_size || length > image_size - offset) return false;
    memcpy(destination, image + offset, length);
    return true;
}
bool fat16_stream(const fat16_file_t *file, fat16_stream_callback_t callback,
                  void *context) {
    (void)file;
    for (uint32_t offset = 0; offset < image_size; offset += 257u) {
        size_t chunk = image_size - offset;
        if (chunk > 257u) chunk = 257u;
        if (!callback(image + offset, chunk, context)) return false;
    }
    return true;
}

void status_set(status_mode_t mode) { (void)mode; }
void parallel_nor_enter_programming(void) {}
void parallel_nor_leave_programming(void) {}
bool parallel_nor_chip_erase(void) {
    ++erase_count;
    word_count = 0;
    return true;
}
bool parallel_nor_program_word(uint32_t address, uint16_t value) {
    if (address >= sizeof words / sizeof words[0]) return false;
    words[address] = value;
    if (word_count <= address) word_count = address + 1u;
    return true;
}
uint16_t parallel_nor_read_word(uint32_t address) { return words[address]; }
void parallel_nor_console_safe_state(void) {}

static void test_md_odd_image(void) {
    image_name = "ODD.BIN";
    image_size = 513u;
    for (uint32_t i = 0; i < image_size; ++i) image[i] = (uint8_t)i;
    memcpy(image + 0x100, "SEGA", 4);
    assert(rom_install_from_staging() == INSTALL_OK);
    assert(word_count == 257u);
    assert(words[0] == 0x0001u);
    assert(words[256] == 0x00ffu);
}

static void test_md_lock_on_mirror(void) {
    image_name = "SONIC2.BIN";
    image_size = sizeof image;
    for (uint32_t i = 0; i < image_size; ++i)
        image[i] = (uint8_t)(i ^ 0xa5u);
    memcpy(image + 0x100, "SEGA", 4);

    assert(rom_install_from_staging() == INSTALL_OK);
    assert(word_count == LOCK_ON_ROM_WORDS);

    const uint32_t period_words = image_size / 2u;
    assert(words[0] == (uint16_t)(((uint16_t)image[0] << 8) | image[1]));
    assert(words[period_words] == words[0]);
    assert(words[LOCK_ON_ROM_WORDS - 1u] == words[period_words - 1u]);
}

static void test_sms(void) {
    image_name = "SONIC.SMS";
    image_size = sizeof image;
    for (uint32_t i = 0; i < image_size; ++i) image[i] = (uint8_t)(i ^ 0x5a);
    memcpy(image + 0x7ff0, "TMR SEGA", 8);
    assert(rom_install_from_staging() == INSTALL_OK);
    assert(word_count == image_size);
    assert(words[0] == (uint16_t)(0xff00u | image[0]));
    assert(words[0x1234] == (uint16_t)(0xff00u | image[0x1234]));
    assert(words[0x7fff] == (uint16_t)(0xff00u | image[0x7fff]));

    const unsigned previous_erases = erase_count;
    memset(image + 0x7ff0, 0, 8);
    assert(rom_install_from_staging() == INSTALL_BAD_IMAGE);
    assert(erase_count == previous_erases);
}

int main(void) {
    test_md_odd_image();
    test_md_lock_on_mirror();
    test_sms();
    puts("dual-format installer and lock-on mirror host tests passed");
    return 0;
}
