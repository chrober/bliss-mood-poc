# FMA-Small VALIDATION: paired 80-song 1280D embedding versus Genre/Mood

**Date:** October 21, 2026 · **Status:** Complete exploratory paired study ·
**Scope:** Draft PR #16, `feat/similarity-metric-evaluation` only.
No change to `main`, PR #13/#17, or the production Lyrion mixer.

## Scientific question and strictly frozen cohort

Does direct Discogs-EffNet song-embedding cosine (approach B) outperform
the Genre/Mood head vectors (approach A) when retrieving recordings with
the **same coarse FMA top-level Genre**? This is a Genre-label proxy,
**not** human judged perceptual similarity or good playlist transitions.

The sample is exactly the previously studied, conservative
catalogue-screened FMA-Small **official VALIDATION** cohort from
[run 39606850307](https://github.com/chrober/bliss-mood-poc/actions/runs/39606850307):
**80 songs**, ten per eight Genres, **80 different artist IDs**.
A potential MTG-Jamendo artist/title overlap screen excluded **42
of 800** VALIDATION titles; 758 remained eligible. Seed `20261021`
and the original `balanced_sample` selector were not changed.
FMA's official **TEST was not inspected**.

| Frozen source or sample | SHA256 |
| --- | --- |
| Ordered cohort IDs | `f4a7a81c0713db7619efdba6eb3d561aa70d6d3cc812b4884793953d93b58509` |
| FMA metadata ZIP | `d9527a5297a65da31c5676484d5047c3e2b8a8060ce72a46e26158be736bf265` |
| Original FMA-Small audio ZIP | `f923bbef327820456d50965c3c320c3c7b6dab8456449429fd78f7ec96a5d02c` |
| MTG catalogue TSV | `bb1efa2876536cbe1a8b67db5dda15249ca144f0cff69e481b638803cbdc9aca` |
| Original Discogs encoder ONNX | `a280825b334797cf677939db8cd5762c0392aedd0ca6415dbc1cd083f045e43c` |
| Representation/pooling fingerprint | `48d6726d346b49aaf9f6d0377778ce0bf46be52285293e2f357ad26832cbc759` |

A catalogue nonmatch is **not a proof of model training disjointness**,
nor does it establish recording-level independence.

## Research implementation and measurement contract

[`benchmark_fma_genre.py`](../scripts/benchmark_fma_genre.py)
adds an optional `--embedding-dir`. The original genre-only
execution path remains available. When enabled, **the same
encoder patch pass** produces 87D Genre, 56D Mood/Theme and
raw 1280D embedding features. The song embedding is
f64-mean-pooled across patches, songwise L2-normalized, and
stored in a separate, private, versioned JSON sidecar.
The existing schema-v3 SQLite head storage is not changed.

[`evaluate_fma_embedding_ab.py`](../scripts/evaluate_fma_embedding_ab.py)
enforces sample, audio, patch count, model SHA and pooling
fingerprints. The pinned original Rust-v5 checkout
`2c3d44401436b3b41b6e067199016a1ed2335fbf`
receives its research-only overlay through
[`apply_rust_v5_embedding_export.py`](../scripts/apply_rust_v5_embedding_export.py)
on the ephemeral GitHub Actions runner. PR #17 is not modified.

For each of the 80 anchor queries, the **same other 79 songs**
form its candidate pool: nine relevant tracks with the same
top-level Genre and 70 different-Genre candidates.
The random P@5 reference is `9/79 ≈ 11.39%`.
Methods: direct Embedding Cosine; Genre Cosine and Centered
Cosine; Mood/Theme Cosine and Centered Cosine as **cross-task
control**, not a Mood ground-truth evaluation.

Report P@5, mAP@10, nDCG@10, coverage, and undefined scores
for **the common query/candidate denominator**.
Rank ties use score descending then a stable opaque song ID.
An incomplete query counts as an abstention with zero
on all three measures, not a shortened denominator.
Embedding-minus-head deltas use 800 shared, Genre-stratified
query resamples. Those 95% quantiles are **descriptive
dependence sensitivities, not independent population CIs**,
because all queries share candidate songs.

Synthetic regression tests:
[`tests/test_evaluate_fma_embedding_ab.py`](../tests/test_evaluate_fma_embedding_ab.py),
including read-only SQLite, sample, no-TEST, and exact head
baseline checks; Linux and Windows CI passed.

## Confirmed full paired A/B run

**PASS:** [GitHub Actions 39625087310](https://github.com/chrober/bliss-mood-poc/actions/runs/39625087310),
[aggregate-only artifact 12355954718](https://github.com/chrober/bliss-mood-poc/actions/runs/39625087310/artifacts/12355954718).
**All five methods evaluated 80/80 queries**, using the same
79 candidates per anchor. Previously frozen Genre Cosine values
were reproduced exactly: P@5 `0.32000000`, mAP@10
`0.17487599206349208`, nDCG@10
`0.29853323224865014`.

| Method | P@5 | mAP@10 | nDCG@10 | Query coverage |
| --- | ---: | ---: | ---: | ---: |
| B: 1280D encoder mean+L2 Cosine | 0.2800 | 0.163044 | 0.282363 | 80/80 |
| A: 87D Genre Cosine | 0.3200 | 0.174876 | 0.298533 | 80/80 |
| A: 87D Genre Centered Cosine | **0.3225** | **0.178147** | **0.304271** | 80/80 |
| Control: 56D Mood Cosine | 0.2775 | 0.150394 | 0.266065 | 80/80 |
| Control: 56D Mood Centered Cosine | 0.2675 | 0.152847 | 0.270372 | 80/80 |

### Descriptive paired differences

Deltas are **embedding minus baseline**; 95% bands below are
Genre-stratified shared-query sensitivity quantiles,
**not population confidence intervals**.

| Baseline | P@5 delta (pp) | 95% sensitivity range (pp) | mAP@10 delta (pp) | nDCG@10 delta (pp) |
| --- | ---: | ---: | ---: | ---: |
| Genre Cosine | −4.00 | −8.75 to +0.75 | −1.183 | −1.617 |
| Genre Centered Cosine | −4.25 | −8.76 to +0.25 | −1.510 | −2.191 |
| Mood Cosine | +0.25 | −3.50 to +4.01 | +1.265 | +1.630 |
| Mood Centered Cosine | +1.25 | −2.50 to +5.00 | +1.020 | +1.199 |

The observed 4.00–4.25-pp deficit versus Genre heads
applies to this **already explored Genre-retrieval proxy**,
not to arbitrary music similarity. The exploratory bands
include zero. Neither mood head here has an independent
Mood reference; the DEAM VA study addresses a different proxy.

### Reproducibility and resource measurements

In the successful cold run, downloading the original
FMA-Small 7.2-GiB ZIP took **243.87 s**, Rust-v5
release compilation **51.48 s** (excluding preceding test
compilation), 80-song inference plus original scoring
**48.37 s**, and paired evaluation including archive
provenance hashing **12.63 s**.

The subsequent FMA **selected-song cache** eliminated
the full download on warm runs; the earlier warning
that no FMA audio would be cached is superseded.
[Cold curated-cache run 39632517381](https://github.com/chrober/bliss-mood-poc/actions/runs/39632517381)
and [warm cross-workflow restore 39633485262](https://github.com/chrober/bliss-mood-poc/actions/runs/39633485262)
passed. The selected archive contains **76.51 MiB**
of the frozen 80 tracks, with original full-archive
SHA and per-MP3 hashes checked at restore. A separate
cache key protects the unscreened cohort
([run 39633600832](https://github.com/chrober/bliss-mood-poc/actions/runs/39633600832)).
See [cache design, access and licence caveats](fma-selected-audio-cache-2026-10-21.md).
**Actions caches are not confidential storage**; source
licences still apply. Only aggregates are uploaded as
Actions artifacts; no audio, private identities or
embedding vectors are published.

## Interpretation and next research

Both the FMA Genre proxy and the explored MTT odd-one-out
task do **not** favor this particular direct EffNet mean+L2
cosine over the most relevant classification-head baseline.
This does **not** rule out other encoders, genuinely
contrastive features, different pooling, or direct
human transition judgments.

The separate paired DEAM-240 Mood/VA evaluation is
prepared but source-blocked; inspect
[DEAM research status](deam-similarity-benchmark.md).
Independent local listening judgments and prospective
development/holdout separation are necessary before a
production decision or calibrated fusion weights.
Keep FMA TEST untouched and PR #16 a draft.
