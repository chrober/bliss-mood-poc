# Phase B: RAM-gated nonmonotonic online worker autotuning

**Status (28 October 2026): experimental opt-in implementation in `feat/ram-safe-online-autotune`, stacked on PR #18. NOT a validated production scheduler or proof of an optimum.** The previous resource-threshold controller is unchanged and selected by default.

## Design intent

The goal is **one adaptive strategy which discovers effective concurrency on its actual host and workload**, not a Ryzen-specific fixed-worker recommendation. The existing 100-song/3-model native C++ benchmark gave median 6=70.98, 8=70.42, 10=63.75 and 12=88.17 songs/minute (two repeats). That is a **nonmonotone observed throughput curve**, with possible environmental noise. A hill-climbing rule that abandons higher counts after a worse point is unsuitable. No claim of causality, universal optimum, or safe fixed-twelve default follows.

Separate mechanisms:

1. **Admission safety / resource governor:** use the CPU capacity permitted to the process as a hard upper bound (maximum 64) and measure available memory before starting. Compute a conservative initial reserve, here `max(512 MiB, 10% of initially available memory)`, and charge **at least 256 MiB estimated incremental memory per added worker**. Reduce the preferred initial concurrency if its estimated budget would be exceeded, rather than assuming `--workers auto` is always safe. Require valid free-RAM telemetry on every completion, **and run an independent 250-ms memory watchdog while a song is in flight**. A missing/invalid sample or a breached reserve is a terminal safety fault: the watchdog signals native IPC cancellation, the coordinator stops dispatch and checks its guard during 200-ms result waits, and the owning Rust threads kill/reap their native Essentia child processes (rather than killing bare PIDs). A completion-driven failure also signals cancellation immediately. On lesser headroom pressure, the online tuner reduces concurrency instead of launching additional sessions. Raise the incremental-memory estimate whenever observed host/cgroup memory depletion implies higher costs; never relax the estimate within that scan. These **provisional guardrails** are portable heuristics to test, **not a guarantee against OOM**. The watchdog is independent of song completions but still samples periodically, so rapid allocations can exceed its margin between polls. Native C++ IPC can be cancelled promptly using the owning Child handle; already-running Rust ONNX computation is **not** preemptible yet. The current design cannot guarantee that an operating system or cgroup OOM killer will not intervene first. Failures may leave a *partial, private* sidecar rather than silently continuing.

2. **Online throughput exploration:** an ordered **coarse candidate schedule** includes minimum, initial, maximum and evenly spaced intermediate worker counts, with no assumption of monotonicity. Each candidate needs at least eight successfully completed songs and twelve seconds of data before its score is accepted. Score is analyzed EffNet patches/second, alongside songs/minute, rather than raw CPU load (which is not a throughput objective). Explore higher candidates even after a lower candidate performs worse. Use a 5% improvement margin when selecting the best observed candidate, to limit insignificant switches. For longer scans, return to the best observed candidate between budgeted re-exploration rounds. Each candidate is separately RAM-gated. The controller adjusts only the **in-flight dispatch cap**; native/ONNX sessions are persistent and never restarted for re-sizing.

3. **Diagnostics:** the existing `diagnostics.adjustments` and `diagnostics.controller_decisions` belong to the legacy policy. Experimental observations live under `diagnostics.online_autotune`: actual starting/final workers, coarse probe measurements, RAM reserve and worker estimate, candidate changes with available RAM, probe/safety counters, and a `search_completed` marker that is false unless **all** bounded candidates actually have measurements. `best_tested_workers` is the best **observed sample**, not a confidence-backed true optimum.

## Invocation (experimental)

```text
bliss-mood scan-features ... --workers auto --adaptive-workers \
  --adaptive-policy autotune --min-workers 1 --max-workers auto \
  --threads 1 --priority normal --json
```

Windows `--priority normal` is only for explicitly controlled comparisons; omit it for portable Linux usage. Use an explicit bounded `--max-new`, a fresh sidecar, and matching model/native worker versions for research. The legacy mode remains `--adaptive-policy resource` (default), with the existing minimum-song gate and 20-second cooldown.

Linux free RAM now combines `/proc/meminfo` with available standard cgroup v2 (`memory.max`, `memory.current`) or v1 memory-controller counters. This is **not yet a full cgroup namespace/mountinfo resolution** and does not cover all nested/container layouts, swap quotas, CPU throttling, or macOS. Where free RAM cannot be read, `autotune` refuses to begin. Tests must cover cgroup variation, failure handling and 4-GB Raspberry Pi constraints before enabling it by default.

## Why this is only Phase B groundwork

- **A short scan cannot identify an optimum.** Coarse candidates can remain untested; no success claim is allowed. The extra initialization cost of rarely used ONNX sessions can hurt short-job throughput.
- A fixed-duration window over *different songs* and NAS caching does not give a statistically comparable experiment. Patch count is a useful denominator, but decode cost, song complexity and ambient interference vary. Do not mistake a single 5% margin for statistical significance.
- **Implemented:** independent watchdog at ~250 ms, coordinator polling at ~200 ms on outstanding completions, explicit native IPC cancellation and process reaping on a memory fault, and additional `diagnostics.memory_watchdog` with sampled low-water RAM. **Still missing:** preemptive Rust ONNX cancellation, measured per-session allocation accounting, full cgroup OOM event inspection, sub-poll allocation protection and a platform-tested hard stop for in-flight nonnative computation. Treat these as blockers to calling RAM safety complete.
- The candidate spacing is provisional and can miss narrow peaks. Explore/refine adaptively with paired/interleaved comparisons, repeated probes, recency-aware confidence estimates and change-detection, while charging search cost. Resource isolation must always dominate optimization.
- Benchmark *completed-song throughput* and *time-to-finish* along with patches/sec on long, heterogeneous bounded cohorts and on differing host budgets. Synthetic tests must include 6→8→10→12 with a local trough, increasing monotone, decreasing, flat/noisy, changing workload, and low-RAM situations. Verify strict classification / embedding parity with the original native C++ frontend.
- Test on CPU-constrained containers and ARM/4-GB machines before generalizing. Defaults must remain stable and fail safe; PR #16 similarity work and original library/Bliss DB stay untouched.

## Next implementation gates

1. Make CI Rust tests/Clippy and native smoke green for **exact** Phase B code head; add CLI integration and failure-mode tests.
2. Validate the new independent 250-ms watchdog and native cancellation path under deliberately blocked native IO and synthetic RAM faults; introduce robust nonnative inference cancellation or a reliable process-level safety boundary, and finish nested cgroup/macOS detection.
3. Improve online measurement with repeated, paired/interleaved candidate windows and a confidence/stability criterion, explicitly accounting for exploration overhead and remaining scan size.
4. Exercise a mixed-duration, private local manifest with no raw private data committed. Compare to best safe fixed setting **per host** solely for validation; no host-specific tuning rules.
5. Only after cross-platform, RAM pressure, throughput and parity validation consider making autotune the default.
