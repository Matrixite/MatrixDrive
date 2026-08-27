# Implementation and release gates

## Phase 1 — included in this branch

- MegaSD-style cartridge architecture and hardware candidate schedule.
- 68000 cartridge-bus request/ack bridge.
- Raw 2352-byte sector-buffer RTL.
- ISO/BIN+CUE manifest parser.
- Manifest-driven reference sector service, including synthetic pregaps.
- Host tests and RTL simulations.

## Phase 2 — Mega-CD subsystem integration

- Import or independently implement the sub-68000, gate array, Word RAM,
  program RAM, graphics engine, CDC/CDD and PCM blocks.
- Replace MiSTer/HPS storage signals with `disc_sector_buffer` requests.
- Remove the emulated base Mega Drive from any standalone core; the physical
  console is authoritative.
- Implement the cartridge-specific main-CPU interrupt-assist/boot mechanism.
  This is the largest compatibility risk because the normal side expansion
  connector exposes signals that the cartridge edge does not.
- Produce a legal, source-available FPGA build with all third-party notices.

## Phase 3 — firmware and menu

- FatFs FAT32/exFAT microSD mount and long-filename support.
- BIOS selection by region; no BIOS bundled.
- On-console game browser and persistent recent-game list.
- CUE parsing equivalent to the tested host model.
- Double-buffered sector streaming with seek, play, pause and CDDA timing.
- USB MSC arbitration that refuses console and PC ownership at the same time.
- Backup-RAM import/export and power-loss-safe writes.

## Phase 4 — hardware verification

- Complete schematic, FPGA pin assignment, power-tree simulation and PCB.
- FPGA fitter/resource report and worst-case timing closure.
- Measure cartridge-slot current before selecting the final FPGA speed grade.
- Prove every 5 V bus signal is translated and high-impedance when unpowered.
- Capture `/AS`, `/CE_0`, `/TIME`, `/DTACK`, data direction and reset timing on
  a protected cartridge-slot breakout.
- Verify PCM/CDDA levels through SL1/SR2 without clipping or DC offset.

## Phase 5 — compatibility

- Boot regional BIOS menu on real Model 1 and Model 2 consoles.
- Run main/sub-CPU communication, Word-RAM and graphics diagnostics.
- Test data-only ISO, one-BIN mixed-mode CUE and multi-BIN CUE.
- Verify continuous CDDA, seek-heavy games, backup RAM and reset recovery.
- Publish a game compatibility list only from legally obtained images.

Until all five phases pass, describe Revision C as an experimental development
platform, not a working commercial-style optical-drive emulator.
