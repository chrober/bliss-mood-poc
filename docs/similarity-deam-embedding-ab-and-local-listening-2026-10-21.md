# DEAM 240: 1280D audio embeddings versus 87D/56D classification heads

**Status:** October 21, 2026. Draft PR #16, branch
`feat/similarity-metric-evaluation` only. No changes to
`main`, PR #13/#17, or the production playlist mixer.

## Research hypothesis

Compare direct 1280D Discogs-EffNet cosine with Genre/Mood classifier
outputs on **exactly the same DEAM recordings and human song-level
valence/arousal labels**. Higher rank association with VA proximity
supports only *emotional proximity under this operational definition*;
it is neither evidence of good Lyrion transitions nor an independent
judgment of general perceived sonic similarity.

### Frozen cohort from the preceding development experiment

Reference: successful
[screened 240-song DEAM run 39579552118](https://github.com/chrober/bliss-mood-poc/actions/runs/39579552118),
[aggregate artifact 12335578980](https://github.com/chrober/bliss-mood-poc/actions/runs/39579552118/artifacts/12335578980).

- Seed `20261021`, **240 songs**: 197 older excerpts and 43 full
  2015 recordings. A conservative MTG-Jamendo artist/title screen
  removed **75 potential matches**, leaving 1,727 eligible audio
  items. This **does not prove training-set independence**.
- Frozen sample SHA256:
  `db12c5d2692285638a4c25af442f29fd75391eb86cd7f1ea88d2f565d12630d0`.
- Publisher DEAM audio ZIP SHA256:
  `e2814325f573ade8caebc697f0efcfdf7207142b737d72558a416117ca591353`.
  Annotation ZIP:
  `809b0feb4ba6196c1eda9b2b7b33b892b11fa71457cfceb0d47e832ed1a5f15f`.
  DEAM metadata:
  `3d1d5ab42e852803a770f2cfbd685c6b464e1ebe76f26b0e10954597902b90f8`.
  MTG catalogue TSV:
  `bb1efa2876536cbe1a8b67db5dda15249ca144f0cff69e481b638803cbdc9aca`.
- Pre-embedding Mood Cosine reference: pooled VA mean-query
  Spearman **0.286784551387186**, Valence **0.16424605171402107**,
  Arousal **0.2726358463243648**.
  Within the older-excerpt protocol, VA **0.3399893505844028**;
  within 2015 full songs, **0.18759773195542612**.
  The reference per axis and protocol is frozen in the evaluator.
  Baseline mismatches fail CI; no new labels or redefinition.

## Implemented paired evaluator

[`scripts/benchmark_deam.py`](../scripts/benchmark_deam.py)
has an optional `--embedding-dir` limited to the screened, stratified,
240-song cohort with seed `20261021`. Without that flag, the established
DEAM benchmark remains unchanged. With it, the **same encoder patch
pass** creates both classification heads and a separate 1280D
patchwise-mean, songwise-L2-normalized embedding sidecar.

[`scripts/evaluate_deam_embedding_ab.py`](../scripts/evaluate_deam_embedding_ab.py)
verifies compatible SQLite-v3 Genre/Mood vectors, patch counts,
audio SHA256, encoder/pooling fingerprints and registered archive
hashes. Each of the 240 anchors has the **same 239 candidates**.
Protocol-separated rerankings use 196 older-excerpt or 42 full-song
candidates per anchor, not pooled cross-protocol candidates.

Methods: direct 1280D cosine; Mood 56D cosine and centered cosine;
Genre 87D cosine and centered cosine (cross-task controls).
Human proximity targets are `-|Δvalence|`, `-|Δarousal|`, and
`-sqrt(Δvalence² + Δarousal²)`. Mean per-query
Spearman correlation compares each similarity ranking with
human VA-proximity rankings.

A method missing even one candidate score abstains for the
**whole anchor query**, contributing zero on the common 240-song
denominator; report coverage separately. Differences are
**embedding minus each head baseline**, using the same
deterministic protocol-stratified query resamples (800 pooled,
400 within protocol). The 95% quantiles are **descriptive sensitivity
ranges, not independent population confidence intervals**, because
candidate songs are shared.

[`research-deam-embedding-ab.yml`](../.github/workflows/research-deam-embedding-ab.yml)
uses the pinned Rust-v5 commit with a research-only 1280D overlay.
It keeps licensed original DEAM audio, labels and per-track
features on the ephemeral runner; exports only aggregated JSON.
Synthetic
[`tests/test_evaluate_deam_embedding_ab.py`](../tests/test_evaluate_deam_embedding_ab.py)
pass under Linux/Windows.

**Current blocker:** Official DEAM host
`cvml.unige.ch:443` did not accept HTTPS connections. The
preceding run independently reproduced the old Mood baseline but
was stopped by a sample-hash serialization mismatch, now fixed
with green Linux/Windows tests. The new end-to-end A/B result is
**not yet available**; the workflow now checks host connectivity
before costly Rust compilation. Do not report numerical
embedding-vs-Mood results until a full provenance-verified PASS.
See [DEAM research status](deam-similarity-benchmark.md).

## Separate local Lyrion listening evaluation

FMA coarse Genre, DEAM VA, and MTT odd-one-out are different
reference tasks, not direct verification of pleasant transitions
in the user's library.

The [bounded local listening plan](similarity-local-library-retest-plan-2026-10-21.md)
is preferred to an immediate 150–300-song full reanalysis.
Start with a read-only sample audit (L0), then a small ~12-contrast
instrument pilot, then a new independently held review block.
Only if appropriate, consider ~150–300 candidate songs for a
later richer randomized study with controlled coverage.

Future anchor/alternative-A/alternative-B comparisons should
hold candidate eligibility constant, balance blind presentations,
allow ties/neither, and separately rate (a) perceived mood/timbre
and (b) playlist transition suitability. Include repeated
controls for intra-rater stability, different artists/genres,
and hard A/B disagreements. Existing
[`queue_similarity_pairs_lyrion.ps1`](../scripts/queue_similarity_pairs_lyrion.ps1)
remains dry-run until the user explicitly authorizes local queue
changes; never upload local paths, addresses, player IDs or
song-feature vectors to GitHub.

Only compare **feature representation A/B/C** first.
The independent **candidate strategy** decision
(Bliss-first / feature-first / hybrid) comes later,
with a Bliss-only reference and its own experiment.
