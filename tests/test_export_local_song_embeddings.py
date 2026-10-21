"""Synthetic bounded Windows-compatible local 1280D research export tests."""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import export_local_song_embeddings as exp
from evaluate_mtt_embedding_ab import filename_for_key
from test_audit_local_feature_readiness import create_db, sidecar


class LocalResearchExportTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.db = self.root / "features.db"
        create_db(self.db)
        self.audio = self.root / "music"
        (self.audio / "Album").mkdir(parents=True)
        self.models = self.root / "models"
        self.models.mkdir()
        self.out = self.root / "benchmark-new-embeddings"
        self.binarydir = self.root / "artifact"
        self.binarydir.mkdir()
        self.binary = self.binarydir / "bliss-mood.exe"
        self.binary.write_bytes(b"TEST ONLY RESEARCH EXE")
        (self.binarydir / "SHA256SUMS.txt").write_text(
            f"{exp.file_sha256(self.binary)} *bliss-mood.exe\n"
        )
        (self.binarydir / "BUILD.txt").write_text(
            f"Experimental research only\nPinned Rust-v5 commit: {exp.PINNED_SOURCE}\n"
            "Research overlay commit: 1234567890abcdef\n"
        )
        encoder = "discogs-effnet-bsdynamic-1.onnx"
        genre = "genre.onnx"
        mood = "moodtheme.onnx"
        digests = {}
        for name in (encoder, genre, mood):
            p = self.models / name
            p.write_bytes(name.encode())
            digests[name] = exp.file_sha256(p)
        for name in (genre, mood):
            (self.models / (Path(name).stem + ".json")).write_text("{}")
        self.encoder_sha = digests[encoder]
        self.key_audio_sha = {}
        with closing(sqlite3.connect(self.db)) as conn:
            for model, classifier in (("genre", genre), ("moodtheme", mood)):
                conn.execute(
                    "UPDATE feature_models SET embedding_model=?,classification_model=?,"
                    "models_sha256_json=? WHERE model_key=?",
                    (encoder, classifier,
                     json.dumps({encoder: digests[encoder], classifier: digests[classifier]}),
                     model+"-key"),
                )
            for k in ("Album/A.mp3", "Album/B.mp3", "Album/C.mp3"):
                path = self.audio.joinpath(*k.split("/"))
                path.write_bytes(k.encode("utf-8") + b" audio bytes")
                self.key_audio_sha[k] = exp.file_sha256(path)
                conn.execute(
                    "UPDATE feature_tracks SET audio_sha256=? WHERE track_file=?",
                    (self.key_audio_sha[k], k),
                )
            conn.commit()

    def _call(self, *, execute=False, resume=False, limit=2):
        with patch.object(exp.shutil, "which", return_value="fake-executable"):
            return exp.export(
                self.db, self.audio, self.models, self.binary, self.out,
                limit=limit, seed=20261021, execute=execute, resume=resume
            )

    def _fake_run(self, args, **kwargs):
        key = args[args.index("--track-key")+1]
        target = Path(args[args.index("--embedding-out")+1])
        self.assertFalse(target.exists(), "Existing files cannot be overwritten")
        payload = sidecar(key)
        payload["audio_sha256"] = self.key_audio_sha[key]
        payload["encoder_sha256"] = self.encoder_sha
        payload["representation_fingerprint"] = hashlib.sha256(
            json.dumps([
                1, payload["encoder_model"], self.encoder_sha, exp.readiness.V5_PREPROCESSING,
                payload["pooling_version"], payload["normalization_version"], 1280,
            ], separators=(",", ":")).encode("utf-8"),
        ).hexdigest()
        target.write_text(json.dumps(payload), encoding="utf-8")
        return SimpleNamespace(returncode=0)

    def test_preflight_dry_run_validates_all_source_and_model_sha_without_writes(self):
        before = self.db.read_bytes()
        result = self._call()
        self.assertEqual(result["status"], "dry_run_verified_no_changes")
        self.assertEqual(result["sample_count"], 2)
        self.assertEqual(result["audio_sha_verified"], 2)
        self.assertFalse(self.out.exists())
        self.assertEqual(before, self.db.read_bytes())
        for sensitive in ("Album/A.mp3", "Album/B.mp3", str(self.audio)):
            self.assertNotIn(sensitive, json.dumps(result))

    def test_one_changed_audio_fails_before_creating_output_folder(self):
        (self.audio / "Album" / "B.mp3").write_bytes(b"CHANGED")
        with self.assertRaisesRegex(ValueError, "changed"):
            self._call(limit=3, execute=True)
        self.assertFalse(self.out.exists())

    def test_wrong_model_hash_or_wrong_binary_is_rejected(self):
        (self.models / "genre.onnx").write_bytes(b"CHANGED")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self._call()
        self.assertFalse(self.out.exists())
        (self.binarydir / "BUILD.txt").write_text("Other non-research executable")
        with self.assertRaisesRegex(ValueError, "Wrong research executable"):
            self._call()

    def test_rejects_unsafe_paths_and_outside_music_exports(self):
        for key in ("../Album/A.mp3", "Album/../A.mp3", r"C:\Windows\secret.mp3",
                    "//private/a.mp3", "Album//A.mp3"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                exp.source_file(self.audio.resolve(), key)
        with patch.object(exp.shutil, "which", return_value="fake-executable"):
            with self.assertRaisesRegex(ValueError, "outside the music library"):
                exp.export(self.db, self.audio, self.models, self.binary,
                           self.audio / "exports", limit=2, seed=20261021, execute=True)

    def test_complete_execute_and_resume_preserve_original_db_and_existing_embeddings(self):
        before = self.db.read_bytes()
        with patch.object(exp.subprocess, "run", side_effect=self._fake_run) as proc:
            result = self._call(execute=True, limit=2)
            self.assertEqual(proc.call_count, 2)
        self.assertEqual(result["status"], "complete_verified")
        self.assertEqual(result["exported_and_verified"], 2)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(before, self.db.read_bytes())
        with patch.object(exp.subprocess, "run") as proc:
            resumed = self._call(execute=True, resume=True, limit=2)
            self.assertEqual(proc.call_count, 0)
        self.assertEqual(resumed["existing_valid"], 2)
        self.assertEqual(resumed["exported_and_verified"], 0)
        self.assertEqual(before, self.db.read_bytes())

    def test_existing_directory_never_overwritten_and_tamper_is_not_replaced(self):
        self.out.mkdir()
        with self.assertRaises(FileExistsError):
            self._call(execute=True)
        file = self.out / filename_for_key("Album/A.mp3")
        file.write_text('{"invalid": true}')
        with patch.object(exp.subprocess, "run", side_effect=self._fake_run):
            result = self._call(execute=True, resume=True, limit=3)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["status"], "incomplete_do_not_use_for_scoring")
        self.assertEqual(file.read_text(), '{"invalid": true}')

    def test_low_bound_and_resume_without_execute_rejected(self):
        with self.assertRaisesRegex(ValueError, "100 songs"):
            self._call(limit=101)
        with self.assertRaisesRegex(ValueError, "requires --execute"):
            self._call(resume=True)


if __name__ == "__main__":
    unittest.main()
