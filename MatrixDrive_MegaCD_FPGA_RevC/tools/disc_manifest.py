#!/usr/bin/env python3
"""Build a deterministic Mega-CD sector manifest from ISO or BIN/CUE input."""

from __future__ import annotations

import argparse
import json
import shlex
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


class DiscManifestError(ValueError):
    """The image layout cannot be represented by the Revision C loader."""


MODE_INFO = {
    "MODE1/2048": (2048, 0, 2048, 4),
    "MODE1/2352": (2352, 16, 2048, 4),
    "MODE2/2336": (2336, 8, 2048, 4),
    "MODE2/2352": (2352, 24, 2048, 4),
    "AUDIO": (2352, 0, 2352, 0),
}


@dataclass
class CueTrack:
    number: int
    mode: str
    file_path: Path
    index01: int | None = None
    pregap: int = 0


@dataclass
class ManifestTrack:
    number: int
    mode: str
    control: int
    file: str
    file_offset_bytes: int
    raw_sector_bytes: int
    user_data_offset: int
    user_data_bytes: int
    index01_file_sector: int
    pregap_sectors: int
    start_lba: int
    sector_count: int


def msf_to_frames(value: str, line_number: int = 0) -> int:
    fields = value.split(":")
    if len(fields) != 3:
        raise DiscManifestError(f"line {line_number}: invalid MSF value {value!r}")
    try:
        minutes, seconds, frames = (int(field, 10) for field in fields)
    except ValueError as exc:
        raise DiscManifestError(
            f"line {line_number}: non-numeric MSF value {value!r}"
        ) from exc
    if minutes < 0 or not 0 <= seconds < 60 or not 0 <= frames < 75:
        raise DiscManifestError(f"line {line_number}: out-of-range MSF {value!r}")
    return (minutes * 60 + seconds) * 75 + frames


def _tokens(line: str, line_number: int) -> list[str]:
    try:
        return shlex.split(line, posix=True)
    except ValueError as exc:
        raise DiscManifestError(f"line {line_number}: {exc}") from exc


def parse_cue(cue_path: Path) -> list[CueTrack]:
    try:
        lines = cue_path.read_text(encoding="utf-8-sig").splitlines()
    except UnicodeDecodeError as exc:
        raise DiscManifestError("CUE must be UTF-8 or ASCII text") from exc

    current_file: Path | None = None
    current_track: CueTrack | None = None
    tracks: list[CueTrack] = []

    for line_number, raw_line in enumerate(lines, 1):
        stripped = raw_line.strip()
        if not stripped:
            continue
        parts = _tokens(stripped, line_number)
        if not parts:
            continue
        command = parts[0].upper()

        if command == "REM":
            continue
        if command == "FILE":
            if len(parts) < 3 or parts[-1].upper() != "BINARY":
                raise DiscManifestError(
                    f"line {line_number}: only FILE ... BINARY is supported"
                )
            filename = " ".join(parts[1:-1])
            current_file = (cue_path.parent / filename).resolve()
            current_track = None
        elif command == "TRACK":
            if current_file is None or len(parts) != 3:
                raise DiscManifestError(
                    f"line {line_number}: TRACK requires a preceding FILE"
                )
            try:
                number = int(parts[1], 10)
            except ValueError as exc:
                raise DiscManifestError(
                    f"line {line_number}: invalid track number {parts[1]!r}"
                ) from exc
            mode = parts[2].upper()
            if mode not in MODE_INFO:
                raise DiscManifestError(
                    f"line {line_number}: unsupported track mode {mode}"
                )
            if number < 1 or number > 99:
                raise DiscManifestError(
                    f"line {line_number}: track number must be 1..99"
                )
            current_track = CueTrack(number=number, mode=mode,
                                     file_path=current_file)
            tracks.append(current_track)
        elif command == "INDEX":
            if current_track is None or len(parts) != 3:
                raise DiscManifestError(
                    f"line {line_number}: INDEX requires an active TRACK"
                )
            try:
                index_number = int(parts[1], 10)
            except ValueError as exc:
                raise DiscManifestError(
                    f"line {line_number}: invalid INDEX number"
                ) from exc
            if index_number == 1:
                if current_track.index01 is not None:
                    raise DiscManifestError(
                        f"line {line_number}: duplicate INDEX 01"
                    )
                current_track.index01 = msf_to_frames(parts[2], line_number)
        elif command == "PREGAP":
            if current_track is None or len(parts) != 2:
                raise DiscManifestError(
                    f"line {line_number}: PREGAP requires an active TRACK"
                )
            current_track.pregap = msf_to_frames(parts[1], line_number)
        elif command in {"TITLE", "PERFORMER", "SONGWRITER", "CATALOG",
                         "ISRC", "FLAGS", "POSTGAP", "CDTEXTFILE"}:
            # Metadata and postgaps do not change source-sector addressing in
            # the Phase-1 service contract.
            continue
        else:
            raise DiscManifestError(
                f"line {line_number}: unsupported CUE command {command}"
            )

    if not tracks:
        raise DiscManifestError("CUE contains no tracks")
    if [track.number for track in tracks] != sorted(
            {track.number for track in tracks}):
        raise DiscManifestError("track numbers must be unique and ascending")
    for track in tracks:
        if track.index01 is None:
            raise DiscManifestError(f"track {track.number:02d} has no INDEX 01")
        if not track.file_path.is_file():
            raise DiscManifestError(
                f"track {track.number:02d} file not found: {track.file_path.name}"
            )
    return tracks


def _file_sector_count(path: Path, sector_bytes: int) -> int:
    size = path.stat().st_size
    if size == 0 or size % sector_bytes:
        raise DiscManifestError(
            f"{path.name}: size {size} is not a non-zero multiple of "
            f"{sector_bytes}"
        )
    return size // sector_bytes


def build_cue_manifest(cue_path: Path) -> dict:
    cue_path = cue_path.resolve()
    tracks = parse_cue(cue_path)
    output: list[ManifestTrack] = []
    disc_lba = 0

    for index, track in enumerate(tracks):
        sector_bytes, user_offset, user_bytes, control = MODE_INFO[track.mode]
        assert track.index01 is not None
        total_file_sectors = _file_sector_count(track.file_path, sector_bytes)

        next_track = tracks[index + 1] if index + 1 < len(tracks) else None
        if next_track is not None and next_track.file_path == track.file_path:
            next_sector_bytes = MODE_INFO[next_track.mode][0]
            if next_sector_bytes != sector_bytes:
                raise DiscManifestError(
                    f"tracks {track.number:02d}/{next_track.number:02d} share "
                    "one file but use different raw sector sizes"
                )
            assert next_track.index01 is not None
            sector_count = next_track.index01 - track.index01
        else:
            sector_count = total_file_sectors - track.index01

        if track.index01 >= total_file_sectors or sector_count <= 0:
            raise DiscManifestError(
                f"track {track.number:02d}: INDEX/length is outside source file"
            )

        disc_lba += track.pregap
        try:
            relative_file = str(track.file_path.relative_to(cue_path.parent))
        except ValueError:
            relative_file = track.file_path.name
        output.append(ManifestTrack(
            number=track.number,
            mode=track.mode,
            control=control,
            file=relative_file,
            file_offset_bytes=track.index01 * sector_bytes,
            raw_sector_bytes=sector_bytes,
            user_data_offset=user_offset,
            user_data_bytes=user_bytes,
            index01_file_sector=track.index01,
            pregap_sectors=track.pregap,
            start_lba=disc_lba,
            sector_count=sector_count,
        ))
        disc_lba += sector_count

    return {
        "format": "matrixdrive-megacd-manifest-v1",
        "source": cue_path.name,
        "source_type": "cue",
        "leadout_lba": disc_lba,
        "tracks": [asdict(track) for track in output],
    }


def build_iso_manifest(iso_path: Path) -> dict:
    iso_path = iso_path.resolve()
    if not iso_path.is_file():
        raise DiscManifestError(f"ISO not found: {iso_path}")
    sectors = _file_sector_count(iso_path, 2048)
    track = ManifestTrack(
        number=1,
        mode="MODE1/2048",
        control=4,
        file=iso_path.name,
        file_offset_bytes=0,
        raw_sector_bytes=2048,
        user_data_offset=0,
        user_data_bytes=2048,
        index01_file_sector=0,
        pregap_sectors=0,
        start_lba=0,
        sector_count=sectors,
    )
    return {
        "format": "matrixdrive-megacd-manifest-v1",
        "source": iso_path.name,
        "source_type": "iso",
        "leadout_lba": sectors,
        "tracks": [asdict(track)],
    }


def build_manifest(source: Path) -> dict:
    suffix = source.suffix.casefold()
    if suffix == ".cue":
        return build_cue_manifest(source)
    if suffix == ".iso":
        return build_iso_manifest(source)
    raise DiscManifestError("source must be .iso or .cue (use .cue for BIN data)")


def _dump(manifest: dict, output: Path | None) -> None:
    encoded = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    if output is None:
        print(encoded, end="")
    else:
        output.write_text(encoded, encoding="utf-8")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help=".iso or .cue to inspect")
    parser.add_argument("--output", "-o", type=Path,
                        help="JSON output (stdout when omitted)")
    args = parser.parse_args(argv)
    try:
        _dump(build_manifest(args.source), args.output)
    except DiscManifestError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
