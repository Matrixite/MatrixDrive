/* SPDX-License-Identifier: BSD-3-Clause */
#ifndef _BOARDS_MATRIXDRIVE_H
#define _BOARDS_MATRIXDRIVE_H

pico_board_cmake_set(PICO_PLATFORM, rp2350)

#define MATRIXDRIVE_REV_B
#define PICO_RP2350A 0

#define PICO_BOOT_STAGE2_CHOOSE_W25Q080 1
#ifndef PICO_FLASH_SPI_CLKDIV
#define PICO_FLASH_SPI_CLKDIV 2
#endif
pico_board_cmake_set_default(PICO_FLASH_SIZE_BYTES, (2 * 1024 * 1024))
#ifndef PICO_FLASH_SIZE_BYTES
#define PICO_FLASH_SIZE_BYTES (2 * 1024 * 1024)
#endif

pico_board_cmake_set_default(PICO_RP2350_A2_SUPPORTED, 1)
#ifndef PICO_RP2350_A2_SUPPORTED
#define PICO_RP2350_A2_SUPPORTED 1
#endif

#endif
