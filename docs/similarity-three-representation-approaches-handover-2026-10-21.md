# Handover: Three song representations and similarity approaches for Lyrion

**Updated:** October 22, 2026 · **Working branch:**
`feat/similarity-metric-evaluation` · **Draft PR #16**.
Use the [end-to-end roadmap](similarity-lyrion-roadmap.md)
for the current phase-0-to-6 status. **Phase 0 is experimentally
implemented, not completely verified or production-ready.**

This document is the **representation-level research contract**.
It is not the BlissMixerLab playlist architecture decision.

## Research objective

Determine which representation and mathematical similarity method
best predicts meaningful musical relationships between songs,
with **separate reference targets** for stylistic/Genre proximity,
Mood/energy, audible/perceptual proximity, and suitability of
playlist transitions. The initial idea of selecting one of
seven distance formulas on classification heads alone was
insufficient: the underlying **representation** matters.

The same source track, encoder pass, preprocessing, candidate
pool, human/reference labels and abstention policy must be
used within each comparison. Do not compare numerical
scores across inherently different tasks (e.g. MTT odd-one-out
accuracy versus FMA Genre P@5).

## Approach A — Existing classification vectors

The shared original Discogs-EffNet model yields patch embeddings
that feed two separately trained MTG-Jamendo classifier heads:
87 Genre sigmoid labels and 56 Mood/Theme sigmoid labels.
The current schema-v3 SQLite sidecar stores per-head scores,
their ordered class definitions, preprocessing identity and
model provenance. Additional Voice/Instrumental capability
is independent from the two primary heads.

Candidate mathematical functions: **cosine**, **centered cosine**,
RMS-like distance, **weighted Jaccard** and historical
top-K/rank variants. Cosine compares direction; centered
cosine subtracts the within-vector mean and may reduce
the effect of shared baseline activation; weighted Jaccard
uses componentwise minima/maxima and relies on nonnegative
scores. Undefined norms, ties, near-zero vectors and
scale distributions need explicit policies. A Sigmoid
classification probability is **not** a pairwise
similarity probability. Different heads must not
be pooled without calibration.

**Advantages:** interpretable Genre/Mood dimensions,
existing compatible SQLite data, less expensive
per-pair comparisons. **Limitations:** a 56/87-label
taxonomy is a bottleneck and loses information about
timbre, instrumentation, arrangement and fine style;
Genre and Mood each address different user judgments.

## Approach B — Direct Discogs-EffNet 1280D audio embedding

Take the **raw 1280D vector before Genre/Mood heads**.
For the registered research implementation, accumulate
per-patch components in f64, take arithmetic mean across
patches, normalize once with song-level L2, and
compare with cosine. Store the result **separately**,
in a versioned research JSON file with audio SHA256,
track key, encoder SHA256, patch count, preprocessing,
pooling and representation fingerprints.
Do not silently add a schema-v3 model column or
recompute classification scores.

A direct embedding can encode aspects that are
absent from the classifier vocabulary, but 1280
dimensions do not imply improved human similarity.
The original encoder was **not established to be
specifically contrastive for this evaluation target**.
A later separate model family of pre-trained,
contrastively optimized embeddings should be tested
only with new pinned model hashes and controlled
data splits. Alternative pooling (attention,
duration-weighted, trimmed, temporal) is another
hypothesis, not a validated improvement.

**Implementation milestone:** optional Rust-v5
export via `research/song_embedding.rs` and
[`apply_rust_v5_embedding_export.py`](../scripts/apply_rust_v5_embedding_export.py).
The underlying temporary checkout stays pinned at
`2c3d44401436b3b41b6e067199016a1ed2335fbf`
from the separate Rust-v5 work, without merging PR #17.
Existing classification SQLite feature rows are
bitwise unchanged with embedding export disabled/enabled
in the declared synthetic smoke test.

**Technical gates:** versioned song-level contract,
L2 finite norm, same patch counts and audio hashes,
synthetic independent raw-patch mean pooling,
one-vs-two ONNX thread reproducibility, head/SQLite
off/on equality, reference C++/Essentia parity on a
representative multi-song cohort before any
production-readiness claim. Synthetic and single-song
proofs are narrower than full reference parity.

## Approach C — Deliberate feature fusion

Combine separate Genre, Mood and Embedding evidence
**after** deciding whether each is relevant to the
requested human objective. Raw cosine distributions
are not necessarily commensurate. A usable general
pair-score fusion requires documented score
calibration, expected coverage, missing-input handling,
possibly confidence measures, and development/test
separation by song/album/artist.

A first *untrained* local rank ablation used a frozen
triplet-wise average of equal-weight midranks of the
three pair cosines. It avoids fitting labels but is
**transductive and question-local**: adding/removing
candidate pairs changes the rank and there is no
global song-to-song score directly suitable for
Lyrion retrieval. The original MTT human questions
were already explored, so weight optimization and
evaluation on the same 293 questions would overfit.

See [fixed-rank research](similarity-fixed-rank-fusion-research-2026-10-21.md)
for the exact algebra, tie/abstention contract,
the four pre-defined combinations, complete
paired outcomes and diagnostic limits.

## Extension (2026-10-22): General scorer remains independent of personalization

**A/B/C are candidates for the GENERAL metric**, which must be
selected and validated for listeners **with zero personal
training data**. The optional, user-learned metric is an
additional scoring layer **on top of** a fixed, always
available general A/B/C solution; learning is never required
for retrieval or playlist creation.

Once a user has a compatible, quality-gated learned score
and the scores have a documented common scale:
`S_effective=(1-alpha)S_general + alpha*S_personal`,
with the user's **0–100% personal-blend** control.
If no valid per-user model exists, `alpha_effective=0`
and the general score is used **100%** regardless of the
saved preference. A/B/C *general* fusion coefficients
are not per-user blend weights. Raw cross-model cosine
scores, Mahalanobis distances and triplet-local midranks
must not be combined without calibration.

**Implementation and evidence status:** this is an
architectural decision, not a deployed Lab feature.
The existing `bliss-learner` and `lms-blissmixer-lab`
provide reusable triplet/survey and 23D Bliss learning
concepts. The new personal learner, model quality gate,
score calibration and UI slider still require separate
design and validation.

**Current local checkpoint (2026-10-22):** 100/100 matching
87D/56D/1280D feature vectors verified; 12 blinded
song pairs using 24 different tracks have been generated.
Their four human rating axes are still **unanswered**;
the old eight labels remain untouched. Do not call
this a selected general metric or an evaluated personal
learner. Preserve the blinded pilot before inspecting
its private sampling/model-score audit.

**Canonical decision:**
[General-first similarity and optional per-user metric
learning](similarity-general-personal-blending-architecture.md).
The existing independent candidate-source strategy remains open.

## Distinct decision: feature representation vs playlist sourcing

| Layer | Core question | Competing options |
| --- | --- | --- |
| **Similarity representation** | How do we compare two songs? | A: Genre/Mood classifiers; B: direct embedding; C: calibrated fusion |
| **Lyrion candidate admission and mixing** | Which tracks are eligible or retrieved for the next playlist position? | Bliss-first; feature-first; hybrid candidate-pool union; Bliss-only control |

An approach-C score can be used to rerank a
Bliss-first shortlist. Conversely, a feature-first
retriever can use pure approach A. The two
decisions must not be conflated.

The [Lyrion integration plan](lyrion-bliss-mood-genre-integration.md)
preserves hard rules, artist/repeat constraints,
Lyrion virtual-library membership and Bliss-only
fallback regardless of candidate source.

## Verified paired external research — current evidence

| Dataset / target | Registered same-song evidence | Caution |
| --- | --- | --- |
| **MTT: human odd-one-out** | 346 questions, 293 unique-majority, 53 human ties, 1,019 unique clips. Direct embedding cosine **182/293 = 62.12%**; Genre cosine **191/293 = 65.19%**; Mood cosine **192/293 = 65.53%**; Mood centered cosine **193/293 = 65.87%** | All human triplets explored; shared songs/artists; **no independent MTT holdout** |
| **FMA-Small: coarse same-Genre retrieval** | Frozen screened VALIDATION, 80 artist-distinct songs, each against 79 candidates. Embedding P@5 **0.2800**; Genre cosine **0.3200**; Genre centered **0.3225** | Genre labels are proxy, not transitions; **official FMA TEST untouched** |
| **DEAM: human VA emotion proximity** | Filtered 240-song cohort (197 excerpts + 43 full songs), old Mood cosine mean-query Spearman **0.28678455**; **new paired embedding comparison not completed** | Model training overlap unproven; publisher host unreachable |
| **MTG-Jamendo catalogue** | Conservative metadata artist/title overlap screening: FMA VALIDATION 42 possible matches among 800; DEAM 75 possible matches excluded | Nonmatches do not prove unseen recording/model-training independence |

Successful MTT direct paired research:
[run 39617159250](https://github.com/chrober/bliss-mood-poc/actions/runs/39617159250).
Full synthetic pooling/parity replay:
[run 39618323154](https://github.com/chrober/bliss-mood-poc/actions/runs/39618323154).
Exploratory equal-midrank A/B/C:
[run 39619708040](https://github.com/chrober/bliss-mood-poc/actions/runs/39619708040).
FMA direct paired:
[run 39625087310](https://github.com/chrober/bliss-mood-poc/actions/runs/39625087310).
The original genre baseline was reproduced exactly.
No evidence above selects a general production winner.

### Numeric result of the four fixed fusion ablations

On the common 293 human-majority MTT denominator,
with prediction abstentions counted wrong:

| Fusion | Correct / 293 | Coverage |
| --- | ---: | ---: |
| Audio + Genre | 163 (55.63%) | 234/293 |
| Audio + Mood | 170 (58.02%) | 241/293 |
| Genre + Mood | 167 (57.00%) | 230/293 |
| All three | 192 (65.53%) | 283/293 |
| Unfused Mood centered cosine | **193 (65.87%)** | **293/293** |

The fixed fusions did not improve the
common-denominator result. This does not
disprove fusion as a family; different
calibration, weights or encoders would
require disjoint new development/test data.

## Reproducibility, CI and data safety

Research code and workflows:
[`research-mtt-embedding-ab.yml`](../.github/workflows/research-mtt-embedding-ab.yml),
[`research-fma-embedding-ab.yml`](../.github/workflows/research-fma-embedding-ab.yml),
[`research-deam-embedding-ab.yml`](../.github/workflows/research-deam-embedding-ab.yml),
[`evaluate_mtt_embedding_ab.py`](../scripts/evaluate_mtt_embedding_ab.py),
[`evaluate_fma_embedding_ab.py`](../scripts/evaluate_fma_embedding_ab.py),
[`evaluate_deam_embedding_ab.py`](../scripts/evaluate_deam_embedding_ab.py).

The MTT curated audio cache covers exactly 1,019 clips,
approximately 117 MiB; FMA restores only 80 pre-registered
clips, approximately 76.51 MiB, not the 7.2-GiB
publisher archive. Both source rights and
Actions-cache visibility require care.
Never upload personal Lyrion audio/track IDs,
a local NAS path, per-song feature vectors,
or licensed corpus audio as public artifacts.
Only aggregate statistics and hashes are published.

The formerly failed
[MTT run 39621028716](https://github.com/chrober/bliss-mood-poc/actions/runs/39621028716)
contained a **test-harness filename discovery bug**:
the glob for `process-worker-*.json` also matched
four head report files, making eight reports where
four embedding reports were expected. The fix
uses an exact basename/full-match pattern;
[Linux/Windows regression CI 39622478825](https://github.com/chrober/bliss-mood-poc/actions/runs/39622478825)
passed, with the concurrent parity gate passing
in the subsequent MTT rerun. This was not an
observed model numerical discrepancy.

The paired DEAM evaluator also had a fixed
sample-fingerprint serialization mismatch,
corrected with
[Linux/Windows tests 39638092328](https://github.com/chrober/bliss-mood-poc/actions/runs/39638092328).
Later runs failed on external publisher connectivity,
not on an observed embedding accuracy comparison.

## Next research actions and decision gates (updated 2026-10-22)

1. **General-purpose A/B/C is the main workstream.** The
   user's bounded phase-2 feature inventory/export is
   **complete for the research cohort**: all 100 songs
   have coherent and verifiable 87D/56D/1280D features.
   Do not require any optional per-user learner to evaluate
   these untrained general similarity methods.
2. **Diagnostic listening is ready:** the local blinded
   12-pair pilot has actually been generated, using
   24 distinct songs, with **zero new human ratings
   supplied**. Collect independent 1–5 genre, mood,
   timbre and next-track judgments; keep the
   model-selection audit sealed until after review.
3. **Assess general similarity first:** compare A/B/C
   on matching songs, query sets and held-out evidence
   with explicit abstentions and uncertainty; retain
   simple reference baselines. Freeze a fresh
   24–40-pair evaluation block before weight fitting.
4. **Optional personal learning is a parallel track:**
   independently design informative/near/random/control
   triplets, train a small regularized per-user metric
   from human choices and evaluate incremental benefits
   on separate held-out votes. Then test calibrated
   **0–100% personal influence**, with deterministic
   **100% GENERAL fallback** if the per-user model
   is absent or incompatible. No Lab/learner changes
   are authorized at this stage.
5. **Product strategy remains separate:** compare
   Bliss-only, Bliss-first, feature-first and hybrid
   sourcing only with the same mandatory Lyrion
   filters and actual playlist-quality evidence.
   DEAM publisher/source verification can continue
   independently; never invent unsupported scores.

No merge to `main`, no changes to PR #13/#17
or the production mixer, and no production
default selected. The latest comprehensive
plan is the
[phase-0-to-6 roadmap](similarity-lyrion-roadmap.md).
