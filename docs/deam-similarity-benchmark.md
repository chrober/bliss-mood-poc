# Automated DEAM similarity benchmark — Draft PR #16

**Status:** experimental research workflow. No metric selected; no production
Lyrion/Bliss change; no user-library rescans. Research files and sidecars are
ephemeral on a GitHub-hosted runner, never committed or uploaded.

## Why DEAM first?

[DEAM](https://cvml.unige.ch/databases/DEAM/) provides human annotated
song-level valence (positive ↔ negative affect) and arousal
(calm ↔ energetic) and corresponding audio excerpts/full songs.
The [official manual](https://cvml.unige.ch/databases/DEAM/manual.pdf)
describes approximately 1,802 recordings, 2014/2015 subsets, average
static labels on a **1..9** scale, and a **CC BY-NC** data license.
Annotations from multiple years have differing collection protocols;
static song-level means are available, but Arousal annotations were reported
as more reliable than Valence in some original subsets.

**External validation is not automatically held out.** DEAM includes Jamendo
material, and our classifiers were trained on MTG-Jamendo data. Before making
an out-of-domain or independence claim, cross-match track IDs/metadata and
remove potential training overlaps. DEAM Valence/Arousal proximity is a
*proxy* for similarity, **not direct human pairwise genre or mood agreement**.
Genre-vs.-VA correlations are diagnostic controls only, **not Genre accuracy**.

## Actual implementation

- [scripts/benchmark_deam.py](../scripts/benchmark_deam.py):
  - consumes **official** DEAM ZIP files only;
  - looks up average static annotation rows by numeric song ID;
  - matches numeric MP3 filenames inside the ZIP by exact numeric ID;
  - selects a deterministic subset from the common IDs via seed;
  - extracts **one MP3 at a time** to bound scratch space;
  - invokes the existing Rust CLI **analyze-features** with both independent
    87D Genre and 56D Mood/Theme heads, storing a *new* schema-v3 sidecar;
  - uses the existing seven similarity algorithms without redefining them;
  - compares song-level Valence-only, Arousal-only and joint VA rankings via
    macro-average query Spearman, with exploratory query-bootstrap intervals;
  - checks model cohort fingerprints and Rust-v5 preprocessing identity;
  - refuses to overwrite prior sidecars or reports and fails if vectors
    are missing or annotation IDs conflict.
- [tests/test_benchmark_deam.py](../tests/test_benchmark_deam.py):
  synthetic archives/labels/feature sidecars, deterministic sampling,
  tie handling, corruption/missing-data behavior and read-only evaluation
  on Linux and Windows CI.
- [.github/workflows/deam-benchmark.yml](../.github/workflows/deam-benchmark.yml):
  builds the **pinned corrected Rust-v5 analyzer from an independent checkout**
  at PR #17 commit `2c3d44401436b3b41b6e067199016a1ed2335fbf`
  on **ubuntu-24.04** with FFmpeg, using that source's tracked Cargo.lock.
  PR #17 is not merged. Fetches official Essentia
  ONNX models + metadata, downloads the **official** DEAM audio/annotations,
  invokes the benchmark and uploads **only** the aggregate JSON.
  A one-time small **12-song smoke** is triggered when the workflow file
  changes on the feature branch; later research runs are on-demand via
  workflow_dispatch. Note: GitHub's workflow_dispatch GUI/API normally
  requires the workflow file on the repository's default branch; while this
  remains a Draft PR, use the branch smoke run for initial evidence and do
  not merge to enable dispatch without explicit authorization.

### Report schema and interpretation

- schema: deam-similarity-benchmark-v1
- source/rights, song count, seed and SHA-256 of audio/annotation archives
- cohort keys and preprocessing fingerprints
- per Head → Metric → reference axis:
  - query_count
  - mean_query_spearman
  - exploratory query_bootstrap_95pct
- queries_insufficient_defined_scores records lack of defined scores
  (especially relevant for historical fixed-cutoff Top-K).

The report contains **no** decoded audio, metadata rows, artist names,
identifying track IDs, original human annotations or feature vectors.

A 12-song smoke test is strictly for verifying download, Rust inference,
feature sidecar, reference matching and reporting. It must not be used
to choose a metric. Query scores share candidate songs, so the bootstrap
intervals are descriptive, not independent-sample inference.
Larger experiments will need stratified, artist-aware splits, DEAM year
cohorts, training-overlap audit, held-out data and better uncertainty
handling. In particular DEAM VA annotations do not establish an absolute
probability that two songs are similarly perceived.

### Licensing and distribution

The official DEAM **CC BY-NC** terms must be respected and cited. Audio,
metadata/annotation ZIPs, generated SQLite sidecar and model binaries
remain ephemeral runner inputs. We do not cache, check in or upload these
as public GitHub artifacts. The workflow publishes only an aggregate
research summary (14-day retention). Before broader or commercial use,
check the license of each input and code/dependency separately.

### Workflow execution and reproducibility

The initial branch benchmark downloads up to ~1.3 GB DEAM audio even for a
12-song sample because the source publishes a single archive. It avoids
extracting the whole archive at once. The 14 GiB standard-runner SSD limits
data scale; 1,802 full-song analyses may require partitions/jobs and
artifact persistence policy. This first stage has no FMA integration.

Archive hashes, model fingerprint/versions, Rust branch/commit, and
deterministic sample seed should be compared between runs. PR #16 still has no Cargo.lock; the DEAM workflow uses an explicitly
pinned second checkout of the verified Rust-v5 implementation including
its tracked lockfile, built with cargo build --release --locked.
This avoids relabeling a v4 implementation or merging PR #17.
Do **not** claim bit-identical builds without runtime validation.

## Planned next gates

1. Pass ordinary synthetic CI tests on both Linux and Windows.
2. Complete the real DEAM 12-song end-to-end CI smoke, inspect concrete
   runner logs, and fix any legitimate source/archive/CLI mismatch.
3. Freeze a larger research sample and collect descriptive head/metric
   results on VA axes, avoiding an arbitrary winner.
4. Audit overlap with MTG-Jamendo and dataset-level partitions.
5. Extend the same manifest/evaluation infrastructure to FMA Genre labels;
   then test general musical similarity on direct human pairwise/triplet
   evidence before any Lyrion-mixer recommendation.

PR #16 is Draft; PR #13, PR #17 and main remain outside scope.

### Observed version-safety smoke gates

- First actual run: cargo build --locked failed before any download,
  because the PR #16 source tree has no Cargo.lock. This verified
  fail-closed behavior, not a DEAM dataset failure.
- Second actual run: downloaded official annotations and audio;
  matched **1,802** audio/annotation IDs; processed **12** songs with
  the source PR #16 analyzer. Final validation **correctly rejected**
  this sidecar: src/features.rs still identifies **v4** preprocessing.
- The workflow is now revised to check out the frozen PR #17 commit
  2c3d44401436b3b41b6e067199016a1ed2335fbf in its **own**
  separate directory and build the default Rust/ONNX backend. It checks
  for the actual v5 preprocessing fingerprint and cannot silently
  accept v4. Using this exact source revision is a **build dependency**
  for DEAM research only; PR #17 is not merged or edited.

### Confirmed first corrected Rust-v5 end-to-end benchmark (21.10.2026)

**PASS**, GitHub Actions run
[39576010217](https://github.com/chrober/bliss-mood-poc/actions/runs/39576010217).
The runner checked out the immutable corrected Rust-v5 source commit
2c3d44401436b3b41b6e067199016a1ed2335fbf in a second directory,
used that source's Cargo.lock, built it, downloaded the official models
and DEAM archives, verified **1,802 audio/annotation ID matches**, inferred
both heads for **12 seeded tracks**, evaluated all seven existing similarity
metrics, and published only aggregate JSON in
[artifact 12333973414](https://github.com/chrober/bliss-mood-poc/actions/runs/39576010217/artifacts/12333973414).

As a **smoke observation only**, the macro mean query Spearman of similarity
against joint human Valence/Arousal proximity among these twelve tracks was:

| Metric | Genre head vs. VA proxy | Mood head vs. VA proxy |
| --- | ---: | ---: |
| RMS | 0.325 | 0.301 |
| Cosine | 0.425 | 0.308 |
| Centered cosine | 0.417 | 0.280 |
| Weighted Jaccard | 0.348 | 0.252 |
| Historical cutoff Top-K | 0.360 | 0.387 (only 6 valid queries) |
| Ranked Top-6 | 0.390 | 0.474 |
| Ranked Top-12 | 0.353 | 0.345 |

Do **not** select Top-6 from this table: N=12 is far too small;
the Genre head is not being tested on genre labels; the old Top-K
samples only half the anchor queries; no independent-data or
cross-dataset guarantee has been established. These are not ROC-AUC
values and not calibrated probability estimates.

**Next science gate:** increase the dataset size and test reference
alignment, annotation quality, year splits, and artist/train-set
overlap before any metric choice. Add a dedicated *Genre*-label
benchmark (FMA) rather than interpreting Genre vs. Valence/Arousal
as Genre-retrieval quality.

The real DEAM workflow and standard synthetic Rust/Python CI tests
completed successfully on the changes tested. No production changes.


## Follow-up: 240-track collection-aware DEAM benchmark (21.10.2026)

The first 12-track end-to-end smoke PASSED. The next benchmark run uses
**240 deterministic songs** with --stratify-cohorts. Selection records a
SHA-256 digest of the selected ordered DEAM IDs (never exports the IDs).
A seeded sampler deliberately oversamples the small 2015 full-song group
at 20% of the requested sample, subject to the available 58 examples:
for N=240, **192 earlier excerpts + 48 2015 full songs**.

The official DEAM manual explains that the historical collections differ
in audio scope and annotation protocol. We therefore report:
- an all-query pooled VA-proximity benchmark (a **heterogeneous, exploratory**
  indicator, NOT a final score);
- an earlier-excerpt-only benchmark (same within-protocol candidates);
- a 2015-full-song-only benchmark (same within-protocol candidates).

For each group, we report query-macro Spearman per Genre/Mood head and each
of seven metrics, separately for Valence, Arousal and VA Euclidean proximity,
plus valid/undefined query counts and descriptive query-bootstrap bands.
The comparison is **not weighted to restore real DEAM prevalence**, and the
two groups are never interpreted as independent replicas or as direct
genre/playlist quality.

The first 240-track branch run is triggered by the workflow-file change,
because workflow_dispatch normally requires the workflow to also exist
on the default branch. The workflow remains PR #16-only; it is NOT
merged to main solely to enable a manual dispatch. It downloads the
DEAM metadata.zip for inventory and logs its **CSV header names only**
(no title/artist/track values). This is preparatory work for the
Jamendo-training-overlap audit, **not the audit itself**.

**Data leakage status explicitly set to train_overlap_check: not_performed.**
DEAM includes material originally obtained from Jamendo, FMA, and MedleyDB,
and our ONNX heads were trained on MTG-Jamendo. Therefore we must NOT
call these correlations fully independent external validation until a
credible source/track/artist overlap exclusion has been performed.
The license remains DEAM CC BY-NC; no music or per-track features are
committed or uploaded.

These additions are tested with synthetic fixture archives, 2015/older
ID ranges, deterministic sampling, immutable SQLite assertions, and
aggregate-only, cohort-separated reports on Linux and Windows CI.
No metric selection is made from the 240-song run regardless of its scores.


## Results: 240-song stratified DEAM end-to-end run (21 October 2026)

**PASS**, GitHub Actions
[run 39577605466](https://github.com/chrober/bliss-mood-poc/actions/runs/39577605466)
on code revision b8e7486e8871ee5c245b0c11334bafdf4d8387fb;
[aggregate-only report artifact 12335725900](https://github.com/chrober/bliss-mood-poc/actions/runs/39577605466/artifacts/12335725900).

The official DEAM archive matched 1,802 annotation/audio IDs;
the frozen seed 20261021 selected and analyzed **240** using the
pinned corrected Rust-v5 analyzer and **no** user audio or local build:
192 earlier excerpts and 48 full-song 2015 examples. DEAM metadata.zip
was inspected without printing artist/title values; it has distinct
2013/2014/2015 files and schemas:
- metadata_2013.csv: song_id, Artist, Song title, etc.
- metadata_2014.csv: Id, Artist, Album, Track, etc.
- metadata_2015.csv: id, Filename, title, artist, album, etc.

Mean per-query Spearman of similarity score vs **human VA Euclidean proximity**
(higher means stronger monotonic association):

| Metric | Genre head vs VA (not a Genre test) | Mood head vs VA |
| --- | ---: | ---: |
| RMS | 0.0857 | 0.2277 |
| Cosine | 0.1009 | 0.2421 |
| Centered cosine | 0.0999 | 0.2471 |
| Weighted Jaccard | 0.1052 | 0.2507 |
| Historical cutoff Top-K | 0.0925 (240 queries) | 0.1558 (218 queries) |
| Ranked Top-6 | 0.0885 | 0.2250 |
| Ranked Top-12 | 0.0969 | 0.2351 |

Within-cohort Mood Cosine vs VA proximity:
- earlier excerpts (192 songs): **0.2689**
- 2015 full songs (48 songs): **0.3044**

The pooled results are a heterogeneous, deliberately 2015-oversampled
sample, so the overall table is **not a prevalence-weighted estimate**.
Cohort-specific candidate pools/annotation protocols differ. These
are **not ROC-AUC**, and a small score difference does not establish
statistical superiority. In particular, the twelve-song result that
favored ranked Top-6 did not generalize as the highest scorer in this
larger run. **Do not select any metric from these numbers.**

The aggregate report explicitly states that **MTG-Jamendo training
overlap is not yet audited**. Training overlap may still be present;
artist/track metadata matching and separate held-out evaluation are
required. Genre VA correlation does NOT validate Genre retrieval.
The benchmark passed the CI workflow, but does **not** establish
playlist quality or deployment readiness.

Next research gates: read-only DEAM metadata to MTG-Jamendo overlap
screening without publicly exposing individual metadata; an independent
FMA-Small Genre retrieval evaluation, designed separately at
[docs/fma-genre-benchmark-plan.md](fma-genre-benchmark-plan.md).


## Conservative DEAM/MTG overlap screening and filtered rerun (21 Oct 2026)

The first **metadata-only** GitHub Actions
[run 39579084649](https://github.com/chrober/bliss-mood-poc/actions/runs/39579084649)
completed successfully. It downloaded only DEAM metadata.zip and the
official MTG-Jamendo raw.meta.tsv (no audio), parsed actual 2013/2014/2015
DEAM CSV formats, and compared artist+track title after unicode NFKD
accent folding, case folding and punctuation normalization.
The [aggregate artifact 12335402582](https://github.com/chrober/bliss-mood-poc/actions/runs/39579084649/artifacts/12335402582)
contains no individual artist, title or track key.

- DEAM: **1,801 of 1,802** songs with usable artist/title data.
- MTG-Jamendo: **56,552** catalog metadata rows.
- Potential exact-artist/title catalog overlap candidates:
  **60 earlier excerpts + 15 full-song 2015 = 75**.

These are **possible catalog matches**, not a verified model-training
split match, and titles/artist strings can be inexact or reused.
A nonmatch cannot prove independent audio or unseen artists.
We therefore cannot yet claim that the DEAM pilot is a truly
train-independent external test. This audit is part of the study's
provenance record, not a metric-validation result.

[scripts/audit_deam_mtg_overlap.py](../scripts/audit_deam_mtg_overlap.py)
implements the conservative, metadata-only screening, with synthetic
Linux/Windows CI tests and strict no-personal-data aggregate reports.
[.github/workflows/deam-mtg-overlap-audit.yml](../.github/workflows/deam-mtg-overlap-audit.yml)
can run it separately without downloading media/models.

The DEAM benchmark now has an opt-in
--exclude-mtg-catalog-matches flag plus required --deam-metadata-zip and
--mtg-metadata-tsv paths. It rejects insufficient metadata coverage
before processing any song, removes all exact candidates from the
available sampling pool, then evaluates a **new** frozen seed sample.
The new report records only counts, hashes and the explicit status
partial_catalog_exact_artist_title_exclusion_NOT_verified_training_disjointness.
The original unfiltered 240-song run and report remain untouched.

An exclusion-filtered 240-track E2E GitHub Actions run was started by
[workflow update 374514d](https://github.com/chrober/bliss-mood-poc/commit/374514debe47564a70f0b57db52140dbae47cabe).
Check the actual run outcome before reporting any filtered metrics.
The 2015 cohort is limited to at most **43** filtered full songs
from the originally available 58; with N=240 this gives an expected
197 older excerpts and 43 full songs, subject to real log verification.

Next: assess the filtered aggregate results and independent
[planned FMA genre benchmark](fma-genre-benchmark-plan.md).
No metric winner, PR merge or local Rust build is justified.
