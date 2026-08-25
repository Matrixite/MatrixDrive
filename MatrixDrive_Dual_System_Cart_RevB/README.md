# MatrixDrive Dual-System USB Cartridge — Revision B

MatrixDrive Revision B is a prototype Mega Drive/Genesis cartridge that can
also run Sega Master System software on compatible Mega Drive/Genesis hardware.
Connect USB-C and it appears as a removable drive named `MATRIXDRV`; copy one
ROM, safely eject, and the RP2350B installs it into non-volatile parallel NOR.
The console reads the NOR through translators and an instant-on CPLD; it never
depends on microcontroller response time while a game is running.

## Supported images

| Console mode | File | Active image limit | Cartridge hardware |
| --- | --- | ---: | --- |
| Mega Drive / Genesis | `.BIN`, `.MD`, `.GEN` | 4 MiB | Linear `$000000-$3FFFFF` ROM |
| Master System | `.SMS` | 2 MiB | Sega mapper, registers `$FFFC-$FFFF` |

SMS images are stored one byte per x16 NOR word so the cartridge can present an
8-bit bus without a second ROM. The CPLD implements the normal Sega 16 KiB bank
mapper, the fixed first 1 KiB region, and two 16 KiB banks of non-volatile FRAM
save memory. Plain 8/16/32/48 KiB images and larger Sega-mapper images work.
Codemasters, Korean and other special mappers are outside Revision B's scope.

The intended host is a Mega Drive/Genesis with working Master System
compatibility. It is not shaped for a standalone Master System cartridge slot.
Some later console revisions and clones omit or alter Master System support.

## Normal use

1. Remove the cartridge from the console and connect USB-C.
2. Delete the previous ROM and copy one supported image to `MATRIXDRV`.
3. Safely eject the drive. Wait for a steady green LED while the active NOR is
   erased, repacked and verified.
4. Disconnect USB. With the console powered off, set `SW2` to **MD** for a Mega
   Drive image or **SMS** for a Master System image.
5. Insert the cartridge and power on. In SMS mode, press the cartridge's
   **PAUSE** button for games that use the Master System NMI pause input.

Never move the MD/SMS switch with the console powered. Never connect USB while
the cartridge is inserted. Hardware isolates the bus and supply domains, but a
console cannot boot while USB programming mode is active.

## Image validation

- Mega Drive images require `SEGA` at byte offset `0x100` and normal big-endian
  byte order. Interleaved `.SMD` images are rejected.
- Headerless `.SMS` images require `TMR SEGA` at a standard header position
  (`0x1FF0`, `0x3FF0`, or `0x7FF0`). Copier-headered images must be cleaned
  before use.
- Use only software you are legally entitled to use.

## Hardware summary

- RP2350B, USB Full-Speed Mass Storage and a 16 MiB FAT16 staging flash.
- S29GL032N-compatible 32-Mbit x16 active parallel NOR.
- ATF1508ASV-15AU100 CPLD for instant-on mode selection and SMS mapping.
- FM18W08 32 KiB x8 FRAM for SMS save RAM, no battery required.
- Dual-supply 5 V/3.3 V translation on every active cartridge signal.
- USB/console source isolation, USB-present bus isolation, PROGRAM and PAUSE
  buttons, and an MD/SMS power-off slide switch.

## Project contents

- `docs/architecture.md` — electrical and data-path architecture.
- `docs/master-system-mode.md` — mapper, storage layout and mode details.
- `docs/safety-and-bringup.md` — mandatory staged test procedure.
- `docs/usb-workflow.md` — drag-and-drop operation and indicators.
- `hardware/bom.csv`, `connector-pinout.csv`, `electrical-netlist.csv` —
  component and connection authorities.
- `hardware/MatrixDrive-RevB.kicad_pcb` — mechanical/placement-only template.
- `cpld/matrixdrive_mapper.v` — synthesizable mapper source and host model test.
- `firmware/` — RP2350/Pico SDK firmware source.

## Engineering status

This is a **Revision B engineering prototype**, not a fabrication-ready or
production-tested commercial cartridge. The PCB is intentionally unrouted.
Before fabrication, capture and review a complete schematic, assign and verify
CPLD pins, copy the current official RP2350B minimal design, verify every exact
package, simulate timing, and compare the edge geometry with known-good donor
hardware. Complete the current-limited breakout tests in
`docs/safety-and-bringup.md` before inserting it into a console.

Do not send the included KiCad template directly to fabrication.

## Build prerequisites

- Raspberry Pi Pico SDK 2.1 or later and Arm GNU Toolchain.
- CMake plus Ninja or Make.
- KiCad 8 or later for the placement template.
- Microchip WinCUPL/Atmel tools or another verified ATF1508ASV flow for the
  final CPLD equations and JED programming.

The prototype USB descriptor uses TinyUSB's development VID `0xCAFE`. Obtain a
proper VID/PID before distribution.

## Primary references

- RP2350: <https://www.raspberrypi.com/documentation/microcontrollers/microcontroller-chips.html>
- TinyUSB MSC: <https://docs.tinyusb.org/en/latest/examples/device/cdc_msc.html>
- Cartridge signals: <https://plutiedev.com/cartridge-slot>
- Sega SMS mapper: <https://www.smspower.org/Development/Mappers>
- SMS memory map: <https://www.smspower.org/Development/MemoryMap>
- ATF1508ASV: <https://www.microchip.com/en-us/product/atf1508asv>
- FM18W08 FRAM: <https://www.infineon.com/part/FM18W08-SG>
