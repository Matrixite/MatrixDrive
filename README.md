# MatrixDrive

[![Build, test, and package](https://github.com/Matrixite/MatrixDrive/actions/workflows/build-test-package.yml/badge.svg)](https://github.com/Matrixite/MatrixDrive/actions/workflows/build-test-package.yml)

MatrixDrive started with a simple idea: make a Mega Drive/Genesis cartridge
that you can plug into a computer with USB-C, copy a game onto like a flash
drive, and then use in a real console.

Revision B takes that idea quite a bit further. It is also designed to run
Master System software on compatible Mega Drive hardware, supply ROM data to a
real 32X, work in the upper slot of Sonic & Knuckles, and keep supported save
data in battery-free FRAM.

- [Download the current source and prebuilt firmware package](https://github.com/Matrixite/MatrixDrive/raw/refs/heads/main/MatrixDrive_Dual_System_Cart_RevB_LockOn_Codemasters_64K_FRAM.zip)
- [Download the standalone KiCad project](https://github.com/Matrixite/MatrixDrive/raw/refs/heads/main/MatrixDrive_RevB_KiCad_Project.zip)

> [!IMPORTANT]
> MatrixDrive is still an engineering prototype. The software and logic have
> been tested, and the PCB has a preliminary fully connected route, but no
> physical cartridge has been built or tested in a console. Several package pin
> assignments still need to be verified and the board has not passed KiCad DRC.
> Please do not send the current PCB straight to a manufacturer.

## What MatrixDrive can do

| Mode | Files | Maximum size | What happens |
| --- | --- | ---: | --- |
| Mega Drive / Genesis | `.BIN`, `.MD`, `.GEN` | 4 MiB | The game is presented as linear cartridge ROM |
| 32X with real 32X hardware | `.32X` | 4 MiB | MatrixDrive supplies the ROM while the real 32X provides the 32X hardware |
| Sonic & Knuckles upper slot | Mega Drive images | 2 MiB recommended | Supports Sonic 2 lock-on and Sonic 3 with its dedicated save area |
| Master System | `.SMS` | 2 MiB | Uses either the Sega or Codemasters mapper selected by SW4 |

Master System mode should work on standard Mega Drive/Genesis Model 1 and Model
2 consoles. It will not work on an unmodified Genesis 3 or Sega Nomad because
their cartridge-port Master System mode pin is disconnected. The JVC X'Eye can
run SMS cartridges through an adapter, but its reset circuit prevents SMS games
from running from a Genesis flash cartridge such as MatrixDrive. Compatibility
with other all-in-one, portable, licensed, or clone systems has not yet been
verified. MatrixDrive also does not fit a standalone Master System cartridge
slot, and SMS mode cannot run through a 32X or the Sonic & Knuckles upper slot.

## How it works

When MatrixDrive is connected to a computer, it appears as a FAT16 drive called
`MATRIXDRV`. The RP2350B checks the game image and programs it into parallel NOR
flash. After USB is disconnected, the CPLD takes over and responds to the
console immediately, without waiting for the microcontroller to boot.

The main hardware is:

- an RP2350B for USB, file handling, validation, and flash programming;
- 32-Mbit x16 parallel NOR flash for predictable cartridge ROM reads;
- an ATF1508ASV CPLD for mode selection, address decoding, and SMS mapping;
- level translators and bus isolation for the 5 V console and 3.3 V logic;
- two FRAM devices providing 64 KiB of battery-free SMS save storage;
- a separate FRAM for the 8 KiB Sonic 3 lock-on save window;
- USB/console power isolation, status LEDs, SWD/UART, and test points.

## Loading a game

1. Remove MatrixDrive from the console, 32X, or lock-on cartridge.
2. Connect it to your computer with USB-C.
3. Open the `MATRIXDRV` drive, delete the old game, and copy over one supported
   image.
4. Safely eject the drive and wait for the green completion light.
5. Disconnect USB completely.
6. With all power off, select MD or SMS with SW2 and choose the required profile
   with SW4.
7. Insert the cartridge, then power on the console.

> [!WARNING]
> Never connect USB while MatrixDrive is fitted to a console, 32X, or Sonic &
> Knuckles cartridge. Never move SW2 or SW4 while powered, and never hot-plug any
> part of the cartridge stack.

## Switch settings

SW4 changes purpose depending on the position of SW2:

| SW2 | SW4 low | SW4 high |
| --- | --- | --- |
| MD | Linear ROM, 32X, or Sonic 2 lock-on | Linear ROM with Sonic 3 save FRAM |
| SMS | Sega mapper | Codemasters mapper |

Always change these switches with USB and console power disconnected.

## Sonic & Knuckles lock-on

For **Sonic 2 & Knuckles**, copy a normal Sonic 2 image, set SW2 to **MD**, and
set SW4 low to **LINEAR**. Power-of-two images up to 2 MiB are mirrored across
the upper-cartridge ROM window.

For **Sonic 3 & Knuckles**, copy a normal Sonic 3 image, set SW2 to **MD**, and
set SW4 high to **S3 SAVE**. MatrixDrive then maps the dedicated save FRAM over
odd-byte addresses `$200001-$203FFF` while leaving the rest of the ROM visible.

Read [Sonic & Knuckles lock-on mode](MatrixDrive_Dual_System_Cart_RevB/docs/sonic-knuckles-lock-on.md)
for the exact mapping, switch positions, and physical-fit checks.

## Using a real 32X

MatrixDrive is not trying to reproduce a 32X. A real 32X still supplies its
processors, boot ROM, registers, video, and audio hardware; MatrixDrive only
supplies the cartridge ROM.

Copy a `.32X` image, set SW2 to **MD**, leave SW4 low, disconnect USB, and fit
MatrixDrive to an unpowered 32X. The installer checks the `SEGA` header and
`MARS CHECK MODE` marker before accepting the image.

Do not use SW4 high for 32X software because that setting deliberately replaces
part of the ROM address range with the Sonic 3 save window. More detail is in
[32X cartridge mode](MatrixDrive_Dual_System_Cart_RevB/docs/32x-mode.md).

## Master System mapping and saves

| Profile | Mapper writes | Starting ROM banks | Save window |
| --- | --- | --- | --- |
| Sega | `$FFFC-$FFFF` | 0, 1, 2 | 16 KiB at `$8000-$BFFF` |
| Codemasters | `$0000`, `$4000`, `$8000` | 0, 1, 0 | 8 KiB at `$A000-$BFFF` |

In Codemasters mode, bit 7 of the `$4000` write enables FRAM and bits 2:0 choose
one of eight 8 KiB banks. This makes all 64 KiB of SMS save storage available
without hiding the ROM at `$8000-$9FFF`.

See [Master System mode](MatrixDrive_Dual_System_Cart_RevB/docs/master-system-mode.md)
for the full register and banking behaviour.

## Supported image rules

- Mega Drive/Genesis images must be normal big-endian ROMs, contain `SEGA` at
  offset `0x100`, and fit within 4 MiB.
- 32X images must use `.32X`, contain `SEGA` at `0x100` and `MARS CHECK MODE` at
  `0x3C0`, be a multiple of four bytes, and fit within 4 MiB.
- Lock-on images should be even-sized powers of two no larger than 2 MiB.
- Headerless SMS images need `TMR SEGA` at `0x1FF0`, `0x3FF0`, or `0x7FF0`.
- Interleaved `.SMD` files and copier headers are not supported.
- Only use game images that you are legally entitled to use.

No commercial ROM images are included in this repository.

## What has been tested

The project is automatically rebuilt and tested on every change. The passing
software-only tests currently cover:

- the FAT16 USB drive and ROM installer;
- Mega Drive, Master System, and 32X image validation;
- simulated NOR programming and ROM mirroring;
- Sega and Codemasters SMS mapper behaviour;
- Codemasters FRAM enabling and all eight save banks;
- Sonic 2/Sonic 3 lock-on mapping and the Sonic 3 save decoder;
- CPLD RTL simulation for MD, SMS, 32X ROM access, and lock-on modes;
- a complete RP2350B firmware build;
- a two-ROM emulator test that reached the combined Sonic 3 & Knuckles title
  screen and opening sequence.

These tests show that the intended software and logic paths behave correctly.
They cannot prove cartridge fit, signal timing, voltage translation, power
isolation, save retention, or operation on real Sega hardware.

## PCB status

The KiCad project contains a complete logical schematic and a preliminary
eight-layer PCB route. The routing report currently records all 188 routable
nets connected, using six signal layers plus dedicated ground and 3.3 V planes.

Before a board can be considered ready to build, it still needs:

- verified physical pin assignments and manufacturer footprints for the
  RP2350B, CPLD, NOR, translators, and FRAM devices;
- CPLD fitting, resource checks, and worst-case timing analysis;
- KiCad ERC/DRC after refilling the copper zones;
- USB differential-pair and signal/power-integrity review;
- cartridge-edge, PCB-thickness, bevel, shell, and insertion measurements;
- staged bench testing before it is connected to any console.

Only the Sonic 3 odd-byte save layout is implemented for Mega Drive software.
Generic Mega Drive or 32X SRAM/EEPROM saves, ROMs larger than 4 MiB,
enhancement hardware, unusual regional or game-specific SMS mappers, light-gun
support, and Sega mapper RAM-at-`$C000` mode are outside this revision.

Start with [Safety and bring-up](MatrixDrive_Dual_System_Cart_RevB/docs/safety-and-bringup.md)
before attempting any hardware test.

## Project layout

| Path | What you will find there |
| --- | --- |
| [`MatrixDrive_Dual_System_Cart_RevB/`](MatrixDrive_Dual_System_Cart_RevB/) | Main Revision B project |
| [`cpld/`](MatrixDrive_Dual_System_Cart_RevB/cpld/) | Mapper RTL, reference model, and testbench |
| [`firmware/`](MatrixDrive_Dual_System_Cart_RevB/firmware/) | RP2350B USB installer firmware |
| [`hardware/`](MatrixDrive_Dual_System_Cart_RevB/hardware/) | KiCad files, BOM, pinout, netlist, and routing report |
| [`docs/`](MatrixDrive_Dual_System_Cart_RevB/docs/) | Architecture, compatibility, and bring-up notes |
| [`tools/`](MatrixDrive_Dual_System_Cart_RevB/tools/) | Project generator, router, and validation scripts |

The [full design README](MatrixDrive_Dual_System_Cart_RevB/README.md) contains
the component-level details and additional design notes.

## Building and testing the project

You will need Python 3, the Raspberry Pi Pico SDK 2.3.0, an Arm GNU toolchain,
CMake/Ninja, and Icarus Verilog.

```sh
cd MatrixDrive_Dual_System_Cart_RevB
python3 tools/generate_kicad_project.py
python3 tools/route_kicad_pcb.py
python3 tools/validate_project.py
```

To build the RP2350B firmware:

```sh
export PICO_SDK_PATH=/absolute/path/to/pico-sdk
cmake -S firmware -B ../build/firmware -G Ninja \
  -DPICO_BOARD=matrixdrive \
  -DPICO_PLATFORM=rp2350-arm-s \
  -DCMAKE_BUILD_TYPE=Release
cmake --build ../build/firmware
```

## Technical references

- [Genesis Plus GX cartridge implementation](https://github.com/ekeeke/Genesis-Plus-GX/blob/master/core/cart_hw/md_cart.c)
- [Sega 32X Hardware Manual transcription](https://github.com/matiaszanolli/sega-vr-disasm/blob/master/docs/32x-hardware-manual.md)
- [Raspberry Pi RP2350 documentation](https://www.raspberrypi.com/documentation/microcontrollers/microcontroller-chips.html)
- [Microchip ATF1508ASV](https://www.microchip.com/en-us/product/atf1508asv)
- [Infineon FM18W08 FRAM](https://www.infineon.com/part/FM18W08-SG)
- [TI SN74LVC1T45](https://www.ti.com/product/SN74LVC1T45)
