# FMA-Small / MTG-Jamendo catalog overlap: development-only screen

**Date:** 2026-10-21 · **Branch:** `feat/similarity-metric-evaluation`
· **PR:** Draft #16; no merge to `main`.

## Question and interpretation

The original 80-song FMA-Small Genre **VALIDATION** study used
a separately provided public label/reference dataset. However,
the 87-class Genre ONNX classifier was originally trained on
MTG-Jamendo tags, and some catalog entries across these public
collections may coincide. To limit this risk without exposing
the official FMA TEST labels, run a conservative metadata screen
on the FMA **training** and **validation** partitions, comparing
normalized artist+track names to the **public MTG-Jamendo
raw metadata catalog**. The original Discogs encoder also has
independent training provenance that this screen does NOT address.

**IMPORTANT:** FMA's own `training` split is **not** the
MTG-Jamendo model's training set. Matching the broader MTG
catalog is NOT proof of identity of the underlying audio
recording, membership in the actual ONNX classifier's
training split, or encoder-data contamination; non-matches
cannot prove the absence of such reuse either.

## Verified audit, without any music data

[GitHub Actions run 39605675932](https://github.com/chrober/bliss-mood-poc/actions/runs/39605675932)
**PASS**, [aggregate-only result artifact
12347897819](https://github.com/chrober/bliss-mood-poc/actions/runs/39605675932/artifacts/12347897819).

| Official FMA-Small partition | Songs | Joinable artist+title | Possible exact artist+title matches | Possible artist-only matches |
| --- | ---: | ---: | ---: | ---: |
| Training | 6,400 | 6,396 | **121** | 260 |
| Validation | 800 | 799 | **42** | 68 |

All 800 official TEST rows were counted **only for split-size
verification**. No TEST artist, title, top-level genre,
recording or classifier output was inspected or scored. The
FMA training/validation artist-ID sets were disjoint (zero
overlap). MTG raw metadata: 56,552 catalog rows,
55,454 distinct normalized artist/title pairs.

Within the 800-song FMA **VALIDATION** partition:

| Coarse FMA top-level genre | Eligible validation tracks | Exact MTG catalog match candidates |
| --- | ---: | ---: |
| Electronic | 100 | 0 |
| Experimental | 100 | 0 |
| Folk | 100 | 1 |
| Hip-Hop | 100 | **35** |
| Instrumental | 100 | 0 |
| International | 100 | 3 |
| Pop | 100 | 0 |
| Rock | 100 | 3 |

The **42/800 = 5.25%** exact-catalog-match proportion overall
masks a highly nonuniform genre risk: **35/100** Hip-Hop
validation songs matched artist+title fields. A naive
80-song balanced sample might inherit some of that risk;
the old 80-song run was not retroactively audited track
by track and cannot be called proven disjoint.

Audit implementation:
[scripts/audit_fma_mtg_overlap.py](../scripts/audit_fma_mtg_overlap.py)
and offline tests
[tests/test_audit_fma_mtg_overlap.py](../tests/test_audit_fma_mtg_overlap.py).
It reuses the established NFKD accent-folded,
case-insensitive, punctuation-normalized artist/title
comparison from the DEAM/MTG audit. It publishes
**counts by FMA development split and coarse genre**, input
SHA-256 hashes, warnings and method/schema, never source
artist/title values, filenames, track IDs, audio or embeddings.
The metadata audit itself took **8.84 s**
(excluding official ZIP/TSV transfer), peaking around
**39,908 KiB RSS**.

## Filtered, still exploratory VALIDATION study

The FMA research CLI now accepts:
`--exclude-mtg-catalog-matches --mtg-metadata-tsv PATH`,
**only with** `--split validation`. Before choosing
the balanced 10-per-genre / 80-song validation cohort,
the script removes songs with a normalized exact
artist+title match against the MTG raw catalog;
it records only a count, input hash and provenance
limitations. It prevents any official TEST song from
being parsed beyond its split field in this discovery
workflow. The ordinary unfiltered benchmark remains
available and unchanged as a historical research record.

New dedicated [catalog-screened FMA validation workflow](../.github/workflows/fma-genre-filtered-validation.yml)
runs Python fixture tests and source-metadata screening **before
downloading the 7.2-GiB audio ZIP**. It uses the already
verified **source-commit-pinned Rust-v5 executable cache**, falling
back to `cargo build --release --locked` on a miss; the original
public FMA audio ZIP is **not** uploaded or implicitly copied
into GitHub Actions cache. Other model/version and
similarity metric semantics are unchanged. All FMA
per-song vectors, identities and genre labels stay
temporary on the runner.

The filtered run's output must **not** be numerically paired
to the old 80-song study: the available sampling pool
changed and the deterministic RNG produces a different
cohort. A difference in score cannot causally be
attributed to metadata exclusions or improvement in
model generalization. Reference labels remain *coarse
genre*, not general perceived song similarity.
The official FMA TEST split is still reserved for later,
predeclared independent confirmation.

The first filtered workflow attempt
[39606671003](https://github.com/chrober/bliss-mood-poc/actions/runs/39606671003)
stopped at a **synthetic** TEST-row fixture: the loader
parsed a deliberately malformed TEST track ID before
skipping the partition. This was fixed by inspecting
the official split **first** and skipping TEST rows
before reading IDs, genres, artists or titles. Linux/
Windows Python tests
[39606799883](https://github.com/chrober/bliss-mood-poc/actions/runs/39606799883)
**PASS**. The corrected filtered real validation workflow
[39606850307](https://github.com/chrober/bliss-mood-poc/actions/runs/39606850307)
was triggered. Verify its completion and aggregate
artifact before claiming any post-exclusion retrieval
quality or benchmark speedup.

## Next scientifically useful steps

1. Confirm the filtered FMA Genre validation artifact
   and verify all 80 analyzed tracks are disjoint artists,
   all seven metrics are present and all 42 matched
   catalog candidates were excluded before inference.
2. Compare filtered/unfiltered *descriptively* and
   explicitly disclose different sampled tracks.
   If a controlled effect estimate is desired, run the
   very same original 80-song cohort with **only
   matched candidates removed/replaced** under a frozen,
   predeclared design, not a post-hoc difference of two
   convenience samples.
3. Audit exact **classifier training split** provenance
   and potential Discogs-encoder overlap if data exist;
   never equate a raw catalog match with training exposure.
4. Freeze a final evaluation protocol before opening
   FMA official TEST. Do not use TEST labels, retrieval
   metrics or artist/title values for exploratory tuning.
5. Confirm perceived playlist/transition coherence
   separately via legitimate held-out listening evidence.

No main merge, production similarity setting,
Lyrion user-library scan, or changes to PR #13/#17.


## Verified filtered 80-song FMA Genre retrieval run

**PASS**: [GitHub Actions 39606850307](https://github.com/chrober/bliss-mood-poc/actions/runs/39606850307),
[aggregate-only artifact 12349595666](https://github.com/chrober/bliss-mood-poc/actions/runs/39606850307/artifacts/12349595666).
Official FMA-Small audio archive/metadata and canonical ONNX
encoder/Genre head were used. The early metadata screen confirmed
the **42** exact artist/title catalog candidates among **800
official VALIDATION songs**, leaving **758** possible candidates.
After indexing FMA-Small audio, size checking and artist-distinct
balanced seeded sampling, **80 distinct-artist VALIDATION
recordings** (10 of each of eight top-level genres) were analyzed
with the immutable verified Rust-v5 analyzer. Official TEST
audio, genres, artists, titles and identifiers were NOT evaluated.

| Metric | Previous unfiltered Validation P@5 | Filtered Validation P@5 | Filtered mAP@10 | Filtered nDCG@10 |
| --- | ---: | ---: | ---: | ---: |
| RMS | 0.3175 | 0.3000 | 0.1624 | 0.2819 |
| Cosine | 0.3500 | 0.3200 | 0.1749 | 0.2985 |
| Centered Cosine | 0.3525 | **0.3225** | **0.1781** | 0.3043 |
| Weighted Jaccard | 0.3550 | 0.3000 | 0.1719 | 0.2933 |
| Historical cutoff Top-K | 0.3150 | 0.3025 | 0.1719 | 0.3014 |
| Ranked Top-6 | 0.3150 | 0.3125 | 0.1752 | **0.3048** |
| Ranked Top-12 | 0.3400 | 0.3050 | 0.1740 | 0.3000 |

The balanced cohort's expected random P@5 baseline is
**9/79 = 0.113924**. All seven FMA filtered retrieval
metrics reported **80 queries**. These are **different
validation samples**, not paired repeated-measures experiments.
For example, the 0.3525 → 0.3225 Centered Cosine difference
is NOT evidence that excluding training-overlap candidates
reduced model quality or revealed a 3-percentage-point
optimism bias. The source catalog match itself does not
prove model training exposure.

**Measured GH Actions evidence:** The Rust-v5 executable
cache was a true HIT; the Rust toolchain and release build
steps were skipped. The canonical FMA metadata was
screened before downloading ~7.2-GiB original FMA-Small
audio. The workflow logged the audio-archive completion
around 13:22:48 UTC and the final metrics at 13:23:49 UTC.
The full audio inference used serial `--threads 1`,
not adaptive or multi-worker mode. No FMA audio
was committed, uploaded or stored in a cache.

Next: if additional effort on FMA is justified,
use a **larger frozen, artist-aware validation cohort**
and paired query-level metric comparisons, with genre
stratification and explicit Top-K abstention coverage.
Maintain the TEST embargo until evaluation rules
are frozen. For stronger independence from classifier
training data, audit the actual model training split
and Discogs encoder corpus where possible.
