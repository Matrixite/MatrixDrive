# MegaSD-style cartridge architecture

## What Revision C emulates

The real Mega Drive keeps its own 68000, Z80, VDP, controllers and normal video
output. The cartridge FPGA supplies the Mega-CD side:

- 12.5 MHz sub-68000;
- gate-array registers, ownership and interrupts;
- 512 KiB program RAM and 256 KiB Word RAM;
- graphics-cell conversion/rotation/scaling engine;
- CDC/CDD command and DMA behaviour;
- 64 KiB PCM RAM and eight-channel PCM audio;
- CDDA sector timing and stereo playback;
- backup RAM and BIOS mapping.

There is no optical mechanism. The RP2350 reads the selected image from
microSD and supplies raw sectors to the FPGA at the requested logical block.

## Data paths

```text
PC <--USB-C MSC--> RP2350B <--SPI--> microSD
                         |
                         +--QSPI sector/command link--> Cyclone V FPGA

Mega Drive 68000 bus <--> 5V/3V3 translators <--> FPGA Mega-CD bridge/core
Mega Drive audio input <-- analog mixer/DAC <----- FPGA PCM + CDDA
```

USB storage and console execution are mutually exclusive. USB mode holds all
cartridge outputs high-impedance and grants the RP2350 exclusive microSD
ownership. Console mode unmounts USB storage before the FPGA may request files.

## Address contract

`matrixcd_cart_bridge.sv` exposes byte addresses to the eventual core and
recognises these main-CPU regions:

| Window | Function | Bridge selection |
| --- | --- | --- |
| `$000000-$03FFFF` | BIOS/program-RAM aperture | `/CE_0` plus full address |
| `$200000-$23FFFF` | 256 KiB Word RAM | `/CE_0` plus full address |
| `$600000-$607FFF` | backup-RAM development aperture | `/AS` plus full address |
| `$A12000-$A120FF` | Mega-CD gate-array registers | `/AS` plus full address |

The core remains responsible for exact BIOS overlay, program-RAM banking,
Word-RAM 1M/2M ownership, write protection, register semantics and wait-state
timing. The bridge merely converts a physical 68000 cycle into a stable
request/acknowledge transaction.

`/DTACK` must be driven through an open-drain transistor. RTL exports only an
output-enable request and can never drive the console line high.

## Disc service

The RP2350 parses the CUE sheet and supplies a compact manifest containing
track type, raw sector size, file offset, file-relative INDEX 01, start LBA and
sector count. The FPGA requests one logical sector. Firmware reads 2048, 2336
or 2352 bytes from the corresponding file and normalises it into the raw-sector
contract expected by the CDC integration.

The initial RTL buffer is one full 2352-byte sector. The production design
should use at least two buffers so microSD latency cannot starve continuous
CDDA playback.

## Clock and memory plan

- 50 MHz low-jitter oscillator into FPGA PLLs.
- Console VCLK sampled independently for cartridge-bus synchronisation.
- 12.5 MHz sub-68000 enable generated synchronously inside the core.
- 32 MiB x16 SDRAM holds Mega-CD RAM, cache and working state.
- Dedicated 64-Mbit configuration QSPI flash.

All clock crossings require explicit synchronisers or asynchronous FIFOs in
the fitted design. The current single-clock sector buffer is an interface
reference, not the final CDC implementation.
