# WP3: first real grouped Bliss23 -> Essentia teacher study (30 October 2026)

**Status:** COMPLETED, EXPLORATORY DEVELOPMENT ONLY. **Not** independent musical-similarity validation, a deployed similarity metric, a calibrated probability, or a trained personal metric.

## Evidence and chronology

This result is grounded in the operator's actual Windows PowerShell 5.1 output and the anonymized `aggregate-teacher-research.json` supplied on 30 October 2026. No raw per-track rows, vectors, MusicBrainz identities, audio files, private SQLite databases or personally rated pairs were uploaded or committed. The complete private aggregate remains on the operator's Windows machine.

The research follows the previously documented stages in [the consolidated WP3 record](wp3-consolidated-research-sqlite-20261029.md):

1. Bliss23 and native Essentia Genre87/MoodTheme56 were computed earlier on the same 100-song local research cohort; the standalone feature SQLite was first built **without** Lyrion grouping. 3,289 feature/class correlations and selected within-cohort robustness checks were performed **before** this group-heldout study.
2. Genuine LMS `library.db` and BlissMixerLab `artist-repeat-identities.sqlite` were located on the user's piCorePlayer. Read-only SQLite online backups were transferred to private Windows storage and individually validated. The exact four-source grouping preflight succeeded for 100/100 selected songs, without missing artists or albums.
3. The user invoked `scripts/build_wp3_research_db_windows.ps1`, using the existing Python **3.15.0** and explicitly supplied existing Lyrion metadata copies. It first reported `Group provenance: READY`, then created a **new** grouped private SQLite at `benchmark-wp3-research-20261030-091600-8c93d55f/wp3-research.sqlite`. It did **not** overwrite the earlier `benchmark-wp3-research-20261030-064618-7f8c43a3/wp3-research.sqlite`.
4. The launcher created a private isolated Python 3.15 environment, installed [pinned statistical dependencies](../research/requirements-wp3-py315.txt), then executed `scripts/run_local_bliss_essentia_teacher_study.py --research-db`. The resulting private, aggregate-only report is at `benchmark-wp3-research-20261030-091600-8c93d55f/aggregate-teacher-research.json`. Neither this report nor the private databases have been committed.

The reported schema is `local_bliss_essentia_teacher_only_development_aggregate_v1` and the report status is `EXPLORATORY_DEVELOPMENT_NOT_GENERAL_SIMILARITY_VALIDATION`.

## Genuine metadata and grouping quality gate

| Check | Verified result |
| --- | ---: |
| Eligible Essentia Genre/Mood pairs | 100 |
| Exact-key Bliss23 / Essentia pairs | 100 |
| Source-model provenance rejections | 0 |
| Missing or invalid Bliss vectors | 0 |
| Missing or unverified LMS track IDs / URLMD5 | 0 |
| Missing artist credits / albums | 0 / 0 |
| Missing recording MBIDs | 1 |
| Verified source-grounded artist / album / recording groups | 100 songs |
| Connected artist+album+recording components | 88 |
| Group-disjoint training / holdout songs | 75 / 25 |
| Unique unordered holdout song pairs | 300 |

The missing recording MBID was conservatively assigned to the shared unknown-recording group, rather than being guessed. Seed `20261029`; the artist/album/recording-connected 25% holdout was constructed before fitting the procedures in this run. The report confirms all fitted preprocessing, Ridge, PLS, PCA and CCA transformations use the 75-song training side only.

The grouped research builder reported `READY_FOR_GROUPED_RESEARCH`, `validated_artist_album_recording_holdout=true` and `source_databases_unchanged=true`. This confirms the **source matching and within-run group separation**, not independent verification of same audio bytes across Bliss/Essentia, fresh LMS scan/root fingerprints, provenance of pretrained Essentia teacher training examples, or complete artist attribution.

## Association study: train-ranked correlations with a group-heldout check

Every Bliss23 versus Essentia score combination was estimable on training data: 23 × 87 = **2,001** Genre pairs and 23 × 56 = **1,288** MoodTheme pairs; zero undefined Pearson or Spearman associations. Median absolute training Spearman was **0.240797** for Genre and **0.305548** for MoodTheme.

Five strongest absolute **training-selected** associations for each teacher head (numeric class indices are preserved because the aggregate does not provide an independently verified class-label mapping):

| Head | Bliss feature | Teacher class index | Train Spearman | Holdout Spearman |
| --- | --- | ---: | ---: | ---: |
| Genre87 | Chroma11 | 31 | -0.787767 | -0.406154 |
| Genre87 | Chroma13 | 49 | -0.766060 | -0.514615 |
| Genre87 | Chroma13 | 11 | -0.762788 | -0.433846 |
| Genre87 | Chroma13 | 55 | -0.754339 | -0.407692 |
| Genre87 | Chroma13 | 59 | +0.749332 | +0.603846 |
| MoodTheme56 | Chroma12 | 47 | -0.872461 | -0.581538 |
| MoodTheme56 | Chroma6 | 47 | -0.844637 | -0.529231 |
| MoodTheme56 | Chroma11 | 47 | -0.844410 | -0.554615 |
| MoodTheme56 | Chroma13 | 47 | -0.843642 | -0.591538 |
| MoodTheme56 | Chroma12 | 43 | -0.839118 | -0.536154 |

All ten displayed associations retain their sign in the heldout subset but generally weaken substantially. For example MoodTheme Chroma12/class47 drops in absolute value from **0.872** to **0.582**. This is evidence against treating the strongest whole-cohort correlations as portable universal feature rules. The 3,289-way search is exploratory; multiplicity has **not** been adjusted and no statistical significance or causal relationship is claimed.

## Prediction study: reconstructing Essentia classifier outputs from Bliss

The target is the respective **87- or 56-dimensional model-output vector**, not a human genre/mood judgment. The baseline predicts each class's TRAINING mean. All errors below are mean absolute error (**MAE**) measured on the group-disjoint 25-song holdout; lower is better.

| Teacher head | Train-mean baseline MAE | Ridge MAE | PLS MAE | Best reduction vs baseline |
| --- | ---: | ---: | ---: | ---: |
| Genre87 | 0.020521206 | 0.019421774 | **0.019100153** | **6.92%** (PLS) |
| MoodTheme56 | 0.016937433 | **0.014728956** | 0.015288421 | **13.04%** (Ridge) |

Ridge improved Genre MAE by **5.36%**, while PLS improved MoodTheme MAE by **9.74%**, relative to their respective baseline. Fixed, non-tuned within-run settings: `ridge_alpha=10`, `pls_components=2`, `cca_components=1`, maximum PCA dimensions per CCA view **3**. Reported one-dimensional heldout canonical Pearson for PCA-CCA is **0.632409** (Genre) and **0.815130** (MoodTheme). These CCA results are teacher-representation relationships, **not** musical similarity or externally validated model-quality scores.

Environment in the real output: Python 3.15.0, NumPy **2.5.4**, scikit-learn **1.9.1**; installation also recorded SciPy **1.18.1**, joblib **1.5.2**, threadpoolctl **3.6.0** and transitive narwhals **2.28.0** in the private virtual environment. No global Python installation was replaced.

## Pairwise distance geometry: Bliss-only student vs original Bliss

All correlations are Spearman correlations between pairwise distances and the respective Essentia **teacher distances**, computed on the **300 unordered pairs among the same 25 holdout songs** (shared songs mean 300 **dependent** observations). Higher means better reconstruction of teacher geometry, not better listener-rated musical similarity.

| Teacher head | Original Bliss Euclidean | Train-standardized Bliss Euclidean | Bliss-only Ridge student Euclidean | Student minus original |
| --- | ---: | ---: | ---: | ---: |
| Genre87 | 0.557959 | 0.482853 | **0.569599** | **+0.011640** |
| MoodTheme56 | 0.442049 | 0.406892 | **0.540662** | **+0.098613** |

Permutation negative controls (training teacher permuted): **0.224542** Genre and **0.164484** MoodTheme. Neither is a p-value or a proof of model improvement. The student uses **only original Bliss23 at inference**; Essentia head inference is not needed for this learned teacher-distance proxy.

Genre gain over the original Bliss Euclidean distance is **small** in this run. MoodTheme gain is **larger** and suggests a candidate for *future* verification. Simply standardizing Bliss features did **not** outperform original Bliss for either teacher here. No transformed vector, trained parameter file, general-purpose deployed scorer, calibrated 0–100% score, or personal model was produced.

## Scientific interpretation and non-claims

**Supported:** Authentic Lyrion artist/album/recording information made a connected-group-disjoint development split feasible; Bliss23 carries nonconstant predictive information about Essentia outputs, and a Bliss-only Ridge student tracked the MoodTheme teacher distances better than original Bliss Euclidean distance on this small exploration.

**Not supported:**

- The 25 holdout tracks are artist/album/recording-disjoint **within this run**, but the **same 100 tracks were inspected earlier** in 3,289 correlations and post-selected top-16 robustness checks. Therefore this cannot be treated as a previously untouched *confirmatory* test of research decisions influenced by those earlier analyses.
- Genre and MoodTheme heads are explicitly reported `selected_genre_head_experimentally_validated=false` and `selected_mood_head_experimentally_validated=false`. Their scores are imperfect pseudo-teacher targets, not ground truth or validated listener moods.
- Cross-pipeline identity of decoded audio bytes is not certified. Pretrained teacher-data overlap was not ruled out. Current-live LMS scan and music-root fingerprint freshness were not independently certified.
- No statistical confidence intervals, block/artist bootstrap across genuinely independent groups, preregistered external dataset, corrected multiple-comparison testing or human-perceptual metric-quality evaluation was supplied. Do not interpret paired distance correlations as N=300 independent observations.
- This result does **not** demonstrate that new nearest-neighbor playlists are better, nor authorize integration into BlissMixerLab, worker changes, new compulsory listening tasks or promotion of a WP1 general metric.

## Next reproducible research gates and three-workstream alignment

1. **Freeze a candidate specification, not deploy learned weights:** the MoodTheme56 student architecture with fixed Ridge alpha 10 and train-only preprocessing (plus original Bliss Euclidean and existing Genre/Mood/embedding baselines). The 100-song data may guide *hypothesis formation*, not final model selection or calibration.
2. **New, more varied, independent cohort:** establish group-disjoint identities and freeze the metric evaluation protocol **before inspecting any new results**. Increase independent artist/album/recording groups, balance musical styles, check duplicate recordings and uncertain attributions. Record uncertainty over groups, not over overlapping song pairs.
3. **Independent perceptual assessment:** compare original Bliss, the frozen Bliss-only student, and current WP1 Genre/Mood/1280D/fusion baselines against heldout human judgments or a defensible external music-similarity reference. Report effect sizes, uncertainty and failure modes; keep subjective judgements separate from teacher reconstruction and avoid adaptive reuse of final evaluation.
4. **WP1 General Metric** remains the usable default candidate, **WP2 Personal Metric Learning** remains optional, user-trained and fully fallback-compatible, **WP3** stays a separately evaluated explanatory/student-representation experiment. No production promotion without an independent listening-quality gate.

**Operational safety:** Windows PowerShell 5.1/7 from the existing repository, existing Python 3.15 only, no new audio/ONNX scans, no LMS queue/service changes, source SQLite read-only, outputs in ignored unique private folders only, do not commit the private `aggregate-teacher-research.json` or private SQLites, and leave `main` and PR #16 untouched. Refer to [three-workstream strategy](similarity-three-workstreams-strategy-20261029.md), [source identity adapter](bliss-essentia-lyrion-existing-metadata-source-20261029.md), [full consolidated WP3 record](wp3-consolidated-research-sqlite-20261029.md), and [handover](handover-similarity-three-workstreams-20261029.md).
