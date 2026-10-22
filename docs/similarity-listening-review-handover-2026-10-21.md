# Handover: Local Genre/Mood listening review and research similarity evidence

**Updated:** October 21, 2026, English-only documentation.
**Current overall plan:** [Similarity-to-Lyrion roadmap](similarity-lyrion-roadmap.md).
**Representation-level detail:**
[A/B/C song-representation handover](similarity-three-representation-approaches-handover-2026-10-21.md).
Only `feat/similarity-metric-evaluation`, Draft PR #16;
no changes to `main`, PR #13/#17 or the production mixer.

## Purpose and correct current status

We want human listening evidence to decide how similar
two songs really sound, and separately whether one is
a good **immediate playlist successor**.
The mathematical representation question
(classifier heads A / direct 1280D embedding B /
carefully calibrated combination C) is independent
of the product architecture question
(Bliss-first / feature-first / hybrid candidate pools).

The initial local hearing pilot of **eight pairs
has already been received and analyzed**; do not
ask the user to repeat or newly fill the first
eight rows. It was not adequate for production
metric selection. The subsequent external MTT
and FMA A/B experiments have now completed;
these older chronological notes must not be
interpreted as saying embeddings have never
been extracted or measured.

**Experimental extraction exists, but phase 0
is not fully verified and not production-ready.**
The user's local schema-v3 Genre/Mood sidecar
does not automatically contain song-level 1280D
embeddings. The next local step is a bounded
read-only inventory (phase 2), then an approximately
12-contrast listening-protocol pilot and a distinct
new evaluation block; no automatic full-library
rescan or queue append.

## Methods and evidence hierarchy

| Approach | Representation | Current evidence |
| --- | --- | --- |
| A | 87D Genre and 56D Mood classifier head values; cosine, centered cosine, weighted Jaccard, RMS and historical Top-K variants | Explored in MTT, FMA and DEAM reference tasks |
| B | Raw 1280D Discogs-EffNet patches aggregated by song, normalized with L2, cosine | Optional research export implemented; same-song MTT and FMA A/B passed |
| C | Fusion of embeddings and head evidence | Four untrained local midrank MTT ablations evaluated; globally calibrated song-score fusion still unproven |

**Human target ≠ model label ≠ playlist quality.**
MTT's 293 unique-majority questions do not
leave a new independent holdout; FMA VALIDATION
evaluates coarse Genre retrieval; DEAM human VA
is a Mood/emotion proxy and the new paired
DEAM 1280D comparison is source-blocked.
No evidence establishes an optimal production
metric or Fusion-C weighting. The official
FMA TEST was not inspected.

### Previously verified external research

- MTT direct 1280D cosine **182/293**,
  Mood centered cosine **193/293**;
  [A/B run 39617159250](https://github.com/chrober/bliss-mood-poc/actions/runs/39617159250)
  and [synthetic patch/thread/SQLite regression 39618323154](https://github.com/chrober/bliss-mood-poc/actions/runs/39618323154)
  PASS. Four untrained fixed-rank fusions were
  evaluated in [run 39619708040](https://github.com/chrober/bliss-mood-poc/actions/runs/39619708040);
  no fusion exceeded 193/293 on the common denominator.
- FMA same 80 screened VALIDATION tracks:
  embedding Genre P@5 **0.2800**,
  Genre cosine **0.3200**, Genre centered
  **0.3225**; [run 39625087310](https://github.com/chrober/bliss-mood-poc/actions/runs/39625087310)
  PASS.
- DEAM prior filtered 240-song
  Mood cosine VA Spearman **0.28678455**;
  the new paired A/B code/fingerprint
  was corrected and tested, but official
  source host `cvml.unige.ch:443`
  did not accept connections.
  **No new 1280D DEAM score exists.**
- The selected FMA audio cache reused
  80 original recordings (76.51 MiB)
  across warm workflows instead of
  the full 7.2-GiB download; no
  licensed music was uploaded as
  a result artifact.

The following originally English sections
record earlier published CI experiments.
Their historical "Next" statements describe
what was planned at that time; the
current [central roadmap](similarity-lyrion-roadmap.md)
and [chat handover](chat-handover.md) override
outdated interim priorities.

> **FMA CATALOG-FILTERED GENRE VALIDATION FINISHED (21 OCT 2026):**
> [Real filtered run 39606850307](https://github.com/chrober/bliss-mood-poc/actions/runs/39606850307)
> **PASS**, [aggregate artifact 12349595666](https://github.com/chrober/bliss-mood-poc/actions/runs/39606850307/artifacts/12349595666).
> The preflight removed **42 possible exact FMA VALIDATION /
> MTG-Jamendo artist+title catalog matches among 800**,
> including 35/100 Hip-Hop. All 80 selected validation
> MP3s then analyzed with distinct artists, 10 per
> top-level genre, pinned corrected Rust-v5, official
> publisher music, **no FMA TEST use**. Verified Rust-v5
> binary cache HIT and no Cargo build; no FMA audio cached
> or uploaded.
>
> Filtered FMA Genre **Precision@5**:
> RMS **0.3000**, Cosine **0.3200**, Centered Cosine
> **0.3225**, Weighted Jaccard **0.3000**, old cutoff
> Top-K WJ **0.3025**, Ranked Top-6 **0.3125**, Ranked
> Top-12 **0.3050**. Centered Cosine leads narrowly
> on filtered P@5 and mAP@10 (**0.1781**), Ranked
> Top-6 on filtered nDCG@10 (**0.3048** versus
> Centered **0.3043**). Random P@5 expected **0.113924**;
> all seven metrics had 80 query scores.
> Previous unfiltered 80-song FMA validation numbers
> are from a DIFFERENT cohort; comparing them is
> descriptive, **NOT a paired estimate of overlap
> effects, not proof of ONNX training disjointness**.
> A corpus-level metadata coincidence does NOT
> establish shared audio or training usage.
>
> Completed [FMA catalog research doc](fma-mtg-catalog-overlap-2026-10-21.md)
> and [FMA plan](fma-genre-benchmark-plan.md) should
> be read with [cross-dataset evidence](similarity-cross-dataset-evidence-2026-10-21.md).
> **Next:** preregister expanded validation and
> paired-query Genre scoring, audit actual model
> training split/encoder provenance, only then
> unlock FMA TEST as a single independent check;
> consider separate human transition judgments.
> PR #16 Draft; no merge, no local/private music
> scan or updates to PR #13/#17.
>

> **FMA–MTG CATALOG SCREEN COMPLETED / FILTERED VALIDATION RUNNING (21 OCT 2026):**
> Metadata-only [GitHub Actions 39605675932](https://github.com/chrober/bliss-mood-poc/actions/runs/39605675932)
> **PASS**, aggregate [artifact 12347897819](https://github.com/chrober/bliss-mood-poc/actions/runs/39605675932/artifacts/12347897819).
> On FMA-Small **TRAINING**: 121/6,400 possible exact
> artist+title MTG-Jamendo catalog matches, 260 artist-only
> matches. On official **VALIDATION**: **42/800 possible
> exact matches**, 68 artist-only; of those exact matches,
> **35 of 100 Hip-Hop validation songs**. TEST's 800 records
> were counted only for official split-size checking; NO
> TEST artist/title/genre/MP3/prediction was examined.
> These are **possible metadata matches, not verified
> recordings or actual ONNX training examples**.
> Existing 80-song unfiltered VALIDATION result is NOT
> guaranteed MTG-independent.
>
> Added `scripts/audit_fma_mtg_overlap.py`, synthetic tests,
> [.github/workflows/fma-mtg-overlap-audit.yml](../.github/workflows/fma-mtg-overlap-audit.yml);
> extended `scripts/benchmark_fma_genre.py` with
> `--exclude-mtg-catalog-matches --mtg-metadata-tsv PATH`
> for **validation-only**, filtering potential exact matches
> BEFORE artist-distinct sample selection and inference.
> The official TEST partition is now skipped before
> even parsing its song ID in this discovery CLI.
> [Linux+Windows Python CI 39606799883](https://github.com/chrober/bliss-mood-poc/actions/runs/39606799883)
> PASS after correcting synthetic sealed TEST-row fixture.
> New [filtered FMA workflow 39606850307](https://github.com/chrober/bliss-mood-poc/actions/runs/39606850307)
> has verified its source/42-match metadata preflight,
> a TRUE pinned Rust-v5 binary-cache HIT, and is downloading
> the official 7.2-GiB FMA-Small ZIP (no audio caching).
> **CHECK final PASS/artifact before reporting filtered
> genre-retrieval scores or new walltimes**. New sample
> differs from old unfiltered 80-track cohort; score
> deltas CANNOT be interpreted as a controlled causal effect.
>
> Research details:
> [FMA/MTG catalog methodology](fma-mtg-catalog-overlap-2026-10-21.md),
> [FMA genre validation plan](fma-genre-benchmark-plan.md),
> [cross-dataset evidence](similarity-cross-dataset-evidence-2026-10-21.md).
> No TEST evaluation, PR merge, Lyrion queue/library scan,
> or production metric selection; PR #16 remains Draft.
>

> **MTT FOUR-WORKER BINARY+MUSIC CACHE A/B COMPLETED (21 OCT 2026):**
> [Four-worker run 39602865932](https://github.com/chrober/bliss-mood-poc/actions/runs/39602865932)
> **PASS** ([aggregate artifact 12346509848](https://github.com/chrober/bliss-mood-poc/actions/runs/39602865932/artifacts/12346509848)).
> It reused BOTH caches: previously verified **119,689,247-byte
> 1,019-clip** research package and source-keyed Linux Rust-v5
> binary, verified its cached checksum and CLI; original 2.77-GiB
> download and Cargo toolchain/build **SKIPPED**.
> Four independent Rust-v5 processes (ONNX `--threads 1` each)
> processed all 1,019 clips against the identical 346-triplet
> human questions. **Actual 4-worker inference+SQLite merge:
> 172.324 s**, score 0.929 s. The completed 2-worker paired
> [run 39602475906](https://github.com/chrober/bliss-mood-poc/actions/runs/39602475906)
> needed **291.251 s** inference+merge, 1.053 s score. Thus
> **118.927 s / 40.8% faster observed inference** in these
> two runs; full actual job execution from first/last logs
> **~228 s vs ~367 s**, BUT 2-worker run compiled Rust and
> hosted-runner variability is large. Not a controlled claim
> of general speedup. All **14 metric/head scorecard rows
> and 8 displayed paired contrast rows match exactly** between
> completed two- and four-worker reports; per-track float-bit parity
> not checked from aggregate-only reports.
>
> **COMPLETED PAIRED EVIDENCE:** real 2-worker paired
> [39602475906](https://github.com/chrober/bliss-mood-poc/actions/runs/39602475906)
> PASS, aggregate artifact 12347665613; on the common 293
> MTT human-majority-scorable triplets, Cosine minus
> Centered Cosine **0.0 pp Genre (5/5 discordance),
> −0.3 pp Mood (8/9 discordance)**. Exploratory
> paired IID-triplet and artist-weight sensitivity intervals
> straddle zero in both heads, NOT independent population
> confidence intervals. Cosine minus old Top-K WJ
> +5.1 pp Genre and +21.2 pp Mood when abstentions
> counted as errors. No production winner or independent
> MTT holdout. See
> [paired/performance document](magnatagatune-paired-analysis-2026-10-21.md)
> and [cross-dataset evidence](similarity-cross-dataset-evidence-2026-10-21.md).
> Keep 4 fixed workers provisionally in expensive exploratory
> GH workflow, only change with matched A/B evidence;
> adaptive local scanner not active in this GH runner.
> PR #16 Draft, `main`, PR #13/#17 and private library untouched.
>

> **MTT PAIRED EVIDENCE AND RUST-V5 BINARY CACHE (21 OCT 2026):**
> The confirmed full [curated-audio cache HIT run 39600498519](https://github.com/chrober/bliss-mood-poc/actions/runs/39600498519)
> reported **346 unordered triplets; 53 human-majority ties; 293
> common scorable questions**, 1,019 clips, two Rust-v5 subprocess
> workers, 231.053 seconds inference + merge; complete GitHub run
> 327 seconds. The 1,019-clip audio package was just **119,689,247
> bytes**, CRC-verified against original publisher metadata, and
> prevented the full 2.77-GiB download.
>
> Real scores on a COMMON 293-question denominator, with metric
> abstentions counted as incorrect: **Genre** RMS 63.5%, Cosine
> 65.2%, Centered Cosine 65.2%, Weighted Jaccard 63.8%,
> old Top-K Weighted Jaccard 60.1%, Ranked Top-6 61.8%,
> Ranked Top-12 64.5%. **Mood** respectively 54.6%, 65.5%,
> 65.9%, 61.1%, **44.4% old Top-K with only 71.7% coverage**,
> 62.5%, 64.8%. Cosine-Centered Mood difference ~0.4pp;
> **NOT enough for a metric-winner claim**, same corpus and
> no unseen holdout.
>
> [scripts/mtt_paired_evidence.py](../scripts/mtt_paired_evidence.py)
> and [tests/test_mtt_paired_evidence.py](../tests/test_mtt_paired_evidence.py)
> implement 21 paired contrasts/head (42 total) on the identical
> 293 human-scorable questions, metric abstentions as zero,
> deterministic 600x shared-triplet bootstrap intervals and
> artist-weight dependency *sensitivity* intervals. These are
> **not valid population CIs or a formal independent-cluster
> bootstrap**: all 214 artists are connected. No per-song
> ID, vector or answer is exported. Linux and Windows
> [Python CI 39602141111](https://github.com/chrober/bliss-mood-poc/actions/runs/39602141111)
> PASS. The first synthetic CI failure was a test wording assertion
> only and was corrected without changing math.
> Actual paired 2-worker benchmark
> [39602475906](https://github.com/chrober/bliss-mood-poc/actions/runs/39602475906)
> requires final PASS/artifact verification before quoting
> numerical paired intervals.
>
> Workflow now also caches the pinned exact **Rust-v5 compiled
> binary**, separate from licensed clip cache; verifies SHA256 and
> CLI before use; a MISS builds with locked Cargo and saves it.
> To A/B runtime, the next automatic
> [39602865932](https://github.com/chrober/bliss-mood-poc/actions/runs/39602865932)
> is configured with **four** isolated workers, ONNX 1 thread
> each, vs previous **two** on the same 1,019-clip cohort.
> Do NOT claim a 4-worker speedup or metric parity before
> real run completion.
> Full detailed [scientific/performance handover](magnatagatune-paired-analysis-2026-10-21.md).
> Next: verify both runs, compare paired uncertainty and A/B
> walltimes, cross-reference DEAM/FMA, seek independent perceptual
> test, no production choice. PR #16 Draft; main, PR #13/#17,
> private music unchanged.
>

> **CURATED CACHE REAL MISS→HIT VERIFIED (21 OCT 2026):**
> [First curated run 39599548243](https://github.com/chrober/bliss-mood-poc/actions/runs/39599548243)
> **PASS**: `scripts/mtt_selected_clip_cache.py` packed exactly
> 1,019 CRC-verified referenced MagnaTagATune MP3s into
> **119,689,247 bytes (114.14 MiB)**; all official CRCs/lengths
> verified before Rust-v5. Packaging took **1.18 s**, full recheck
> **0.59 s**. Only this package was saved in `actions/cache`;
> original 2.77-GiB publisher files were deleted and never cached.
> Actual Actions cache storage approx 130.5 MB.
> The exact two-worker Genre/Mood 346-triple benchmark again
> passed with Mood-Cosine **0.6552901** valid-prediction
> majority accuracy. Its analysis+merge took **244.677 s** vs
> **145.505 s** on earlier full-source run: avoid claiming a
> controlled inference speedup from cache alone.
> [Second run 39600498519](https://github.com/chrober/bliss-mood-poc/actions/runs/39600498519)
> verified a **true cache HIT**: publisher source ZIP download
> and repack steps were SKIPPED, package reverified from original
> 8-MiB central-directory tail; check final Actions result and
> fourteen-row head×metric scorecard before reporting total timings.
> Dedicated offline tests for complete, corrupt/missing clip caches
> and scorecard run in Linux/Windows
> [Python CI 39600399370](https://github.com/chrober/bliss-mood-poc/actions/runs/39600399370)
> PASS. The 346 unique triplets are fully exploratory, with
> **NO independent MagnaTagATune holdout** remaining.
> Further tasks: compare MISS/HIT true stage times, compile
> all-metric coverage/abstention scorecard, improve build
> reuse and do dependence-aware uncertainty analysis across
> co-occurring artists; corroborate on DEAM, FMA, and independent
> human similarity sources before any production metric choice.
> No music in git or upload-artifact; GH caches not confidential.
>

> **CURATED MTT AUDIO CACHE — 21 OCT 2026:**
> User approved caching **ONLY 1,019 actually referenced MagnaTagATune
> MP3 clips**, rather than the 2.77-GiB original ZIP parts. New
> [scripts/mtt_selected_clip_cache.py](../scripts/mtt_selected_clip_cache.py)
> builds a lossless, deterministic **ZIP_STORED curated research cache**
> of approximately 117 MB (real size must be checked in Actions), with
> SHA-256-hashed internal names, exact 1,019-file cardinality, and
> original-publisher MP3 length + CRC cross-checks. Original 3-part
> archive downloaded *once on cache miss*, immediately deleted after
> packing and never uploaded or cached. Cache hit only fetches original
> CSV metadata plus 8-MiB ZIP directory tail, validates all 1,019 audio
> payloads, then Rust-v5's **two independent workers** process cached
> bytes. Automated feature-branch workflow uses
> [actions/cache/restore](../.github/workflows/magnatagatune-all-exploratory.yml)
> and cache/save with fixed source identity, manual `cache_audio`
> defaults true and can be disabled. GitHub caches **are not private**,
> third-party CC BY-NC-SA research audio remains subject to access and
> license conditions; no music is ever uploaded as an artifact or git.
>
> **REAL QUALITY BASELINE VERIFIED:**
> [346-triplet run 39597229438](https://github.com/chrober/bliss-mood-poc/actions/runs/39597229438)
> PASS: 1,019 real clips, all seven metrics/both heads,
> two parallel isolated SQLite workers; **145.505 s inference+merge**,
> 145.714 s audio-analysis+scoring, 0.209 s evaluation alone.
> Mood cosine ~**0.6553** majority agreement on *defined*
> predictions (not all-question/holdout accuracy). All 346 triplets
> exploratory => **NO independent MTT holdout remains**.
> Curated-cache seed run
> [39599548243](https://github.com/chrober/bliss-mood-poc/actions/runs/39599548243)
> must be examined for completed outcome and actual saved package
> size; **a second true cache-hit run is required** to measure any
> build/download speedup. The synthetic 1,019-member CRC/cache tests
> [Python CI 39599073019](https://github.com/chrober/bliss-mood-poc/actions/runs/39599073019)
> passed Linux/Windows. See the
> [updated sparse-audio benchmark doc](magnatagatune-sparse-audio-benchmark-2026-10-21.md).
> Next: verify cache MISS→HIT timing and metric parity, run
> paired / artist-sensitive confidence intervals on 346 triplets,
> cross-check DEAM/FMA/MTG and seek independent human similarity
> reference for final production metric choice. Do not use MTT as
> an independent held-out test, merge PRs, or rescan private music.
>

> **FULL 346-TRIPLET EXPLORATORY MTT & CACHE POLICY (21 Oct 2026):**
> The user decided to score **ALL 346 unique unordered triplets /
> 1,019 distinct MagnaTagATune clips**, consuming the 48
> previously untouched artist-holdout candidates. This is explicitly
> **exploratory only; there is NO remaining independent MTT holdout**.
> New `scripts/benchmark_magnatagatune.py --selection-mode all-exploratory`
> uses pinned source file hashes and exact 346/1019 cardinality.
> New `scripts/mtt_parallel_workers.py` uses **2 concurrent isolated
> Rust-v5 processes, --threads 1 each**, separate schema-v3 SQLite
> sidecars, validated/merged only after completion; no shared
> concurrent SQLite writer. `scripts/mtt_local_archive.py` can read
> ZIP members from the three staged publisher files without per-clip
> HTTP calls. Real job
> [39597229438](https://github.com/chrober/bliss-mood-poc/actions/runs/39597229438)
> was triggered; check actual completed outcome/artifacts BEFORE
> claiming 346-triplet scores or parallel performance.
> Workflow [.github/workflows/magnatagatune-all-exploratory.yml](../.github/workflows/magnatagatune-all-exploratory.yml)
> runs only on its own file update or manual dispatch.
>
> **Audio cache is opt-in** via manual `workflow_dispatch`
> `cache_audio: true`, not enabled by default. The full licensed
> archive is 2.77 GiB, a large fraction of GitHub default
> 10-GiB repository cache; default inactivity eviction ~7 days.
> Caches are accessible to certain PRs/forks, so review research
> CC BY-NC-SA 3.0 rights and accessibility before storing the audio.
> Even a cache hit must pass publisher size + MP3 CRC checks; always
> measure hit/restore vs publisher download, not assume it is faster.
> No raw audio, per-track features or private data in run artifacts.
> See [sparse audio doc](magnatagatune-sparse-audio-benchmark-2026-10-21.md).
>


**Historical snapshot date:** October 21, 2026, Europe/Vienna.  
**Repository:** [chrober/bliss-mood-poc](https://github.com/chrober/bliss-mood-poc)  
**Branch:** `feat/similarity-metric-evaluation`  
**Pull request:** [#16 — Evaluate Genre and Mood similarity metrics](https://github.com/chrober/bliss-mood-poc/pull/16), **Draft, not merged**.  
**Original head revision when this historical snapshot was authored:**
`b5827a6b30c07c874f1570b2e8d9e6a7e1e9f12b`.
Always check the current GitHub branch head before acting.
The current research status is in the
[central roadmap](similarity-lyrion-roadmap.md).

## FMA Genre benchmark corrected run CONFIRMED PASS

[Workflow run 39583233757](https://github.com/chrober/bliss-mood-poc/actions/runs/39583233757)
has **completed successfully**, with
[aggregate report artifact 12338242831](https://github.com/chrober/bliss-mood-poc/actions/runs/39583233757/artifacts/12338242831).
Canonical FMA-Small contained three unexpectedly sized MP3s. New
quality gate excluded exactly those while retaining 7,997 playable
candidate files. Fixed seed: **80 distinct artists**, 10 tracks
per genre from the official **Validation** split, all processed with
pinned corrected Rust-v5. Official FMA **TEST** split untouched.

Genre retrieval Precision@5 across seven methods: RMS .3175,
Cosine .3500, Centered Cosine .3525, Weighted Jaccard .3550,
historical cutoff Top-K .3150, ranked Top-6 .3150,
ranked Top-12 .3400; random baseline .113924.
See docs/fma-genre-benchmark-plan.md for full mAP@10/nDCG@10,
limits, actual GH timing, license/provenance caveats.
**No metric winner** or unreported test-split optimization permitted.

GitHub Actions on PR #16 now has separated push-only path-filtered
Rust and Python CI; observed docs-only commits did NOT run these
workflows. GH native pull_request paths would use cumulative PR
diff and be ineffective at suppressing doc-only pushes here.
Per-song benchmark loops are serial; no adaptive Rust workers.
Separate safe batched-worker A/B is the next optional speed study.

## GitHub Actions CI/FMA status correction (21.10.2026)

Real FMA-Small validation run
[39581435733](https://github.com/chrober/bliss-mood-poc/actions/runs/39581435733)
**failed before feature extraction**: ZIP downloads were successful,
but an unexpectedly sized MP3 anywhere in the archive raised
`ValueError: Suspicious FMA audio member size`.
The importer now skips isolated suspect MP3 members while requiring
sufficient archive coverage, with fail-closed synthetic tests.
Corrected real FMA run
[39583233757](https://github.com/chrober/bliss-mood-poc/actions/runs/39583233757)
must be checked for completed artifact before quoting metrics.

Old unfiltered Rust checks had both unscoped push and pull_request
triggers and therefore ran twice per feature-branch commit, including
docs-only commits. They were split into Rust-only ci.yml and dedicated
Python+PowerShell python-checks.yml, both now **push-only** and
path-filtered for source vs scripts/tests; docs-only updates trigger
neither. Other workflows were inventoried and have no exact same
duplicate all-branch push+PR setup. Full methodology and caveats:
[GitHub Actions trigger/worker audit](github-actions-trigger-and-worker-audit-2026-10-21.md).

Parallelism: dataset benchmarks execute `bliss-mood analyze-features`
serially, `--threads 1`, so Rust adaptive scanner workers are **not**
used. They require `scan-features`/Bliss database path rather than
the current per-file workflow. A small controlled A/B of fixed two
workers and a sidecar-safe batch scheduler is a separate task;
no unverified performance improvements claimed.


## New frozen 31-triplet MTT artist-only development CI

`scripts/benchmark_magnatagatune.py --selection-mode frozen-development`
and [new dedicated GH workflow](../.github/workflows/magnatagatune-development.yml)
now enforce the registered SHA-256 cutoff 128/256. The entire
**31-question** artist-only development set is selected without using
human vote consensus; the script verifies source metadata fingerprint
before downloading any media. It excludes all **56 artist-only holdout
candidates** and 259 mixed-artist questions. The **48 candidates
not exposed by the earlier smoke remain untouched**.

Real first-run [39593423801](https://github.com/chrober/bliss-mood-poc/actions/runs/39593423801)
FAILED at MP3 22/92 due to transient curl timeout 28 / HTTP 000.
Twenty-one preceding real tracks passed CRC/audio analysis; no
metric scores or artifact. Bounded HTTP range retries with strict
206 response and ZIP CRC gates added and checked in Linux/Windows
[Python CI 39594080260](https://github.com/chrober/bliss-mood-poc/actions/runs/39594080260).
A retry [39594161136](https://github.com/chrober/bliss-mood-poc/actions/runs/39594161136)
was started; verify completed outcome and aggregate-only artifact
before reporting its metric results. See
[research protocol](magnatagatune-sparse-audio-benchmark-2026-10-21.md).
Development results must not be described as independent/production
evidence. No change to PR #13, PR #17, main, Lyrion queue or private
library analysis.

## MTT sparse-audio end-to-end PASS, with artist-holdout limitation

- ZIP central directory audit
  [39589694423](https://github.com/chrober/bliss-mood-poc/actions/runs/39589694423)
  **PASS**, using only HTTP Range 8 MiB from last archive part.
  All **1,019** required MP3 paths found uniquely; ZIP has 25,863
  entries, total 2,972,769,864 bytes. Required individual compressed
  MP3s sum to 116,910,845 bytes. **533 vote rows are only 346 unique
  unordered triplets** (permutations/repetitions need grouping).
- Development-only sparse audio smoke
  [39590801662](https://github.com/chrober/bliss-mood-poc/actions/runs/39590801662)
  **PASS** with true pinned corrected Rust-v5, both classifier heads,
  all seven metrics, twelve verified ZIP MP3s in four high-consensus
  artist-separated questions. Real HTTP transferred **1.386 MB**,
  analysis/sparse download **14.477 s**, serial one worker / ONNX
  `--threads 1`. Weighted and majority agreement for Mood Cosine both
  **0.75** on deliberately selected *development* questions.
  No best metric or generalization conclusion.
- Artist graph/holdout feasibility
  [39591601421](https://github.com/chrober/bliss-mood-poc/actions/runs/39591601421)
  **PASS**: 214 artist strings and 346 unique triplets form
  **one single connected co-occurrence component**. A strict connected
  artist-disjoint 80/20 holdout is impossible. Deterministic per-artist
  hash partition yielded **162 dev / 4 holdout / 180 excluded mixed**
  questions. Four independent held-out triples are not adequate for
  choosing among seven metrics. Prior smoke must NOT be considered
  held out; may contaminate naive post-hoc partitions.

Details: [sparse benchmark protocol](magnatagatune-sparse-audio-benchmark-2026-10-21.md).
Next: carefully define an *exploratory* analysis of all 346
grouped questions, with dependence-aware uncertainty, and obtain an
additional separate human-perceptual-similarity dataset for final
confirmation. Continue recording download/Cargo build/inference
stage timings. PR #16 remains Draft, main and PR #13/#17 untouched.

## LATEST: MTT sparse-audio E2E and artist-disjoint 48-question holdout

**21 October 2026, Draft PR #16.** No changes to PR #13, PR #17,
main, personal music, user labels, Lyrion playback or distribution.

- Real multipart ZIP membership [Actions 39589694423](https://github.com/chrober/bliss-mood-poc/actions/runs/39589694423)
  **PASS**: verified 25,863 ZIP MP3 entries via an **8-MiB**
  ranged ZIP-tail request; **all 1,019** clip MP3 paths needed for
  533 human comparison rows found without downloading audio.
  The 533 rows correspond to only **346 distinct unordered triplets**.
  Compressed member bytes required for all 1,019 clips: **116,910,845**;
  entire source archive: **2,972,769,864 bytes**.
- Sparse real-audio [Actions 39590801662](https://github.com/chrober/bliss-mood-poc/actions/runs/39590801662)
  **PASS**: four high-consensus, artist-distinct development triplets,
  12 real clips, actual source ZIP member extraction and CRC verification,
  pinned genuine Rust-v5 in separate PR #17 checkout. All seven original
  metrics, both model heads, schema-v3 read-only evaluation.
  **1,385,735 audio bytes** transferred via bounded Range requests;
  **14.477 s** for network+clip inference with **one worker,
  `--threads 1`**, 0.019 s for scoring. Mood-Cosine selected
  majority winner on 3/4 questions, **smoke only, NOT model validation**.
  Aggregate-only artifact [12341406678](https://github.com/chrober/bliss-mood-poc/actions/runs/39590801662/artifacts/12341406678);
  no audio or feature vectors uploaded.
- Independent artist grouping **cannot** split the entire original MTT
  corpus into multiple connected-component-disjoint partitions:
  all 214 artist strings and 346 unique triplets form **one connected
  component**. This is an important limitation of the dataset.
- Metadata-only design audit [39592331265](https://github.com/chrober/bliss-mood-poc/actions/runs/39592331265)
  **PASS**: candidate artist-hash holdout reserves at ~20%, ~33%,
  50% produced development/holdout/mixed-excluded counts
  **162/4/180**, **86/13/247**, and **31/56/259**, respectively.
  A **fixed 50% artist-hash policy** was chosen using metadata and
  artist coverage only, never similarity scores.
  **Eight** of the 56 potential holdout triplets share an artist
  with the previous four-triplet smoke; exclude them. Thus **48
  not-previously-exposed holdout questions** remain, each artist
  disjoint from the 31 development-only questions under the
  normalized-name grouping. Tiny and distribution-shifted; not an
  independent-discography/Discogs-encoder guarantee.
  Audit speed: ~0.23 s and ~55 MiB peak RSS, no audio.
- Regression tests Linux and Windows [39592264225](https://github.com/chrober/bliss-mood-poc/actions/runs/39592264225)
  **PASS**. Earlier failed intermediate CI from synthetic low-consensus
  fixture (5/3/1) was corrected to truly high-consensus synthetic votes
  (8/1/1), not by reducing validation gates.
- The earlier failed duplicate ZIP index workflow was removed; retain
  only the successful bounded tail reader and its separate small
  audio-development workflow to avoid duplicate expensive CI runs.

**NEXT MUST-DO BEFORE MORE AUDIO:** The current MTT audio smoke selector
predates the 50% artist partition. Explicitly enforce the frozen
artist-hash development partition (and exclude the 48 unexposed
holdout questions) in any expanded development-run code; test
artist/sample disjointness. Pre-register consensus/tie/abstention
policies, paired uncertainty and acceptable performance criteria
before evaluating holdout **once**. For population-level evaluation
the original dataset has strong connected-artist dependencies;
seek a separate source of human similarity judgments for independent
confirmation. Never pick production metric from four selected
triplets or claim this 48-question holdout has strong statistical power.

Full design and results:
[MTT sparse-audio benchmark](magnatagatune-sparse-audio-benchmark-2026-10-21.md).

## COMPLETED: two official audio-free preflights (21.10.2026)

**MTG-Jamendo**: [GitHub Actions 39586686845](https://github.com/chrober/bliss-mood-poc/actions/runs/39586686845)
PASSED using pinned upstream split-0 TSVs and Essentia JSON model metadata:
Genre (87 tags): train 32572, validation 11043, test 11479;
Mood/Theme (56 tags): train 9949, validation 3802, test 4231.
No artist-ID or track-ID overlaps **within the official splits**.
This does NOT establish the exact published ONNX model training
provenance or Discogs encoder data independence.

**MagnaTagATune**:
[GitHub Actions 39587323227](https://github.com/chrober/bliss-mood-poc/actions/runs/39587323227)
PASSED. Actual 533 human outlier triplets / 7650 votes
require only **1019 unique audio clip paths**;
87 tied-majority questions, 228 unique >=70% consensus and
160 unanimous, 903 distinct apparent track groups. Of 31382
clip metadata rows, 5519 lack MP3 paths. No audio accessed.
Real format-specific parser and synthetic dialect tests
included in separate Linux/Windows CI, last
[39587511195](https://github.com/chrober/bliss-mood-poc/actions/runs/39587511195) PASS.

Research results, schema/rights limitations and GH runtime policy
documented in
[external evidence preflight results](external-evidence-preflight-results-2026-10-21.md).
First trial odd-one-out audio evaluation should use only
the needed 1019 clips, but must first verify split ZIP archive
member mapping, download rights/size and holdout grouping
by original artist/album/song. Then compare all seven
metrics with vote ties and abstentions. Do not claim best
production metric, independent ONNX training test, or
commercial redistribution rights. No main merge or local
Rust build. Existing PR #16 Draft, #13/#17 untouched.

## CURRENT PRIORITY — externally validated DEAM and FMA evidence (21.10.2026)

User explicitly requested to continue fully on GitHub Actions, without
further subjective eight-song analysis. PR #16 Draft remains active,
main and Draft PR #13/#17 unchanged, no private library scan/build.

**DEAM**:
- Real unfiltered 240-song research run
  [39577605466](https://github.com/chrober/bliss-mood-poc/actions/runs/39577605466)
  PASS: 192 earlier excerpts, 48 full songs from 2015.
  Mood Head vs human Valence/Arousal proximity macro query Spearman:
  RMS .2277, cosine .2421, centered cosine .2471, weighted Jaccard
  .2507, cutoff-based Top-K .1558 on 218/240 valid queries,
  ranked top-6 .2250, ranked top-12 .2351.
- Metadata-only DEAM vs MTG-Jamendo catalog screen
  [39579084649](https://github.com/chrober/bliss-mood-poc/actions/runs/39579084649)
  PASS: 1,801/1,802 joinable DEAM artist/title records, 56,552 MTG
  metadata records, 60 older + 15 full-song potential exact catalog
  matches. Never confuse matching metadata with proven training-set
  overlap or absence of matches with proven independence.
- Filtered 240-song run
  [39579552118](https://github.com/chrober/bliss-mood-poc/actions/runs/39579552118)
  PASS: excluded 75 potential catalog matches, 1,727 candidate tracks,
  sampled 197 older and 43 full-song examples.
  Mood mean query Spearman: RMS .2711, cosine .2868,
  centered cosine .2813, weighted Jaccard .2888,
  historic cutoff Top-K .1903 on 216/240 queries,
  ranked top-6 .2721, ranked top-12 .2745.
  **Unfiltered and filtered samples are NOT paired or directly
  causal-comparable; no metric winner.** Earlier cohort cosine .3400,
  2015 full-song cohort cosine .1876.
- Docs: docs/deam-similarity-benchmark.md, scripts/benchmark_deam.py,
  scripts/audit_deam_mtg_overlap.py and dedicated GitHub workflows.

**FMA Genre**:
- Official FMA-Small metadata preflight
  [39580107275](https://github.com/chrober/bliss-mood-poc/actions/runs/39580107275)
  PASS: 8,000 tracks, eight genres with 1,000 each; 6,400 training,
  800 validation, 800 test; **zero artist-ID overlap across splits**.
- scripts/benchmark_fma_genre.py and its Linux/Windows synthetic
  tests implement source-genre retrieval P@5, mAP@10, nDCG@10,
  query coverage and abstention for all seven metrics on a balanced
  artist-unique validation-only cohort.
- First live 80-track FMA validation run
  [39581435733](https://github.com/chrober/bliss-mood-poc/actions/runs/39581435733)
  was started using original 7.2-GiB FMA-Small ZIP,
  individual streamed extraction and pinned Rust-v5 from separate
  commit 2c3d44401436b3b41b6e067199016a1ed2335fbf.
  **Check actual run outcome/artifact before claiming success.**
  The official FMA test split is untouched. Dataset provenance,
  audio/metadata licenses and external validity must remain explicit.
- Docs: docs/fma-genre-benchmark-plan.md.

**Next:** Inspect FMA real-run result, repair only evidenced failures,
document aggregate Genre Retrieval against random-class baseline.
After validation-only exploratory checks, pre-register a candidate metric
and verify once on artist-disjoint official FMA TEST data in a separate
workflow/run. Do not optimize on the held-out test split or infer real
playlist musical coherence from coarse genre labels alone.

## CONFIRMED CI MILESTONE — DEAM Rust-v5 E2E smoke PASSED

GitHub Actions [run 39576010217](https://github.com/chrober/bliss-mood-poc/actions/runs/39576010217)
**completed successfully** with pinned corrected Rust-v5 source from the
separate PR #17 commit 2c3d44401436b3b41b6e067199016a1ed2335fbf
(**no merge**) and all seven metrics on 12 DEAM tracks. The official
archives mapped all 1,802 audio items to human annotations. No track audio,
per-track scores or personal labels were uploaded; only the aggregate
[report artifact 12333973414](https://github.com/chrober/bliss-mood-poc/actions/runs/39576010217/artifacts/12333973414).
Synthetic Linux and Windows tests also passed.

Mood head vs human **VA proximity** query Spearman on N=12:
RMS .301; cosine .308; centered cosine .280; weighted Jaccard .252;
historical cutoff Top-K .387 (only 6 valid queries); ranked Top-6
.474; ranked Top-12 .345. Genre correlations to VA were also computed
but **are not a Genre validation**. These are diagnostic smoke scores
only: no best metric, no unbiased benchmark, no calibration.
See docs/deam-similarity-benchmark.md for full table and caveats.

**Next:** scale to larger DEAM cohort after confirming sample protocols
and potential MTG-Jamendo overlap; implement independent FMA genre-label
benchmark as separately gated follow-up. No manual eight-pair deep
analysis needed. Keep PR #16 Draft, main and PR #13/#17 unchanged.

## CURRENT PRIORITY — automated external DEAM benchmark in PR #16 (21.10.2026)

**User expressly decided to STOP focusing on subjective eight-pair analysis
and use externally sourced scientific evidence.** The first eight listening
judgments and both local JSONs have been interpreted and archived as
exploratory only; they are not the next action.

The user approved a GitHub Actions-based pipeline: **DEAM first, FMA later**.
Changes on the existing PR #16 research branch:
- scripts/benchmark_deam.py: official static song-level 1..9 Valence/Arousal
  annotations, numbered MP3s, deterministic selection, existing Rust-v5
  analyze-features and schema-v3 SQLite sidecar, all seven methods per head,
  macro-average query Spearman by Valence/Arousal/both; aggregate-only JSON.
- tests/test_benchmark_deam.py: offline synthetic archive and SQLite tests,
  incorporated into .github/workflows/ci.yml on Linux and Windows.
- .github/workflows/deam-benchmark.yml: first limited real 12-song DEAM
  research smoke on GitHub-hosted ubuntu-24.04, plus workflow_dispatch
  for later larger runs; downloads official reference ONNX+metadata and
  licensed DEAM audio/annotation archives. Uploads aggregate report only.
- docs/deam-similarity-benchmark.md: full implementation, provenance,
  license and bias caveats.

**Important:** The workflow was first started at commit 476f03d but failed
before download/build because Cargo.lock is not tracked on this branch and
--locked refused to generate it. This was corrected at commit 65810b9:
ordinary cargo build --release in ephemeral runner; tracked Cargo.lock is
a future reproducibility improvement. Check new DEAM workflow run
39575405139 and subsequent runs for exact final status; do NOT claim a
passed real-audio benchmark without completed download, analysis and
aggregate artifact. Ordinary Rust and synthetic Python CI have passed so far.

External research pitfalls: DEAM contains Jamendo music, so overlap with
MTG-Jamendo training may invalidate an "independent" claim. Song-level
Valence/Arousal distance is a PROXY for similarity, not human genre pairwise
ground truth. Genre-vs.-VA is a negative/control axis, not proof of Genre
quality. DEAM's manual specifies CC BY-NC and citations. Never commit raw
audio, annotation ZIPs, music IDs, sidecars or per-track vectors. No production
metric selection, no main merge, PR #13 and PR #17 untouched, no user music
rescan, no local Rust builds.

**Next:** Monitor the real DEAM smoke workflow outcome, resolve actual
download/archive/model/backend issues based on logs, inspect aggregate
results, then design a larger stratified benchmark and separate FMA Genre
workflow. Keep PR #16 Draft.


**Updated validation gate:** real DEAM run 39575405139 passed source downloads,
1,802 audio/annotation ID matching and all twelve calls to analyze-features,
but correctly **refused to report v4 feature scores as v5**. PR #16's own
features.rs says experimental-essentia-audio-v4-unvalidated. The workflow now
uses a separate **immutable checkout of genuine Rust-v5** from PR #17 commit
2c3d44401436b3b41b6e067199016a1ed2335fbf (including its Cargo.lock);
this does **not** merge/edit PR #17 or main. Check DEAM workflow run
39576010217 for build, real evaluation and final artifact status. Do not
claim success of real end-to-end scientific benchmark until this completes.

## First eight local human judgments — verified exploratory pilot

**Already analyzed locally** with a read-only
`similarity-first8-labeled.json` report.
Original listening CSV, feature DB, audio and
per-pair scores remain **only on the user's
machine** and must not be committed.

The reviewed CSV was originally semicolon-delimited;
`Import-Csv` without `-Delimiter ';'` and the
old comma-only evaluator misread labels.
A separate comma-formatted copy was used
without changing any judgments, and the
read-only evaluation succeeded. Later
per-pair diagnostics accept both delimiters.

- **Eight judged pairs per head**, no missing
  compatible head vectors.
- **Genre:** zero positive and eight negative
  human judgments. Genre ROC-AUC is `null`
  for all seven methods because no positive
  class exists.
- **Mood/Theme:** four positive and four
  negative. ROC-AUC by method:
  RMS **0.5000**, Cosine **0.5625**,
  Centered Cosine **0.5625**,
  Weighted Jaccard **0.5000**,
  historical absolute-cutoff Top-K
  **0.3750**, Ranked Top-6 **0.3125**,
  Ranked Top-12 **0.5000**.
- In the historical cutoff-based Top-K,
  all four positive Mood pairs scored zero,
  three negatives scored zero, and one
  negative scored 0.7603. In the wider
  *unlabeled* random sample, **1,835 of
  2,979 defined** Mood-pair scores were
  zero, plus 21 undefined scores.
- The 3,000 random pairs per head were
  **not** 3,000 human ratings. Four Mood
  positives against four Mood negatives
  produce only 16 positive-negative
  score comparisons; `0.5625 = 9/16`
  after the tie policy.
- Pair selection was **metric-driven**,
  hence pilot AUC is selection biased.
  The user expressed uncertainty over
  some listening labels; preserve them
  verbatim, do not derive replacements
  from ONNX scores or filenames. Confidence
  was not collected in this original pilot.

Next controlled human evidence should
include independently human-rated
positive Genre controls, clear negatives,
challenge pairs where representations
disagree, and separate criteria for
Genre, Mood/energy, audible similarity
and next-song suitability. Use a small
~12-contrast instrument test, then a
new, previously unseen 24–40-pair block;
do **not** retrofit old labels or
call the pilot a production validation.

The original selection audit
`selection-audit-private.json`
must not be used as human ground truth.
PR #16 remains Draft; do not alter
the mixer or private playlist queue.

## Current engineering status — targeted read-only diagnosis is ready (21.10.2026)

After the user explicitly requested to continue, PR #16 gained
a compact per-pair read-only diagnostic mode in scripts/evaluate_similarity.py:
--pair-details-only with --db, --labels and --include-experimental. It
reuses the original seven metric implementations and cohort checks;
it does **not** evaluate 3,000 random pairs, run audio/ONNX,
rescan music, write SQLite or inspect selection-audit-private.json.
Both semicolon- and comma-separated reviewed CSV files are accepted.
Unit tests cover semicolon labels, preserved independent judgments,
per-pair score/AUC consistency and database immutability.

**Next user action:** run the new diagnostic on their existing LOCAL
Rust-v5 sidecar and original listening-pairs-review-first8.csv. Write a
NEW ignored local file similarity-first8-pair-details.json, keeping the
already successful similarity-first8-labeled.json and the CSV intact.
Verify model cohort keys, per-head judged counts and the seven AUCs
match the existing aggregate report before conclusions. The aggregate
report tells us only that the highest negative Mood cosine score is
0.9769996802087874, and the lowest positive is 0.7140565571739185;
it does NOT identify which listening pair is responsible. Never guess
from filenames: obtain concrete per-pair scores before discussion.

**Research follow-up after local result:** distinguish classifier/
vector failure, metric mismatch and subjective differences in listening
criteria. Keep all original labels, explicitly ask about label
certainty if helpful, and consider independently selected positive
Genre examples. No metric-selection or mixing-strategy conclusion yet.

Private scores/track identities, CSV and JSON must not be committed.
PR #16 Draft only, PR #13/#17 and main untouched. Any PowerShell
instructions must use the full & { ... } format.

## Original local listening setup and lessons learned (English historical digest)

The first pair-selection script used
[`propose_similarity_listening_pairs.py`](../scripts/propose_similarity_listening_pairs.py)
on an existing **100-song** corrected
Rust-v5 head-feature sidecar and sampled
3,000 unlabelled pairs per head.
Seven separate functions were compared:
RMS, cosine, centered cosine, weighted Jaccard,
historical cutoff Top-K with threshold 0.10,
ranked Top-6 and ranked Top-12 Jaccard.
The selection procedure selected 24 listening
pairs across eight heuristic strata and
produced a private selection-audit file.
The first eight came from that candidate list.

### Unlabelled numeric distribution diagnostic

This table describes only numerical
properties of the **same 100-song sample**,
not measured human perceived quality.

| Metric | Genre median | Mood median | Genre zero scores | Mood zero scores |
| --- | ---: | ---: | ---: | ---: |
| RMS | 0.8651 | 0.9241 | 0% | 0% |
| Cosine | 0.5344 | 0.6564 | 0% | 0% |
| Centered cosine | 0.4481 | 0.4148 | 0% | 0% |
| Weighted Jaccard | 0.3115 | 0.4105 | 0% | 0% |
| Historical cutoff Top-K | 0.1638 | 0.0000 | 17.2% | 61.6% of 2,979 defined Mood scores |
| Ranked Top-6 | 0.1729 | 0.1826 | 7.7% | 7.8% |
| Ranked Top-12 | 0.2196 | 0.2149 | 0.1% | 0.1% |

Eight of 100 songs had their maximum Mood
activation below 0.10. Median count of
Mood labels exceeding 0.10 was two,
versus five for Genre. The original
Mood cutoff-Top-K had 21 undefined
outcomes from 3,000 sampled pair
comparisons. These show the limitations
of a fixed threshold, not a human
similarity ground truth.

The 24 pairs had the following
metric-driven selection strata:
`high_both` 4,
`mood_high_genre_low` 4,
`genre_metric_disagreement` 3,
`mood_metric_disagreement` 3,
`low_both` 3,
`low_mood_activation` 3,
`random_control` 3 and
`genre_high_mood_low` 1.
This selection creates known bias
that prevents generalizing the
eight-pair pilot AUC to the full library.

### Exact Lyrion song/queue mapping

The original listening queue experiment
used relative `TracksV2.File` keys,
while Lyrion `songinfo` requires
**full valid source URLs**. The initial
catalogue-wide scan was excessively slow
(77,387 library items); the corrected
[`queue_similarity_pairs_lyrion.ps1`](../scripts/queue_similarity_pairs_lyrion.ps1)
uses exact, targeted `songinfo`
lookups and a stable player ID
instead of display-name matching
(which is fragile for Unicode).
The source root on the Pi and private
player identifiers must stay local.

The listening sequence required
**16 queue positions, but only 15
distinct song IDs** because one
song recurred at a pair boundary.
The old bulk `playlistcontrol cmd:add`
deduplicated the repeated item:
it appended 15, not 16 tracks,
despite mutating the queue first.
The corrected script appends IDs
individually, checks each increment,
validates all 16 ordered positions
and detects the already existing
15-track legacy sequence before
writing. There is **no authorization
to enqueue a new list automatically**
from this handover.

### Private inputs and CSV safeguards

The user already has the previous
feature-sidecar DB, original proposed
pair list, first-eight review CSV,
unlabeled diagnostics, and private
selection audit stored locally.
Do not commit these files or infer
their current existence solely
from this historical record.
`left` and `right` in the review CSV
are exact original `TracksV2.File`
keys; do not rewrite them by artist
or title. `genre_label` and
`mood_label` encode separate human
judgments: `1` positive, `0`
negative, blank intentionally
not rated. Each retained row must
have at least one label. Preserve
any semicolon original and use an
explicit delimiter or the parser's
automatic comma/semicolon support.

If the user explicitly requests
further local diagnostics,
[`evaluate_similarity.py`](../scripts/evaluate_similarity.py)
can run its read-only `--pair-details-only`
mode using a compatible SQLite sidecar,
the reviewed CSV and the
`--include-experimental` flag.
It never writes existing feature DBs
or rescores the entire library.
Do not infer per-pair errors from
the aggregate ROC-AUC alone.

### Scientific and branch boundaries

Earlier Rust-v5/C++ reference measurements
on a 100-MP3 corpus and additional
WAV/FLAC controls were encouraging;
they did **not** establish subjective
music quality or complete
production platform validation.
The broad phase-0 extraction parity
and distribution gates remain open
in the [current roadmap](similarity-lyrion-roadmap.md).

Always keep `main`, PR #13,
PR #17 and the production mixer
unchanged. GitHub Actions performs
builds rather than an unrequested
local Windows Rust build. Never
upload private audio, local filenames,
full listening CSVs, labels or
individual score vectors to CI.
For PowerShell tasks, provide
a complete standalone `& { ... }`
script as required by
[PowerShell conventions](powershell-script-conventions.md).

### Later scientific results and references

The direct 1280D-vs-head comparison on
the same 1,019 MTT clips, fixed fusion
ablations, screened 80-song FMA
VALIDATION retrieval and DEAM
source-blocked paired study are
separately documented in:
[MTT A/B](similarity-audio-embedding-ab-results-2026-10-21.md),
[fixed rank fusion](similarity-fixed-rank-fusion-research-2026-10-21.md),
[FMA paired](similarity-fma-embedding-ab-2026-10-21.md),
[DEAM](deam-similarity-benchmark.md),
and [research roadmap](similarity-lyrion-roadmap.md).
No MTT holdout remains; FMA official
TEST was not inspected. No
production method has been selected.
