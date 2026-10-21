# Cross-dataset similarity evidence, without inventing a common score

**As of 2026-10-21**. Branch `feat/similarity-metric-evaluation`,
Draft PR #16. All values reproduced from documented **completed**
repository workflows, not imputed from any uncompleted follow-up.
Different datasets measure **different constructs**. No metric is
approved for production; do not merge to main.

## Independent evidence channels

| Dataset | What is measured | Scored cohort | Source |
| --- | --- | --- | --- |
| [FMA-Small](fma-genre-benchmark-plan.md) | Genre retrieval vs eight coarse *top-level genre categories* using the 87D Genre head | 80 artist-distinct **VALIDATION** tracks, official TEST untouched | [successful run 39583233757](https://github.com/chrober/bliss-mood-poc/actions/runs/39583233757) |
| [DEAM](deam-similarity-benchmark.md) | Query-macro Spearman of 56D Mood similarity vs **human Valence/Arousal proximity**, a *proxy* for mood | 240 seeded, collection-stratified tracks **after exact catalog artist/title screening** (197 earlier excerpts, 43 full 2015 songs) | [successful run 39579552118](https://github.com/chrober/bliss-mood-poc/actions/runs/39579552118) |
| [MagnaTagATune](magnatagatune-paired-analysis-2026-10-21.md) | Human **odd-one-out** general perceived similarity; majority accuracy | 346 unique unordered triplets / 1,019 MP3s, 53 human-vote ties, **293 eligible**; all 346 evaluated, no MTT holdout | [successful cache HIT 39600498519](https://github.com/chrober/bliss-mood-poc/actions/runs/39600498519) |
| MTG-Jamendo | Source 87D Genre / 56D Mood tagging domain, label vocab and training/test provenance sanity | Official split-0 class names/artist separation checked, **no new prediction accuracy computed** | [successful metadata audit 39586686845](https://github.com/chrober/bliss-mood-poc/actions/runs/39586686845) |

## Metric-by-metric triangulation (different units; do not average rows)

| Metric | FMA Genre P@5 | DEAM filtered Mood VA Spearman | MTT Genre majority accuracy | MTT Mood majority accuracy |
| --- | ---: | ---: | ---: | ---: |
| RMS | 0.3175 | 0.2711 | 63.5% | 54.6% |
| Cosine | 0.3500 | 0.2868 | 65.2% | 65.5% |
| Centered Cosine | 0.3525 | 0.2813 | 65.2% | **65.9%** |
| Weighted Jaccard | **0.3550** | **0.2888** | 63.8% | 61.1% |
| Historical cutoff Top-K | 0.3150 | 0.1903 (216/240 valid DEAM queries) | 60.1% | **44.4%** (~71.7% MTT coverage) |
| Ranked Top-6 Jaccard | 0.3150 | 0.2721 | 61.8% | 62.5% |
| Ranked Top-12 Jaccard | 0.3400 | 0.2745 | 64.5% | 64.8% |

FMA P@5 is a **genre retrieval proportion**, DEAM is a **Spearman
rank correlation coefficient** against continuous human VA proximity,
and MTT numbers are **classification proportions for general musical
triplet judgments**. They MUST NOT be numerically averaged,
standardized as if interchangeable, or treated as a joint
statistical meta-analysis.

### Descriptive observations (hypotheses only)

1. **Cosine** performs relatively consistently across independent
   reference types. Its Genre P@5 is 0.3500 vs the FMA best 0.3550
   (tiny difference on just 80 songs); filtered DEAM Mood
   VA correlation 0.2868 vs best 0.2888; MTT Mood and Genre both ~65%.
2. **Centered Cosine** is very close to Cosine throughout.
   MTT Mood is only ~0.4 percentage points higher than Cosine,
   and Genre is tied. The difference is smaller than plausible
   resampling variation and will be inspected with paired
   within-question tests, NOT interpreted as proven.
3. **Weighted Jaccard** is slightly ahead on FMA and DEAM,
   but behind Cosine in MTT general similarity. A different
   objective can lead to a different appropriate metric;
   no single reference is privileged to determine playlist quality.
4. The **historical cutoff Top-K** exhibits important coverage
   failures and weaker Mood triplet coverage-adjusted results.
   It should never be compared to fully defined metrics only
   on its selectively covered questions.
5. **Genre-vs-VA** numbers are deliberately omitted: Genre
   classifiers have not been validated against VA as Genre ground
   truth. Likewise MTT votes are general similarity, not a
   separate genre and mood human annotation split.

### Why these are not independent confirmations

- DEAM's 75 possible artist/title matches to the Jamendo catalog
  were excluded *before* the filtered 240 sample. This is an
  incomplete catalog screen, not proof of unseen audio in the
  Discogs encoder training sets. The filtered and original
  240-track samples differ, so their scores cannot be paired.
- FMA used **VALIDATION only** and the official TEST split is still
  deliberately reserved. The pretrained encoder's overlapping
  recording provenance is not fully audited.
- All 346 unique MagnaTagATune human triplets were explored.
  The artist co-occurrence graph forms one connected component.
  Its baseline accuracy is therefore descriptive *within-corpus*
  evidence, not strict independent artist-heldout proof.
- Not all rows have identical coverage; old Top-K abstentions
  introduce selection/denominator bias if mishandled.
- Full-song Lyrion playback may react differently from 30-s
  low-bitrate research clips, and pairwise similarity is distinct
  from adjacent-song transition quality.
- Annotation uncertainty is material; MTT had 53 questions tied
  for human majority even after merging ordered permutations.

## Next gates, in order

**A. Paired MTT uncertainty.** Use
[mtt_paired_evidence.py](../scripts/mtt_paired_evidence.py):
compare the SAME 293 questions for all seven metrics and
both heads, treating metric abstentions as incorrect. Report
discordance counts plus descriptive (not population-CI)
question resampling and artist-weight sensitivity.
Await real completed run and actual paired numbers before
asserting a difference is nontrivial.

**B. Operational A/B.** A pinned Rust-v5 binary-cache + 114-MiB
curated MP3 cache allow controlled 2- vs 4-worker same-cohort
runs. Check true cache HIT, audio/model hashes, 14 aggregate
scores, wall time and memory before claiming faster workflows.
Do not imply that an adaptive worker scanner is running:
this GH benchmark uses fixed isolated-process workers.

**C. New independent human evidence.** Find a separately
licensed/accessible perceptual or transition quality reference.
Do not recycle MTT as an unseen holdout.

**D. Final FMA TEST split** only once metrics and analysis rules
are predeclared, and no tuning has been carried out against it.
A blinded actual Lyrion playlist listening/transition assessment
remains necessary before choosing a user-facing similarity policy.

PR #16 stays Draft. No local/private music rescan, no
production mixer change, no merge to main, no commits to PR #13/#17.


## Updated FMA training-provenance warning

[Completed metadata-only FMA/MTG screening
39605675932](https://github.com/chrober/bliss-mood-poc/actions/runs/39605675932)
found **42 possible exact artist/title MTG-Jamendo
catalog matches among 800 FMA VALIDATION songs**,
**35 of 100** in Hip-Hop alone; FMA TRAINING had
121 candidates among 6,400. MTG artist-only matches
were 68 VALIDATION / 260 TRAINING.
**These do NOT establish literal audio duplication or
ONNX training exposure**, nor do their nonmatches
prove training disjointness. The untouched official
FMA TEST split is still reserved.

The [catalog-filtered FMA validation research
workflow](../.github/workflows/fma-genre-filtered-validation.yml)
and its Python parser exclude the 42 potential exact
catalog candidates before validation sampling and
model inference, reusing a pinned Rust-v5 binary.
The new filtered 80-song cohort is **not paired with**
the earlier 80-song FMA validation cohort; comparison
must remain descriptive. The filtered real
[run 39606850307](https://github.com/chrober/bliss-mood-poc/actions/runs/39606850307)
needs a completed result before any updated Genre
P@5/mAP/nDCG statements. Audit and reproducibility:
[FMA-MTG metadata screen](fma-mtg-catalog-overlap-2026-10-21.md).
