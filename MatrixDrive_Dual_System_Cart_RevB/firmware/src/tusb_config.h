/* SPDX-License-Identifier: MIT */
#pragma once

#ifdef __cplusplus
extern "C" {
#endif

#define CFG_TUSB_MCU              OPT_MCU_RP2350
#define CFG_TUSB_OS               OPT_OS_NONE
#define CFG_TUSB_RHPORT0_MODE     (OPT_MODE_DEVICE | OPT_MODE_FULL_SPEED)
#define CFG_TUD_ENDPOINT0_SIZE    64
#define CFG_TUD_MSC               1
#define CFG_TUD_MSC_EP_BUFSIZE    512

#ifdef __cplusplus
}
#endif

