/* Host-side unit test for the allocation-free FAT16 formatter/reader. */
#include "fat16.h"
#include "board_pins.h"
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static uint8_t media[STAGE_FLASH_BYTES];

bool storage_init(void) { memset(media, 0xff, sizeof media); return true; }
bool storage_flush(void) { return true; }
uint32_t storage_jedec_id(void) { return 0xef4018u; }
bool storage_read_bytes(uint32_t address, void *destination, size_t length) {
    if (address > sizeof media || length > sizeof media - address) return false;
    memcpy(destination, media + address, length);
    return true;
}
bool storage_write_bytes(uint32_t address, const void *source, size_t length) {
    if (address > sizeof media || length > sizeof media - address) return false;
    memcpy(media + address, source, length);
    return true;
}

static void le16(uint8_t *p, uint16_t value) {
    p[0] = (uint8_t)value; p[1] = (uint8_t)(value >> 8);
}
static void le32(uint8_t *p, uint32_t value) {
    p[0] = (uint8_t)value; p[1] = (uint8_t)(value >> 8);
    p[2] = (uint8_t)(value >> 16); p[3] = (uint8_t)(value >> 24);
}

static bool count_bytes(const uint8_t *data, size_t length, void *context) {
    (void)data;
    *(size_t *)context += length;
    return true;
}

int main(void) {
    assert(storage_init());
    assert(fat16_format_if_needed());
    fat16_volume_t volume;
    assert(fat16_mount(&volume));
    assert(volume.total_sectors == MSC_BLOCK_COUNT);
    assert(volume.data_lba == 289u);

    /* Add TEST.BIN in cluster 3 to the formatted root directory. */
    uint8_t *entry = media + 257u * MSC_BLOCK_BYTES + 64u;
    memcpy(entry, "TEST    BIN", 11);
    entry[11] = 0x20u;
    le16(entry + 26, 3u);
    le32(entry + 28, 512u);
    le16(media + MSC_BLOCK_BYTES + 3u * 2u, 0xffffu);
    le16(media + (1u + 128u) * MSC_BLOCK_BYTES + 3u * 2u, 0xffffu);
    uint8_t *rom = media + 290u * MSC_BLOCK_BYTES;
    memset(rom, 0, 512u);
    memcpy(rom + 0x100, "SEGA", 4);

    fat16_file_t file;
    assert(fat16_find_first_rom(&file));
    assert(strcmp(file.name, "TEST.BIN") == 0);
    uint8_t signature[4];
    assert(fat16_read_at(&file, 0x100u, signature, sizeof signature));
    assert(memcmp(signature, "SEGA", 4) == 0);
    size_t streamed = 0u;
    assert(fat16_stream(&file, count_bytes, &streamed));
    assert(streamed == 512u);

    /* Confirm .SMS is included in the 8.3 root-level image scan. */
    entry[0] = 0xe5u;
    uint8_t *sms_entry = media + 257u * MSC_BLOCK_BYTES + 96u;
    memcpy(sms_entry, "MAPPER  SMS", 11);
    sms_entry[11] = 0x20u;
    le16(sms_entry + 26, 4u);
    le32(sms_entry + 28, 512u);
    le16(media + MSC_BLOCK_BYTES + 4u * 2u, 0xffffu);
    le16(media + (1u + 128u) * MSC_BLOCK_BYTES + 4u * 2u, 0xffffu);
    assert(fat16_find_first_rom(&file));
    assert(strcmp(file.name, "MAPPER.SMS") == 0);

    puts("fat16 host tests passed");
    return 0;
}
