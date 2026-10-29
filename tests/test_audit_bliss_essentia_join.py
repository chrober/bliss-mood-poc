"""WP3-R0 synthetic read-only Bliss 23D/Essentia head exact-key join tests."""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_bliss_essentia_join as join
import evaluate_similarity as ev

KEYS = ("Album/A.mp3", "Album/B.mp3", "Album/C.mp3")
AUDIO = "a" * 64
ENCODER = "discogs-effnet.onnx"


def create_feature_database(path: Path, *, mismatched: bool = False):
    with closing(sqlite3.connect(path)) as db:
        db.executescript("""
            PRAGMA user_version=3;
            CREATE TABLE feature_models(
              model_key TEXT PRIMARY KEY, embedding_model TEXT,
              classification_model TEXT, models_sha256_json TEXT,
              preprocessing_version TEXT, aggregation TEXT,
              classes_json TEXT, validated_against_essentia INTEGER
            );
            CREATE TABLE feature_tracks(
              track_file TEXT, model_id TEXT, capability TEXT,
              model_key TEXT, audio_sha256 TEXT, scores_f32_le BLOB,
              patches_analyzed INTEGER, PRIMARY KEY(track_file, model_id)
            );
        """)
        for head, (capability, dims) in ev.MODELS.items():
            classifier = head + ".onnx"
            db.execute(
                "INSERT INTO feature_models VALUES(?,?,?,?,?,?,?,?)",
                (head, ENCODER, classifier,
                 json.dumps({ENCODER: "b"*64, classifier: "c"*64}),
                 "experimental-essentia-cpp-dsp-v1-unvalidated",
                 ev.AGGREGATION, json.dumps([f"label-{j}" for j in range(dims)]), 0),
            )
            for index, key in enumerate(KEYS):
                data = [0.12+0.6*(j%3)/3 for j in range(dims)]
                data[2] = 0.25+0.07*index
                db.execute(
                    "INSERT INTO feature_tracks VALUES(?,?,?,?,?,?,?)",
                    (key, head, capability, head,
                     "d"*64 if mismatched and index == 1 and head == "moodtheme"
                     else AUDIO, struct.pack("<" + "f"*dims, *data), 13),
                )
        db.commit()


def create_bliss_database(path: Path, *, missing: bool = False,
                          duplicate: bool = False, invalid: bool = False,
                          case_mismatch: bool = False):
    fields = ','.join('"' + col + '" REAL' for col in join.BLISS_COLUMNS)
    with closing(sqlite3.connect(path)) as db:
        db.execute(f'CREATE TABLE TracksV2 ("File" TEXT, {fields})')
        for i, key in enumerate(KEYS):
            if missing and i == 1:
                continue
            if case_mismatch and i == 2:
                key = "album/C.mp3"
            feature = [0.25+(i+j)/100 for j in range(23)]
            if invalid and i == 0:
                feature[6] = None
            db.execute(
                f"INSERT INTO TracksV2 VALUES ({','.join(['?']*24)})",
                (key, *feature),
            )
            if duplicate and i == 2:
                db.execute(
                    f"INSERT INTO TracksV2 VALUES ({','.join(['?']*24)})",
                    (key, *feature),
                )
        db.commit()


class ReadOnlyJoinTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.bliss = self.root / "bliss.db"
        self.features = self.root / "essentia.db"
        create_bliss_database(self.bliss)
        create_feature_database(self.features)

    def test_valid_pairing_23_columns_with_complete_provenance(self):
        previous = (self.bliss.read_bytes(), self.features.read_bytes())
        result = join.report(self.bliss, self.features)
        self.assertEqual(result["counts"]["bliss_23d_valid_and_paired"], 3)
        self.assertEqual(result["counts"]["essentia_head_pairs_eligible_total"], 3)
        self.assertEqual(result["embedding_1280d"], "NOT_ASSESSED_SEPARATE_SIDECARS_REQUIRED")
        self.assertEqual(result["bliss_feature_dimensions"], 23)
        self.assertEqual(result["essentia_head_dimensions"], {"genre": 87, "moodtheme": 56})
        self.assertEqual((self.bliss.read_bytes(), self.features.read_bytes()), previous)
        self.assertFalse((self.root/"bliss.db-wal").exists())
        self.assertFalse((self.root/"essentia.db-wal").exists())
        for forbidden in ("Album/", AUDIO, "discogs-effnet", str(self.root)):
            self.assertNotIn(forbidden, json.dumps(result))

    def test_missing_duplicate_nonfinite_and_case_sensitive(self):
        self.bliss.unlink()
        create_bliss_database(self.bliss, missing=True, duplicate=True, invalid=True)
        data = join.report(self.bliss, self.features)["counts"]
        self.assertEqual(data["bliss_invalid_23d"], 1)
        self.assertEqual(data["bliss_exact_key_missing"], 1)
        self.assertEqual(data["bliss_duplicate_exact_key"], 1)
        self.assertEqual(data["bliss_23d_valid_and_paired"], 0)
        self.bliss.unlink()
        create_bliss_database(self.bliss, case_mismatch=True)
        data = join.report(self.bliss, self.features)["counts"]
        self.assertEqual(data["bliss_exact_key_missing"], 1)
        self.assertEqual(data["bliss_23d_valid_and_paired"], 2)

    def test_hash_mismatch_is_not_a_paired_song(self):
        extra = self.root/"mismatch.db"
        create_feature_database(extra, mismatched=True)
        report = join.report(self.bliss, extra)
        self.assertEqual(report["counts"]["essentia_head_provenance_rejected_in_sample"], 1)
        self.assertEqual(report["counts"]["bliss_23d_valid_and_paired"], 2)

    def test_optional_pinned_1280d_sidecars_verified_and_counted(self):
        from evaluate_mtt_embedding_ab import filename_for_key
        sidecars = self.root/"research-embeddings"
        sidecars.mkdir()
        enc_sha = "b"*64
        frontend = "experimental-essentia-cpp-dsp-v1-unvalidated"
        info = {
            "schema_version": 1,
            "kind": "discogs_effnet_song_embedding",
            "validation_status": "experimental_unvalidated",
            "dimension": 1280,
            "patches_analyzed": 13,
            "audio_sha256": AUDIO,
            "encoder_sha256": enc_sha,
            "preprocessing_version": frontend,
            "pooling_version": "patch_f64_arithmetic_mean_v1",
            "normalization_version": "song_f64_l2_then_cast_f32_v1",
            "encoder_model": ENCODER,
            "vector_f32": [1.0] + [0.0]*1279,
        }
        contract = [1, ENCODER, enc_sha, frontend,
                    info["pooling_version"], info["normalization_version"], 1280]
        info["representation_fingerprint"] = hashlib.sha256(
            json.dumps(contract, ensure_ascii=False, separators=(",", ":")).encode()
        ).hexdigest()
        # A is valid, B has tampered source hash, C is missing.
        for key in KEYS[:2]:
            details = dict(info, track_file=key)
            if key == KEYS[1]:
                details["audio_sha256"] = "f"*64
            (sidecars / filename_for_key(key)).write_text(json.dumps(details))
        data = join.report(self.bliss, self.features, embedding_dir=sidecars)
        self.assertEqual(data["counts"]["bliss_23d_valid_and_paired"], 3)
        self.assertEqual(data["counts"]["embedding_valid_and_paired"], 1)
        self.assertEqual(data["counts"]["embedding_invalid_or_incompatible"], 1)
        self.assertEqual(data["counts"]["embedding_missing"], 1)
        self.assertNotIn(KEYS[0], json.dumps(data))
        with self.assertRaisesRegex(ValueError, "embedding directory"):
            join.report(self.bliss, self.features,
                        embedding_dir=self.root/"missing_embeddings")

    def test_rejects_missing_columns_schema_and_missing_db(self):
        self.bliss.unlink()
        with closing(sqlite3.connect(self.bliss)) as db:
            db.execute('CREATE TABLE TracksV2("File" TEXT, "Tempo" REAL)')
            db.commit()
        with self.assertRaisesRegex(ValueError, "23D column"):
            join.report(self.bliss, self.features)
        with self.assertRaisesRegex(ValueError, "Bliss DB is missing"):
            join.open_bliss(self.root/"not_existing.db")
        self.assertFalse((self.root/"not_existing.db").exists())

    def test_bounded_reproducible_and_no_overwrite(self):
        result = join.report(self.bliss, self.features, limit=2, seed=1234)
        self.assertEqual(result, join.report(self.bliss, self.features, limit=2, seed=1234))
        self.assertEqual(result["counts"]["essentia_head_pairs_selected"], 2)
        with self.assertRaises(ValueError):
            join.report(self.bliss, self.features, limit=301)
        out = self.root/"aggregate.json"
        out.write_text("KEEP")
        with patch.object(sys, "argv", [
            "audit_bliss_essentia_join.py",
            "--bliss-db", str(self.bliss), "--feature-db", str(self.features),
            "--out", str(out),
        ]):
            with self.assertRaises(SystemExit) as raised:
                join.main()
        self.assertEqual(raised.exception.code, 2)
        self.assertEqual(out.read_text(), "KEEP")

    def test_writes_only_new_aggregate_report(self):
        report_path = self.root/"only-aggregates.json"
        with patch.object(sys, "argv", [
            "audit_bliss_essentia_join.py",
            "--bliss-db", str(self.bliss), "--feature-db", str(self.features),
            "--out", str(report_path),
        ]):
            self.assertEqual(join.main(), 0)
        stored = json.loads(report_path.read_text())
        self.assertEqual(stored["counts"]["bliss_23d_valid_and_paired"], 3)
        self.assertNotIn(KEYS[0], report_path.read_text())


if __name__ == "__main__":
    unittest.main()
