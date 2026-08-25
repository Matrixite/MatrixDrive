# Master System mode

## Scope

Revision B targets Master System software running through a Mega Drive/Genesis
cartridge slot, similar to the electrical role of a Power Base Converter. It is
not a physical Master System cartridge and requires a console revision that
still exposes and supports SMS mode.

Implemented:

- 8/16/32/48 KiB fixed/no-mapper ROMs;
- Sega mapper ROMs through 2 MiB;
- `$FFFD`, `$FFFE`, `$FFFF` 16 KiB ROM page registers;
- fixed bank-zero window at `$0000-$03FF`;
- `$FFFC` bit 3 save-RAM enable and bit 2 16 KiB FRAM bank selection;
- non-volatile 32 KiB SMS save memory;
- physical Pause/NMI button.

Not implemented: Codemasters, Korean, multicart or game-specific mappers; FM
sound; light-gun accessory circuitry; Mega Drive save hardware; mapper-control
bit 4 RAM-at-`$C000` mode. These require a later verified CPLD profile.

## Mapper state

U13 resets to control `0`, slot 0 bank `0`, slot 1 bank `1`, and slot 2 bank
`2`. Writes are captured at the rising edge of translated `/LWR`:

| Address | Register | Effect |
| --- | --- | --- |
| `$FFFC` | control | bit 3 enables FRAM at `$8000-$BFFF`; bit 2 selects FRAM bank |
| `$FFFD` | page 0 | ROM bank for `$0000-$3FFF`, except fixed first 1 KiB |
| `$FFFE` | page 1 | ROM bank for `$4000-$7FFF` |
| `$FFFF` | page 2 | ROM bank for `$8000-$BFFF` |

Only bank bits 6:0 reach NOR A20:A14, matching the 2 MiB `.SMS` limit. When
FRAM is enabled, ROM output in slot 2 is disabled. FRAM A13:A0 follow the
address and A14 follows control bit 2.

## NOR representation

The installer writes SMS byte `n` to NOR word address `n` as `0xFF00 | byte`.
In SMS mode only D7:D0 are returned to the console. In MD mode the same device
is read normally as a x16 array. Installing a ROM replaces the previous active
image but does not erase SMS FRAM.

## Physical mode and pause

SW2 must be a break-before-make slide switch and may only be moved with console
and USB power absent. It supplies `SMS_MODE_3V3` to the CPLD and enables
open-drain pulls on `/M3`, VA21 and VA22. Never drive those 5 V cartridge nets
directly from 3.3 V logic.

SW3 drives VA23 only through open-drain Q4. It is ignored in MD mode. Mount both
controls where they cannot contact the cartridge shell or be pressed during
insertion.

## Timing constraints

The CPLD address mux plus translator plus NOR access must fit the SMS ROM read
window at worst-case voltage and temperature. A successful functional test is
not enough: archive oscilloscope/logic-analyser captures for slot changes,
fixed-window reads, FRAM reads/writes, reset defaults and Pause NMI.

Authoritative background: <https://www.smspower.org/Development/Mappers> and
<https://www.smspower.org/Development/MemoryMap>.
