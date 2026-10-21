# MagnaTagATune: paired similarity evidence and runner performance

**Date:** 2026-10-21. **Branch:** `feat/similarity-metric-evaluation`;
Draft PR #16. No merge to main or changes to PR #13/#17.

## Verified canonical 346-triplet measurement

[Successful cache-HIT run 39600498519](https://github.com/chrober/bliss-mood-poc/actions/runs/39600498519)
(aggregate report/artifact [12346356813](https://github.com/chrober/bliss-mood-poc/actions/runs/39600498519/artifacts/12346356813)):
- 1,019 MP3 clips, 346 unique unordered three-clip questions
  (NOT 533 independent observations), **53 human majority-choice ties**;
  293 common human-scorable questions.
- Genuine corrected Rust-v5 ONNX pipeline, 87D Genre and 56D Mood/Theme,
  two independent subprocess workers, two isolated SQLite sidecars.
- Original MP3 ZIPs **not downloaded**. True curated research-audio
  cache HIT, 119,689,247 bytes (~114 MiB) for 1,019 CRC-verified
  source clips, only an 8-MiB publisher archive tail downloaded.
- Description below reports **abstentions as incorrect**, on
  exactly the same 293 eligible questions.

| MTT metric | Genre % | Mood/Theme % | Mood nonabstention % |
| --- | ---: | ---: | ---: |
| RMS | 63.5 | 54.6 | 100 |
| Cosine | 65.2 | 65.5 | 100 |
| Centered Cosine | 65.2 | **65.9** | 100 |
| Weighted Jaccard | 63.8 | 61.1 | 100 |
| Historical Top-K Weighted Jaccard | 60.1 | 44.4 | **71.7** |
| Ranked Top-6 Jaccard | 61.8 | 62.5 | 100 |
| Ranked Top-12 Jaccard | 64.5 | 64.8 | 100 |

The differences between full-coverage Cosine and Centered Cosine
are only **~0.4 percentage points (Mood)** and 0 (Genre).
This is **not evidence of a clear winner**: audio is lossy short
clips, reference is general human similarity rather than head-specific
Genre/Mood similarity, original embeddings may have training-set
overlap, and many triplets share artists/tracks. The complete corpus
has been used for exploratory scoring; **no unseen MTT holdout remains**.

## Statistical robustness implemented

[scripts/mtt_paired_evidence.py](../scripts/mtt_paired_evidence.py)
computes per head all **21** paired contrasts between seven
methods (**42** across both heads), using the *same* 293
human-majority-scorable questions. Each metric abstention is counted
as incorrect rather than silently dropping its questions.

For each pair, the aggregate JSON contains:
- observed difference in accuracy in percentage points, with counts
  of questions only A vs only B gets right (paired discordance);
- a fixed-seed, shared-question **IID resampling interval**
  over 600 draws (optimistic because questions share music);
- an **artist-weight randomized sensitivity interval**
  over 600 draws, perturbing questions according to the artists
  they contain (not a valid artist-cluster bootstrap);
- all comparisons explicitly labeled *post hoc exploratory*,
  neither a population confidence interval nor a hypothesis-test
  p-value. With a single connected 214-artist co-occurrence
  component no strictly independent artist-component bootstrap
  is possible on this dataset.

The benchmark performs these comparisons in RAM, using model
predictions from temporary private SQLite sidecars and original
human votes, **never exporting per-song features, artist names,
per-question raw votes or predictions**.
[scripts/summarize_mtt_benchmark.py](../scripts/summarize_mtt_benchmark.py)
emits a readable, aggregate-only 14-row overall scorecard plus
four selected paired contrasts per head (all 42 recorded in aggregate
JSON). No automatic production metric decision.

Linux/Windows tests:
[test_mtt_paired_evidence.py](../tests/test_mtt_paired_evidence.py),
[Python CI 39602141111](https://github.com/chrober/bliss-mood-poc/actions/runs/39602141111)
**PASS**. An initial test mistakenly searched for the literal string
"CI" in a disclaimer written as "confidence intervals";
the assertion was fixed, **no calculation or reference changed**.

A real benchmark integrating paired statistics was triggered in
[GH run 39602475906](https://github.com/chrober/bliss-mood-poc/actions/runs/39602475906).
Check its *completed* result and aggregate artifact before quoting
real paired delta intervals. Since a post-run image or model
selection is not independent, such intervals only express
within-corpus robustness.

## Measured GitHub Actions walltimes (not controlled A/B)

| Run | Source policy | Workers | Audio inference + SQLite merge | Complete Actions run |
| --- | --- | ---: | ---: | ---: |
| [39597229438](https://github.com/chrober/bliss-mood-poc/actions/runs/39597229438) | 2.77-GiB publisher ZIP temporary | 2 | 145.505 s | ~368 s |
| [39599548243](https://github.com/chrober/bliss-mood-poc/actions/runs/39599548243) | curate/cache 1,019 clips on MISS | 2 | 244.677 s | ~426 s |
| [39600498519](https://github.com/chrober/bliss-mood-poc/actions/runs/39600498519) | **True ~114-MiB selected-cache HIT** | 2 | 231.053 s | ~327 s |

A true cache HIT therefore omitted the 2.77-GiB download and
~1.2-s curated package build; observed end-to-end durations
dropped ~99 s versus the initial MISS, and ~41 s versus the earlier
uncached full-source run. **This is not a controlled inference-speed
comparison**: walltime for the same 1,019 clips varied between
145 and 245 seconds on GitHub hosts.

### Additional runtime optimization

Workflow [magnatagatune-all-exploratory.yml](../.github/workflows/magnatagatune-all-exploratory.yml)
now has a **separate, source-commit-keyed release Rust-v5 CLI cache**.
On a MISS it builds with `cargo build --release --locked`,
writes a SHA256 manifest and caches only the pinned Linux binary
and manifest. On HIT it skips the Rust toolchain, Cargo cache
restoration and build, and verifies the cached binary's SHA256 and
`analyze-features --help`. This cache is for the immutable
source commit `2c3d44401436b3b41b6e067199016a1ed2335fbf`;
it is not a replacement for verifying provenance and does not
make GitHub caches confidential.

The same workflow now accepts manual worker choice **1, 2 or 4**
with one ONNX thread per worker. Automatic path-filtered run
[39602865932](https://github.com/chrober/bliss-mood-poc/actions/runs/39602865932)
was configured for **4 workers** to measure against the earlier
2-worker runs, on the same source and 1,019 clips. Verify actual
completion, parity (all seven method/head aggregates), worker counts,
peak resource use, and time before claiming a speedup.

## Scientific path following MTT

Use these human-perceptual-similarity results to generate
**provisional, clearly labeled hypotheses**, not a final metric choice.
Cross-reference independent DEAM Valence/Arousal and FMA-Small
Genre-retrieval evidence, and audit training-data overlap.
Seek a genuinely independent, appropriately licensed, human
similarity/transition dataset for held-out confirmation;
eventually perform blinded Lyrion playlist listening.
Do not reuse the MTT 346 questions as new held-out evidence.


## Real paired evidence: verified PASS on full 346 MTT corpus

**PASS**: [Actions 39602475906](https://github.com/chrober/bliss-mood-poc/actions/runs/39602475906),
[aggregate-only JSON+Markdown artifact 12347665613](https://github.com/chrober/bliss-mood-poc/actions/runs/39602475906/artifacts/12347665613).
Both model heads, all seven metrics, 293 common
human-majority-scorable unordered triples, 21 paired method
comparisons/head, 600 deterministic shared-question draws and
600 exploratory artist-weight perturbations.

**Paired differences in accuracy (A minus B), percentage points,
always on exactly the same 293 human-scorable triplets with
metric abstentions counting as incorrect:**

| Head | A minus B | Observed delta | IID-triplet resampling interval | Artist-weight perturbation interval | A-only / B-only correct |
| --- | --- | ---: | --- | --- | ---: |
| Genre | Cosine – Centered Cosine | 0.0 pp | −2.1..2.4 pp | −1.2..1.2 pp | 5 / 5 |
| Genre | Cosine – RMS | +1.7 pp | −2.0..5.1 pp | −0.3..4.1 pp | 17 / 12 |
| Genre | Centered Cosine – Ranked Top-12 | +0.7 pp | −2.4..3.8 pp | −1.3..2.9 pp | 12 / 10 |
| Genre | Cosine – old Top-K WJ | +5.1 pp | 2.0..8.9 pp | 3.2..7.0 pp | 21 / 6 |
| Mood | Cosine – Centered Cosine | −0.3 pp | −2.7..2.4 pp | −2.0..1.4 pp | 8 / 9 |
| Mood | Cosine – RMS | +10.9 pp | 6.1..15.7 pp | 8.4..13.7 pp | 44 / 12 |
| Mood | Centered Cosine – Ranked Top-12 | +1.0 pp | −2.7..5.1 pp | −1.4..3.7 pp | 17 / 14 |
| Mood | Cosine – old Top-K WJ | +21.2 pp | 15.0..27.0 pp | 18.0..24.8 pp | 76 / 14 |

These are *post hoc, descriptive within-corpus sensitivity
intervals*, not independent population CIs, multiplicity-controlled
statistical tests or a generalizable best-method proof. The
single artist-connected component precludes independent artist
cluster bootstrap. Notably Cosine/Centered are extremely close,
with 5/5 Genre and 8/9 Mood discordant correct questions.
Conditional-only old Top-K accuracy is misleading because its
coverage is reduced. The full 42 pair summaries, without
clip/artist-level observations, are in the linked aggregate JSON.

The run also saved a **separate pinned Linux Rust-v5 binary cache**
after compiling the immutable PR #17 source, verifying its SHA256
manifest and CLI invocation. It took **291.251 s** to analyze
1,019 clips and merge two private worker SQLite sidecars
(scoring itself 1.053 s). Variance compared to prior two-worker
runs (145.505, 231.053, 244.677 s) is large; no direct
inference speed claim from the CI runner variation.

The next [run 39602865932](https://github.com/chrober/bliss-mood-poc/actions/runs/39602865932)
is the initial **four-worker** same-input A/B and has already
confirmed true Rust-v5 binary cache HIT (no Cargo build)
and 1,019-clip research cache HIT (no original archive download).
Verify its final status, numerical parity, inference walltime
and peak resource measurements before choosing worker count.
