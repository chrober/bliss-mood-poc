# General, untrained GLOBAL pairwise similarity: four exploratory fixed fusions (2026-10-29)

> **Strategische Einordnung (29.10.2026):** Die vier hier getesteten globalen Genre/Mood/Audio-Fusionen sind lediglich **WP1** des verbindlichen, gleichberechtigten Dreiklangs aus **General Similarity Metric**, **Personal Metric Learning + 0–100%-Blending** und **Bliss ↔ Essentia Feature Relationships einschließlich Verbesserungen der Bliss-only-Metrik**. Die [konsolidierte Forschungsstrategie](similarity-three-workstreams-strategy-20261029.md) ist für diesen Forschungsbranch maßgeblich. WP2 und WP3 beginnen konzeptionell und mit sicheren synthetischen Untersuchungen **parallel**, nicht erst nach einem endgültigen WP1-Gewinner. Kein verpflichtender zusätzlicher Hörtest; PR #16 unverändert. Der reale MTT-Großworkflow [Run 40881326086](https://github.com/chrober/bliss-mood-poc/actions/runs/40881326086) ist wegen HTTP-Range-Timeout (curl code 28, HTTP 000) in der benötigten Clip-Cache-Erstellung fehlgeschlagen; **keine** neuen realen Fusionsergebnisse dürfen behauptet werden.


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
