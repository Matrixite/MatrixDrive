#!/usr/bin/env python3
"""Validate the source-only MatrixDrive MegaCD FPGA Rev C prototype."""

from __future__ import annotations

import csv
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / "fpga" / "rtl"
TB = ROOT / "fpga" / "tb"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_csv() -> None:
    connector_path = ROOT / "hardware" / "connector-pinout.csv"
    with connector_path.open(newline="", encoding="utf-8") as handle:
        connector = list(csv.DictReader(handle))
    require(len(connector) == 64, "connector-pinout.csv must list 64 contacts")
    contacts = {row["Contact"] for row in connector}
    expected = {f"{side}{number}" for side in "AB" for number in range(1, 33)}
    require(contacts == expected, "connector contact list is incomplete or duplicated")

    for filename, minimum_rows in (("bom.csv", 20), ("electrical-netlist.csv", 20)):
        path = ROOT / "hardware" / filename
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        require(len(rows) >= minimum_rows, f"{filename} is unexpectedly incomplete")
        require(all(all(value.strip() for value in row.values()) for row in rows),
                f"{filename} contains an empty field")


def validate_source_policy() -> None:
    forbidden_suffixes = {".bin", ".iso", ".chd", ".rom", ".bit", ".sof", ".pof"}
    forbidden = [
        path.relative_to(ROOT)
        for path in ROOT.rglob("*")
        if path.is_file() and path.suffix.lower() in forbidden_suffixes
    ]
    require(not forbidden, f"copyrighted/generated binary files found: {forbidden}")

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    require("does not yet boot retail Mega-CD software" in readme,
            "README must retain the prototype completion boundary")
    require("No BIOS or game images are included" in readme,
            "README must retain the BIOS/game-image notice")


def run(command: list[str], cwd: Path = ROOT) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=cwd, check=True)


def run_python_tests() -> None:
    run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"])


def run_rtl_tests() -> None:
    iverilog = shutil.which("iverilog")
    vvp = shutil.which("vvp")
    require(bool(iverilog and vvp), "iverilog and vvp are required for RTL validation")

    cases = {
        "cart_bridge": [RTL / "matrixcd_cart_bridge.sv", TB / "test_matrixcd_cart_bridge.sv"],
        "sector_buffer": [RTL / "disc_sector_buffer.sv", TB / "test_disc_sector_buffer.sv"],
    }
    with tempfile.TemporaryDirectory(prefix="matrixcd-rtl-") as build_dir:
        build = Path(build_dir)
        for name, sources in cases.items():
            output = build / f"{name}.vvp"
            run([iverilog, "-g2012", "-Wall", "-s", f"test_matrixcd_{name}" if name == "cart_bridge" else "test_disc_sector_buffer",
                 "-o", str(output), *(str(source) for source in sources)])
            run([vvp, str(output)])

        # Elaborate the integration shell independently as a final interface check.
        run([iverilog, "-g2012", "-Wall", "-s", "matrixcd_top", "-o", str(build / "top.vvp"),
             str(RTL / "matrixcd_cart_bridge.sv"),
             str(RTL / "disc_sector_buffer.sv"),
             str(RTL / "matrixcd_top.sv")])


def main() -> int:
    validate_csv()
    validate_source_policy()
    run_python_tests()
    run_rtl_tests()
    print("MatrixDrive MegaCD FPGA Rev C validation passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
