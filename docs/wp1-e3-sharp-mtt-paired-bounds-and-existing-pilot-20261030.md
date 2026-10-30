# WP1-E3: sharp bounds of paired comparisons from historical aggregates (30 October 2026)

> **Operator's original local pilot has now actually been evaluated (30 Oct 2026).** The 11 music-only pairs' 20 real Spearman/Kendall coefficients and the separate all-12 human rating distributions are recorded in [WP1-E3 real local pilot results](wp1-e3-local12-real-human-pilot-results-20261030.md). These were provided by user-visible PowerShell console output; raw private votes and scores were not made available. The original aggregate contains additional 12-versus-11 and leave-one-pair-out sensitivity; a [new aggregate-only read-only helper](../scripts/summarize_wp1_e3_pilot_stability.py) extracts those once run locally. They have **not** been observed from the supplied console alone. This is exploratory one-listener model-selected evidence, not independent quality proof. The older section below describing the local run as pending is historical and superseded here.

## Real reproducible result, no invented joint observations

**PASS:** [GitHub Actions 41064365096](https://github.com/chrober/bliss-mood-poc/actions/runs/41064365096) reran the already successful [WP1-E1](wp1-e1-verified-public-benchmark-evidence-20261030.md) source verification on the identical original GitHub Actions **aggregate-only JSON** artifacts. It then computed [WP1-E3 strict matched-question identifiability bounds](../scripts/audit_wp1_e3_paired_bounds.py) for all 8 historical methods against Mood Centered Cosine on the **same 293 human-decisive MTT triplets**. [Fail-closed synthetic tests](../tests/test_audit_wp1_e3_paired_bounds.py) explicitly enumerate feasible 2×2 contingency tables and verify sharpness. [Source-locked E1/E3 anonymous aggregate artifact](https://github.com/chrober/bliss-mood-poc/actions/runs/41064365096/artifacts/12981971941).

**No new MTT source audio or inference, no public FMA TEST, no human vote rows, no new embeddings, no private user files, no per-question predictions, no additional listening.** This is a further **analysis of previously explored** benchmark evidence, not an independent confirmation.

## Identifiability: what matched scores do and do not reveal

For two methods A and B scored against the **same** n=293 decisive human judgments, let `a` and `b` be known totals of correct responses, and let `c` be the *unknown* number of questions on which **both** were correct. The exact feasible bounds are:

```text
max(0, a + b - n) <= c <= min(a, b)
A-only correct  = a - c
B-only correct  = b - c
both incorrect  = n - a - b + c
disagree in correctness = a + b - 2*c
```

Both endpoints and every integer `c` between them are attainable by some 2×2 arrangement with the given marginals, so these are **sharp**, not heuristics. The archive gives *only marginal counts*, NOT actual pairwise correctness. A pooled p-value, actual McNemar test, paired bootstrap, within-question discordance or group-aware uncertainty cannot be reconstructed from these marginals. The CLI computes the **range of hypothetical exact McNemar p-values** over every feasible table **only to demonstrate nonidentifiability**; these are NOT observed p-values, evidence of significance, confidence intervals, adjusted tests or defensible independent musical-similarity claims. Furthermore the MTT questions are not proven IID and all 346 unique questions have been explored already.

### Actually verified MTT numbers versus Mood Centered Cosine

| Candidate compared with Mood Centered Cosine (193/293) | Candidate correct / 293 | Percentage-point difference (Mood Centered minus candidate) | Sharp possible disagreement in **correctness** across the 293 questions |
| --- | ---: | ---: | ---: |
| Mood Cosine | 192 | +0.3413 pp | **1 to 201** |
| Genre Cosine | 191 | +0.6826 pp | **2 to 202** |
| Genre Centered Cosine | 191 | +0.6826 pp | **2 to 202** |
| Embedding1280 Cosine | 182 | +3.7543 pp | **11 to 211** |
| Triplet-local equal rank: Embedding + Genre + Mood | 192 | +0.3413 pp | **1 to 201** |
| Triplet-local equal rank: Embedding + Mood | 170 | +7.8498 pp | **23 to 223** |
| Triplet-local equal rank: Genre + Mood | 167 | +8.8737 pp | **26 to 226** |
| Triplet-local equal rank: Embedding + Genre | 163 | +10.2389 pp | **30 to 230** |

The four rank-fusion entries are **triplet-local**, NOT globally comparable pairwise similarity metrics. Ties, undefined scores and abstentions count as **incorrect** on the same common 293-question denominator. The differences above are **descriptive**; there is no certified superiority or universal winner even for the largest marginal differences.

For Mood Cosine (192) versus Mood Centered Cosine (193), the actual correctness disagreement could range from 1 to 201 questions. Therefore “193 beats 192” does **not** tell us which model gets which human cases right, whether an improvement holds for groups/genres, or whether different metric views complement each other. With only two marginals, even a true paired McNemar p value is unidentifiable. **Do not assume each method's success events are independent**, and do not approximate a paired test using unpaired standard errors.

## Other existing evidence remains separate

- **FMA 80 artist-distinct VALIDATION songs:** P@5, mAP@10 and nDCG@10 aggregate values exist, but no per-query paired predictions/ranking outcomes in the archived E1 aggregate. Cannot recover source-artist-group bootstrap, candidate overlap, reciprocal ranking changes or reliable per-query comparative uncertainty. **Official TEST remains unopened**.
- **DEAM 240 screened songs:** mean query-wise valence/arousal Spearman per method exists, but no individual query coefficients in E1 aggregate. Cannot reconstruct paired correlation differences or artist-/album-group-aware variance. The Va/Ar target is a **mood-proximity proxy**, not direct music pair-similarity.
- **Public MTT four fixed global equal-weight pairwise fusions:** still **NOT MEASURED** on real audio; the official publisher repeated-range access gate [WP1-E2](wp1-e2-mtt-source-and-cache-diagnostics-20261030.md) stopped after **7/30 clips** even though tiny HTTP-206 probes and one original ZIP/CRC-checked member succeeded. Repeating the full 1,019-clip workflow now is not justified; moving the licensed cache across sibling branches or publicly uploading it is not authorized.
- **WP3-R6/R7:** Bliss23↔Essentia teacher approximation on 240 private songs, not human ground truth and not a replacement for independent WP1 validation. **WP2-P3/P4:** fictional-only Personal Metric Learning and calibration; not production calibration or real preferences.

## Optional existing, already completed private 12-pair listening pilot

A separate, **previously fully rated** local study already contains 12 model-selected song pairs, 24 different recordings, **60 human numeric ratings**, and an original selection audit containing five frozen scoring representations. It was not collected as a prospective independent General-Metric holdout; it has one listener and selection bias. Pair **10** is explicitly recognized as a nonmusic interview/comment and must remain in the preserved full-12 result, with a distinct **11 music-only sensitivity** view.

The existing [read-only original pilot evaluator](../scripts/evaluate_local_listening_pilot.py) computes tie-aware Spearman and Kendall tau-b for five representations against four different human dimensions (genre/style, mood/energy, timbre and **directed** next-track suitability), for both full 12 and music-only 11. It requires the user's original local `listening-pairs.csv` and sealed `selection-audit-private.json`. **No such private files are available in GitHub Actions**; no real pilot result was invented or committed.

To reuse the existing ratings without new listening, a new [branch-aware PowerShell launcher](../scripts/run_wp1_e3_local12_windows.ps1) reads *only* the exact files in `D:\LMS\bliss-mood-poc\benchmark-local-blinded-ab-pilot12-20261021`, requires the current `feat/general-pairwise-similarity-research` branch and checked-in evaluator, creates a fresh locally ignored `benchmark-wp1-e3-local12-<uuid>` directory without overwrite, flags pair 10 explicitly, and prints only aggregate ranks/correlations. Outputs include `aggregate-model-comparison.json` (numeric and numbered-pair-only, safe to inspect before voluntarily sharing) and `numbered-pair-details-private.csv` (personal listening scores by pair number; **keep private**). Do not commit/upload original votes, comments, model selection audit, feature vectors, local paths or source DB. The launcher itself is syntax-only tested on Windows CI without user files.

The local pilot provides **more direct human-facing evidence** than teacher reconstruction, but is **small, intentionally model-selected, exploratory**, and its 11/12-person sensitivity cannot be used as a holdout to fit and then validate a new metric. Keep four human dimensions separate and do not pretend a symmetric pair metric predicts directed playlist transitions.

### Optional single Windows PowerShell invocation (no new ratings)

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $Repo = 'D:\LMS\bliss-mood-poc'
    git -C $Repo switch feat/general-pairwise-similarity-research
    if ($LASTEXITCODE -ne 0) { throw 'Branch change failed.' }
    git -C $Repo pull --ff-only origin feat/general-pairwise-similarity-research
    if ($LASTEXITCODE -ne 0) { throw 'Repository update failed.' }
    & (Join-Path $Repo 'scripts\run_wp1_e3_local12_windows.ps1') -Repo $Repo
    if (-not $?) { throw 'Read-only original 12-pair evaluation failed.' }
}
```

No real pilot execution is asserted by this public research commit. The safe optional user-facing report is the numeric aggregate only, never the private per-pair file.

## Decisions

**Current scientific decision:** Historical Mood Centered Cosine is a descriptive MTT leader by **one** correctness judgment versus Mood Cosine, and by **two** versus Genre Cosine. No current evidence certifies one universal *General Metric*. The most consequential missing input for an actual paired MTT comparison is **per-question prediction correctness** on original audio, which is not retained in the original aggregate; for FMA/DEAM it is similarly per-query comparisons. New audio retrieval is currently technically blocked and no independent MTT holdout remains.

Instead of repeating WP2 fictional optimizations or generating speculative p values, we have now made the statistical uncertainty explicit and prepared read-only **existing** local human evidence for optional further diagnostic analysis. Do not choose fusion weights based on the 12 selected pairs, do not access FMA TEST for exploration, do not require new user ratings, and do not change production Lyrion, BlissMixerLab, the native scanner, `main` or PR #16.
