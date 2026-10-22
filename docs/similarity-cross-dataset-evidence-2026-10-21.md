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

## Second FMA VALIDATION reference: catalog-screened, independent TEST still reserved

[Confirmed filtered FMA Validation benchmark
39606850307](https://github.com/chrober/bliss-mood-poc/actions/runs/39606850307)
**PASS**: 42 possible exact artist/title catalog matches
with MTG-Jamendo (35/100 Hip-Hop candidates) were excluded
from the 800-song validation pool before an
80-artist-distinct, ten-per-genre selection.
**Filtered FMA Genre P@5** RMS 0.3000, Cosine 0.3200,
Centered Cosine **0.3225**, Weighted Jaccard 0.3000,
old cutoff Top-K 0.3025, Ranked Top-6 0.3125,
Ranked Top-12 0.3050. Filtered mAP@10 favored
Centered Cosine **0.1781** narrowly, filtered
nDCG@10 favored Ranked Top-6 **0.3048**
compared to Centered 0.3043. Random balanced
reference 0.113924.

**Crucial design:** This is a second *development*
reference on **different validation recordings**
from the unfiltered 80-song FMA sample in the main
table above, NOT a controlled paired causal
comparison and NOT confirmed independence from the
model's actual ONNX classifier/Discogs encoder
training data. The original FMA TEST partition
remains unused, and no MTT holdout remains.
[FMA provenance and filtering details](fma-mtg-catalog-overlap-2026-10-21.md).

The cross-dataset qualitative hypothesis remains
that Cosine and Centered Cosine are consistent
baseline/challenger methods; tiny shifts among
several methods on 80 songs cannot identify a
reliable production winner. Use separate Genre
ground truth vs Mood VA vs general human-triplet
judgments, never numerical averaging of these units.

## Next research axis (2026-10-21): Compare *representations*, not just metrics

The current seven metrics have been evaluated on already-pooled **87D Genre / 56D Mood/Theme classifier scores** only. The shared Discogs-EffNet model also internally provides **1,280D audio embeddings per patch**, but schema-v3 currently stores only the classifier heads. **No 1,280D song-level embedding baseline or multi-signal fusion has yet been evaluated.**

The next controlled experiment explicitly compares **A: per-head classification similarity**, **B: pooled direct 1,280D embedding cosine**, and **C: calibrated/rank-based task-aware fusion**, using identical clips and reference questions with strict cohort provenance. See [the canonical new-session handover](similarity-representation-comparison-handover-2026-10-21.md) for definitions, 1280D export/pooling design, reproducibility/parity gates, external Essentia/cosine.club precedents, CI costs, ground-truth caveats and prioritized implementation. Do not confuse fusion of similarity signals with Lyrion's separate Bliss-first / Feature-first / Hybrid candidate-admission strategy choice. Official FMA TEST remains unexamined, full MTT is exploratory, and no production choice has been made.


## Representation A/B research: now measured on MTT and FMA (2026-10-21)

This update supersedes the historical plan above, which correctly
described the state *before* embedding-export experiments.
Subsequent pinned Rust-v5 research runs evaluated **direct 1280D
Discogs-EffNet mean+L2 cosine** (approach B) against Genre/Mood
classifier-head similarities (approach A), with the same audio
and human/reference questions.

### Human odd-one-out evidence: complete MTT research set

[MTT paired A/B run 39617159250](https://github.com/chrober/bliss-mood-poc/actions/runs/39617159250)
PASS, with synthetic pooling/thread/SQLite regression
[run 39618323154](https://github.com/chrober/bliss-mood-poc/actions/runs/39618323154)
PASS. Of 346 unique unordered human questions, 293 have a
unique majority outlier and 53 tie; all 1,019 referenced
clips were covered. On the same 293 denominator:

| Representation | Correct / 293 | Agreement |
| --- | ---: | ---: |
| Direct 1280D cosine | 182 | 62.116% |
| Genre cosine | 191 | 65.188% |
| Mood cosine | 192 | 65.529% |
| Genre centered cosine | 191 | 65.188% |
| Mood centered cosine | **193** | **65.870%** |

The paired embedding-minus-Mood-centered difference is
**−3.754 percentage points**. Naive paired query resampling
sensitivity spans **−9.215 to +1.365 pp**, not an independent
population CI. Training-catalog overlap and repeated artists/
songs mean there is no fresh MTT holdout.

Four additional **untrained equal-weight triplet-local midrank
fusion** experiments also passed in
[run 39619708040](https://github.com/chrober/bliss-mood-poc/actions/runs/39619708040).
The best three-input fusion was **192/293** on the full
common denominator with 283/293 coverage, versus
193/293 and full coverage for Mood Centered Cosine.
The two-head fusion variants made 52–63 tied
abstentions. These are not globally calibrated
per-pair similarity functions, nor independent
estimates of fusion generalization. See the
[rank-fusion report](similarity-fixed-rank-fusion-research-2026-10-21.md).

### Independent *task* evidence, not an independent train holdout: FMA

The
[catalogue-screened, frozen 80-song official VALIDATION study](similarity-fma-embedding-ab-2026-10-21.md)
was implemented and verified in
[run 39625087310](https://github.com/chrober/bliss-mood-poc/actions/runs/39625087310).
Each of the 80 artist-distinct anchors was compared against
the same 79 candidates. Exact pre-embedding Genre cosine
baseline replay passed.

| Method | Genre P@5 | mAP@10 | nDCG@10 |
| --- | ---: | ---: | ---: |
| 1280D embedding cosine | 0.2800 | 0.163044 | 0.282363 |
| 87D Genre cosine | 0.3200 | 0.174876 | 0.298533 |
| 87D Genre centered cosine | **0.3225** | **0.178147** | **0.304271** |
| 56D Mood cosine (cross-task control) | 0.2775 | 0.150394 | 0.266065 |
| 56D Mood centered cosine (cross-task control) | 0.2675 | 0.152847 | 0.270372 |

All methods had 80/80 query coverage.
Embedding-minus-Genre-centered P@5 was
**−4.25 pp**; genre-stratified shared-query
95% sensitivity **−8.76 to +0.25 pp**.
This is **coarse Genre retrieval**, not
human similarity or playlist transition quality.
FMA **official TEST was not accessed**.
Potential MTG artist/title catalogue matches
were excluded from VALIDATION, but this does
not establish full model-training independence.

### DEAM and real-library listening remain necessary

DEAM's filtered 240-song Mood-Cosine mean-query
VA Spearman reference is **0.286784551387186**.
The new paired 1280D-vs-Mood/Genre workflow
was created and its sample-hash regression corrected
([Linux/Windows CI 39638092328](https://github.com/chrober/bliss-mood-poc/actions/runs/39638092328)),
but the most recent end-to-end attempt was blocked
by the original publisher host's failure to accept
HTTPS/TCP connections. No new DEAM embedding
difference has been measured. See
[DEAM benchmark status](deam-similarity-benchmark.md).

Across different experimental tasks, the existing
**raw mean-pooled EffNet cosine is not a demonstrated
universal winner**. This does **not** show that all
audio embeddings, contrastive models, other pooling
or calibrated fusions are inferior. Moreover,
Genre retrieval, Mood valence/arousal proximity,
general human odd-one-out similarity, and
**playlist transition quality** are distinct.
The next decisive reference comes from a controlled
local listening study using the same tracks and
independently rated Genre, Mood, audible similarity,
and next-song suitability. See the
[phase 0–6 roadmap](similarity-lyrion-roadmap.md).

**No production metric, mixing strategy or tuned fusion has
been selected.** Keep PR #16 Draft, official FMA TEST untouched,
and PR #13/#17, `main` and production mixer unchanged.