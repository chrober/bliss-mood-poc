"""Synthetic 100-track native similarity bridge tests; no user songs, network or ONNX."""
from __future__ import annotations
import hashlib
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
import native_similarity_cohort_bridge as bridge

FRONTEND = "experimental-essentia-cpp-dsp-v3-test-only"
WORKER = "essentia_cpp_worker_binary_sha256"


def build_fixture(root: Path):
    old_db, native_db = root / "old.db", root / "native.db"
    old_dir, native_dir = root / "oldemb", root / "newemb"
    model_dir, audio = root / "models", root / "music"
    for p in (old_dir, native_dir, model_dir, audio):
        p.mkdir()
    models = {name for pair in bridge.EXPECTED_MODELS.values() for name in pair}
    models.add(bridge.ENCODER)
    for name in models:
        p = model_dir / name
        if name.endswith(".json"):
            head = next(h for h, pair in bridge.EXPECTED_MODELS.items() if pair[1] == name)
            p.write_text(json.dumps({"classes": [f"{head} class {i}" for i in range(bridge.DIMENSIONS[head])]}))
        else:
            p.write_bytes(("synthetic fake ONNX " + name).encode())
    hashes = {name: bridge.digest(model_dir / name) for name in models}
    (root / "scanner.exe").write_bytes(b"synthetic scanner not a real executable")
    (root / "worker.exe").write_bytes(b"synthetic native worker not a real executable")
    worker_hash = bridge.digest(root / "worker.exe")

    def mkdb(path: Path):
        conn = sqlite3.connect(path)
        conn.executescript("""
            PRAGMA user_version=3;
            CREATE TABLE feature_models(
              model_key TEXT PRIMARY KEY, preprocessing_version TEXT,
              embedding_model TEXT, classification_model TEXT,
              models_sha256_json TEXT, classes_json TEXT, aggregation TEXT);
            CREATE TABLE feature_tracks(
              track_file TEXT, model_id TEXT, audio_sha256 TEXT,
              patches_analyzed INTEGER, scores_f32_le BLOB, model_key TEXT);
        """)
        return conn

    a, b = mkdb(old_db), mkdb(native_db)
    try:
        for head, (classifier, metadata) in bridge.EXPECTED_MODELS.items():
            labels = json.loads((model_dir / metadata).read_text())["classes"]
            for native, conn in ((False, a), (True, b)):
                if not native and head == "voice":
                    continue
                head_hashes = {
                    bridge.ENCODER: hashes[bridge.ENCODER],
                    classifier: hashes[classifier],
                }
                if native:
                    head_hashes[WORKER] = worker_hash
                conn.execute("INSERT INTO feature_models VALUES(?,?,?,?,?,?,?)", (
                    f"{head}-{'native' if native else 'old'}",
                    FRONTEND if native else bridge.OLD_FRONTEND,
                    bridge.ENCODER, classifier,
                    json.dumps(head_hashes), json.dumps(labels),
                    ("arithmetic_mean_of_per_patch_softmax_scores" if head == "voice"
                     else "arithmetic_mean_of_per_patch_sigmoid_scores"),
                ))
        for n in range(100):
            key = f"Artist-{n:03d}/Album {n//3:03d}/Titel {n:03d}.flac"
            file = audio.joinpath(*key.split("/"))
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(f"synthetic copyright-free audio placeholder {n}".encode())
            sha = bridge.digest(file)
            for head, d in bridge.DIMENSIONS.items():
                values = ([0.4, 0.6] if head == "voice"
                          else [0.01 + ((n*7+i*13) % 95)/100 for i in range(d)])
                blob = struct.pack("<" + "f"*d, *values)
                for native, conn in ((False, a), (True, b)):
                    if not native and head == "voice":
                        continue
                    conn.execute("INSERT INTO feature_tracks VALUES(?,?,?,?,?,?)", (
                        key, head, sha, 12, blob,
                        f"{head}-{'native' if native else 'old'}",
                    ))
            vec = [0.0] * 1280
            vec[0] = .6
            vec[(n % 13) + 1] = .8
            for native, folder in ((False, old_dir), (True, native_dir)):
                frontend = FRONTEND if native else bridge.OLD_FRONTEND
                contract = [1, bridge.ENCODER, hashes[bridge.ENCODER], frontend,
                            bridge.POOLING, bridge.NORMALIZATION, 1280]
                fp = hashlib.sha256(json.dumps(
                    contract, ensure_ascii=False, separators=(",", ":")
                ).encode()).hexdigest()
                payload = {
                    "schema_version": 1, "kind": "discogs_effnet_song_embedding",
                    "validation_status": "experimental_unvalidated", "dimension": 1280,
                    "track_file": key, "audio_sha256": sha, "patches_analyzed": 12,
                    "encoder_model": bridge.ENCODER,
                    "encoder_sha256": hashes[bridge.ENCODER],
                    "preprocessing_version": frontend,
                    "pooling_version": bridge.POOLING,
                    "normalization_version": bridge.NORMALIZATION,
                    "representation_fingerprint": fp, "vector_f32": vec,
                }
                (folder / bridge.embedding_filename(key)).write_text(
                    json.dumps(payload), encoding="utf-8")
        a.commit()
        b.commit()
    finally:
        a.close()
        b.close()
    return old_db, native_db, old_dir, native_dir, model_dir, audio


class NativeBridgeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.old, self.native, self.old_emb, self.new_emb, self.models, self.audio = build_fixture(self.root)
        self.plan = self.root / "plan"
        self.result = self.root / "result"

    def prep_args(self):
        from argparse import Namespace
        return Namespace(
            baseline_db=self.old, baseline_embeddings=self.old_emb,
            audio_root=self.audio, models_dir=self.models,
            scanner=self.root/"scanner.exe", worker=self.root/"worker.exe",
            expected_scanner_sha256=bridge.digest(self.root/"scanner.exe"),
            expected_worker_sha256="", out_dir=self.plan,
        )

    def comp_args(self):
        from argparse import Namespace
        return Namespace(plan_dir=self.plan, baseline_db=self.old,
                         baseline_embeddings=self.old_emb,
                         native_db=self.native, native_embeddings=self.new_emb,
                         models_dir=self.models, native_frontend=FRONTEND,
                         ratings=None, pilot_audit=None,
                         score_tolerance=0.001, embedding_cosine_min=0.999,
                         out_dir=self.result)

    def test_complete_private_preflight_and_identical_native_100(self):
        before = self.old.read_bytes()
        p = bridge.prepare(self.prep_args())
        self.assertEqual(p["tracks"], 100)
        self.assertEqual((self.plan/"exact-100-tracks.txt").read_text().count("\n"), 100)
        report = bridge.compare(self.comp_args())
        self.assertEqual(report["status"], "PASS_EXPLORATORY_TOLERANCES")
        self.assertEqual(report["complete_song_pairs"], 4950)
        self.assertEqual(report["voice_head_coverage"], 100)
        self.assertEqual(report["patch_counts_match"], 100)
        self.assertEqual(report["overall_max_abs_score_difference"], 0)
        self.assertEqual(report["per_song_embedding_cosine_min"], 1)
        for r in report["similarity_rank_drift"].values():
            self.assertAlmostEqual(r["spearman_all_4950_pairs"], 1)
        self.assertEqual(before, self.old.read_bytes())
        output = (self.result/"aggregate-native-cohort-comparison.json").read_text()
        self.assertNotIn("Artist-", output)
        self.assertNotIn("Titel", output)
        self.assertNotIn(str(self.audio), output)

    def test_original_12_human_labels_replayed_privately_without_retraining(self):
        bridge.prepare(self.prep_args())
        tracks, defs = bridge.read_cohort(
            self.old, {"genre", "moodtheme"}, bridge.OLD_FRONTEND)
        vectors = bridge.validate_embeddings(self.old_emb, tracks, defs)
        keys = sorted(tracks)
        rated_csv, sealed_json = self.root/"human.csv", self.root/"sealed.json"
        rows, private = [], []
        for i in range(12):
            left, right = keys[i*2], keys[i*2+1]
            source = {
                key: {"genre": tracks[key]["genre"]["scores"],
                      "moodtheme": tracks[key]["moodtheme"]["scores"],
                      "embedding": vectors[key]}
                for key in (left, right)
            }
            scores = bridge.model_scores(source[left], source[right])
            rows.append({
                "left": left, "right": right,
                "genre_similarity_1to5": str(i % 5 + 1),
                "mood_energy_similarity_1to5": str((i * 2) % 5 + 1),
                "timbre_similarity_1to5": str((i * 3) % 5 + 1),
                "next_track_suitability_1to5": str((i * 4) % 5 + 1),
                "confidence_1to3": "3", "notes": "Fiktiver Hörtest",
            })
            private.append({
                "pair_number": i + 1, "left": left, "right": right,
                "similarity_scores_not_probabilities": scores
            })
        with rated_csv.open("w", encoding="cp1252", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter="\t")
            writer.writeheader()
            writer.writerows(rows)
        sealed_json.write_text(json.dumps({
            "schema": "private_blinded_local_ab_pilot_selection_v1",
            "pairs_private_do_not_open_before_review": private
        }), encoding="utf-8")
        args = self.comp_args()
        args.ratings = rated_csv
        args.pilot_audit = sealed_json
        result = bridge.compare(args)
        audit = result["original_12_pair_human_sensitivity"]
        self.assertTrue(audit["original_sealed_scores_reproduced"])
        self.assertTrue(audit["human_ratings_verified_from_local_csv"])
        self.assertEqual(audit["sample_sizes"], {"all": 12, "music": 11})
        for sample in audit["paired_model_vs_human"].values():
            self.assertEqual(len(sample), 5)
            for model in sample.values():
                self.assertEqual(len(model), 4)
                for values in model.values():
                    self.assertEqual(values["previous_spearman"],
                                     values["native_spearman"])
        aggregate = (self.result/"aggregate-native-cohort-comparison.json").read_text()
        self.assertNotIn("Artist-", aggregate)
        self.assertNotIn("Hörtest", aggregate)
        self.assertNotIn("Titel", aggregate)

    def test_modified_original_audio_fails_before_any_output(self):
        file = self.audio / "Artist-003" / "Album 001" / "Titel 003.flac"
        file.write_bytes(b"drifted original audio")
        with self.assertRaisesRegex(ValueError, "no longer matches"):
            bridge.prepare(self.prep_args())
        self.assertFalse(self.plan.exists())

    def test_incorrect_scanner_hash_or_missing_model_fails_closed(self):
        args = self.prep_args()
        args.expected_scanner_sha256 = "0"*64
        with self.assertRaisesRegex(ValueError, "Scanner EXE hash"):
            bridge.prepare(args)
        self.assertFalse(self.plan.exists())
        (self.models / bridge.ENCODER).unlink()
        with self.assertRaisesRegex(ValueError, "model"):
            bridge.prepare(self.prep_args())
        self.assertFalse(self.plan.exists())

    def test_fingerprint_and_patch_change_fail_closed(self):
        bridge.prepare(self.prep_args())
        with closing(sqlite3.connect(self.native)) as conn:
            conn.execute("UPDATE feature_tracks SET patches_analyzed=13 WHERE model_id='genre'")
            conn.commit()
        with self.assertRaisesRegex(ValueError, "patch count"):
            bridge.compare(self.comp_args())
        self.assertFalse(self.result.exists())

    def test_reject_traversal_and_output_overlap(self):
        with self.assertRaises(ValueError):
            bridge.safe_song_path("../secret.wav", self.audio)
        with self.assertRaises(ValueError):
            bridge.safe_song_path("C:/secret.wav", self.audio)
        with self.assertRaises(ValueError):
            bridge.verify_disjoint_output(self.audio/"new", [self.audio])
        with self.assertRaises((ValueError, FileExistsError)):
            bridge.verify_disjoint_output(self.root, [self.old])

    def test_rank_statistic_ties(self):
        self.assertEqual(bridge.average_ranks([2, 1, 2, 3]), [1.5, 0., 1.5, 3.])
        self.assertAlmostEqual(bridge.spearman([1, 2, 3], [3, 2, 1]), -1.)


if __name__ == "__main__":
    unittest.main()
