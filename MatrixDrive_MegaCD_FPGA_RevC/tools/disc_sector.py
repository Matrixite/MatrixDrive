#!/usr/bin/env python3
"""Read one raw sector through a MatrixDrive MegaCD disc manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


class DiscSectorError(ValueError):
    """A manifest or requested sector cannot be serviced safely."""


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DiscSectorError(f"cannot read manifest: {exc}") from exc
    if not isinstance(manifest, dict) or manifest.get("format") != (
            "matrixdrive-megacd-manifest-v1"):
        raise DiscSectorError("unsupported or missing manifest format")
    if not isinstance(manifest.get("tracks"), list):
        raise DiscSectorError("manifest tracks must be a list")
    return manifest


def _safe_image_path(root: Path, relative_name: str) -> Path:
    root = root.resolve()
    candidate = (root / relative_name).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise DiscSectorError("track file escapes the image directory") from exc
    if not candidate.is_file():
        raise DiscSectorError(f"track file not found: {relative_name}")
    return candidate


def read_sector(manifest: dict[str, Any], image_root: Path,
                lba: int) -> tuple[dict[str, Any], bytes, bool]:
    """Return (track, raw bytes, synthetic_pregap) for an internal disc LBA."""
    if not isinstance(lba, int) or lba < 0:
        raise DiscSectorError("LBA must be a non-negative integer")

    for track in manifest.get("tracks", []):
        try:
            start = int(track["start_lba"])
            pregap = int(track["pregap_sectors"])
            count = int(track["sector_count"])
            raw_bytes = int(track["raw_sector_bytes"])
        except (KeyError, TypeError, ValueError) as exc:
            raise DiscSectorError("track contains invalid numeric fields") from exc

        if raw_bytes not in (2048, 2336, 2352) or min(start, pregap, count) < 0:
            raise DiscSectorError("track contains an invalid layout")

        if start - pregap <= lba < start:
            # Explicit CUE PREGAP has no source-file sectors. Zero bytes are
            # digital silence for AUDIO and a deterministic empty data sector
            # for the Phase-1 service model.
            return track, bytes(raw_bytes), True

        if start <= lba < start + count:
            try:
                filename = str(track["file"])
                base_offset = int(track["file_offset_bytes"])
            except (KeyError, TypeError, ValueError) as exc:
                raise DiscSectorError("track source fields are invalid") from exc
            image = _safe_image_path(image_root, filename)
            offset = base_offset + (lba - start) * raw_bytes
            with image.open("rb") as handle:
                handle.seek(offset)
                payload = handle.read(raw_bytes)
            if len(payload) != raw_bytes:
                raise DiscSectorError(
                    f"short read from {filename} at byte offset {offset}"
                )
            return track, payload, False

    raise DiscSectorError(f"LBA {lba} is outside the disc layout")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="generated .mcd.json file")
    parser.add_argument("lba", type=int, help="internal LBA; track 1 INDEX 01 is 0")
    parser.add_argument("--image-root", type=Path,
                        help="directory containing track files; defaults to manifest directory")
    parser.add_argument("--output", "-o", required=True, type=Path,
                        help="raw sector output file")
    args = parser.parse_args()
    try:
        manifest = load_manifest(args.manifest)
        root = args.image_root or args.manifest.parent
        track, payload, synthetic = read_sector(manifest, root, args.lba)
        args.output.write_bytes(payload)
        source = "synthetic pregap" if synthetic else track["file"]
        print(f"track {int(track['number']):02d}: {len(payload)} bytes from {source}")
    except (DiscSectorError, OSError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
