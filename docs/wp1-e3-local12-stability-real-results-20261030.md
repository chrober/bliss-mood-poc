# WP1-E3: observed 12/11 human-pilot robustness and single-pair sensitivity (30 October 2026)

## Provenance — real operator-reported aggregate, NOT public independent validation

This **read-only result** is transcribed from the user's successful local run of the previously committed [aggregate-only stability summarizer](../scripts/summarize_wp1_e3_pilot_stability.py) against the existing original `aggregate-model-comparison.json`, in the private ignored directory from [the first 12-pair evaluation](wp1-e3-local12-real-human-pilot-results-20261030.md). It uses original human ratings only through their previously computed aggregate; **the assistant did not inspect the underlying private files**, per-pair score table, original ratings, song identities, metadata, audio or model vectors. The user-reported report has schema `wp1-e3-local12-aggregate-stability-only-v1` and status `EXPLORATORY_SENSITIVITY_NO_INDEPENDENT_VALIDATION`.

Exactly **12 original human-rated pairs** include the explicitly declared **nonmusic spoken interview, pair 10**. The primary music-only view excludes that pair, leaving **11 musical pairs** rated by **one listener**, deliberately chosen using the five compared model families. Leave-one-out (LOO) removes one further *musical* pair from the 11, computing eleven separate Spearman correlations on **10 music pairs each**. LOO ranges are descriptive *sensitivity extrema*, **not statistical confidence intervals**. None of the comparisons below demonstrates population generalizability, independent validation, statistical significance, or universal metric superiority.

## Complete, observed 20-cell stability report

Spearman rank correlations from exactly the 20 model × human-dimension combinations. `rho12`: all 12 including nonmusic; `rho11`: music only; delta = `rho11 - rho12`; LOO min/max over the 11 possible 10-music-pair subsets.

| Frozen pairwise scorer | Human objective | ρ12 including nonmusic | ρ11 music-only | Δ excluding pair 10 | Music-11 LOO ρ min–max |
| --- | --- | ---: | ---: | ---: | ---: |
| Genre Cosine | Genre/Style | 0.459981 | 0.423370 | -0.036611 | 0.225110–0.617065 |
| Genre Cosine | Mood/Energy | 0.007391 | -0.088041 | -0.095432 | -0.203240–0.120605 |
| Genre Cosine | Timbre | 0.492345 | 0.501670 | 0.009325 | 0.299644–0.582616 |
| Genre Cosine | Next-Track-Suitability | 0.473106 | 0.434914 | -0.038192 | 0.233550–0.667424 |
| Genre Centered Cosine | Genre/Style | 0.549125 | 0.497809 | -0.051316 | 0.325159–0.710560 |
| Genre Centered Cosine | Mood/Energy | 0.000000 | -0.132061 | -0.132061 | -0.255690–0.060302 |
| Genre Centered Cosine | Timbre | 0.476715 | 0.454144 | -0.022571 | 0.232224–0.527781 |
| Genre Centered Cosine | Next-Track-Suitability | 0.524056 | 0.473148 | -0.050908 | 0.285450–0.711919 |
| Mood Cosine | Genre/Style | 0.620440 | 0.590857 | -0.029583 | 0.450220–0.741725 |
| Mood Cosine | Mood/Energy | 0.221742 | 0.161408 | -0.060334 | 0.058186–0.316789 |
| Mood Cosine | Timbre | 0.336045 | 0.264037 | -0.072008 | -0.037456–0.514510 |
| Mood Cosine | Next-Track-Suitability | 0.676905 | 0.673878 | -0.003027 | 0.557924–0.788196 |
| Mood Centered Cosine | Genre/Style | 0.695321 | 0.688558 | -0.006763 | 0.581534–0.772890 |
| Mood Centered Cosine | Mood/Energy | 0.266091 | 0.220102 | -0.045989 | 0.073703–0.386812 |
| Mood Centered Cosine | Timbre | 0.398565 | 0.348529 | -0.050036 | 0.082402–0.633817 |
| Mood Centered Cosine | Next-Track-Suitability | 0.749691 | 0.769463 | 0.019772 | 0.687674–0.877186 |
| Embedding1280 Cosine | Genre/Style | 0.588348 | 0.465242 | -0.123106 | 0.281387–0.710560 |
| Embedding1280 Cosine | Mood/Energy | 0.495224 | 0.410857 | -0.084367 | 0.194307–0.601253 |
| Embedding1280 Cosine | Timbre | 0.816668 | 0.765707 | -0.050961 | 0.674200–0.829370 |
| Embedding1280 Cosine | Next-Track-Suitability | 0.633234 | 0.520941 | -0.112293 | 0.350325–0.699206 |

### What survives removing any ONE further musical pair?

The mathematical sufficient condition `min_LOO_ρ(A) > max_LOO_ρ(B)` means A beats B on **every one** of the same 11 ten-pair leave-one-out subsets, even though the actual per-subset vectors were not supplied. Conversely, *overlapping ranges cannot prove either advantage or disadvantage*, because the extrema might come from different deleted pairs.

- **Timbre:** Embedding1280 Cosine LOO minimum **0.674200** exceeds the LOO maximum of **every** other scorer; the largest rival maximum is Mood Centered Cosine **0.633817**, yielding a strictly positive worst-case gap of **0.040383**. This is the **clearest within-pilot deletion-robust relative lead**. Still not an independently validated music-quality lift.
- **Directed Next-Track-Suitability:** Mood Centered Cosine is strongly positive throughout **0.687674–0.877186**, and its minimum exceeds Genre Cosine's maximum **0.667424** by **0.020250**. It does **not** have a proven all-deletions advantage over Mood Cosine (maximum 0.788196), Genre Centered (0.711919), or Embedding1280 (0.699206) from these interval summaries alone. A symmetric pair metric cannot encode the *direction* of a playlist transition.
- **Genre/Style:** Mood Centered Cosine's music-only ρ is **0.688558**, its LOO range **0.581534–0.772890** remains positive, and removing nonmusic pair 10 shifts the estimate by just **−0.006763**. Its LOO interval overlaps other methods' intervals; no strict all-deletions *method* win is proven.
- **Mood/Energy:** Embedding1280 Cosine music-only ρ is **0.410857**, LOO **0.194307–0.601253**. This minimum dominates both Genre Cosine (maximum 0.120605) and Genre Centered Cosine (maximum 0.060302), but not either Mood-score family. The leading observed Mood/Energy correlation remains **moderate and sensitive** to one deleted pair; no general Mood detection conclusion follows.
- Two Genre scorer Mood/Energy intervals change sign; Mood Cosine Timbre also crosses zero. Those are especially weak/descriptively unstable within this pilot. Sign stability of the remaining correlations does not imply significance.

### Nonmusic-pair sensitivity on the four descriptively leading combinations

| Frozen scorer / human objective | Full 12 ρ | Musical 11 ρ | Change when excluding pair 10 |
| --- | ---: | ---: | ---: |
| Mood Centered / Genre/Style | 0.695321 | 0.688558 | −0.006763 |
| Mood Centered / directed Next-Track | 0.749691 | 0.769463 | +0.019772 |
| Embedding1280 / Timbre | 0.816668 | 0.765707 | −0.050961 |
| Embedding1280 / Mood/Energy | 0.495224 | 0.410857 | −0.084367 |

Excluding the nonmusic question changes the strength of the descriptive associations but does not reverse their sign or remove the Timbre deletion-robust lead. The full-12 sample is **not** an acceptable music-only accuracy sample: pair 10 must remain preserved in original ratings and in the declared sensitivity comparison, not silently dropped from the historical record.

## Scientific decision and constraints

1. **Retain both Mood Centered Cosine and Embedding1280 Cosine as separate General Metric research candidates**. The strongest *within-pilot* evidence supports a task-conditional acoustic/timbre contribution from Embedding1280 and a descriptive relation between Mood Centered and Genre/Style or playlist continuation; no universal mixing weights are fitted or approved.
2. Do not average or select across the four fundamentally different rating objectives (Genre/Style, Mood/Energy, Timbre, *directed* Next-Track). No objective was independently held out for model selection; the 11-pair study was deliberately model-selected and has one rater. Correlation ranks neither quantify playlist satisfaction nor guarantee real-world metric performance.
3. This operator's 20-cell LOO report has only the **min and max** for each scorer/objective; no per-deletion paired vectors are in the submitted aggregate, so overlapping extrema must **not** be interpreted as a paired model-win analysis or significance test. The robust dominance for Timbre follows only because separated ranges mathematically guarantee the ordering.
4. Public [WP1-E1/E3 MTT/FMA/DEAM evidence](wp1-e3-sharp-mtt-paired-bounds-and-existing-pilot-20261030.md) remains task-separated. Mood Centered was a descriptive 193/293 MTT triplet leader, but original per-question joint correctness is unavailable. [WP1-E2 source](wp1-e2-mtt-source-and-cache-diagnostics-20261030.md) still failed after 7 of 30 CRC-verified clip requests; the four **global** Genre/Mood/Embedding fusion benchmark results have NOT been measured. **FMA official TEST stays unopened.**
5. WP2-P3/P4 synthetic personal-learning/calibration contracts and WP3-R6/R7 Essentia-teacher approximation do not demonstrate higher human musical-similarity quality. No new listening, model training, audio scan, private file publishing, PR #16/main or production-mixer modifications follow from this report.

**Recommended next quality gate:** prioritize an independently sampled, legal, truly group-distinct human similarity/playlist reference with predeclared endpoint and untouched final test, only when it becomes available and without requiring the current operator to rate more music. In the meantime compare existing task-level evidence *qualitatively* and preserve the simplest complete General candidate as a baseline, without declaring a winner.
