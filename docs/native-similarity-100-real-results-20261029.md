# Real Windows native same-100 song comparison: results (29 October 2026)

**Status: REAL LOCAL SCAN + COMPARISON REPORTED PASS; engineering handback complete.**

This document summarizes **only anonymized aggregate values** from the
user-supplied local `aggregate-native-cohort-comparison.json` (schema
`native_similarity_cohort_comparison_v1`). The aggregate was read and
internally checked on 29 October 2026. The private SQLite databases,
100 individual song files and sidecars were **not** transferred to GitHub
or independently inspected here. A reported successful comparison must
not be confused with independent certification of the original Essentia
reference or scientific validation of musical similarity.

The original frozen Windows preflight and manifest are preserved,
including manifest SHA256
`f4d359fa1187f4a2626c14b7abe4a34f5d2143ec014c1b9e7f01545cc53e0b77`.
Do **not** rerun prepare, rerun scan into an existing target, reselect
songs or overwrite original Rust-v5 or listening-research files.

## Report provenance / cohort integrity

| Report field | Observed |
| --- | --- |
| Schema | `native_similarity_cohort_comparison_v1` |
| Report status | `PASS_EXPLORATORY_TOLERANCES` |
| Track identities | 100 |
| All unordered pairs | 4,950 = 100 × 99 / 2 |
| Source audio SHA256 equality | 100 / 100 |
| Exact patch count equality | 100 / 100 |
| Native Voice 2D coverage | 100 / 100 |
| Old SQLite SHA unchanged | true |
| Old DSP identity | `experimental-essentia-audio-v5-f32-src-ratio-unvalidated` |
| Native DSP identity | `experimental-essentia-cpp-dsp-v1-unvalidated` |
| Native SQLite SHA256 | `1c4f947f3d5416cd49479e30236e3cd7a574618314dc003914b796965b07d433` |
| Scanner executable SHA256 | `00a41687fd79c53a536b6de6bf865647ef2d6f9ee453419cc69ca00911f5d82d` |
| Native worker executable SHA256 | `fd6b172f2db84a614c2db5c80b47670f363fbaafa4e2b9db6f02c3fbd262f3da` |

The aggregate also reports matching SHA256 for all seven frozen ONNX
and class-metadata files. Only hashes and aggregates are recorded here,
not file contents or song identities. Redistributing the native Windows
kit **remains BLOCKED** regardless of scan success.

## Technical Rust-v5 versus native Essentia C++ representation

| Measure | Reported value |
| --- | ---: |
| Largest absolute Genre 87D component difference | 0.000005394 |
| Largest absolute Mood/Theme 56D component difference | 0.000007123 |
| Mean absolute Genre component difference | 0.000000120 |
| Mean absolute Mood component difference | 0.000000120 |
| Overall largest classifier component difference | 0.000007123 |
| Minimum per-song old/native 1280D embedding cosine | 1.0 (rounded to nine decimals) |
| Mean per-song old/native embedding cosine | 1.0 (rounded to nine decimals) |
| Largest 1280D embedding component difference | 0.000004510 |
| Exploratory allowed max classification drift | 0.001 |
| Exploratory required min embedding cosine | 0.999 |

The maximum classification component difference is approximately **140×
below** the exploratory tolerance. Embedding cosine rounded to 1.0
is not a bit-for-bit equality claim.

### Stability of the five similarity rankings

Spearman rho is calculated between the Rust-v5 and new native *score
rankings of the same 4,950 pairs*. These correlated pairs share just
100 songs and do not constitute 4,950 independent human judgments.

| Pairwise metric | Old/native Spearman (8 decimals) | Maximum absolute similarity-score drift |
| --- | ---: | ---: |
| Genre cosine | 1.00000000 | 0.00000720 |
| Genre centered cosine | 1.00000000 | 0.00000885 |
| Mood cosine | 1.00000000 | 0.00000625 |
| Mood centered cosine | 1.00000000 | 0.00000885 |
| 1280D embedding cosine | 1.00000000 | 0.00000457 |

Because rho and drift are rounded by the report, this is evidence of
**near-perfect ranking continuity**, not proof that every pairwise
ordering is exactly equal or that every score is identical.

## Previously completed human listening pilot reproduced

The original sealed pilot model scores were reproduced, the original
local human ratings were verified, and the same twelve and
eleven-music-pair sensitivity analyses ran. For every one of the
**40** `(cohort × metric × target)` results, the old and new Spearman
rho are identical **to the reported six decimals**.

Below: for each human rating target, the method with the largest
*descriptive* Spearman rho on both pilot subsets.

| Target | Method | Full 12 rho | Music-only 11 rho |
| --- | --- | ---: | ---: |
| Genre/style | Mood centered cosine | 0.695321 | 0.688558 |
| Mood/energy | Embedding cosine | 0.495224 | 0.410857 |
| Timbre/sound | Embedding cosine | 0.816668 | 0.765707 |
| Next-track suitability | Mood centered cosine | 0.749691 | 0.769463 |

Spoken/non-music pair #10 was excluded **only** in the secondary
11-pair view; the original twelve rows and ratings remain untouched.
The pilot is *model-selected, single-listener, small and exploratory*.
No new listening tests are required. Do **not** select, tune or assess
general or personal fusion weights on those same twelve labels.

Next-track suitability is directed, whereas each similarity metric here
is symmetric. Genre/style, mood/energy and timbre are different targets.
The fact that Mood centered cosine led the *genre/style* pilot score
does **not** establish a task-appropriate genre classifier.

## Engineering conclusion versus general-metric science

1. **Backend continuity gate passed (exploratory tolerances):** the
   native original Essentia C++ backend yields negligibly different
   numbers and practically identical 4,950-pair rankings on this same
   frozen user-library cohort. Stable representation migration can be
   treated as technically qualified for further research, subject to
   broader-platform and independent-reference limitations.
2. **No new scientific musical-quality evidence:** old/native same-song
   comparisons are not labeled perceptual similarity tests. The 12/11
   pilot correlations are *unchanged*, not a new external holdout.
   Voice 2D coverage is established, but its contribution to
   similarity or music/speech gating is **not** validated here.
3. **Resume general, no-training metric research:** retain Genre/Mood/
   Embedding signals and examine target-specific behavior using
   existing MagnaTagATune human odd-one-out results, FMA genre
   retrieval development evidence and DEAM valence/arousal proximity.
   Do not mix incomparable percentages and rank correlations or treat
   artist/recording overlaps as proven absent.
4. **Evaluation before product choices:** predeclare candidate
   comparisons on development data, reserve genuinely independent
   held-out tasks where possible (FMA official TEST has not been used
   as development data), compare to fixed baselines and measure
   coverage, uncertainty and robustness. Previous MTT questions have
   already been explored; they are not fresh independent validation.
   The prior **triplet-local equal-midrank fusion** cannot be used as
   a globally comparable per-pair Lyrion score. Investigate
   unsupervised/global score normalization or calibration only with
   explicit validation boundaries.
5. **Unchanged non-goals:** no new worker/adaptive autotuning,
   no unrequested edits to PR #16, no new mandatory human ratings,
   no personal model training. Personalization/blending remains
   optional and downstream; native kit redistribution remains BLOCKED.

## Next safe handoff

Current authoritative status: **preflight PASS → native scan PASS as
reported by the successful local comparison → same-100 comparison
PASS_EXPLORATORY_TOLERANCES → general-metric selection OPEN**.

No further local Rust-v5-vs-native parity scan is necessary for the
next scientific question. Keep the original private aggregate and
all private inputs locally. This **derived public summary** is the
only repository publication; no JSON report, raw embeddings, source
audio, notes, manifest file or human evaluation CSV was committed.
Continue general-metric research from the existing PR #16 *read-only*,
with any new code first isolated on a separate research branch.
