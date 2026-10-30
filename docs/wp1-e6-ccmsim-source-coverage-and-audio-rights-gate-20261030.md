# WP1-E6: actual CCMSim source-access and rated-pair coverage ceilings (30 October 2026)

## Real measured results; no licensed audio was accessed

**Completed**: [GitHub Actions 41072601751](https://github.com/chrober/bliss-mood-poc/actions/runs/41072601751), Linux and Windows fictional regressions PASS, and genuine pinned public aggregate CCMSim source-pair replay PASS. [Strict auditor](../scripts/audit_wp1_e6_ccmsim_source_coverage.py), [synthetic privacy tests](../tests/test_audit_wp1_e6_ccmsim_source_coverage.py), and [workflow](../.github/workflows/research-wp1-e6-ccmsim-source-access.yml) read exactly two upstream public CC BY 4.0 metadata/aggregated-label CSVs, with Git blob verification on fixed upstream commit `eff8ab428dd12f1973548d657928b5211dd290bb`. No original audio source was probed, downloaded, decoded or scored; no human similarity value, clip ID, track path, recording, private votes or person-level response was included in the output.

This is an **upper bound on potentially usable human-rated pairs**, *assuming* that all rated clips from the named audio sources could be retrieved lawfully with exact 20-second clip parity. No actual recording availability, track-level license, rights/redistribution or same-recording model feature coverage was proven.

## Source combination feasibility ceiling

| Hypothetically accessible complete source set | Distinct annotated clips | Human annotated pairs (upper bound) | Pairs annotated by one person | Replicated pairs | Within-source pairs | Cross-source pairs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| FMA-medium only | 51 | **11** | 10 | 1 | 11 | 0 |
| MagnaTagATune only | 51 | **10** | 9 | 1 | 10 | 0 |
| Lyra only | 51 | **12** | 12 | 0 | 12 | 0 |
| FMA-medium + MagnaTagATune | 102 | **46** | 41 | 5 | 21 | 25 |
| FMA-medium + Lyra | 102 | **46** | 45 | 1 | 23 | 23 |
| MagnaTagATune + Lyra | 102 | **47** | 45 | 2 | 22 | 25 |
| FMA-medium + MagnaTagATune + Lyra | 153 | **106** | **100** | 6 | 33 | 73 |
| All nine sources | 463 | **1,130** | 1,052 | 78 | 112 | 1,018 |

All nine original source-pair categories for within-source pairs and all 36 between-source categories appear in the pinned aggregate. The nine documented original corpus source labels and per-source 54 mapping rows/51–52 used rated clips are preserved; there is still a mismatch with the original CCMSim README's 52 sampled clips per corpus (468) versus 54 pinned mapping rows per corpus (486). Do not reconcile this mismatch by assuming 18 absent tracks.

The fixed source combinations are descriptive engineering options, not an optimized subset selected from human scores. Only the pair endpoints, corpus IDs and annotation *counts* were used; changing the original human similarity values while preserving valid schema does not change the coverage results.

## Rights and exact-recording availability: desk review of publisher source documentation

This is a **documentation-only** appraisal, not a legal opinion or a contractual grant. The CCMSim authors explicitly say that third-party audio is *not redistributed*. Their **published human annotations** are CC BY 4.0; original sound recordings retain independent rights.

- **FMA-medium:** [FMA original repository](https://github.com/mdeff/fma) documents a separately downloadable ~22 GiB 25,000-track medium audio archive and public metadata. It does NOT mean the audio recordings are licensed under the repository code's MIT license. Recording-level terms follow each artist/track; [Library of Congress FMA rights advisory](https://www.loc.gov/item/2018655052/) distinguishes the code MIT license, CC BY 4.0 metadata and individual audio rights. E6 did not download FMA audio or inspect individual track licenses. The 11 FMA-only human pairs are **too few** for a robust independent General Metric benchmark, though a limited lawful technical smoke test might be possible later.
- **MagnaTagATune:** [Official dataset link via CCMSim](https://github.com/pxaris/CCMSim#datasets) and our [original WP1-E2 sparse source transport test](wp1-e2-mtt-source-and-cache-diagnostics-20261030.md) establish that only 7 of 30 repeated original clip-member requests passed before a transport failure. This is not stable mass access and does not grant redistribution rights. Ten within-source CCMSim human pairs would be the **upper bound**, not an accessible benchmark.
- **Lyra:** [Lyra authors' repository](https://github.com/pxaris/lyra-dataset) provides timestamped YouTube references, not a general blanket permission to collect or redistribute sound recordings; the published Lyra **metadata** is CC BY-NC-SA 4.0. Original per-video rights, availability and exact segment parity must be established before any clips are acquired; no YouTube extraction was attempted. Lyra contributes at most 12 within-source human pairs.
- **CorpusCOFLA:** CCMSim's [source table](https://github.com/pxaris/CCMSim#datasets) lists the original audio as **upon request**. No approval has been obtained or assumed.
- **Arab-Andalusian, Turkish-makam, Hindustani, Carnatic and Jingju:** CCMSim lists original **CompMusic/Dunya registration-based** access. Registration is not a copyright or publication permission; access, source track identity and research use terms have not been verified.

There is no basis to merge source audio licenses, silently use a substitute mirror, publish an audio cache in GitHub Actions, or infer a legal grant from the CCMSim CC BY 4.0 human annotation files. The original CCMSim cohort uses **20-second exact source segments**, whereas FMA-medium source tracks are generally 30-second examples; exact signal parity is an additional gate. The CCMSim mapping paths provide identifiers but neither authenticated content hashes nor a proven artist-/album-/recording-disjoint split.

## Decision and next genuinely useful technical step

**WP1-E6 SOURCE COVERAGE: PASS; AUDIO/RIGHTS/EXACT RECORDING PARITY: NOT VERIFIED.**

1. Do not spend resources collecting 153 clips merely to recover 106 mostly once-rated pairs across three culturally restricted or technically unreliable sources. This would not yet demonstrate a robust General Metric.
2. The next useful evidence **already exists without new audio**: the CCMSim authors have published the original per-pair results for **eleven third-party audio-model and MIR baselines**, in `data/combined_similarities.csv` (pinned Git blob `b0d475c6f58f5d0ec2fbdeaaca57d87f472a2c3d`). These may be audited as **published model benchmarks**, not relabeled as our Essentia/Bliss results. See [WP1-E7](wp1-e7-ccmsim-published-baselines-20261030.md).
3. Freeze any future **ours**: overall human musical similarity primary objective, separate cross-culture and within-culture endpoints, explicit clip/artist grouping, source license/20-second fidelity and preprocessing, same-track model vectors for every comparator, and transparent skip counts before touching more audio or human labels. CCMSim's 1,052 single-rater pairs and near-giant graph still create uncertainty.
4. WP1 remains the independent General Metric research objective. [WP1-E5](wp1-e5-ccmsim-clip-disjoint-split-feasibility-20261030.md) showed only 40 test pairs survive the frozen train/validation/test clip-disjoint split; do **not** fit Personal or General mixing weights on this source and then claim holdout superiority. Keep [earlier real one-listener 11-song-pair local pilot](wp1-e3-local12-stability-real-results-20261030.md), MTT 193/293 and FMA/DEAM task evidence separate and exploratory; MTT four global fusions remain unmeasured. FMA official TEST untouched, WP2 optional Personal and WP3 Essentia teacher reconstruction separate, no Lyrion, PR #16 or `main` changes.
