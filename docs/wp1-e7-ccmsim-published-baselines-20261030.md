# WP1-E7: third-party published 11-model human-similarity baselines on CCMSim (30 October 2026)

## An actual public-data replay; NOT a test of Bliss, Essentia or Lyrion

[GitHub Actions 41073110130](https://github.com/chrober/bliss-mood-poc/actions/runs/41073110130) **PASS**: original public CCMSim authors' pair-score table re-read and Git blob verified, along with the published CC BY 4.0 human similarity labels and clip-source mapping. Linux and Windows offline tests pass; live report includes exactly **11 authors' third-party computational scorers**, **three human objectives**, **1,130 original rated pairs** and three fixed all/within-source/cross-source strata. [Frozen reproduction code](../scripts/replay_wp1_e7_ccmsim_published_baselines.py), [offline regression tests](../tests/test_replay_wp1_e7_ccmsim_published_baselines.py) and [workflow](../.github/workflows/research-wp1-e7-ccmsim-published-baselines.yml).

Exact pinned source: `pxaris/CCMSim` commit `eff8ab428dd12f1973548d657928b5211dd290bb`; `data/combined_similarities.csv` blob SHA-1 **`b0d475c6f58f5d0ec2fbdeaaca57d87f472a2c3d`**, original `data/annotations/human_similarity.csv` blob `dd1f026ca72cc1616a7a7cdebd333d869d6c6720`, original `data/annotations/audio_annotations_mapping.csv` blob `0921898a7920858db0472ed11bc222578f80d834`. The read-only auditor checks 1,130 **same unordered pair IDs**, no duplicates and exact equality of all three human score values between the combined dataset and separate authoritative annotations. Published pair scores must be finite similarities in [0,1]; no original participant raw responses are accessed, no audio downloaded, and no new model inference or personal feature extraction occurs. Public song/pair/source paths and row-level scores are **not** emitted by the report; only method/endpoint/stratum aggregate correlations appear.

The eleven *published* methods are `SP-Melody`, `SP-Rhythm`, `SP-Harmony`, `SP-Timbre`, `FM-MERT_95`, `FM-MERT_330`, `FM-CULTURE_MERT`, `FM-CULTURE_MERT_TA`, `FM-CLAP_MUSIC`, `FM-CLAP_MUSIC_SPEECH`, and `FM-QWEN`. **None** of these 11 is automatically our Genre87, Mood56, original Essentia embedding1280, Bliss23, or any trained or combined General Metric candidate.

## Actual reproduced descriptive Spearman rank correlations

Correlation is computed directly on the authors' original complete published 1,130 pair rows, **with average ranks for ties**; no label fitting, regression, optimizations, p-values, FMA official TEST, or data-dependent subset selection. Repeated clips across many pair rows mean **1,130 is not an independent sample size for significance**, and human labels are predominantly from one annotator. The authors' independent report `report/similarity_alignment/alignment_metrics.csv` uses varying metric denominators (e.g. 426/427/443) for its particular study metrics, so our **1,130-row Spearman replay is not identical to the authors' per-query or filtered published headline analyses** and should not be described as their measured value.

| Published third-party model | Overall similarity, all 1,130 | Cultural similarity, all 1,130 | Recommendation level, all 1,130 |
| --- | ---: | ---: | ---: |
| **FM-CLAP_MUSIC_SPEECH** | **0.369369** | **0.330715** | **0.339621** |
| SP-Melody | 0.326620 | 0.317907 | 0.301200 |
| FM-MERT_95 | 0.297746 | 0.281572 | 0.279291 |
| FM-MERT_330 | 0.252633 | 0.238831 | 0.240707 |
| FM-QWEN | 0.243387 | 0.252878 | 0.242843 |

These are **the leading five in the overall-similarity column**, not an assertion that the same ranking holds for every target or source slice. The exact workflow aggregate JSON contains all **11 methods × 3 objectives × 3 predeclared strata**; only five methods are excerpted above for readability.

| Published method and target | Within source only (112 rated pairs) | Cross source only (1,018 rated pairs) |
| --- | ---: | ---: |
| FM-CLAP_MUSIC_SPEECH, overall similarity | **0.347485** | **0.329279** |
| SP-Melody, overall similarity | 0.243768 | 0.290241 |
| FM-MERT_95, overall similarity | 0.301883 | 0.261825 |
| FM-CLAP_MUSIC_SPEECH, recommendation level | 0.250865 | **0.301712** |
| FM-MERT_95, recommendation level | **0.290967** | 0.240998 |
| FM-CLAP_MUSIC_SPEECH, cultural similarity | 0.322260 | **0.291709** |
| FM-MERT_95, cultural similarity | **0.324558** | 0.238253 |

In the 112 within-source pairs, MERT_95 narrowly exceeds CLAP_MUSIC_SPEECH on cultural similarity (0.324558 vs 0.322260) and has a stronger recommendation-level correlation (0.290967 vs 0.250865); these are purely descriptive differences between public scorers, not adjusted statistical claims or evidence of individual listener playlist quality. Within-source coverage is **112 across nine source corpora**, not 112 within any one corpus. The 1,018 cross-source pairs are likewise interdependent and culturally skewed.

## Why this matters to WP1 and what must not be concluded

1. **There is real existing third-party experience**: signal-processing melody similarity, audio encoders MERT, CLAP and Qwen, and learned ensembling have already been studied by the original CCMSim authors. We should not claim that nobody has investigated globally comparable song similarity or that every evaluation method must be invented from scratch.
2. Baseline pair-score correlations to a heterogeneous, generally one-annotator human corpus remain moderate. This motivates combining robust acoustic and semantic signals **only as an unverified design hypothesis** and retaining separate endpoints. Raw Spearman values on different datasets (our MTT 293 triplets, FMA genre retrieval, DEAM VA proximity and local 11-pair listening pilot) cannot be averaged or directly compared numerically.
3. **No actual result for our General or Personal Metric**: the CCMSim authors used different models and audio. The published score table does **not** contain original Genre87/Mood56/Essentia1280/Bliss23 features from our implementation. Do not rename CLAP or MERT scores as Essentia outputs, and do not fit/adopt their ensemble weights as if already validated for Lyrion.
4. **Historical study, not independent validation**: this is a replay of public original-model predictions and publicly known human scores. Additional reanalysis after observing this ranked table is exploratory only. The single-rater predominance, artist/recording overlap risks and severe [WP1-E5 frozen clip holdout shortfall](wp1-e5-ccmsim-clip-disjoint-split-feasibility-20261030.md) still prevent a robust General-Metric training/test superiority claim.
5. [WP1-E6 source rights and source-pair ceilings](wp1-e6-ccmsim-source-coverage-and-audio-rights-gate-20261030.md) apply fully. The annotations and computational published scores can be studied under their stated licenses; this does **not** grant permission to retrieve or redistribute third-party audio. FMA-medium/MTT/Lyra alone would cover at most 106 mostly single-rated original human pairs even with every clip lawfully recovered.

## Decision

**WP1-E7 third-party baseline replay is complete**. It offers actual public human-pair benchmark context without audio, independent of the operator's private one-listener pilot, but **does not increase the directly measured perceptual effectiveness of our General Metric**. Preserve Mood Centered Cosine, original Essentia embedding1280, other original task-specific metrics and Bliss23 as distinct unfitted WP1 candidates; do not tune new fusion weights on these publicly inspected human labels.

Next useful research priority is to assess whether a sufficiently large and licensed **same-recording** public reference actually exists for our own models, or find precomputed *original Essentia output vectors* on those exact clips. Do **not** treat third-party models or small restricted-source subsets as direct replacements. Keep FMA official TEST untouched, MTT original source 7/30 failure, WP2 synthetic Personal safeguards and WP3 teacher-proxy investigation separate. No Lyrion, other repo, PR #16 or main changes.
