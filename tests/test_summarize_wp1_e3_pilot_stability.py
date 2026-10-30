"""Synthetic, no-human-file tests of WP1-E3 pilot aggregate-only stability."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import summarize_wp1_e3_pilot_stability as p


def fixture():
    def cell(n, rho):
        return {
            "n":n,"spearman_rho":rho,
            "kendall_tau_b":0.1,
            "loo_spearman_min":rho-0.05,
            "loo_spearman_max":rho+0.05,
            "largest_rank_disagreements":[
                {"pair_number":2,"model_minus_human_rank_percentile":-0.8}],
        }
    def cohort(n,rho):
        return {
            "n":n,
            "model_vs_human":{
                model:{
                    rating:cell(n,rho)
                    for rating in p.RATINGS
                }
                for model in p.MODELS
            },
        }
    return {
        "schema":p.SOURCE_SCHEMA,
        "status":"EXPLORATORY_ONLY_NO_GENERAL_METRIC_SELECTED",
        "pairs_total":12,
        "nonmusic_pairs_explicitly_flagged":[10],
        "complete_sample_including_nonmusic":cohort(12,0.25),
        "musical_pairs_sensitivity_excluding_flagged":cohort(11,0.5),
        "extra_private_song_fields_should_be_ignored":"SECRET_SONG_ID",
    }


class Wp1E3AggregateOnlyTests(unittest.TestCase):
    def test_reports_20_cells_with_only_safe_rho_shifts_and_loo(self):
        result=p.summarize(fixture())
        self.assertEqual(result["schema"],p.SCHEMA)
        self.assertEqual(result["comparison_cells"],20)
        self.assertFalse(result["general_metric_selected"])
        self.assertFalse(result["original_ratings_or_audit_or_song_ids_used"])
        self.assertFalse(result["confidence_interval_or_significance_computed"])
        report=json.dumps(result)
        self.assertNotIn("SECRET_SONG_ID",report)
        self.assertNotIn("pair_number",report)
        self.assertNotIn("largest_rank_disagreements",report)
        for model in p.MODELS:
            for dimension in p.RATINGS:
                row=result["results"][model][dimension]
                self.assertEqual(row["rho_12_including_nonmusic"],0.25)
                self.assertEqual(row["rho_11_music_only"],0.5)
                self.assertEqual(row["rho_change_excluding_pair10"],0.25)
                self.assertEqual(row["music_11_leave_one_out_rho_min"],0.45)
                self.assertEqual(row["music_11_leave_one_out_rho_max"],0.55)

    def test_reject_mutated_or_missing_denominators_schemas_channels(self):
        base=fixture()
        modifications=[
            lambda d:d.update(schema="unknown"),
            lambda d:d.update(status="APPROVED_GENERAL_METRIC"),
            lambda d:d.update(pairs_total=11),
            lambda d:d.update(nonmusic_pairs_explicitly_flagged=[]),
            lambda d:d["complete_sample_including_nonmusic"].update(n=11),
            lambda d:d["musical_pairs_sensitivity_excluding_flagged"].update(n=12),
            lambda d:d["musical_pairs_sensitivity_excluding_flagged"]["model_vs_human"].pop("mood_cosine"),
            lambda d:d["complete_sample_including_nonmusic"]["model_vs_human"]["mood_cosine"].pop("timbre_similarity_1to5"),
            lambda d:d["musical_pairs_sensitivity_excluding_flagged"]["model_vs_human"]["genre_cosine"]["genre_similarity_1to5"].update(n=12),
            lambda d:d["musical_pairs_sensitivity_excluding_flagged"]["model_vs_human"]["genre_cosine"]["genre_similarity_1to5"].update(loo_spearman_min=None),
            lambda d:d["musical_pairs_sensitivity_excluding_flagged"]["model_vs_human"]["genre_cosine"]["genre_similarity_1to5"].update(spearman_rho=2.),
            lambda d:d["musical_pairs_sensitivity_excluding_flagged"]["model_vs_human"]["genre_cosine"]["genre_similarity_1to5"].update(loo_spearman_min=0.8,loo_spearman_max=0.1),
        ]
        for mutation in modifications:
            d=copy.deepcopy(base)
            mutation(d)
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                p.summarize(d)

    def test_file_reader_never_consumes_original_pilot_files(self):
        d=fixture()
        with tempfile.TemporaryDirectory(prefix="synthetic-wp1-e3-") as tmp:
            path=Path(tmp)/"aggregate-model-comparison.json"
            path.write_text(json.dumps(d),encoding="utf-8")
            self.assertIsInstance(p.summarize(json.loads(path.read_text())),
                                  dict)
            self.assertNotIn("SECRET_SONG_ID",json.dumps(p.summarize(d)))


if __name__=="__main__":
    unittest.main()
