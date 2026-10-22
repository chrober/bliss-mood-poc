# Exploratory approach-C ablation: fixed equal-weight rank fusion (2026-10-21)

**Final experimental status:** Completed and verified,
[GitHub Actions run 39619708040](https://github.com/chrober/bliss-mood-poc/actions/runs/39619708040)
**PASS**, [aggregate artifact 12354537538](https://github.com/chrober/bliss-mood-poc/actions/runs/39619708040/artifacts/12354537538).
The original method and fusion options were experimental, conceived
after the initial A/B results. No fusion weights were tuned.

## Motivation and precise algorithm

Direct 1280D embedding cosine, 87D Genre cosine and 56D Mood cosine
have differently scaled score distributions. Directly summing raw scores
with equal coefficients would be hard to interpret. For a **strictly
triplet-local** baseline, normalize all three *pair* scores to
within-triplet midranks, avoiding label-fitted calibration.

Given clips `a,b,c`, pair ordering
`((a,b),(a,c),(b,c))`:

1. For every included representation `h`, compute three
   `s_h(i,j) = cosine(v_h(i),v_h(j))` using the
   **same provenance-checked 1,019 MTT clips**.
2. Assign within-question midranks `0` (lowest), `0.5`
   (middle), `1` (highest). Equal scores within
   `1e-12` receive an average rank, rather than
   arbitrary pair priority.
3. For a fixed included-head set `H`, compute
   `R(i,j) = sum(rank_h(i,j) for h in H) / |H|`.
   A *unique* highest pair predicts that the remaining
   clip is the odd one out. Tied highest ranks or
   undefined inputs result in **abstention**, counted
   as wrong against the common 293-majority-question
   denominator.

### Frozen equal-weight variants

| Method ID | Inputs |
| --- | --- |
| `rank_audio_genre_equal` | 1280D embedding + 87D Genre |
| `rank_audio_mood_equal` | 1280D embedding + 56D Mood |
| `rank_genre_mood_equal` | 87D Genre + 56D Mood |
| `rank_audio_genre_mood_equal` | All three |

Every included representation has weight `1/|H|`.
These are **not class-, corpus-, or target-optimized weights**.
[`fixed_rank_fusion.py`](../scripts/fixed_rank_fusion.py)
fixes the method IDs and tie policy.
[`tests/test_fixed_rank_fusion.py`](../tests/test_fixed_rank_fusion.py)
covers normal predictions, positive rescaling invariance,
ties, NaNs, and zero-norm vectors.

**Crucial limitation:** Such ranks are *transductive and triplet-local*.
They do not define a single, globally comparable song-to-song
similarity score for a playlist engine. A production score would
require explicit calibration on disjoint development data.

## Evaluation protocol

[`evaluate_mtt_embedding_ab.py`](../scripts/evaluate_mtt_embedding_ab.py)
has optional, disabled-by-default `--fixed-rank-fusions`,
emitting a separate version-2 report with four fusions
**plus all five unchanged original baselines**.
Across 346 unique human MTT triplets, 293 have a unique
majority outlier and 53 have a human majority tie.
The same 293 denominator applies to all models.
Prediction abstentions (from ties or undefined scores)
earn zero; conditional accuracy on predicted-only rows
must not be substituted for common-denominator accuracy.

Only aggregate reports leave GitHub runners.
Paired query-resampling uses
[`mtt_paired_evidence.py`](../scripts/mtt_paired_evidence.py).
Because original song/artist dependencies cannot be
converted into independent groups, uncertainty estimates
are **sensitivity analyses, not 95% generalization CIs**.

## Empirical results: all four equal-rank ablations

The successful workflow replayed all 1,019 clips and
again passed the synthetic 1280D patch, pooling, SQLite/head,
and threading parity gates.
[Aggregate file: `mtt-audio-genre-mood-fixed-rank-fusion-exploratory.json`](https://github.com/chrober/bliss-mood-poc/actions/runs/39619708040/artifacts/12354537538)
contains paired sensitivity results. The v1 A/B report
remained separate and unchanged.

| Method | Correct | Predicted | Tied abstentions | Coverage | Accuracy on all 293 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Direct 1280D embedding cosine | 182 | 293 | 0 | 100.00% | 62.116% |
| Genre cosine | 191 | 293 | 0 | 100.00% | 65.188% |
| Mood cosine | 192 | 293 | 0 | 100.00% | 65.529% |
| Mood centered cosine | **193** | 293 | 0 | 100.00% | **65.870%** |
| Equal-rank audio+Genre | 163 | 234 | 59 | 79.86% | 55.631% |
| Equal-rank audio+Mood | 170 | 241 | 52 | 82.25% | 58.020% |
| Equal-rank Genre+Mood | 167 | 230 | 63 | 78.50% | 56.997% |
| Equal-rank all three | 192 | 283 | 10 | 96.59% | 65.529% |

The two-representation equal-rank fusions create
52–63 abstentions from equal top-pair rank scores,
undermining common-denominator agreement even when
predicted-only conditional accuracy might look good.
Three-way equal-rank fusion reduces the ties to
10, but obtains only `192/293`, below the
Mood Centered Cosine `193/293`.

Paired difference **three-way minus Mood centered**:
20 questions only three-way got right,
21 only Mood centered got right; difference
**−0.341 percentage points** with an
exploratory naive paired bootstrap 95%-sensitivity
range **−4.437 to +3.754 percentage points**.
This is **not an independent significance test**
because question/artist dependencies, post-hoc
method development and possible training overlaps
remain unresolved.

**Conclusion for exactly these four ablations:**
None improves over Mood Centered Cosine on the
common 293-question denominator. This does
**not disprove feature fusion in general** or a
globally calibrated fusion fitted only on
separate development data. The local midrank
fusion is unsuitable as an immediate per-pair
Lyrion similarity score. Do not tune weights
on already explored MTT questions.

## Further research by target

- **General audible proximity:** test 1280D contributions
  on future human listening references, potentially comparing
  genuinely contrastive pre-trained audio encoders.
- **Genre proximity:** interpret FMA VALIDATION
  cautiously after potential catalogue overlap screening.
- **Mood proximity:** DEAM valence/arousal is a limited proxy;
  human playlist and mood-transition judgments are separate.
- **Playlist transitions:** investigate temporal/directional
  judgments rather than inferring continuity from odd-one-out.

Keep the official FMA TEST untouched and PR #16 as Draft.
Do not merge PR #17, change `main`, or edit the mixer.
