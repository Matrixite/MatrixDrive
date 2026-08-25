/* SPDX-License-Identifier: MIT */
#include "tusb.h"
#include "pico/unique_id.h"
#include <string.h>

enum {
    ITF_NUM_MSC = 0,
    ITF_NUM_TOTAL
};

#define EPNUM_MSC_OUT 0x01u
#define EPNUM_MSC_IN  0x81u
#define CONFIG_TOTAL_LEN (TUD_CONFIG_DESC_LEN + TUD_MSC_DESC_LEN)

static const tusb_desc_device_t device_descriptor = {
    .bLength = sizeof(tusb_desc_device_t),
    .bDescriptorType = TUSB_DESC_DEVICE,
    .bcdUSB = 0x0200,
    .bDeviceClass = 0x00,
    .bDeviceSubClass = 0x00,
    .bDeviceProtocol = 0x00,
    .bMaxPacketSize0 = CFG_TUD_ENDPOINT0_SIZE,
    .idVendor = 0xcafe,
    .idProduct = 0x4d44,
    .bcdDevice = 0x0200,
    .iManufacturer = 0x01,
    .iProduct = 0x02,
    .iSerialNumber = 0x03,
    .bNumConfigurations = 0x01
};

const uint8_t *tud_descriptor_device_cb(void) {
    return (const uint8_t *)&device_descriptor;
}

static const uint8_t configuration_descriptor[] = {
    TUD_CONFIG_DESCRIPTOR(1, ITF_NUM_TOTAL, 0, CONFIG_TOTAL_LEN,
                          TUSB_DESC_CONFIG_ATT_REMOTE_WAKEUP, 100),
    TUD_MSC_DESCRIPTOR(ITF_NUM_MSC, 4, EPNUM_MSC_OUT, EPNUM_MSC_IN, 64)
};

const uint8_t *tud_descriptor_configuration_cb(uint8_t index) {
    (void)index;
    return configuration_descriptor;
}

static const char *string_table[] = {
    (const char[]){ 0x09, 0x04 },
    "Matrixite",
    "MatrixDrive Dual Cart",
    NULL,
    "MATRIXDRV"
};

static uint16_t string_descriptor[33];
static char serial_ascii[2u * PICO_UNIQUE_BOARD_ID_SIZE_BYTES + 1u];

const uint16_t *tud_descriptor_string_cb(uint8_t index, uint16_t langid) {
    (void)langid;
    if (index >= (sizeof string_table / sizeof string_table[0])) return NULL;
    if (index == 0u) {
        memcpy(&string_descriptor[1], string_table[0], 2);
        string_descriptor[0] = (uint16_t)((TUSB_DESC_STRING << 8) | 4u);
        return string_descriptor;
    }
    const char *source = string_table[index];
    if (index == 3u) {
        pico_get_unique_board_id_string(serial_ascii, sizeof serial_ascii);
        source = serial_ascii;
    }
    if (source == NULL) return NULL;
    size_t count = strlen(source);
    if (count > 32u) count = 32u;
    for (size_t i = 0; i < count; ++i)
        string_descriptor[1u + i] = (uint8_t)source[i];
    string_descriptor[0] = (uint16_t)((TUSB_DESC_STRING << 8) |
                                      (2u * count + 2u));
    return string_descriptor;
}
