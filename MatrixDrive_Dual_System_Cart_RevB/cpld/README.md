# CPLD logic

`matrixdrive_mapper.v` is the portable logic source for U13. It contains only
instant-on mapper state and address/control equations; no console transaction
depends on the RP2350.

Target: `ATF1508ASV-15AU100`, 3.3 V, TQFP-100. The part has enough I/O and
macrocells for the 21-bit pass-through/mux and four SMS registers, but **this
prototype intentionally does not include guessed package pin assignments**.
Create them only after schematic placement so voltage, JTAG, clock-capable pins,
output-enable resources, routing and timing can be reviewed together.

Required flow before hardware release:

1. Import/translate the module into the selected ATF1508ASV-supported tool.
2. Assign every port to the reviewed U13 schematic symbol and JTAG header.
3. Constrain translated address/control input-to-memory output delays.
4. Confirm the device fits and archive equations, fitter report, timing report,
   JED file and checksum.
5. Run `python3 test_mapper_model.py`, simulate the fitted equations, then test a
   programmed device on a current-limited cartridge-slot breakout.

The USB-mode tri-states require 10 kOhm external inactive pulls on NOR/FRAM
controls. Do not rely on CPLD power-up values for bus safety.

Device page: <https://www.microchip.com/en-us/product/atf1508asv>
