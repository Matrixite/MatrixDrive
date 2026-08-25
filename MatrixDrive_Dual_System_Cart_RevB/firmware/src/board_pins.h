/* SPDX-License-Identifier: MIT */
#pragma once

/* Parallel active-ROM bus: GPIO0..20 address, GPIO21..36 data. */
#define PIN_ROM_A_FIRST       0u
#define PIN_ROM_A_COUNT      21u
#define PIN_ROM_D_FIRST      21u
#define PIN_ROM_D_COUNT      16u
#define PIN_ROM_CE_N         37u
#define PIN_ROM_OE_N         38u
#define PIN_ROM_WE_N         39u

/* Dedicated SPI1 staging flash on the valid RP2350B GPIO40..43 group. */
#define PIN_STAGE_MISO       40u
#define PIN_STAGE_CS_N       41u
#define PIN_STAGE_SCK        42u
#define PIN_STAGE_MOSI       43u

/* GPIO44/ADC4 sits at about VBUS/2. SW1 pulls it low. */
#define PIN_USB_PROGRAM_ADC  44u
#define ADC_USB_PROGRAM_CH    4u
#define PIN_LED_GREEN        45u
#define PIN_LED_AMBER        46u
#define PIN_LED_RED          47u

#define STAGE_FLASH_BYTES    (16u * 1024u * 1024u)
#define MSC_BLOCK_BYTES      512u
#define MSC_BLOCK_COUNT      (STAGE_FLASH_BYTES / MSC_BLOCK_BYTES)
#define ACTIVE_ROM_BYTES     (4u * 1024u * 1024u)
#define ACTIVE_SMS_BYTES     (2u * 1024u * 1024u)
