/* SPDX-License-Identifier: MIT */
#include "fat16.h"
#include "board_pins.h"
#include "spi_nor.h"
#include <ctype.h>
#include <string.h>

#define FAT16_RESERVED_SECTORS 1u
#define FAT16_FAT_COUNT 2u
#define FAT16_ROOT_ENTRIES 512u
#define FAT16_SECTORS_PER_FAT 128u
#define FAT16_ROOT_SECTORS 32u
#define FAT16_ROOT_LBA (FAT16_RESERVED_SECTORS + FAT16_FAT_COUNT * FAT16_SECTORS_PER_FAT)
#define FAT16_DATA_LBA (FAT16_ROOT_LBA + FAT16_ROOT_SECTORS)

static uint16_t read_le16(const uint8_t *p) {
    return (uint16_t)((uint16_t)p[0] | ((uint16_t)p[1] << 8));
}

static uint32_t read_le32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static void write_le16(uint8_t *p, uint16_t value) {
    p[0] = (uint8_t)value;
    p[1] = (uint8_t)(value >> 8);
}

static void write_le32(uint8_t *p, uint32_t value) {
    p[0] = (uint8_t)value;
    p[1] = (uint8_t)(value >> 8);
    p[2] = (uint8_t)(value >> 16);
    p[3] = (uint8_t)(value >> 24);
}

static bool write_sector(uint32_t lba, const uint8_t sector[MSC_BLOCK_BYTES]) {
    return storage_write_bytes(lba * MSC_BLOCK_BYTES, sector, MSC_BLOCK_BYTES);
}

static bool read_sector(uint32_t lba, uint8_t sector[MSC_BLOCK_BYTES]) {
    return storage_read_bytes(lba * MSC_BLOCK_BYTES, sector, MSC_BLOCK_BYTES);
}

static bool valid_boot_sector(const uint8_t sector[MSC_BLOCK_BYTES]) {
    return sector[510] == 0x55u && sector[511] == 0xaau &&
           read_le16(sector + 11) == MSC_BLOCK_BYTES &&
           memcmp(sector + 54, "FAT16   ", 8) == 0;
}

static bool format_volume(void) {
    uint8_t sector[MSC_BLOCK_BYTES];
    memset(sector, 0, sizeof sector);
    sector[0] = 0xebu; sector[1] = 0x3cu; sector[2] = 0x90u;
    memcpy(sector + 3, "MATRIXRB", 8);
    write_le16(sector + 11, MSC_BLOCK_BYTES);
    sector[13] = 1u;
    write_le16(sector + 14, FAT16_RESERVED_SECTORS);
    sector[16] = FAT16_FAT_COUNT;
    write_le16(sector + 17, FAT16_ROOT_ENTRIES);
    write_le16(sector + 19, (uint16_t)MSC_BLOCK_COUNT);
    sector[21] = 0xf8u;
    write_le16(sector + 22, FAT16_SECTORS_PER_FAT);
    write_le16(sector + 24, 63u);
    write_le16(sector + 26, 255u);
    sector[36] = 0x80u;
    sector[38] = 0x29u;
    write_le32(sector + 39, 0x4d445241u);
    memcpy(sector + 43, "MATRIXDRV  ", 11);
    memcpy(sector + 54, "FAT16   ", 8);
    sector[510] = 0x55u; sector[511] = 0xaau;
    if (!write_sector(0u, sector)) return false;

    memset(sector, 0, sizeof sector);
    for (uint32_t fat = 0; fat < FAT16_FAT_COUNT; ++fat) {
        const uint32_t first = FAT16_RESERVED_SECTORS + fat * FAT16_SECTORS_PER_FAT;
        for (uint32_t i = 0; i < FAT16_SECTORS_PER_FAT; ++i)
            if (!write_sector(first + i, sector)) return false;
        /* Reserved entries and cluster 2, which contains README.TXT. */
        sector[0] = 0xf8u; sector[1] = 0xffu;
        sector[2] = 0xffu; sector[3] = 0xffu;
        sector[4] = 0xffu; sector[5] = 0xffu;
        if (!write_sector(first, sector)) return false;
        memset(sector, 0, sizeof sector);
    }

    for (uint32_t i = 0; i < FAT16_ROOT_SECTORS; ++i)
        if (!write_sector(FAT16_ROOT_LBA + i, sector)) return false;

    memcpy(sector, "MATRIXDRV  ", 11);
    sector[11] = 0x08u;
    memcpy(sector + 32, "README  TXT", 11);
    sector[32 + 11] = 0x20u;
    write_le16(sector + 32 + 26, 2u);
    static const char message[] =
        "MATRIXDRIVE DUAL-SYSTEM USB CARTRIDGE\r\n"
        "Copy one .BIN/.MD/.GEN/.32X or .SMS image here, then safely eject.\r\n"
        "Limits: MD/32X 4 MiB; SMS 2 MiB. Set mode with power off.\r\n";
    write_le32(sector + 32 + 28, (uint32_t)(sizeof message - 1u));
    if (!write_sector(FAT16_ROOT_LBA, sector)) return false;

    memset(sector, 0, sizeof sector);
    memcpy(sector, message, sizeof message - 1u);
    if (!write_sector(FAT16_DATA_LBA, sector)) return false;
    return storage_flush();
}

bool fat16_format_if_needed(void) {
    uint8_t sector[MSC_BLOCK_BYTES];
    if (!read_sector(0u, sector)) return false;
    return valid_boot_sector(sector) || format_volume();
}

bool fat16_mount(fat16_volume_t *volume) {
    uint8_t sector[MSC_BLOCK_BYTES];
    if (volume == NULL || !read_sector(0u, sector) || !valid_boot_sector(sector))
        return false;
    volume->bytes_per_sector = read_le16(sector + 11);
    volume->sectors_per_cluster = sector[13];
    volume->reserved_sectors = read_le16(sector + 14);
    volume->fat_count = sector[16];
    volume->root_entries = read_le16(sector + 17);
    volume->sectors_per_fat = read_le16(sector + 22);
    volume->total_sectors = read_le16(sector + 19);
    if (volume->total_sectors == 0u) volume->total_sectors = read_le32(sector + 32);
    volume->root_lba = volume->reserved_sectors +
                       (uint32_t)volume->fat_count * volume->sectors_per_fat;
    volume->root_sectors = ((uint32_t)volume->root_entries * 32u +
                            volume->bytes_per_sector - 1u) /
                           volume->bytes_per_sector;
    volume->data_lba = volume->root_lba + volume->root_sectors;
    return volume->bytes_per_sector == MSC_BLOCK_BYTES &&
           volume->sectors_per_cluster != 0u && volume->fat_count != 0u;
}

static bool supported_extension(const uint8_t entry[32]) {
    char extension[4];
    for (unsigned i = 0; i < 3u; ++i)
        extension[i] = (char)toupper((unsigned char)entry[8u + i]);
    extension[3] = '\0';
    return strcmp(extension, "BIN") == 0 || strcmp(extension, "MD ") == 0 ||
           strcmp(extension, "GEN") == 0 || strcmp(extension, "32X") == 0 ||
           strcmp(extension, "SMS") == 0;
}

static void make_name(const uint8_t entry[32], char output[13]) {
    size_t n = 0u;
    for (size_t i = 0; i < 8u && entry[i] != ' '; ++i)
        output[n++] = (char)entry[i];
    output[n++] = '.';
    for (size_t i = 8u; i < 11u && entry[i] != ' '; ++i)
        output[n++] = (char)entry[i];
    output[n] = '\0';
}

bool fat16_find_first_rom(fat16_file_t *file) {
    if (file == NULL || !fat16_mount(&file->volume)) return false;
    uint8_t sector[MSC_BLOCK_BYTES];
    for (uint32_t s = 0; s < file->volume.root_sectors; ++s) {
        if (!read_sector(file->volume.root_lba + s, sector)) return false;
        for (size_t offset = 0; offset < MSC_BLOCK_BYTES; offset += 32u) {
            const uint8_t *entry = sector + offset;
            if (entry[0] == 0x00u) return false;
            if (entry[0] == 0xe5u || entry[11] == 0x0fu ||
                (entry[11] & 0x18u) != 0u) continue;
            const uint32_t size = read_le32(entry + 28);
            if (!supported_extension(entry) || size < 512u ||
                size > ACTIVE_ROM_BYTES) continue;
            file->first_cluster = read_le16(entry + 26);
            file->size = size;
            make_name(entry, file->name);
            return file->first_cluster >= 2u;
        }
    }
    return false;
}

static bool next_cluster(const fat16_volume_t *volume, uint16_t current,
                         uint16_t *next) {
    const uint32_t fat_offset = (uint32_t)current * 2u;
    uint8_t bytes[2];
    if (!storage_read_bytes((volume->reserved_sectors * MSC_BLOCK_BYTES) +
                            fat_offset, bytes, sizeof bytes)) return false;
    *next = read_le16(bytes);
    return true;
}

static uint32_t cluster_address(const fat16_volume_t *volume, uint16_t cluster) {
    const uint32_t sector = volume->data_lba +
        ((uint32_t)cluster - 2u) * volume->sectors_per_cluster;
    return sector * MSC_BLOCK_BYTES;
}

bool fat16_read_at(const fat16_file_t *file, uint32_t offset,
                   void *destination, size_t length) {
    if (file == NULL || destination == NULL || offset > file->size ||
        length > file->size - offset) return false;
    const uint32_t cluster_bytes = (uint32_t)file->volume.sectors_per_cluster *
                                   MSC_BLOCK_BYTES;
    uint16_t cluster = file->first_cluster;
    uint32_t skip_clusters = offset / cluster_bytes;
    for (uint32_t i = 0; i < skip_clusters; ++i) {
        if (!next_cluster(&file->volume, cluster, &cluster) || cluster >= 0xfff8u)
            return false;
    }
    uint32_t within = offset % cluster_bytes;
    uint8_t *out = (uint8_t *)destination;
    while (length != 0u) {
        if (cluster < 2u || cluster >= 0xfff8u) return false;
        size_t chunk = cluster_bytes - within;
        if (chunk > length) chunk = length;
        if (!storage_read_bytes(cluster_address(&file->volume, cluster) + within,
                                out, chunk)) return false;
        out += chunk;
        length -= chunk;
        within = 0u;
        if (length != 0u && !next_cluster(&file->volume, cluster, &cluster))
            return false;
    }
    return true;
}

bool fat16_stream(const fat16_file_t *file, fat16_stream_callback_t callback,
                  void *context) {
    if (file == NULL || callback == NULL) return false;
    uint8_t buffer[MSC_BLOCK_BYTES];
    uint16_t cluster = file->first_cluster;
    uint32_t remaining = file->size;
    uint32_t visited = 0u;
    while (remaining != 0u) {
        if (cluster < 2u || cluster >= 0xfff8u || ++visited > MSC_BLOCK_COUNT)
            return false;
        for (uint8_t s = 0; s < file->volume.sectors_per_cluster &&
                            remaining != 0u; ++s) {
            const uint32_t address = cluster_address(&file->volume, cluster) +
                                     (uint32_t)s * MSC_BLOCK_BYTES;
            if (!storage_read_bytes(address, buffer, sizeof buffer)) return false;
            size_t length = remaining > sizeof buffer ? sizeof buffer : remaining;
            if (!callback(buffer, length, context)) return false;
            remaining -= (uint32_t)length;
        }
        if (remaining != 0u && !next_cluster(&file->volume, cluster, &cluster))
            return false;
    }
    return true;
}
