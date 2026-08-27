#!/usr/bin/env python3
"""Host tests for manifest-driven raw-sector reads."""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from disc_manifest import build_manifest  # noqa: E402
from disc_sector import DiscSectorError, read_sector  # noqa: E402


class DiscSectorTests(unittest.TestCase):
    def test_iso_sector_read(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "game.iso"
            image.write_bytes(bytes([0x11]) * 2048 + bytes([0x22]) * 2048)
            track, payload, synthetic = read_sector(build_manifest(image), root, 1)
            self.assertEqual(track["mode"], "MODE1/2048")
            self.assertEqual(payload, bytes([0x22]) * 2048)
            self.assertFalse(synthetic)

    def test_cue_file_offset_and_pregap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data.bin").write_bytes(bytes([0x31]) * 2352 * 2)
            (root / "audio.bin").write_bytes(bytes([0x42]) * 2352 * 2)
            cue = root / "game.cue"
            cue.write_text(
                'FILE "data.bin" BINARY\n'
                ' TRACK 01 MODE1/2352\n'
                '  INDEX 01 00:00:00\n'
                'FILE "audio.bin" BINARY\n'
                ' TRACK 02 AUDIO\n'
                '  PREGAP 00:00:02\n'
                '  INDEX 01 00:00:01\n',
                encoding="utf-8",
            )
            manifest = build_manifest(cue)
            second = manifest["tracks"][1]
            self.assertEqual(second["start_lba"], 4)

            track, payload, synthetic = read_sector(manifest, root, 2)
            self.assertEqual(track["number"], 2)
            self.assertEqual(payload, bytes(2352))
            self.assertTrue(synthetic)

            _, payload, synthetic = read_sector(manifest, root, 4)
            self.assertEqual(payload, bytes([0x42]) * 2352)
            self.assertFalse(synthetic)

    def test_rejects_out_of_range_and_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "game.iso"
            image.write_bytes(bytes(2048))
            manifest = build_manifest(image)
            with self.assertRaises(DiscSectorError):
                read_sector(manifest, root, 1)
            manifest["tracks"][0]["file"] = "../outside.iso"
            with self.assertRaises(DiscSectorError):
                read_sector(manifest, root, 0)


if __name__ == "__main__":
    unittest.main()
