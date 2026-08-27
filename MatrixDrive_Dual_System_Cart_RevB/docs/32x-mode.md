# 32X cartridge mode

## Scope

MatrixDrive can supply a cartridge ROM to a physical Sega 32X. It does not
emulate the 32X: the real adapter still provides the two SH2 processors, boot
ROM, security check, registers, video hardware, audio hardware, and cartridge
arbitration.

The 32X hardware maps a 32-Mbit cartridge space and can read the cartridge from
both its SH2 side and the Mega Drive/Genesis 68000 side. MatrixDrive's existing
4 MiB x16 NOR and MD linear CPLD path match that cartridge-ROM width and size.

## Image installation

Use a clean, normal big-endian `.32X` image no larger than 4 MiB. The installer
requires:

- file size of at least `0x400` bytes and no more than 4,194,304 bytes;
- a size divisible by four, as required by the 32X startup data layout;
- `SEGA` at byte offset `0x100`;
- `MARS CHECK MODE` at byte offset `0x3C0`.

The last check distinguishes an explicit `.32X` image from an ordinary Mega
Drive image and protects against programming an image without the expected 32X
startup/security area. The firmware does not patch this data. Every source byte
is written to parallel NOR in its original order.

When a `.32X` image is an exact power of two smaller than 4 MiB, the installer
repeats it through the complete 4 MiB active NOR. This reproduces the way a
smaller mask ROM appears when the 32X drives address pins that the original ROM
did not implement.

## Switches and physical stack

| Item | Required setting |
| --- | --- |
| SW2 | MD |
| SW4 | Low: LINEAR |
| USB | Disconnected |
| Stack | MatrixDrive -> real 32X -> Mega Drive/Genesis |

SW4 high is not a 32X profile. In MD mode it enables the Sonic 3 odd-byte FRAM
window at `$200001-$203FFF`, which would replace part of the 32X ROM and prevent
correct operation.

Power off the complete stack before insertion or removal. Do not place Sonic &
Knuckles between MatrixDrive and the 32X. Do not connect USB while MatrixDrive is
inserted into the 32X.

## What is implemented

- Standard 4 MiB linear x16 cartridge ROM.
- Explicit `.32X` FAT16 discovery and validation.
- Byte-for-byte preservation of the 32X header and security/startup code.
- Full 4 MiB mirroring for smaller power-of-two images.
- CPLD pass-through through the highest cartridge word address (`$3FFFFE`).

## Limits

- No generic 32X SRAM or EEPROM save emulation.
- No ROM images larger than 4 MiB.
- No special mapper, coprocessor, or enhancement cartridge hardware.
- Physical fit, voltage levels, bus timing, boot/security completion, and game
  operation have not yet been measured on a real 32X.

Games that depend on unsupported cartridge save memory may boot but cannot be
expected to save correctly. Use a ROM-only diagnostic or game for the first
hardware test.

## First real-32X test

Complete the USB-only, simulated-console, and direct Mega Drive tests in
`safety-and-bringup.md` first.

1. Inspect and clean the MatrixDrive and 32X cartridge contacts.
2. Install a legally obtained, known-good ROM-only `.32X` diagnostic or game.
3. Verify SW2=MD and SW4=LINEAR with all power removed.
4. Insert MatrixDrive into the unpowered 32X, then install the 32X normally.
5. Power the stack through a current monitor and stop for abnormal current,
   heat, or out-of-rail signals.
6. Capture cartridge `/CE_0`, `/CAS0`, address, and data timing at the start,
   middle, and top of the ROM range.
7. Confirm the 32X security/startup sequence completes and the program reaches
   its first interactive screen.
8. Power off and remove the complete stack before reconnecting USB.

## References

- [Sega 32X Hardware Manual transcription](https://github.com/matiaszanolli/sega-vr-disasm/blob/master/docs/32x-hardware-manual.md)
- [32X ROM identification in file(1)](https://github.com/file/file/blob/master/magic/Magdir/console)
