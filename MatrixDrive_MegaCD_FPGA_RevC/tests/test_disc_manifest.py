#!/usr/bin/env python3
"""Host tests for Revision C ISO and BIN/CUE metadata handling."""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from disc_manifest import DiscManifestError, build_manifest  # noqa: E402


class DiscManifestTests(unittest.TestCase):
    def test_iso_is_single_mode1_track(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "data.iso"
            image.write_bytes(bytes(2048 * 9))
            manifest = build_manifest(image)
            self.assertEqual(manifest["source_type"], "iso")
            self.assertEqual(manifest["leadout_lba"], 9)
            self.assertEqual(manifest["tracks"][0]["mode"], "MODE1/2048")
            self.assertEqual(manifest["tracks"][0]["sector_count"], 9)

    def test_single_bin_mixed_mode_cue(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "disc.bin").write_bytes(bytes(2352 * 150))
            (root / "disc.cue").write_text(
                'FILE "disc.bin" BINARY\n'
                '  TRACK 01 MODE1/2352\n'
                '    INDEX 01 00:00:00\n'
                '  TRACK 02 AUDIO\n'
                '    INDEX 00 00:00:74\n'
                '    INDEX 01 00:01:00\n',
                encoding="utf-8",
            )
            manifest = build_manifest(root / "disc.cue")
            self.assertEqual([t["sector_count"] for t in manifest["tracks"]],
                             [75, 75])
            self.assertEqual(manifest["tracks"][1]["control"], 0)
            self.assertEqual(manifest["tracks"][1]["file_offset_bytes"],
                             75 * 2352)

    def test_multiple_bin_files_and_pregap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "track 01.bin").write_bytes(bytes(2352 * 20))
            (root / "track 02.bin").write_bytes(bytes(2352 * 30))
            (root / "game.cue").write_text(
                'FILE "track 01.bin" BINARY\n'
                ' TRACK 01 MODE2/2352\n'
                '  INDEX 01 00:00:00\n'
                'FILE "track 02.bin" BINARY\n'
                ' TRACK 02 AUDIO\n'
                '  PREGAP 00:02:00\n'
                '  INDEX 01 00:00:00\n',
                encoding="utf-8",
            )
            manifest = build_manifest(root / "game.cue")
            first, second = manifest["tracks"]
            self.assertEqual(first["sector_count"], 20)
            self.assertEqual(second["start_lba"], 170)
            self.assertEqual(second["pregap_sectors"], 150)
            self.assertEqual(manifest["leadout_lba"], 200)

    def test_mode2_2336(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "mode2.bin").write_bytes(bytes(2336 * 3))
            (root / "mode2.cue").write_text(
                'FILE "mode2.bin" BINARY\n'
                ' TRACK 01 MODE2/2336\n'
                '  INDEX 01 00:00:00\n',
                encoding="utf-8",
            )
            track = build_manifest(root / "mode2.cue")["tracks"][0]
            self.assertEqual(track["raw_sector_bytes"], 2336)
            self.assertEqual(track["user_data_offset"], 8)

    def test_invalid_inputs_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bad_iso = root / "bad.iso"
            bad_iso.write_bytes(b"not a complete sector")
            with self.assertRaises(DiscManifestError):
                build_manifest(bad_iso)

            cue = root / "missing.cue"
            cue.write_text(
                'FILE "missing.bin" BINARY\n'
                ' TRACK 01 MODE1/2352\n'
                '  INDEX 01 00:00:00\n',
                encoding="utf-8",
            )
            with self.assertRaises(DiscManifestError):
                build_manifest(cue)

    def test_bin_without_cue_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "orphan.bin"
            image.write_bytes(bytes(2352))
            with self.assertRaises(DiscManifestError):
                build_manifest(image)


if __name__ == "__main__":
    unittest.main(verbosity=2)
