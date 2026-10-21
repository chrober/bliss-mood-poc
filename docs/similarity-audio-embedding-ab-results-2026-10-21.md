# Paired research A/B: direct 1280D embeddings versus Genre/Mood heads on MagnaTagATune

**Date:** October 21, 2026 · **Branch:** `feat/similarity-metric-evaluation` ·
**PR:** [#16 (Draft)](https://github.com/chrober/bliss-mood-poc/pull/16).

## Research question and status

On **exactly the same audio recordings and human odd-one-out votes**,
which representation yields more human-compatible pair rankings:
direct raw Discogs-EffNet Song embeddings (B), 87D Genre/56D Mood
classifier head scores (A), or a separately studied later fusion (C)?

**First full paired A/B PASSED.** This is exploratory associative
evidence, not an independent test, not a playlist-transition
assessment, and not a production recommendation.

- [Successful complete run 39617159250](https://github.com/chrober/bliss-mood-poc/actions/runs/39617159250),
  [aggregate-only artifact 12354255450](https://github.com/chrober/bliss-mood-poc/actions/runs/39617159250/artifacts/12354255450).
  Used the same cached 1,019 MTT clips, four isolated
  `bliss-mood` processes and one ONNX thread per process.
- Direct embeddings are extracted from **the exact encoder patch pass**
  that feeds Genre and Mood; no second decoder or preprocessing
  implementation was introduced. Raw 1280D patches are accumulated
  in f64, arithmetic-mean-pooled, then the song vector is
  L2-normalized and stored privately in a versioned JSON sidecar.
  Classification scores remain in unchanged SQLite schema v3.
- The original Rust-v5 checkout is pinned at
  `2c3d44401436b3b41b6e067199016a1ed2335fbf`.
  A temporary research overlay adds raw embedding export on
  the Actions runner. Neither PR #17 nor its pinned binary
  cache is changed.

## Exactly the same denominator: 346 questions, 293 decidable, 1,019 clips

MTT contains **346 unique unordered human triple questions**
referring to **1,019 unique clips**. **53** questions have
a human majority-vote tie. The other **293** have a unique
majority-chosen outlier. All representations predict from
those exact same 293 questions; the pair with the highest
song-similarity score determines the predicted odd one out.
Abstentions count as wrong on a common denominator.
All five head/embedding methods achieved **293/293 coverage**.
The naive random odd-one-out baseline is 33.33%.

| Representation / score | Correct / 293 | Common-denominator agreement |
| --- | ---: | ---: |
| B: 1280D embedding mean+L2 Cosine | 182 | 62.116% |
| A: Genre 87D Cosine | 191 | 65.188% |
| A: Mood/Theme 56D Cosine | 192 | 65.529% |
| A: Genre 87D Centered Cosine | 191 | 65.188% |
| A: Mood/Theme 56D Centered Cosine | **193** | **65.870%** |

In this frozen human-triplet task, raw EffNet Cosine
performed below all four classification baselines.
A higher-dimensional embedding does **not** guarantee
better pairwise perceptual ranking. One hypothesis
is that the original encoder was not contrastively
optimized for this human odd-one-out target; this
experiment **does not prove that explanation**.

## Paired method differences and dependency-sensitive uncertainty

`B_only_correct` and `A_only_correct` count questions
where exactly one representation matches the human majority.
The 95% naive query-resampling quantiles are not valid
independent-population confidence intervals: songs and
artists recur across questions. The MTT artist co-occurrence
graph forms a connected component, preventing a simple
independent artist-cluster bootstrap. Artist reweighting
ranges are **sensitivity diagnostics**, not significance
tests, even when entirely negative.

| B minus A | B-only / A-only correct | Delta (pp) | Naive paired 95% query sensitivity (pp) | Artist-weight 95% sensitivity (pp) |
| --- | ---: | ---: | ---: | ---: |
| Embedding − Genre Cosine | 30 / 39 | −3.072 | −8.532 to +2.048 | −6.235 to −0.095 |
| Embedding − Mood Cosine | 27 / 37 | −3.413 | −9.215 to +2.048 | −6.341 to −0.268 |
| Embedding − Genre Centered | 26 / 35 | −3.072 | −8.191 to +2.048 | −6.122 to −0.216 |
| Embedding − Mood Centered | 27 / 38 | −3.754 | −9.215 to +1.365 | −6.773 to −0.969 |

**Do not interpret negative artist-weight quantiles as formal significance**.
All naive paired-query ranges allow zero and positive differences.

## Reproducible implementation and measured costs

Key files:
[`research-mtt-embedding-ab.yml`](../.github/workflows/research-mtt-embedding-ab.yml),
[`evaluate_mtt_embedding_ab.py`](../scripts/evaluate_mtt_embedding_ab.py),
[`mtt_parallel_workers.py`](../scripts/mtt_parallel_workers.py),
[`research/song_embedding.rs`](../research/song_embedding.rs).

The selected-clip ZIP held **119,689,247 bytes** and
was restored from a CRC-verified Actions cache without
re-downloading the full 2.77-GiB source archives.
All 1,019 clip CRC checks passed in about **0.52 s**.
Four separate processes, one ONNX thread each, analyzed
all clips in about **143 s**. The paired scorer took
**1.07 s**, with peak RSS **108,160 KiB**; the
locked research Rust release-build stage took **68.94 s**
plus unit-test compilation. Rust pooling unit tests:
**3 PASS**. Linux and Windows Python regression tests:
[run 39616940299](https://github.com/chrober/bliss-mood-poc/actions/runs/39616940299),
both jobs PASS. No recordings, clip identities,
individual votes or vectors are published.

### Independently repeated numeric and regression gates

The earlier standalone
[run 39616222834](https://github.com/chrober/bliss-mood-poc/actions/runs/39616222834)
was blocked by an upstream model download timeout,
**not** a demonstrated numeric parity failure.
A newer synthetic raw-patch/pooled-song and
head/SQLite/thread parity gate was added to the
complete MTT workflow.

[Run 39618323154](https://github.com/chrober/bliss-mood-poc/actions/runs/39618323154)
**PASS** for the new synthetic numeric checks
and the full 1,019-clip, 346-triplet A/B replay
with identical scores:

| Verification gate | Measured result |
| --- | --- |
| Synthetic WAV length | 6 seconds |
| Encoder patch count | 4 |
| Direct song embedding dimensions | 1280 |
| Maximum independent patch-pooling discrepancy | 1.0855063 × 10⁻⁸ |
| Difference between song L2 norm and one | 4.1199244 × 10⁻¹⁰ |
| Maximum difference with one vs two ONNX threads | **0.0** |
| Genre/Mood values with versus without embedding export | **bitwise equal** |
| SQLite v3 rows with versus without export | **identical** |
| Full 1,019-clip same-question MTT A/B | **PASS, unchanged** |

These checks establish ONNX-internal pooling and classification
regression parity **for this synthetic case**; they do **not**
establish broad many-song original TensorFlow/Essentia C++
embedding parity on diverse real music.

### Complete exploratory approach A/B/C with fixed rank fusion

Four *untrained* equal-midrank, triplet-local fusions
were evaluated on the same 1,019 clips and the same
293 human-decidable questions, with synthetic parity
checks repeated:
[Run 39619708040](https://github.com/chrober/bliss-mood-poc/actions/runs/39619708040)
**PASS**, [aggregate artifact 12354537538](https://github.com/chrober/bliss-mood-poc/actions/runs/39619708040/artifacts/12354537538).

| Equal-rank method | Correct / 293 | Prediction coverage |
| --- | ---: | ---: |
| Audio + Genre | 163 = 55.63% | 234/293 |
| Audio + Mood | 170 = 58.02% | 241/293 |
| Genre + Mood | 167 = 57.00% | 230/293 |
| Audio + Genre + Mood | 192 = 65.53% | 283/293 |
| Mood Centered Cosine (unfused baseline) | **193 = 65.87%** | 293/293 |

None of these **exact fixed local rank fusions** improved
upon Mood Centered Cosine on the common denominator.
Many tied best-pair scores cause two-input fusion
abstentions. This does not refute globally calibrated
fusion, but the existing sample has been explored and
cannot fairly fit new weights and then claim holdout
performance. Detailed protocol:
[fixed-rank fusion research](similarity-fixed-rank-fusion-research-2026-10-21.md).

## Next evidence and guardrails

- Reproduce A vs B on FMA's **previously screened VALIDATION**
  sample and DEAM's filtered 240-song development sample,
  using identical audio and model hashes; [FMA A/B has now
  been completed](similarity-fma-embedding-ab-2026-10-21.md).
  The DEAM A/B comparison remains source-blocked.
- Consider independently pre-trained *contrastive*
  audio embeddings with their own frozen provenance
  as a distinct representation family, not proof
  of performance from the current encoder.
- Do **not** optimize fusion coefficients against the
  fully explored MTT questions.
- Evaluate Genre, Mood, general auditory proximity
  and **actual playlist transitions** as distinct
  questions; representation A/B/C and mixing strategy
  Bliss-first/feature-first/hybrid are different
  levels of the eventual product.
- Keep PR #16 Draft, leave FMA official TEST untouched,
  and do not modify PR #13/17, `main`, or the mixer.
