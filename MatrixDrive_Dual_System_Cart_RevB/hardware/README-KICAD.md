# MatrixDrive Revision B KiCad project

This directory now contains a complete logical engineering capture for the
MatrixDrive cartridge and a native KiCad 8 PCB with the same component and net
model.

## Open the project

1. Open `MatrixDrive-RevB.sch` in KiCad 8 or 9 Eeschema.
2. Accept KiCad's conversion prompt, then save it as
   `MatrixDrive-RevB.kicad_sch` beside the existing project file.
3. Open `MatrixDrive-RevB.kicad_pcb` in PCB Editor.
4. Refill all zones with `B`, then run **Inspect > Design Rules Checker**. Do
   not waive errors until the logical footprints below have been replaced.

The schematic is supplied in KiCad's readable legacy format because the
automated build environment does not contain Eeschema. `MatrixDrive_RevB.lib`
and `sym-lib-table` make the custom logical symbols self-contained. The board
file and `MatrixDrive-RevB.kicad_pro` are native KiCad 8 files.

## Captured circuitry

- 64-contact Mega Drive/Genesis cartridge edge and every used signal;
- USB-C UFP power, CC resistors, ESD protection and USB data path;
- diode-OR power isolation, fuse, 3.3 V regulator and RP2350 support rails;
- RP2350B GPIO mapping, boot QSPI, staging SPI flash, SWD/UART and indicators;
- 32-Mbit x16 active NOR ROM;
- five address/control translators, two data translators and isolation logic;
- ATF1508ASV mapper interface, JTAG and all RTL-visible signals;
- Sega/Codemasters SMS mapper controls and 64 KiB FRAM;
- Sonic 3 lock-on save FRAM and upper-byte disable path;
- MD/SMS, Pause and profile switches plus open-drain cartridge controls;
- pull-ups, pull-downs, decoupling and 22 named diagnostic test points.

The generated model currently contains 143 component references, 777 logical
pins and 192 named nets. `kicad-project-manifest.json` records these counts and
the outstanding release gates.

## PCB status

The PCB has the 100 mm x 65 mm engineering outline, physical 2x32 cartridge
edge, all component references, assigned pad nets, preliminary placement and a
connectivity-complete deterministic route. The eight-layer stack uses F.Cu,
In2.Cu, In3.Cu, In4.Cu, In5.Cu and B.Cu for signals, with uninterrupted GND on
In1.Cu and 3V3 on In6.Cu. `routing-report.json` records 188 of 188 routable nets
complete, 3,917 segments and 1,246 vias.

This route is a DRC handoff, not a fabrication release. It has not been opened
or checked by KiCad in the automated environment, USB is not yet
length/impedance controlled, and no signal-integrity or power-integrity review
has been done.

The programmable-device and memory symbols use logical, alphanumeric pad names
until the exact physical package maps have been approved. Those footprints are
marked `UNVERIFIED` or `LOGICAL`. They prevent this engineering capture from
being mistaken for a fabrication-ready board.

Before fabrication:

1. replace the U1, U2, U13, translator and FRAM logical footprints with verified
   manufacturer/package footprints;
2. assign and fit every ATF1508ASV pin, then close CPLD timing;
3. copy the current official RP2350B minimal-design power and QSPI pin mapping;
4. confirm NOR reset, write-protect and byte-mode strap polarity;
5. review/refine the preliminary bus route and route USB as a controlled 90-ohm differential pair;
6. review power integrity, translator direction/OE timing and cartridge loading;
7. refill zones and pass KiCad ERC, DRC and connectivity inspection;
8. complete the staged checks in `../docs/safety-and-bringup.md`.

Do not order PCBs from the generated board in its current state.

## Regeneration

Run:

```sh
python3 tools/generate_kicad_project.py
python3 tools/route_kicad_pcb.py
```

The older `generate_kicad_pcb.py` command is retained as a compatibility
wrapper and generates the same complete project.
