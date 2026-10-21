# MagnaTagATune multipart ZIP inspection and sparse-audio research benchmark

**Status (2026-10-21):** Full archive membership verified with NO MP3
download in [GitHub Actions run 39589694423](https://github.com/chrober/bliss-mood-poc/actions/runs/39589694423).
A separate four-triplet sparse-audio, artist-disjoint developmental smoke
has been implemented and started, but it is not a credible population
benchmark and must not be interpreted as a metric selection or validated
holdout result. Check the actual actions run state before claiming success.

## Official source and provenance

- Publisher: https://mirg.city.ac.uk/datasets/magnatagatune/
- Audio: **a single ZIP stream split into three consecutive files**
  `mp3.zip.001`, `mp3.zip.002`, `mp3.zip.003`.
- Official byte lengths observed with HTTP 206 Content-Range:
  **1,100,000,000 + 1,100,000,000 + 772,769,864 bytes** =
  **2,972,769,864 bytes (2.769 GiB)**.
- These are NOT three independently openable archives.
- Source terms: original TagATune noncommercial research data under
  **CC BY-NC-SA 3.0**, scripts separately under GPL-v3.
  These conditions do not imply commercial shipping rights for Lyrion.

## Successful audio-free byte-range preflight

`scripts/audit_magnatagatune_archive.py` constructs a seekable, virtual
multipart ZIP covering only the **last 8 MiB of part .003**, obtained by
HTTP Range requests. The complete ZIP central directory lives inside this
bounded tail and can be enumerated without extracting or downloading the
almost 3-GiB compressed music archive.

Observed [successful run 39589694423](https://github.com/chrober/bliss-mood-poc/actions/runs/39589694423)
and [aggregate-only artifact 12341410295](https://github.com/chrober/bliss-mood-poc/actions/runs/39589694423/artifacts/12341410295):

| Finding | Observed result |
| --- | ---: |
| ZIP nondirectory audio entries | **25,863** |
| Clip IDs needed by all published triplets | **1,019** |
| Exact MP3 filename matches | **1,019** |
| Missing or ambiguous needed MP3 paths | **0** |
| Unique unordered three-clip questions | **346** |
| Original comparison rows (including clip permutations) | **533** |
| Required compressed MP3 member bytes, summed | **116,910,845** (~111.5 MiB) |
| Archive central-directory probe download | **8 MiB plus three 1-byte probes** |
| Membership audit wall time | **0.51 seconds** |
| Peak memory of membership process | ~**69 MB RSS** |

The 533 published records represent only 346 unique unordered
three-clip sets. Permutations of the same three clips share human
votes and are NOT separate independent statistical units; the new
audio experiment aggregates votes by clip ID across all permutations
of each unordered triple.

**Caveats:** The byte-range directory inspection verifies
presence, central-directory filenames and compressed sizes, not audio
CRC/decode. The total 116.9 million compressed member bytes is a
theoretical transfer floor, not a measured full-cohort download
amount; range-request overhead, ZIP local headers and split-boundary
fetches add traffic. ZIP part hosting supports HTTP 206 ranges at
the time of this check. No music or clip identity was shared.

## Sparse audio-only-on-demand implementation

`scripts/benchmark_magnatagatune.py`:
- verifies the official zip central directory and exact metadata
  clip ID/MP3 path identity;
- aggregates the 533 individual (potentially reordered) vote records
  to vote distributions on **unique unordered triplets**;
- selects a **four-triplet development-only smoke**, requiring
  unique >=70% outlier choice and no artist overlap across the
  selected clips; selection and fixed seed are recorded only as
  aggregate hashes (individual chosen IDs are not disclosed);
- reads each selected ZIP member by HTTP 206 *absolute byte range*
  mapped onto the three consecutive source files; validates local
  header, compression method, entry name, payload size and CRC;
- extracts exactly one clip into a temporary private file at a time;
  invokes pinned numerically verified Rust-v5 `analyze-features`
  to store 87D Genre and 56D Mood/Theme in a private schema-v3
  SQLite sidecar; no transfer of these audio files or features into
  GitHub artifacts, caches, logs or commits;
- compares all seven existing similarity metrics using the same
  three clips: the strongest pair determines the predicted odd one
  out; ties, undefined scores and zero-information Top-K predictions
  abstain instead of inventing an outcome;
- reports majority-choice correctness, vote-weighted agreement,
  abstention rates and analysis/network throughput for each
  head/metric in **aggregate only**.

The complete audio workflow is
[.github/workflows/magnatagatune-sparse-smoke.yml](../.github/workflows/magnatagatune-sparse-smoke.yml)
with synthetic offline tests at
[tests/test_benchmark_magnatagatune.py](../tests/test_benchmark_magnatagatune.py).
It uses a second, *pinned* PR #17 checkout at
`2c3d44401436b3b41b6e067199016a1ed2335fbf`,
not a merge of PR #17.

The current implementation is **fixed serial**: one MP3 analyzed at
a time (`--threads 1`), no adaptive workers. Network, build, inference,
scoring and ZIP validation stages are timed; GitHub runner CPUs are
recorded. A safe parallel Batch/isolated-sidecar A/B is a separate
task, justified only when same-clip memory, determinism and speed
have been measured.

## Important statistical separation for later runs

The first four selected triplets are for **end-to-end correctness only**.
The explicit selection of strong-consensus questions based on human
answers invalidates any claim of representative accuracy. No metric
winner, no direct comparison to FMA/DEAM retrieval percentages and no
human-independent evaluation should be inferred.

Before scoring more data, freeze a **grouped holdout plan** across the
346 unique unordered clip sets, using connected artists/tracks to avoid
a recording appearing in both development and test. If group-connected
components make a clean partition infeasible, report this honestly and
prefer independent studies over falsely claiming a holdout.

Separately evaluate human choice consensus tiers and vote-weighted
agreement, preserve all original votes, report abstentions and paired
uncertainty by independent clip/artist group. The original 533
permutations are not 533 independent observations.

No changes to production Lyrion mixer, branch main, PR #13 or PR #17.


## Verified 4-triplet genuine audio Rust-v5 development smoke

**PASS**: [GitHub Actions 39590801662](https://github.com/chrober/bliss-mood-poc/actions/runs/39590801662),
[aggregate-only artifact 12341406678](https://github.com/chrober/bliss-mood-poc/actions/runs/39590801662/artifacts/12341406678).

The first invocation was blocked **before Rust** by a shell manifest
newline bug under `set -e` (file-read status), fixed without changing
any audio analysis or label data. The corrected run succeeded through
all stages:
- metadata source and 8 MiB ZIP-central-directory Range preflight;
- pinned corrected Rust-v5 build from immutable PR #17 source checkout,
  with its committed Cargo.lock (without merging PR #17);
- upstream Discogs-EffNet ONNX encoder plus Genre and Mood/Theme
  classifier metadata and binaries;
- **four deterministic, high-consensus, artist-disjoint development
  triple questions**, **twelve distinct MP3 clips**;
- twelve CRC-checked ZIP-member MP3s retrieved from actual compressed
  remote byte ranges, decoded/analyzed one by one with fixed
  `--threads 1`, stored in a fresh private schema-v3 sidecar;
- **both** validated v5 feature heads and **all seven** existing
  similarity metrics scored against aggregated clip-ID-wise
  human odd-one-out votes; only aggregate report uploaded.

Measured in this exact GitHub runner:
- **12 remote HTTP Range requests**, **1,385,735 bytes**
  transferred for the twelve ZIP member ranges;
- Audio range download + feature inference: **14.477 seconds**
  (~1.21 seconds per clip overall);
- End-to-end audio+score segment: **14.496 seconds**;
  scoring only **0.019 seconds**;
- `/usr/bin/time` for Python smoke process **14.95 s**
  and **81,400 KiB peak RSS** (scope excludes/depends on child
  process accounting; not a proof of systemwide peak memory);
- one fixed song worker and one ONNX thread; adaptive scanner
  workers are not yet applicable;
- Cargo/FFmpeg-build workflow step took approximately
  **88 seconds** and thus dwarfed the ~15-second audio stage.

The **four-question** Mood-Cosine smoke returned 3/4 correct
majority odd-one-out predictions (**0.75**) and a vote-weighted
agreement of **0.75** in this deliberately *preselected*
high-consensus development cohort. This is **not** a generalization
estimate, not a Genre/Mood rank winner and not a holdout result.
The tiny selected set is biased by design, and independent questions
must be grouped by original artist/track for any future confidence
interval or hypothesis test.

The first candidate throughput improvement is therefore **reusing
a source-hash-verified Linux Rust-v5 executable or improving cross-run
Cargo reuse**, rather than adding workers immediately. The 8-MiB
directory fetch and 12 targeted clips already avoided >2.7-GiB
full-archive download. Do not assume Rust worker count will
materially reduce total job duration until fixed/serial A/B runs
measure the same audio and all downstream feature values.


## Artist holdout feasibility: real data (2026-10-21)

[GitHub Actions 39591601421](https://github.com/chrober/bliss-mood-poc/actions/runs/39591601421)
completed a **metadata-only** human-triplet/artist graph audit;
[aggregate report 12342082098](https://github.com/chrober/bliss-mood-poc/actions/runs/39591601421/artifacts/12342082098).
It studied the **346 unique unordered triplets** (not 533 independent
cases) across the **214 referenced artist strings**.

**Critical observation:** The artist co-occurrence graph has **one
connected component** containing all **214 artists and all 346
unique triplets**. A connected-component-disjoint train/test split is
thus **mathematically impossible** without discarding triplets.
The published data are too interconnected for the ideal proposed
80/20 artist-component holdout without exclusions.

A deterministic SHA-256 artist-based assignment with strict exclusion
of cross-group triplets yields:
- **162** all-development-artist triplets;
- only **4** all-holdout-artist triplets;
- **180** mixed-artist triplets excluded;
- **0** questions with missing artist.

Four independent held-out questions are insufficient for reliable
comparison among seven methods. Even a fully executed benchmark could
not substantiate an artist-generalization claim from that split.
A less strict grouped or triplet holdout may still provide
**descriptive same-corpus rankings**, but shared artists and songs
must then be explicitly reported as sources of dependence; confidence
intervals and final claims must reflect that design.

The previous four-triplet smoke chose high-consensus examples before
this artist split was frozen, so it **cannot be retroactively treated
as held-out evidence**. Treat any possible overlap with candidate
holdout artists conservatively (exclude those questions or freeze an
unseen independent reference corpus before testing).
Current algorithm: [audit_magnatagatune_holdout.py](../scripts/audit_magnatagatune_holdout.py).
No audio used or private identifiers released.

**Next science decision:** use the 346 questions as an *exploratory*
perceptual-similarity benchmark, with vote/consensus handling and
repeated-artist sensitivity analyses, and seek a separate independent
human-similarity dataset for final confirmation. Do not select a
production metric based on four holdout triplets.


### Follow-up artist-hash sensitivity: alternative 50/50 design

The **revised, successful** metadata audit
[run 39592331265](https://github.com/chrober/bliss-mood-poc/actions/runs/39592331265)
([aggregate artifact 12342707931](https://github.com/chrober/bliss-mood-poc/actions/runs/39592331265/artifacts/12342707931))
computed artist-hash thresholds **51, 85, 128** out of 256 without
accessing any new model predictions or audio:

| Artist hash cutoff | Development triplets | Candidate holdout triplets | Mixed artist exclusions |
| --- | ---: | ---: | ---: |
| 51 (~20% artists in holdout) | 162 | 4 | 180 |
| 85 (~33%) | 86 | 13 | 247 |
| 128 (~50%) | **31** | **56** | **259** |

Under the final tested 128/256 option, **8** of the 56 potential
holdout questions have artists already seen in the preceding
four-triplet real-audio smoke; **48** remain untouched by that smoke.
This is a more usable *potential* artist-disjoint test than the
four-question 20%-artist candidate, but the loss of 259/346 triplets
and the small 31-question development set constrain reliability.
The all-connected artist graph finding remains unchanged.

**IMPORTANT:** The hash threshold was compared using metadata-only
counts after four development clips/triples had already been explored.
A new test protocol must freeze the chosen cutoff **before** evaluating
holdout model results, exclude the eight previously exposed
questions, avoid further adjustment on test performance, and
preserve the test-candidate identity hash in the research record.
These triplets are only held out from our four-triplet analysis,
not proven outside the original ONNX training corpus. No quality
result for the 48 candidate holdout questions has yet been measured.
