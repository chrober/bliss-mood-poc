# Scientific similarity-evidence roadmap and GitHub Actions runtime budget

**Date:** 2026-10-21. **Scope:** Draft PR #16 `feat/similarity-metric-evaluation`.
Status: **research design and official-source due diligence; no new dataset audio
workflow implemented or executed by this document**.

## Why another dataset?

We now have a corrected Rust-v5 feature extractor and exploratory benchmarks:
- FMA-Small 80 artist-unique validation songs, eight coarse genres, seven
  similarity metrics; successful aggregate-only GitHub Actions report in
  run 39583233757. Its **official TEST split is still reserved**.
- DEAM two separate 240-song validation samples using human mean valence/
  arousal ratings as a *mood-proximity proxy*, not direct pairwise musical
  similarity. A conservative artist/title overlap screen identified 75
  possible MTG-Jamendo catalog matches; matching is not proof of identical
  recording or train membership. Do not attribute metric changes between
  different samples to the filter.

Neither type of label alone establishes which scores yield pleasant music
transitions, general pairwise agreement or Lyrion playlist coherence.
We must separate **classifier validity**, **label-based retrieval**,
**human perceived similarity**, and ultimately **actual playlist quality**.

## MTG-Jamendo — classifier domain reference, not automatically independent

Official resources:
- https://github.com/MTG/mtg-jamendo-dataset
- https://github.com/MTG/mtg-jamendo-dataset/tree/master/derived/music-classification-annotations
- https://essentia.upf.edu/models.html

The canonical repository describes 55,525 tracks in common split sets with
**87 Genre and 56 Mood/Theme labels**, matching our ONNX head dimensions.
These are uploader-supplied tags in the original corpus; class sparsity
and annotator/label noise are relevant. Official training/validation/testing
splits and the derived additional human music-classification annotations
(on split-0 test data) are useful.

**Evidence questions:**
1. Verify published ONNX model metadata and exact original split identity
   and the upstream Discogs embedding model provenance before calling any
   input "held out"; common dataset test split is not independently proven
   out-of-training for these particular weights.
2. Reproduce multilabel classification ROC-AUC / PR-AUC per head and label,
   with support, missing labels and macro/micro averages; do not treat
   sigmoid activation as a calibrated similarity probability.
3. Compare same-artist-excluded top-K retrieval and ranking scores against
   **reference tag sets** (e.g. per-query tag-set overlap), reporting
   label frequencies and classifier-domain self-reference as limits.
4. Optionally analyze **derived music-classification annotations** as a
   different human reference without silently equating taxonomies.
5. Verify out-of-dataset generalization on FMA Genre and DEAM VA; these
   are separate evidence channels and not directly comparable numbers.

**Operational plan:** Start with metadata/splits/model JSON only on GitHub
Actions, validate tag maps and train/test provenance, pin versions and hashes.
Select a bounded, artist-aware **research audio subset only if needed**.
Do NOT download the 46 GB low-quality Mood/Theme audio subset or 156 GB
low-quality general corpus into a standard runner by default. Official
download scripts use chunked archives and checksum verification; cap
downloads and disk. Avoid committing or uploading audio, private metadata
rows or per-track feature vectors.

**License:** Official MTG-Jamendo repository code: Apache-2.0; metadata:
CC BY-NC-SA 4.0; audio: individual Creative Commons licenses in
audio_licenses.txt. The maintainers state the dataset is solely for
non-commercial research/academic use; other uses require prior Jamendo S.A.
authorization. These research permissions must **not** be silently
assumed to cover shipping licensed recordings, a commercial product,
or public re-distribution as CI artifacts.

## MagnaTagATune — prioritized *direct human similarity* benchmark

Official sources:
- https://mirg.city.ac.uk/codeapps/the-magnatagatune-dataset
- https://mirg.city.ac.uk/datasets/magnatagatune/
- https://tagatune.org/details.html
- https://magnatune.com/terms_of_use

The City University mirror supplies **comparisons_final.csv** (~129 kB),
**clip_info_final.csv** (~8.2 MB), human tag annotations and three
split MP3 archives (~1 GB + 1 GB + 737 MB). Original dataset has
**25,863 short mono 16-kHz/32-kbps MP3 clips** and **533 triplet
similarity questions with ~7,650 votes** reported by its creators.
The game asks which clip of a triple is the *most dissimilar*; votes
can disagree. Similarity must not be silently relabeled as Genre or Mood
ground truth. Audio is lo-fi and short, so domain shift from full-song
Lyrion MP3s is material.

**First execute a cheap metadata-only preflight** (no audio):
1. Fetch comparisons_final.csv and clip_info_final.csv by exact
   official URL in a dedicated (manual/targeted) workflow. Preserve file
   hashes, validate column names, vote totals, duplicates, clip references,
   votes with ties/low consensus and candidate coverage. Fail closed when
   schema differs from expectations; do not invent file mappings.
2. Determine the actual **unique clips needed by voted triplets**
   (not all 25,863). Check clip→track→album/artist grouping and
   whether repeated excerpts, duplicates, disjoint splits or contradictory
   judgments need special treatment.
3. Freeze a development/holdout partition **grouped at original
   song/album/artist level** and record the sampling/consensus protocol.
   No metric optimization on held-out triplets.
4. Verify exact sound-file rights for the City-hosted dataset and the
   constraints of GitHub runner downloads/storage. The original
   TagATune page says the dataset is **CC BY-NC-SA 3.0** for
   non-commercial research, with generator scripts **GPL-v3**.
   The City-hosted research files and Magnatune music are not a
   blanket commercial license. Confirm applicable version, attribution,
   limits and whether use on public runners is within authorized
   non-commercial research before fetching audio. Never redistribute
   original clips through a public artifact.

**Audio phase only after provenance/licensing preflight:**
- Download the minimum legally accessible audio archive(s) and
  analyze **only distinct clips used in comparison questions**, using
  the separate pinned corrected Rust-v5 ONNX analyzer checkout.
- Report **triplet odd-one-out agreement**: for voted outlier C,
  S(A,B) should exceed both S(A,C) and S(B,C). Define tie/zero
  policies *before* seeing holdout; do not infer certainty from
  high cosine alone.
- Report both **unweighted majority-consensus accuracy** and
  **vote-distribution-weighted agreement**, disagreement/consensus
  strata, coverage/undefined scores, and simple baselines. Keep
  all seven methods and Genre/Mood heads separate. Group-bootstrap
  by original song/artist for uncertainty; test metric differences
  paired on the **same** comparisons. If training provenance cannot
  exclude potential Discogs encoder overlap, say so.
- This is stronger evidence for **general perceptual similarity**,
  but not direct evidence of independent Genre- or Mood-specific similarity,
  nor of smoothness between adjacent Lyrion songs.

**Research priority:** MagnaTagATune metadata validation first
(high information / negligible cost); in parallel, MTG-Jamendo
metadata and model-split provenance; then a bounded, compliant
MagnaTagATune clip experiment. Afterwards independent FMA TEST
only with predeclared hypotheses and metrics, and eventually real
playlist-listening/transition tests.

## GitHub Actions runtime quality budget — for *every* new benchmark

Every audio workflow report and run log should include:
- run and source/model revision hashes; runner OS, CPU count, free disk
  before/after, maximum resident memory when feasible;
- elapsed seconds for **checkout, Cargo build/cache, ONNX model download,
  reference metadata/audio download, decode/preprocessing/ONNX analysis,
  scoring, and artifact upload**, plus total workflow time;
- songs processed, patches or duration analyzed, throughput
  (songs/min), worker count, ONNX threads per worker, failure counts,
  undefined/abstained metric scores, dataset/model SHA hashes.

**Avoid unnecessary work by default:**
- Follow PR #16's **single push, path-filtered** general Rust vs
  Python/PowerShell CI and keep expensive external audio benchmarks
  manual/limited, never accidentally triggered by README/docs edits.
- Run metadata-only schema/rights/gold-label preflight *before*
  expensive archives. Do not download whole catalogs when a small
  annotated subset is enough. Use ZIP member streaming, safe
  checksum-verified chunks, scratch-space limits and delete
  temporary extracted clips as soon as analyzed.
- Cargo dependency/build caching is established; pin Cargo.lock from
  the separate Rust-v5 checkout and ONNX/file hashes. Do not cache
  raw licensed dataset audio in public GitHub caches or artifacts by
  default. Shared model cache is conditional on its license/access.
- Existing FMA 80-song workflow had ~3m39s archive download and
  only ~42s audio preprocessing/inference on the 4-CPU runner;
  optimizing workers **alone** cannot remove the download bottleneck.
- Benchmark a safe *serial baseline* against fixed 2-worker
  inference only after deterministic, isolated-sidecar or
  single-writer merging semantics; **do not** concurrently
  persist from multiple per-file processes into one SQLite file
  without specific contention/race tests. Adaptive workers are
  currently available in `scan-features`, **not** in the
  external benchmark's sequential `analyze-features` loops.
  Measure same songs, same models, byte/float parity, walltime,
  peak RAM and SQLite integrity first. Four GH runner vCPUs
  do not justify copying max_workers=8 from desktop benchmarks.
- Emit an actionable, compact performance comparison alongside
  quality metrics after each meaningful infrastructure change.
  Optimize only measured bottlenecks. No invented speedups.

## Release gates and future decision

Choose **no** production similarity method from any single
pilot. Require concordant evidence from independent genre retrieval,
VA mood proxy and direct human triplet judgments, stable coverage,
robustness across corpus/artist groups, and a later blinded Lyrion
playlist study. Retain PR #16 Draft; no merges or alterations to
PR #13, PR #17, main, user audio or original databases.
