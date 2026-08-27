# Safety and first bring-up

This is prototype hardware for ageing original equipment. Complete every bench check before inserting it into a Mega Drive/Genesis, 32X, or Sonic & Knuckles cartridge.

## Assembly and mechanical inspection

1. Confirm PCB thickness, hard-gold fingers, bevel, contact pitch, A/B orientation, and insertion depth against a known-good Mega Drive cartridge.
2. Measure the Sonic & Knuckles upper-slot opening, door/latch travel, shell wall, component height, and extraction clearance. Do not assume direct-console fit proves upper-slot fit.
3. Measure the real 32X cartridge-slot opening, door travel, shell wall, component height, insertion depth, and extraction clearance.
4. Check all QFN, TSOP, SOIC, translator, and USB-C pins under magnification.
5. Verify `/CART` is grounded. In MD mode `/M3`, VA21, and VA22 must float; in SMS mode only their open-drain FETs may pull low.
6. Confirm SW4 low means SEGA/LINEAR and high means CODEMASTERS/S3 SAVE.
7. Measure resistance from every supply rail to ground before applying power.

## USB-only test

Use a current-limited 5 V supply set initially to 100 mA.

1. Apply 5 V at `USB_VBUS` with `CART_5V` disconnected.
2. Confirm `SYS_5V` and `3V3` before fitting the RP2350B or memories.
3. Confirm no measurable voltage appears at cartridge contacts A2/A31.
4. Confirm the PC enumerates `MATRIXDRV`.
5. Confirm every cartridge-facing translator pin is high impedance.
6. Confirm U17, U18, and U20 chip enables remain inactive.

## Console-supply simulation

Do not use a console for this stage. Apply current-limited 5 V at `CART_5V` through a cartridge breakout.

1. Leave USB disconnected and confirm `BUS_DISABLE` is low.
2. Confirm each dual-supply translator has the intended 5 V and 3.3 V rails.
3. Confirm RP2350 parallel-bus GPIOs remain inputs.
4. In MD/LINEAR, compare NOR address and data patterns with a logic analyser.
5. In MD/S3 SAVE, sweep word addresses `$0FFFFF-$102000` and verify U20 is selected only at `$100000-$101FFF`.
6. During U20 reads/writes, verify ROM CE/OE are inactive, U17/U18 remain disabled, U7 OE is high, U6 has the correct direction, and `/CAS0`/`/LWR` meet U20 timing.
7. In SMS/SEGA, verify reset banks 0/1/2, `$FFFC-$FFFF`, the fixed first 1 KiB, and both 16 KiB FRAM banks.
8. In SMS/CODEMASTERS, verify exact mapper writes, ROM at `$8000-$9FFF`, and all eight 8 KiB FRAM banks.
9. Confirm worst-case translator+CPLD+NOR/FRAM delay meets the console bus windows.

## FPGA FM spin bench test

Only begin after the base SMS bus tests pass. Keep SL1 and SR2 disconnected for
the first logic tests.

1. Power the FPGA rails from a current-limited breakout and verify 1.1 V, 2.5 V
   and 3.3 V sequencing/current before fitting the FPGA configuration flash.
2. Program a diagnostic bitstream and prove every MEM_D pin is high-impedance
   during configuration, MD mode and USB mode.
3. In SMS mode, drive qualified F0/F1 writes and verify exactly one clean core
   write for each I/O cycle. Repeat the same low address with `/IORQ` inactive
   and verify no write occurs.
4. Verify F2 resets to `FF`, stores only bits 2:0, and drives MEM_D0-D7 only
   while VA19 `/IORQ` and `/CAS0` are both active for port `F2`.
5. Prove the NOR and all FRAM chip enables remain inactive throughout F0-F2
   cycles and that U6 turnaround has no contention.
6. With audio injection still disconnected, measure FM_PDM and both low-pass
   nodes for expected density, cutoff, DC blocking and ultrasonic residue.
7. Fit conservative 10 kOhm SL1/SR2 injection resistors, then scope peak and DC
   levels into a powered console before listening tests.
8. Run the YM2413 diagnostic followed by several FM-capable games. Stop for
   abnormal current, heat, bus overshoot or audio clipping.

## Dual-source isolation test

1. Apply current-limited 5 V independently to both sources.
2. Confirm no reverse current enters either source.
3. Confirm `BUS_DISABLE` rises close to `CART_5V`.
4. Confirm console-facing translators become high impedance before RP2350 GPIOs drive the NOR bus.
5. Confirm `USB_MODE_3V3` releases NOR and all FRAM controls and `md_high_disable` requests upper-byte isolation.

## First direct-console test

1. Use a protected cartridge breakout where possible.
2. Program a small known-good MD diagnostic.
3. Disconnect USB, choose MD/LINEAR, insert MatrixDrive directly, and power on through a current monitor.
4. Stop immediately for abnormal current, heat, or out-of-rail bus levels.
5. Repeat with an SMS diagnostic and verify PAUSE/NMI.

## First 32X test

Only begin after direct-console MD tests pass.

1. Use a legally obtained, known-good ROM-only `.32X` diagnostic or game no larger than 4 MiB.
2. With all power removed, choose MD/LINEAR and insert MatrixDrive into the real 32X cartridge slot.
3. Install and connect the 32X normally, including its power and video-link cables.
4. Power the stack through a current monitor and verify the 32X startup/security sequence completes.
5. Stop immediately for abnormal current, heat, boot loops, or out-of-rail bus levels.
6. Capture `/CE_0`, `/CAS0`, address, and data timing at low, banked, and top-of-ROM addresses.
7. Power off and remove the complete stack before reconnecting USB.

See `32x-mode.md` for the exact image checks and unsupported save hardware.

## First Sonic & Knuckles test

Only begin after direct-console tests pass.

1. Clean and inspect both sets of contacts on an original Sonic & Knuckles cartridge.
2. With all power removed, load a legal Sonic 2 image, choose MD/LINEAR, insert MatrixDrive into the upper slot, then insert the lock-on cartridge into the console.
3. Power through a current monitor and verify Sonic 2 & Knuckles boot/read timing.
4. Power off and remove the complete stack before changing the image or switches.
5. Load a legal Sonic 3 image, choose MD/S3 SAVE, and repeat.
6. Verify U20 save writes and persistence; confirm U17/U18 contents do not change.
7. Capture `/CE_0`, `/CAS0`, `/LWR`, VA21, U7 OE, ROM CE, and U20 CE for the archive.

Never hot-plug either cartridge. Never connect USB to a stacked cartridge. Do not attach an oscilloscope earth clip until the console/test-equipment grounding arrangement is verified.
