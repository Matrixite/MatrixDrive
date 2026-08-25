# Design review checklist before routing

Revision B intentionally stops before a fabrication release. Close every item
below in the final schematic and PCB review.

## RP2350B subsystem

- Import the **current RP2350B Minimal KiCad** reference from Raspberry Pi's
  Product Information Portal; do not redraw the on-chip buck regulator from
  memory.
- Copy the complete VREG, DVDD/1V1, IOVDD, ADC_AVDD, USB_OTP_VDD, RUN, crystal,
  boot-flash and decoupling circuits.
- Preserve the official inductor orientation, output-capacitor placement and
  current return path. Use the specified polarised Abracon inductor unless the
  current hardware guide approves a substitute.
- Confirm every QFN-80 power and ground pin plus the exposed pad.
- Confirm external QSPI routing and boot-straps for the exact W25Q16 package.
- Run the latest Pico SDK board-header checks with `PICO_RP2350A=0`.

Official source: <https://pip.raspberrypi.com/categories/1214-rp2350>

## Cartridge interface

- Compare all 64 pad numbers with a known-good donor PCB and continuity-test a
  cartridge-slot breakout.
- Confirm that the KiCad front copper is the console-facing B row and back copper
  is the A row for the selected physical orientation.
- Verify hard-gold thickness, 1.6 mm board thickness, edge bevel and insertion
  depth with the intended manufacturer.
- Simulate or measure 90 ns NOR access plus translator and CPLD delay against
  `/CE_0`, `/CAS0`, and `/CAS2` at minimum and maximum supply voltage.
- Confirm translator DIR straps and `BUS_DISABLE` default state with both power
  sources in every sequence.
- Fit an ATF1508ASV programming coupon first, assign all TQFP-100 pins, and
  archive the compiler fit/timing report and programmed JED checksum.
- Prove CPLD outputs release before RP2350 programming ownership and that
  passive pulls keep NOR/FRAM `/CE`, `/OE`, and `/WE` inactive during reset.
- Verify SW2 is break-before-make and asserts `/M3`, VA21 and VA22 through
  open-drain devices only; never source 3.3 V into those cartridge nets.
- Verify SW4 is labelled SEGA/CODEMASTERS, is sampled as a 3.3 V CPLD input,
  and cannot float during break-before-make travel.
- Measure U16/U6 direction turnaround around `/LWR` and prove the console, NOR,
  either FRAM and translator never drive D7:D0 simultaneously.
- Verify U17/U18 never assert together and exercise all eight Codemasters 8 KiB
  FRAM banks through logical addresses `$0000-$FFFF`.
- Check unused console inputs are not accidentally driven.

## USB and power

- Route D+/D- as a short 90-ohm differential pair over an uninterrupted ground
  reference, with the ESD device at the receptacle.
- Verify separate 5.1 kOhm Rd resistors on CC1 and CC2.
- Measure reverse leakage through both source-isolation diodes.
- Verify the resettable fuse value against measured console-mode current.
- Prove that USB-only operation leaves A2/A31 and every other edge contact
  unpowered/high impedance.

## Storage and firmware

- Confirm the exact staging-flash JEDEC ID or relax the whitelist only after
  testing a substitute.
- Power-cycle during writes to evaluate FAT and erase-cache recovery.
- Test Windows, macOS and Linux safe-eject behaviour.
- Test fragmented files and root directories containing unrelated files.
- Test minimum, maximum, odd-length and invalid-header images.
- Test `.SMS` images at 8 KiB, 32 KiB, 48 KiB and 2 MiB in both SW4 positions.
- Exercise every Sega register, the fixed 1 KiB window, both Sega FRAM halves,
  all three Codemasters bank registers and all eight Codemasters FRAM banks.
- Reserve a real USB VID/PID before any public product release.

## Release gates

- ERC clean with reviewed exceptions.
- DRC clean with a documented manufacturer rule set.
- Four-layer stack-up and impedance quotation approved.
- Current-limited breakout test passed.
- Logic-analyser timing capture archived.
- At least one Model 1 and one Model 2 console tested with homebrew diagnostics.
- Master System mode tested on each intended console revision, including reset,
  Pause NMI and a save/load/power-cycle cycle.
