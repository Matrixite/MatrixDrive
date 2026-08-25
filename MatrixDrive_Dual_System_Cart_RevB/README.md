# MatrixDrive Dual-System USB Cartridge — Revision B

MatrixDrive Revision B is a prototype USB-loadable Mega Drive/Genesis cartridge that can also run Master System software on compatible consoles and act as the upper cartridge in Sonic & Knuckles lock-on mode. USB-C exposes a removable FAT16 drive named `MATRIXDRV`; after one ROM is copied and safely ejected, the RP2350B installs it into non-volatile parallel NOR.

Console reads never depend on RP2350 response time. Translators and an instant-on CPLD connect the console directly to NOR or the selected FRAM.

## Supported images

| Console mode | File | Active image limit | Cartridge hardware |
| --- | --- | ---: | --- |
| Mega Drive / Genesis | `.BIN`, `.MD`, `.GEN` | 4 MiB | Linear `$000000-$3FFFFF` ROM |
| Sonic & Knuckles upper slot | Mega Drive image | 2 MiB recommended | Mirrored ROM; optional Sonic 3 save profile |
| Master System | `.SMS` | 2 MiB | Sega or Codemasters mapper selected by SW4 |

Power-of-two Mega Drive images smaller than 2 MiB are repeated by the installer through the full 2 MiB lock-on window. This gives a 1 MiB Sonic 2 image the mirroring expected from its original mask ROM.

For Sonic 3 & Knuckles, SW4's high position in MD mode enables a dedicated 8 KiB odd-byte FRAM window at `$200001-$203FFF`. This storage is physically separate from the two FM18W08 devices that supply the complete 64 KiB SMS save array.

SMS images are stored one byte per x16 NOR word. The CPLD implements Sega or Codemasters 16 KiB banking selected by SW4. Plain 8/16/32/48 KiB images and larger mapped images work.

## Normal use

1. Remove MatrixDrive from the console or Sonic & Knuckles cartridge.
2. Connect USB-C, remove the previous image, and copy one supported ROM to `MATRIXDRV`.
3. Safely eject and wait for the steady green completion indication.
4. Disconnect USB and set SW2/SW4 while all hardware is unpowered.
5. Insert MatrixDrive directly into the console, or into the Sonic & Knuckles upper slot for MD lock-on use.
6. Power on. In SMS mode, use the cartridge PAUSE button when a game needs the Master System NMI pause input.

### Switch positions

| Use | SW2 | SW4 |
| --- | --- | --- |
| Normal Mega Drive or Sonic 2 & Knuckles | MD | Low: LINEAR |
| Sonic 3 & Knuckles with saves | MD | High: S3 SAVE |
| Sega-mapper SMS | SMS | Low: SEGA |
| Codemasters-mapper SMS | SMS | High: CODEMASTERS |

Never move either switch while powered. Never connect USB while MatrixDrive is inserted into a console or another cartridge.

## Lock-on compatibility

The electrical profile follows the pass-through behaviour represented by MAME and Genesis Plus GX:

- Sonic & Knuckles supplies its own ROM at the lower 2 MiB and exposes the upper cartridge in the remaining window.
- MatrixDrive behaves as a normal MD ROM in the upper slot.
- The installer supplies mask-ROM-style mirroring for even-sized power-of-two images up to 2 MiB.
- The Sonic 3 save profile maps U20 to odd-byte addresses `$200001-$203FFF`.
- U19 translates the CPLD's high-byte-disable request into the 5 V domain so U7 is inactive during low-byte-only save cycles.
- Sonic & Knuckles owns its `$A130F0` lock-on control; MatrixDrive does not emulate the base lock-on cartridge.

See `docs/sonic-knuckles-lock-on.md` for exact use and remaining physical-fit validation.

## Image validation

- Mega Drive images require `SEGA` at byte offset `0x100`, normal big-endian byte order, and a maximum size of 4 MiB. Interleaved `.SMD` images are rejected.
- Lock-on images should be even-sized powers of two no larger than 2 MiB.
- Headerless SMS images require `TMR SEGA` at `0x1FF0`, `0x3FF0`, or `0x7FF0`.
- Use only software you are legally entitled to use.

## Hardware summary

- RP2350B, USB Full-Speed Mass Storage, and a 16 MiB FAT16 staging flash.
- S29GL032N-compatible 32-Mbit x16 active parallel NOR.
- ATF1508ASV-15AU100 CPLD for instant-on mode, SMS mapping, and Sonic 3 save decode.
- U17/U18: two FM18W08 32 KiB x8 FRAMs, exactly 64 KiB for SMS saves.
- U20: dedicated FM18W08, with 8 KiB decoded for Sonic 3 lock-on saves.
- U19: SN74LVC1T45 translating the MD high-data-disable control to CART_5V.
- Dual-supply 5 V/3.3 V translation on every active cartridge signal.
- USB/console source isolation, PROGRAM and PAUSE buttons, and power-off selectors.

## Project contents

- `docs/architecture.md` — electrical and data-path architecture.
- `docs/master-system-mode.md` — SMS mapper and storage details.
- `docs/sonic-knuckles-lock-on.md` — lock-on mapping, switches, fit, and limitations.
- `docs/safety-and-bringup.md` — mandatory staged test procedure.
- `hardware/bom.csv`, `connector-pinout.csv`, `electrical-netlist.csv` — connection authorities.
- `hardware/MatrixDrive-RevB.kicad_pcb` — mechanical/placement-only template.
- `cpld/matrixdrive_mapper.v` — synthesizable SMS and lock-on decoder RTL.
- `cpld/test_matrixdrive_mapper.v` — RTL mapper/FRAM testbench.
- `firmware/` — RP2350/Pico SDK firmware source.

## Engineering status

This is a **Revision B engineering prototype**, not a fabrication-ready or production-tested commercial cartridge. The PCB is intentionally unrouted. Before fabrication, capture and review a complete schematic, assign and fit the CPLD, verify resources and timing, copy the official RP2350B minimal design, confirm exact packages, and measure the edge/shell against both a normal donor cartridge and a real Sonic & Knuckles upper slot.

Do not send the included KiCad template directly to fabrication. Complete `docs/safety-and-bringup.md` before any console test.

## Build prerequisites

- Raspberry Pi Pico SDK 2.3.0 and Arm GNU Toolchain.
- CMake plus Ninja or Make.
- Icarus Verilog for RTL simulation.
- KiCad 8 or later for the placement template.
- A verified ATF1508ASV fitting/JED programming flow.

The prototype USB descriptor uses TinyUSB's development VID `0xCAFE`. Obtain a proper VID/PID before distribution.

## Primary references

- MAME S&K pass-through: <https://github.com/mamedev/mame/blob/master/src/devices/bus/megadrive/sk.cpp>
- Genesis Plus GX MD cartridge: <https://github.com/ekeeke/Genesis-Plus-GX/blob/master/core/cart_hw/md_cart.c>
- Genesis Plus GX SRAM: <https://github.com/ekeeke/Genesis-Plus-GX/blob/master/core/cart_hw/sram.c>
- TI SN74LVC1T45: <https://www.ti.com/product/SN74LVC1T45>
- RP2350: <https://www.raspberrypi.com/documentation/microcontrollers/microcontroller-chips.html>
- ATF1508ASV: <https://www.microchip.com/en-us/product/atf1508asv>
- FM18W08 FRAM: <https://www.infineon.com/part/FM18W08-SG>
