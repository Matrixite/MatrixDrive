# Master System mode

## Scope

Revision B targets Master System software running through a Mega Drive/Genesis
cartridge slot, similar to the electrical role of a Power Base Converter. It is
not a physical Master System cartridge and requires a console revision that
still exposes and supports SMS mode.

Implemented:

- 8/16/32/48 KiB fixed/no-mapper ROMs;
- Sega mapper ROMs through 2 MiB;
- Codemasters mapper ROMs through 2 MiB;
- power-off Sega/Codemasters mapper selector;
- 64 KiB non-volatile FRAM shared by both mapper profiles;
- physical Pause/NMI button;
- optional FPGA YM2413 with `F0`/`F1` writes, `F2` detection and cartridge audio output.

Not implemented: Korean, multicart or game-specific mappers;
light-gun accessory circuitry; Mega Drive save hardware; Sega mapper bit 4
RAM-at-`$C000` mode. These require a later verified CPLD profile.

The FM option requires a new board spin and is not present on the Revision B
placement template.

## Power-off mapper selector

SW4 selects the SMS mapper profile. Move it only when console and USB power are
absent.

| SW4 position | Mapper writes | Reset ROM banks | Save window |
| --- | --- | --- | --- |
| Sega | `$FFFC-$FFFF` | 0, 1, 2 | 16 KiB at `$8000-$BFFF` |
| Codemasters | exact `$0000`, `$4000`, `$8000` | 0, 1, 0 | 8 KiB at `$A000-$BFFF` |

The selector is a hardware input to U13. Firmware does not auto-detect the
mapper and console transactions never wait for the RP2350.

## Sega mapper

U13 resets the control register to `0` and the three ROM banks to 0, 1, and 2.
Writes are captured at the rising edge of translated `/LWR`:

| Address | Register | Effect |
| --- | --- | --- |
| `$FFFC` | control | bit 3 enables FRAM; bit 2 selects FRAM half |
| `$FFFD` | page 0 | ROM bank for `$0000-$3FFF`, except fixed first 1 KiB |
| `$FFFE` | page 1 | ROM bank for `$4000-$7FFF` |
| `$FFFF` | page 2 | ROM bank for `$8000-$BFFF` |

Only bank bits 6:0 reach NOR A20:A14, matching the 2 MiB `.SMS` limit. Sega
FRAM uses the lower 32 KiB of the installed 64 KiB: A13 follows the CPU
address, A14 follows control bit 2, and the low FRAM chip is selected.

## Codemasters mapper

U13 resets the three ROM banks to 0, 1, and 0. There is no Sega-style fixed
first-1-KiB window.

| Write address | Effect |
| --- | --- |
| `$0000` | Select 16 KiB ROM bank for `$0000-$3FFF` |
| `$4000`, bit 7 clear | Disable FRAM and select ROM bank for `$4000-$7FFF` |
| `$4000`, bit 7 set | Enable FRAM; bits 2:0 select one of eight 8 KiB banks |
| `$8000` | Select 16 KiB ROM bank for `$8000-$BFFF` |

When FRAM is enabled, only `$A000-$BFFF` is replaced. ROM remains readable at
`$8000-$9FFF`, and enabling FRAM preserves the previous slot-1 ROM bank. The
three FRAM bank bits become logical A15:A13. Two 32 KiB FM18W08 devices provide
the exact 64 KiB array; U13 drives separate active-low chip enables for the low
and high halves.

The Codemasters behaviour matches the reset and banking implementation in
[Genesis Plus GX](https://github.com/ekeeke/Genesis-Plus-GX/blob/master/core/cart_hw/sms_cart.c).

## FPGA YM2413 option

In SMS mode, Mega Drive cartridge edge signal VA19 becomes the Z80 `/IORQ`.
Revision B already translates VA19 as `CART_A18`; the FPGA spin taps that net
along with A0-A7, D0-D7, `/LWR`, `/CAS0`, reset and the mode signals.

| I/O port | Behavior |
| --- | --- |
| `F0` | Write YM2413 register address |
| `F1` | Write YM2413 register data |
| `F2` | Read/write the three-bit FM/detection register |

The F2 register resets to `111`; reads return `11111xxx`. Bit 0 enables FM
audio. Bits 1 and 2 are stored for compatibility, but a cartridge cannot mute
the Mega Drive's internal PSG, so bit 1 is not able to reproduce that system-
level function.

F0 and F1 are forwarded to the cycle-accurate IKAOPLL core. Its signed output
feeds a one-bit PDM DAC, a two-pole low-pass filter, AC coupling, and separate
SL1/SR2 injection resistors. The FPGA bus pins are high-impedance in MD mode,
with USB present, and on every cycle other than an exact F2 I/O read.

See `../fpga/README.md` for RTL, clocking, synthesis, licensing and hardware
release gates.

## NOR representation

The installer writes SMS byte `n` to NOR word address `n` as
`0xFF00 | byte`. In SMS mode only D7:D0 are returned to the console. In MD
mode the same device is read normally as an x16 array. Installing a ROM replaces
the previous active image but does not erase FRAM.

## Physical mode and pause

SW2 must be a break-before-make slide switch and may only be moved with console
and USB power absent. It supplies `SMS_MODE_3V3` to the CPLD and enables
open-drain pulls on `/M3`, VA21 and VA22. Never drive those 5 V cartridge nets
directly from 3.3 V logic.

SW3 drives VA23 only through open-drain Q4. It is ignored in MD mode. Mount all
controls where they cannot contact the cartridge shell or move during insertion.

## Timing constraints

The CPLD address mux plus translator plus NOR/FRAM access must fit the SMS read
and write windows at worst-case voltage and temperature. Archive fitted-CPLD
timing plus oscilloscope/logic-analyser captures for both mapper profiles,
FRAM reads/writes, reset defaults, selector states and Pause NMI.

For the FPGA spin, also archive captures of F0/F1/F2 I/O cycles showing VA19
`/IORQ`, `/LWR` or `/CAS0`, address, data and FPGA output enable. Verify F2
turnaround through U6, confirm NOR/FRAM remain inactive, and measure filtered
audio amplitude and ultrasonic residue at both SL1 and SR2.
