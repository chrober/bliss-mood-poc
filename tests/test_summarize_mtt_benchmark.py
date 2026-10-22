"""Offline scorecard tests for MTT coverage/abstention reporting."""
import importlib.util
from pathlib import Path
import unittest

P = Path(__file__).resolve().parents[1] / "scripts" / "summarize_mtt_benchmark.py"
spec = importlib.util.spec_from_file_location("mtt_summary", P)
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)


class ReportTests(unittest.TestCase):
    def test_exploratory_results_show_both_heads_and_all_metrics(self):
        metric = {
            "total_unique_unordered_questions":346,
            "evaluated_questions":300,
            "abstained_questions":46,
            "human_tied_majority_questions":40,
            "prediction_coverage_of_scorable_questions":300/306,
            "majority_odd_one_out_accuracy":.65,
            "majority_accuracy_with_metric_abstentions_as_incorrect":195/306,
            "human_vote_weighted_agreement":.59,
        }
        report={
            "schema":"magnatagatune-all-exploratory-v1",
            "triplets_scored":346,
            "unique_clip_ids":1019,
            "per_head":{
                h:{"metrics":{f"metric{i}":dict(metric) for i in range(7)}}
                for h in ("genre","moodtheme")
            },
        }
        output=s.summarize(report)
        self.assertEqual(output.count("| moodtheme | metric"),7)
        self.assertEqual(output.count("| genre | metric"),7)
        self.assertIn("65.0%",output)
        self.assertIn("No independent MTT holdout remains",output)

    def test_incomplete_results_fail_closed(self):
        report={"schema":"magnatagatune-all-exploratory-v1",
                "triplets_scored":345,"unique_clip_ids":1019}
        with self.assertRaisesRegex(ValueError,"Unexpected MTT cohort"):
            s.summarize(report)


if __name__=="__main__":
    unittest.main()
