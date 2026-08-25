/* SPDX-License-Identifier: MIT */
#pragma once

#include <stdbool.h>

typedef enum {
    STATUS_OFF = 0,
    STATUS_USB_MOUNTED,
    STATUS_USB_WRITING,
    STATUS_PROGRAMMING,
    STATUS_SUCCESS,
    STATUS_BAD_IMAGE,
    STATUS_FLASH_ERROR
} status_mode_t;

void status_init(void);
void status_set(status_mode_t mode);
void status_task(void);
status_mode_t status_get(void);

