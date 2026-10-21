# Planned FMA genre-retrieval benchmark — Draft PR #16

**Status:** design only; not yet an implemented, executed or validated
GitHub Actions genre benchmark. The reproducible DEAM research pipeline
must be assessed before expensive FMA audio downloads. No production
similarity metric or mixer decision is made here.

## Data and provenance

Official source: https://github.com/mdeff/fma
ISMiR 2017: Defferrard, Benzi, Vandergheynst, Bresson,
FMA: A Dataset For Music Analysis.

The official FMA-Small collection comprises **8,000 30-second MP3
excerpts** with a **balanced eight-class top-level genre taxonomy**;
the ZIP is **7.2 GiB**. The official metadata archive is about
**342 MiB** and supplies tracks.csv, with track IDs, song/artist
information, subset membership, train/validation/test assignment,
top-level genres and further fields.

The music and metadata have per-track Creative Commons licensing
considerations. Audio is not relicensed by appearing in FMA. Download
from the canonical FMA source, verify available SHA checksums and
permissions; never commit, distribute or upload recordings and never
upload a catalog of personal/private music.

## Evaluation contract

Evaluate the **Genre 87-D head** on independent human/editor-supplied
FMA top-level genres. The 56-D Mood head may be included only as an
informative control; FMA genre labels are NOT Mood ground truth.

1. Obtain and freeze an artist-aware sample of the official FMA-Small
   subset. Preserve the official split annotations. Inspect the official
   metadata and split semantics before implementation.
2. Resolve exact numeric track IDs and MP3 archive members in a fail-closed
   importer. Stream/extract one recording at a time to avoid exceeding
   GitHub-hosted runner scratch capacity (the full ZIP cannot safely
   be extracted alongside the original archive).
3. Build the existing pinned, numerically validated Rust-v5 ONNX analyzer
   via GitHub Actions, with a separate checkout; do NOT merge PR #17.
   Persist only an ephemeral benchmark-specific schema-v3 SQLite sidecar.
4. For each query, rank all eligible different-artist candidates separately
   under all seven existing similarity metrics. Report per-class counts,
   candidates with undefined scores, Precision@K, nDCG@K and macro mAP@K.
   Do not count undefined historical Top-K similarities as zeros without
   explicitly documenting that policy. Compare to uniform and
   label-frequency baselines.
5. **Development versus holdout:** choose any hyperparameters,
   ranking policy and threshold in the *development partition* only.
   Reserve a frozen artist-disjoint official test partition for an
   unbiased final comparison. Keep nested sampling and same-artist
   duplicate recordings out of evaluation candidates.
6. Report uncertainty using artist-/query-grouped resampling and
   paired comparisons; all pair scores sharing one artist/query are
   not statistically independent. A single genre label is a coarse
   indicator of music similarity, not direct human pairwise preference.
7. Publish only aggregate JSON/Markdown tables, model/data hashes,
   run/commit IDs, sample size, split counts and methodology. Do not
   publish raw audio, per-track vectors, per-track metadata, or user data.

## GitHub Actions design

- CI unit tests with synthetic multi-row FMA tracks.csv metadata and
  small artificial MP3 ZIPs, no external downloads.
- Optional on-demand research workflow and a small branch-scoped smoke
  before a larger run.
- Limit runner disk use: download FMA-Small ZIP once, stream a bounded
  deterministic sample and remove temporary extracted MP3s.
- Pin the FMA metadata release, model/checksum, Rust-v5 commit and
  sampling seed. Store an output fingerprint for the frozen cohort,
  not its private per-track records.
- Guard against reusing the genre-training labels as evaluation labels
  for the same model; compare to the original MTG-Jamendo genre training
  provenance and explicitly audit plausible cross-dataset duplicates.

## Evidence hierarchy

- DEAM: subjective **Valence/Arousal distance proxy** for Mood.
- FMA-Small: independent **coarse genre-label retrieval** evidence.
- MagnaTagATune/other pairwise or triplet assessments: direct, broader
  human *music similarity* judgments.
- Lyrion playback: final separate listening validation of actual
  playlist coherence and transition quality.

None of the above individually establishes a production similarity
probability. Respect the research-only, Draft-PR scope.


## Implementation and proven metadata preflight (21 October 2026)

The metadata-only GitHub Actions
[run 39580107275](https://github.com/chrober/bliss-mood-poc/actions/runs/39580107275)
**passed** with canonical FMA archives: FMA-Small has 8,000 tracks,
exactly 1,000 in each of the eight top-level genres Electronic,
Experimental, Folk, Hip-Hop, Instrumental, International, Pop and Rock.
Official split sizes: training 6,400; validation 800; test 800.
Artist-ID overlaps across training, validation, test: **zero**.

New research-only files on PR #16:
- scripts/audit_fma_metadata.py and tests/test_audit_fma_metadata.py,
  used in .github/workflows/fma-metadata-audit.yml (PASSED).
- scripts/benchmark_fma_genre.py and tests/test_benchmark_fma_genre.py.
  Reads official two-row CSV metadata, streams selected ZIP members
  without full extraction, samples **ten distinct artists per genre**
  from **official VALIDATION only** (80 tracks), analyzes the 87-D
  Genre head with pinned corrected Rust-v5, compares all seven methods
  against coarse FMA top-level genres and outputs aggregate P@5,
  mAP@10, nDCG@10, query/abstention coverage and a random baseline.
- .github/workflows/fma-genre-benchmark.yml builds the pinned v5
  analyzer in a separate checkout, downloads official model files,
  canonical metadata and FMA-Small archives (7.2 GiB), extracts one
  MP3 at a time, uploads aggregate JSON only.

Top-K scores with no positive class overlap explicitly **abstain**;
they are NOT silently assigned an alphabetically first neighbor.
The initial workflow smoke failed a synthetic test assertion that had
mistakenly required Top-K to return a defined retrieval score even
when every query abstained; corrected tests now pass on both Linux
and Windows. The validation-only workflow was retriggered in
[run 39581435733](https://github.com/chrober/bliss-mood-poc/actions/runs/39581435733).
Check its actual result: do not claim real FMA-Audio benchmark success
without the aggregate artifact and completed Rust-v5 inference.

The **official TEST split is not used** by this exploratory run.
No best production metric or final generalization claim is valid.
All input audio, per-track artist/genre labels and vectors stay
on the ephemeral Actions runner.
