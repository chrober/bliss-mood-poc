# WP1-E3: actual local 12/11-pair human pilot — operator-reported results (30 Oct 2026)

## Provenance and strict scope

The operator executed [the read-only Windows launcher](../scripts/run_wp1_e3_local12_windows.ps1) successfully on the existing research branch, after an origin fast-forward to commit `6084f145`. This document records the **numerical console output supplied by the operator**, **not** a GitHub-verified independent execution of confidential local inputs. The console confirmed **12/12 human-rated pairs**, **60/60 numeric human rating fields** and a sensitivity view excluding **the previously declared nonmusic pair 10**, leaving 11 music pairs. No new votes, audio scans, source DB writes, re-training or external uploads occurred.

Original private human votes and sealed score/source files remain on the research workstation; they were not read by this assistant or put into GitHub. The console returned the existing `EXPLORATORY_ONLY_NO_GENERAL_METRIC_SELECTED` status. This is one user's **deliberately model-selected** pilot, not an independent randomly selected or artist-disjoint holdout, and all listed hypotheses were post-hoc inspected. Neither correlation magnitudes nor pairwise differences are significance or proof of cross-listener generalization.

**Important distinction:** The displayed four human rating histograms below summarize the **full 12 pairs**, whereas the displayed Spearman/Kendall correlations were printed by the launcher for the **11 music-only pairs**. Do **not** mix their denominators, impute the omitted pair, or claim that full-12 correlations were reported.

## Actual console output: 11 music-only pairs

Spearman rank correlations (ρ), five frozen representations × four separate human-rated objectives:

| Frozen representation | Genre/Style | Mood/Energy | Timbre | Directed next-track suitability |
| --- | ---: | ---: | ---: | ---: |
| Genre Cosine | 0.423370 | -0.088041 | 0.501670 | 0.434914 |
| Genre Centered Cosine | 0.497809 | -0.132061 | 0.454144 | 0.473148 |
| Mood Cosine | 0.590857 | 0.161408 | 0.264037 | 0.673878 |
| Mood Centered Cosine | **0.688558** | 0.220102 | 0.348529 | **0.769463** |
| Embedding1280 Cosine | 0.465242 | **0.410857** | **0.765707** | 0.520941 |

Kendall tau-b (tie aware), same 11 pairs, same order and four objectives:

| Frozen representation | Genre/Style | Mood/Energy | Timbre | Directed next-track suitability |
| --- | ---: | ---: | ---: | ---: |
| Genre Cosine | 0.295026 | -0.064775 | 0.399035 | 0.332900 |
| Genre Centered Cosine | 0.334363 | -0.107958 | 0.352089 | 0.374513 |
| Mood Cosine | 0.452374 | 0.064775 | 0.211254 | 0.582575 |
| Mood Centered Cosine | **0.531048** | 0.151142 | 0.305144 | **0.665800** |
| Embedding1280 Cosine | 0.373700 | **0.323875** | **0.680706** | 0.457738 |

Observed descriptive leaders differ **by the human objective**: Mood Centered Cosine on Genre/Style and directed next-track suitability, and Embedding1280 Cosine on Mood/Energy and Timbre. In particular, the nominal Mood classifier scores correlate only 0.161/0.220 with the 11 Mood/Energy judgments, while Embedding1280 correlates 0.411; this is a **specific local hypothesis**, not a proven inadequacy of a Mood head. Mood Centered's 0.769 directed next-track correlation is likewise NOT proof of directional playlist suitability: its symmetric pair score has no intrinsic transition direction and the pairs were selected.

The observed pattern is **compatible with task-conditional signal complementarity**, not sufficient to select or fit General Metric weights, deploy per-user personal learning, or choose a universal winner. Spearman and Kendall differences were neither prospectively prespecified nor independently validated; n=11, one listener, many inspected scores/objectives, human rating ties and possible single-pair leverage preclude defensible significance claims.

## The separate 12-pair human rating distribution (including nonmusic pair 10)

| Rating question (1..5) | Mean of 12 | 4-or-5 ratings / 12 |
| --- | ---: | ---: |
| Genre/Style | 3.083333 | 5 |
| Mood/Energy | 3.333333 | 6 |
| Timbre | 3.500000 | 8 |
| Directed next-track suitability | 3.333333 | 6 |

All five rating fields per pair, including confidence, were complete: 60 numeric entries. All original pair-10 judgments must remain unchanged in the preserved full-12 report, and **only** the declared 11-pair sensitivity excludes pair 10.

## What is NOT available from the console output

The original evaluator's **locally saved**, anonymized `aggregate-model-comparison.json` includes full-12 model correlation results, all-11 and all-12 **leave-one-pair-out Spearman minimum/maximum**, concordance/discordance/tie counts and three largest numbered rank disagreements. The console output supplied here prints only the 11-pair Spearman/Kendall scores and the full-12 rating histograms. Therefore, *full-12-versus-11 correlation shifts, one-pair influence, influence-stable method ordering and any exact confidence/probability claims have NOT been verified in this turn*.

A separate read-only aggregate-only helper, if implemented, may extract just the **20×two-cohort LOO min/max and rank-correlation shifts**, with no original private filenames, song identifiers, comments, source features or numbered private pair diagnostics. Treat even those summaries as post-hoc sensitivity, not population inference. No additional listening needed.

## Implemented next sensitivity check — aggregate only

The tracked, read-only [WP1-E3 stability summarizer](../scripts/summarize_wp1_e3_pilot_stability.py) was added **after** the operator's pilot run. It takes only the existing local `aggregate-model-comparison.json` (not the original ratings, sealed selection audit, or private numbered pair CSV). It validates the frozen 12-versus-11 research schema and extracts, for all five models × four objectives:

- Spearman rho on full 12 (including unchanged pair 10);
- Spearman rho on 11 music-only pairs;
- signed rho shift from removing nonmusic pair 10;
- minimum/maximum music-only leave-one-pair-out Spearman rho;
- flag indicating whether the LOO extrema span negative and positive values.

No original human rating rows, private artist or track names, raw features, model pair scores, or numbered rank discrepancies are printed or written. The helper cannot produce statistical significance or independent validation. It **does not** rank/select a model or automatically tune weights. [Synthetic privacy/contract tests](../tests/test_summarize_wp1_e3_pilot_stability.py) check source-schema drift and exclusion of extra/private fields; the [WP1 external evidence workflow](../.github/workflows/research-wp1-external-evidence-replay.yml) runs the tests without loading private data.

The operator can run it on the locally generated existing aggregate, after updating the branch, using this exact PowerShell block:

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $Repo = 'D:\LMS\bliss-mood-poc'
    $Aggregate = Join-Path $Repo 'benchmark-wp1-e3-local12-b34b7e62fc5649c19033b0366dcc59f8\aggregate-model-comparison.json'
    $Analyzer = Join-Path $Repo 'scripts\summarize_wp1_e3_pilot_stability.py'
    if (!(Test-Path -LiteralPath $Aggregate -PathType Leaf)) {
        throw 'Original aggregate-only WP1-E3 report is missing.'
    }
    if (!(Test-Path -LiteralPath $Analyzer -PathType Leaf)) {
        throw 'Update the existing research branch before invoking this analyzer.'
    }
    & python $Analyzer --aggregate $Aggregate
    if ($LASTEXITCODE -ne 0) {
        throw 'WP1-E3 aggregate-only sensitivity check blocked.'
    }
}
```

This requires **no re-listening and no rerun of the original 12-pair evaluator**; it is an optional next read-only local diagnostic. Results from it must not be reported as observed until the user has actually executed it or provided the full aggregate.

## Decision and WP1 General research continuation

1. Retain Mood Centered Cosine as a **descriptive candidate**, not a decided General winner, and Embedding1280 as a **task-specific candidate** particularly for timbre/acoustic similarity.
2. Keep Genre, Mood/Energy, Timbre and directional Next-Track objectives separate; do not average their correlations into a composite quality score or infer valid universal fusion weights.
3. First inspect the previously saved **full-12 vs music-only-11 and leave-one-pair-out sensitivity** from the *existing aggregate only*, without moving confidential files or asking for new music ratings.
4. The existing MTT official source remains **blocked** in the actual [30-clip range test after 7 successes](wp1-e2-mtt-source-and-cache-diagnostics-20261030.md); the eight historical MTT methods have only aggregate accuracy evidence and the exact joint-correctness distribution is not known ([WP1-E3 sharp limits](wp1-e3-sharp-mtt-paired-bounds-and-existing-pilot-20261030.md)). FMA official TEST stays untouched. No four-global-fusion real MTT scores can be imputed.
5. WP1 remains primary; WP2-P3/P4 are synthetic software contracts and WP3-R6/R7 approximate Essentia *teacher outputs*, not subjective musical quality. No General/Personal metric selection, PR #16/main or Lyrion/BlissMixerLab/native worker edits.

The source material for the exact local results above is the **user-supplied PowerShell console output**, not a re-downloaded file or a new inference.
