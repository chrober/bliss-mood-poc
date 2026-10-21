# Chat handover — adaptive offline feature scans (2026-10-19)

> **UPDATED MTT HOLDOUT METADATA AUDIT, 21 OCT 2026:**
> [GitHub Action 39592331265](https://github.com/chrober/bliss-mood-poc/actions/runs/39592331265)
> successfully checked artist-hash sensitivity without any new audio
> inference or human metric inspection: cutoff 51/256 gives 162 dev /
> 4 candidate holdout / 180 excluded mixed; cutoff 85 gives 86/13/247;
> cutoff 128 gives **31 dev / 56 potential holdout / 259 excluded**.
> Under cutoff 128, 8 of 56 potential holdout triplets share artists
> with the prior four-question smoke; the remaining **48** were not
> exposed in that run. This DOES NOT eliminate the one-giant-artist
> component or establish population/generalization reliability.
> Freeze one artist split and exclusions BEFORE scoring the 48
> candidate test questions, and never optimize using their labels
> or model performance. See
> [sparse-audio methodology](magnatagatune-sparse-audio-benchmark-2026-10-21.md).
>
> **MTT SPARSE REAL AUDIO E2E PASS + HOLDOUT LIMIT, 21 OCT 2026:**
> [ZIP membership 39589694423](https://github.com/chrober/bliss-mood-poc/actions/runs/39589694423)
> **PASS** using only 8 MiB HTTP Range tail: all **1,019** referenced MP3s
> found among 25,863 ZIP members, 0 ambiguous/missing. Three consecutive
> ZIP parts total 2,972,769,864 bytes; needed compressed MP3 member sizes
> sum to 116,910,845 bytes. **533 ordered records reduce to 346 unique
> unordered triplets**, requiring aggregated clip-ID votes.
> [Real Rust-v5 sparse-audio workflow 39590801662](https://github.com/chrober/bliss-mood-poc/actions/runs/39590801662)
> **PASS**: 4 deliberately high-consensus artist-disjoint DEVELOPMENT triples,
> 12 clips CRC checked, 12 bounded HTTP 206 requests transferring only
> **1,385,735 bytes**, 14.48 seconds transfer+feature inference.
> Both heads and seven metrics ran, result aggregate-only. Mood cosine
> got 3/4 majority choices, **NOT generalization evidence**; most job
> overhead was building Rust-v5 (~88 sec). See
> [sparse audio benchmark doc](magnatagatune-sparse-audio-benchmark-2026-10-21.md).
>
> **CRITICAL SCIENTIFIC FINDING:** artist-group preflight
> [39591601421](https://github.com/chrober/bliss-mood-poc/actions/runs/39591601421)
> shows **ALL 214 artists + 346 unordered triples in ONE connected
> artist co-occurrence component**. Strict component-disjoint 80/20
> holdout impossible without dropping triples. Hash-based artist
> split gave 162 development, only **4** held-out, 180 mixed excluded.
> This is scientifically inadequate for metric selection. Do NOT
> present four selected development triples as independent test data.
> Future work: larger descriptive MTT evaluation with dependence/vote
> uncertainty disclosed, plus separate human-similarity confirmation.
> No production decision, no merge, no private music, PR #16 Draft.
>
> **MTG/MAGNATAGATUNE REAL METADATA PREFLIGHT PASS (21 OCT 2026):**
> Both agreed metadata-only workflows now completed successfully,
> with **no audio downloads**. MTG-Jamendo split-0 / official
> Essentia JSON classes audited at
> [39586686845](https://github.com/chrober/bliss-mood-poc/actions/runs/39586686845):
> 87 Genre head classes, train/validation/test 32572/11043/11479;
> 56 Mood/Theme, 9949/3802/4231; zero artist-ID/track-ID
> overlap across official splits (not proof of exact ONNX training
> provenance or no encoder training overlap).
>
> MagnaTagATune schema + **human votes and clip joins** validated
> in [39587323227](https://github.com/chrober/bliss-mood-poc/actions/runs/39587323227):
> 533 odd-one-out triple questions, 7650 human votes, 1019 distinct
> referenced MP3 paths, 903 apparent song groups, 214 artist
> strings; 87 tied top-vote questions, 228 unique >=70% consensus
> questions, 160 unanimous. The source clip catalog has 31382 rows,
> of which 5519 have empty MP3 path. These are research metadata
> only. The corrected parser detects original CSV delimiters;
> continuous synthetic Linux/Windows CI
> [39587511195](https://github.com/chrober/bliss-mood-poc/actions/runs/39587511195)
> PASSED. No unfiltered audio benchmark executed or metric selected.
> See [formal preflight results](external-evidence-preflight-results-2026-10-21.md).
>
> **NEXT:** Plan a rights-compliant, bounded study processing the
> 1019 distinct MTT clips only; first verify physical ZIP member
> mapping and archive integrity/disk budget, then paired, artist-grouped
> human triplet agreement and uncertainty against all seven metrics.
> For MTG-Jamendo, consider auxiliary human classification annotations
> on official split-0 test data, but DO NOT pretend these are
> independent evidence of original ONNX training. Every audio workflow
> gets stage walltimes, worker counts, peak RAM and throughput.
> No main/PR #13/PR #17 merges.
>
> **EXTERNAL EVIDENCE ROADMAP / PERFORMANCE POLICY — 21 Oct 2026:**
> The user explicitly wants **continued GitHub Actions runtime optimization
> alongside musical evidence research**. See the detailed
> [MTG-Jamendo + MagnaTagATune plan](similarity-external-evidence-roadmap-2026-10-21.md).
> Priority: (1) metadata-only MagnaTagATune comparison/vote/clip schema and
> licensing audit (533 human odd-one-out triples, ~7650 votes, CC BY-NC-SA
> 3.0 dataset, GPLv3 scripts); (2) in parallel, metadata/split/model-provenance
> audit of MTG-Jamendo 87-Genre/56-Mood heads and derived human annotations;
> (3) only after rights/metadata validation, bounded MagnaTagATune
> audio benchmark with corrected pinned Rust-v5, triplet voting agreement,
> human consensus and paired uncertainty; (4) final independent testing
> and Lyrion playlist validation. **Do not download huge Jamendo audio
> collections or MagnaTagATune split archives until validated.**
> Every expensive workflow must report elapsed times for build, download,
> inference and evaluation; worker count, CPU/RAM and throughput;
> optimize measured bottlenecks. External per-track analyze-features
> loops remain serial; adaptive scan-features workers are not enabled
> there. No production metric selection or merge.
>
> **FMA GENRE VALIDATION E2E PASS, 21 Oct 2026:** Corrected
> [run 39583233757](https://github.com/chrober/bliss-mood-poc/actions/runs/39583233757)
> passed. Official FMA-Small archive has **3 size-anomalous MP3s**,
> safely excluded, with 7,997 usable MP3s. The **80** seeded, artist-unique
> validation tracks (10 per genre, FMA test split untouched) were processed
> by pinned genuine Rust-v5, and an
> [aggregate-only artifact](https://github.com/chrober/bliss-mood-poc/actions/runs/39583233757/artifacts/12338242831)
> published. P@5 random expectation .1139; RMS .3175, cosine .3500,
> centered cosine .3525, weighted Jaccard .3550, old Top-K .3150,
> ranked Top-6 .3150 and ranked Top-12 .3400. Exploratory ONLY,
> no metric chosen. See docs/fma-genre-benchmark-plan.md and
> docs/github-actions-trigger-and-worker-audit-2026-10-21.md.
> Trigger change to push-only CI and docs-only skip is verified;
> Rust adaptive workers are not used by per-song AnalyzeFeatures.
>
> **GH CI / FMA FOLLOW-UP — 21 Oct 2026:** The real FMA validation
> run [39581435733](https://github.com/chrober/bliss-mood-poc/actions/runs/39581435733)
> failed **before inference**, after downloading the archives, because
> `scripts/benchmark_fma_genre.py` rejected one unexpectedly sized MP3
> anywhere in the archive. The code now excludes isolated size anomalies
> and fails closed on excessive damage; synthetic tests were added.
> The corrected GH validation run is
> [39583233757](https://github.com/chrober/bliss-mood-poc/actions/runs/39583233757):
> **verify completion/artifact before claiming FMA retrieval results**.
> General CI was split into Rust-only and Python/PowerShell-only workflows;
> both now use path-filtered **push** triggers (not push+pull_request),
> so each in-repository commit runs a check at most once per relevant
> workflow, and docs-only changes do not execute those checks. See
> [GitHub Actions audit](github-actions-trigger-and-worker-audit-2026-10-21.md).
> FMA/DEAM audio analysis is currently **serial** (`analyze-features` for
> each track, `--threads 1`); adaptive workers belong to `scan-features`
> and are not active. Benchmark fixed-two-worker vs serial only after
> an isolated, validated batch/sidecar implementation.
>
> **UPDATED CURRENT STATUS 21 OCT 2026 — 240-song DEAM and FMA validation:**
> Two 240-song DEAM GitHub Actions benchmarks passed: unfiltered
> [39577605466](https://github.com/chrober/bliss-mood-poc/actions/runs/39577605466),
> conservatively exact MTG-catalog-match-filtered
> [39579552118](https://github.com/chrober/bliss-mood-poc/actions/runs/39579552118).
> Full metadata-only DEAM/MTG screening passed
> [39579084649](https://github.com/chrober/bliss-mood-poc/actions/runs/39579084649):
> **75 possible metadata matches**, not proof of model-training usage.
> Filtered Mood VA-proximity query Spearman: weighted Jaccard .2888,
> cosine .2868, centered .2813, rms .2711, ranked top-6 .2721,
> ranked top-12 .2745, historical cutoff top-K .1903
> (216/240 comparable anchor queries). Different samples, no winner.
>
> FMA-Small metadata-only workflow passed
> [39580107275](https://github.com/chrober/bliss-mood-poc/actions/runs/39580107275):
> 8,000 tracks, 8 exactly balanced genres, artist-disjoint official
> training/validation/test split counts 6,400/800/800.
> New scripts/benchmark_fma_genre.py + regression tests implement
> real Genre retrieval metrics and bounded artist-unique VALIDATION
> evaluation; first live 80-song workflow
> [39581435733](https://github.com/chrober/bliss-mood-poc/actions/runs/39581435733)
> was started, check final run logs/artifact before reporting its result.
> The official FMA test split is reserved. All research workflows use
> corrected pinned Rust-v5 source from PR #17 in separate checkout,
> without merging PR #17. See docs/deam-similarity-benchmark.md,
> docs/fma-genre-benchmark-plan.md and the dated detailed handover.
> No user music rescans, subjective relabels, selected production metric,
> PR merge or main changes.
>
> **DEAM v5 END-TO-END PASS, 21 Oct 2026:** Official DEAM data
> successfully downloaded; **1,802** audio/annotation matches; **12**
> human-annotated DEAM songs analyzed with corrected Rust-v5,
> all seven similarity metrics compared, aggregate-only report uploaded.
> [Successful GitHub Action](https://github.com/chrober/bliss-mood-poc/actions/runs/39576010217),
> [report artifact](https://github.com/chrober/bliss-mood-poc/actions/runs/39576010217/artifacts/12333973414).
> Rust-v5 analyzer came from **separate pinned PR #17 source checkout**
> at 2c3d44401436b3b41b6e067199016a1ed2335fbf without
> merging/editing PR #17. Prior failures intentionally caught missing
> Cargo.lock (PR #16) and v4 preprocessing mismatches. See
> [DEAM benchmark document](deam-similarity-benchmark.md) for complete
> provisional VA correlations. Do **not** choose a metric from 12 songs,
> claim DEAM independent of MTG-Jamendo training, or treat Genre-vs.-VA
> as Genre validation. Next: larger controlled DEAM study, training
> overlap audit, then FMA Genre reference. No main merge.
>
> **CURRENT PRIORITY 21 OCT 2026 — automatic scientific DEAM benchmark, PR #16.**
> The user explicitly shifted away from further manual eight-pair listening
> studies. A reproducible DEAM Valence/Arousal benchmark now lives in
> [docs/deam-similarity-benchmark.md](deam-similarity-benchmark.md) with
> scripts/benchmark_deam.py, test_benchmark_deam.py and
> .github/workflows/deam-benchmark.yml. Synthetically tested on Linux/Windows
> in GitHub Actions. Official DEAM audio and annotations plus official models
> will be fetched only by the runner; only aggregate research results can be
> uploaded. First real workflow run failed because Cargo.lock is not yet
> committed and --locked prevented build; updated workflow removed --locked.
> Check DEAM GitHub Actions run 39575405139 (or latest) before claiming any
> end-to-end result. DEAM's CC BY-NC license, possible MTG-Jamendo train set
> overlaps and the status of Valence/Arousal **as a similarity proxy** must
> remain explicit. No metric winner, user-library scan, public music
> artifacts, mixing decision, main merge or PR #13/#17 changes.
>
> **CURRENT HANDOVER (21 October 2026): Similarity-Metriken auf Rust-v5-Daten, Draft-PR #16.**
> Das folgende Scanner-/Worker-Handover vom 19. Oktober ist historisch,
> nicht die aktuelle Aufgabenliste. Maßgeblich ist das
> [Similarity-Hörtest-Handover vom 21.10.2026](similarity-listening-review-handover-2026-10-21.md).
> **Neuer Status: Die ersten acht menschlichen Hörurteile liegen vor; der
> read-only Evaluator lief erfolgreich.** Genre: 0 positive und 8 negative
> Paare (keine ROC-AUC definierbar); Mood/Theme: 4 positive, 4 negative
> Paare, Cosine und Centered Cosine je AUC 0,5625, andere Metriken
> 0,3125–0,5000. Historisches Mood-Top-K mit absolutem Cutoff liefert
> für alle vier positiven Pilotpaare Null. Keine fehlenden Vektoren.
> Dies sind **unsichere, selektiv ausgewählte Piloturteile**, keine
> unabhängige Validierung und kein Nachweis für eine beste Metrik.
> Nächsten Evaluations- bzw. Hörschritt **mit dem Benutzer vereinbaren**;
> vorher keine eigenmächtigen Experimente oder Änderungen an Queue/Code.
> Private CSV, JSON, Auswahl-Audit, Feature-DB und Audiodateien lokal
> belassen. PR #13 und #17 bleiben separat und Draft, `main` unverändert.
> Bei Bedarf ausschließlich vollständige PowerShell-`& { ... }`-Blöcke.


> **21.10.2026 – Current executable next step:** PR #16 now includes
> a targeted read-only --pair-details-only option in
> scripts/evaluate_similarity.py. It supports semicolon CSVs and
> generates seven score values per head/per human-reviewed pair without
> random sampling, audio analysis, queue changes or changes to labels.
> The original first-eight CSV and saved JSON remain private and
> unchanged. Ask the user to run this option with the saved Rust-v5
> SQLite sidecar and return the new local pair-details report, verifying
> that its labeled AUCs match the existing saved report. The aggregate
> Mood cosine high-scoring negative is 0.9769996802 but its identity
> is not established without the per-pair values. All musical
> conclusions remain explicitly exploratory and uncertain.

> **Purpose:** Start a new development chat without losing the current project
> state. The detailed performance experiment, raw benchmark measurements,
> implementation details and open questions are in
> [adaptive-scan-performance-handover.md](adaptive-scan-performance-handover.md).
>
> **Source of truth:** Always re-check current GitHub `main` before making
> claims or changing code. This handover was prepared against
> `55b35dab1a873c3e61ecd639b7430caf0b09034c` (PR #5 merged), before the
> documentation-only handover PR. Do not assume that SHA is still the latest.

## Project and boundaries

Repository: [chrober/bliss-mood-poc](https://github.com/chrober/bliss-mood-poc).
Experimental Rust/ONNX offline audio analysis to complement Lyrion/Bliss,
**not** an instruction to change production mixers, plugins or Bliss Guidance
SPI. The generic CLI handles **three independent heads** sharing one
Discogs-EffNet embedding per song:

- `moodtheme` — 56-label MTG-Jamendo Mood/Theme (Sigmoid).
- `genre` — 87-label MTG-Jamendo Genre (Sigmoid).
- `voice` — Voice/Instrumental, 2 labels (Softmax). Not vocal-technique or
  percentage-of-vocal-time detection.

Original `bliss.db` and audio are read-only. Experimental results live in a
separate SQLite sidecar, schema v3, keyed by exact `TracksV2.File` identity.
Old Mood-only CLI and legacy rows remain untouched. Real-world prediction
quality is **not** production-validated; verified synthetic Essentia numerical
parity is not evidence of musical usefulness. See
[feature-provider-architecture.md](feature-provider-architecture.md) and
[offline-mood-database.md](offline-mood-database.md).

## What has shipped

1. Generic Mood + Genre + Voice analysis, shared encoder, model registry,
   per-head caching and validated numerical parity.
2. Incremental `scan-features` with bounded, parallel *songs*, independent
   per-worker ONNX Sessions and a single transaction-safe SQLite writer.
3. Corrected ONNX Runtime process-global Environment (earlier concurrent
   `ort::init().build()` attempts failed on Windows).
4. `--max-new N` means **at most N newly attempted tracks**, not N
   successes; `--max-errors N` aborts repeatedly failing scans.
5. `--workers auto` keeps Windows responsive (roughly 25% CPU headroom,
   cap eight), `--workers N` is explicit; for parallel use `--threads 1`.
6. [PR #5](https://github.com/chrober/bliss-mood-poc/pull/5), merged:
   opt-in `--adaptive-workers` with `--workers 6 --min-workers 4
   --max-workers 8`; per-song decode/preprocessing/inference/hash/load
   stage totals; OS CPU/RAM monitoring; logged worker adjustments.
   The fixed-worker interface remains available and unchanged.

Important source entry points:

- `src/features.rs`: `FeatureEngine`, `scan_parallel`,
  `save_completion`, `ScanSummary`, `ScanDiagnostics`.
- `src/parallel.rs`: `worker_count`, `AdaptiveWorkers::observe`.
- `src/resources.rs`: OS-level load sampling.
- `src/main.rs`: CLI flags and validation.
- `src/storage.rs`: read-only upstream Bliss access and SQLite sidecar.
- `model-registry.json` and
  `.github/workflows/voice-parity.yml`: model contract and integration tests.
- `README.md`: usage and caveats.

## Real test setup

User machine: Windows 11, HP Laptop 15-fc0xxx, AMD Ryzen 7 7730U,
8 physical cores / 16 logical CPUs, ~16 GB physical RAM; Wi-Fi 6 Realtek
RTL8852BE-VS at negotiated 600 Mbit/s. Music on NAS UNC share
`\\192.168.1.100\music`, local checkout
`D:\LMS\bliss-mood-poc`, 64,062 eligible Bliss tracks.

Deterministic local 100-song fixture:
`D:\LMS\bliss-mood-poc\benchmark-workers-20261019-060347\sample-100.db`
(seed 20261018). Benchmark sidecars:
`features-6.db`, `features-8.db`, `features-10.db`,
`features-12.db`; raw samples `resources-*.csv`, `summary.csv`
and `summary-with-6.csv`. Keep this suite for apples-to-apples work;
do **not** upload personal music or database to GitHub.

**Fixed-worker results over the same 100 tracks**:

| Workers | Wall time | Songs/min | System CPU avg | RAM max | Analyzer RAM max |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 6 | 80.48 s | 74.6 | 47.9% | 85.0% | 0.66 GB |
| 8 | 80.18 s | 74.8 | 63.5% | 89.5% | 1.17 GB |
| 10 | 82.29 s | 72.9 | 70.8% | 91.6% | 1.94 GB |
| 12 | 112.79 s | 53.2 | 83.2% | 97.5% | 3.21 GB |

All 300 model vectors per run were **byte-identical**. With six workers:
CPU max 87%, WLAN receive mean 24.05 MiB/s, max 39.08 MiB/s. Six fixed
workers are the measured efficiency baseline; eight have similar throughput
at much higher resource pressure.

**First adaptive run**, reported after PR #5 from a database within the
same benchmark directory:
`adaptive-20261019-080350.db`; 100/100 successful, zero failures,
**120.66 s (49.7 songs/min)**; workers initial/final/max **6/6/6**,
CPU avg 51.26%, peak RAM 86.33%, 38 OS-load samples, **no adjustments**.
Per-song *summed overlapping* durations: decoding 173.52 s, Mel/patches
100.82 s, ONNX 343.09 s, SHA-256 reread 66.54 s, session init 1.63 s,
sum of song durations 685.61 s. These are NOT sequential wall-clock or
exclusive CPU durations.

The adaptive controller's low-load rule is **CPU <=65% AND RAM <=79%
for 3 consecutive resource observations**. High-load rule is **CPU >=90%
OR RAM >=88% for 2 consecutive observations**. Changes are inhibited
until >=24 completed songs and at least 20 s since the last adjustment
(or creation). The observed near-86% RAM can sit in the deadband for the
entire run. Therefore **no worker change is not proof of a bug**. The
report shows only maximum RAM, not every sample: inspect actual timelines
and effective conditions before concluding why no adjustment occurred.
Whether the ~50% longer adaptive runtime is reproducible, and whether
the command truly used an identical track set/cache/priority, remain OPEN.

## Next work — priority order

1. **Investigate the adaptive performance regression** on exactly the
   existing `sample-100.db` and music source. Compare fixed six vs adaptive
   six under equivalent environment and process priority; alternate run
   order/repeat measurements, inspect NAS/OS caching, thermal/power throttling,
   and runtime phases. Do not conclude adaptive scheduling is at fault merely
   because of one timing difference.
2. **Make decisions explainable**: record per-resource sample time, CPU/RAM,
   consecutive low/high counters, cooldown, controller state, real in-flight
   count and why it held or changed. Check for starvation caused by samples
   only being taken when job results arrive.
3. **Evaluate safe policy options**, with tests: explicit pressure-only guard
   (reduce at high RAM/CPU), separate throughput-seeking tuning policy, or
   thresholds based on available memory + CPU/queue throughput rather than
   CPU/RAM fixed cutoffs alone. A correct policy may intentionally stay at six.
   Do not blindly force an adjustment.
4. **Measure NAS versus local SSD** on identical files with controlled
   cache state; distinguish SMB latency, network throughput and CPU
   preprocessing/inference. File hashing reads the source twice overall.
5. Regression CI: deterministic simulated resource timelines (high, low,
   deadband, missing samples, cooldown); verify real in-flight changes,
   maximum attempts, error stop and byte-identical feature vectors.
6. Only after evidence, optimize the controller and maybe expose explicit
   `--max-workers` defaults; keep fixed-worker behavior stable. Later:
   full-library progress/ETA and resumable/interruptible UX.

## Rules for the next chat

- Fetch fresh `main` SHA and review these docs + source **first**.
- Diagnose rather than assert adaptive is broken: 6/6/6 can be correct.
- Prefer a reproducible minimal PR; run Rust tests, Clippy, Windows x64,
  and required Essentia/model parity before merge.
- No production mixer/plugin changes. Keep `bliss.db`/music read-only;
  new SQLite benchmark DBs only; never commit music, model weights,
  local sidecar DBs or personal track lists.
- Always bound experiments: `--max-new`, `--max-errors`, timeouts;
  `--threads 1` when parallel. Retain `--workers N` and
  `--adaptive-workers` as optional.
- The user prefers actionable full PowerShell blocks (`& { ... }`) and
  measured evidence over speculative optimizations.


## Mandatory GitHub Actions / local testing workflow (2026-10-19)

**User preference and delivery contract for all future chats:**

1. **Never build Rust binaries on the user's Windows laptop.** Do not put
   `cargo build` or local Rust compilation in a PowerShell test script.
   Source code, unit tests, and release binaries are built and verified by
   GitHub Actions.
2. Make development changes on a feature branch and open a PR. PR events
   automatically trigger the existing **Windows x64 binary** workflow
   (workflow ID `387992797`) along with Rust checks and model parity checks.
   Do not assume that a documentation-only `main` commit also generated a
   Windows executable. Inspect the PR **head SHA** and matching Actions runs.
3. **Do not stop after reporting a queued/in-progress build.** Check the
   triggered Windows workflow to completion; verify that its conclusion is
   `success`, its head SHA matches the exact code under test, and that its
   non-expired artifact **`bliss-mood-windows-x64`** exists. Check all
   relevant Rust and model-parity workflows too. If any check fails, diagnose
   and fix first; never claim the binary is available prematurely.
4. Whenever the user is asked to run a local test, provide a **complete
   executable PowerShell script in `& { ... }` form**, containing the
   **literal, verified numeric Actions run ID** (not a placeholder, an
   automatically selected run, or instructions for the user to look it up).
   Embed the actual binary download, for example:
   `gh run download $runId --repo chrober/bliss-mood-poc --name bliss-mood-windows-x64 --dir $binDir`,
   followed by verification of `bliss-mood.exe`. Download to a run-ID-specific
   path such as `bin\windows-x64\$runId` and reuse only that matching binary.
   The script must check workflow head SHA/conclusion and fail safely if they
   do not match, use a fresh benchmark sidecar, and report useful diagnostics.
5. Preserve the user's existing setup: repo
   `D:\LMS\bliss-mood-poc`, source music `\\192.168.1.100\music`,
   stable 100-song sample
   `benchmark-workers-20261019-060347\sample-100.db`,
   `--models moodtheme,genre,voice --threads 1`. Audio files and original
   `bliss.db` are read-only. Do not commit personal media or benchmark DBs.
6. If testing code on a PR branch, don't require the user's local checkout
   to be on `main`; the binary must match the chosen PR SHA. Do not merge
   before CI and local validation where required.
7. Continue gathering evidence rather than changing worker behavior based
   solely on one timing result. Keep fixed worker modes and model-score
   identity intact.

**Previously verified example:** PR #7 Windows run `39236884182`,
artifact `bliss-mood-windows-x64`, head
`d34e2c4941d008caae089640dc4b75925da5c3e6`. PR #7 was squash-merged
into main as `8ee29972999caf1e543dbb7ce63d57868fdd16f2`.
Do **not** reuse that run ID for subsequently modified code.


## PR #10 pre-worker baseline measurement (2026-10-19)

**New benchmark requirement:** capture and report the system's RAM **and CPU
baseline before any scanner worker starts**, plus available physical RAM
and analyzer process Working Set and Private Bytes. For CPU, a single
instantaneous OS counter is meaningless: use a **one-second interval** before
workers are spawned, and expose the actual elapsed measurement window.
Do **not** feed this baseline into the adaptive worker controller or
normal runtime samples. On Linux and Windows this is measured at the start of
the parallel scan, after opening the input and sidecar DB and before
creating ONNX worker sessions. The one-second baseline measurement is
included in wall-clock scan elapsed time.

The JSON location is `diagnostics.baseline`:
`system_cpu_percent`, `cpu_measurement_seconds`,
`system_ram_percent`, `system_available_ram_mib`,
`process_working_set_mib`, `process_private_bytes_mib`.
These baseline values reflect **pre-worker** machine load, not a completely
idle Windows system before the application was launched. Compare changes
with runtime extrema; extrema can occur at different instants and do not
prove the analyzer was the cause of overall RAM pressure.

Use the mandatory PR-triggered GitHub Actions Windows artifact workflow
and exact-run PowerShell download rules documented above; never suggest
local cargo builds.


## Current product priority: Bliss + Mood/Genre Lyrion integration (2026-10-19)

**Read [lyrion-bliss-mood-genre-integration.md](lyrion-bliss-mood-genre-integration.md) before new product changes.** The immediate engineering task is F1: reliable exact `TracksV2.File` joining and read-only model-provenance-aware Mood/Genre SQLite retrieval for a bounded Bliss/Lyrion candidate set. The first strategy is **Bliss-first with optional Mood/Genre reranking in BlissMixerLab** through guidance SPI v2, with hard eligibility and original Bliss untouched, separate per-head influence, experimental preview opt-in and neutral fallback. Current provider host transmits candidate IDs/urlmd5, but exact file keys are not yet guaranteed; do not silently join by title/artist. Do not enable stored unvalidated model scores for production playlist generation by default.

The cross-platform worker and Raspberry Pi runtime/resource strategy is **deferred**, documented in [platform-resource-roadmap.md](platform-resource-roadmap.md). The user explicitly does not want tuning for one benchmark laptop; development focus now is meaningful playlist fusion, not scanner performance.

## Three-way mixing decision and local workfiles (2026-10-19)

The mixing architecture remains **undecided** between **Bliss-first**,
**Mood-/Genre-first**, and **Hybrid**. The first integration vertical slice
uses Bliss-first because the existing SPI v2 can already rerank a Bliss
candidate pool, **not** because Bliss-first has won a listening/coverage
comparison. All three must be compared on equivalent seeds, constraints,
coverage, transition quality, drift/diversity and Pi budgets before choosing.
See [lyrion-bliss-mood-genre-integration.md](lyrion-bliss-mood-genre-integration.md).

Root-level `benchmark-*/`, `bin/`, local `mood-full.json` and
`mood-quality-*.csv` are excluded by `.gitignore`; keep personal
music paths/analysis outputs out of commits. Do **not** ignore
`Cargo.lock`: this binary application's dependency lockfile should
be separately versioned once. Git status will continue showing it as
untracked until added/committed.
