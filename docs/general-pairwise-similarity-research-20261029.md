# General, untrained GLOBAL pairwise similarity: four exploratory fixed fusions (2026-10-29)

> **WP1-E6/E7 REAL PUBLIC CORPUS FEASIBILITY AND HISTORICAL BASELINES — 30 OCT 2026:** [Source-licensed-audio access is not established](wp1-e6-ccmsim-source-coverage-and-audio-rights-gate-20261030.md): original CCMSim human source pairs are sparsely distributed over nine separate audio corpora. Even three named source corpora (FMA-medium, MagnaTagATune, Lyra) would offer only **106/1,130 pairs** if *all* original 153 referenced clips could be obtained lawfully, and 100/106 labels are single-rater. The E6 metadata-only original-source audit [CI 41072601751](https://github.com/chrober/bliss-mood-poc/actions/runs/41072601751) passed without any audio. [Replayed 11 original third-party CCMSim audio scorers](wp1-e7-ccmsim-published-baselines-20261030.md) from the authors' **already published** same-pair score table, [CI 41073110130](https://github.com/chrober/bliss-mood-poc/actions/runs/41073110130) PASS: overall-human-similarity raw all-pairs Spearman CLAP Music+Speech 0.369369, SP Melody 0.326620, MERT95 0.297746; 112 within-dataset and 1,018 cross-dataset pairs reported separately. These are **NOT Bliss23/Essentia1280/Genre87/Mood56** and do not select or prove quality of our General metric; there is no license grant for original per-track audio. E5 song-disjoint split test retains only 40 heldout pairs and neither artist-level independence nor publisher source rights have been proven. No audio, weights, user ratings or production changed. WP1 General still unresolved, MTT global fusions unmeasured on original 1,019 clips (sparse access failed after 7/30), FMA official TEST reserved, WP2/3 parallel, do not merge to main or PR #16.


> **WP1-E5 REAL CCMSim CLIP-DISJOINT HOLDOUT FEASIBILITY — 30 OCT 2026:** [Source-pinned human-pair graph metadata audit](wp1-e5-ccmsim-clip-disjoint-split-feasibility-20261030.md) passed actual [GitHub Actions 41070926652](https://github.com/chrober/bliss-mood-poc/actions/runs/41070926652), with Linux/Windows synthetic regression gates. This is **not** an acoustic General Metric test. Fixed, label-blind source-balanced song-ID 60/20/20 partition retains **394 train / 47 validation / 40 test** of 1,130 human-annotated CCMSim pairs, quarantining **649** crossing pairs; only **5 of 40 test pairs** are within a source dataset. Five original-seed sensitivities yield only **38–48 test pairs**. Fixed 5-fold alternatives retain **210–244** total pair edges across five folds (18.58–21.59%), 31–68 per fold. Known song IDs are disjoint across partitions, but independent artists/recording families remain UNVERIFIED and original audio rights/segment parity are not cleared. **No-Go for learned/tuned General Metric based on CCMSim labels with a claimed robust independent holdout**; consider a frozen untrained external zero-shot descriptive test only after lawful exact recording features are available. Original full-MTT global fusion remains unmeasured, FMA official TEST untouched, Personal/teacher proxies separate, no production or PR #16/main changes.


> **30 OCT 2026 WP1-E3 SCIENTIFIC STATUS:** Genuine SHA-256-locked public aggregate replay and [sharp feasible paired correctness bounds](wp1-e3-sharp-mtt-paired-bounds-and-existing-pilot-20261030.md) **PASS** ([CI 41064623284](https://github.com/chrober/bliss-mood-poc/actions/runs/41064623284)). Mood centered cosine 193/293 differs from Mood cosine 192/293 by ONE marginal correct outcome, but the unknown paired correctness mismatch may be **1–201 questions**; actual matched analysis and reliable uncertainty cannot be calculated without discarded per-question predictions. All four **globally comparable pair-score fusions remain UNMEASURED** on real MTT because original audio access halted at 7/30 verified clip trials (WP1-E2). Optional read-only replay of existing local *12 already-rated human pairs* is now scripted for Windows; no new votes and not an independent holdout. Keep FMA official TEST untouched, task scores separate, WP2 Personal optional and WP3 teacher proxies not perceptual truth. **Do not select a universal General Metric or merge experimental branches.**


> **MEASURED WP1-E2 REPEATED-RANGE FAILURE — 30 OCT 2026:** Original official MTT MP3 source is reachable for three 4096-byte HTTP-206 tests and one fully verified 116,178-byte original ZIP member. The [30-member source stress gate 41060669011](https://github.com/chrober/bliss-mood-poc/actions/runs/41060669011) failed to complete: only **7/30 CRC-verified clips** (3/2/2 across original archive parts), source failure class RANGE_TRANSPORT_FAILURE, despite 3.5-second request pacing. No per-track features or quality metric was published. The original 1,019-clip rerun is now explicitly **blocked** until stable, lawful, verified source access exists; branch-scoped prior audio cache cannot be accessed as a sibling branch. Continue cross-task evidence and optional WP2 research separately. The four predeclared global pair fusions are still **unmeasured** on real MTT. [Detailed diagnosis](wp1-e2-mtt-source-and-cache-diagnostics-20261030.md).


> **LATEST WP1-E2 SOURCE DIAGNOSIS — 30 OCT 2026:** After the old global-fusion MTT workflow failed on an absent sibling-branch-scoped cache and timeout retrieving an official original MP3 range, a [new source-only diagnostic](wp1-e2-mtt-source-and-cache-diagnostics-20261030.md) verified three live 4096-byte HTTP-206 archive-part ranges and one complete original ZIP-CRC-checked registered clip. The originally failed full 1,019-clip fusion evaluation is STILL **UNMEASURED**: metadata/one-clip reachability is not full corpus replay. An optional bounded 30-clip request-pacing stress gate now tests sustained availability without publishing audio. Do not invent global fusion scores, create a new public licensed-audio cache, access reserved FMA TEST or choose a General Metric based on pseudo-Teacher WP3 results. Preserve WP2 Personal and separate cross-task MTT/FMA/DEAM evidence.


> **Strategic scope (29 October 2026):** These four fixed global Genre/Mood/Audio fusions represent **only WP1** of a mandatory three-track research strategy: **General Similarity Metric**, **Personal Metric Learning with 0–100% General/Personal blending**, and **Bliss ↔ Essentia Feature Relationships, including genuinely improved Bliss-only similarity**. See the [unified strategy](similarity-three-workstreams-strategy-20261029.md). WP2 interfaces and WP3 paired-feature research begin **in parallel** rather than waiting for WP1 to declare a winner. No additional compulsory listening; PR #16 unchanged. The real MTT replay [run 40881326086](https://github.com/chrober/bliss-mood-poc/actions/runs/40881326086) failed during required sparse-cache construction (publisher HTTP-Range timeout, curl code 28, HTTP 000), yielding **no new real fusion scores**.


**Separate research branch:** `feat/general-pairwise-similarity-research`,
forked at the exact existing Draft PR #16 head
`2204ec91d8d8a773872f266397b0656178b481ee` solely to reuse its
original, pinned, tested MTT/FMA/DEAM evaluation code.
**No commits to PR #16 or its branch, main, or production mixer.**
Do not merge any experimental fusion to production until independent
task-appropriate evidence justifies it.

## Why now

The **original native Essentia C++ same-100 song engineering gate PASSED**
on the separate bridge branch; see
[real native results](https://github.com/chrober/bliss-mood-poc/blob/feat/native-similarity-cohort-validation/docs/native-similarity-100-real-results-20261029.md).
All five old-vs-native rank Spearman correlations on 4,950 pairs round
to 1.00000000. This establishes technical backend continuity, **not**
musical quality. No more same-100 rescans or worker tuning.

Existing PR #16 scientific development observations:
- MTT previously explored all **346 unordered triplets**, with **293**
  unique majority labels: Mood centered cosine 193/293 = 65.870%,
  Genre cosine 191/293 = 65.188%, embedding cosine 182/293 = 62.116%.
- Prior **triplet-local equal-midrank** three-way fusion achieved
  192/293 = 65.529%, versus 193/293 Mood centered cosine.
  It **does not define a global songpair similarity value** and can
  abstain due to summed rank ties. Do not silently reuse as a Lyrion score.
- FMA screened **VALIDATION** (80 songs, same 79 candidates/query):
  Genre centered cosine P@5 = 0.3225, mAP@10 = 0.178147.
  Official FMA TEST is still reserved and must remain unexamined during
  exploratory method development.
- Screened DEAM 240 Mood cosine VA rank reference is ~0.286784551;
  previous paired embedding-vs-head real workflow was blocked by a
  publisher HTTPS outage. No verified DEAM three-head fusion result.
- The original **12 human listening labels** (11 music-only
  sensitivity) are already explored; no new compulsory user judgments.
  They are not an independent or sufficient fusion-weight fitting set.

## Registered hypothesis and exact mathematical definition

Investigate whether fixed, globally defined pairwise fusions avoid
the triplet-local tie pathology while making use of complementary
Genre, Mood and Timbre representations. This is a **post-hoc
development hypothesis**, formulated after earlier benchmark results;
not independently preregistered, unbiased validation or metric selection.

Given two songs `a,b`, define independently for each signal:

- `G(a,b) = (1 + centered_cosine(genre_87D[a], genre_87D[b]))/2`
- `M(a,b) = (1 + centered_cosine(mood_56D[a], mood_56D[b]))/2`
- `A(a,b) = (1 + cosine(embedding_1280D[a], embedding_1280D[b]))/2`

Clamped within numerical tolerance to [0,1]; undefined/invalid input
abstains **for the entire pair**, never silently reweights missing
signals. A fusion of included signals `H` returns

```text
S_H(a,b) = sum(signal_h(a,b) for h in H) / len(H)
```

with **no fitted weights, no personal training**, no candidate-list
normalization and no external reference-cohort dependency. All input
signals are cosine/centered-cosine evaluated on the exact same two
songs. The four immutable research IDs are:

| Method | Formula |
| --- | --- |
| `global_genre_mood_equal` | (G + M)/2 |
| `global_genre_audio_equal` | (G + A)/2 |
| `global_mood_audio_equal` | (M + A)/2 |
| `global_genre_mood_audio_equal` | (G + M + A)/3 |

This is a *range transform*, not empirical distribution matching or
proof that the three heads are commensurate, equally informative, or
calibrated probabilities. Multiple variants are **comparative
ablations**; a higher observed benchmark score does not automatically
justify production adoption or weight search. In particular, a
symmetric score cannot directly model the directed judgement
`next_track_suitability`.

## Implemented in this separate branch

- `scripts/global_pairwise_fusion.py`: exact scoring specification,
  fixed IDs, deterministic formula, nonfinite/degenerate fail-closed
  and JSON-safe provenance.
- Original `scripts/evaluate_mtt_embedding_ab.py`: new
  `--global-pair-fusions` flag adds exactly four global scorers to the
  existing five on the **same 293 human-majority questions / same 1,019
  clips**. Undefined/tie => incorrect on the same denominator; includes
  existing paired sensitivity diagnostics. The original invocation
  without flag retains its old schema and methods.
- Original FMA and DEAM paired evaluators: same optional flag, distinct
  versioned aggregate schemas, original source/candidate/genre/protocol
  gates and original baselines unchanged. FMA includes genre-stratified
  sensitivity, DEAM retains separate 197/43 collection sensitivity.
  These are **different scientific tasks**, not combinable numerical
  effect sizes.
- Synthetic regressions include symmetry, candidate-set invariance,
  fixed equal weights, no silent missing-vector renormalization,
  old-baseline reproducibility and complete denominator/coverage.
- `.github/workflows/research-global-pair-fusion-synthetic.yml`:
  Linux/Windows synthetic, no licensed audio/model/ratings and original
  MTT/FMA/DEAM contract regression.
- `.github/workflows/research-global-pair-fusion-mtt.yml`:
  separate automatic replay of the existing **public MTT** research
  pipeline. Downloads verified publisher metadata/8-MiB ZIP directory;
  attempts a branch-accessible curated cache; on miss uses bounded,
  rate-limited HTTP 206 member ranges for **only the 1,019 referenced
  MP3 clips**, CRC checks against publisher ZIP, and builds a transient
  compact ZIP. Does NOT download all 2.77 GiB; does not publish a new
  audio cache or any original audio, human votes, per-song features,
  embeddings or track identities as Actions artifacts. Existing
  Rust-v5 scanner/provenance and same-clip analysis code are reused;
  no work on the worker controller or native Windows bundle.
  Real run may safely fail if publisher range serving is unavailable.
  The output artifact contains **aggregate results only**.
- `scripts/mtt_selected_clip_cache.py --remote-range-source`:
  optional new source mode. The old local source-part builder and
  verified-cache reader retain their default behavior, with synthetic
  1,019-entry ZIP/CRC tests. The source URLs and host must match the
  verified original publisher ZIP metadata; HTTP 200 full-archive
  responses are rejected.

## Evidentiary acceptance criteria

For the **real MTT** comparison, the entire workflow must pass:
registered metadata hashes, 346/1,019 membership, model and audio
integrity, fixed five original baseline results reproduced, exactly
293 decided human triplets, counts (correct + incorrect/abstention),
and all four global candidate results. Report 293-denominator
accuracy, coverage, per-method abstentions and paired discordance
and sensitivity against Mood centered cosine. Do **not** claim
statistical generality from query resampling: songs and artists
overlap across questions.

Only after this pass, consider reusing FMA VAL and DEAM paired
evaluation on the exact frozen cohorts, if research data and legally
permissible archive access are available. No new human testing is
required. Any choice of variant derived from already-explored
MTT/FMA/DEAM is **development only**; independent validation requires
predeclared criteria and an unused suitable holdout. The official
FMA TEST must **not** be opened simply to break a development tie.

## Results status and next handoff

- **Proven**: real native same-100 engineering continuation; existing
  MTT and FMA prior A/B evidence cited above.
- **Implemented**: opt-in global pair scorer, three benchmark adapters,
  isolated synthetic CI and standalone MTT replay workflow.
- **Unproven**: accuracy of these four global fusions on actual
  MTT/FMA/DEAM recordings, any numerical improvement over baseline,
  any universal winner or playlist-transition improvement.
- **Not requested**: changes to Draft PR #16, additional mandatory user
  listening labels, personal training or worker-autotuning.

After a completed real MTT run, update *this document* from the
aggregate CI outputs (not from invented scores), preserve original
test reports, and mark any new ranking **exploratory / already
developed**. Do not run unnecessary extra researcher-selected tests
or claim independent evidence from the previously explored MTT corpus.
