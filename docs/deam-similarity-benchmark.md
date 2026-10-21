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
