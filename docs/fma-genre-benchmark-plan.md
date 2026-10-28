# Planned FMA genre-retrieval benchmark — Draft PR #16

**Status (21 Oct 2026):** metadata-only CI preflight PASSED;
the first real audio validation run failed on three anomalous MP3 sizes.
The bounded archive-quality fix was tested; the corrected full
**80-song validation-only** Rust-v5 Genre retrieval workflow
[39583233757](https://github.com/chrober/bliss-mood-poc/actions/runs/39583233757)
then **PASSED**, with an aggregate-only report. No production metric or
mixer decision is made here; the official TEST split remains untouched.

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


## Confirmed corrected first FMA-Small Genre retrieval result (21 Oct 2026)

[Successful Actions run 39583233757](https://github.com/chrober/bliss-mood-poc/actions/runs/39583233757);
[aggregate-only artifact 12338242831](https://github.com/chrober/bliss-mood-poc/actions/runs/39583233757/artifacts/12338242831).

The canonical FMA-Small ZIP contained 8,002 archive members
(including directories). Exactly **3 anomalous-size MP3s** were
excluded; **7,997** accepted archive tracks remained. Fixed seed
20261021 selected **80 artist-distinct Validation songs (10 per
top-level genre)**. The pinned corrected Rust-v5 source revision
2c3d44401436b3b41b6e067199016a1ed2335fbf analyzed 80/80
selected MP3s. The off-limits official **FMA TEST** split was never
used.

| Metric | Precision@5 | mAP@10 | nDCG@10 |
| --- | ---: | ---: | ---: |
| RMS | 0.3175 | 0.2064 | 0.3298 |
| Cosine | 0.3500 | 0.2353 | 0.3509 |
| Centered Cosine | 0.3525 | 0.2400 | 0.3554 |
| Weighted Jaccard | 0.3550 | 0.2332 | 0.3415 |
| Historical cutoff Top-K | 0.3150 | 0.2233 | 0.3304 |
| Ranked Top-6 | 0.3150 | 0.2249 | 0.3350 |
| Ranked Top-12 | 0.3400 | 0.2291 | 0.3369 |

The balanced-cohort **random Precision@5 expectation** is
9 / 79 = **0.113924** (9 relevant same-genre neighbors among
79 distinct-artist candidates).

**Interpretation limits:** Each song has coarse genre labels, not
direct human musical similarity preferences. Selected validation
artists are unique and official FMA splits are artist-ID-disjoint,
but the model's MTG-Jamendo training catalog has not been fully
audited against FMA audio/artist data. No development/test
hyperparameter choice or independent held-out TEST score is
claimed. Top-K overlap-abstention policies can alter the candidate
pool, so comparisons should be paired and report coverage in
future larger samples. Differences around 0.002--0.005 P@5 are
too small for a defensible winner on just 80 tracks.

**Observed workflow timing:** the Runner reported 4 CPUs;
canonical archive download began at ~10:17:21 UTC and ended
at 10:21:00 UTC, ~3 min 39 sec. The 80 individual-song
Rust-v5 subprocesses were logged by ~10:21:50 UTC, with the final
metrics at ~10:21:58 UTC. This stage was **serial** with
--threads 1 and no adaptive workers. For such small cohorts,
network, setup and Rust build time dominate; parallel audio
analysis should be A/B tested on identical inputs before enabling
it. No measured speedup exists yet.

Workflow maintenance and trigger caveats are detailed in
[GitHub Actions audit](github-actions-trigger-and-worker-audit-2026-10-21.md).


## FMA validation provenance clarification and catalog-screened rerun

The dedicated metadata-only
[FMA–MTG screen 39605675932](https://github.com/chrober/bliss-mood-poc/actions/runs/39605675932)
**PASS** (aggregate [artifact 12347897819](https://github.com/chrober/bliss-mood-poc/actions/runs/39605675932/artifacts/12347897819)):
121/6,400 **FMA training** and **42/800 FMA validation**
songs share normalized artist+title catalog entries with the
56,552-row MTG-Jamendo raw catalog. An additional 260 training
and 68 validation songs share artist strings alone.
**35 of the 42** validation exact artist/title matches are
in **Hip-Hop** (35 of 100 songs in that genre).
These are *possible metadata matches only*: no sound fingerprint,
no actual ONNX classifier training-split comparison, no proof
of reused encoder training music. Original FMA artist-ID
split disjointness does not resolve overlap with external
MTG-Jamendo training material. The previous 80-song validation
cohort was not individually provenance-audited.

New `scripts/benchmark_fma_genre.py` flags
`--exclude-mtg-catalog-matches --mtg-metadata-tsv`
exclude conservative catalog-matched FMA VALIDATION tracks
**before** selecting ten artist-distinct songs per
top-level genre and before any Rust-v5 ONNX inference.
The official FMA **TEST** split is skipped before even
reading the track ID in this benchmark. A dedicated
[filtered validation workflow](../.github/workflows/fma-genre-filtered-validation.yml)
reuses the pinned corrected Rust-v5 release-binary cache
while downloading canonical source FMA archives (never
publishing or caching music). The
[real filtered run 39606850307](https://github.com/chrober/bliss-mood-poc/actions/runs/39606850307)
completed metadata and cached-binary preflights; its
final retrieval results remain to be verified.
[Linux/Windows tests 39606799883](https://github.com/chrober/bliss-mood-poc/actions/runs/39606799883)
PASS. The first synthetic TEST-row fixture exposed that
the parser tried to parse an unusable TEST ID before
skipping it; corrected to skip TEST based on its split
before accessing any identity/labels. The earlier
unfiltered and subsequent filtered 80-song samples
**are not the same tracks** and their score differences
cannot be interpreted as paired/causal evidence.
For full research methodology see
[FMA/MTG catalog screen](fma-mtg-catalog-overlap-2026-10-21.md).

## Completed catalog-filtered FMA Validation benchmark

**PASS**, [run 39606850307](https://github.com/chrober/bliss-mood-poc/actions/runs/39606850307),
[aggregate artifact 12349595666](https://github.com/chrober/bliss-mood-poc/actions/runs/39606850307/artifacts/12349595666).

The FMA-MTG **metadata-only** audit identified **42
possible exact artist+title catalog matches among 800
FMA VALIDATION tracks**, including **35 of 100 Hip-Hop
tracks**. The filtered benchmark excluded all 42
**before deterministic balanced artist-distinct
VALIDATION sampling**, then analyzed 80 MP3s
(10 per genre, 80 distinct artists). No official
FMA TEST identities, genres, artist/title labels,
audio or model outputs were used; the loader now
skips TEST based on its split value before any
song-ID parsing. The corrected Rust-v5 binary was
restored from verified cache, saving the release build.

| Metric | Unfiltered Validation P@5 (DIFFERENT tracks) | Filtered Validation P@5 | Filtered mAP@10 | Filtered nDCG@10 |
| --- | ---: | ---: | ---: | ---: |
| RMS | 0.3175 | 0.3000 | 0.1624 | 0.2819 |
| Cosine | 0.3500 | 0.3200 | 0.1749 | 0.2985 |
| Centered Cosine | 0.3525 | 0.3225 | 0.1781 | 0.3043 |
| Weighted Jaccard | 0.3550 | 0.3000 | 0.1719 | 0.2933 |
| Old cutoff Top-K | 0.3150 | 0.3025 | 0.1719 | 0.3014 |
| Ranked Top-6 | 0.3150 | 0.3125 | 0.1752 | 0.3048 |
| Ranked Top-12 | 0.3400 | 0.3050 | 0.1740 | 0.3000 |

The samples are NOT matched, so these differences
are NOT valid paired estimates of training-overlap
effects. Metadata matches are possible catalog
collisions, NOT confirmed classifier training
recordings, and nonmatches do not prove absence
of training or encoder reuse. The TEST embargo
continues. Further details and uncertainty:
[FMA-MTG catalog research](fma-mtg-catalog-overlap-2026-10-21.md).
