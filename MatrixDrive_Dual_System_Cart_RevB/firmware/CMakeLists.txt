cmake_minimum_required(VERSION 3.13)

set(PICO_BOARD_HEADER_DIRS ${CMAKE_CURRENT_LIST_DIR}/boards)
include($ENV{PICO_SDK_PATH}/external/pico_sdk_import.cmake)

project(matrixdrive C CXX ASM)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

pico_sdk_init()

add_executable(matrixdrive
    src/main.c
    src/status.c
    src/spi_nor.c
    src/fat16.c
    src/parallel_nor.c
    src/rom_installer.c
    src/msc_disk.c
    src/usb_descriptors.c
)

target_include_directories(matrixdrive PRIVATE
    ${CMAKE_CURRENT_LIST_DIR}/src
)

target_compile_options(matrixdrive PRIVATE
    -Wall -Wextra -Werror -Wshadow -Wconversion
)

target_link_libraries(matrixdrive PRIVATE
    pico_stdlib
    pico_unique_id
    hardware_adc
    hardware_spi
    tinyusb_device
)

pico_enable_stdio_uart(matrixdrive 0)
pico_enable_stdio_usb(matrixdrive 0)
pico_add_extra_outputs(matrixdrive)

