"""Synthetic local phase-2 L0 feature readiness gates; never access user audio."""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
import pathlib
import sqlite3
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import audit_local_feature_readiness as audit
from evaluate_mtt_embedding_ab import filename_for_key

ENCODER = "discogs-effnet-bsdynamic-1.onnx"
ENCODER_SHA = "a" * 64
AUDIO_SHA = "d" * 64
PREP = audit.V5_PREPROCESSING


def create_db(path, *, wrong_audio=False, wrong_prep=False, low_variance=False):
    with closing(sqlite3.connect(path)) as conn:
        conn.executescript("""
            PRAGMA user_version=3;
            CREATE TABLE feature_models(
                model_key TEXT PRIMARY KEY,
                embedding_model TEXT NOT NULL,
                classification_model TEXT NOT NULL,
                models_sha256_json TEXT NOT NULL,
                preprocessing_version TEXT NOT NULL,
                aggregation TEXT NOT NULL,
                classes_json TEXT NOT NULL,
                validated_against_essentia INTEGER NOT NULL
            );
            CREATE TABLE feature_tracks(
                track_file TEXT NOT NULL, model_id TEXT NOT NULL,
                capability TEXT NOT NULL, model_key TEXT NOT NULL,
                audio_sha256 TEXT NOT NULL,
                scores_f32_le BLOB NOT NULL,
                patches_analyzed INTEGER NOT NULL,
                PRIMARY KEY(track_file, model_id)
            );
        """)
        for model, (cap, dims) in audit.ev.MODELS.items():
            classifier = model + ".onnx"
            conn.execute(
                "INSERT INTO feature_models VALUES(?,?,?,?,?,?,?,0)",
                (model + "-key", ENCODER, classifier,
                 json.dumps({ENCODER: ENCODER_SHA, classifier: "b"*64}),
                 "wrong-frontend" if wrong_prep else PREP,
                 audit.ev.AGGREGATION,
                 json.dumps([model + "-" + str(i) for i in range(dims)])),
            )
            for idx, key in enumerate(("Album/A.mp3", "Album/B.mp3", "Album/C.mp3")):
                vec = [0.1 + 0.7 * (j % 2) for j in range(dims)]
                if low_variance and idx == 2:
                    vec = [0.1] * dims
                else:
                    vec[1] = 0.5 + idx * 0.1
                conn.execute(
                    "INSERT INTO feature_tracks VALUES(?,?,?,?,?,?,?)",
                    (key, model, cap, model + "-key",
                     "e"*64 if wrong_audio and idx == 1 and model == "moodtheme" else AUDIO_SHA,
                     struct.pack("<" + "f"*dims, *vec), 11),
                )
        conn.commit()


def sidecar(key, *, tamper=False):
    fields = {
        "schema_version": 1,
        "kind": "discogs_effnet_song_embedding",
        "validation_status": "experimental_unvalidated",
        "dimension": 1280,
        "patches_analyzed": 11,
        "audio_sha256": "f"*64 if tamper else AUDIO_SHA,
        "encoder_sha256": ENCODER_SHA,
        "preprocessing_version": PREP,
        "pooling_version": "patch_f64_arithmetic_mean_v1",
        "normalization_version": "song_f64_l2_then_cast_f32_v1",
        "track_file": key,
        "encoder_model": ENCODER,
        "vector_f32": [1.] + [0.]*1279,
    }
    fields["representation_fingerprint"] = hashlib.sha256(
        json.dumps([
            1, ENCODER, ENCODER_SHA, PREP,
            fields["pooling_version"], fields["normalization_version"], 1280,
        ], ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()
    return fields


class ReadOnlyLocalFeatureAuditTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = pathlib.Path(temp.name)
        self.db = self.root / "user.db"
        self.embed = self.root / "sidecars"
        create_db(self.db)

    def test_without_embedding_dir_does_not_count_missing(self):
        before = self.db.read_bytes()
        data = audit.report(self.db, None, limit=100, seed=20261021)
        self.assertEqual(data["sampling"]["compatible_87d_56d_total_before_sample"], 3)
        self.assertEqual(data["counts"]["compatible_head_pairs"], 3)
        self.assertEqual(data["counts"]["embedding_status"], "not_assessed_no_directory")
        self.assertIsNone(data["counts"]["embedding_missing"])
        self.assertIsNone(data["counts"]["embedding_valid"])
        self.assertEqual(before, self.db.read_bytes())
        report_json = json.dumps(data)
        for private in ("Album/", str(self.root), AUDIO_SHA, ENCODER_SHA):
            self.assertNotIn(private, report_json)

    def test_embedding_mixed_valid_missing_incompatible(self):
        self.embed.mkdir()
        key_valid = "Album/A.mp3"
        key_invalid = "Album/B.mp3"
        (self.embed/filename_for_key(key_valid)).write_text(json.dumps(sidecar(key_valid)))
        (self.embed/filename_for_key(key_invalid)).write_text(json.dumps(sidecar(key_invalid, tamper=True)))
        before = self.db.read_bytes()
        result = audit.report(self.db, self.embed, limit=100, seed=20261021)
        counts = result["counts"]
        self.assertEqual(counts["compatible_head_pairs"], 3)
        self.assertEqual(counts["embedding_valid"], 1)
        self.assertEqual(counts["embedding_missing"], 1)
        self.assertEqual(counts["embedding_invalid_or_incompatible"], 1)
        self.assertEqual(before, self.db.read_bytes())
        self.assertNotIn("Album/A.mp3", json.dumps(result))

    def test_flags_mixed_audio_sha_without_exposing_track_identity(self):
        create_db(self.root/"mixed.db", wrong_audio=True)
        result = audit.report(self.root/"mixed.db", None, limit=100, seed=20261021)
        self.assertEqual(result["counts"]["compatible_head_pairs"], 2)
        self.assertEqual(result["counts"]["head_provenance_mismatches"], 1)

    def test_rejects_wrong_frontend_and_schema_without_writes(self):
        create_db(self.root/"old.db", wrong_prep=True)
        with self.assertRaisesRegex(ValueError, "Rust v5"):
            audit.report(self.root/"old.db", None, limit=100, seed=20261021)
        with closing(sqlite3.connect(self.root/"invalid.db")) as conn:
            conn.execute("PRAGMA user_version=2")
            conn.commit()
        before = (self.root/"invalid.db").read_bytes()
        with self.assertRaisesRegex(ValueError, "schema v3"):
            audit.report(self.root/"invalid.db", None, limit=100, seed=20261021)
        self.assertEqual(before, (self.root/"invalid.db").read_bytes())

    def test_invalid_constant_head_excluded_and_sample_bounded(self):
        create_db(self.root/"constant.db", low_variance=True)
        result = audit.report(self.root/"constant.db", None, limit=2, seed=20261021)
        self.assertEqual(result["counts"]["sampled_paired_head_vectors"], 2)
        self.assertEqual(result["sampling"]["invalid_joined_head_vectors_excluded"], 1)
        with self.assertRaisesRegex(ValueError, "1..300"):
            audit.report(self.db, None, limit=0, seed=20261021)

    def test_cli_does_not_overwrite_existing_report(self):
        from unittest.mock import patch
        out = self.root / "report.json"
        out.write_text("DO_NOT_OVERWRITE")
        with patch.object(sys, "argv", [
            "audit_local_feature_readiness.py", "--db", str(self.db),
            "--out", str(out),
        ]):
            with self.assertRaises(SystemExit) as caught:
                audit.main()
        self.assertEqual(caught.exception.code, 2)
        self.assertEqual(out.read_text(), "DO_NOT_OVERWRITE")


if __name__ == "__main__":
    unittest.main()
