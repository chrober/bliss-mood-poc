# Handover: native Essentia adaptive workers, priority, and host-dependent limits (2026-10-28)

> **NEWER CANONICAL PHASE C HANDOVER (12:08 Europe/Vienna, 28 October 2026):** Read [handover-phase-c-isolated-worker-20261028.md](handover-phase-c-isolated-worker-20261028.md) **before** this historical PR #18/Phase A-B benchmark record. The live PR #19 implementation was inspected at `e2b1a0a4bd256d88e8704abcc8bf158878296ddc` **before documentation updates**. Rust tests/Clippy, Windows x64 binary and Genre/Voice CI parity passed, but **both native Essentia workflows failed**. Linux is a concrete source regression: `native/rust-mel-reference` imports `src/audio_decode.rs` but cannot resolve `crate::resources` (Rust E0433); Windows stops during pinned upstream source verification with unresolved cause. See the new handover for exact run IDs, implementation details, proposed remediation and missing private real-song numerical/embedding parity. The hidden Phase C worker **does run the actual FeatureEngine** for Initialize/AnalyzeSong but is **not yet used by normal scan-features**. Do not rely on older paragraphs below that still describe Phase C as only synthetic Ping or CI as queued.


**Canonical current handover for PR #18 (code baseline):** [PR #18](https://github.com/chrober/bliss-mood-poc/pull/18), branch `feat/manifest-batch-adaptive-worker-analysis`, code head `ea514f144183fc8b24c82ad25e93c0f3e201b2e2` **before this documentation update**. PR #18 is stacked on PR #17 (`feat/essentia-cpp-worker-backend`), not on `main`. Independent similarity research PR #16 remains unaffected. **Always re-read the live PR head** and corresponding CI checks; this SHA is a historical verification point, not a permanent tip.

See [the paste-ready handover prompt](handover-prompt-adaptive-host-sizing-20261028.md), [adaptive historical handover](adaptive-scan-performance-handover.md), [manifest/scanner design](manifest-batch-adaptive-analysis.md), [priority investigations](native-worker-priority-study.md), and [cross-platform resource roadmap](platform-resource-roadmap.md).

## 1. Purpose and immutable boundaries

Investigate fast, repeatable **offline** Mood/Genre/Voice inference with an original Essentia C++ audio frontend and Rust scan coordinator. Per-song embedding: shared Discogs-EffNet **1280D**; heads: Jamendo Mood/Theme (56 labels), Genre (87 labels), Voice/Instrumental (2 labels). Original music and Bliss DB must remain **read-only**; store scans in fresh local SQLite sidecars and optional embedding JSON directories. Keep original model weights, output identity, source track keys, independent per-worker model sessions, a single SQLite writer, `--max-new`, `--max-errors`, native timeouts, `--threads 1` with parallel workers, and exact score/embedding parity. Production plugin/mixer changes and similarity PR #16 are out of scope.

The representative private local benchmark uses an existing **100-song** `TracksV2` cohort on Windows 11 / Ryzen 7 7730U (**16 logical CPUs**, ~16 GB RAM), original song audio on NAS over Wi-Fi, official ONNX models, and the verified original Essentia C++ worker. **Do not commit/upload personal media, private cohort DB, local manifests, raw per-song scanner logs, ONNX weights or machine secrets.** Only aggregate findings and generic instructions belong in the repository.

## 2. Real-music evidence — completed experiments, not performance hypotheses

### 2a. Prior unbalanced priority comparison (27 October 2026)

100 songs, fixed 1/2/4/6 vs adaptive 2–6, two repetitions each, exact output parity. Median seconds: fixed1 **282.126**, fixed2 **277.649**, fixed4 **110.803**, fixed6 **93.417**, adaptive2–6 **116.852**. **Confounded**: old adaptive mode ran Windows `BelowNormal`, fixed numeric runs normally `Normal`; cannot infer adaptive overhead from that experiment alone.

### 2b. Explicit three-priority matrix (27–28 October 2026)

Exactly **30 completed scans** (five modes × three priority classes × two repetitions; all 100 songs and three heads), original native C++ backend, verified exact classification and complete embedding parity, actual Win32 priority class verified for scanner and every native subprocess.

| Mode | BelowNormal median s | Normal median s | AboveNormal median s |
|---|---:|---:|---:|
| fixed1 | 414.889 | 416.232 | 403.865 |
| fixed2 | 257.683 | 238.162 | 270.009 |
| fixed4 | 167.856 | 163.123 | 164.551 |
| fixed6 | 118.605 | 107.819 | 112.764 |
| adaptive2–6 | 174.288 | 171.791 | 172.294 |

Interpretation: no reliable/reproducible benefit from `AboveNormal` on this unloaded workload. Six fixed workers beat slowly growing adaptive 2→6. The three priority groups were **run sequentially**, so background changes, NAS caches, power/thermal state and song-duration variance remain confounders. Do not use this data to claim scheduling priority never matters under CPU contention.

### 2c. Controlled adaptive start/gate study (28 October 2026)

**10 completed scans**, same 100 songs, models, binary class `Normal`, two order-balanced repetitions, exact score/embedding parity. Every adaptive variant used minimum **2**, maximum **6**; fixed6 was the reference. Table is median wall seconds over two runs, **not an independently proven universal ranking**.

| Mode | Median wall s | Peak private process-tree MiB | Total changes over 2 runs |
|---|---:|---:|---:|
| adaptive6_gate24 | **119.668** | 635.027 | 0 |
| fixed6 | 125.589 | 647.445 | 0 |
| adaptive4_gate24 | 126.537 | 625.828 | 4 |
| adaptive2_gate8 | 146.344 | 604.090 | 8 |
| adaptive2_gate24 | 148.650 | 604.461 | 8 |

Real worker adjustment positions:
- adaptive2_gate24: round1 **25,34,48,68**; round2 **25,35,48,62**.
- adaptive2_gate8: round1 **12,30,38,56**; round2 **9,27,40,58**.
- adaptive4_gate24: round1 **25,38**; round2 **26,35**.
- adaptive6_gate24: no changes; active six throughout both runs.
- fixed6: fixed six throughout.

**Interpret carefully:** earlier gate eight advanced the first growth but barely improved median whole-run time versus gate 24 (**146.344 vs 148.650 s**); startup **2 versus 4 versus 6** is much more consequential. Adaptive-start-6 vs fixed6 differed in round1 (109.656 vs 121.546 s) but were practically tied in round2 (129.680 vs 129.631 s). This is likely run-to-run variability, **not proven adaptive-over-fixed speedup**. In both adaptive6 runs no resize occurred. Every adaptive run starting under six eventually reached **the configured maximum six**; therefore measurements **cannot yet determine** whether the true optimal native-worker count is 6, 8, 10, 12 or another value. CPU/RAM measurements at six showed headroom, but that alone does not prove throughput scales further. Earlier 6/8/10/12 tests on a *different Rust audio backend/setup* are historical, **not direct native-C++ evidence**.

## 3. Current controller algorithm (code-verified)

`src/parallel.rs::AdaptiveWorkers::observe_at`:
- High load when **system RAM >=88% OR system CPU >=90%** for **two consecutive valid resource samples** → decrease by **one** active slot, unless already at minimum.
- Low load when **system RAM <=79% AND system CPU <=65%** for **three consecutive valid samples** → increase by **one** slot, unless at maximum.
- Neutral observations reset both streaks. Require at least **24 successfully completed songs** by default (`--adaptive-min-completed-songs 8` in special test) **and** **20 seconds** since controller creation or last change for either direction.
- Resource observations are completion-driven, no more often than every **2 seconds**, **not** a continuous timer; empty/missing metrics do not drive decisions.
- A controller decision modifies **in-flight admission cap**, not ongoing tasks or loaded ONNX sessions. Actual native worker pool can already have max-capacity thread slots; only admitted concurrent song jobs change.
- Adaptive diagnostics: `diagnostics.initial_workers`, `final_workers`, `peak_workers`, `adaptive_min_completed_songs`, `adjustments[]` with `after_completed_songs`, `from_workers`, `to_workers`, `reason`, CPU/RAM; `controller_decisions` with low/high/neutral samples and hold/change counters. The benchmark `runs.csv` includes `first_resize_after_completed_songs`, `resize_song_positions`, `controller_gate_holds`, `controller_cooldown_holds`.
- Current algorithm uses **CPU/RAM threshold headroom**, **not** actual throughput-improvement feedback. Dynamic process priority is **not implemented**.

## 4. Host-dependent maximum: current implemented semantics

User requirement: **no fixed global 6/8-worker cap**; Raspberry Pi 4B with **4 permitted logical CPUs** must not get a fixed-six limit. In the current PR #18 code, `src/parallel.rs` uses `std::thread::available_parallelism()` (may reflect affinity/container limits; max technical 64, fallback one CPU):

- `--max-workers auto` **default** resolves to permitted logical CPUs capped at **64**. In `src/main.rs`, CLI `auto` parses internally as sentinel `0`, then resolves before constructing `ScanOptions`; `0` is **never** a real count.
- `--workers auto` remains a conservative **initial** sizing: reserve `max(2, floor(allowed_CPUs/4))`, then cap start at **8**, minimum 1.
- `--min-workers` default **1** (formerly 4), allowing small CPU devices. `--workers` CLI default remains `1`; simply enabling `--adaptive-workers` without choosing `--workers auto` does **not** mean automatic initial sizing.
- Explicit `--workers N` and explicit `--max-workers N` above available logical CPUs are **rejected**, rather than silently oversubscribing. A fixed cap requested by benchmark is still honored on capable machines. Adaptive validation still requires `min <= initial <= max`.
- Examples: with **4** permitted CPUs: `--workers auto` starts **2**, `--max-workers auto` resolves **4**; with **16**: starts **8**, maximum **16**; with **1**: initial/max **1** (serial path).
- `diagnostics.logical_cpu_capacity` and `diagnostics.configured_max_workers` report host capacity and effective pool cap (pool is also bounded by number of candidate tracks).
- **Not RAM-aware yet.** A Raspberry Pi 4B with 4 GB RAM can still run out of memory with four ONNX sessions, and thermals, I/O, memory/cgroup quotas and library workload can lower the *safe/optimal* cap. CPU-only is a first-stage ceiling, not a promised optimal or always-safe default. `available_parallelism` is not a guaranteed precise cgroup quota measurement on every host.

Explicit Windows priority classes `--priority below-normal|normal|above-normal` independently apply to scanner and original C++ children (explicit Win32 process creation flags; actual observed classes verified). Omitted priority retains legacy behavior: fixed numeric doesn't change priority; auto/adaptive requests `BelowNormal`. Explicit priority currently unsupported on Linux/macOS (error). All real-music comparisons above used explicit equal priority per respective group. No dynamic priority governor.

## 5. Source/CI status and precise reproducibility

**Code-verified baseline before writing this handover:** `ea514f144183fc8b24c82ad25e93c0f3e201b2e2`. The earlier host-cap patch `5b36652f...` triggered strict Clippy `large_enum_variant` when `--max-workers` was represented as `String`. That issue was subsequently fixed in actual source by parsing `auto` to `usize=0` sentinel; do **not** reintroduce the large enum issue. The CI follow-up also changed the voice parity workflow to avoid explicit oversubscription on small hosted runners; check current `.github/workflows/voice-parity.yml`.

Successful checks on that exact code commit:
- Rust checks: [40653208984](https://github.com/chrober/bliss-mood-poc/actions/runs/40653208984) — PASS.
- Windows x64 binary: [40653208925](https://github.com/chrober/bliss-mood-poc/actions/runs/40653208925) — PASS; verified existing, non-expired `bliss-mood-windows-x64` artifact on matching source code SHA.
- Original native Essentia C++ smoke: [40653208936](https://github.com/chrober/bliss-mood-poc/actions/runs/40653208936) — PASS.
- Genre ONNX/TensorFlow parity: [40653208976](https://github.com/chrober/bliss-mood-poc/actions/runs/40653208976) — PASS.
- Voice/Instrumental parity: [40653208956](https://github.com/chrober/bliss-mood-poc/actions/runs/40653208956) — PASS.

**After these Markdown changes the PR head will differ from that code commit.** A documentary commit is not a code change, but any new run/artifact must still be matched to the exact commit under test; do not claim prior artifacts are for the newer documentation commit.

Local workflow: **no Rust build on Windows laptop**; build via CI. Use a complete self-contained PowerShell `& { ... }` block with verified literal run ID, `gh run download`, `BUILD.txt` source-commit identity, SHA256 verification, clean detached worktree, 100-song bounded input, explicit `--threads 1`, `--priority normal`, native worker prerequisite and new/empty result dir. No login access to private local Windows/NAS from remote GitHub Actions. Use `--experiment adaptive-policy` for the earlier 2/4/6 and 8/24-song controller study; its study modes deliberately cap at 6. Do not present that experiment as a validation of host-`auto` on a Pi. Use the CI-backed binary from a **matching commit** and confirm green Windows + Rust + native/model parity workflows. Separate all code changes from experiment result claims.

> **Phase A measured update (28 October 2026):** The independent
> [native 6/8/10/12 fixed-worker scaling study](native-worker-scaling-study.md)
> now includes **eight completed private local real-music scans** (100 songs,
> three heads, exact classifier and 1280D embedding parity). Median whole
> scan times: fixed6 **84.558 s**, fixed8 **85.562 s**, fixed10 **94.127 s**,
> fixed12 **68.069 s**. Twelve was fastest in both repeats, at **88.166 songs/min**
> and **1127 MiB** peak observed private process-tree memory, with at least
> **3679 MiB** physical RAM available. This is the best *tested* worker count,
> **not** proof of the optimum at fourteen/sixteen or on small ARM hardware.
> The ten-worker slowdown is not yet explained. The scanner code and
> last Windows binary remain tied to the prior **10dadb65** source SHA;
> subsequent Markdown commits must not be presented as new binary validation.
>
## Phase B opt-in implementation status (28 October 2026)

A new stacked branch `feat/ram-safe-online-autotune` begins a hardware-independent Phase B prototype. Read [the Phase B design and limitations](online-autotune-phase-b.md) before testing it. `scan-features --adaptive-workers --adaptive-policy autotune --workers auto --max-workers auto` selects it; the default legacy `resource` policy remains unchanged. The prototype runs coarse, nonmonotonic exploration with a free-RAM admission budget and patch-throughput observations, while disallowing claims of a global optimum from short scans. This is **not** yet production-safe on Pi/cgroup/macos, nor an excuse to remove the existing per-host RAM watchdog from private benchmark execution.

### Phase B iteration: replicated online measurements and nested-cgroup budgets (28 October 2026)

PR #19 now implements an independent ~250-ms RAM watchdog (native cancellation, 200-ms coordinator guard checks), clean in-flight drains between worker-capacity probes, a **forward/reversed second coarse sweep**, and ranking by rolling medians from at most eight recent samples per worker count. An unreplicated outlier cannot replace the incumbent after the initial search pass. Diagnostics distinguish `search_completed` (at least one valid observation per candidate), `replication_completed` (at least two retained observations per candidate), and `observed_ranges_separated` (descriptive sample-range separation, **not a statistical confidence guarantee**). Per-scan detailed records are bounded to 256 probes and 256 worker adjustments, with aggregate counts retained.

Linux memory telemetry additionally walks accessible cgroup v1/v2 ancestor limits identified from `/proc/self/cgroup` under standard mounts. Custom mountinfo layouts and invisible container ancestors remain unverified; on macOS this autotune prototype deliberately lacks a supported free-RAM provider. Neither memory polling nor admission budgets can *guarantee* survival of abrupt allocations or interrupt a running Rust ONNX inference. See [Phase B limitations](online-autotune-phase-b.md); verify CI against the **current PR #19 tip** before using any test artifact. Exact Mood/Genre/Voice and 1280D parity have not yet been validated on local real-music scans with this new online tuner.

### Phase B safety continuation: scan-isolated cancellation (28 October 2026)

The previous process-wide native RAM-cancellation flag has been removed. In PR #19 each experimental autotune scan now owns a dedicated `Arc<AtomicBool>` cancellation token. The independent watchdog and completion-driven RAM governor signal the same token; the scoped worker pool passes it to the native Essentia IPC and Rust ONNX feature engine. Native transport checks at most every 200 ms while blocked and kills/reaps the owning child on cancellation. Rust analysis checks between audio stages, ONNX encoder/head calls, patches and the final hashing stages; session construction additionally checks between encoder and classifier-session loads. **An already running ONNX Runtime invocation or session load is not preempted**; neither is an in-flight FFmpeg decoder in the Rust frontend. A true per-scan process boundary is still required for a stronger termination guarantee.

Deterministic watchdog tests verify distinct scans do not cancel one another. A C++ protocol-fixture test now cancels a blocked `hang.flac` request, verifies child ownership cleanup, and analyzes an unrelated song with an independent cancellation token. Rust tests/Clippy passed for fixture-test code commit `d792dc50`; code added since (model-session initialization checks) requires verification at its exact head. Do **not** infer completed real-music parity or Pi/macOS support from these tests.

### Phase B supervised audio subprocess and ONNX hard-isolation design (28 October 2026)

After the all-green PR #19 baseline `a71a995f`, the experimental `autotune` Rust audio frontend now supervises and actively terminates its own `ffprobe` and `ffmpeg` subprocesses on the scan-specific RAM cancellation signal. The supervised path uses bounded dual-pipe capture, kill/reap ownership on early failures, and a decoded PCM budget derived from **current effective free RAM and configured pool size** rather than any Ryzen-specific worker setting. The legacy `resource`/fixed decoder remains unchanged. Unit tests exercise Unix subprocess cancellation/oversized output and a Windows cancellation scenario; a generated WAV tests bit-level PCM identity against the old decoder when FFmpeg is available. **These do not prove local real-audio Mood/Genre/Voice/1280D output parity or OOM immunity.** Current CI status must be checked at the exact latest code head.

A new architecture/design-only document, [onnx-worker-process-isolation.md](onnx-worker-process-isolation.md), describes moving each entire ONNX EffNet/selected-head session set into an owned, killable Rust child process, keeping SQLite writing and resource policy in the parent and preserving the existing native Essentia C++ DSP child. This hard-kill ONNX execution boundary is **not yet implemented** and is the primary remaining blocker for reliable termination of in-progress ONNX Runtime calls. Process-tree termination, versioned bounded IPC, test fixture, model and embedding parity, memory headroom and CPU quotas must be validated before any default promotion.

### Phase C: first isolated feature-worker IPC prototype (28 October 2026)

The initial phase of [onnx-worker-process-isolation.md](onnx-worker-process-isolation.md) is implemented as a **hidden same-executable worker**: `bliss-mood internal-feature-worker`. New `src/feature_worker_process.rs` defines a versioned protocol with `FWP1` handshake, `REQ1` requests, `RES1` responses, 1–65,536-byte framed JSON, exact request IDs and validation, and the corresponding supervised parent `FeatureWorkerProcess`. A direct owned Child can be killed/reaped on hard timeout or scan-specific RAM cancellation without waiting for the worker to finish. Multiple persistent Ping operations and a bounded synthetic TestDelay are supported. `tests/feature_worker_process.rs` runs the compiled CLI binary to verify reuse, isolation, hard timeout, fresh-worker recovery, duplicate/oversized message rejection and shutdown. The hidden worker **does not load ONNX or analyze media**, and the existing `scan-features` thread-based scanner is **not** wired to it; therefore it does not yet close the ONNX memory-safety gap. Subprocess **descendant-tree** hard-kill also remains unimplemented.

CI status must be verified for the *current exact PR head*. Initial module-only Rust checks succeeded at `d847f5ea`; an intermediate commit `ccec4f6c` failed strict Clippy on unused prototype functions and unnecessary mutability, corrected in later commits. Do not infer success until the newest integration tests are green. Next is to implement actual FeatureEngine request/result transport, preserve all model keys/classifier labels/pooled embeddings and validate parity before switching experimental autotune over. Keep PR #19 a Draft.

### Phase C continuation: real FeatureEngine executed in isolated child (28 October 2026)

Building on the earlier synthetic IPC prototype, the hidden `internal-feature-worker` now accepts a **one-time `Initialize`** request and repeated `AnalyzeSong` requests. It calls the existing `features::load_profiles`, `retarget_profiles`, and `FeatureEngine::with_backend`; no ONNX math, preprocessing, classifier aggregation or embedding pooling was reimplemented. It returns the same serialized `FeatureReport` and optional `SongEmbedding` without opening SQLite. The initialization response includes the selected models and existing model/cache fingerprints. A second hidden CLI, `internal-isolated-analyze-features`, exercises the *parent-side* supervised subprocess path and prints the complete JSON response. The real `scan-features` implementation is still unchanged, including default `resource` behavior and the experimental in-process `autotune` policy.

Added `scripts/compare_isolated_feature_worker.py` for **private local comparison**: it runs direct and isolated CLIs on identical source/model/backend parameters, compares all selected head identities and score **f32 bits exactly**, audio hash and patch count, and optionally verifies isolated embedding length/normalization/fingerprint consistency. The verifier now also uses the separate hidden `internal-direct-analyze-features` reference with `--embedding` and checks **every one of the 1280 `f32` embedding bits and representation fingerprints against the isolated output**. The check is implemented and unit-tested but has not yet passed a real-music run with the official ONNX/native model set. No private data or scores are persisted or committed. Python unit tests exercise the comparator without model files; Rust integration tests reject missing models and uninitialized/invalid requests. CI `ci.yml` invokes the comparator unit tests.

The parent now places **Unix** feature subprocesses in their own process groups, signaling the group before reaping on failure to terminate native/FFmpeg descendants that remain in it. Windows Job Objects and physical Pi/macOS/cgroup termination checks are still missing; this is **not cross-platform process-tree safety**. No measured throughput, actual-model numeric parity or out-of-memory guarantees may be claimed from synthetic IPC tests. The exact latest PR #19 head must pass Rust tests, Clippy, Windows/native smoke and model parity workflow checks before promotion from the hidden experiment. A large GitHub Actions queue of intermediate commits may delay visibility of the latest head; distinguish queued from green.

## 6. Recommended next work — hardware-independent self-optimization

**User objective, updated 28 October 2026:** No Ryzen-specific fixed-worker optimum or fixed-14/16 expansion is required to proceed. The scheduler must autonomously discover safe, high-throughput concurrency on each host. A throughput decline at 8/10 workers must not stop exploration of 12+ when RAM and permitted CPUs allow it. Phase A's 6/8/10/12 scans are evidence of nonmonotonicity, not default-setting calibration.

1. **CI and opt-in prototype audit:** inspect PR #19 live checks, synthetic nonmonotonic tests, resource governance, counters and exact scan-path integration. Legacy `resource` mode must remain unchanged. Validate the actual observed probe sequence, and prevent claims of optimum if insufficient scan work remains.
2. **Real RAM safety:** install an independent continuous memory watchdog, inspect process-tree/private memory, effective cgroup ceilings and OOM pressure, handle allocations between completions and abort/cancel without leaking native subprocesses. Verify 4-GB Pi, 1/2/4 CPU, Windows and constrained containers; no universal fixed reserve should be assumed sufficient.
3. **Statistically defensible throughput search:** interleave/replicate candidate windows so varying song length, model patches, NAS state and session warmup do not dominate. Add confidence/uncertainty, drift response and bounded exploration budget. Preserve nonmonotonic exploration and fast RAM-pressure retreat.
4. **Cross-platform validation and parity:** test real native C++ sidecars, 1280D embeddings and all three classifier heads using private bounded data; verify immutable audio/Bliss source. Use available ARM/macOS equipment if possible; explicitly record untested targets. Avoid publishing raw private logs or inventing measured improvements.
5. **Product decision:** only consider autotune as the default once the safety watchdog, comparable quality-of-measurement, overhead vs best fixed-per-host reference and key platform tests are convincingly green. Do not make Ryzen-based settings global.
6. PR #16 similarity, PR #17 native integration, licensing/distribution and dynamic priority switching remain independent workstreams.

## 7. New-session checklist

Read this document and [the handover prompt](handover-prompt-adaptive-host-sizing-20261028.md). Fetch **live** PR #19 (Phase B) and its stacked PR #18 base, current CI and source before changes. Distinguish **completed local measurements** from code/CI-only verification and unmeasured throughput hypotheses. Do not repeat prior questions already answered. Continue within `feat/ram-safe-online-autotune` for Phase B, preserving the PR #18 experimental baseline, update docs/tests together, keep private input read-only, and use commit-matched GitHub Actions artifacts for any Windows testing.

## Reproduzierbarer PR-19-PowerShell-E2E-Benchmark (28.10.2026)

Aufbauend auf dem in diesem historischen Dokument beschriebenen lokalen 100-Song-`TracksV2`-Sample und den bekannten NAS-/Worker-Pfaden existiert ein neuer, versionsgebundener [PowerShell-Launcher](../scripts/run_autotune_e2e_windows.ps1) fuer echte opt-in Autotune-versus-Fixed-End-to-End-Messungen. **Den kopierbaren `& { ... }`-Aufruf samt Plan-only-/Execute-Schalter im [neueren PR-19-Handover](handover-phase-c-isolated-worker-20261028.md#kopierbarer-powershell-block-realer-autotune-end-to-end-benchmark-28102026) verwenden.** Kein lokales Binary aus historischen Runs unbesehen nutzen: der Launcher kontrolliert Git-Herkunft, Windows-Actions-Run 40697871147, BUILD.txt und EXE-SHA256. Die 6/8/10/12-Werte sind konkrete Vergleichs-Kandidaten, keine universelle optimale Workerzahl. Privater Realmusik-Speedup bleibt ungemessen, bis der echte Scan abgeschlossen ist.

## Phase B: erster echter 100-Song-Autotune-Benchmark und nachgewiesene frühe Exploration-Sperre

Im echten Windows/NAS-E2E-Benchmark wurden **10 vollständige private 100-Song-Scans** mit allen drei Klassifikationsmodellen und exakt identischen SQLite-Klassifikations- und 1280D-Embedding-Daten durchgeführt. Gesamtlaufzeit-Mediane: fixed6 **90,079s**, fixed8 **82,562s**, fixed10 **73,055s**, fixed12 **70,560s** und autotune 6..12 **87,559s**. Jeder Lauf verarbeitete 27.617 EffNet-Patches; keine kritische RAM-Grenze. Die echten Autotune-Einzelfenster zeigen in beiden Wiederholungen ausschließlich 6-Worker-Probes und keinerlei Controllerexpansion. Der alte erste Budget-Check verlangte aufgrund eines bereits gemessenen Kandidaten und doppelten fensterbezogenen Overheads **96 undispatchte Songs**, obwohl nach der ersten 12-Song-Probe höchstens 88 Songs verblieben. Daher keine Chance zur Exploration. Die neue hardwareunabhängige Regel verlangt für den ersten Sweep nur einen gemessenen Fensterumfang pro noch *unbesuchtem* Kandidaten plus einen zur Ausnutzung, während teure Replikation optional bleibt. Zusätzlich konkrete diagnostische Budgetparameter und gemessene Fenstergrößen als Regressionstest. Vollständiger wissenschaftlicher Befund: [online-autotune-phase-b.md](online-autotune-phase-b.md). **Erneute echte Verbesserung noch nicht gemessen**; neuer Quellcommit darf erst mit eigenem exakt passendem Windows-CI-Binary erneut lokal getestet werden.
