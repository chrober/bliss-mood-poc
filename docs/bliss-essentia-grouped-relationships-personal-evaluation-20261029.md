# WP3-R1 grouped feature relationships and WP2-P1 grouped personal evaluation

**Updated 29 October 2026.** Research only on the isolated branch
feat/general-pairwise-similarity-research. The binding three-workstream
strategy remains [the unified roadmap](similarity-three-workstreams-strategy-20261029.md).
No data from a private song library have been read for these experiments.
No real correlations, improved similarity metric, personal training,
new human ratings or deployed Lyrion control are claimed. Draft PR #16,
bliss-learner, BlissMixerLab, main, original ratings and previous native
100-song comparisons remain unchanged.

## Reusable anti-leakage contract for WP2 and WP3

New [deterministic grouped splitter](../scripts/research_grouped_split.py):
song rows carry a unique opaque track identity and an explicit
artist_group, album_group and recording_group. The algorithm builds
connected components: any songs sharing artist, album or recording
belong together. For personal survey triplets, all three tracks of
each recorded odd-one-out vote are also connected. Each component
is assigned in its entirety to training or holdout; a target holdout
fraction is approximate because groups cannot be broken.

If there is a single component, a partition is empty, required group
metadata are missing, or a triple crosses partitions, the split
**fails closed**. No fallback to a track-random or triplet-random
partition. This avoids a common flaw of the original learner:
random survey-triplet splits do not ensure independent artists,
albums, tracks, recording families or repeated judgments.
The function returns row/triplet indices and aggregate counts, not
track metadata. These partitions are not independent of upstream
Essentia training unless separately audited.

## WP3-R1: train-selected Spearman/Pearson relationships

New [in-memory evaluator](../scripts/research_feature_relationships.py)
takes permissioned paired 23D Bliss, 87D Genre and 56D Mood/Theme
feature rows with explicit grouping metadata. It checks dimensions,
finite values and head range, creates the above grouped holdout,
and estimates **Pearson** and tie-aware **Spearman** correlations
on training data separately for every Bliss-by-head coordinate pair.

- Genre: 23 x 87 = 2,001 exploratory feature/teacher pairs.
- Mood/Theme: 23 x 56 = 1,288 such pairs.
- Undefined/constant feature pairs remain undefined; there is no
  zero filling, automatic significance claim or p-value fishing.
- Up to five strongest associations are selected **exclusively by
  absolute training Spearman** and then evaluated on the untouched,
  group-disjoint holdout. The holdout may not change the selection.
- The report contains only task names, Bliss column names,
  Essentia class *indices* (labels require separately verified
  ordered model metadata), train/holdout coefficients, counts and
  scientific limitation flags. It has no song identifiers, raw
  feature vectors, private paths, comments or personal preferences.
- Reported associations concern *Essentia model outputs*, not an
  externally certified genre/mood ground truth. High correlation
  does not imply that a learned Bliss-only metric improves musical
  similarity.

The R1 code is a statistical infrastructure gate, not an
execution against the user's library. No new real measured
correlation coefficients exist yet. Multiple-comparison adjustments,
partial correlations, CCA, PLS, group bootstrap, confounder analysis,
student-to-teacher predictions and learned Bliss transformations
are **future separate experiments**. Any fitted preprocessing and
hyperparameter selection must remain inside training folds and
be independently validated on artist-/album/source-disjoint music.

## WP2-P1: reuse the legacy Bliss learner safely

New [grouped triplet protocol](../scripts/research_personal_triplet_protocol.py)
uses the current Lab survey order [similar1, similar2, odd], exactly
the existing 23 Bliss columns, and the legacy 23 x 23 Mahalanobis
matrix format from chrober/bliss-learner. It computes held-out
odd-one-out accuracy of the **raw 23D Euclidean baseline**, with
ties and abstentions counted as incorrect.

If a caller supplies an existing learned matrix, the adapter
checks structural compatibility, all finite values, symmetry
and approximate numerical positive semidefiniteness. It then uses
the original quadratic distance formula to score the same
group-disjoint holdout. It **requires** an explicit assertion that
the matrix was trained on exactly the selected training-triplet
indices, never on the full set.

**Crucial limitation:** this assertion is not independent evidence
that the original training process respected the split. The original
unmodified learner's final matrix is retrained on all input
triplets and is therefore **unsuitable for evaluating the same
triplets as a fresh holdout**. Any matrix evaluation remains
descriptive and marks actual training provenance as unverified.
The new code **does not** fit a model, change Lab survey
behaviour or imply a validated personal improvement.

The Personal score blend remains a **different layer** than
the existing Lab learned-versus-variance-matrix blend. Any
0-100% General/Personal blending still requires independently
compatible calibrated similarity scores and a valid model, as
specified by [WP2-P0](bliss-essentia-join-personal-contracts-20261029.md).
Absent or invalid Personal models always fall back to the
General score for the complete candidate cohort.

## Verification and next work

Three new synthetic test modules cover group disjointness,
artist/album/recording and triplet links, fail-closed single
components, known positive/negative Pearson/Spearman
relationships, constant values, private aggregate output,
correct Mahalanobis distance, malformed/indefinite matrices
and rejection of an explicitly full-survey-trained matrix.

They run in the Linux/Windows
[WP2-WP3 contract workflow](../.github/workflows/research-bliss-personal-contracts.yml)
alongside the previous read-only join, blend and baseline
regressions; no audio/model download or user-supplied files
are required.

**Next steps:** WP3-R2 design a private, permissioned paired-data
protocol with real album/artist and recording identities and
fit-on-training-only correlation controls, followed by regularized
CCA/PLS and Bliss-only geometry tests. WP2-P2 plan an
explicit group-aware invocation of the existing Rust learner
with a frozen train-only triplet manifest and a separate
validation report. Independent personal data remain optional.
Do not request any additional compulsory listening tests.
The prior global-fusion MTT CI did not produce results due
to a publisher HTTP-range timeout, not a measured metric failure.
