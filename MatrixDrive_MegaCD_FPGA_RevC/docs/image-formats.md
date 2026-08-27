# Disc-image formats

## ISO

A `.iso` is mounted as one MODE1/2048 data track starting at LBA 0. File size
must be a non-zero multiple of 2048 bytes. ISO cannot describe CD-audio tracks,
pregaps or mixed-mode layouts.

## BIN + CUE

The CUE parser accepts quoted or unquoted `FILE ... BINARY` entries and these
track modes:

- `MODE1/2048`
- `MODE1/2352`
- `MODE2/2336`
- `MODE2/2352`
- `AUDIO` (2352 bytes per sector)

Single-image and one-file-per-track layouts are supported. Each track needs an
`INDEX 01`; `PREGAP` is included in disc-LBA placement. Every referenced image
must exist and its useful byte range must contain complete sectors.

The manifest does not change the image. It records:

- track number and mode;
- control nibble (`4` data or `0` audio);
- source filename;
- source byte offset and raw sector size;
- start LBA, sector count and pregap sectors;
- user-data offset/length for data tracks.

## Deliberate omissions

- CHD is not part of the first MatrixDrive loader.
- MP3/OGG/WAV tracks are not accepted; decode audio to raw BIN first.
- ZIP archives are not mounted.
- Subchannel files, copy protection and malformed/nonstandard CUE dialects are
  not claimed compatible.
