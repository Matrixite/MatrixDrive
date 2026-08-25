# Safety and first bring-up

This is prototype hardware for ageing original equipment. Complete every bench
check before inserting it into a Mega Drive or Genesis.

## Assembly inspection

1. Confirm the PCB thickness and gold-finger bevel against a known-good
   cartridge. A thick or square-edged PCB can damage the console connector.
2. Check that A-side and B-side numbering has not been mirrored during layout.
3. Check all QFN, TSOP and USB-C pins under magnification.
4. Verify that `/CART` is grounded; in MD mode `/M3`, VA21 and VA22 float, and
   in SMS mode their open-drain FETs pull low without sourcing voltage.
5. Measure resistance from every supply rail to ground before applying power.

## USB-only test

Use a current-limited 5 V supply set initially to 100 mA.

1. Apply 5 V at `USB_VBUS`; leave `CART_5V` disconnected.
2. Confirm `SYS_5V` is approximately one Schottky drop below the input.
3. Confirm `3V3` is 3.3 V before fitting the RP2350B or flash devices.
4. Confirm no measurable voltage appears at cartridge contacts A2 or A31.
5. With all devices fitted, confirm the PC enumerates `MATRIXDRV`.
6. Confirm every cartridge-facing translator pin is high impedance.

## Console-supply simulation

Do not use a console for this stage. Apply a current-limited 5 V bench supply at
`CART_5V`.

1. Leave USB disconnected and confirm `BUS_DISABLE` is low.
2. Confirm each translator has 5 V on VCCA and 3.3 V on VCCB.
3. Confirm RP2350 parallel-bus GPIOs remain inputs.
4. In MD mode, feed test address/control patterns through a cartridge-slot
   breakout and compare flash data with a logic analyser.
5. In SMS mode, verify reset banks 0/1/2, writes to `$FFFC-$FFFF`, the fixed
   first 1 KiB, both FRAM banks, and PAUSE before connecting a console.
6. Confirm ROM/FRAM access, including translator and CPLD delay, meets both
   console read windows.

## Dual-source isolation test

1. Apply current-limited 5 V independently to both sources.
2. Confirm no reverse current enters either source.
3. Confirm `BUS_DISABLE` rises close to `CART_5V`.
4. Confirm all console-facing translators become high impedance before allowing the
   RP2350B to drive ROM-side signals.
5. Confirm `USB_MODE_3V3` releases every U13 NOR output while PROGRAM-button
   operation leaves that isolation signal unchanged.

## First console test

1. Use a sacrificial or protected cartridge-slot breakout where possible.
2. Program a tiny, known-good Mega Drive homebrew diagnostic ROM.
3. Disconnect USB and power the console off.
4. Insert the cartridge and power on through a current monitor.
5. Stop immediately if current rises abnormally, the regulator heats, or any bus
   line is driven above its permitted rail.
6. Power off, install a small SMS diagnostic, set SW2 to SMS, repeat the current
   check, and verify the cartridge PAUSE button produces NMI.

Do not hot-plug the cartridge. Do not attach an oscilloscope earth clip unless
the console and test equipment grounding arrangement has been checked.
