/* SPDX-License-Identifier: MIT */
#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

bool storage_init(void);
bool storage_read_bytes(uint32_t address, void *destination, size_t length);
bool storage_write_bytes(uint32_t address, const void *source, size_t length);
bool storage_flush(void);
uint32_t storage_jedec_id(void);

