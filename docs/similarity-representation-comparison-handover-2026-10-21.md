# Handover: Comparing three mathematical song-similarity representations

**Date:** October 21, 2026 · Draft PR #16,
`feat/similarity-metric-evaluation` only.
The [phase-0-to-6 roadmap](similarity-lyrion-roadmap.md)
is the current overall plan and **does not mark
experimental phase 0 as production-complete**.
This document focuses on contracts and reproducible
same-recording A/B/C comparisons.

## 0. Terms and decision layers

**A — Classifier-score similarity:** cosine and
related functions on independent 87D Genre / 56D
Mood/Theme Sigmoid-score vectors.

**B — Direct embedding similarity:** 1280D
Discogs-EffNet raw encoder representation,
pooled across patches in f64, songwise L2
normalized, compared with cosine.

**C — Combined score:** explicit fusion of
one or more A and B signals, only after
their score-scale/abstention contracts and
development-only calibration are defined.

**Do not conflate** A/B/C with the independent
Lyrion candidate-source strategies
**Bliss-first**, **feature-first** and
**hybrid candidate union**. All three
representation types can conceivably guide
the same candidate source.

Current code stores 87D/56D Genre/Mood heads
in a read-only-comparable schema-v3 feature
SQLite sidecar keyed by exact `TracksV2.File`,
with fingerprinted model and label ordering.
The shared 1280D encoder pass is already
internal to both heads, but a separate
**song-level** representation requires an
explicit research export; it does not
automatically appear in an existing local
feature database.

### Binding extension: default GENERAL metric first, user learning optional (2026-10-22)

The A/B/C comparison still chooses a **general-purpose similarity
representation and function independently of user-specific training**.
The resulting default must work with **no triplet history**.
A separately learned per-user metric may later contribute 0–100%
of the calibrated pairwise score; without a compatible, validated
personal model the effective blend is **100% general**, independent
of the stored slider setting.

`S_eff=(1-alpha)*S_general+alpha*S_personal`, with
`alpha=personal_blend/100` only for a usable per-user model
and explicitly commensurate score scales; otherwise
`alpha_effective=0`. Do not interpret the previous
MTT *triplet-local rank* fusion as a globally blended
Lyrion score. General fusion (C), personal blending,
and candidate-source strategies are **three distinct
layers**. The existing Lab `learned_blend` refers
to its 23D Bliss adaptation, not this new feature.

**Current measured local status:** the 100 original songs
have 100/100 compatible 87D, 56D and 1280D feature
representations with no invalid/missing sidecars. The
local blinded 12-pair instrument has been **generated**
but no new human votes/rating cells were submitted.
Thus neither general winner nor personalized lift
has been measured from it.

[Canonical general/personal decision](similarity-general-personal-blending-architecture.md).
The historical A/B/C results and numerical comparisons below
remain unchanged and unpersonalized.

## 1. Technical design of A vs B

The corrected Rust-v5 research checkout is
pinned at `2c3d44401436b3b41b6e067199016a1ed2335fbf`.
A runner-local overlay adds a versioned
1280D export without changing PR #17,
existing head normalization, or schema-v3.

For each audio file, the same FFmpeg/decoder,
sample-rate preprocessing, patch segmentation,
and EffNet encoder produce all feature
representations. Each 1280D component
is accumulated in f64 over raw patch
outputs. The song vector is the arithmetic
patch mean, L2-normalized once and serialized
as 1280 finite float32 components. A separate
JSON stores `schema_version`, exact source
track key, audio SHA256, encoder SHA256,
preprocessing version, patch count, pooling
version, normalization version, and
representation fingerprint.

A comparable classifier vector additionally
requires ordered classes, correct 87/56
dimension, model registry/head SHA and
aggregation identity; scores cannot be
interpreted as calibrated pairwise similarity
probabilities. A cross-head fusion must
not add raw cosine scores with unmatched
distributions without a declared scale
and missing-data policy.

Required parity checks before more ambitious
claims: direct ONNX patch-vs-pooled-song
equality, f64 mean/L2 contract, unchanged
Genre/Mood head vectors and SQLite records
with/without export, thread repeatability,
and representative reference Essentia C++
parity across diverse real audio. The
successful synthetic and single-song
checks do **not** by themselves satisfy
the last, broader parity requirement.

### CI implementation and reproducibility

The original research-export code lives
in [`research/song_embedding.rs`](../research/song_embedding.rs);
temporary pinned-checkout changes are applied
by [`apply_rust_v5_embedding_export.py`](../scripts/apply_rust_v5_embedding_export.py).
The MTT harness, pooled embedding evaluator,
four-worker process management and cached
1,019-clip subset are tested in
[`research-mtt-embedding-ab.yml`](../.github/workflows/research-mtt-embedding-ab.yml).
Source files, CRCs, model SHA256, patch counts
and output fingerprints are verified.
Run all Rust builds/benchmarks in GitHub
Actions, not by forcing an unplanned
local Windows Rust toolchain.

A past concurrency/parity smoke harness
failed because its glob matched both
`process-worker-N.json` and
`process-worker-heads-N.json`.
The strict filename regex fix passed
[Linux/Windows CI 39622478825](https://github.com/chrober/bliss-mood-poc/actions/runs/39622478825);
the concurrent synthetic parity gate passed
on the subsequent full workflow.
That earlier failure was not model
numeric non-parity.

## 2. Exact paired MTT research outcomes

The single completely explored MTT
human-triplet cohort has 346 unordered
questions, of which 293 have a unique
human majority and 53 tie; those questions
reference **1,019 unique clips**.
No MTT question remains as an untouched
holdout. Each method predicts the
odd clip from the *same* three pairwise
cosines and same majority votes.
Unpredicted questions count wrong on
the common 293 denominator.

Successful A/B
[run 39617159250](https://github.com/chrober/bliss-mood-poc/actions/runs/39617159250)
and independent synthetic pooling gate
[run 39618323154](https://github.com/chrober/bliss-mood-poc/actions/runs/39618323154)
measured:

| Method | Correct / 293 | Agreement |
| --- | ---: | ---: |
| B: 1280D mean-pooled embedding cosine | 182 | 62.116% |
| A: Genre cosine | 191 | 65.188% |
| A: Mood cosine | 192 | 65.529% |
| A: Genre centered cosine | 191 | 65.188% |
| A: Mood centered cosine | **193** | **65.870%** |

All have 293/293 coverage. Embedding-minus-Mood-centered
is **−3.754 percentage points**, naive paired 95%
question-resampling sensitivity **−9.215 to +1.365 pp**.
Questions reuse songs and artists; bootstrap
ranges are **not independent population CIs**.

## 3. Exact paired FMA VALIDATION research outcomes

The already-screened official FMA-Small
VALIDATION selection contains **80
artist-distinct songs**, ten per eight
coarse Genres, with 42 of the original
800 VALIDATION tracks excluded as possible
MTG catalogue artist/title matches before
selecting the frozen sample. The FMA
official **TEST remains unopened**.

Same 80 songs, 79 candidates per anchor,
nine same-Genre reference positives:
[run 39625087310](https://github.com/chrober/bliss-mood-poc/actions/runs/39625087310)
**PASS** and exact replay of the
pre-embedding Genre-Cosine baseline
P@5 **0.3200**.

| Method | Genre P@5 | mAP@10 | nDCG@10 |
| --- | ---: | ---: | ---: |
| B: 1280D embedding cosine | 0.2800 | 0.163044 | 0.282363 |
| A: Genre cosine | 0.3200 | 0.174876 | 0.298533 |
| A: Genre centered cosine | **0.3225** | **0.178147** | **0.304271** |
| Mood cosine (cross-task control) | 0.2775 | 0.150394 | 0.266065 |
| Mood centered cosine (cross-task control) | 0.2675 | 0.152847 | 0.270372 |

All five methods have 80/80 query
coverage. Embedding-minus-Genre-centered
P@5 **−4.25 pp**, shared Genre-stratified
95% query-resampling sensitivity
**−8.76 to +0.25 pp**. These are
small, dependent VALIDATION results,
not proof of universal significance
or a production metric winner.
Full cohort and source hashes:
[FMA A/B study](similarity-fma-embedding-ab-2026-10-21.md).

## 4. Fusion-C ablations: exploratory only

Four equal-weight, untrained
*triplet-local midrank* combinations were
added to the MTT evaluator after the
initial A/B measurement:
[run 39619708040](https://github.com/chrober/bliss-mood-poc/actions/runs/39619708040)
**PASS**.

| Fixed combination | Correct / 293 | Coverage |
| --- | ---: | ---: |
| Audio+Genre | 163 = 55.63% | 234/293 |
| Audio+Mood | 170 = 58.02% | 241/293 |
| Genre+Mood | 167 = 57.00% | 230/293 |
| Audio+Genre+Mood | 192 = 65.53% | 283/293 |
| Mood centered (unfused) | **193 = 65.87%** | 293/293 |

Several fusions produce tied
best-pair ranks, raising abstention
rates. No option improved the
Mood centered baseline on the common
denominator, but this is not a
general disproof of fusion.
Triplet-local ranks are not a
globally calibrated per-pair score.
Any globally usable calibrated
fusion and weights need **separate,
unseen development and evaluation**.
Details:
[fixed-rank fusion contract](similarity-fixed-rank-fusion-research-2026-10-21.md).

## 5. DEAM Mood/VA proxy, status and leakage limits

The separate DEAM filtered 240-song
sample (197 earlier excerpts and 43
full 2015 recordings) has a verified
pre-embedding Mood cosine mean-query
Spearman **0.286784551387186**
against human VA proximity.
The new A/B evaluator and provenance
checks were implemented; a serialization
mismatch between literal `\\n` and
actual linefeed in the frozen sample
fingerprint was fixed with
[Linux/Windows tests 39638092328](https://github.com/chrober/bliss-mood-poc/actions/runs/39638092328).
The later original data publisher
`cvml.unige.ch:443` was unreachable.
Therefore **no successful new 1280D
vs Mood-head DEAM score exists yet**.

Artist/title catalogue screening in
DEAM and FMA is only a partial check
for model-training overlap. The shared
Discogs encoder can have independent
recording overlaps. A nonmatch does
not prove independent testing.

MTT odd-one-out, FMA coarse Genre,
and DEAM VA evaluate different
reference properties. Never average
their percentages/correlations
or claim they directly validate
Lyrion playlist coherence.

## 6. Next controlled phases and release boundaries

- **N1:** Check original DEAM source
  availability or exact SHA/layout/
  licence of a replacement **before**
  new Rust builds or audio downloads.
- **N2:** Independently audit exact
  `TracksV2.File` keys and all
  87D/56D/1280D representations
  for a bounded sample of the user's
  **existing local library**. Do not
  overwrite feature databases.
- **N3:** If N1 passes, rerun
  DEAM-240 paired with identical
  sample SHA and 197/43 protocol strata.
- **N4:** Human listening:
  ~12 diagnostic contrasts, then
  a fresh, independent ~24–40-pair
  review block. Distinguish Genre,
  Mood, audible nearness and
  next-song suitability.
- **N5:** Select approach A, B or C
  only with paired review, clear
  coverage and independent evaluation;
  avoid tuning C on reviewed MTT/FMA.
- **N6:** Compare Lyrion candidate
  sourcing Bliss-only, Bliss-first,
  feature-first and hybrid **separately**
  from representation selection.

Keep the existing plugin, Mixer,
PR #13/#17 and `main` unchanged;
PR #16 stays Draft. No private
music files or per-track vectors
may be published as artifacts.
The current
[central roadmap](similarity-lyrion-roadmap.md)
defines the exact phase and stop/go
gates for further work.

## Reference documents

- [MTT embedding evidence](similarity-audio-embedding-ab-results-2026-10-21.md)
- [FMA paired study](similarity-fma-embedding-ab-2026-10-21.md)
- [DEAM source and paired-evaluation status](deam-similarity-benchmark.md)
- [Paired fixed-rank fusion](similarity-fixed-rank-fusion-research-2026-10-21.md)
- [Local listening review plan](similarity-local-library-retest-plan-2026-10-21.md)
- [Lyrion Bliss/feature candidate strategy](lyrion-bliss-mood-genre-integration.md)
