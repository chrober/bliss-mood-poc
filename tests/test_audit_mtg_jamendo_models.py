"""Offline fixture tests for MTG-Jamendo tag/vocabulary and split safety."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_mtg_jamendo_models.py"
spec = importlib.util.spec_from_file_location("audit_mtg", SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class MtgSplitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.split = root / "splits"
        self.models = root / "models"
        self.split.mkdir()
        self.models.mkdir()
        self.populate()

    def populate(self):
        for head, dimensions in audit.HEADS.items():
            tags = [f"class{n}" for n in range(dimensions)]
            prefix = "genre---" if head == "genre" else "mood/theme---"
            modelname = "mtg_jamendo_" + head
            obj = {
                "type": "multi-label classifier",
                "name": modelname, "classes": tags,
                "dataset": {"name": "MTG Jamendo", "metrics": {"test ROC-AUC": .7}},
                "inference": {"embedding_model": {"model_name": "discogs-effnet-bs64-1"}},
            }
            (self.models / f"{modelname}-discogs-effnet-1.json").write_text(
                json.dumps(obj), encoding="utf-8"
            )
            for idx, part in enumerate(audit.SPLITS):
                row = (f"track_{idx}\tartist_{idx}\talbum_{idx}\t"
                       f"{idx}/song.mp3\t180.0\t"
                       + "\t".join(prefix + t for t in (tags if idx == 0 else tags[:2])))
                txt = ("TRACK_ID\tARTIST_ID\tALBUM_ID\tPATH\tDURATION\tTAGS\n"
                       + row + "\n")
                (self.split / f"autotagging_{head}-{part}.tsv").write_text(
                    txt, encoding="utf-8"
                )

    def test_split_model_head_agreement(self):
        report = audit.inspect(self.split, self.models)
        self.assertEqual(report["heads"]["genre"]["class_count"], 87)
        self.assertEqual(report["heads"]["moodtheme"]["class_count"], 56)
        self.assertEqual(report["heads"]["genre"]["distinct_tracks_union"], 3)
        self.assertEqual(
            report["heads"]["genre"]["artist_overlaps_between_splits"]["train_vs_test"], 0
        )
        self.assertEqual(report["heads"]["genre"]["splits"]["train"]["distinct_tags"], 87)
        self.assertNotIn('"track_1"', json.dumps(report))
        self.assertIn("NOT_verified", report["status"])

    def test_duplicate_track_across_splits_fails(self):
        file = self.split / "autotagging_genre-test.tsv"
        file.write_text(file.read_text().replace("track_2", "track_0"), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "duplicate track"):
            audit.inspect(self.split, self.models)

    def test_unrecognized_model_class_fails(self):
        file = self.models / "mtg_jamendo_genre-discogs-effnet-1.json"
        model = json.loads(file.read_text(encoding="utf-8"))
        model["classes"][0] = "unknown_class"
        file.write_text(json.dumps(model), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "model classes"):
            audit.inspect(self.split, self.models)


if __name__ == "__main__":
    unittest.main()
