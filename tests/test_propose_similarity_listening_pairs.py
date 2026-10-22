"""Small, self-contained deterministic read-only listening selection fixtures."""
import csv
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import evaluate_similarity as ev
import propose_similarity_listening_pairs as proposal


def make_db(db, prep=proposal.V5_PREPROCESSING):
    with closing(sqlite3.connect(db)) as conn:
        conn.executescript("""
            PRAGMA user_version=3;
            CREATE TABLE feature_models(
                model_key TEXT PRIMARY KEY,
                preprocessing_version TEXT NOT NULL,
                aggregation TEXT NOT NULL,
                classes_json TEXT NOT NULL,
                validated_against_essentia INTEGER NOT NULL
            );
            CREATE TABLE feature_tracks(
                track_file TEXT NOT NULL, model_id TEXT NOT NULL,
                capability TEXT NOT NULL, model_key TEXT NOT NULL,
                scores_f32_le BLOB NOT NULL,
                PRIMARY KEY(track_file, model_id)
            );
        """)
        for head, (capability, dimensions) in ev.MODELS.items():
            conn.execute(
                "INSERT INTO feature_models VALUES (?, ?, ?, ?, 0)",
                (head + "-fingerprint", prep, ev.AGGREGATION,
                 json.dumps([f"label-{i}" for i in range(dimensions)]))
            )
            for n in range(14):
                # Deliberately heterogeneous non-degenerate vectors, including
                # low-activation Mood and very different score distributions.
                vec = []
                for i in range(dimensions):
                    if head == "moodtheme" and n % 4 == 0:
                        val = 0.002 + ((i * (n + 3) + n * 7) % 80) / 1000
                    else:
                        val = 0.01 + ((i * (n * 3 + 11) + n * 29) % 88) / 100
                    vec.append(min(val, 1.0))
                # Pair names with commas test RFC4180 CSV escaping.
                name = f"Artist-{n // 2}/Album,{n}/Track {n}.flac"
                conn.execute(
                    "INSERT INTO feature_tracks VALUES(?,?,?,?,?)",
                    (name, head, capability, head + "-fingerprint",
                     struct.pack("<" + "f" * dimensions, *vec))
                )
        conn.commit()


def read_pairs(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


class PairProposalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / "rust-v5-sidecar.db"
        make_db(self.db)

    def test_outputs_unlabeled_csv_and_sealed_audit_without_touching_db(self):
        before = self.db.read_bytes()
        dst = self.root / "pilot"
        response = proposal.create_review_files(
            self.db, dst, 14, 12, 20261021, 70, True
        )
        self.assertEqual(response["status"], "READY_FOR_HUMAN_LISTENING")
        self.assertEqual(response["genre_labels_filled"], 0)
        self.assertEqual(response["mood_labels_filled"], 0)
        self.assertNotIn("Track 1", str(response))
        self.assertEqual(self.db.read_bytes(), before)
        pairs = read_pairs(dst / "listening-pairs.csv")
        self.assertEqual(len(pairs), 12)
        self.assertEqual(len({tuple(sorted((p["left"], p["right"])))
                              for p in pairs}), 12)
        self.assertEqual(list(pairs[0]), ["left", "right", "genre_label", "mood_label"])
        for p in pairs:
            self.assertNotEqual(p["left"], p["right"])
            self.assertEqual(p["genre_label"], "")
            self.assertEqual(p["mood_label"], "")
            self.assertIn("Album,", p["left"])
            self.assertIn("Album,", p["right"])
        audit = json.loads((dst / "selection-audit-private.json").read_text("utf-8"))
        self.assertEqual(audit["selected_pairs"], 12)
        self.assertEqual(len(audit["pair_selection_audit"]), 12)
        self.assertEqual(sum(audit["stratum_counts"].values()), 12)
        self.assertTrue(audit["source"]["input_read_only"])
        self.assertEqual(audit["source"]["models"]["genre"][
            "preprocessing_version"
        ], proposal.V5_PREPROCESSING)
        with self.assertRaisesRegex(ValueError, "at least one head label"):
            ev.load_labels(dst / "listening-pairs.csv")
        # The reviewer later adds genuine independent labels. No automatic
        # model-score-derived labels are ever provided by this tool.
        for item in pairs:
            item["genre_label"] = "1"
            item["mood_label"] = "0"
        with (dst / "listening-pairs.csv").open(
            "w", encoding="utf-8-sig", newline=""
        ) as handle:
            wr = csv.DictWriter(handle, fieldnames=list(pairs[0]))
            wr.writeheader()
            wr.writerows(pairs)
        self.assertEqual(len(ev.load_labels(dst / "listening-pairs.csv")), 12)

    def test_repeatable_seed_is_bit_for_bit_stable(self):
        a = self.root / "a"
        b = self.root / "b"
        proposal.create_review_files(self.db, a, 12, 11, 123, 30, True)
        proposal.create_review_files(self.db, b, 12, 11, 123, 30, True)
        self.assertEqual((a / "listening-pairs.csv").read_bytes(),
                         (b / "listening-pairs.csv").read_bytes())
        self.assertEqual((a / "selection-audit-private.json").read_bytes(),
                         (b / "selection-audit-private.json").read_bytes())

    def test_rejects_old_preprocessing_when_v5_identity_required(self):
        old = self.root / "old.db"
        make_db(old, prep="experimental-essentia-audio-v4-unvalidated")
        dst = self.root / "reject"
        with self.assertRaisesRegex(ValueError, "corrected Rust v5 preprocessing"):
            proposal.create_review_files(old, dst, 14, 8, 3, 30, True)
        self.assertFalse(dst.exists())

    def test_rejects_existing_review_folder_and_preserves_user_edits(self):
        dst = self.root / "reviews"
        dst.mkdir()
        valuable = dst / "listening-pairs.csv"
        valuable.write_text("user listening judgments", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            proposal.create_review_files(self.db, dst, 14, 8, 3, 30, True)
        self.assertEqual(valuable.read_text("utf-8"), "user listening judgments")

    def test_strict_small_bounded_listening_set_and_pool(self):
        with closing(ev.open_database(self.db)) as conn:
            heads = {h: ev._catalog(conn, h, True) for h in ev.MODELS}
            sample = ev.load_sample(conn, heads, 14, 8)
        for count, pool in ((101, 110), (5, 50), (20, 10), (6, 25000)):
            with self.subTest(count=count, pool=pool), self.assertRaises(ValueError):
                proposal.select_review_pairs(sample, count, 3, pool)
        tiny = {"tracks": {k: v for k, v in list(sample["tracks"].items())[:5]}}
        with self.assertRaisesRegex(ValueError, "6..300"):
            proposal.select_review_pairs(tiny, 6, 5)

    def test_defined_low_mood_vectors_do_not_require_absolute_threshold(self):
        with closing(ev.open_database(self.db)) as conn:
            heads = {h: ev._catalog(conn, h, True) for h in ev.MODELS}
            sample = ev.load_sample(conn, heads, 14, 8)
        prompts, audit = proposal.select_review_pairs(sample, 16, 19, 80)
        self.assertEqual(len(prompts), 16)
        self.assertEqual(len(audit["stratum_counts"].keys() - set(proposal.STRATA)), 0)
        self.assertLessEqual(max(
            sum(p["left"] == k or p["right"] == k for p in prompts)
            for k in sample["tracks"]), 16)
        self.assertEqual(sum(audit["stratum_counts"].values()), 16)

    def test_schema_v3_and_existing_file_are_required_before_creation(self):
        dst = self.root / "never-create"
        with self.assertRaises(FileNotFoundError):
            proposal.create_review_files(
                self.root / "missing.db", dst, 14, 10, 1, 20, False
            )
        self.assertFalse(dst.exists())
        with closing(sqlite3.connect(self.db)) as conn:
            conn.execute("PRAGMA user_version=2")
        with self.assertRaisesRegex(ValueError, "schema v3"):
            proposal.create_review_files(self.db, dst, 14, 10, 1, 20, False)
        self.assertFalse(dst.exists())


if __name__ == "__main__":
    unittest.main()
