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


## All-346 exploratory design: staged audio, two isolated workers and opt-in cache

**Research decision 21 Oct 2026:** Rather than overinterpret the small
31-development/48-candidate-holdout strict artist partition, the user
chose a **full, explicitly exploratory analysis** of all 346 unique
unordered MTT triplets and their 1,019 referenced clips. This
**consumes the formerly reserved holdout questions**. Once it is
run there is **no independent MTT holdout left**; this must never be
described as an unseen holdout experiment or used to proclaim a
production metric winner. The 533 ordered comparison records are
collapsed by sorted clip triple, summing individual clip-ID votes.

New workflow:
[.github/workflows/magnatagatune-all-exploratory.yml](../.github/workflows/magnatagatune-all-exploratory.yml),
initial Actions run
[39597229438](https://github.com/chrober/bliss-mood-poc/actions/runs/39597229438).
**Check the actual completed run and aggregate report before claiming
metrics or speedup.** The workflow is triggered by its own file change
or manual dispatch (no docs-only automatic run).

New implementation:
- `scripts/benchmark_magnatagatune.py --selection-mode all-exploratory`
  requires unchanged official CSV fingerprints plus exactly 346
  unique unordered triplets / 1,019 clip IDs. It does not apply
  subjective consensus filtering or artist partitioning.
- `scripts/mtt_local_archive.py` reads each ZIP member from the
  three consecutively staged source parts without concatenating,
  unzipping all members or doing ~1,000 throttled network requests.
  The HTTP Content-Range source-probed part lengths are validated
  against the staged archives; each actually used MP3 is verified
  against ZIP central-directory CRC and size before inference.
- `scripts/mtt_parallel_workers.py` runs **two independently
  writing Rust-v5 `analyze-features` subprocesses**, each with
  ONNX `--threads 1`, on 4-CPU Actions runners. Every worker
  owns its own SQLite schema-v3 sidecar. A deterministic,
  fail-closed single-writer merger checks cohort metadata,
  SQLite integrity, complete 87D/56D coverage, no duplicate
  keys and expected clip count. There are **no concurrent writes
  to a shared database**.
- Aggregate-only score output for 7 metrics × 2 heads reports
  distinct human majority ties, score undefined/metric ties/
  Top-K zero overlap, defined-query coverage, conditional and
  abstention-inclusive majority accuracy, 1/3 random odd-one-out
  reference, votes-weighted agreement and two human-consensus
  strata. This is *descriptive* same-corpus evidence and accounts
  for correlated triplets sharing artists/songs.

### Implemented: cache only the exact 1,019 relevant MP3s

**User decision 21 Oct 2026:** Use a small *selected-clip-only* GitHub
Actions cache instead of retaining the complete 2.77-GiB multipart
audio archive. Scripts:
- [mtt_selected_clip_cache.py](../scripts/mtt_selected_clip_cache.py):
  on the initial cache miss, reads just the 1,019 referenced members from
  the publisher ZIP locally, verifies their **original ZIP CRC32 and
  uncompressed lengths**, then assembles a single deterministic
  **ZIP_STORED** file (`mtt-required-1019-clips.zip`) containing
  exactly the selected clip payloads under hashed internal filenames.
  Expected size is about 117 MB, but actual byte count must be read
  from the real GH Actions run rather than assumed.
- On a cache hit the workflow downloads only official **metadata plus
  the 8-MiB ZIP directory tail**. It verifies the complete cached
  package's 1,019 file names, types, lengths and CRCs against the
  original central directory **before Rust is built**.
- [benchmark_magnatagatune.py](../scripts/benchmark_magnatagatune.py)
  accepts `--selected-clip-cache`; two isolated `bliss-mood`
  workers analyze those cached audio bytes, never the original full
  archive. The 346-triplet sampling and all seven scores are identical
  to the successful earlier full-archive run.
- Cache miss: original files are temporarily downloaded, checked against
  HTTP Content-Range sizes, compacted and **deleted from the runner**.
  Only the 1,019-clip package is passed to
  `actions/cache/save@v4`. **No full source ZIP** is cached,
  committed or uploaded through GitHub artifacts.
- Cache is automatically reused on the trusted research feature branch.
  Manual `workflow_dispatch` has `cache_audio` (default true);
  set false to bypass caching for that manual run.
  Cache keys pin the source CSV cohort and archive size; all stored clips
  undergo the same per-run original-CRC checks, preventing silent
  corruption or inaccurate provenance.

**Security/licensing condition:** The package still contains third-party
**CC BY-NC-SA 3.0 research audio**. GitHub Actions caches are **not
confidential** and some PR workflows targeting the cache-bearing branch
may gain access; feature-branch scoping reduces accidental sharing but
does not eliminate this access model. Treat the cache as restricted
research material, not approved commercial redistribution, and disable
caching if those access conditions are unacceptable. No music in
`upload-artifact` or public git.

**Verification:** Offline cache-specific synthetic tests cover
all 1,019 clips, missing/corrupt payloads, publisher CRC mismatch,
strict ZIP contents, and cache read restrictions. GitHub Action
[39599548243](https://github.com/chrober/bliss-mood-poc/actions/runs/39599548243)
is the initial real cache-seeding attempt; **check completed outcome
before claiming size, successful cache save, speedup or metric parity**.
A subsequent completed run with actual `cache-hit: true` is required
to substantiate measured time savings.

GitHub's default repository cache budget is about 10 GiB; cached
items are not permanent and can be evicted after inactivity or
under quota pressure. On a miss the workflow deterministically
recreates and validates the curated package, without changing
musical similarity reference scores.

Track actual walltimes in GitHub step summary for central-directory
preflight, archive stage, Cargo build, model downloads, parallel
inference/scoring, and compare serial vs two-worker performance only
on identical pinned audio/model inputs. Do not present inferred
speedups as measurements.

Official GitHub cache policies:
https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching
Original TagATune research terms:
https://tagatune.org/details.html

## Real 1,019-clip curated cache: MISS confirmed, HIT being validated

[Run 39599548243](https://github.com/chrober/bliss-mood-poc/actions/runs/39599548243)
**PASS**: full publisher multipart archive temporarily downloaded, only
the **1,019 required MP3s** repacked and CRC-verified into
`mtt-required-1019-clips.zip`, raw publisher files immediately
deleted. The resulting research package contains **119,689,247 bytes
(114.14 MiB)**; verified extracted audio totals 119,460,969 bytes.
Building the curated ZIP from the downloaded publisher parts took
**1.18 seconds**, and a separate full 1,019-clip CRC verification took
**0.59 seconds** on the GitHub runner. The GitHub cache action saved
only this single package under the pinned MTT source key
(`actions/cache` storage reports ~130,467,584 bytes).

The *first seeded cache run* also independently processed all 1,019
clips with two isolated Rust-v5 worker sidecars and reproduced the
baseline Mood-Cosine majority accuracy **0.6552901024** on defined
predictions. However, the analysis+merge portion took **244.677 s**
rather than the original full-source run's **145.505 s**. This shows
that run-to-run inference timing variability is material: an apparent
overall difference must **not** be ascribed to caching or thread count
without matched stage comparisons.

[Run 39600498519](https://github.com/chrober/bliss-mood-poc/actions/runs/39600498519)
then confirmed a **true GitHub cache HIT** at the workflow-step
level: the original 2.77-GiB publisher download and curated ZIP
rebuild were **SKIPPED**; all 1,019 cached files again passed
publisher CRC verification before Rust compilation. The cached-run
final metrics, end-to-end timings and all seven-metric scorecard need
to be checked once GitHub Actions reaches a completed state. This
is the required two-run MISS/HIT comparison, not merely a hypothetical
cache benefit.

## Verified first complete 346-triplet, two-worker run

[Actions run 39597229438](https://github.com/chrober/bliss-mood-poc/actions/runs/39597229438)
**PASSED**, using full publisher archive staged ephemerally, two
isolated Rust-v5 worker sidecars, both model heads and all seven
metrics. [Aggregate report](https://github.com/chrober/bliss-mood-poc/actions/runs/39597229438/artifacts/12345475102).

The benchmark processed **1,019 clips**, grouped **346 unique
unordered human triplets**, and recorded **145.505 s** for
parallel inference+SQLite merge and **145.714 s** for download-free
local analysis plus scoring. Model scoring alone took ~0.209 s.
The Mood-Cosine majority-choice accuracy on defined predictions
was **0.6552901**; see report for human ties, abstention-inclusive
coverage and the remaining six metrics. No artist-disjoint holdout
remains in this all-346 exploratory run.

This first successful full-run timing is a **two-worker baseline**,
not proof that workers are faster than a matched one-worker run.
The curated-cache optimization is intended to reduce **archive
download and restore time**, not claim that inference is faster.


## Verified cache HIT and full seven-metric scorecard

[Cached run 39600498519](https://github.com/chrober/bliss-mood-poc/actions/runs/39600498519)
**PASS**; real `actions/cache` HIT, 2.77-GiB source download and
compaction **skipped**, all 1,019 cached MP3s cross-checked against
the publisher's central-directory CRCs, two separate Rust-v5 worker
sidecars. [Aggregate JSON and
scorecard](https://github.com/chrober/bliss-mood-poc/actions/runs/39600498519/artifacts/12346356813).
The same Mood Cosine accuracy `0.6552901023890785` was reproduced.
Cached-hit inference + merge **231.053 s**, scoring **0.343 s**.
The run's start-to-updated end time was about **327 seconds**,
versus **426 seconds** for the initial cache-creation run and **368
seconds** for the previous full-original-archive workflow. This is
an **observed** 99-second reduction against the cache MISS run and
41-second reduction against the prior full-original run; these are
not controlled speedup estimates since inference varies between
145.5, 244.7 and 231.1 seconds with the same two workers.

There are **53 majority-vote-tied unique triplets**, leaving
**293 common human-scorable questions**. Below is
**accuracy including metric abstentions as incorrect**, always
on the same 293 denominator:

| Method | Genre | Mood/Theme | Mood prediction coverage |
| --- | ---: | ---: | ---: |
| RMS | 63.5% | 54.6% | 100% |
| Cosine | 65.2% | 65.5% | 100% |
| Centered Cosine | 65.2% | **65.9%** | 100% |
| Weighted Jaccard | 63.8% | 61.1% | 100% |
| Historical Top-K Weighted Jaccard | 60.1% | 44.4% | **71.7%** |
| Ranked Top-6 Jaccard | 61.8% | 62.5% | 100% |
| Ranked Top-12 Jaccard | 64.5% | 64.8% | 100% |

The best *descriptive* Mood result is only **~0.4 pp**
above ordinary Cosine; such small differences cannot be
interpreted as meaningful without same-question paired comparison,
uncertainty and dependence analysis. Genre Cosine and Centered
Cosine tie at **65.2%**. No model head, metric or
business-default winner is authorized by these observations.
Mood Top-K loses ~28% question coverage and must never be compared
using conditional accuracy alone.

## Paired post-hoc uncertainty research and subsequent performance

A new in-memory
[mtt_paired_evidence.py](../scripts/mtt_paired_evidence.py)
module computes **all 21 head-specific method pairs** on exactly
the same human-scorable unordered questions (42 comparisons
across two heads). A metric abstention scores **zero** on
the common denominator; human majority ties are excluded.
The in-memory method predictions and raw votes remain on the
runner and are NOT published. Exported aggregate data include
a-only/b-only-correct discordant counts, delta in percentage points,
paired-question IID resampling intervals (600 deterministic
replicates) and artist-level randomized-weight perturbation
intervals (600 replicates). The latter is an **exploratory
dependency sensitivity exercise, not a cluster bootstrap or
population confidence interval**; artist co-occurrence forms
one large connected component. It is also NOT independent
held-out confirmation and the 42 contrasts are post hoc.
Do not choose a metric using the narrowest interval.

The GitHub scorecard now includes a small number of explicit
paired contrasts for interpretation and the aggregate JSON
contains all 42, with separate limitations. Scripts and
unit tests were checked on Linux/Windows in
[run 39602141111](https://github.com/chrober/bliss-mood-poc/actions/runs/39602141111)
(PASS after fixing a literal test assertion). A real full-data
paired benchmark was triggered in
[run 39602475906](https://github.com/chrober/bliss-mood-poc/actions/runs/39602475906);
check its completed result and the actual uncertainty values
before citing any new paired metric differences.

Further repeated build overhead is addressed via a **second**
Actions cache for the compiled, immutable-source
`2c3d44401436b3b41b6e067199016a1ed2335fbf` Linux Rust-v5
executable plus SHA256 manifest. On a trusted-branch hit,
Cargo toolchain and compilation are skipped after verifying
the binary and its smoke CLI command. On a miss, original
`Cargo.lock` and pinned checkout produce the executable
and save it. This **binary cache is separate from the licensed
audio cache** and from the dependency/target Cargo fallback cache.
A successful actual binary cache HIT and measured timing comparison
are still required; do not advertise savings before that.
