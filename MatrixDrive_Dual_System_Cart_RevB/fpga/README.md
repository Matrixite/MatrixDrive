# Master System YM2413 FPGA option

This directory implements the optional MatrixDrive Master System FM path. It
adds a dedicated Lattice ECP5 FPGA beside the existing ATF1508 mapper; the
CPLD remains responsible for ROM and save mapping, while the FPGA implements
the YM2413, its I/O ports and the audio DAC.

This is an RTL-complete engineering option, not a retrofit for an assembled
Revision B PCB. The Revision B placement template has no FPGA, configuration
flash, FPGA power rails or audio filter. Integrate the logical netlist here
into a reviewed schematic and routed board spin before building hardware.

## Implemented behavior

| SMS port | Direction | FPGA behavior |
| --- | --- | --- |
| `F0` | Write | Latches the YM2413 register address |
| `F1` | Write | Writes data to the selected YM2413 register |
| `F2` | Read/write | Three-bit FM/detection register; reset read is `FF` |

F2 bit 0 enables the cartridge FM output. Bits 1 and 2 are stored and read
back for software compatibility. Bit 1 cannot mute the Mega Drive's internal
PSG from a cartridge, so software that relies on hardware PSG suppression may
sound different.

Every port decode includes `/IORQ`. In Mega Drive SMS mode, VA19 on the edge
connector becomes the Master System `/IORQ`; MatrixDrive already translates
that pin onto the `CART_A18` net. The FPGA top-level therefore receives it as
`cart_a18_iorq_n`. Do not replace this with address-only decoding.

## RTL data path

1. `sms_fm_bus.v` synchronizes F0/F1/F2 writes from the cartridge bus and
   generates clean write pulses for the OPLL core.
2. The BSD-licensed IKAOPLL core implements the cycle-accurate YM2413 signal
   path and produces a signed 16-bit accumulated sample.
3. `pdm_dac.v` converts that sample to a 14.31818 MHz one-bit stream.
4. A two-pole passive low-pass filter, AC coupling capacitor and separate
   injection resistors feed cartridge audio inputs SL1 and SR2.

The data bus is driven only for an F2 I/O read while SMS mode is selected and
USB is absent. It is high-impedance for normal memory cycles, MD mode and USB
programming.

## Clock and target

The reference target is `LFE5U-12F-6BG256C`. The top-level input is a dedicated
14.318180 MHz CMOS oscillator. A one-in-four clock enable supplies the OPLL
with the 3.579545 MHz phiM rate while all FPGA registers stay in one physical
clock domain.

Generic ECP5 synthesis reports approximately 1,347 LUT4s, 1,727 flip-flops,
103 carry cells and two 18x18 multipliers. This leaves substantial margin in a
12K device. Final utilization and timing must be rechecked after package-pin,
I/O-standard and board constraints are assigned.

For PAL pitch locked to the console's slower SMS clock, populate the
region-specific oscillator and change the top-level divide ratio/constraint
accordingly. The supplied 14.318180 MHz option intentionally produces the
original 3.579545 MHz YM2413 reference rate.

## Build and test

From this directory:

```sh
make test
make lint
make synth
```

`make test` needs Python 3 and Icarus Verilog. `make lint` and `make synth`
need Yosys with ECP5 support. Synthesis creates
`build/matrixdrive_sms_fm.json`.

`make test-core` runs `tb/test_ikaopll.v`, a direct self-checking harness for
the vendored YM2413 core. It verifies reset silence, synchronized address/data
writes, a melodic instrument and key-off transition, all five rhythm voices,
sample bounds, activity, zero crossings, and deterministic audio signatures.
To retain a waveform for inspection, run:

```sh
vvp build/test_ikaopll +vcd
```

This writes `build/test_ikaopll.vcd` after the harness has been compiled by
`make test-core`.

The repository deliberately does not include a place-and-route constraint
file or bitstream. Package pins depend on the final schematic and PCB escape;
using invented assignments would be unsafe. Complete
`hardware/pin-assignment-template.csv`, add an LPF constraint file, run
nextpnr-ecp5, and close timing before programming a device.

## Hardware release gates

- Capture the FPGA, 1.1 V core, 2.5 V auxiliary, 3.3 V I/O/configuration and
  SPI-flash circuits from current Lattice reference documents.
- Recalculate the cartridge current budget and replace the existing 200 mA
  protection/regulator arrangement if measurements require it.
- Prove all FPGA pins are high-impedance during configuration, MD mode and USB
  programming. Add external gating if the chosen configuration mode cannot
  guarantee this.
- Scope VA19, `/LWR`, `/CAS0`, address and data on each supported console
  revision before relying on the timing assumptions.
- Verify the F2 read turnaround with U6 and prove NOR/FRAM output enables stay
  inactive during the I/O cycle.
- Measure the filtered output for DC, peak voltage and ultrasonic residue
  before connecting SL1/SR2. Tune the two injection resistors on real hardware.
- Validate with the YM2413 test ROM and several FM-capable games on NTSC and
  PAL console revisions.

See `hardware/fpga-addon-bom.csv`, `hardware/logical-netlist.csv` and
`hardware/pin-assignment-template.csv` for the schematic-level integration
authority.
