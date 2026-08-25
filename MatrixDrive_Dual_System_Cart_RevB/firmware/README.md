# Firmware

The firmware uses the Raspberry Pi Pico C/C++ SDK and TinyUSB. It targets the
RP2350B package because the parallel ROM bus consumes GPIO0 through GPIO39 and
the QFN-80 device supplies GPIO40 through GPIO47 for staging flash, sensing and
indicators.

## Build

```sh
export PICO_SDK_PATH=/absolute/path/to/pico-sdk
cmake -S . -B build -DPICO_BOARD=matrixdrive
cmake --build build
```

The output is `build/matrixdrive.uf2` plus ELF, BIN and HEX files. Fit the board's
SWD header for the first load; later firmware can also be loaded through the
RP2350 boot ROM when the hardware exposes its boot-select condition.

## Source layout

- `main.c` selects console-safe or USB programming operation.
- `msc_disk.c` implements the TinyUSB Mass Storage callbacks.
- `spi_nor.c` provides a 4 KiB cached block device on the staging flash.
- `fat16.c` formats and scans the staging volume without a dynamic allocator.
- `parallel_nor.c` programs and verifies the S29GL032N-compatible active ROM.
- `rom_installer.c` validates and streams a selected ROM into the active flash,
  packing MD/32X images x16 and SMS images one byte per word. Explicit `.32X`
  files also require the standard header/security marker and are mirrored
  through the complete 4 MiB cartridge range when appropriate.
- `usb_descriptors.c` defines a single Full-Speed MSC interface.

## Important implementation note

This is first-pass prototype firmware and has not been executed on the custom
board. Compile warnings should be treated as errors, and the active-NOR command
set must be checked against the exact suffix of the fitted flash before running
an erase or program operation. Keep the hardware write-enable pullup fitted
during all early tests. Firmware does not move the physical MD/SMS switch; set
SW2 only while the board is unpowered.
