# Sonic & Knuckles lock-on mode

## Scope

MatrixDrive is designed to behave as the ordinary Mega Drive/Genesis cartridge inserted into the upper slot of an original Sonic & Knuckles cartridge. It does not replace or emulate the Sonic & Knuckles base cartridge.

This profile targets:

- Sonic 2 & Knuckles from a normal Sonic 2 image;
- Sonic 3 & Knuckles from a normal Sonic 3 image;
- the normal Blue Sphere response that Sonic & Knuckles produces for other simple ROM cartridges.

SMS mode, unusual MD mappers, serial EEPROM cartridges, enhancement hardware, and carts larger than 2 MiB are not supported through the lock-on path in this revision.

## Why ROM mirroring is required

The MAME pass-through implementation maps the upper cartridge into Sonic & Knuckles' upper 2 MiB and notes that cartridges no larger than 2 MiB are mirrored in that window. A physical small mask ROM naturally repeats when unimplemented high address pins are absent. MatrixDrive uses a 4 MiB NOR, so firmware must reproduce that behaviour.

During installation, an MD image is repeated through 2 MiB when all of these are true:

- the file is smaller than 2 MiB;
- its size is a power of two;
- its size is even;
- it has passed the normal MD header validation.

A normal 1 MiB Sonic 2 image is therefore written twice. A 2 MiB Sonic 3 image needs no extra copy. The original source file on `MATRIXDRV` is unchanged.

## Sonic 3 save window

Sonic 3 & Knuckles accesses the save memory from the upper cartridge at odd-byte addresses `$200001-$203FFF`. On the cartridge word-address bus this is `$100000-$101FFF`.

With SW2=MD and SW4 high:

| Signal or device | Behaviour |
| --- | --- |
| U2 NOR | Disabled inside the save window |
| U20 | Selected for exactly 8 KiB using A0-A12 |
| U17/U18 | Disabled; SMS saves remain separate |
| U6 low data | Carries D0-D7 reads and writes |
| U7 high data | Disabled by U13 → U19 → U15 |
| Read strobe | `/CAS0` drives shared FRAM `/OE` |
| Write strobe | `/LWR` drives shared FRAM `/WE` |

U20 is a 32 KiB FM18W08 for component consistency and availability, but A13/A14 are grounded and only 8 KiB is visible. Its remaining capacity is intentionally inaccessible.

## Switch settings

| Game/result | SW2 | SW4 |
| --- | --- | --- |
| Sonic 2 & Knuckles | MD | Low: LINEAR |
| Sonic 3 & Knuckles with save support | MD | High: S3 SAVE |
| Other simple lock-on cartridge / Blue Sphere | MD | Low: LINEAR |

SW4 remains the Sega/Codemasters selector when SW2 is in SMS mode. Move both switches only with console and USB power absent.

## Loading and stacking

1. Remove MatrixDrive from all console hardware.
2. Connect USB-C and install a legal, clean big-endian Sonic 2 or Sonic 3 image.
3. Safely eject, wait for the steady green indication, and disconnect USB.
4. Set SW2/SW4 using the table above.
5. Insert MatrixDrive fully into the Sonic & Knuckles upper slot without rocking it.
6. Insert Sonic & Knuckles into the powered-off console.
7. Power on.
8. Power off and remove the complete stack before reconnecting USB or moving a switch.

## Physical requirements

The electrical design uses the standard 64-contact Mega Drive/Genesis edge. Physical lock-on compatibility also depends on details that cannot be proven by the unrouted placement template:

- PCB thickness and bevel;
- finger plating, pitch, and insertion depth;
- board and shell width;
- component height below the upper-slot door;
- switch and USB-C clearance;
- retention and extraction forces.

Measure a real Sonic & Knuckles cartridge and a known-good upper cartridge before finalising the board outline and shell. Do not fabricate the current template as-is.

## Validation gates

Before connecting to Sonic & Knuckles:

- pass direct-console MD tests;
- verify the 2 MiB mirror pattern in NOR;
- sweep the U20 decode boundaries with a cartridge breakout;
- verify U7 is disabled during every U20 cycle;
- confirm U20 does not overlap U17/U18;
- fit and time the exact ATF1508ASV equations;
- confirm the complete stacked assembly is mechanically stable;
- monitor current on the first lock-on power-up.

Automated tests prove the source-level decode and installer pattern. They do not prove CPLD fit, analogue timing, connector wear, or real-cartridge operation.

## Primary implementation references

- [MAME Sonic & Knuckles pass-through cartridge](https://github.com/mamedev/mame/blob/master/src/devices/bus/megadrive/sk.cpp)
- [Genesis Plus GX Mega Drive cartridge and lock-on handling](https://github.com/ekeeke/Genesis-Plus-GX/blob/master/core/cart_hw/md_cart.c)
- [Genesis Plus GX backup RAM mapping](https://github.com/ekeeke/Genesis-Plus-GX/blob/master/core/cart_hw/sram.c)
