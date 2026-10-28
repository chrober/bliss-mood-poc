"""Synthetic privacy, parsing, tie-statistics and strict pair audit regression tests."""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import evaluate_local_listening_pilot as pilot


def make_fixture(root: Path, *, delimiter: str = ",", encoding: str = "utf-8-sig",
                 shuffle_audit: bool = False) -> tuple[Path, Path]:
    review, audit = root / "listening-pairs.csv", root / "selection-audit-private.json"
    raw = io.StringIO(newline="")
    writer = csv.DictWriter(raw, fieldnames=pilot.CSV_FIELDS, delimiter=delimiter)
    writer.writeheader()
    pairs = []
    for i in range(1, 13):
        a, b = f"Fiktiv, Künstler-{i:02d}/A-{i}.flac", f"München, Test-{i:02d}/B-{i}.flac"
        record = {
            "left": a, "right": b,
            "genre_similarity_1to5": (i % 5) + 1,
            "mood_energy_similarity_1to5": ((i + 1) % 5) + 1,
            "timbre_similarity_1to5": ((i + 2) % 5) + 1,
            "next_track_suitability_1to5": ((i * 2) % 5) + 1,
            "confidence_1to3": 3 if i != 5 else 2,
            "notes": "Fiktiv; kein Song" if i == 10 else "",
        }
        writer.writerow(record)
        pairs.append({
            "pair_number": i, "left": a, "right": b,
            "selection_stratum_not_human_label": "synthetic_held_out",
            "similarity_scores_not_probabilities": {
                "genre_cosine": i / 20,
                "genre_centered_cosine": (13 - i) / 20,
                "mood_cosine": ((i % 5) + 1) / 6,
                "mood_centered_cosine": (i % 6) / 7,
                "embedding_cosine": (i % 3) / 4,
            },
        })
    review.write_bytes(raw.getvalue().encode(encoding))
    if shuffle_audit:
        pairs[1], pairs[2] = pairs[2], pairs[1]
    audit.write_text(json.dumps({
        "schema": pilot.EXPECTED_SCHEMA,
        "n_review_pairs": 12,
        "pairs_private_do_not_open_before_review": pairs,
    }, ensure_ascii=False), encoding="utf-8")
    return review, audit


class LocalListeningPilotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_cp1252_tab_excel_all_five_scores_and_nonmusic_sensitivity(self):
        ratings, audit = make_fixture(self.root, delimiter="\t", encoding="cp1252")
        original_ratings, original_audit = ratings.read_bytes(), audit.read_bytes()
        result = pilot.evaluate(ratings, audit, self.root / "result", nonmusic="10")
        self.assertEqual(result["pairs_total"], 12)
        self.assertEqual(result["review_file_format"],
                         {"encoding": "cp1252", "delimiter": "tab"})
        self.assertEqual(result["numeric_ratings_valid"], 60)
        self.assertEqual(result["nonmusic_pairs_explicitly_flagged"], [10])
        self.assertEqual(result["complete_sample_including_nonmusic"]["n"], 12)
        self.assertEqual(result["musical_pairs_sensitivity_excluding_flagged"]["n"], 11)
        self.assertEqual(len(result["musical_pairs_sensitivity_excluding_flagged"]["model_vs_human"]), 5)
        self.assertEqual(len(result["musical_pairs_sensitivity_excluding_flagged"]["model_vs_human"]["genre_cosine"]), 4)
        self.assertEqual(result["pairs_with_note"], 1)
        aggregate = (self.root / "result" / "aggregate-model-comparison.json").read_text()
        details = (self.root / "result" / "numbered-pair-details-private.csv").read_text(encoding="utf-8-sig")
        self.assertNotIn("München", aggregate + details)
        self.assertNotIn("Künstler", aggregate + details)
        self.assertNotIn("kein Song", aggregate + details)
        self.assertIn('"spearman_rho"', aggregate)
        self.assertEqual(original_ratings, ratings.read_bytes())
        self.assertEqual(original_audit, audit.read_bytes())
        with self.assertRaises(FileExistsError):
            pilot.evaluate(ratings, audit, self.root / "result", nonmusic="10")

    def test_delimiters_and_utf8_bom(self):
        for delim in (",", ";", "\t"):
            with self.subTest(delimiter=repr(delim)):
                sub = self.root / str(ord(delim))
                sub.mkdir()
                ratings, audit = make_fixture(sub, delimiter=delim)
                reviews, meta = pilot.read_reviews(ratings)
                self.assertEqual(len(reviews), 12)
                self.assertIn("München", reviews[0]["right"])
                self.assertEqual(pilot.read_audit(audit, reviews)[0]["pair_number"], 1)
                self.assertEqual(meta["encoding"], "utf-8-sig")

    def test_mismatched_identity_fails_before_writing(self):
        ratings, audit = make_fixture(self.root, shuffle_audit=True)
        target = self.root / "should-not-exist"
        with self.assertRaisesRegex(ValueError, "identities/order differ"):
            pilot.evaluate(ratings, audit, target)
        self.assertFalse(target.exists())

    def test_rating_validation_missing_and_bad_number(self):
        ratings, audit = make_fixture(self.root)
        text = ratings.read_text(encoding="utf-8-sig")
        # Only change a numeric CSV cell, not the 24 distinct synthetic identities.
        text = text.replace(",3,4,5,3,", ",3,4,5,99,", 1)
        ratings.write_text(text, encoding="utf-8-sig")
        with self.assertRaises(ValueError):
            pilot.evaluate(ratings, audit, self.root / "bad")

    def test_nonmusic_pair_validation(self):
        ratings, audit = make_fixture(self.root)
        for invalid in ("0", "13", "1,1", "song", "1,", "1,2,3,4,5,6,7,8,9,10,11"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    pilot.evaluate(ratings, audit, self.root / "none", nonmusic=invalid)

    def test_spearman_and_kendall_ties_and_leave_one_out(self):
        self.assertAlmostEqual(pilot.spearman([1, 2, 3, 4], [1, 2, 3, 4]), 1.0)
        self.assertAlmostEqual(pilot.spearman([1, 2, 3, 4], [4, 3, 2, 1]), -1.0)
        self.assertAlmostEqual(pilot.kendall_tau_b([1, 2, 3], [1, 2, 3])[0], 1.0)
        self.assertEqual(pilot.kendall_tau_b([1, 2, 3], [3, 2, 1])[1]["discordant"], 3)
        self.assertIsNone(pilot.spearman([1, 1, 1], [1, 2, 3]))
        self.assertIsNone(pilot.kendall_tau_b([1, 1, 1], [1, 2, 3])[0])
        ranks = pilot.average_ranks([2, 1, 2, 3])
        self.assertEqual(ranks, [1.5, 0, 1.5, 3])
        self.assertEqual(len(pilot.loo_spearman([1,2,3,4], [1,4,2,3])), 4)

    def test_reject_untrusted_scores(self):
        ratings, audit = make_fixture(self.root)
        payload = json.loads(audit.read_text())
        payload["pairs_private_do_not_open_before_review"][0][
            "similarity_scores_not_probabilities"]["genre_cosine"] = float("nan")
        audit.write_text(json.dumps(payload))
        with self.assertRaisesRegex(ValueError, "Invalid similarity score"):
            pilot.evaluate(ratings, audit, self.root / "unsafe")
        self.assertFalse((self.root / "unsafe").exists())


if __name__ == "__main__":
    unittest.main()
