# Decision record: General-first similarity with optional per-user metric learning

> **30 OCT 2026: WP2-P4 RESEARCH PROTOCOL IMPLEMENTED AND CI PASS.** [Fictional four-way calibration/validation/endtest study](wp2-p4-fictional-calibration-validation-20261030.md) extends P3 with disjoint synthetic 192/48/48/96 triplet partitions, fixed pair-target monotone calibration mappings and a validation-only quality gate controlling whether a simulated personal contribution is used. The unchanged [General/Personal batch gate](../scripts/general_personal_blend_contract.py) is exercised at 0%, 25%, 50%, 75%, 100%, including full-query fallback when unvalidated/incompatible. Cross-platform [CI 41063403438](https://github.com/chrober/bliss-mood-poc/actions/runs/41063403438) PASS, identical anonymized fictional output SHA-256 `037aa4fac02a1eb19be74580b5f0349c3408de36b4361d9588a4aa90b8683113`. **These are only fabricated labels and features**: no actual real-user calibration or musical personalization quality, no real model activation, no production/other-repository integration, and no substitute for independent General Metric quality research.


> **30 OCT 2026, RESEARCH-ONLY WP2-P3 UPDATE:** [New fictional grouped diagonal vs PSD diagonal+rank2 triplet learning study](wp2-p3-fictional-grouped-metric-learning-20261030.md) ran with a 288/96 training/holdout triplet split from 48 artificial source-identity groups and five predeclared label counts (0/10/25/50/100). Linux and Windows CI [41062367997](https://github.com/chrober/bliss-mood-poc/actions/runs/41062367997) passed with byte-identical anonymized fictional JSON results, including matrix compatibility with the existing 23x23 Mahalanobis validator and full-query missing/uncertified personal-model fallback at every blend percentage. **This is NOT real personal training, personal quality uplift, independently calibrated score blending or a runtime setting.** General Metric independent quality validation remains essential. The original external Rust learner and Lab apps were not modified, and no music, private triplets, original historical 12 pair ratings or actual user models were involved. 


> **Research strategy addendum 29 October 2026 (separate branch only):** The General/Personal product contract below remains **binding and unchanged**, but **personal metric learning is an explicit parallel research workstream**, not a distant optional suggestion with no milestones. Together with WP1 General, there is now a third independent WP3 focused on **Bliss 23D ↔ Essentia Genre 87D / Mood 56D / audio embedding 1280D relationships and on improving the Bliss-only similarity geometry**, not merely using Essentia as an extra reranking signal. See the [authoritative three-workstream strategy](similarity-three-workstreams-strategy-20261029.md) and its exact join, leakage, teacher-vs-truth, model-reuse, frozen-blend, milestones and independent-quality gates. The existing Lab `learned_blend` is **not** a General/Personal slider. The current learning code uses random triplet splits without certified artist/album separation; reusing it requires grouped evaluation. The 12 user ratings are closed and cannot be relabeled as new personal training data. Neither PR #16 nor the two related repositories were modified by this addendum.


**Decision date:** October 22, 2026. **Status:** Architectural requirement accepted;
research and implementation pending. **Scope:** `bliss-mood-poc`, Draft PR #16,
research documentation only; **not** a claim of deployment or an approved
production metric.

## 1. Non-negotiable product and research objective

**Do not replace the original task with personal preference learning.**
The primary goal remains to identify, rigorously evaluate and eventually
deploy a **strong, self-sufficient general-purpose song similarity metric**
that performs well **without any user ratings or trained personal matrix**.
"General" means robust across evaluation libraries/listeners/tasks; it
does not assert that one objective human-independent notion of musical
similarity exists. Song genre/style, mood/energy, timbre and immediate
playlist suitability remain separately measured targets.

**Personalized metric learning is strictly optional and additive.**
An individual listener may supply relative judgments to learn a separate
personal metric. A **0–100% personalization blend control**, conceptually
like the existing BlissMixerLab `learned_blend`, determines its influence.
The general metric remains permanently available and is the complete
fallback in the absence of a compatible, validated personal model.

This is a **third independent design dimension**, not a replacement for:

1. **Representation and general metric:** A = 87D Genre/56D Mood head
   comparisons; B = direct 1280D Discogs-EffNet song embedding; C =
   calibrated, *general* multi-representation combination, potentially
   including Bliss 23D when explicitly evaluated.
2. **Candidate source:** Bliss-first, feature-first, hybrid pool, and
   Bliss-only control. Their ranking/admission rules remain separately
   evaluated.
3. **Personalization layer:** general baseline + optional learned user
   metric + user-configured blend. It can apply with any candidate strategy
   once that strategy exposes a bounded eligible candidate set.

**The "C" general fusion and the personal/general blend are different
operations.** General fusion selects globally useful signal weights
from independent evidence; personal learning adjusts similarity for
one listener. Neither presumes Bliss-first is the winning retrieval
strategy.

## 2. Required behavior and mathematical contract

Let `S_general(i,j)` be the selected versioned general song-to-song
similarity. Let `S_personal,u(i,j)` be the validated similarity
produced by user `u`'s learned metric. Let the user store an
integer `personal_blend` `p` in `[0,100]` and define
`alpha_requested = p/100`.

Only when a **compatible, quality-gated and available** personal model is
loaded for this query and the needed candidate cohort does the requested
blend take effect:

```text
alpha_effective = personal_model_usable_for_query ? alpha_requested : 0

S_effective_u(i,j) = (1 - alpha_effective) * S_general(i,j)
                   + alpha_effective * S_personal_u(i,j)
```

**Score comparability is a gate, not an assumption.** This formula only
becomes operational after the general and personal output scores have
been mapped to a **documented common, query-consistent orientation and
scale**. Raw cross-representation cosines, Mahalanobis distances,
triplet-local midranks and unnormalized classifier activations must
**not** be blended directly. Score transforms/calibration must be
frozen from separate development evidence, with versioned parameters,
and must preserve the interpretation of `0%`, `100%` and the middle
settings. No calibration is inferred from the user's selected test
judgments. If comparability cannot be certified, the personal model is
not usable; apply the general fallback, not an arbitrary mixture.

| Personal model status | UI requested blend | Effective scoring |
| --- | --- | --- |
| Absent (new user, no triplets) | Any 0–100% | 100% general; effective `alpha=0` |
| Training in progress, unvalidated, stale, incompatible or failed | Any 0–100% | 100% general; preserve stored preference |
| Valid and compatible | 0% | 100% general, byte-for-byte same general scoring/rank contract |
| Valid and compatible | 25% | 75% general / 25% personal, after calibration |
| Valid and compatible | 50% | 50% general / 50% personal, after calibration |
| Valid and compatible | 100% | 100% personal; general metric remains installed for fallback |

The slider measures **personal influence**, *not* general influence.
Missing personal data is **never** grounds for blocking playback or
silently using an untrained identity matrix at `alpha>0`.
The effective blend, usable-model status and fallback reason should be
observable. A stored preference may remain at 100% while the actual
blend safely falls back to 0% until valid training exists.

**Pair and query availability:** require compatibility of representation
fingerprints, audio/feature provenance, user profile and available
anchors/candidates. A query must use one declared effective policy
for the comparable candidate cohort: if a personal metric is not
available for the requested ranking set, consistently fall back to the
general metric (or explicitly apply a separately specified partial
coverage policy backed by tests); **do not silently assign personal
scores only to a few candidates and compare them against uncalibrated
general-only others**. Undefined scores follow the general scorer's
existing abstention/fallback contract.

## 3. Personal data and learner architecture

The existing projects
[`chrober/bliss-learner`](https://github.com/chrober/bliss-learner)
and
[`chrober/lms-blissmixer-lab`](https://github.com/chrober/lms-blissmixer-lab)
are **reference implementations**, not automatically adopted
unchanged. Current verified behavior:

- BlissMixerLab's separate survey selects analyzed tracks randomly
  from `bliss.db` and records odd-one-out triplets in
  `training_triplets.json` as `[similar_1, similar_2, odd]`.
  The survey supports skipping ambiguous questions and stores votes
  separately from upstream Bliss.
- `bliss-learner` learns a regularized 23-feature Mahalanobis matrix
  with a probit/STE-style triplet likelihood, L-BFGS optimization
  and a cross-validated regularization search.
- BlissMixerLab already has `learned_blend` for **its own**
  learned-versus-variance-based Bliss adaptive weighting.
  **That existing setting does not currently control the new
  Genre/Mood/Embedding general/personal blend.** Do not present
  the design as an already implemented Lyrion setting.

Proposed future learning interface (still to be designed/validated):

- Preserve a local per-user **append-only versioned vote record**:
  exact track references, question/selection seed, algorithm and
  difficulty stratum, selected similar pair / odd one out,
  optional skip/uncertainty, timestamp and music objective
  (general similarity vs directed next-track fit).
  Repeat questions provide a consistency check; they must not
  be duplicated across train/test splits as independent evidence.
- Keep one user's ratings/models isolated from other users. Do not
  upload audio, individual feature vectors or personal votes to CI
  or a central service. Version, back up, export, disable and
  reset user models without editing `bliss.db` or general features.
- Start with a **small, constrained number of trainable parameters**:
  for example nonnegative, regularized weights on a few separately
  calibrated general Bliss/Genre/Mood/Embedding signals, potentially
  relative to a fixed general prior. Do **not** train an unrestricted
  1,423-dimensional full Mahalanobis matrix from tens of triplets.
  Higher-capacity diagonal or low-rank adaptation requires evidence
  and held-out validation before introduction.
- The personal learner outputs a versioned metric, training count,
  calibration compatibility, provenance, uncertainty/quality
  checks and validation results. Training failure leaves the
  previously validated metric or the general fallback intact.

This is a design direction. **No personal ONNX/bliss learner has been
implemented in PR #16**, and no personalized weight vector has been
measured on the 100-song cohort.

## 4. Triplet sampling and experimental controls

The user's existing odd-one-out survey is a good reusable interaction:
the user listens to three tracks, selects the one that does not belong
(or equivalently selects the most similar pair), and may skip.
**Personal judgments are the training signal, not a nuisance to
eliminate and not a universal ground truth.** Keep the target
"Which two are musically most alike?" separate from directed
"What is a better follower for anchor A, B or C?"

Instead of relying on only uniformly random triples, investigate
a **documented mix** of:
- **Model disagreement / informative triples:** general and competing
  representations identify different nearest pairs. Active sampling
  can select uncertain cases when the personal model becomes available.
- **Near-neighbor / boundary cases:** discriminate subtle similarities.
- **Easy presumed two-similar/one-different controls:** useful for
  calibration of question clarity, but the presumed pair is only a
  *model-generated hypothesis*, not a universally correct answer.
- **Random/diverse exploration and repeats:** prevent selection bias,
  track shifts and assess consistency. Do not force choices on ties.

Question selection policy and its probabilities/strata must be
persisted to permit later bias analysis. Never claim an odd-one-out
answer is wrong solely because it contradicts a model-chosen
"control." Define human-authored/independently curated checks
separately from model-generated checks.

## 5. Evidence and stop/go gates

**General branch is mandatory and primary:**

1. Continue paired A/B/C evaluation on external MTT, FMA and DEAM
   (when officially verifiable), plus a newly collected local
   human-study block; preserve identical song/query cohorts,
   model provenance and holdout boundaries.
2. Compare Genre, Mood, 1280D and calibrated general fusion; retain
   meaningful single-signal baselines and Bliss-only controls.
   Select the general scorer for broad, independently measured
   musical quality, coverage, stability and cost **without** relying
   on personal votes or training.
3. Document an immutable default scorer contract, calibrated score
   orientation/scale, abstentions and validated behavior. The actual
   general method and weights are **still undecided**.
4. Only after quality gates, evaluate candidate-source strategy
   (Bliss-first, feature-first, hybrid) and real playlist quality.

**Optional personal branch must prove incremental benefit:**

1. Validate that chosen question mix elicits reproducible relative
   judgments and allows skipping / stated uncertainty.
2. Compare unpersonalized general baseline, eligible single-signal
   baselines and regularized personalized model on **held-out user
   triplets**, separated by track/artist where practical, with
   explicitly common coverage. Record triplet accuracy, negative
   log-likelihood, sample size, bootstrap/sensitivity and repeated
   question consistency. Adaptive training questions alone cannot
   measure unbiased generalization.
3. Evaluate learning curves versus number of votes (e.g. 0, 10, 25,
   50, 100) with prespecified sampling and multiple users if
   available; these are measurement checkpoints **not activation
   thresholds**.
4. Test scoring with `alpha=0,25,50,75,100` on held-out questions,
   respecting the user's intended setting. Do not optimize each
   blend on the same test answers.
5. Run blinded real playlist A/B comparisons with the same seeds,
   candidates and mandatory Lyrion filters, comparing 0% personal
   against fixed selected blend(s), also tracking repeat violations,
   diversity and runtime overhead. Evidence must support any claim
   of improvement.

**Updated experimental state (October 28, 2026):** the
local 12-pair diagnostic instrument has now been
**fully human-rated** (12/12 pairs, 24 distinct tracks,
60/60 ratings, seven comments). The original 100-song
cohort retains compatible 87D Genre, 56D Mood and
1280D embeddings (**100/100 valid; zero mismatches**).
The [local ordinal evaluator](similarity-local-listening-pilot12-evaluation-2026-10-28.md)
is implemented and synthetic-tested on Linux and Windows.
Its real model-vs-human comparison **still requires the
locally sealed private model audit** and has not been
completed in chat. Pair 10 is a declared human-identified
nonmusic sensitivity case; original labels are preserved.
These observations are **not** a certified general metric,
completed phase-0 parity or an adequately large learned
personal model. The prior eight labels remain unchanged.

## 6. Lyrion runtime constraints and implementation boundaries

- Upstream Bliss Mixer and `bliss.db` remain unchanged. A future
  experimental integration belongs behind an opt-in Lab-side
  extension, following existing local/candidate-provider contracts.
  No changes to `chrober/lms-blissmixer-lab`,
  `chrober/bliss-learner`, PR #13/#17 or upstream main are
  authorized by this documentation decision.
- Blending happens **after** the selected candidate source and
  mandatory Lyrion eligibility, virtual-library, repeat and
  source filters; a personalized metric must not admit otherwise
  ineligible tracks. Local offline features only: no ONNX audio
  inference at playlist-generation time.
- Do not conflate **general-vs-personal blend** with the existing
  experimental *Bliss-vs-Genre/Mood guidance* knobs or the
  current BlissMixerLab internal `learned_blend`. Decide the
  UI/API mapping and names before any host implementation.
- Version and test all accepted methods, profile calibration,
  invalid-model detection, fallback to `alpha_effective=0`,
  score reproducibility, plugin disabled path, multi-user
  isolation and per-song missing-feature behavior.

## 7. Immediate next steps

1. Keep the **general-metric evaluation** as the primary near-term
   research activity. The 12-pair human listening judgments
   are complete; run the new local ordinal evaluator with
   the *original* private selection audit, explicitly reporting
   both the full 12 and 11 music-only pairs. Preserve ratings
   and do not pretend it is an unbiased metric holdout.
2. Independently specify a compact personal triplet data contract
   and a baseline active/random/control sampling experiment using
   the same existing 100-song research cohort. Do not substitute it
   for the independent general-metric holdout.
3. Define/test a calibration and blend *research* protocol against
   synthetic and disjoint human comparisons **before** wiring any
   Lyrion runtime control. Only a future explicit work package
   may modify the other two repositories.

**Canonical handover:** [`docs/chat-handover.md`](chat-handover.md).
**Roadmap:** [`docs/similarity-lyrion-roadmap.md`](similarity-lyrion-roadmap.md).
**Representation A/B/C:** [`docs/similarity-three-representation-approaches-handover-2026-10-21.md`](similarity-three-representation-approaches-handover-2026-10-21.md).
**Lyrion candidate strategy:** [`docs/lyrion-bliss-mood-genre-integration.md`](lyrion-bliss-mood-genre-integration.md).
