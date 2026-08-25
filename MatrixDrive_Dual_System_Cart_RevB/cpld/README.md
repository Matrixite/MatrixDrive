# CPLD logic

`matrixdrive_mapper.v` is the portable logic source for U13. It contains the
instant-on Mega Drive pass-through, Sega SMS mapper, Codemasters SMS mapper,
64 KiB FRAM decode, and USB ownership isolation. No console transaction depends
on the RP2350.

The power-off SW4 selector drives `codemasters_mapper` low for Sega or high for
Codemasters. Sega writes are decoded only at `$FFFC-$FFFF`. Codemasters writes
are decoded only at `$0000`, `$4000`, and `$8000`; bit 7 of the `$4000`
value enables an 8 KiB FRAM window at `$A000-$BFFF`, with bits 2:0 selecting
one of eight FRAM banks.

Target: `ATF1508ASV-15AU100`, 3.3 V, TQFP-100. The device has 128
macrocells, but fit and timing are release gates. This prototype intentionally
does not include guessed package pin assignments. Create them only after
schematic placement so voltage, JTAG, clock-capable pins, output-enable
resources, routing and timing can be reviewed together.

Required flow before hardware release:

1. Import/translate the module into the selected ATF1508ASV-supported tool.
2. Assign every port to the reviewed U13 schematic symbol and JTAG header.
3. Constrain translated address/control input-to-memory output delays.
4. Confirm the device fits and archive equations, fitter report, timing report,
   JED file and checksum.
5. Run `python3 test_mapper_model.py` and the Icarus RTL testbench.
6. Simulate the fitted equations and test a programmed device on a
   current-limited cartridge-slot breakout.

The USB-mode tri-states require external inactive pulls on NOR/FRAM controls
and FRAM address lines A13/A14. Do not rely on CPLD power-up values for bus
safety.

Device page: <https://www.microchip.com/en-us/product/atf1508asv>
