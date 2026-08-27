# MatrixDrive

[![Build, test, and package](https://github.com/Matrixite/MatrixDrive/actions/workflows/build-test-package.yml/badge.svg)](https://github.com/Matrixite/MatrixDrive/actions/workflows/build-test-package.yml)

**MatrixDrive Revision B** is an open hardware prototype for a USB-loadable Mega Drive/Genesis cartridge that can also supply cartridge ROM to a real 32X, run Master System software on compatible consoles, and operate as the upper cartridge in Sonic & Knuckles lock-on mode. It combines an RP2350B installer, parallel NOR ROM, an instant-on CPLD mapper, and battery-free FRAM saves.

The repository also contains an **experimental Revision C MegaCD FPGA ODE** architecture. Its target is MegaSD-style operation from the Mega Drive cartridge slot: the real console supplies the base Mega Drive hardware while the cartridge emulates the Mega-CD subsystem and streams legally obtained `.ISO` or `.CUE` plus `.BIN` images from microSD. Revision C is currently a source and simulation platform; it does not yet boot retail Mega-CD software.

[Download the current source and prebuilt firmware package](https://github.com/Matrixite/MatrixDrive/raw/refs/heads/main/MatrixDrive_Dual_System_Cart_RevB_LockOn_Codemasters_64K_FRAM.zip)

> [!IMPORTANT]
> This repository is an **engineering prototype**, not a fabrication-ready or production-tested cartridge. The included KiCad board is a mechanical/placement template and is intentionally unrouted. Complete the schematic, CPLD pin assignment/fitting, timing analysis, shell measurements, and staged hardware bring-up before fabrication or console use.

## What it supports

| Mode | Image types | Maximum image | Mapping |
| --- | --- | ---: | --- |
| Mega Drive / Genesis | `.BIN`, `.MD`, `.GEN` | 4 MiB | Linear ROM; power-of-two images up to 2 MiB are mirrored for lock-on |
| 32X through real 32X hardware | `.32X` | 4 MiB | Linear x16 ROM; smaller power-of-two images are mirrored to 4 MiB |
| Sonic & Knuckles upper slot | Mega Drive images | 2 MiB recommended | Sonic 2 ROM or Sonic 3 ROM with dedicated 8 KiB save FRAM |
| Master System | `.SMS` | 2 MiB | Sega or Codemasters mapper selected by SW4 |

Master System mode requires a Mega Drive/Genesis revision with working SMS compatibility. It is not mechanically compatible with a standalone Master System cartridge slot. SMS mode is not supported through the Sonic & Knuckles upper slot.

## Experimental MegaCD FPGA ODE

[`MatrixDrive_MegaCD_FPGA_RevC/`](MatrixDrive_MegaCD_FPGA_RevC/) is a separate, clean-room development path for cartridge-slot Mega-CD emulation. It does not replace or modify the working Revision B source tree.

The current prototype includes:

- a candidate Cyclone V, RP2350B, SDRAM, microSD, USB-C, DAC, and cartridge-bus hardware architecture;
- a synthesizable Mega Drive bus bridge with open-drain `/DTACK` control;
- a raw 2,352-byte disc-sector handoff buffer;
- a deterministic `.ISO` and `.CUE`/`.BIN` manifest generator, including mixed data/audio and multi-file discs;
- self-checking parser and SystemVerilog simulations; and
- a documented interface for later integration of a license-compatible Mega-CD FPGA core.

The full Mega-CD gate array, Sub-68000, Word RAM arbitration, CDC/CDD behavior, graphics engine, PCM/CDDA audio path, BIOS mapping, and cartridge-specific interrupt/boot assist are not integrated yet. No Sega BIOS, commercial game image, proprietary MegaSD source, or proprietary bitstream is included.

### Highlights

- USB-C drag-and-drop ROM loading through a FAT16 volume named `MATRIXDRV`.
- RP2350B firmware built with the Raspberry Pi Pico SDK and TinyUSB.
- 32-Mbit x16 active parallel NOR for deterministic console-side ROM reads.
- Explicit `.32X` validation and a full 4 MiB linear cartridge-ROM profile for use through real 32X hardware.
- Sonic & Knuckles upper-slot ROM mirroring for power-of-two images up to 2 MiB.
- Dedicated odd-byte Sonic 3 save window at `$200001-$203FFF`.
- ATF1508ASV CPLD for instant-on mode selection and mapper/save decoding.
- Sega and Codemasters SMS mapper profiles selected by a power-off switch.
- 64 KiB battery-free SMS save memory using two 32 KiB FM18W08 FRAMs.
- Dedicated FM18W08 for Sonic 3 lock-on saves; 8 KiB of it is decoded.
- Dedicated Master System Pause/NMI button.
- 5 V/3.3 V translation, USB/console power isolation, and bus isolation.
- Automated host, mapper-model, RTL, firmware-build, and packaging checks.

## Selector behavior

SW4 has a different meaning in MD and SMS modes. Move it only while all power is disconnected.

| SW2 | SW4 low | SW4 high |
| --- | --- | --- |
| MD | Linear ROM / 32X / Sonic 2 lock-on | Linear ROM plus Sonic 3 save FRAM |
| SMS | Sega mapper | Codemasters mapper |

## Sonic & Knuckles lock-on

For **Sonic 2 & Knuckles**, load a normal Sonic 2 image, set SW2 to **MD**, and set SW4 low to **LINEAR**. The installer mirrors an even-sized power-of-two image throughout the 2 MiB upper-cartridge window.

For **Sonic 3 & Knuckles**, load a normal Sonic 3 image, set SW2 to **MD**, and set SW4 high to **S3 SAVE**. U13 then replaces only odd-byte addresses `$200001-$203FFF` with the dedicated U20 FRAM and disables the unused high data byte during those cycles.

See [Sonic & Knuckles lock-on mode](MatrixDrive_Dual_System_Cart_RevB/docs/sonic-knuckles-lock-on.md) for the exact mapping, switch positions, and physical-fit requirements.

## 32X through real hardware

Load a `.32X` image, set SW2 to **MD**, set SW4 low to **LINEAR**, disconnect USB, and insert MatrixDrive into the cartridge slot of an unpowered real 32X. The 32X supplies the processors, boot ROM, registers, video, and audio hardware; MatrixDrive supplies only the byte-for-byte cartridge ROM.

The installer checks the standard `SEGA` header and the mandatory `MARS CHECK MODE` security marker, preserves the complete security/startup area, and exposes up to 4 MiB as linear x16 ROM. Do not use SW4 high: that position deliberately replaces part of the ROM range with the Sonic 3 save FRAM window.

See [32X cartridge mode](MatrixDrive_Dual_System_Cart_RevB/docs/32x-mode.md) for exact mapping, limits, and the required real-hardware bring-up procedure.

## SMS mapper behavior

| Profile | Mapper writes | Reset ROM banks | FRAM window |
| --- | --- | --- | --- |
| Sega | `$FFFC-$FFFF` | 0, 1, 2 | 16 KiB at `$8000-$BFFF`; lower 32 KiB is addressable |
| Codemasters | Exact writes at `$0000`, `$4000`, `$8000` | 0, 1, 0 | 8 KiB at `$A000-$BFFF`; eight banks expose all 64 KiB |

For Codemasters, writing bit 7 at `$4000` enables FRAM and bits 2:0 select one of eight 8 KiB banks. ROM remains visible at `$8000-$9FFF`, and enabling FRAM preserves the previous slot-1 ROM bank.

See [Master System mode](MatrixDrive_Dual_System_Cart_RevB/docs/master-system-mode.md) for the full register behavior.

## Loading a ROM

1. Remove MatrixDrive from the console or lock-on cartridge.
2. Connect MatrixDrive to a computer over USB-C.
3. Delete the previous ROM from `MATRIXDRV` and copy one supported image.
4. Safely eject the drive and wait for the steady green completion indication.
5. Disconnect USB.
6. With power off, choose MD or SMS with SW2 and the required profile with SW4.
7. Insert MatrixDrive directly into the console, into the Sonic & Knuckles upper slot for MD lock-on use, or into the cartridge slot of a real 32X for `.32X` use.
8. Insert Sonic & Knuckles or the 32X into the console if used, then power on.

> [!WARNING]
> Never move SW2 or SW4 while powered. Never connect USB while MatrixDrive is inserted into a console, 32X, or Sonic & Knuckles cartridge. Never hot-plug any part of the cartridge stack.

## Image requirements

- Mega Drive/Genesis images must use normal big-endian byte order, contain `SEGA` at offset `0x100`, and fit in 4 MiB.
- 32X images must use `.32X`, fit in 4 MiB, be a multiple of four bytes, contain `SEGA` at `0x100`, and contain `MARS CHECK MODE` at `0x3C0`.
- Lock-on images should be even-sized powers of two no larger than 2 MiB.
- Interleaved `.SMD` images are not accepted.
- Headerless SMS images must contain `TMR SEGA` at `0x1FF0`, `0x3FF0`, or `0x7FF0`.
- Copier headers must be removed before loading.
- Use only software you are legally entitled to use.

## Repository layout

| Path | Contents |
| --- | --- |
| [`MatrixDrive_Dual_System_Cart_RevB/`](MatrixDrive_Dual_System_Cart_RevB/) | Main hardware, firmware, CPLD, tools, and documentation |
| [`MatrixDrive_MegaCD_FPGA_RevC/`](MatrixDrive_MegaCD_FPGA_RevC/) | Experimental MegaSD-style FPGA ODE architecture, image parser, RTL shell, and tests |
| [`cpld/`](MatrixDrive_Dual_System_Cart_RevB/cpld/) | MD/32X ROM path, SMS mappers, lock-on save decoder, model, and RTL testbench |
| [`firmware/`](MatrixDrive_Dual_System_Cart_RevB/firmware/) | RP2350B/Pico SDK USB installer, 32X validation, and ROM mirroring |
| [`hardware/`](MatrixDrive_Dual_System_Cart_RevB/hardware/) | BOM, electrical netlist, pinout, and KiCad placement template |
| [`docs/`](MatrixDrive_Dual_System_Cart_RevB/docs/) | Architecture, lock-on/SMS mapping, workflow, and bring-up guidance |
| [`tools/`](MatrixDrive_Dual_System_Cart_RevB/tools/) | Project validator and KiCad template generator |
| [Build workflow](.github/workflows/build-test-package.yml) | GitHub Actions build, test, and package pipeline |

The [full design README](MatrixDrive_Dual_System_Cart_RevB/README.md) contains additional component and compatibility details.

## Build and test

The GitHub Actions workflow uses Ubuntu, Pico SDK 2.3.0, the Arm GNU toolchain, CMake/Ninja, and Icarus Verilog.

```sh
cd MatrixDrive_Dual_System_Cart_RevB
python3 tools/generate_kicad_pcb.py
python3 tools/validate_project.py
```

Firmware build:

```sh
export PICO_SDK_PATH=/absolute/path/to/pico-sdk
cmake -S MatrixDrive_Dual_System_Cart_RevB/firmware -B build/firmware -DPICO_BOARD=matrixdrive -DPICO_PLATFORM=rp2350-arm-s -DCMAKE_BUILD_TYPE=Release
cmake --build build/firmware
```

MegaCD FPGA Rev C prototype validation:

```sh
cd MatrixDrive_MegaCD_FPGA_RevC
python3 tools/validate_project.py
```

The automated pipeline checks electrical/static consistency, FAT16 and installer host code, 32X validation and 4 MiB ROM mirroring, lock-on ROM mirroring, Sega/Codemasters models, Sonic 3 FRAM decode, MegaCD disc manifests and interface RTL, the complete RP2350B firmware build, and package creation.

## Software-only test status

MatrixDrive has been tested in software, but it has not yet been tested on a fabricated cartridge or real console. The following checks currently pass:

- FAT16 USB-volume and dual-format ROM installer host tests.
- Mega Drive/Genesis ROM validation and simulated parallel-NOR programming.
- Synthetic `.32X` header/security validation, byte packing, full 4 MiB mirroring, and top-of-ROM RTL addressing.
- Byte-for-byte verification of a 2 MiB Sonic 3 image after simulated installation.
- Power-of-two ROM mirroring across the 2 MiB Sonic & Knuckles upper-cartridge window.
- Sonic 3 odd-byte save decoding to the dedicated 8 KiB FRAM window.
- Sega and Codemasters Master System mapper reference-model tests.
- Codemasters 64 KiB FRAM enable, banking, and ROM-window behavior.
- CPLD RTL simulation for Mega Drive, lock-on, Sega SMS, and Codemasters SMS modes.
- A two-ROM lock-on emulator test using legally obtained Sonic 3 and Sonic & Knuckles images. It reached the combined Sonic 3 & Knuckles title screen and opening sequence, confirming the expected software mapping path.
- MegaCD `.ISO` and `.CUE`/`.BIN` parser tests covering raw data, mixed-mode audio, pregaps, and multi-file discs.
- MegaCD cartridge-bridge and raw-sector-buffer RTL simulations.

No commercial ROM images are included in this repository. These results verify the implemented logic and software behavior only; cartridge fit, 32X security/timing on a physical adapter, voltage translation, power isolation, save retention, and operation on real Sega hardware remain unverified.

## Engineering status and known limits

The source and automated tests pass, but no physical MatrixDrive PCB or Sonic & Knuckles stack has been validated. Before treating the design as buildable:

- capture and review a complete schematic;
- assign, fit, and verify all ATF1508ASV pins and resources;
- confirm worst-case CPLD, NOR, translator, and FRAM timing;
- measure the upper-slot opening and latch/door clearances on a real Sonic & Knuckles cartridge;
- measure cartridge fit and capture read timing in a real 32X cartridge slot;
- verify the 64-contact edge, PCB thickness, bevel, shell, and insertion depth against donor hardware;
- route the PCB and run electrical/design-rule checks;
- validate direct-console operation before testing through lock-on hardware;
- capture real-console timing and current for both lock-on profiles.

Only the Sonic 3 odd-byte MD save layout is implemented in Revision B. Generic Mega Drive or 32X SRAM/EEPROM saves are not implemented. 32X CD software, ROMs larger than 4 MiB, enhancement hardware, Korean/multicart/game-specific SMS mappers, FM sound, light-gun support, and Sega mapper RAM-at-`$C000` mode are also outside Revision B. Revision C targets Mega-CD image playback, but remains pre-hardware and pre-game-boot until the complete Mega-CD core and cartridge interrupt/boot path are integrated.

Start with [Safety and bring-up](MatrixDrive_Dual_System_Cart_RevB/docs/safety-and-bringup.md).

## Technical references

- [Genesis Plus GX cartridge implementation](https://github.com/ekeeke/Genesis-Plus-GX/blob/master/core/cart_hw/md_cart.c)
- [MiSTer Mega-CD FPGA core](https://github.com/MiSTer-devel/MegaCD_MiSTer)
- [Sega 32X Hardware Manual transcription](https://github.com/matiaszanolli/sega-vr-disasm/blob/master/docs/32x-hardware-manual.md)
- [Raspberry Pi RP2350 documentation](https://www.raspberrypi.com/documentation/microcontrollers/microcontroller-chips.html)
- [Microchip ATF1508ASV](https://www.microchip.com/en-us/product/atf1508asv)
- [Infineon FM18W08 FRAM](https://www.infineon.com/part/FM18W08-SG)
- [TI SN74LVC1T45](https://www.ti.com/product/SN74LVC1T45)
