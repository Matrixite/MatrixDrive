# Architecture

## Console data paths

The console does not read through the RP2350. Translators convert the 5 V
cartridge bus to 3.3 V, and an instant-on CPLD selects the address mapping.

```text
MD mode:  68000 bus -> translators -> CPLD pass-through -> x16 NOR
SMS mode: Z80 bus   -> translators -> CPLD selected mapper -> NOR low byte
                         write tap -> Sega/Codies registers -> 2 x x8 FRAM
USB mode: USB-C -> RP2350B -> staging SPI NOR -> active parallel NOR
```

`hardware/electrical-netlist.csv` is the signal connection authority. The
diagram is descriptive, not a substitute for a reviewed schematic.

## Power and isolation

- Edge contacts A2/A31 feed `CART_5V` through F1; USB VBUS is separate.
- D1 and D2 diode-OR the sources into `SYS_5V`; U11 produces `3V3`.
- Translator A ports use `CART_5V`, so they are unpowered/high-impedance during
  USB-only operation. Their B ports use `3V3`.
- `BUS_DISABLE` is forced high when USB VBUS and console power coexist.
- A separate `USB_MODE_3V3` divider tells U13 to tri-state all active-NOR pins.
  It is intentionally independent of the PROGRAM-button ADC ladder.
- ROM and FRAM write pins have passive inactive pullups.

This prevents either source from feeding the other and prevents the CPLD or
RP2350 from fighting the console bus during programming.

## Mega Drive mode

SW2 leaves `/M3`, VA21 and VA22 floating and presents `SMS_MODE_3V3=0`. U13
passes translated VA1-VA21 to NOR A0-A20, `/CE_0` to `/CE`, and `/CAS0` to
`/OE`. The x16 data path returns VD0-VD15. The result is a deterministic linear
4 MiB cartridge. SMS FRAM is disabled.

## Master System mode

With power off, SW2 is moved to SMS. Its hardware pole asserts the mode before
reset; open-drain FETs pull `/M3`, VA21 and VA22 low as required by the
Power-Base-Converter-style interface. The CPLD then:

- uses translated VA1-VA16 as Z80 A0-A15;
- observes `$FFFC-$FFFF` writes through a dedicated VD0-VD7 input translator;
- maps three 16 KiB ROM slots using the power-off SW4 profile;
- in Sega mode, fixes `$0000-$03FF` and decodes `$FFFC-$FFFF`;
- in Codemasters mode, decodes exact writes at `$0000/$4000/$8000`;
- uses `/CE_0` for `$0000-$7FFF` and `/CAS2` for `$8000-$BFFF`;
- drives only the low console data byte for ROM and save-memory reads;
- decodes 32 KiB Sega saves or banked 64 KiB Codemasters saves.

SW3 pulls the cartridge PAUSE/NMI contact low through an open-drain FET. SW4
selects Sega or Codemasters mapper logic and must only move while unpowered.
See `master-system-mode.md` for exact equations and compatibility.

## USB storage and installation

The 2 MiB QSPI flash is dedicated to RP2350 execute-in-place firmware. A
separate 16 MiB SPI NOR backs a FAT16 superfloppy named `MATRIXDRV`. On safe
eject, firmware flushes the 4 KiB sector cache, selects one root-level image,
validates its extension/header, erases active NOR, and verifies each programmed
word.

- MD bytes are packed big-endian: bytes 0/1 become flash D15:8/D7:0.
- SMS bytes use one word each: flash D15:8 is `0xFF`, D7:0 is the ROM byte.

This makes the same 4 MiB x16 NOR hold either 4 MiB of MD byte data or 2 MiB of
SMS 8-bit data.

## Programming ownership

RP2350 GPIO0-GPIO39 share the NOR-side bus. They remain inputs when USB is
absent. With USB present, U13 first releases its address/control outputs and the
cartridge translators are isolated before firmware makes those GPIOs outputs.
External pulls hold NOR/FRAM controls inactive and FRAM A13/A14 low during
reset and handover. U17/U18 provide two 32 KiB halves of the 64 KiB save array.
