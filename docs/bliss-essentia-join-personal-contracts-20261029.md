# WP3-R0 Bliss / Essentia read-only joins and WP2-P0 personal scoring contracts

**Status (29 October 2026): research implementations and synthetic tests, NOT a deployed Lyrion feature or a real user-data evaluation.**

Canonical strategy: [three parallel workstreams](similarity-three-workstreams-strategy-20261029.md). Both implementations are isolated on the general-pairwise-similarity-research branch. Draft PR #16, upstream Bliss Mixer, bliss-learner, BlissMixerLab, existing audio, measurements and the successfully completed native 100-song comparison remain untouched.

## WP3-R0: join and coverage inventory

**Code:** [audit_bliss_essentia_join.py](../scripts/audit_bliss_essentia_join.py).

**Verified Bliss source:** chrober/bliss-learner, src/main.rs, FEATURE_COLUMNS. Exactly 23 columns are required in this order: Tempo, Zcr, Mean/StdDev SpectralCentroid, Mean/StdDev SpectralRolloff, Mean/StdDev SpectralFlatness, Mean/StdDev Loudness, and Chroma1 through Chroma13. The source is an existing Bliss TracksV2 table. The script opens SQLite using mode=ro and PRAGMA query_only=ON; it never creates a missing source DB.

**Verified Essentia source:** the current schema-v3 feature_models and feature_tracks tables with model-versioned Genre 87D and Mood/Theme 56D heads. The pre-existing, tested head decoders and catalog selectors are reused. For sampled songs, the audit also requires both heads to agree on input-audio SHA256, patch count, preprocessing and encoder model/checksum. The stored classifier outputs remain experimental predictions, not musical truth.

**Identity:** exact binary-equal TracksV2.File versus feature_tracks.track_file. Missing keys, ambiguous duplicate keys, invalid Bliss values and cross-head provenance conflicts are separate aggregate counters. Neither rowid nor artist/title/basename nor case-insensitive path matching is accepted. Identical file keys do not establish byte-for-byte equal audio between Bliss and Essentia: the historic Bliss database has no matching independent audio-hash contract here.

**Bounded execution:** a deterministic reservoir sample of 1 to 300 songs (default 100) from all compatible stored head pairs. Sample size and the full eligible head count are reported. The Bliss and Essentia inputs are read-only; no scanning, ONNX, audio decoding, worker execution or Lyrion playlist operation occurs.

**1280D embeddings:** an optional existing sidecar directory can be provided. Its JSON files are validated using the existing pinned research format, exact SHA256-hashed file keys, per-track audio checksum, shared encoder, 1280D normalization, pooling, patch count and representation fingerprint. With no directory, coverage is explicitly NOT ASSESSED, never reported as zero missing. This parser describes the original experimental sidecar format: a new native-backend format must be independently inspected and versioned, not silently coerced. With an explicit directory, valid/missing/incompatible embedding counts are measured among already validated Bliss + Genre + Mood rows.

**Privacy:** only nonidentifying counts, dimensions, version/status flags and sampling settings leave the function. No song identifiers, artist/album metadata, vectors, hashes, input paths, personal judgments or local URLs appear in the report. The CLI either prints aggregate JSON to stdout or creates an entirely new explicitly selected output file and refuses overwrite. Error messages intentionally omit user song paths. No actual user library has been read in this research implementation.

**Current limitations:** this is **a source/coverage readiness gate**, not a complete paired statistical dataset and not an experiment comparing musical similarities. Proper R1 correlation/CCA/PLS research requires approved private paired vectors, recording-level identity checks, user-independent or grouped artist/album/source partitions, missingness assessment, permission to process dataset audio/features and an independent musical-quality reference. The original 100-song cohort is adequate for an initial join smoke, but not for a generalizable model claim.

## WP2-P0: General / Personal contract and learner compatibility

**Code:** [general_personal_blend_contract.py](../scripts/general_personal_blend_contract.py).

**Versioned scoring design:** every eligible query always has a complete, finite, bounded General score vector. A user-requested integer 0–100% sets the influence of a separately produced Personal vector only when a compatible version, profile, feature fingerprint, calibration contract, exact candidate cohort and positive prior quality and calibration gates all agree. Complete Personal scores are mandatory across the candidate cohort. A missing, stale, corrupted, uncalibrated or partially covered Personal model causes one deterministic **whole-query General fallback** with 0% effective Personal influence; the requested setting is retained and a reason supplied. Explicit 0% must preserve the unchanged original General scores; 100% is Personal only with all gates passed.

**Calibration qualification:** this module checks positive externally asserted quality and calibration gates and compatible identifiers; it **does not independently train or validate** a calibrator. Affine mapping into the same range is not by itself evidence of score comparability, and the runtime must never assume a raw Bliss Mahalanobis distance can be directly averaged with Essentia cosine.

**Verified reuse targets:** chrober/bliss-learner writes a version-1, 23-by-23 learned matrix with 529 scalar entries in a top-level m object. The inspector validates **structural JSON format only**. It explicitly does not certify PSD, feature order/normalization, predictive quality or general-personal calibration, and must not activate a personal model. The existing BlissMixerLab survey stores three ordered track keys as [similar_1, similar_2, odd]; its legacy inspector returns only valid/invalid/duplicate counts without exposing the track keys. Existing learned_blend is a learned-versus-variance **Bliss matrix** control in the adaptive mixer and is NOT the new General/Personal slider. Existing per-triplet random folds do not certify song/artist/album-disjoint validation.

**Not yet implemented:** personal training or a Lyrion UI, opt-in preference survey changes, model-calibration fitting, grouped user holdouts, learning curves, independent held-out personal quality improvement or a deployed plugin. No additional mandatory manual listening is introduced; the twelve prior pair judgments remain completed exploratory diagnostics, not a new learning set.

## Synthetic verification and next experiments

- [WP3 join tests](../tests/test_audit_bliss_essentia_join.py): exact 23D source schema, read-only bytes, case sensitivity, missing/duplicate/invalid tracks, head provenance mismatch, optional valid/missing/tampered sidecars, bounded sampling, private aggregates and refusal to overwrite.
- [WP2 blend tests](../tests/test_general_personal_blend_contract.py): 0/25/50/75/100%, complete cohort fallback, wrong user, model version, stale feature/calibration/cohort, missing/nonfinite scores, invalid General, original learned matrix and triplet format.
- [Windows/Linux synthetic workflow](../.github/workflows/research-bliss-personal-contracts.yml): runs these contracts with **no public or private audio**, no model weight download and no user files; also preserves the earlier local-feature readiness regression.

**Next gate:** WP3-R1 prepare a group-aware, no-leakage analysis design for paired Bliss↔Essentia vectors and descriptive Spearman/Pearson/partial correlations, then regularized CCA/PLS and Bliss-only transformations on permissioned real recordings. WP2-P1 specify an independently held-out personal triplet protocol, low-parameter learner baseline and calibrated score contract. WP1 general-metric research continues, but an unavailable MTT source archive must not block WP2 or WP3.

**Local Windows rule:** any real library read must be separately delivered as one complete, verified, fail-closed automated PowerShell block using exact known paths, with no guessing of Bliss DB location, no source modifications and no private data upload.
