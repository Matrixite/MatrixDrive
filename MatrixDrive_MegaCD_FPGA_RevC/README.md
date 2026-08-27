# MatrixDrive MegaCD FPGA ODE — Revision C

Revision C is the experimental MegaSD-style branch of MatrixDrive. It keeps a
real Mega Drive/Genesis as the base console, but moves the Mega-CD add-on into a
large FPGA cartridge and replaces the optical drive with disc images on
microSD.

This directory is a **development platform**, not a finished Mega-CD clone. The
implemented and tested pieces are the real-console cartridge-bus bridge, the
raw-sector buffer contract, and the `.ISO`/`.BIN + .CUE` manifest parser. A
complete Mega-CD gate-array/graphics/CDC/PCM/sub-68000 core and the main-CPU
interrupt-assist mechanism still have to be integrated and proven on hardware.

## Intended user experience

1. Format a microSD card as FAT32 or exFAT.
2. Put a legally obtained regional Mega-CD BIOS at `/MegaCD/boot.rom`.
3. Copy games beneath `/MegaCD/Games/` as either:
   - one data-only `.iso`; or
   - a `.cue` plus its single or multiple `.bin` track files.
4. Insert the card, select **MCD FPGA** with all power disconnected, insert the
   cartridge into a real Mega Drive/Genesis, and power on.
5. The cartridge menu selects the image and streams raw sectors to the FPGA.

`.BIN + .CUE` is the preferred archival format because it preserves raw
2352-byte sectors and CD-audio tracks. A plain `.ISO` is treated as one
MODE1/2048 data track and therefore cannot contain CD audio.

No BIOS or game images are included.

## Revision C architecture

- Intel Cyclone V-class FPGA with external SDRAM.
- RP2350B supervisory controller and USB-C.
- Removable microSD storage; the RP2350 owns the filesystem and streams sectors
  to the FPGA over a dedicated QSPI link.
- Mega Drive cartridge-bus bridge for the BIOS/program-RAM, Word RAM,
  backup-RAM and gate-array register windows.
- Open-drain `/DTACK` generation for expansion-register cycles.
- FPGA-generated PCM/CDDA audio converted to analog and returned through the
  cartridge audio inputs.
- Existing MatrixDrive Revision B remains the smaller ROM/SMS/32X/lock-on
  design; Revision C is a separate board rather than a drop-in CPLD change.

## Implemented source

| Path | Purpose |
| --- | --- |
| `fpga/rtl/matrixcd_cart_bridge.sv` | Real-console 68000 bus request/ack bridge |
| `fpga/rtl/disc_sector_buffer.sv` | 2352-byte raw-sector staging buffer |
| `fpga/rtl/matrixcd_top.sv` | Integration shell and explicit core contract |
| `fpga/tb/` | Self-checking bridge and sector-buffer simulations |
| `tools/disc_manifest.py` | ISO/CUE parser and JSON manifest generator |
| `tools/disc_sector.py` | Manifest-driven raw-sector reference service |
| `tests/test_disc_manifest.py` | Data, audio, multi-file and failure tests |
| `hardware/` | Candidate BOM, cartridge pin schedule and interface netlist |
| `docs/` | Architecture, compatibility limits and implementation gates |

## Build and validation

```sh
python3 tools/validate_project.py
python3 tools/disc_manifest.py /path/to/game.cue --output game.mcd.json
python3 tools/disc_sector.py game.mcd.json 0 --output sector-0.raw
```

Validation requires Python 3.11+ and Icarus Verilog. The parser reads file
metadata only; it never copies or modifies disc-image data.

## Current completion boundary

Passing the supplied tests proves:

- `.ISO`, single-BIN CUE and multi-BIN CUE layouts are converted into a stable
  sector manifest;
- MODE1/2048, MODE1/2352, MODE2/2336, MODE2/2352 and AUDIO tracks are described;
- the cartridge bridge rejects unrelated Mega Drive address cycles;
- selected Mega-CD windows issue one request per bus cycle and hold data/
  `/DTACK` until the console releases the cycle;
- a complete 2352-byte sector can be filled, committed and read back.

This prototype does not yet boot retail Mega-CD software. See
`docs/implementation-roadmap.md` for the remaining core, timing, firmware and
hardware gates.

## Licensing and references

The new MatrixDrive shell code is MIT-licensed at the file level. A practical
core-integration candidate is the GPL-3.0
[MegaCD MiSTer core](https://github.com/MiSTer-devel/MegaCD_MiSTer); importing
or adapting that RTL would require the combined distributed FPGA source to
comply with GPL-3.0. `THIRD_PARTY.md` records this boundary. Terraonion MegaSD
is used only as the requested product-behaviour reference; no proprietary code,
bitstream, firmware or reverse-engineered protected content is included.
