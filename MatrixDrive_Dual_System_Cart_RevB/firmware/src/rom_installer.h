/* SPDX-License-Identifier: MIT */
#pragma once

typedef enum {
    INSTALL_OK = 0,
    INSTALL_NO_IMAGE,
    INSTALL_BAD_IMAGE,
    INSTALL_STORAGE_ERROR,
    INSTALL_FLASH_ERROR
} install_result_t;

install_result_t rom_install_from_staging(void);

