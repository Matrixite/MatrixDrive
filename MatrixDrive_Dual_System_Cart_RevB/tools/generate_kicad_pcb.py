#!/usr/bin/env python3
"""Generate the Rev B dual-system and lock-on placement-only KiCad template."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "hardware" / "MatrixDrive-RevB.kicad_pcb"


def text(reference: str, x: float, y: float, layer: str = "F.SilkS") -> str:
    return (
        f'  (gr_text "{reference}" (at {x:.2f} {y:.2f}) (layer "{layer}")\n'
        '    (effects (font (size 1.20 1.20) (thickness 0.20)))\n'
        '  )\n'
    )


def placeholder(ref: str, label: str, x: float, y: float, w: float, h: float) -> str:
    return f'''  (footprint "MatrixDrive:PLACEMENT_{ref}" (layer "F.Cu") (at {x:.2f} {y:.2f})
    (attr board_only exclude_from_pos_files exclude_from_bom)
    (fp_rect (start {-w/2:.2f} {-h/2:.2f}) (end {w/2:.2f} {h/2:.2f})
      (stroke (width 0.25) (type default)) (fill none) (layer "F.SilkS"))
    (fp_text reference "{ref}" (at 0 {-h/2-1.0:.2f}) (layer "F.SilkS")
      (effects (font (size 1 1) (thickness 0.15))))
    (fp_text value "{label}" (at 0 0) (layer "F.Fab")
      (effects (font (size 0.8 0.8) (thickness 0.12))))
  )
'''


def edge_connector() -> str:
    lines = [
        '  (footprint "MatrixDrive:MD_2x32_EDGE" (layer "F.Cu") (at 0 0)\n',
        '    (attr board_only exclude_from_pos_files exclude_from_bom)\n',
        '    (fp_text reference "J1" (at 5 59 90) (layer "F.SilkS")\n',
        '      (effects (font (size 1.2 1.2) (thickness 0.2))))\n',
        '    (fp_text value "MEGA_DRIVE_EDGE_VERIFY_ORIENTATION" (at 95 55 90) (layer "F.Fab")\n',
        '      (effects (font (size 0.8 0.8) (thickness 0.12))))\n',
    ]
    first_x = 10.63
    for pin in range(1, 33):
        x = first_x + (pin - 1) * 2.54
        lines.append(
            f'    (pad "B{pin}" connect rect (at {x:.2f} 61.50) '
            '(size 1.80 7.00) (layers "F.Cu" "F.Mask"))\n'
        )
        lines.append(
            f'    (pad "A{pin}" connect rect (at {x:.2f} 61.50) '
            '(size 1.80 7.00) (layers "B.Cu" "B.Mask"))\n'
        )
    lines.append('  )\n')
    return ''.join(lines)


def build() -> str:
    header = '''(kicad_pcb (version 20240108) (generator pcbnew)
  (general (thickness 1.6))
  (paper "A4")
  (layers
    (0 "F.Cu" signal)
    (31 "B.Cu" signal)
    (36 "B.SilkS" user "b.silkscreen")
    (37 "F.SilkS" user "f.silkscreen")
    (44 "Edge.Cuts" user)
  )
  (setup (pad_to_mask_clearance 0))
'''
    body = [header]
    body.append('  (gr_rect (start 0 0) (end 100 65) (stroke (width 0.10) (type default)) (fill none) (layer "Edge.Cuts"))\n')
    body.append(text("MATRIXDRIVE REV B DUAL-SYSTEM + LOCK-ON — PLACEMENT ONLY", 50, 3))
    body.append(text("DO NOT FABRICATE UNTIL SCHEMATIC/DRC REVIEW", 50, 6))
    body.append(edge_connector())
    body.extend([
        placeholder("J2", "USB-C", 49, 1.5, 10, 7),
        placeholder("U1", "RP2350B QFN80", 48, 14, 10, 10),
        placeholder("U2", "S29GL032N TSOP48", 54, 45, 18.4, 12),
        placeholder("U3", "ADDR XCVR 0-7", 15, 41, 8, 6.5),
        placeholder("U4", "ADDR XCVR 8-15", 24, 41, 8, 6.5),
        placeholder("U5", "ADDR/CTRL XCVR", 33, 41, 8, 6.5),
        placeholder("U6", "LOW DATA BIDI", 76, 41, 8, 6.5),
        placeholder("U7", "HIGH DATA OUT", 85, 41, 8, 6.5),
        placeholder("U9", "BOOT QSPI", 37, 14, 6, 5),
        placeholder("U10", "STAGING SPI", 59, 14, 6, 5),
        placeholder("U11", "3V3 LDO", 13, 11, 5, 4),
        placeholder("U13", "ATF1508ASV CPLD", 27, 26, 14, 14),
        placeholder("U14", "CTRL2 XCVR", 13, 27, 8, 6.5),
        placeholder("U15-U16", "DATA CONTROL ORS", 75, 30, 7, 5),
        placeholder("U17", "32KiB SMS FRAM LOW", 88, 25, 10, 8),
        placeholder("U18", "32KiB SMS FRAM HIGH", 88, 34, 10, 8),
        placeholder("U19", "MD HIGH DISABLE XCVR", 75, 24, 6, 4),
        placeholder("U20", "SONIC 3 SAVE FRAM", 88, 51, 10, 8),
        placeholder("J4", "CPLD JTAG", 8, 4, 8, 5),
        placeholder("Y1", "12MHz", 40, 7, 4, 3),
        placeholder("L1", "POLARISED 3V3 CORE L", 57, 7, 4, 3),
        placeholder("SW1", "PROGRAM", 73, 7, 6, 4),
        placeholder("SW2", "MD / SMS", 86, 7, 8, 4),
        placeholder("SW3", "SMS PAUSE", 86, 14, 8, 4),
        placeholder("SW4", "SEGA-LINEAR / CODIES-S3 SAVE", 86, 20, 16, 4),
        placeholder("D3-D5", "STATUS LEDS", 72, 19, 8, 4),
    ])
    body.append(text("STANDARD MD EDGE / S&K UPPER-SLOT PROFILE — VERIFY SHELL", 50, 56))
    body.append(')\n')
    return ''.join(body)


if __name__ == "__main__":
    OUTPUT.write_text(build(), encoding="utf-8")
    print(OUTPUT)
