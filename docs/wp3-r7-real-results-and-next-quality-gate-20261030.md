# WP3-R7: real bootstrap and neighbor-retrieval results (30 October 2026)

## Real measurement: 240 frozen new songs, R6 reproduced

The operator ran the R7 read-only analysis on the original native C++ Essentia R6 cohort. The anonymized private aggregate reports 240 source-identity-disjoint songs, 28,680 dependent pairs, seed 20261030, and 300 paired song-group bootstrap replicates. The saved R6 report was reproduced exactly (r6_report_exactly_reproduced = true). No new audio inference, user ratings, fitting on new labels or production changes. The 240-song cohort had already been inspected in R6: R7 is **exploratory post-hoc**, not a second untouched external confirmation, and neither R6 nor R7 measures human musical similarity.

## Global pair-distance agreement

All comparisons use the same 240 songs and Essentia teacher **Euclidean** distances:

| Raw Bliss23 -> frozen candidate, reference | Raw Spearman | Candidate Spearman | Delta | Exploratory 95% song-group bootstrap percentile interval |
| --- | ---: | ---: | ---: | ---: |
| Mood Ridge -> Mood teacher | 0.387956 | 0.439035 | **+0.051079** | [+0.014451, +0.085105] |
| Mood Ridge -> Genre teacher | 0.430849 | 0.478136 | **+0.047287** | [+0.007265, +0.087971] |
| Genre PLS2 -> Genre teacher | 0.430849 | 0.441516 | +0.010666 | [-0.033155, +0.053310] |

The R7 paired bootstrap resamples **songs/groups**, not dependent pair observations, and removes repeated-original-song self pairs. Both Mood Ridge intervals are positive in this exploratory analysis. The Genre PLS interval includes zero. These intervals are not multiplicity-corrected confirmatory tests or evidence of listener preference.

R6 had shown 15.95% Mood Ridge and 12.31% Genre PLS reduction in pseudo-teacher output MAE versus constant training-mean baselines. Vector reconstruction, global pair-rank correlation and local nearest-neighbor retrieval are distinct endpoints.

## Actual teacher-neighbor Top-k overlap

The query is each of 240 songs, searched against the other 239. Entries are mean fraction of shared nearest k neighbors against the respective *Essentia head Euclidean* teacher reference. Results are **not** human relevance ratings.

| Representation | Mood @5 | Mood @10 | Mood @20 | Genre @5 | Genre @10 | Genre @20 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Raw Bliss23 Euclidean | 6.25% | 11.92% | 19.85% | 7.92% | 12.21% | 19.69% |
| Old-fit scaled Bliss23 Euclidean | 7.17% | 11.75% | 19.85% | 7.50% | 11.75% | 19.40% |
| Frozen Mood Ridge Euclidean | **8.58%** | 12.29% | 20.92% | **5.67%** | 11.79% | 20.38% |
| Frozen Genre PLS2 Euclidean | 3.83% | 9.08% | 17.52% | 4.42% | 9.54% | 17.85% |
| Native Mood56 cosine | 63.83% | 69.38% | 75.15% | 28.58% | 35.00% | 44.81% |
| Native Genre87 cosine | 25.67% | 32.42% | 42.19% | 76.42% | 80.83% | 83.54% |
| Native EffNet1280 cosine | 26.75% | 32.92% | 41.15% | 32.42% | 39.75% | 48.13% |

Old-training-mean-centered Mood cosine scores 65.17%, 67.33%, 70.19% at Mood @5/10/20; 23.58%, 30.75%, 40.31% at Genre @5/10/20.

**Critical tension:** On 240 queries times 5 neighbors = 1,200 returned neighbor slots, Mood Ridge improves Mood teacher overlap from **75 to 103** (+28 matches, +2.33 percentage points), but *reduces* Genre teacher Top-5 from **95 to 68** (-27 matches, -2.25 percentage points). For Mood @10/@20 its gains are only +0.38/+1.06 percentage points. For Genre @10/@20 it gives -0.42/+0.69 points. The frozen Genre PLS decreases teacher Top-k overlap against raw Bliss for all six listed retrieval endpoints, even though its MAE improves and global Genre Spearman delta is marginally positive.

For scale only, unrelated random Top-k rankings among 239 candidates yield expected overlap fractions k/239 = 2.09%, 4.18%, 8.37% for k=5/10/20. The high agreement of native Mood cosine against Mood Euclidean and native Genre cosine against Genre Euclidean reflects **shared head outputs**, not independent evidence of better musical quality. R7 does **not** calculate Top-k uncertainty intervals, so no claims of robust retrieval gain/loss can be made from these descriptive differences alone.

## Scientific conclusion and priorities

**Supported:** Old-100-trained Mood Ridge has a generalizable relationship to global Essentia teacher distances; its modest Mood Top-5 improvement is real as a descriptive count for this same inspected corpus. **Not supported:** broad genre/mood nearest-neighbor superiority, human musical-quality improvement, WP1 General Metric victory, a chosen WP2 personal model, or promotion of the Ridge/PLS student to production.

Prioritize **independent, task-appropriate WP1 external/human similarity validation** with the already available MTT majority-vote triplets, FMA genre retrieval and DEAM valence/arousal evidence **as separate tasks**, preserving the untouched official FMA TEST. Include the frozen Bliss-only student only where comparable features/provenance exist, next to raw Bliss and direct Mood/Genre/1280D/fusion baselines. WP2 Personal Metric Learning and 0–100% General/Personal blending remain a separate planned capability with 100%-General fallback; no extra compulsory listening and no work on production Lyrion/BlissMixerLab/PR #16/main.

Optionally, an exploratory future R8 diagnostic could quantify paired per-query Top-k deltas and source-group-aware retrieval uncertainty, distinguish global ranking from top-neighbor failures, and inspect teacher-reference self-head circularity. It must **not** be described as another independent confirmation or justify tuning on the reused R6 cohort.

Do not upload/commit the private R7 aggregate, source databases, music, embeddings, model weights or any song identities. Methodology and Windows runner remain in [R7 protocol](wp3-r7-post-r6-robustness-and-retrieval-20261030.md).