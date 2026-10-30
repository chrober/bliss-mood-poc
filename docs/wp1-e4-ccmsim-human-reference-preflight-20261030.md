# WP1-E4: CCMSim real human-similarity reference preflight (30 Oct 2026)

## Completed reproducible source audit

[GitHub Actions run 41069144899](https://github.com/chrober/bliss-mood-poc/actions/runs/41069144899) succeeded: offline synthetic safety tests on Linux and Windows, followed by real public **metadata-only** collection and Git blob integrity verification. [Aggregate-only artifact](https://github.com/chrober/bliss-mood-poc/actions/runs/41069144899/artifacts/12984851272).

Research source: [Cross-Cultural Music Similarity](https://github.com/pxaris/CCMSim) by Papaioannou, Benetos and Potamianos, [TISMIR 2026](https://doi.org/10.5334/tismir.341). Exact upstream commit: `eff8ab428dd12f1973548d657928b5211dd290bb`. Public human aggregate Git blob: `dd1f026ca72cc1616a7a7cdebd333d869d6c6720`; clip mapping blob: `0921898a7920858db0472ed11bc222578f80d834`. Original published human annotation data are CC BY 4.0, but the audio belongs to its original sources and has separate legal/access requirements. No source audio or model has been fetched, inferred, cached or published.

Strict [metadata auditor](../scripts/audit_wp1_e4_ccmsim_metadata.py), [offline safety tests](../tests/test_audit_wp1_e4_ccmsim_metadata.py) and [research CI](../.github/workflows/research-wp1-e4-ccmsim-metadata.yml) inspect only two small upstream CSV files and publish sanitized aggregate counts. Individual response files, artist/song paths, pair IDs, embeddings and local user data are not published.

## Verified real source counts

| Provenance and quality dimension | Verified result |
| --- | ---: |
| Human similarity pairs | **1,130**, all unique |
| Published study participants | **125** |
| Total judgments in aggregate count fields | **1,250** |
| Pairs judged once | **1,052 (93.10%)** |
| Pairs judged 2 / 3 / 4 / 5 times | 48 / 22 / 4 / 4 |
| Audio clips used by evaluated pairs | **463** |
| Published source clip mapping entries | **486 = 54 per source x 9 sources** |
| Source README description | **468 = 52 x 9**, **18 fewer** than actual mapping |
| Pairs between different source datasets | **1,018 (90.09%)** |
| Pairs within one source dataset | **112 (9.91%)** |
| Connected components of annotated-pair graph | **2** |
| Largest connected clip component | **445 of 463** |
| Values for three published human objectives | All in 0..1 |
| Actual same-clip Essentia or Bliss scores | **Not available** |
| Any new General Metric test or selected winner | **No** |

Source datasets: MagnaTagATune, FMA-medium, CorpusCOFLA, Arab-Andalusian, Lyra, Turkish-makam, Hindustani, Carnatic and Jingju. Distinct human objectives are **overall musical similarity**, **cultural similarity**, and **recommendation level**. Do not combine these into one label or assume recommendation level captures the direction of a playlist transition. The source README's 52/468 statement and the pinned 54/486 mapping disagree: this is a recorded provenance discrepancy, **not** a correction to either upstream file.

## Decision and actual evidence limits

This is a promising new **independent human annotation source** for testing how general pairwise similarities behave across musical cultures. It is **not a finished test of our features or scorer**. The considerable fraction of single-annotator labels, 90% cross-dataset pairs, and near-giant connected song-pair graph make the original labels especially vulnerable to annotation noise, culture/source cues and non-independent pair-level train/test partitions. No artist/album grouping, exact underlying audio identity, or pretrained-model recording independence has been verified. FMA-medium is not automatically the identical FMA-small cohort evaluated in previous work.

A sound future protocol should (1) keep the three human objectives distinct; (2) preregister the original *globally comparable, label-free* General cosine and fixed fusion methods; (3) establish exact audio identity, licenses and 20-second segment bounds for each eligible source recording; (4) use song/artist-disjoint splits with crossing edges excluded rather than treating random pairs as independent; (5) report covered vs skipped pairs, source strata, single-rater limitations, and appropriate clustered uncertainty; and (6) reserve a genuinely independent final evaluation where feasible. Do not claim a new p-value, metric improvement or quality winner until the necessary **same-recording features** have actually been obtained lawfully and evaluated.

**Next WP1 feasibility gate:** Determine lawful audio access and reliable exact-clip provenance on a bounded, predeclared subset, with no audio download or source-publication as part of this preflight. If rights and group independence are inadequate, reject this reference for production-quality inference. Existing human MTT 193/293, FMA VALIDATION and DEAM VA benchmarks remain separately valid exploratory channels; original full MTT new global pair-fusion is still source-blocked at 7/30 checks; FMA official TEST stays untouched. WP2 Personal Metric Learning and WP3 teacher reconstruction remain separate. No new operator listening, source DB modifications, native scan, PR #16, main, or Lyrion production changes.
