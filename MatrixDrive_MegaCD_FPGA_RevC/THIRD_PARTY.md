# Third-party and clean-room boundary

Revision C contains only newly written MatrixDrive interface, parsing and test
code. It does not contain Terraonion MegaSD or Mega EverDrive Pro code,
firmware, keys, bitstreams, BIOS data or board files.

The open-source MegaCD MiSTer project is a useful functional reference and a
candidate source for the Mega-CD subsystem:

- Project: <https://github.com/MiSTer-devel/MegaCD_MiSTer>
- License: GNU GPL version 3
- Upstream currently supports CUE with single or multiple image files and CHD.

If its RTL is imported or adapted, keep upstream notices and publish the
complete corresponding combined FPGA source under GPL-3.0. Do not relabel
upstream RTL as MIT. BIOS and game images remain user-supplied and are never
committed.

Hardware register behaviour should be checked against legitimately available
Sega Mega-CD hardware/software manuals and measurements from owned hardware.
