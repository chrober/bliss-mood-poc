"""Regression tests for local-only bounded native adaptive scanner benchmark."""
from __future__ import annotations

import argparse
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import benchmark_native_adaptive_manifest as bench


class NativeAdaptiveManifestTests(unittest.TestCase):
    def test_relative_bliss_keys_are_manifest_compatible(self):
        keys = ["Artist/Album/a.mp3", "Other\\Album\\b.flac"]
        self.assertEqual(bench.prepare_manifest_keys(keys, None), [
            "Artist/Album/a.mp3", "Other/Album/b.flac",
        ])

    def test_library_root_remapping_is_explicit(self):
        keys = ["/mnt/music/Artist/Album/a.mp3"]
        self.assertEqual(bench.prepare_manifest_keys(keys, "/mnt/music"),
                         ["Artist/Album/a.mp3"])
        self.assertEqual(
            bench.prepare_manifest_keys(
                ["D:\\Music\\Artist\\track.mp3"], "D:\\Music"
            ), ["Artist/track.mp3"])
        with self.assertRaises(ValueError):
            bench.prepare_manifest_keys(["/another/music/a.mp3"], "/mnt/music")

    def test_rejects_unsafe_or_ambiguous_paths(self):
        bad = [
            "", "/absolute.wav", "C:\\music\\song.mp3", "a//b.mp3",
            "a/../b.mp3", "a/./b.mp3", "a\\..\\b.mp3", " song.mp3",
            "song.mp3 ", "a\nb.mp3", "a\r.mp3", "a\x00b.mp3",
        ]
        for key in bad:
            with self.subTest(key=repr(key)), self.assertRaises(ValueError):
                bench.normalize_manifest_key(key, None)
        with self.assertRaises(ValueError):
            bench.prepare_manifest_keys(["a/b.mp3", "a\\b.mp3"], None)

    def test_two_repeats_reverse_execution_order(self):
        first = bench.schedule(2, 20261022)
        self.assertEqual(len(first), 10)
        self.assertEqual(first[:5], [
            (1, mode) for mode in reversed([p[1] for p in first[5:]])
        ])
        self.assertEqual(set(name for _, name in first), {
            "fixed1", "fixed2", "fixed4", "fixed6", "adaptive2",
        })

    def test_preflight_rejects_missing_music_and_symlink_escapes(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "music"
            root.mkdir()
            (root / "one.mp3").write_bytes(b"stub")
            bench.verify_music_paths(["one.mp3"], root)
            with self.assertRaisesRegex(ValueError, "unavailable"):
                bench.verify_music_paths(["missing.mp3"], root)
            outside = base / "other.mp3"
            outside.write_bytes(b"stub")
            link = root / "escape.mp3"
            try:
                link.symlink_to(outside)
            except (OSError, NotImplementedError):
                return  # Symlink privileges are optional on Windows.
            with self.assertRaisesRegex(ValueError, "outside"):
                bench.verify_music_paths(["escape.mp3"], root)

    def test_scan_command_uses_manifest_and_not_bliss_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            options = argparse.Namespace(
                analyzer=root / "bliss-mood", essentia_worker=root / "native-worker",
                source_root=root / "music", manifest_file=root / "tracks.txt",
                models_dir=root / "models", models="moodtheme,genre,voice",
                timeout_seconds=900, output_dir=root / "results",
            )
            options.output_dir.mkdir()
            class Capture(Exception):
                pass
            with patch.object(bench.subprocess, "run", side_effect=Capture) as run:
                with self.assertRaises(Capture):
                    bench.analyze(options, 1, "adaptive2", 100)
                arguments = run.call_args.args[0]
            self.assertIn("--tracks-file", arguments)
            self.assertIn("--source-root", arguments)
            self.assertIn("--embedding-dir", arguments)
            self.assertNotIn("--bliss-db", arguments)
            self.assertNotIn("--library-root", arguments)
            self.assertIn("--adaptive-workers", arguments)
            self.assertEqual(arguments[arguments.index("--max-new") + 1], "100")

    def test_plan_only_on_exact_local_30_track_sqlite_cohort(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            audio = base / "music"
            audio.mkdir()
            models = base / "models"
            models.mkdir()
            cohort = base / "sample-30.db"
            conn = sqlite3.connect(cohort)
            conn.execute("CREATE TABLE TracksV2 (File TEXT, Ignore INTEGER)")
            for i in range(30):
                key = f"artist_{i:02d}/song.flac"
                folder = audio / f"artist_{i:02d}"
                folder.mkdir()
                (folder / "song.flac").write_bytes(b"placeholder")
                conn.execute("INSERT INTO TracksV2 VALUES (?, ?)", (key, 0))
            conn.commit()
            conn.close()
            exe = base / "bliss-mood.exe"
            native = base / "bliss-essentia-worker.exe"
            exe.write_bytes(b"stub")
            native.write_bytes(b"stub")
            out = base / "output"
            argv = [
                "--cohort-db", str(cohort), "--analyzer", str(exe),
                "--essentia-worker", str(native),
                "--models-dir", str(models), "--source-root", str(audio),
                "--output-dir", str(out), "--plan-only",
            ]
            with patch.object(sys, "argv", ["benchmark_native_adaptive_manifest.py", *argv]):
                bench.main()
            self.assertFalse(out.exists(), "plan-only must not write files")


if __name__ == "__main__":
    unittest.main()
