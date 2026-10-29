# WP3-R2 and WP2-P2: grouped statistical models and isolated Bliss learning

**Status: 29 October 2026. Research-only source and synthetic cross-platform checks.**
All changes on `feat/general-pairwise-similarity-research`. No original PR #16 changes,
no native rescans, no worker tuning, no new compulsory listening and no private
library/song survey opened. Reuse the binding
[three-workstream research strategy](similarity-three-workstreams-strategy-20261029.md)
and the prior
[grouped WP3-R1/WP2-P1 protocol](bliss-essentia-grouped-relationships-personal-evaluation-20261029.md).

## WP3-R2: fit-on-train-only Ridge / PLS / PCA-limited CCA

Implementation: [research_bliss_essentia_teacher_models.py](../scripts/research_bliss_essentia_teacher_models.py).

Use the existing exactly ordered 23D Bliss representation as input, and existing
87D Genre or 56D Mood/Theme experimental **Essentia teacher outputs** as
targets. Create the immutable artist/album/recording connected-component
outer partition using the existing
[grouping guard](../scripts/research_grouped_split.py).

Algorithms are **reused from NumPy/SciPy/scikit-learn**, rather than
reimplemented:

- `StandardScaler + Ridge(alpha=10)` predicts each of the 87/56
  teacher dimensions from Bliss 23D; evaluate heldout mean absolute
  error against a constant teacher mean fitted on **training only**.
- `StandardScaler + PLSRegression(n_components=2)` gives an
  independent low-dimensional multivariate predictive comparator.
- Training-fitted `StandardScaler + PCA` compresses the Bliss
  and teacher views, then `CCA(n_components=1)` analyzes their
  shared structure. Report heldout canonical Pearson association
  only. This is **PCA rank truncation**, not an unqualified
  regularized CCA guarantee or independent hypothesis test.
- Fixed complexity and penalties are chosen **before the new
  synthetic or future real run**. No outer test-set feature
  selection, scaler fitting or hyperparameter search. New
  tuning would require nested grouped development CV.
- Every bad dimensionality, missing/NaN head, insufficient
  independent component rank, absent grouped holdout or
  unstable prediction fails closed.

Use the fixed research-only versions in
[requirements-wp3-r2.txt](../research/requirements-wp3-r2.txt).
These model runs **do not estimate musical or playlist similarity**,
and no user data are collected. A low teacher reconstruction error
alone does not mean Essence is the correct ground truth or Bliss's
song-distance ranking has improved.

### WP3-R2-B: improving *Bliss itself*, without an Essentia runtime signal

Implementation: [research_bliss_only_teacher_geometry.py](../scripts/research_bliss_only_teacher_geometry.py).

Fit a **Ridge student transform** only on train:
`Bliss 23D -> predicted Essentia Genre/Mood vectors`. At inference
the student consumes **only Bliss 23D**; no Essentia model, classifier
head or 1280D embedding is needed at ranking time. This is a
separate concept from directly mixing Bliss and Essentia similarity
scores at serving time.

On entirely heldout artist/album/recording groups, compare the
**Spearman rank order of pairwise distances** for:

1. Raw 23D Bliss Euclidean geometry.
2. Bliss Euclidean geometry standardized with **train-fitted scales**.
3. Student geometry produced by train-fitted Bliss-to-Genre/Mood Ridge.
4. A train-only teacher-label permutation negative-control student.

Targets are paired **heldout Essentia teacher distances**, not
human-annotated perceptual similarity. A better student-to-teacher
rank agreement would prove **teacher-geometry distillation** on
these examples, **not** better musical similarity. Pairs share
songs and must not be treated as independent observations;
limit any report to at most 80 heldout songs (3,160 pairs).
Use frozen fixed hyperparameters and seeded subsampling
without consulting heldout teacher values. No output contains
song names, learned vectors, paths or individual pair scores.
This is an *intermediate research gate* toward a Bliss-only
metric, with independent music-quality testing still mandatory.

These routines currently run on **synthetic records only**.
No real WP3 association, teacher-prediction, or Bliss-distance
quality result exists. Note that native and Rust-v5 1280D
embeddings and voice classifiers are **not** the target of this
phase; validating 1280D distillation would require additional
train-fitted dimension reduction and more diverse recordings.
Do not expand the network model workload simply to fill a
missing dataset.

## WP2-P2: source-restricted existing Rust bliss-learner training

Source-level findings from [chrober/bliss-learner](https://github.com/chrober/bliss-learner)
`src/main.rs`:

- It accepts a SQLite database (`--db`), a list of ordered
  `[similar_1,similar_2,odd]` triplets (`--triplets`) and an
  output matrix file (`--output`).
- It internally uses random triplet 80/20 and lambda CV on
  its supplied dataset, then trains the final matrix on
  **every supplied triplet**. This is okay for eventual production
  training but invalid if the *same supplied triplets* are
  presented as independent heldout evidence.
- Its format and core STE/probit/L-BFGS Mahalanobis algorithm
  are reusable. **Do not copy its optimizer, modify its repo
  without authorization, or pass the original complete survey
  file as experimental training input**.

New [prepare_bliss_learner_train_only.py](../scripts/prepare_bliss_learner_train_only.py)
solves the **outer holdout contamination** without changing
the Rust learner: after a group-disjoint partition, it opens
the original `bliss.db` with mode=ro and selects only the
exact 23 learner columns for songs used by **train triplets**.
It creates, in a **new private directory only**:

- `train-only-bliss.db`: minimal SQLite TracksV2, containing only
  distinct train songs and the original 23-feature ordering.
- `train-only-triplets.json`: only the original, unchanged-role
  training triplets, no heldout labels or song keys.
- `train-only-manifest-private.json`: strictly private counts,
  input database size/mtime and SHA256, output DB and triplet
  SHA256, hashed source group selection, learner argument
  contract and a clear **NOT_TRAINED** status.

The original source DB's full SHA256 and size/mtime are checked
before and after reading; a missing source cannot be implicitly
created; a preexisting output directory is never overwritten.
The original Rust learner can later be invoked with
`--db` pointing *only* at the isolated training SQLite,
`--triplets` pointing *only* at the train-only JSON, no LMS
notifications and `--output` into that private directory.
This is not yet executed, and no Rust binary was built
or downloaded for this phase.

An independently published heldout quality score would still
require an exact **learner executable SHA256, source revision,
verified training manifest and resulting matrix SHA256** plus
a follow-up evaluation using only heldout votes. The present
train-only manifest is a preparation contract, not proof
that a subsequent arbitrary external binary actually obeyed
its input arguments. The learner's own *inner* lambda CV
remains triplet-random within the supplied training portion:
its internal CV score is **not** group-valid; freeze/tune
hyperparameters only through a separate grouped scheme if
claiming generalizable gains. A full learner modification
would require a separately reviewed branch/authorization.
No personalized gain or trained model is claimed yet.

### Binding missing-data and safety constraints

- Both stages depend on a valid, previously approved
  **private or public paired song-feature dataset** with exact
  Bliss 23D, Essentia 87/56 (and optional 1280D),
  artist/album/recording groups and licensing provenance.
- The old 12 user-rated **pairs are complete** and must
  not be treated as a new independent or personally
  labeled triplet dataset. Future personal labels are
  entirely opt-in; WP1 General remains usable without them.
- Model heads are predictions, not error-free ground truth.
  Recording duplicates, album/artist/source leakage and
  **teacher model training overlap** remain scientifically
  significant and can only be ruled out with provenance
  that is not currently established.
- Real external music-quality validation, especially whether
  a distilled **Bliss-only** metric improves human
  similarity judgments or playlist transitions against an
  unchanged Bliss baseline, remains a **separate gate**.
  Do not claim a better General Metric from artificial
  synthetic teacher examples.
- No modifications to PR #16, original private music,
  native 100-song files, upstream bliss-learner,
  lms-blissmixer-lab or worker tuning.
- If local Windows runs are later required, deliver one
  complete automated PowerShell `& { ... }` block that
  discovers the *actual* Bliss DB and read-only source
  inputs; updates an isolated clean worktree, verifies
  hashes/dependencies and creates only new private outputs.
  Never guess user-specific paths or silently use the
  original DB for learner training.

## Cross-platform test gates

- [WP2 staging synthetic tests](../tests/test_prepare_bliss_learner_train_only.py)
  use scratch SQLite and triplets, verify original DB byte
  SHA unchanged, contents of new train-only DB match the
  isolated triplets, manifest SHA, input protection, 5-triplet
  learner minimum and no file/key disclosure in aggregates.
- [WP3 fit-on-train tests](../tests/test_research_bliss_essentia_teacher_models.py)
  verify fixed Ridge/PLS/PCA-CCA with mathematically constructed
  heads, group holdout, determinism and fail-closed invalid vectors.
- [Bliss-only student tests](../tests/test_research_bliss_only_teacher_geometry.py)
  verify no Essentia head is required at *student inference*,
  negative control, out-of-group distance association, bounded
  song pairs, determinism and no private track identities.
- [WP2/WP3 CI](../.github/workflows/research-bliss-personal-contracts.yml):
  Python 3.13 Linux/Windows, **stdlib only**, no user data.
- [WP3-R2 CI](../.github/workflows/research-bliss-essentia-teacher-models.yml):
  Python 3.13 Linux/Windows with fixed mature statistical packages,
  synthetic data only, no model downloads or music.

## Next experiments

1. **WP3-R3** obtain a permissible, group-labeled, verified
   Bliss↔Essentia paired-feature source and record coverage,
   exact feature and model versions, label order and
   unverified teacher training overlap.
2. Conduct fixed, descriptive real correlations, PCA/CCA/PLS
   and Bliss-only teacher-distillation *development* results.
   Only later use a genuinely independent perceptual/music
   similarity reference to compare unchanged Bliss with
   predeclared transformed Bliss; report uncertainty and
   library/genre/artist strata.
3. **WP2-P3** verify/train the *existing* learner exclusively
   from the prepared private train-only bundle using an
   authorized executable and nonoverwriting private output,
   followed by heldout-only external scoring with verified
   manifest and binary hashes. If no licensed independent
   per-user survey is available, continue synthetic protocol
   and fallback tests without soliciting compulsory votes.
4. Continue **WP1 General** in parallel. A former MTT
   global-fusion CI was blocked by publisher sparse HTTP
   timeouts, not by an observed musical-metric failure.
