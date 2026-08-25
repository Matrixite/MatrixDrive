# USB workflow and indicators

## Drive behaviour

The staging volume appears as `MATRIXDRV`. It accepts one root-level `.BIN`,
`.MD`, `.GEN`, `.32X`, or `.SMS` file. Subdirectories, `.SMD`, copier-headered SMS
images and files for unsupported mappers are ignored or rejected.

After copying, use **Eject** or **Safely remove**. The cartridge remains powered
while the active flash is erased, repacked and verified. Wait for steady green
before unplugging. The staging copy remains until the PC deletes it.

The firmware uses the file extension to choose flash layout. The physical SW2
mode is deliberately not changed by USB software; set it to match the installed
image only after USB has been disconnected and before console power is applied.

## Image rules

| Format | Minimum | Maximum | Header check | Flash packing |
| --- | ---: | ---: | --- | --- |
| MD/GEN/BIN | 512 B | 4,194,304 B | `SEGA` at `0x100` | two bytes/x16 word |
| 32X | 1 KiB | 4,194,304 B | `SEGA` at `0x100`; `MARS CHECK MODE` at `0x3C0` | two bytes/x16 word |
| SMS | 8 KiB | 2,097,152 B | `TMR SEGA` at `0x1FF0`, `0x3FF0`, or `0x7FF0` | one byte/x16 word |

Odd MD images receive an `0xFF` low-byte pad. `.32X` images must be a multiple
of four bytes and retain their original security/startup area. Smaller
power-of-two `.32X` images repeat through the complete 4 MiB cartridge range.
SMS images must be headerless binary dumps. Extension alone cannot make an
unsupported mapper, save device, or enhancement cartridge compatible.

## LEDs

| State | Green | Amber | Red |
| --- | --- | --- | --- |
| USB drive mounted | slow blink | off | off |
| PC writing staging flash | off | fast blink | off |
| Erasing/programming active ROM | off | steady | off |
| Install and verification successful | steady | off | off |
| No supported ROM, wrong size, or bad header | off | off | two-blink code |
| Flash/program/verify failure | off | off | steady |

The PROGRAM button requests the same install after pending USB writes are
flushed. Do not press it while the operating system is copying data.
