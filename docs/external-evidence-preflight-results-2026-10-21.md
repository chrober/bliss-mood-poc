# External evidence preflights: MTG-Jamendo and MagnaTagATune

**Completed 2026-10-21**, branch `feat/similarity-metric-evaluation`,
Draft PR #16. No audio downloaded or scanned. No production metric selected,
no changes to PR #13, PR #17, main, private user music or DB.

## MTG-Jamendo: publisher splits and Essentia 87D/56D model heads

**PASS** — [GitHub Actions run 39586686845](https://github.com/chrober/bliss-mood-poc/actions/runs/39586686845),
[aggregate-only report 12339596333](https://github.com/chrober/bliss-mood-poc/actions/runs/39586686845/artifacts/12339596333).

Official source commit for MTG-Jamendo metadata:
`cafd8e20c265ed84f1e61f1c875327971f43a62f`.
Six split-0 genre/moodtheme TSVs downloaded and checked against official
upstream Essentia JSON model metadata. The test verifies **identical
vocabularies**, not just the count of classes. Track and artist IDs
are disjoint between official training, validation and test subsets
within each head.

| Head | Classes | Training | Validation | Test |
| --- | ---: | ---: | ---: | ---: |
| Genre | 87 | 32,572 | 11,043 | 11,479 |
| Mood/Theme | 56 | 9,949 | 3,802 | 4,231 |

This is evidence that the published catalog's official split-0 and
head JSON metadata are structurally aligned. It is **NOT proof that these
were the exact training/test splits used for a specific published
ONNX weight file**, does not reproduce its published ROC-AUC/PR-AUC,
and does not establish that the independent Discogs-EffNet encoder
did not see the same audio. Genre and Mood/Theme tags are multilabel
uploader-provided categories, not direct song-pair listening ratings.

The auditor [scripts/audit_mtg_jamendo_models.py](../scripts/audit_mtg_jamendo_models.py)
performs a fail-closed comparison, collects per-class tag counts
and metadata hashes, and outputs aggregate-only JSON. Corresponding
synthetic Linux/Windows tests run in general Python CI. Workflow:
[mtg-jamendo-metadata-audit.yml](../.github/workflows/mtg-jamendo-metadata-audit.yml),
which is branch-scoped and not triggered by documentation edits.

Observed pure metadata audit: **0.31 seconds, ~27 MB peak RSS** on
GitHub Actions. Downstream work should first inspect the separate
official **Music Classification Annotations** (split-0 test)
and verify exact annotation and training provenance without downloading
the 46--156 GB upstream audio collections.

## MagnaTagATune: direct human odd-one-out votes

**PASS** — [GitHub Actions run 39587323227](https://github.com/chrober/bliss-mood-poc/actions/runs/39587323227),
[aggregate-only report 12340976176](https://github.com/chrober/bliss-mood-poc/actions/runs/39587323227/artifacts/12340976176).

Official host: https://mirg.city.ac.uk/datasets/magnatagatune/ .
The archive hosts `comparisons_final.csv` and `clip_info_final.csv`
independently of roughly 2.7 GB of 3-part music audio archives.
**No audio was downloaded.**

Verified original CSV schema:
- Each comparison has clip1/2/3_id, clip1/2/3_numvotes,
  and clip1/2/3_mp3_path. The vote columns count human selections
  of a clip as the **odd-one-out** in a triple.
- Clip metadata provides clip_id, track_number, title, artist, album,
  segment time, URL and MP3 path. **31,382** catalog rows,
  **5,519** lacking an MP3 path; this leaves **25,863** with a
  catalog MP3 path, not a guarantee of archive presence.

### Real vote distribution

| Measured characteristic | Result |
| --- | ---: |
| Triplets | **533** |
| Total human votes | **7,650** |
| Unique clip IDs / MP3 paths needed for all triplets | **1,019** |
| Distinct original song groups in comparisons | **903** |
| Distinct artists in comparisons | **214** |
| Distinct artist-album groups | **399** |
| Questions with tied top vote count | **87** |
| Questions with absolute majority (over 50%) | **371** |
| Questions with a unique choice at least 70% consensus | **228** |
| Unanimous questions | **160** |
| Questions with two excerpts of the same apparent original song | **1** |
| Questions with two clips by the same artist | **10** |
| Questions with two clips from the same artist/album | **4** |

Zero vote-less questions. The proportion of individual human votes
that agree with the majority winner (oracle majority reference) is
**0.6034**. This is a descriptive human disagreement measure,
**not a model score** or an upper bound on every possible performance
metric. A random odd-one-out choice would agree with a human
individual vote in expectation 1/3; comparison of majority-vote
triplet accuracy uses a different denominator.

**Important:** 87 tied triples have no uniquely determined
majority winner. Do not silently break the ties using a clip ID or
the algorithm's preferred outcome. The high-consensus subset
(228 questions with unique >=70% winner) offers a clear exploratory
starting point, but selecting it changes the task distribution.
For official test/holdout and uncertainties, group by original
artist/album/song before any scoring; abstain and report zero-overlap
or tie cases per metric.

Actual metadata processing runtime: **0.45 seconds / 31 MB peak RSS**
for schema inventory and **0.19 seconds / 46 MB peak RSS**
for full vote/clip join on the Actions runner. No need for
parallel worker orchestration for this metadata phase.

### Source rights and next gates

[Original TagATune terms](https://tagatune.org/details.html) state
**CC BY-NC-SA 3.0** for the dataset and GPL-v3 for scripts;
it is expressly a noncommercial research distribution. The City MIRG
archive is hosted with permission of the original authors.
The license does **not** automatically grant commercial redistribution
of music in the eventual Lyrion product.
Do not commit or upload licensed audio, raw clip metadata/paths,
human per-clip votes or generated track vectors as artifacts.

Code: [scripts/inspect_magnatagatune_metadata.py](../scripts/inspect_magnatagatune_metadata.py),
[scripts/audit_magnatagatune_votes.py](../scripts/audit_magnatagatune_votes.py),
[.github/workflows/magnatagatune-metadata-audit.yml](../.github/workflows/magnatagatune-metadata-audit.yml).
Python CI includes independent Linux/Windows synthetic tests.

Next planned work: clip-archive membership preflight and
license-compatible, bounded Rust-v5 analysis of those **1,019**
needed clips, not all 25,863 tracks. The three published ZIP
parts may still need to be downloaded together; check content
layout, checksums, disk budget and staging before paying that cost.
Use direct triplet odd-one-out agreement for both model heads
and all seven metrics, with vote-distribution-weighted agreement
and artist-grouped uncertainty. No unregistered use of the held-out
triplets or arbitrary forced best metric.

## GitHub Actions runtime policy

Metadata-only quality gates precede large audio downloads.
Use only once-per-commit and relevant-path workflow triggers;
no Rust build if the change is documentation or Python-only.
Each future audio run records checkout/build/model/audio download,
inference, scoring, artifact upload, worker count, CPU, memory and
song throughput separately. The existing `analyze-features`
loop is serial with `--threads 1`; adaptive scan workers are not
automatically active in external dataset jobs.
See [GitHub Actions trigger/worker audit](github-actions-trigger-and-worker-audit-2026-10-21.md)
and [external evidence roadmap](similarity-external-evidence-roadmap-2026-10-21.md).
