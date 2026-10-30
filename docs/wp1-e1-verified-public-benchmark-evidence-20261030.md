# WP1-E1: verified historical public benchmark evidence (30 October 2026)

## Status: real aggregate replay PASSED; no audio or new inferred metric score

[Completed GitHub Actions run 41058917003](https://github.com/chrober/bliss-mood-poc/actions/runs/41058917003) **PASS** (Python 3.15, synthetic fail-closed tests, three cross-run aggregate artifact downloads, exact member-SHA256 checks and real report generation). [Published aggregate artifact](https://github.com/chrober/bliss-mood-poc/actions/runs/41058917003/artifacts/12978177761) contains only already-public, non-identifying numeric aggregates.

This is an **audit/reproduction of existing historical results**, NOT a new audio benchmark, new model prediction, independent held-out confirmation, or selection of a General Metric. The output is a compact evidence inventory, **never a weighted mean of incompatible benchmark outcomes**.

### Frozen reproducibility contract

- [Machine-readable source locks](../research/wp1-e1-external-aggregate-lock-v1.json): exact GitHub workflow run ID, historical artifact ID, expected JSON member path and SHA256.
- [Strict offline verifier](../scripts/audit_wp1_external_aggregates.py): verifies member bytes and complete cohort/method/coverage contracts, rejects missing or substituted results, never guesses values for unmeasured models.
- [Synthetic regressions](../tests/test_audit_wp1_external_aggregates.py): corrupt ZIP member detection, test-split refusal, 293-question common-denominator and abstention rules, global-fusion non-substitution, DEAM cohort checks.
- [Public-artifact replay CI](../.github/workflows/research-wp1-external-evidence-replay.yml): reads only GitHub Actions **aggregate JSON**, not MP3, ONNX, teacher weights, embeddings, individual predictions, listener-vote rows, song identities, private LMS, or local NAS. It publishes **only** the sanitized numeric report.

The three verified archive artifacts:

| Dataset | Historical run | Artifact ID | Exact member SHA256 | Dataset status |
| --- | --- | --- | --- | --- |
| MagnaTagATune | 39619708040 | 12354537538 | a5367ccb2b43259a56c55aa9fb9dc3f80457969c98d1e592b5c55a5ff5ea2caf | Full 346 triplet / 293 decisive, all already explored |
| FMA-Small | 39625087310 | 12355954718 | dee3fa0ccd5e942d0abc62fb493094cdfef148dc67110ed66af9ce8bc2169e9a | 80 source-artist-disjoint VALIDATION; official TEST untouched |
| DEAM | 39579552118 | 12335578980 | a0032f5ee935fcb7be328daaf4a7a768eb80b02965ea9bb55bafa15f7426e3b3 | Screened 240, including 197 excerpts and 43 full songs |

## The actual three-task evidence — separate units, not one grand score

### MagnaTagATune: human odd-one-out majority accuracy

All methods use the **same 293 decisive human triplets** from 346 unique questions (53 human-vote ties), and 1,019 unique clips. Accuracy denominator is 293 **including method abstentions as incorrect**.

| Method | Correct / 293 | Majority agreement | Method coverage |
| --- | ---: | ---: | ---: |
| Mood centered cosine | **193** | **65.87%** | 100% |
| Mood cosine | 192 | 65.53% | 100% |
| Genre cosine or centered cosine | 191 | 65.19% | 100% |
| 1280D embedding cosine | 182 | 62.12% | 100% |
| Triplet-local rank fusion (embedding+genre+mood) | 192 | 65.53% | 96.59% |
| Triplet-local rank fusion (embedding+mood) | 170 | 58.02% | 82.25% |
| Triplet-local rank fusion (genre+mood) | 167 | 56.997% | 78.50% |
| Triplet-local rank fusion (embedding+genre) | 163 | 55.63% | 79.86% |

**CRITICAL:** These four existing rank-based fusions depend on the *three specific pairs of one triplet*. They cannot serve as globally comparable pairwise song-similarity scores. They are NOT any of the four proposed globally defined equal-weight pair fusions. The historical 293 questions are development evidence, not an untouched new MTT holdout.

### FMA: coarse genre retrieval (separate task)

Exact catalog-screened 80-song official **VALIDATION** cohort, 80 different artists, 79 other candidates per query, 100% query coverage for all five methods.

| Method | P@5 | mAP@10 | nDCG@10 |
| --- | ---: | ---: | ---: |
| Genre centered cosine | **0.3225** | **0.178147** | **0.304271** |
| Genre cosine | 0.3200 | 0.174876 | 0.298533 |
| Embedding cosine | 0.2800 | 0.163044 | 0.282363 |
| Mood cosine | 0.2775 | 0.150394 | 0.266065 |
| Mood centered cosine | 0.2675 | 0.152847 | 0.270372 |

FMA measures *top-level genre coherence*, not direct perceptual similarity; potential upstream model-training overlap is not completely excluded. Do not confuse this catalog-filtered sample with the older unfiltered FMA baseline (different scope), and never open official TEST as an exploratory tie-breaker.

### DEAM: mood proxy to human valence/arousal proximity

240 source-screened songs; values below are per-query mean Spearman to continuous human Valence/Arousal proximity, not human odd-one-out or playlist quality.

| Mood56 metric | VA Spearman | Valid query count |
| --- | ---: | ---: |
| Weighted Jaccard | **0.288850** | 240 |
| Cosine | 0.286785 | 240 |
| Centered cosine | 0.281344 | 240 |
| Ranked Top-12 Jaccard | 0.274481 | 240 |
| Ranked Top-6 Jaccard | 0.272141 | 240 |
| RMS | 0.271113 | 240 |
| Historical cutoff Top-k Jaccard | 0.190336 | 216 |

This is not a paired embedding test. The future DEAM embedding/multi-head replay was blocked by publisher access; the historical baseline aggregate does **not** supply its missing results. Valence/arousal overlap with Essentia pretraining is not proven absent.

## Exact same-audio representation availability and nonclaims

| Historical benchmark | Genre87 | MoodTheme56 | Embedding1280 | Bliss23 on identical recordings |
| --- | --- | --- | --- | --- |
| MTT paired A/B aggregate | Evaluated | Evaluated | Evaluated | **Not verified** |
| FMA screened paired A/B aggregate | Evaluated | Evaluated | Evaluated | **Not verified** |
| DEAM historical baseline | Evaluated | Evaluated | **Not verified in same cohort** | **Not verified** |

The four **globally comparable**, label-free, equally weighted Genre/Mood/Embedding pair-score fusions already have code and synthetic tests, but have **no verified numerical scores on the real MTT/FMA/DEAM cohorts**. The last MTT attempt [run 40881326086](https://github.com/chrober/bliss-mood-poc/actions/runs/40881326086) failed before inference at the 1,019-clip sparse audio cache reconstruction. No acoustic quality result follows from that failure. Existing aggregate-only artifacts cannot reconstruct missing per-song vectors or human-level per-question data for these four fusions. The historical GH cache may be branch-scoped; never assume a cache created on a sibling research branch is accessible here.

WP3's already completed Bliss23 -> Essentia Mood Ridge R6/R7 uses a **different private 240-song cohort** and Teacher proxy, not these public benchmarks; none of the original public MTT/FMA/DEAM aggregates establishes same-recording Bliss23 access. Do not insert Ridge/Bliss as if evaluated on the public datasets.

## Decision: next substantive WP1 experiment

**Next engineering focus:** recover safe reproducible public audio/features for a true **same-recording MTT global pairwise fusion replay**, using the verified existing curated 1,019-clip cache if actually accessible; otherwise document and diagnose the publisher HTTP-206 issue. An old aggregate-only artifact cannot replace the required vectors. Keep cache and publisher license restrictions: no full 2.77-GiB archive download, no public clip or weight artifacts, no private user audio. Once this replay succeeds, report all four global pair fusions beside the historical baselines on the **same 293 common questions**, including coverage, ties, paired discordance and group-aware uncertainty. Such new results will remain exploratory because this MTT corpus was already fully examined.

Only after establishing feasibility should FMA VALIDATION and DEAM paired fusion replays proceed on their pinned exact cohorts, retaining dataset-specific endpoints and avoiding access to reserved FMA TEST. No new compulsory listening, original Lyrion scan, student fitting on R6, personalized training data or changes to main/PR #16.

**WP2:** In parallel preserve the existing General/Personal 0–100% calibrated blend contract and synthetic fallback tests; real personalized metric improvement still needs permissioned independent user preferences and group-disjoint evaluation.

No single general model, production scorer, personal blend calibration or deployment is selected by this evidence audit.