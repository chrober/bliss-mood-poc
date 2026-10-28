"""Synthetic, offline verification of FMA-Small metadata-only audit."""
import csv
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_fma_metadata.py"
spec = importlib.util.spec_from_file_location("audit_fma_metadata", SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class FmaMetadataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        self.archive = self.dir / "fma_metadata.zip"
        self.write_rows([
            ("123", "small", "training", "Rock", "42"),
            ("124", "small", "validation", "Electronic", "55"),
            ("125", "small", "test", "Rock", "42"),
            ("126", "small", "test", "Electronic", "70"),
            ("127", "medium", "test", "Blues", "11"),
        ])

    def write_rows(self, rows):
        out = io.StringIO(newline="")
        writer = csv.writer(out)
        writer.writerow(["", "set", "set", "track", "artist"])
        writer.writerow(["", "subset", "split", "genre_top", "id"])
        writer.writerows(rows)
        with zipfile.ZipFile(self.archive, "w") as handle:
            handle.writestr("fma_metadata/tracks.csv", out.getvalue())

    def test_genres_splits_and_artist_collision(self):
        report = audit.inspect(self.archive)
        self.assertEqual(report["schema"], "fma-small-metadata-audit-v1")
        data = report["data"]
        self.assertEqual(data["track_count"], 4)
        self.assertEqual(data["genres"], {"Electronic": 2, "Rock": 2})
        self.assertEqual(data["splits"], {
            "test": 2, "training": 1, "validation": 1,
        })
        self.assertEqual(data["artists_in_multiple_splits"]["training_test"], 1)
        self.assertEqual(len(report["metadata_zip_sha256"]), 64)
        self.assertNotIn('"123"', json.dumps(report))

    def test_missing_artist_id_column_rejected(self):
        with zipfile.ZipFile(self.archive, "w") as archive:
            archive.writestr(
                "tracks.csv",
                ",set,set,track\n,subset,split,genre_top\n"
                "123,small,training,Rock\n",
            )
        with self.assertRaisesRegex(ValueError, "Missing FMA"):
            audit.inspect(self.archive)

    def test_duplicate_song_ids_rejected(self):
        self.write_rows([
            ("10", "small", "training", "Rock", "42"),
            ("10", "small", "test", "Rock", "43"),
        ])
        with self.assertRaisesRegex(ValueError, "Duplicate FMA"):
            audit.inspect(self.archive)


if __name__ == "__main__":
    unittest.main()
