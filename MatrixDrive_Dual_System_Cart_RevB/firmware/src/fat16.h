/* SPDX-License-Identifier: MIT */
#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef struct {
    uint16_t bytes_per_sector;
    uint8_t sectors_per_cluster;
    uint16_t reserved_sectors;
    uint8_t fat_count;
    uint16_t root_entries;
    uint16_t sectors_per_fat;
    uint32_t total_sectors;
    uint32_t root_lba;
    uint32_t root_sectors;
    uint32_t data_lba;
} fat16_volume_t;

typedef struct {
    fat16_volume_t volume;
    uint16_t first_cluster;
    uint32_t size;
    char name[13];
} fat16_file_t;

typedef bool (*fat16_stream_callback_t)(const uint8_t *data, size_t length,
                                        void *context);

bool fat16_format_if_needed(void);
bool fat16_mount(fat16_volume_t *volume);
bool fat16_find_first_rom(fat16_file_t *file);
bool fat16_read_at(const fat16_file_t *file, uint32_t offset,
                   void *destination, size_t length);
bool fat16_stream(const fat16_file_t *file, fat16_stream_callback_t callback,
                  void *context);

