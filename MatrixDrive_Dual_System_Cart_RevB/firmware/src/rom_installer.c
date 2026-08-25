/* SPDX-License-Identifier: MIT */
#include "rom_installer.h"
#include "board_pins.h"
#include "fat16.h"
#include "parallel_nor.h"
#include "spi_nor.h"
#include "status.h"
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

#define LOCK_ON_ROM_WINDOW_BYTES (2u * 1024u * 1024u)

typedef enum {
    IMAGE_MEGA_DRIVE = 0,
    IMAGE_MASTER_SYSTEM
} image_kind_t;

typedef struct {
    image_kind_t kind;
    uint32_t word_address;
    uint8_t high_byte;
    bool have_high_byte;
    bool failed;
    uint32_t crc;
} program_context_t;

static uint32_t crc32_update(uint32_t crc, uint8_t byte) {
    crc ^= byte;
    for (unsigned bit = 0; bit < 8u; ++bit)
        crc = (crc >> 1) ^ (0xedb88320u & (uint32_t)-(int32_t)(crc & 1u));
    return crc;
}

static bool is_power_of_two(uint32_t value) {
    return value != 0u && (value & (value - 1u)) == 0u;
}

static bool name_is_sms(const char *name) {
    const size_t length = strlen(name);
    if (length < 4u || name[length - 4u] != '.') return false;
    const char a = name[length - 3u];
    const char b = name[length - 2u];
    const char c = name[length - 1u];
    return (a == 'S' || a == 's') && (b == 'M' || b == 'm') &&
           (c == 'S' || c == 's');
}

static bool has_md_header(const fat16_file_t *file) {
    uint8_t signature[4];
    return file->size >= 0x104u && file->size <= ACTIVE_ROM_BYTES &&
           fat16_read_at(file, 0x100u, signature, sizeof signature) &&
           memcmp(signature, "SEGA", sizeof signature) == 0;
}

static bool has_sms_header_at(const fat16_file_t *file, uint32_t offset) {
    static const uint8_t signature[] = {'T', 'M', 'R', ' ', 'S', 'E', 'G', 'A'};
    uint8_t candidate[sizeof signature];
    return file->size >= offset + sizeof candidate &&
           fat16_read_at(file, offset, candidate, sizeof candidate) &&
           memcmp(candidate, signature, sizeof signature) == 0;
}

static bool valid_sms_image(const fat16_file_t *file) {
    if (file->size < 8u * 1024u || file->size > ACTIVE_SMS_BYTES) return false;
    return has_sms_header_at(file, 0x1ff0u) ||
           has_sms_header_at(file, 0x3ff0u) ||
           has_sms_header_at(file, 0x7ff0u);
}

static bool program_chunk(const uint8_t *data, size_t length, void *opaque) {
    program_context_t *context = (program_context_t *)opaque;
    for (size_t i = 0; i < length; ++i) {
        context->crc = crc32_update(context->crc, data[i]);
        if (context->kind == IMAGE_MASTER_SYSTEM) {
            const uint16_t word = (uint16_t)(0xff00u | data[i]);
            if (!parallel_nor_program_word(context->word_address++, word)) {
                context->failed = true;
                return false;
            }
        } else if (!context->have_high_byte) {
            context->high_byte = data[i];
            context->have_high_byte = true;
        } else {
            const uint16_t word = (uint16_t)(((uint16_t)context->high_byte << 8) |
                                              data[i]);
            if (!parallel_nor_program_word(context->word_address++, word)) {
                context->failed = true;
                return false;
            }
            context->have_high_byte = false;
        }
    }
    return true;
}

static bool finish_odd_md_byte(program_context_t *context) {
    if (!context->have_high_byte) return true;
    const uint16_t word =
        (uint16_t)(((uint16_t)context->high_byte << 8) | 0xffu);
    context->have_high_byte = false;
    if (!parallel_nor_program_word(context->word_address++, word)) {
        context->failed = true;
        return false;
    }
    return true;
}

install_result_t rom_install_from_staging(void) {
    if (!storage_flush()) return INSTALL_STORAGE_ERROR;
    fat16_file_t file;
    if (!fat16_find_first_rom(&file)) return INSTALL_NO_IMAGE;

    const image_kind_t kind = name_is_sms(file.name) ? IMAGE_MASTER_SYSTEM :
                                                       IMAGE_MEGA_DRIVE;
    if ((kind == IMAGE_MASTER_SYSTEM && !valid_sms_image(&file)) ||
        (kind == IMAGE_MEGA_DRIVE && !has_md_header(&file)))
        return INSTALL_BAD_IMAGE;

    status_set(STATUS_PROGRAMMING);
    parallel_nor_enter_programming();
    if (!parallel_nor_chip_erase()) {
        parallel_nor_leave_programming();
        return INSTALL_FLASH_ERROR;
    }

    program_context_t context = {
        .kind = kind,
        .word_address = 0u,
        .high_byte = 0xffu,
        .have_high_byte = false,
        .failed = false,
        .crc = 0xffffffffu
    };

    bool streamed = fat16_stream(&file, program_chunk, &context);
    if (kind == IMAGE_MEGA_DRIVE && streamed)
        streamed = finish_odd_md_byte(&context);

    // A real <=2 MiB mask ROM repeats when higher address pins are not
    // populated. Sonic & Knuckles relies on that upper-cartridge behaviour.
    // Repeat even-sized, power-of-two MD images through its complete 2 MiB
    // subslot window. Sonic 2 (1 MiB) is therefore visible in both halves.
    if (kind == IMAGE_MEGA_DRIVE && streamed && !context.failed &&
        (file.size & 1u) == 0u && is_power_of_two(file.size) &&
        file.size < LOCK_ON_ROM_WINDOW_BYTES) {
        while ((context.word_address * 2u) < LOCK_ON_ROM_WINDOW_BYTES) {
            if (!fat16_stream(&file, program_chunk, &context)) {
                streamed = false;
                break;
            }
            if (context.failed) break;
        }
    }

    parallel_nor_leave_programming();
    (void)context.crc; /* Reserved for a future STATUS.TXT record. */
    if (!streamed || context.failed) return INSTALL_FLASH_ERROR;
    return INSTALL_OK;
}
