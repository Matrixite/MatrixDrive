/* SPDX-License-Identifier: MIT */
#pragma once

#include <stdbool.h>
#include <stdint.h>

void parallel_nor_console_safe_state(void);
void parallel_nor_enter_programming(void);
void parallel_nor_leave_programming(void);
bool parallel_nor_chip_erase(void);
bool parallel_nor_program_word(uint32_t word_address, uint16_t value);
uint16_t parallel_nor_read_word(uint32_t word_address);

