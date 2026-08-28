#!/usr/bin/env python3
"""Static checks that do not require KiCad or the Pico SDK."""

import csv
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check_public_references() -> None:
    forbidden = (
        bytes((77, 65, 77, 69)).decode("ascii"),
        bytes((109, 97, 109, 101, 100, 101, 118)).decode("ascii"),
    )
    paths = [ROOT.parent / "README.md", ROOT / "README.md"]
    paths.extend(sorted((ROOT / "docs").glob("*.md")))
    for path in paths:
        content = path.read_text(encoding="utf-8").casefold()
        for token in forbidden:
            assert token.casefold() not in content


def check_connector() -> None:
    path = ROOT / "hardware" / "connector-pinout.csv"
    rows = list(csv.DictReader(path.open(newline="", encoding="utf-8")))
    contacts = [row["Contact"] for row in rows]
    expected = [f"A{i}" for i in range(1, 33)] + [f"B{i}" for i in range(1, 33)]
    assert len(contacts) == 64
    assert set(contacts) == set(expected)
    assert len(set(contacts)) == 64


def check_gpio_map() -> None:
    header = (ROOT / "firmware" / "src" / "board_pins.h").read_text()
    required = {
        "PIN_STAGE_MISO": 40,
        "PIN_STAGE_CS_N": 41,
        "PIN_STAGE_SCK": 42,
        "PIN_STAGE_MOSI": 43,
        "PIN_USB_PROGRAM_ADC": 44,
        "PIN_LED_GREEN": 45,
        "PIN_LED_AMBER": 46,
        "PIN_LED_RED": 47,
    }
    for name, value in required.items():
        assert re.search(rf"#define\s+{name}\s+{value}u", header)
    assert "ACTIVE_ROM_BYTES     (4u * 1024u * 1024u)" in header
    assert "ACTIVE_SMS_BYTES     (2u * 1024u * 1024u)" in header


def check_pcb() -> None:
    pcb = (ROOT / "hardware" / "MatrixDrive-RevB.kicad_pcb").read_text()
    pads = re.findall(r'\(pad "([AB]\d+)"', pcb)
    assert len(pads) == 64
    assert len(set(pads)) == 64
    balance = 0
    for char in pcb:
        if char == "(": balance += 1
        elif char == ")": balance -= 1
        assert balance >= 0
    assert balance == 0
    for token in ("PLACEMENT_U19", "PLACEMENT_U20", "32X EDGE", "S&K UPPER-SLOT"):
        assert token in pcb


def run_fat_test() -> None:
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "test_fat16"
        command = [
            "cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
            "-I", str(ROOT / "firmware" / "src"),
            str(ROOT / "firmware" / "src" / "fat16.c"),
            str(ROOT / "tests" / "test_fat16.c"),
            "-o", str(output),
        ]
        subprocess.run(command, check=True)
        subprocess.run([str(output)], check=True)


def run_installer_test() -> None:
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "test_rom_installer"
        command = [
            "cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
            "-I", str(ROOT / "firmware" / "src"),
            str(ROOT / "firmware" / "src" / "rom_installer.c"),
            str(ROOT / "tests" / "test_rom_installer.c"),
            "-o", str(output),
        ]
        subprocess.run(command, check=True)
        subprocess.run([str(output)], check=True)


def run_mapper_test() -> None:
    subprocess.run(["python3", str(ROOT / "cpld" / "test_mapper_model.py")],
                   check=True)
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "test_matrixdrive_mapper"
        subprocess.run([
            "iverilog", "-g2012", "-s", "test_matrixdrive_mapper",
            "-o", str(output),
            str(ROOT / "cpld" / "matrixdrive_mapper.v"),
            str(ROOT / "cpld" / "test_matrixdrive_mapper.v"),
        ], check=True)
        subprocess.run(["vvp", str(output)], check=True)


def check_rev_b_hardware() -> None:
    bom = (ROOT / "hardware" / "bom.csv").read_text()
    netlist = (ROOT / "hardware" / "electrical-netlist.csv").read_text()
    connector = (ROOT / "hardware" / "connector-pinout.csv").read_text()
    for token in (
        "ATF1508ASV-15AU100", "U17-U18", "64 KiB total", "U19", "U20",
        "Sonic 3 lock-on save FRAM", "DPDT break-before-make",
        "SPDT break-before-make",
    ):
        assert token in bom
    for token in (
        "SMS_MODE_3V3", "SMS_MAPPER_CM_3V3", "USB_MODE_3V3",
        "FRAM_A13", "FRAM_CE_N", "FRAM_HI_CE_N", "MD_FRAM_CE_N",
        "MD_HIGH_DISABLE_3V3", "MD_HIGH_DISABLE_5V", "LOW_DATA_DIR",
    ):
        assert token in netlist
    for token in ("/M3", "/CAS2", "/LWR", "/TIME", "Sonic 3", "PAUSE/NMI"):
        assert token in connector
    rtl = (ROOT / "cpld" / "matrixdrive_mapper.v").read_text()
    for token in ("md_s3_save_selected", "md_fram_ce_n", "md_high_disable"):
        assert token in rtl
    assert (ROOT / "docs" / "sonic-knuckles-lock-on.md").is_file()
    assert (ROOT / "docs" / "32x-mode.md").is_file()


if __name__ == "__main__":
    check_public_references()
    check_connector()
    check_gpio_map()
    check_pcb()
    check_rev_b_hardware()
    run_fat_test()
    run_installer_test()
    run_mapper_test()
    print("MatrixDrive Rev B static validation passed")
