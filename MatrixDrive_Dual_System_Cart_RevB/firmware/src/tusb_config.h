/* SPDX-License-Identifier: MIT */
#pragma once

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Pico SDK supplies CFG_TUSB_MCU and CFG_TUSB_OS for the selected RP2350
 * platform. Defining them here causes conflicting command-line definitions on
 * current SDK releases.
 */
#define CFG_TUSB_RHPORT0_MODE     (OPT_MODE_DEVICE | OPT_MODE_FULL_SPEED)
#define CFG_TUD_ENDPOINT0_SIZE    64
#define CFG_TUD_MSC               1
#define CFG_TUD_MSC_EP_BUFSIZE    512

#ifdef __cplusplus
}
#endif
