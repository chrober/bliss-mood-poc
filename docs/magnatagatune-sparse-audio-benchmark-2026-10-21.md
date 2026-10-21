# MagnaTagATune multipart ZIP inspection and sparse-audio research benchmark

**Status (2026-10-21):** Full archive membership verified with NO MP3
download in [GitHub Actions run 39589694423](https://github.com/chrober/bliss-mood-poc/actions/runs/39589694423).
A four-triplet sparse-audio, artist-disjoint developmental smoke
**PASSED** in [GitHub Actions run 39590801662](https://github.com/chrober/bliss-mood-poc/actions/runs/39590801662).
The later artist-only holdout-feasibility audit **PASSED** in
[run 39592331265](https://github.com/chrober/bliss-mood-poc/actions/runs/39592331265).
These are not population-level similarity rankings or model-training
independence claims; no production metric or validated holdout score exists.

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


## Follow-up: frozen 50/50 artist-hash holdout and smoke exposure controls

[Metadata-only GitHub Actions run 39592331265](https://github.com/chrober/bliss-mood-poc/actions/runs/39592331265)
**PASS**. Three predeclared artist-hash reserve thresholds
were checked without calculating or inspecting any new model scores:

| SHA first-byte cutoff | Development-only triples | Holdout-only triples | Mixed artist triples excluded |
| --- | ---: | ---: | ---: |
| 51 (~20%) | 162 | 4 | 180 |
| 85 (~33%) | 86 | 13 | 247 |
| 128 (50%) | **31** | **56** | **259** |

The 50/50 design is now recorded as the **preferred, metadata-derived
artist-hash holdout policy**: SHA-256 of the fixed salt and normalized
artist string, first byte below 128 reserved to holdout. This
percentage was chosen **from artist/annotation coverage only**,
not from classification or similarity performance.

**Prior smoke exposure:** The earlier four-triplet technical smoke
sampled 12 distinct artists before this explicit partition was
registered. Eight of the 56 holdout-only triplets share an artist
with that smoke and are conservatively excluded. Therefore the
**as-yet-unexposed holdout comprises only 48 unique triplets**.
Both artist partitions and the 48 remaining triplets have reproducible
aggregate hashes in the CI report; no music IDs or artist identities
are published.

This author-level independence is not absolute audio or label
independence (same artists can be named differently; the Discogs
encoder's historical training data are not fully known). Strictly
excluding mixed triples removes **259/346** reference questions;
therefore any future comparison restricted to these folds describes
a particular subset of MagnaTagATune and must report label/
consensus distribution, paired metric coverage and uncertainty.

**No more development/holdout audio analysis has been executed**
from this revised partition. The prior four-triplet run is an E2E
smoke only, not a new performance estimate. Before extending
the benchmark to all 31 development questions, enforce the frozen
128-byte policy in its selection code; never evaluate the reserved
48 questions during tuning. Report holdout values only once a
metric or evaluation policy has been pre-registered and a complete
independence/uncertainty plan documented.

Implementation:
[scripts/audit_magnatagatune_holdout.py](../scripts/audit_magnatagatune_holdout.py),
[tests/test_audit_magnatagatune_holdout.py](../tests/test_audit_magnatagatune_holdout.py).
Linux and Windows Python regression tests completed successfully in
[run 39592264225](https://github.com/chrober/bliss-mood-poc/actions/runs/39592264225).
The metadata-only follow-up ran in under one second and avoided all
model, MP3 and Rust downloads.


## Frozen 128/256 artist-only DEVELOPMENT run, with preserved holdout

On 21 October 2026, the development benchmark was implemented in
`scripts/benchmark_magnatagatune.py` with
`--selection-mode frozen-development`. It **must** select all
**31** artist-only development triplets from the previously registered
`SHA-256("MTT-artist-holdout-v1|20261021|" + normalized_artist)`
first-byte cutoff **128**, without filtering by human vote consensus.
The selector runs `audit_magnatagatune_holdout.evaluate_inputs`
and verifies the exact expected count and sorted-triplet SHA-256
fingerprint **before any MP3 byte range is requested**.

The development run deliberately does not download or score the
**56** artist-only candidate holdout triples (of which **48**
were not exposed to the original technical smoke) or the **259**
mixed-artist triples. Original ordered duplicates are aggregated.
Tied human majority votes and undefined/tied metric predictions
are abstentions, not forced matches. No metric winner or independent
population claim is justified.

Research workflow:
[.github/workflows/magnatagatune-development.yml](../.github/workflows/magnatagatune-development.yml),
branch-file-change triggered and manually dispatchable only.
It retains offline synthetic tests, metadata/8-MiB ZIP validation,
pinned corrected Rust-v5, Cargo cache, sequential one-worker
`--threads 1` inference, checksum-verified bounded HTTP 206
requests and aggregate-only upload. Python tests include a regression
that deliberately places held-out artists in an artificial fixture
and asserts their complete exclusion.

**First real attempt [39593423801](https://github.com/chrober/bliss-mood-poc/actions/runs/39593423801): FAILED** due to a transient
`curl` **exit 28, HTTP 000**, while fetching the 22nd of
**92 uniquely needed development clips**. The first 21 genuine
clips were successfully analyzed. This was a network timeout, not
a failure of the split, ZIP integrity, Rust-v5 parity or a model
score; the interrupted run produced no comparison report.
A new bounded HTTP retry policy (`curl --retry 5 --retry-max-time
300 --max-time 50`) was regression tested on Linux/Windows while
retaining `--max-filesize`, 206 Content-Range validation,
audio CRC and the no-whole-ZIP protection.

**Retry Actions [39594161136](https://github.com/chrober/bliss-mood-poc/actions/runs/39594161136)** is triggered and must be checked
for actual completion and its aggregate artifact before reporting
scores or measured improvements. No audio, track IDs or feature vectors
are committed, cached or uploaded. Do not call a failed run a PASS.

Performance emphasis: the prior 4-triplet smoke needed 1.39 MB
of compressed ZIP ranges and ~14.5 s inference+download, versus
~88 s for the Cargo/FFmpeg build. The 31-triplet attempt reached
21/92 song analyses in about 26 seconds before the source server
temporarily stopped responding; do not extrapolate that into
verified complete-job throughput or benefit from multiple workers.
