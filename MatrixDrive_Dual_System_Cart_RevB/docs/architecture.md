# Architecture

## Console data paths

The console does not read through the RP2350. Translators convert the 5 V cartridge bus to 3.3 V, and the instant-on CPLD selects ROM or FRAM.

```text
MD mode:      68000 bus -> translators -> CPLD -> x16 NOR
S3 save:      odd byte  -> low translator -> CPLD -> dedicated x8 FRAM
SMS mode:     Z80 bus   -> translators -> CPLD mapper -> NOR low byte
                                      write/save tap -> 2 x x8 SMS FRAM
USB mode:     USB-C -> RP2350B -> staging SPI NOR -> active parallel NOR
```

`hardware/electrical-netlist.csv` is the signal connection authority. This description is not a substitute for a reviewed schematic.

## Power and isolation

- Edge contacts A2/A31 feed `CART_5V` through F1; USB VBUS is separate.
- D1 and D2 diode-OR the sources into `SYS_5V`; U11 produces `3V3`.
- Cartridge-facing translator ports use `CART_5V` and become high impedance during USB-only operation.
- `BUS_DISABLE` is forced high when USB VBUS and console power coexist.
- `USB_MODE_3V3` tells U13 to release all shared NOR and FRAM controls.
- ROM and every FRAM chip enable have passive inactive pullups.
- U19 uses VCCA=3V3, VCCB=CART_5V, fixed A-to-B direction, Ioff, and VCC isolation to carry the Sonic 3 high-byte-disable request safely into U15.
- Both gates in U15 are used: the first combines bus/SMS isolation and the second adds the MD odd-byte save-cycle request.

## Mega Drive and lock-on mode

With SW2 in MD, `/M3`, VA21, and VA22 float. U13 normally passes translated VA1-VA21 to NOR A0-A20, `/CE_0` to `/CE`, and `/CAS0` to `/OE`. The x16 path returns VD0-VD15.

SW4 low selects the ordinary linear profile. It is also the Sonic 2 lock-on profile. Firmware repeats even-sized power-of-two MD images smaller than 2 MiB until the 2 MiB upper-cartridge window is filled.

SW4 high selects the Sonic 3 save profile:

- CPU odd-byte addresses `$200001-$203FFF` correspond to word addresses `$100000-$101FFF` on `cart_a`.
- U13 disables NOR and selects U20 only inside that range while `/CE_0` is active.
- U20 A0-A12 follow the cartridge word address; A13/A14 are grounded.
- `/CAS0` and `/LWR` become the shared FRAM OE/WE strobes.
- `md_high_disable` passes through U19 and U15 to disable U7, preventing the unused high byte from being driven during x8 FRAM access.
- U17/U18 remain inactive, keeping all 64 KiB of SMS save storage separate.

Sonic & Knuckles owns its `$A130F0` mapping control and supplies the lower cartridge ROM. MatrixDrive behaves only as the normal cartridge inserted in the upper slot.

## Master System mode

With power off, SW2 is moved to SMS. Open-drain FETs pull `/M3`, VA21, and VA22 low. U13 then:

- uses translated VA1-VA16 as Z80 A0-A15;
- observes mapper writes through the low-byte bidirectional translator;
- maps three 16 KiB ROM slots using the SW4 profile;
- decodes Sega writes at `$FFFC-$FFFF` or exact Codemasters writes at `$0000/$4000/$8000`;
- uses `/CE_0` for `$0000-$7FFF` and `/CAS2` for `$8000-$BFFF`;
- drives only VD0-VD7;
- decodes 32 KiB Sega saves or banked 64 KiB Codemasters saves.

SW3 pulls the PAUSE/NMI contact low through an open-drain FET. See `master-system-mode.md`.

## USB storage and installation

The RP2350 QSPI flash is dedicated to firmware. A separate 16 MiB SPI NOR backs a FAT16 superfloppy named `MATRIXDRV`. On safe eject, firmware validates one image, erases active NOR, and verifies each programmed word.

- MD bytes are packed big-endian: bytes 0/1 become flash D15:8/D7:0.
- Even-sized power-of-two MD images below 2 MiB repeat through the 2 MiB lock-on window.
- SMS bytes use one x16 word each: D15:8 is `0xFF` and D7:0 is the ROM byte.

The same 4 MiB x16 NOR therefore holds either 4 MiB of MD data or 2 MiB of SMS byte data.

## Programming ownership

RP2350 GPIO0-GPIO39 share the NOR-side bus and remain inputs without USB. With USB present, U13 releases shared outputs and the cartridge translators isolate before firmware drives those GPIOs. External pulls hold NOR, U17, U18, and U20 inactive during reset and handover. The RP2350 does not currently expose FRAM contents through USB.
