# WP1-E5: measured CCMSim clip-disjoint holdout feasibility and rights gate (30 October 2026)

## Real, pinned source execution — NOT a General Metric evaluation

**PASS:** [GitHub Actions 41070926652](https://github.com/chrober/bliss-mood-poc/actions/runs/41070926652) completed the real CCMSim public-source **metadata-only** feasibility analysis, with synthetic leakage/privacy checks passing on **Linux and Windows**. [Published aggregate-only counts artifact](https://github.com/chrober/bliss-mood-poc/actions/runs/41070926652/artifacts/12984293292) contains neither song IDs nor human similarity values, individual annotations, raw audio paths or calculated model scores.

Frozen [E5 splitter](../scripts/audit_wp1_e5_ccmsim_clip_splits.py), [synthetic regression tests](../tests/test_audit_wp1_e5_ccmsim_clip_splits.py), [real CI](../.github/workflows/research-wp1-e5-ccmsim-splits.yml). The source validation reuses the earlier [WP1-E4 pinned public human annotation audit](wp1-e4-ccmsim-human-reference-preflight-20261030.md): exact upstream `pxaris/CCMSim` Git commit `eff8ab428dd12f1973548d657928b5211dd290bb`; original Git blob fingerprints `0921898a7920858db0472ed11bc222578f80d834` for clip source mapping and `dd1f026ca72cc1616a7a7cdebd333d869d6c6720` for 1,130 aggregated human-rated pairs.

**Important:** The partitioning code consults **only the source clip IDs, their nine source-dataset identifiers, and the 1,130 unordered pair endpoints/number of annotators**. Human similarity scores in three objectives are verified for source-format integrity by E4 but **not used** to assign clips, select a seed, optimize weights, choose methods or rank proposed splits. No participant responses, raw votes, downloaded audio, private songs, model features or FMA official TEST files are used. The code exports only per-source/per-fold counts. All deliberately frozen seeds are evaluated; none is retrospectively picked based on measured music similarity.

## Two predetermined policies and five seed sensitivity checks

From the *463 original clips that actually participate in the 1,130 human-annotated pairs*, rank the clip IDs deterministically **within each of nine source datasets** by a SHA-256 seeded shuffle. Keep whole clip IDs within one partition, and exclude every pair whose two endpoint clips belong to different partitions. Five seeds are frozen to the original CCMSim analysis code's published set **3, 4, 7, 13, 21**; their results are descriptive split-sensitivity checks, not a search for a winner. Assignments contain no overlap in **known clip IDs**, but actual artist/album/recording identity relationships between different clips cannot yet be certified. The resulting heldout pairs also share clips **within** a partition, so the number of independent statistical units is below the raw number of pairs.

The first policy allocates approximately **60% training, 20% validation, 20% test** within each source. The second policy creates **five balanced, clip-disjoint folds** within each source. Neither is claimed to be a ready-to-use independent human metric holdout.

### Actual 60/20/20 coverage (pairs retained only when both clips remain in one partition)

| Fixed seed | Train clips | Validation clips | Test clips | Train pairs | Validation pairs | Test pairs | Crossing pairs excluded | Total pairs retained |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **3 (predeclared primary)** | 279 | 94 | 90 | **394** | **47** | **40** | **649** | **481 / 1,130** |
| 4 | 279 | 94 | 90 | 417 | 37 | 39 | 637 | 493 / 1,130 |
| 7 | 279 | 94 | 90 | 415 | 33 | 38 | 644 | 486 / 1,130 |
| 13 | 279 | 94 | 90 | 397 | 50 | 47 | 636 | 494 / 1,130 |
| 21 | 279 | 94 | 90 | 405 | 63 | 48 | 614 | 516 / 1,130 |

In the **primary test**, 35 of 40 pairs cross different source datasets; only **5 pairs** involve both clips from the *same* source dataset. For the five frozen seeds, only **38–48 test pairs** are retained, and the validation cohort varies from **33 to 63** pairs. The predeclared conservative practical threshold of **at least 100 test questions** is **not met** by the primary policy. This 100-question marker is a preliminary engineering feasibility floor, NOT a formal statistical power analysis.

### Actual five clip-disjoint folds

| Seed | Per-fold retained pair counts | Total retained / 1,130 | Crossing pairs excluded |
| --- | --- | ---: | ---: |
| 3 | 52 / 31 / 45 / 44 / 40 | 212 (18.76%) | 918 |
| 4 | 68 / 41 / 44 / 33 / 39 | 225 (19.91%) | 905 |
| 7 | 47 / 57 / 37 / 31 / 38 | 210 (18.58%) | 920 |
| 13 | 49 / 46 / 35 / 46 / 47 | 223 (19.73%) | 907 |
| 21 | 48 / 54 / 37 / 57 / 48 | 244 (21.59%) | 886 |

Each fold may cover **31–68** actual pair judgments, depending on seed and fold. Counting all retained fold-internal pairs together gives only **18.58–21.59%** of the original observations. Pooling folds for descriptive cross-validation does **not** convert this into independent performance of a trained system; no training, model fitting, pooled predictions or significance tests have been performed.

## Why this affects the WP1 roadmap

1. CCMSim gives a **direct human-labeled overall similarity endpoint**, across nine cultures, that MTT's limited triplet experiment and FMA's genre labels do not fully replace. This is valuable even if only as an exploratory **zero-shot, already-fixed scorer** challenge. A strictly **untrained**, predeclared General Metric can be evaluated descriptively on all accessible pairs without a train/test split if its score specification is frozen *before accessing the labels*, but a comparison on previously inspected human labels is not magically an untouched final holdout.
2. The **classic label-fitted train/validation/test design** is a poor fit: more than half of the pair edges must be discarded (primary policy), leaving **40** test questions dominated by **35** cross-source comparisons, and strong within-split shared-clip dependence. The five-fold design is even sparser. Worse, neither ensures independent source artists or recording families. **Do not attempt to train/reweight/blend to these public labels and advertise the results as a reliable independent General Metric.**
3. The original upstream source README describes 52 clips x nine sources (=468), while the actual **pinned mapping contains 54 clips x nine sources (=486)**; **463** appear in rated pairs. The discrepancy remains unresolved and must be carried into any subsequent source/segment/rights gate rather than silently fixing the files.
4. **Audio source access is still a separate blocker.** The original CCMSim authors distribute only their CC BY 4.0 human annotations, not licensed audio. FMA-*medium* may be openly documented but **the FMA code repository license is not a blanket sound-recording license**. The MTT original source previously failed at the eighth of 30 live sparse member requests; other CCMSim cultural corpora have restricted/request or registration-based access, and Lyra uses YouTube IDs. No source rights, 20-second audio segment parity, Essentia pretraining overlap, artist disjointness or original recording fingerprints have been verified for this study.
5. **Independent evidence must be earned, not simulated.** The user-reported 11-music-pair listening pilot remains a single-listener model-selected diagnostic, WP2 Personal Metric Learning and calibration are synthetic contracts, and WP3 R6/R7 regressions approximate teacher outputs rather than human musical preference. Existing MTT 193/293 human triplet accuracy is descriptive; the four globally comparable equal-weight fusion metrics remain unmeasured on MTT real audio. FMA official TEST remains unopened.

## Decision and recommended next gate

**WP1-E5 decision: SPLIT QUALITY GATE NOT SATISFIED for training/validating/tuning a new General Metric on this 1,130-pair source.** This is a real measured feasibility outcome, not a claim that the CCMSim human annotations are low quality or unusable for other tasks. Keep CCMSim as a potential **external, frozen zero-shot challenge**, with per-source and cross-source reporting and clustered/shared-song caution.

Before any CCMSim acoustic comparison, perform a **strict per-source legal/access and source-identity/segment parity check**, starting with the minimum existing legitimately accessible same-recording recordings (without crossing to unverified mirrors). Determine whether at least one predeclared music source can supply a useful, attributable, lawful cohort and enough human pair coverage. Do not run source audio downloads or raw clip collection as part of the E5 metadata workflow. If legal access, clip identity, source grouping or coverage is inadequate, stop this CCMSim evaluation. No new user listening, private user features, new distributed artifacts containing audio/track IDs, original source DB mutations, PR #16/main or production mixer changes.
