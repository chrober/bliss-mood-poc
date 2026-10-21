"""Synthetic, fully paired and blinded 100-song local A/B listening instrument tests."""
from __future__ import annotations

from contextlib import closing
import csv
import hashlib
import json
from pathlib import Path
import sqlite3
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import propose_local_embedding_ab_pilot as pilot
import audit_local_feature_readiness as readiness
import evaluate_similarity as ev
from evaluate_mtt_embedding_ab import filename_for_key

PREP = readiness.V5_PREPROCESSING
ENC = "discogs-effnet-bsdynamic-1.onnx"
ENC_SHA = "a" * 64
AUDIO_SHA = "d" * 64


def make_sample(db: Path, embedding_dir: Path):
    embedding_dir.mkdir()
    with closing(sqlite3.connect(db)) as conn:
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
        for head, (cap, dimensions) in ev.MODELS.items():
            classifier = head + ".onnx"
            conn.execute("INSERT INTO feature_models VALUES(?,?,?,?,?,?,?,0)", (
                head + "-key", ENC, classifier,
                json.dumps({ENC: ENC_SHA, classifier: "b"*64}),
                PREP, ev.AGGREGATION,
                json.dumps([f"{head} label {i}" for i in range(dimensions)]),
            ))
        for n in range(100):
            key = f"Artist-{n//3:03d}/Album {n//2:03d}/Song {n:03d}.flac"
            for head, (cap, dimensions) in ev.MODELS.items():
                values = [
                    min(.99, .01 + (((i + 1) * (n % 31 + 3) + n * 13) % 92)/100)
                    for i in range(dimensions)
                ]
                conn.execute("INSERT INTO feature_tracks VALUES(?,?,?,?,?,?,?)", (
                    key, head, cap, head + "-key", AUDIO_SHA,
                    struct.pack("<" + "f"*dimensions, *values), 11,
                ))
            # Two non-zero sparse encoder coordinates, exact unit norm.
            vec = [0.] * 1280
            vec[(n*7+1) % 1280] = .6
            vec[(n*7+2) % 1280] = .8
            payload = {
                "schema_version": 1, "kind": "discogs_effnet_song_embedding",
                "validation_status": "experimental_unvalidated",
                "dimension": 1280, "patches_analyzed": 11,
                "encoder_model": ENC, "encoder_sha256": ENC_SHA,
                "preprocessing_version": PREP,
                "pooling_version": "patch_f64_arithmetic_mean_v1",
                "normalization_version": "song_f64_l2_then_cast_f32_v1",
                "audio_sha256": AUDIO_SHA, "track_file": key,
                "vector_f32": vec,
            }
            contract = [
                1, ENC, ENC_SHA, PREP, payload["pooling_version"],
                payload["normalization_version"], 1280,
            ]
            payload["representation_fingerprint"] = hashlib.sha256(json.dumps(
                contract, ensure_ascii=False, separators=(",", ":")
            ).encode()).hexdigest()
            (embedding_dir / filename_for_key(key)).write_text(
                json.dumps(payload), encoding="utf-8"
            )
        conn.commit()


def csv_rows(p: Path) -> list[dict]:
    with p.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


class LocalEmbeddingABPilotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = self.root / "song-features.db"
        self.embeddings = self.root / "embeddings"
        make_sample(self.db, self.embeddings)

    def test_12_pairs_blinded_distinct_deterministic_and_db_read_only(self):
        old_db = self.db.read_bytes()
        out = self.root / "pilot"
        summary = pilot.create_pilot(self.db, self.embeddings, out)
        self.assertEqual(summary["status"], "BLINDED_REVIEW_READY")
        self.assertEqual(summary["pilot_pairs"], 12)
        self.assertEqual(summary["unique_songs_in_pilot"], 24)
        self.assertTrue(summary["all_human_rating_cells_blank"])
        self.assertEqual(self.db.read_bytes(), old_db)
        self.assertEqual(sorted(p.name for p in out.iterdir()),
                         ["listening-pairs.csv", "selection-audit-private.json"])
        rows = csv_rows(out / "listening-pairs.csv")
        self.assertEqual(len(rows), 12)
        self.assertEqual(list(rows[0]), list(pilot.CSV_FIELDS))
        self.assertTrue(all(not v for row in rows for k, v in row.items()
                            if k not in ("left", "right")))
        self.assertEqual(len({key for row in rows for key in (row["left"], row["right"])}), 24)
        self.assertEqual(len({frozenset((row["left"], row["right"])) for row in rows}), 12)
        private = json.loads((out / "selection-audit-private.json").read_text())
        self.assertEqual(private["sampling_quotas"], pilot.QUOTAS)
        self.assertEqual(len(private["pairs_private_do_not_open_before_review"]), 12)
        self.assertTrue(private["source_provenance"]["embedding_fingerprint_consistent"])
        self.assertTrue(private["source_provenance"]["same_audio_and_encoder_provenance"])
        self.assertNotIn("Artist-", json.dumps(summary))
        same = self.root / "same"
        pilot.create_pilot(self.db, self.embeddings, same)
        self.assertEqual((out / "listening-pairs.csv").read_bytes(),
                         (same / "listening-pairs.csv").read_bytes())
        self.assertEqual((out / "selection-audit-private.json").read_bytes(),
                         (same / "selection-audit-private.json").read_bytes())

    def test_old_pairs_excluded_including_reverse_and_semicolon_csv(self):
        raw = self.root / "initial"
        pilot.create_pilot(self.db, self.embeddings, raw)
        prior = csv_rows(raw / "listening-pairs.csv")
        source = self.root / "previous.csv"
        with source.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["left", "right", "genre_label"], delimiter=";")
            w.writeheader()
            for row in prior[:8]:
                w.writerow({"left": row["right"], "right": row["left"], "genre_label": 1})
        dst = self.root / "new"
        result = pilot.create_pilot(self.db, self.embeddings, dst, source)
        self.assertEqual(result["earlier_review_pairs_excluded"], 8)
        prior_pairs = {frozenset((x["left"], x["right"])) for x in prior[:8]}
        self.assertTrue(all(frozenset((r["left"], r["right"])) not in prior_pairs
                            for r in csv_rows(dst / "listening-pairs.csv")))

    def test_corrupt_or_missing_embedding_fails_before_writing(self):
        files = list(self.embeddings.glob("*.json"))
        victim = files[0]
        original = victim.read_text()
        for change in ("audio_hash", "dimension", "fingerprint"):
            with self.subTest(change=change):
                obj = json.loads(original)
                if change == "audio_hash":
                    obj["audio_sha256"] = "f"*64
                elif change == "dimension":
                    obj["vector_f32"].pop()
                else:
                    obj["representation_fingerprint"] = "f"*64
                victim.write_text(json.dumps(obj))
                target = self.root / ("invalid-"+change)
                with self.assertRaises(ValueError):
                    pilot.create_pilot(self.db, self.embeddings, target)
                self.assertFalse(target.exists())
        victim.unlink()
        missing_out = self.root / "missing"
        with self.assertRaises(ValueError):
            pilot.create_pilot(self.db, self.embeddings, missing_out)
        self.assertFalse(missing_out.exists())

    def test_no_overwrite_existing_user_review_csv(self):
        out = self.root / "human_reviews"
        out.mkdir()
        rated = out / "listening-pairs.csv"
        rated.write_text("PRIVATE HUMAN REVIEW", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            pilot.create_pilot(self.db, self.embeddings, out)
        self.assertEqual(rated.read_text(), "PRIVATE HUMAN REVIEW")

    def test_rejects_unknown_head_cohort_or_broken_schema(self):
        with closing(sqlite3.connect(self.db)) as conn:
            conn.execute(
                "UPDATE feature_models SET preprocessing_version='wrong' WHERE model_key='genre-key'"
            )
            conn.commit()
        out = self.root / "wrong"
        with self.assertRaisesRegex(ValueError, "Rust-v5"):
            pilot.create_pilot(self.db, self.embeddings, out)
        self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
