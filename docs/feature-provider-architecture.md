# Model-independent features and future mixing strategies

**Update 21.10.2026:** Die bestehenden separaten 87D/56D-Kopfvektoren sind nur **eine** mögliche Song-Repräsentation. Direkte **1280D-Discogs-EffNet-Embeddings** (vor den Klassifikationsköpfen) und **kalibrierte Kombinationen aus Embedding/Genre/Mood** sind gleichberechtigte, noch nicht implementiert/evaluierte Forschungsansätze. Der Encoder liefert den 1280D-Patch-Vektor intern, das aktuelle schema-v3-Feature-Sidecar persistiert ihn aber nicht als Song-Embedding. Minimaler Umsetzungsplan, Paritätsanforderungen, externe Beispiele und Abgrenzung zur hier diskutierten **Bliss-first/Mood-/Genre-first/Hybrid**-Kandidatenarchitektur: [Handover der drei Similarity-Repräsentationsansätze](similarity-three-representation-approaches-handover-2026-10-21.md).

## Current implementation (experimental)

The Rust proof of concept [bliss-mood-poc](../README.md) implements an
opt-in capability registry, one Discogs-EffNet audio/embedding pass, and
independent Sigmoid and Softmax classification heads for three registered models:

| Registry model ID | Capability | Classes | Encoder |
| --- | --- | --- | --- |
| moodtheme | mood_theme | 56 | Discogs-EffNet 1280D |
| genre | genre | 87 | Discogs-EffNet 1280D |
| voice | voice_presence | 2 (Softmax) | Discogs-EffNet 1280D |

A descriptor maps the model ID to a capability, trusted local weight filenames,
metadata and dimensional constraints. The generic scanner stores independent
vectors with exact model/preprocessing fingerprints; no model names or class
lists are hard-coded in the feature storage format. This is *head-agnostic
within a compatible encoder family*, not arbitrary support for MusicNN, VGGish,
regressors, or models whose output is not a supported Sigmoid/Softmax vector.

Genre, Mood/Theme and Voice/Instrumental remain different score spaces.
The per-head `output_type` controls validity checks and per-model aggregation
provenance: Sigmoid allows independent 0..1 labels, whereas Softmax requires
a normalized sum of approximately one across mutually exclusive classes.
The registry schema v2 makes this explicit; older v1 registries still default
to Sigmoid so existing custom model configurations remain readable. The system does not imply
that a score of 0.8 has the same probabilistic meaning for both models.

## Planned separation of responsibilities

Three distinct concepts must not be merged in the user-facing application:

1. **Feature source**: performs offline analysis and exposes versioned numeric
   descriptors for a local track (e.g. Bliss 23D, 87D Genre, 56D Mood/Theme).
   Providers declare *capabilities*, not hard-coded model names.
2. **Candidate source**: determines which eligible tracks are proposed for
   mixing (e.g. Bliss similarity, Genre/Mood proximity, or a union of both).
3. **Guidance/scoring source**: contributes bounded scores or preferences for
   candidates the selected strategy is considering (e.g. Bliss transition
   similarity, Mood/Theme anchor distance, Last.fm relationships, local
   listening statistics).

An overall **mixing strategy** decides candidate source(s), normalization,
soft/hard constraints, reranking, and variation. Common Lyrion membership,
repeat-window and playlist integrity rules remain in the host regardless
of the chosen strategy. Unavailable or unvalidated features must lead to
explicit, predictable fallback, not silently alter the candidate pool.

## Three product strategies under evaluation (no final decision)

- **Bliss-first (first integration experiment only)**: Bliss admits candidates based on acoustic similarity;
  compatible Genre/Mood signals may rerank only that candidate pool. This is
  feasible with today's Bliss Guidance SPI v2 after adding an opt-in feature
  provider. The existing SPI forbids external providers from admitting tracks.
- **Mood-/Genre-first** (feature-first): Genre/Mood descriptors generate
  candidates; Bliss provides transition similarity in the final scoring.
  This requires a new candidate-selection host contract. It must **not**
  silently reinterpret the existing Bliss-only eligibility semantics.
- **Hybrid**: candidate sources union or otherwise combine their proposals,
  then a coherent strategy evaluates transition quality, musical identity,
  preference, and diversity. Feature score scales must be normalized and
  calibrated rather than directly summed.


**Decision status:** All three approaches remain genuine competing
product options, not a sequentially predetermined roadmap ending with one
choice. Bliss-first was implemented first **only because current SPI v2
provides bounded reranking of Bliss's pool**, allowing evaluation of the
full feature→sidecar→guidance path without changing hard candidate
admission. This does **not** establish that Bliss-first is the best
algorithm: it can miss tracks with excellent Mood/Genre compatibility that
Bliss never proposed. Mood-/Genre-first and Hybrid require a new host
candidate-source contract and calibrated cross-source scoring; they
should be evaluated on the same frozen seeds, eligibility constraints,
candidate coverage, listening impressions, drift/diversity and Pi budget
before the product strategy is selected. See the detailed
[strategy decision record](lyrion-bliss-mood-genre-integration.md#mixing-strategy-decision-record--deliberately-open-2026-10-19).

Model selection and mixing strategy are separate user settings. A model can
declare capability genre without the UI needing to display its ONNX filename.
Capability alone does not make score semantics or taxonomies interchangeable;
mapping and calibration may be needed when another model is substituted.

## Drift protection as an orthogonal policy

Drift control should be available across strategies. It compares future
candidates to a frozen source identity (single or multi-track anchor), recent
mix history, and a selectable target preference. Genre consistency, mood
consistency and acoustic transition quality are distinct objectives; a
user-requested style transition should not be accidentally defeated by a
hardcoded starting-genre rule.

Compare four experimental conditions with fixed seeds and identical LMS hard
constraints: original Bliss, Bliss with existing dynamic/adaptive weighting,
Bliss with model-based guidance, and Bliss with both. Feature-first and Hybrid
should be evaluated separately once their candidate-selection contracts exist.

## Compatibility and boundaries

- Keep the original Bliss database read-only; never rewrite source audio.
- Preserve the legacy Mood-only CLI and sidecar rows while the feature path is
  evaluated. Writable schema v3 must not be used with v2-only binaries.
- Keep [Bliss Guidance SPI v2](https://github.com/chrober/bliss-playlist-guidance-spi/blob/main/SPI.md)
  unchanged and Bliss-first. A future strategy host must introduce its own
  candidate-source abstraction rather than mislabel a provider as a candidate
  generator.
- No modifications to production BlissMixer, BlissMixerLab or Better Call Bliss
  are part of this pull request.
- Numerical parity on synthetic files is **not** proof of useful predictions
  on music. Experimental/unvalidated flags remain false for production and
  users must evaluate real tracks before enabling automated playlists.

## Vocal characteristics and finer genres

`voice` currently distinguishes predominantly voice vs instrumental music.
It does **not** classify clean vocals, screams, growls, rap techniques or
singer timbre; those require models trained on the corresponding labels.
Song-wide average Softmax scores also cannot be interpreted as the proportion
of time containing voice.

The 400-label Discogs taxonomy would offer Black Metal, Post-Metal and
Psychedelic Rock categories for improved style matching. However, the
Discogs-EffNet head is officially hosted as a TensorFlow `.pb` without an
ONNX file in the official directory. This enhancement remains out of scope
until an independent conversion and TensorFlow-vs-ONNX parity gate pass.


## Active next phase (2026-10-19)

The concrete staged Lyrion integration contract is in
[lyrion-bliss-mood-genre-integration.md](lyrion-bliss-mood-genre-integration.md).
The **first Bliss-first experiment** reranks only the existing
acoustically eligible candidate pool via SPI v2 and preserves every upstream
hard constraint. This is an integration shortcut, **not** a product
decision against Mood-/Genre-first or Hybrid.
Exact `TracksV2.File` key mapping between Lyrion and the read-only feature
sidecar is the first unsolved implementation seam. Separate Mood/Genre
signals and an explicitly experimental opt-in preview come before any
feature-first or hybrid candidate admission. Platform resource tuning is
[deferred](platform-resource-roadmap.md).

## Next research axis (2026-10-21): Compare *representations*, not just metrics

The current seven metrics have been evaluated on already-pooled **87D Genre / 56D Mood/Theme classifier scores** only. The shared Discogs-EffNet model also internally provides **1,280D audio embeddings per patch**, but schema-v3 currently stores only the classifier heads. **No 1,280D song-level embedding baseline or multi-signal fusion has yet been evaluated.**

The next controlled experiment explicitly compares **A: per-head classification similarity**, **B: pooled direct 1,280D embedding cosine**, and **C: calibrated/rank-based task-aware fusion**, using identical clips and reference questions with strict cohort provenance. See [the canonical new-session handover](similarity-representation-comparison-handover-2026-10-21.md) for definitions, 1280D export/pooling design, reproducibility/parity gates, external Essentia/cosine.club precedents, CI costs, ground-truth caveats and prioritized implementation. Do not confuse fusion of similarity signals with Lyrion's separate Bliss-first / Feature-first / Hybrid candidate-admission strategy choice. Official FMA TEST remains unexamined, full MTT is exploratory, and no production choice has been made.
