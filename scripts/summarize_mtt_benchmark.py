#!/usr/bin/env python3
"""Aggregate-only table for seven MTT metrics; never implies a metric winner.

Consumes research JSON produced by benchmark_magnatagatune.py.
Display coverage and abstention-inclusive results alongside conditional
majority accuracy. This cannot estimate paired statistical significance:
per-question model predictions are not included in aggregate reports.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path


def fmt(value):
    if value is None:
        return "n/a"
    if not isinstance(value, (float, int)) or not math.isfinite(value):
        raise ValueError("Non-finite metric value")
    return f"{100 * value:.1f}%"


def summarize(report):
    if report["schema"] != "magnatagatune-all-exploratory-v1":
        raise ValueError("Only entire 346-question exploratory corpus supported")
    if report["triplets_scored"] != 346 or report["unique_clip_ids"] != 1019:
        raise ValueError("Unexpected MTT cohort")
    result = [
        "## MagnaTagATune: 346 questions, exploratory only",
        "",
        "Two heads, seven metrics; all 1,019 clips analyzed. No independent MTT holdout remains.",
        "",
        "| Head | Metric | Valid predictions | Human ties | Coverage | Accuracy on valid | Accuracy incl. abstentions | Human-vote agreement |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for head in ("genre", "moodtheme"):
        metrics = report["per_head"][head]["metrics"]
        if len(metrics) != 7:
            raise ValueError("Expected seven metrics per model head")
        for name, stats in metrics.items():
            if (stats["total_unique_unordered_questions"] != 346
                    or stats["evaluated_questions"] + stats["abstained_questions"] != 346):
                raise ValueError("Incomplete/tampered score accounting")
            result.append(
                f"| {head} | {name} | {stats['evaluated_questions']} | "
                f"{stats['human_tied_majority_questions']} | "
                f"{fmt(stats['prediction_coverage_of_scorable_questions'])} | "
                f"{fmt(stats['majority_odd_one_out_accuracy'])} | "
                f"{fmt(stats['majority_accuracy_with_metric_abstentions_as_incorrect'])} | "
                f"{fmt(stats['human_vote_weighted_agreement'])} |"
            )
    result.extend([
        "",
        "**Interpretation:** 1/3 is the random odd-one-out accuracy reference.",
        "Accuracy on valid predictions excludes human ties and metric abstentions; it must not be compared alone.",
        "These questions share artist/song identities and cannot support a strict independent MTT holdout claim.",
        "This is descriptive same-corpus evidence, not a preregistered paired test or a production-metric decision.",
    ])
    return "\n".join(result) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--out", type=Path)
    a = p.parse_args()
    result = summarize(json.loads(a.report.read_text(encoding="utf-8")))
    if a.out:
        if a.out.exists():
            p.error("Never overwrite existing research report")
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(result, encoding="utf-8")
    print(result)


if __name__ == "__main__":
    main()
