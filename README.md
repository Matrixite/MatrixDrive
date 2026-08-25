# MatrixDrive

[![Build, test, and package](https://github.com/Matrixite/MatrixDrive/actions/workflows/build-test-package.yml/badge.svg)](https://github.com/Matrixite/MatrixDrive/actions/workflows/build-test-package.yml)

**MatrixDrive Revision B** is an open hardware prototype for a USB-loadable Mega Drive/Genesis cartridge that can also run Master System software on compatible consoles. It combines an RP2350B installer, parallel NOR ROM, an instant-on CPLD mapper, and battery-free FRAM saves.

[Download the current source and prebuilt firmware package](https://github.com/Matrixite/MatrixDrive/raw/refs/heads/main/MatrixDrive_Dual_System_Cart_RevB_Codemasters_64K_FRAM.zip)

> [!IMPORTANT]
> This repository is an **engineering prototype**, not a fabrication-ready or production-tested cartridge. The included KiCad board is a mechanical/placement template and is intentionally unrouted. Complete the schematic, CPLD pin assignment/fitting, timing analysis, and staged hardware bring-up before fabrication or console use.

## What it supports

| Mode | Image types | Maximum image | Mapping |
| --- | --- | ---: | --- |
| Mega Drive / Genesis | `.BIN`, `.MD`, `.GEN` | 4 MiB | Linear ROM at `$000000-$3FFFFF` |
| Master System | `.SMS` | 2 MiB | Sega or Codemasters mapper, selected by SW4 |

The Master System mode is intended for a Mega Drive/Genesis cartridge slot with working SMS compatibility, similar to the electrical role of a Power Base Converter. It is not mechanically compatible with a standalone Master System cartridge slot.

### Highlights

- USB-C drag-and-drop ROM loading through a FAT16 volume named `MATRIXDRV`.
- RP2350B firmware built with the Raspberry Pi Pico SDK and TinyUSB.
- 32-Mbit x16 active parallel NOR for deterministic console-side ROM reads.
- ATF1508ASV CPLD for instant-on mode selection and SMS bank mapping.
- Sega and Codemasters SMS mapper profiles selected by a power-off switch.
- 64 KiB battery-free save memory using two 32 KiB FM18W08 parallel FRAMs.
- Dedicated Master System Pause/NMI button.
- 5 V/3.3 V translation, USB/console power isolation, and bus isolation.
- Automated host, mapper-model, RTL, firmware-build, and packaging checks.

## SMS mapper behavior

SW4 selects the mapper before console power is applied. Mapper selection is hardware-controlled; firmware does not auto-detect it.

| Profile | Mapper writes | Reset ROM banks | FRAM window |
| --- | --- | --- | --- |
| Sega | `$FFFC-$FFFF` | 0, 1, 2 | 16 KiB at `$8000-$BFFF`; lower 32 KiB of FRAM is addressable |
| Codemasters | Exact writes at `$0000`, `$4000`, `$8000` | 0, 1, 0 | 8 KiB at `$A000-$BFFF`; eight banks expose all 64 KiB |

For the Codemasters profile, writing bit 7 at `$4000` enables FRAM and bits 2:0 select one of eight 8 KiB banks. ROM remains visible at `$8000-$9FFF`, and enabling FRAM preserves the previous slot-1 ROM bank.

See [Master System mode](MatrixDrive_Dual_System_Cart_RevB/docs/master-system-mode.md) for the complete register and storage behavior.

## Loading a ROM

1. Remove the cartridge from the console.
2. Connect it to a computer over USB-C.
3. Delete the previous ROM from `MATRIXDRV` and copy one supported image.
4. Safely eject the drive and wait for the steady green completion indication.
5. Disconnect USB.
6. With the console powered off, select **MD** or **SMS** using SW2.
7. For an SMS image, select **SEGA** or **CODEMASTERS** using SW4.
8. Insert the cartridge, then power on the console.

> [!WARNING]
> Never move SW2 or SW4 while powered. Never connect USB while the cartridge is inserted in a console.

## Image requirements

- Mega Drive/Genesis images must use normal big-endian byte order and contain `SEGA` at offset `0x100`.
- Interleaved `.SMD` images are not accepted.
- Headerless SMS images must contain `TMR SEGA` at `0x1FF0`, `0x3FF0`, or `0x7FF0`.
- Copier headers must be removed before loading.
- Use only software you are legally entitled to use.

## Repository layout

| Path | Contents |
| --- | --- |
| [`MatrixDrive_Dual_System_Cart_RevB/`](MatrixDrive_Dual_System_Cart_RevB/) | Main hardware, firmware, CPLD, tools, and documentation |
| [`cpld/`](MatrixDrive_Dual_System_Cart_RevB/cpld/) | Dual-profile mapper RTL, reference model, and RTL testbench |
| [`firmware/`](MatrixDrive_Dual_System_Cart_RevB/firmware/) | RP2350B/Pico SDK USB installer firmware |
| [`hardware/`](MatrixDrive_Dual_System_Cart_RevB/hardware/) | BOM, electrical netlist, pinout, and KiCad placement template |
| [`docs/`](MatrixDrive_Dual_System_Cart_RevB/docs/) | Architecture, SMS mapping, USB workflow, and bring-up guidance |
| [`tools/`](MatrixDrive_Dual_System_Cart_RevB/tools/) | Project validator and KiCad template generator |
| [Build workflow](.github/workflows/build-test-package.yml) | GitHub Actions build, test, and package pipeline |

The [full design README](MatrixDrive_Dual_System_Cart_RevB/README.md) contains additional component and compatibility details.

## Build and test

The GitHub Actions workflow uses Ubuntu, Pico SDK 2.3.0, the Arm GNU toolchain, CMake/Ninja, and Icarus Verilog.

To run the project checks locally:

```sh
cd MatrixDrive_Dual_System_Cart_RevB
python3 tools/generate_kicad_pcb.py
python3 tools/validate_project.py
```

To build the firmware:

```sh
export PICO_SDK_PATH=/absolute/path/to/pico-sdk
cmake -S MatrixDrive_Dual_System_Cart_RevB/firmware -B build/firmware -DPICO_BOARD=matrixdrive -DPICO_PLATFORM=rp2350-arm-s -DCMAKE_BUILD_TYPE=Release
cmake --build build/firmware
```

Expected firmware outputs include `matrixdrive.uf2`, `.bin`, `.elf`, and `.hex`.

The automated pipeline checks:

- electrical/static project consistency;
- FAT16 and ROM-installer host C tests;
- Sega and Codemasters Python mapper behavior;
- Icarus Verilog RTL simulation;
- complete RP2350B firmware compilation;
- creation of the downloadable project ZIP.

## Engineering status and known limits

The source and automated tests pass, but physical hardware validation is still required. Before treating the design as buildable:

- capture and review a complete schematic;
- assign, fit, and verify all ATF1508ASV pins;
- confirm CPLD resource usage and worst-case timing;
- verify exact package footprints and cartridge-edge geometry;
- route the PCB and run electrical/design-rule checks;
- validate NOR and FRAM transactions on a current-limited breakout;
- capture real-console timing for both mapper profiles and save-memory access.

Not currently implemented: Korean, multicart, or game-specific SMS mappers; FM sound; light-gun support; Mega Drive save hardware; and Sega mapper RAM-at-`$C000` mode.

Start with [Safety and bring-up](MatrixDrive_Dual_System_Cart_RevB/docs/safety-and-bringup.md) before connecting prototype hardware to a console.

## Technical references

- [Raspberry Pi RP2350 documentation](https://www.raspberrypi.com/documentation/microcontrollers/microcontroller-chips.html)
- [Microchip ATF1508ASV](https://www.microchip.com/en-us/product/atf1508asv)
- [Infineon FM18W08 FRAM](https://www.infineon.com/part/FM18W08-SG)
- [MAME Sega 8-bit cartridge mapper implementation](https://github.com/mamedev/mame/blob/master/src/devices/bus/sega8/rom.cpp)
- [SMS Power mapper documentation](https://www.smspower.org/Development/Mappers)
