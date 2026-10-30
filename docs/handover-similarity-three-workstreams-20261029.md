# Handover: Lyrion General + Personal + Bliss↔Essentia research (29 October 2026)

> **LATEST WP1-E6/E7 REAL CCMSim SOURCE FEASIBILITY + THIRD-PARTY BASELINE REPLAY — 30 OCT 2026:** The previously completed E4/E5 human-reference and clip-disjoint analyses are extended by two **successful real-data** CI workflows on this research branch. [WP1-E6 source-coverage/rights gating](wp1-e6-ccmsim-source-coverage-and-audio-rights-gate-20261030.md), [CI 41072601751](https://github.com/chrober/bliss-mood-poc/actions/runs/41072601751) PASS (Linux/Windows tests + real SHA-pinned original CCMSim aggregates): FMA-medium only 51 clips/11 human-rated pairs, MagnaTagATune 51/10, Lyra 51/12, FMA+MTT 102/46, all three 153/106 of 1,130; **100/106 triple-source pairs have only one rater**. Numbers are STRICT THEORETICAL UPPER BOUNDS IF all original exact 20-second clips can be accessed lawfully; zero rights, actual audio availability, original features or song-fingerprint parity were established. FMA repository MIT license does **not** cover each sound recording; per-track licenses apply, MTT original 7/30 repeated Range access failed, Lyra uses YouTube-ID recordings and CC BY-NC-SA metadata, CorpusCOFLA request and other CompMusic source registration are no blanket copyright grants. **No audio download or source access bypass.** Crucially, E6 located the authors' already-published *pair-level model score table*, enabling [WP1-E7 external third-party baseline replay](wp1-e7-ccmsim-published-baselines-20261030.md), [CI 41073110130](https://github.com/chrober/bliss-mood-poc/actions/runs/41073110130) PASS on Windows/Linux synthetic and original source SHA verification. Actual **1,130 rated-pair** Spearman to overall human similarity: published **FM-CLAP_MUSIC_SPEECH 0.369369**, **SP-Melody 0.326620**, **FM-MERT_95 0.297746**; within-source 112 pairs: CLAP 0.347485 vs MERT95 0.301883, cross-source 1,018 pairs: CLAP 0.329279, Melody 0.290241, MERT95 0.261825. Three different human objectives and 11 published external model families are reported separately, 33 score cells/stratum; they are **NOT our Bliss23, Genre87, Mood56 or original Essentia embedding1280, and NOT independent Lyrion General quality evidence**. The public report also includes the authors' existing alignment/ensemble studies; our 1,130-row raw Spearman replay must not be conflated with their filtered/per-query 426/443 denominators. E5 clip-disjoint 40-test-pair shortfall, 93% single-rater limitation, MTT audio source block, FMA official TEST reservation remain. WP1 General primary and **unselected**; WP2 Personal Learning synthetic/P4 score compatibility and WP3 teacher proxies separate. No required operator listening, source DB, other repo, PR #16/main or production edits. Older paragraphs below precede these new completed gates.


> **LATEST WP1-E5 REAL LABEL-BLIND INDEPENDENT-SPLIT FEASIBILITY — 30 OCT 2026:** [CCMSim 1,130-pair clip-disjoint train/validation/test analysis](wp1-e5-ccmsim-clip-disjoint-split-feasibility-20261030.md) **COMPLETED** on immutable upstream public metadata ([CI 41070926652](https://github.com/chrober/bliss-mood-poc/actions/runs/41070926652): Linux/Windows offline synthetic PASS and actual publisher metadata-only source replay PASS). Using five frozen upstream-specified seeds 3/4/7/13/21 and splitting only within nine source datasets by **song ID** (not human scores), 60/20/20 allocation retains just **38–48 test pairs** of 1,130, with primary seed 3: 394 train / 47 validation / **40 test**, **649 pairs quarantined** for cross-partition clip leakage. Primary test contains only **5 within-source pairs**, 35 cross-source. Five song-disjoint folds retain **210–244/1,130 total** across folds (18.58–21.59%), only 31–68 per individual fold. Strict song-identity disjointness and count accounting passed, **BUT artist/album/recording-family disjointness, source rights and same-clip Essentia/Bliss feature parity remain unverified**. E5 decision: **NO-GO for human-label-fitted/optimized General Metric** with a purported statistically adequate independent test. CCMSim may still support a **predeclared frozen zero-shot external descriptive check**, only once lawful exact 20-second audio access/model features/provenance are available. CC BY 4.0 annotation rights do NOT license original audio, MTT 7/30 source failure persists; FMA official TEST untouched. WP2 personal P3/P4 synthetic and WP3 teacher-proxy evidence independent; preserve original 11-pair one-listener LOO as exploratory. No new votes, audio, source DB, main/PR #16 or runtime modifications. Previous WP1-E4 summary below predates this quality gate.


> **LATEST WP1-E4 EXTERNAL HUMAN-REFERENCE AUDIT — 30 OCT 2026:** A new 2026 [CCMSim public human-annotation source](wp1-e4-ccmsim-human-reference-preflight-20261030.md) was identified and verified on original pinned Git blob bytes, with [live GitHub Actions 41069144899](https://github.com/chrober/bliss-mood-poc/actions/runs/41069144899) **PASS** on Linux/Windows tests and metadata-only source replay. Published 125 participants/1,130 unique real human-rated song pairs/463 used clips, with 1,250 pair judgments and **1,052/1,130 (93.10%) only one annotator**. **1,018/1,130 (90.09%)** pairs are cross-source/cross-tradition; ratings separately measure overall, cultural and recommendation similarity. Actual pinned mapping contains **486 entries (54 per nine sources)** despite upstream README 468 (52 per nine sources); discrepancy is preserved, not silently reconciled. Rated-pair graph has **two components, largest 445 of 463 clips**, so ordinary pair-based split is leakage-prone and component-level holdout is unbalanced. Published aggregated annotation data CC BY 4.0; original source audio has **separate rights** and is not distributed by CCMSim. Same-source song-level Genre/Mood/1280D/Bliss features, artist-independent grouping, and encoder training overlap have NOT been verified. **This is only a new independent-human-reference METADATA feasibility audit, not a General Metric quality result or adopted scorer.** Do not download licensed audio or start a full benchmark until original source/clip ID, rights, source-group independence and score evaluation are established. Earlier WP1-E3 one-listener 11-song-pair human LOO and original MTT/FMA/DEAM results remain exploratory; WP2/3 distinct; FMA official TEST untouched, PR #16/main/production unchanged. Also the prior repository-wide English-doc CI failures were traced to the intentionally German ChatGPT export guide and fixed by an **exact filename exception only** in the documentation checker, leaving English research docs enforcement intact.


> **LATEST WP1-E3 HUMAN PILOT STABILITY — 30 OCT 2026:** User has **now also run** the aggregate-only full12/music11 and music11 leave-one-out stability helper on their already-existing human-rated 12-pair pilot, without exposing original private song/ratings/audit records. [All 20 real operator-reported model×human-objective rho12/rho11/LOO ranges](wp1-e3-local12-stability-real-results-20261030.md) are now committed as aggregate-only evidence. Eleven music pairs after original flagged nonmusic pair 10; eleven leave-one-more-pair-out ten-music-pair subsets, one listener, deliberately model-selected questions. Mood Centered Cosine Spearman Genre 0.688558 with LOO 0.581534–0.772890; directed Next-Track 0.769463 with LOO 0.687674–0.877186. Embedding1280 Timbre rho 0.765707 with LOO 0.674200–0.829370: **minimum Embedding Timbre LOO exceeds maximum of every other Timbre model** (highest rival max Mood Centered 0.633817), a mathematically guaranteed within-these-11-subsets relative lead, **not** confidence interval, population significance or universal quality. Embedding1280 Mood/Energy rho 0.410857 with LOO 0.194307–0.601253 is more sensitive. Removing nonmusic pair10 changes Mood Centered Next-Track rho +0.019772 and Embedding Timbre −0.050961. No individual LOOCV paired outcome vectors, new listening, training, public data access, PR #16/main or production changes. **WP1 General still unselected**; 4 global pairwise fusions unmeasured due MTT external source 7/30 failure; FMA official TEST untouched; WP2-P3/P4 synthetic and WP3 teacher proxies remain separate. Earlier WP1-E3 handover paragraphs below predate the now-observed stability output.


> **LATEST REAL WP1-E3 12-PAIR HUMAN PILOT — 30 OCT 2026:** The user executed the existing read-only local pilot successfully on the current research branch after fast-forward to `6084f145`. Their displayed console output confirms **12 original pairs / 60 completed ratings**, music-only analysis excluding original declared nonmusic **pair 10** (**n=11**) and 5 frozen scorer representations × 4 *different* human dimensions. Actual **music-only Spearman ρ**: **Mood Centered** Genre/Style **0.688558**, directed Next-Track **0.769463**; **Embedding1280** Timbre **0.765707**, Mood/Energy **0.410857** (highest among five in those two targets). Mood Cosine and Mood Centered only score 0.161408 / 0.220102 against human Mood/Energy in this selected pilot. All 20 Spearman and Kendall scores, plus full-12 rating histograms, are copied **from operator-visible aggregate console output only** to [WP1-E3 real local human results](wp1-e3-local12-real-human-pilot-results-20261030.md); original private song paths, original votes, confidential selection audit and numbered per-pair details were NOT uploaded, inspected or committed. Full-12 model correlations and 11-pair leave-one-pair-out Spearman MIN/MAX exist in already-saved **aggregate** but were not displayed in the user console. A new read-only [aggregate-only 12/11 and LOO stability summarizer](../scripts/summarize_wp1_e3_pilot_stability.py) and synthetic privacy/contract tests are added to retrieve these without new listening or original input access; pending actual user's run, no full12 vs11 rho shift is claimed. This sample is one listener, 11 intentionally model-selected music pairs and FOUR separate objectives, so **no independently confirmed General Metric, fitted fusion or significant model differences**. FMA TEST untouched, MTT source stress gate still blocked at 7/30, WP2 synthetic calibration and WP3 teacher proxies remain distinct. No production, source DB, PR #16/main or native worker edits. Earlier WP1-E3 handover paragraph below predates this real local execution.


> **LATEST WP1-E3 REAL AGGREGATE REPLAY — 30 OCT 2026:** [GitHub Actions 41064623284](https://github.com/chrober/bliss-mood-poc/actions/runs/41064623284) **PASS**. New strict [WP1-E3 sharp paired marginal-bounds study](wp1-e3-sharp-mtt-paired-bounds-and-existing-pilot-20261030.md) re-verifies exact SHA-256-locked public MTT/FMA/DEAM archives without audio and enumerates every mathematically feasible pair-correctness 2x2 table for the 8 historically observed MTT representation contrasts. Same human-decisive 293 MTT triplets: Mood centered cosine 193 correct, Mood cosine 192, Genre cosine 191, Embedding1280 cosine 182; **the 193-versus-192 pair may disagree in correctness on anywhere from 1 to 201 questions** because no original per-question predictions survived in the aggregate. Therefore NO actually observed paired McNemar test, paired CI, group bootstrap, independent holdout, global fusion accuracy, or selected General Metric is possible from these marginals; hypothetical exact p-value ranges in the audit demonstrate NON-identifiability only and are NOT p-values for claims. FMA official TEST remains unopened; its 80-query results and DEAM 240-query results likewise lack per-query paired information. [New private-data-safe optional PowerShell launcher](../scripts/run_wp1_e3_local12_windows.ps1) invokes the **already rated** 12-pair local human pilot with original sealed five-model audit and explicit pair-10 nonmusic 11-pair sensitivity, no new listening, no new scans, no source writes; it has only been syntax checked in CI, **not run on the user's private files**. Local pilot remains a deliberately model-selected one-person exploratory study; do not train/freeze a winner from it. WP2-P3/P4 artificial calibration/learning remain successfully tested but do not substitute for real independent General evidence. WP1-E2 original MTT sparse HTTP source remains blocked after 7/30 attempts; do not rerun 1019 or invent new fusion scores. No main/PR #16/production or other repo changes. Historical sections below are dated states and superseded where applicable.


> **CURRENT WP2-P4 RESULT — 30 OCT 2026:** The new [four-way, artist/album/recording/triplet-group-disjoint Personal score calibration protocol](wp2-p4-fictional-calibration-validation-20261030.md) is implemented and **executed on both Linux and Windows**, [CI run 41063403438](https://github.com/chrober/bliss-mood-poc/actions/runs/41063403438) successful with byte-identical **synthetic-only** JSON SHA-256 `037aa4fac02a1eb19be74580b5f0349c3408de36b4361d9588a4aa90b8683113`. Four partitions of fictional triplet judgments: 192 train / 48 calibration / 48 validation / 96 sealed test, identity groups disjoint; no TEST labels used to fit/calibrate/gate. Calibrator targets identical fictional **binary pair-closeness** labels; 90 calibrator / 90 validator / 180 sealed-test distinct pair rows per scenario. Raw General / diagonal Personal / diagonal+rank2 Personal sealed-test **Brier**: axis oracle `0.22550 / 0.14408 / 0.16550`; cross-feature oracle `0.24319 / 0.20322 / 0.17322`. Validation gates exercised all five 0/25/50/75/100 blend points and exact full-query General fallback; this is **NOT independently certified real music score calibration, personal musical quality, an actual selected General scorer, or production activation**. Cross-feature rank2 has better pair Brier but worse heldout triplet accuracy than diagonal, demonstrating metric endpoint tradeoffs. WP2-P3 synthetic geometry experiments remain complete; main WP1 General research is mandatory, old MTT source blocked after 7/30 requests, WP3 teacher proxy is not human truth. No new real votes/music scan/other repo/PR #16/main changes. Historical sections below are dated records, not latest status.


> **LATEST WP2-P3 ENGINEERING RESULT — 30 OCT 2026:** A new reproducible, strictly **FICTIONAL ONLY** 23D Personal Metric Learning experiment is implemented and completed on Linux/Windows ([successful cross-platform CI 41062367997](https://github.com/chrober/bliss-mood-poc/actions/runs/41062367997), exact aggregate SHA-256 `f41689fee4765256b30d2671a67fa5b0d08c65e175d545f025fe7dfeda7f9fbe`). The [WP2-P3 protocol and measured synthetic learning curves](wp2-p3-fictional-grouped-metric-learning-20261030.md) compare untrained Raw Bliss23, regularized diagonal and strictly PSD diagonal+rank2 models on two artificial target geometries, 48 artist/album/recording groups, 288 train-only and 96 unseen synthetic holdout triplets, fixed 0/10/25/50/100 label checkpoints. At 100 fictional training answers: axis-aligned target raw 46.88%, diagonal 83.33%, rank2 60.42%; cross-feature target raw 50%, diagonal 62.50%, rank2 75%. Results prove only synthetic capacity/deterministic grouped software behavior, **NO real-user preference learning, no music quality lift, no adopted Personal/General scorer and no calibration certification**. All five General/Personal blend settings and exact full-query fallback with missing/uncertified per-user models pass via the existing contract, using explicitly fictional *assumed* compatibility; no runtime/other-repo integration. WP1 General remains the mandatory primary metric; MTT source is still blocked after 7/30 repeated requests, external historical evidence remains valid, FMA TEST untouched. Preserve no new compulsory user listening, user DB reads/edits, native scans, PR #16/main, or production changes. Historical workstream status entries below are retained as dated evidence and superseded on current state. 


> **LATEST WP1-E2 NETWORK RESEARCH — 30 OCT 2026: MTT ORIGINAL SOURCE BLOCKED ON REPEATED MP3 REQUESTS.** Safe source-only GitHub Actions diagnostics prove the original multipart ZIP publisher responds to tiny HTTP-206 range probes (3/3), and an exact metadata/ZIP-header/CRC-validated real single referenced clip succeeds (116,178 bytes). BUT the deliberately rate-limited, source-part-stratified 30-clip sample [run 41060669011](https://github.com/chrober/bliss-mood-poc/actions/runs/41060669011) stopped **after 7/30 CRC-verified clips** (part counts 3/2/2; 811,839 successfully transferred bytes), sanitized failure category RANGE_TRANSPORT_FAILURE. The old sibling-branch clip cache is inaccessible on this branch (scoped cache MISS); copying or publishing licensed clips is not a safe assumed workaround. The diagnostic workflow green conclusion means blocked source condition was correctly measured, **not** a successful audio benchmark. **Do NOT trigger a full 1,019-clip replay now** based on three tiny probes. The four globally comparable pairwise MTT fusion scores remain UNMEASURED; original [WP1-E1 historical MTT/FMA/DEAM evidence audit](wp1-e1-verified-public-benchmark-evidence-20261030.md) remains valid, with separate task endpoints and FMA official TEST untouched. Preserve the completed WP3-R6/R7 real teacher proxy work; WP2 Personal is parallel. See [real WP1-E2 source/cache/CRC findings](wp1-e2-mtt-source-and-cache-diagnostics-20261030.md). No new user music, rating tasks, model fitting, PR #16/main, worker or production modifications. Supersedes the previous WP1-E2 status below that called the 30-clip gate pending.


> **WP1-E2 MTT SOURCE/REPLAY ENGINEERING — 30 OCT 2026:** The [real WP1-E1 aggregate evidence replay](wp1-e1-verified-public-benchmark-evidence-20261030.md) remains PASS; four global pairwise fusion scores on the same MTT human triplets remain UNMEASURED. For WP1-E2, original [MTT failed fusion workflow 40881326086](https://github.com/chrober/bliss-mood-poc/actions/runs/40881326086) failed because its research-branch cache was absent (sibling branch caches are inaccessible by key) and the subsequent first-part member HTTP-206 request timed out with curl 28 / HTTP 000. Dedicated [WP1-E2 source/cache gate](wp1-e2-mtt-source-and-cache-diagnostics-20261030.md) implemented and genuine checks passed: same-branch cache MISS, three official 4-KiB archive ranges PASS, and a single real SHA/source-pinned MP3 member CRC PASS (116,178 bytes, no audio published). A further bounded 10-per-archive-part/30-clip stress diagnosis is added to detect repeated-request failure; its outcome must be read from the exact run, never guessed. No music similarity, model inference, official FMA TEST inspection, native worker tuning, LMS/PR #16/main change or manual listening occurred. The next milestone is a real same-1,019-clip MTT fixed-four-global-fusions evaluation **only if** the source/cache path passes feasibility and all audio provenance gates. WP2 Personal remains an active separate parallel direction.


> **LATEST VERIFIED WP1-E1 REAL AGGREGATE REPLAY — 30 OCT 2026:** The separate research branch has completed a **no-audio, SHA256-locked historical public evidence audit** using GitHub Actions [successful run 41058917003](https://github.com/chrober/bliss-mood-poc/actions/runs/41058917003), artifact 12978177761. Genuine past MTT (293 decisive/346, 1,019 clips), FMA catalog-screened 80-artist VALIDATION (official TEST untouched) and DEAM screened 240 reports were downloaded from existing original runs, verified by member SHA and strict dataset/coverage constraints, then summarized as **three independent task-specific reports without cross-task score blending**. MTT Mood centered cosine 193/293=65.87%, triplet-LOCAL 3-head rank fusion 192/293 with only 283 predicted; FMA Genre centered cosine P@5=.3225; DEAM Mood weighted Jaccard VA Spearman=.28885, Mood cosine=.28678. **The four GLOBAL pairwise equal-weight fusions have NO verified real scores**: existing MTT global replay run 40881326086 failed before inference during curated audio-cache reconstruction; prior archives contain aggregates only, not missing vectors. No same-recording Bliss23 available for MTT/FMA/DEAM is established, so WP3 Ridge must NOT be inserted as a public benchmark result. The complete [WP1-E1 evidence and next cache-dependent research gate](wp1-e1-verified-public-benchmark-evidence-20261030.md), [immutable artifact source lock](../research/wp1-e1-external-aggregate-lock-v1.json), [offline verifier](../scripts/audit_wp1_external_aggregates.py) and [live aggregate-only CI](../.github/workflows/research-wp1-external-evidence-replay.yml) are now available. Next: establish legal/reliable selected-1019 MTT audio/feature availability, then run **real same-cohort global-fusion comparisons** (not a self-contained inference based on summary JSON). No new user listening, private audio, worker tuning, official FMA TEST, PR #16/main or production changes. WP2 optional Personal Metric Learning and 100% General fallback remain parallel. Older WP1 plans below are historical.


> **LATEST REAL MEASUREMENT — 30 OCT 2026, WP3-R7 COMPLETE:** The operator completed the non-scanning R7 analysis on the previously frozen 240 R6 native C++ songs; original R6 aggregate reproduced exactly; 240 source-identity groups, 28,680 dependent pairs, 300 paired song-group bootstrap repetitions. Frozen old-100 Mood Ridge versus raw Bliss has exploratory global Spearman deltas **+0.051079** to Mood teacher (95% percentile [+0.014451,+0.085105]) and **+0.047287** to Genre teacher ([+0.007265,+0.087971]). Old-100 Genre PLS2 to Genre teacher: **+0.010666** ([-0.033155,+0.053310]). **Key divergence:** Mood Ridge raises Mood teacher Top-5 overlap **6.25% -> 8.58%**, yet LOWERS Genre teacher Top-5 **7.92% -> 5.67%**; Genre PLS2 lowers all measured teacher Top-5/10/20 overlaps against raw Bliss. R7 post-hoc reuse, intervals not multiplicity-adjusted, NO retrieval uncertainty, no human/playlist validation, teacher model numeric parity/pretraining overlap still uncertified. **Do NOT rerun R6 or R7**; preserve private aggregates and input data. [Full measured findings and scientific next gate](wp3-r7-real-results-and-next-quality-gate-20261030.md). Priority is independently task-appropriate WP1 perceptual/external validation and separate WP2 personal learning, rather than choosing a universal metric on teacher reconstruction. Historical lines below claiming R7 pending are superseded. No new compulsory listening, scans, PR #16/main, worker tuning or production modifications.


> **CURRENT STATUS — 30 OCT 2026, real R6 completed and R7 implementation added:** The operator completed the original native Essentia C++ R6 scan on the **frozen 240 source-identity-disjoint new songs**, with 240/240 Genre87, MoodTheme56, Voice2 and normalized 1280D embeddings, all source/model hash checks PASS. The user supplied the non-identifying R6 numerical aggregate: frozen MoodTheme Ridge MAE reduction **15.9474%**, frozen Genre PLS2 MAE reduction **12.3069%**; teacher-distance Spearman raw Bliss→Mood **0.387956** vs Mood Ridge **0.439035**, raw Bliss→Genre **0.430849** vs Ridge **0.478136** across **28,680 dependent pairs**. R6 is teacher-proxy reconstruction, not human-quality evidence, and no model pretraining-overlap/parity certification was obtained. The next post-hoc [WP3-R7 bootstrap + retrieval protocol](wp3-r7-post-r6-robustness-and-retrieval-20261030.md) and [Windows-only no-scan runner](../scripts/run_wp3_r7_240_windows.ps1) are implemented on the separate research branch. R7 requires original R6 numerical reproduction, resamples **240 distinct source-identity song groups** (not pairs), compares 3 paired Spearman deltas and Top-5/10/20 teacher-neighbor retrieval including old-fit Genre PLS, writes anonymized private aggregate only. **R7 real-data run NOT YET performed**, synthetic CI is a distinct engineering gate. Use verified existing input R6 plan benchmark-wp3-r6-native240-f8c65ca449eb40e8ad6b5b3e817c18b2. Prior handover notes below contain historical statuses, including 'R6 pending', and do not override this current statement. No additional Essentia scan, human-rating request, PR #16/main or production modification. WP1 General/WP2 optional Personal remain fully separate.


> **WP3-R6 SCIENTIFIC DIRECTION UPDATED — 30 OCT 2026 (real new scan still pending):** The user expressly approved analyzing the **complete frozen 240-song cohort with native original Essentia C++**, rather than restricting WP3-R6 to Bliss-only 24-pair blind diagnostic. R5 240-song cohort selection is already real PASS. Machine-readable [predeclared 240 new teacher protocol](../research/wp3-r6-full-teacher-evaluation-v1.json) fixes old-100 train-only MoodTheme Ridge(alpha 10), old-100 PLS2 Genre, raw/old-scaled Bliss, Mood/Genre, normalized EffNet1280D and 28,680 DEPENDENT pairs; no new-teacher hyperparameter selection. New [R6 native 240 runbook](wp3-r6-native-240-essentia-protocol-20261030.md), [Python manifest/source/audio/model/native hash-preflight + guard + full 240 postscan validator](../scripts/wp3_r6_native_240.py), [frozen evaluator](../scripts/evaluate_wp3_r6_240.py), and [one-command Windows PS5/7 staged script](../scripts/run_wp3_r6_native_240_windows.ps1). Strict previously verified scanner source/hash, worker/DLL fingerprints and original ONNX model equality. The actual private 240-song scan is NOT executed, CI synthetic only. Current next operator action after verified CI is prepare/scan/verify on Windows (default Prepare; explicitly `-Stage All` enables real audio analysis). No public code/data publication, native distro legal release, production LMS, PR #16/main changes. Previously implemented optional 24-pair R6 blind pilot is now DEFERRED, not required. Human-perceptual similarity evidence requires separate gate; WP1 and WP2 remain active.


> **CURRENT USER-VERIFIED 240-SONG SOURCE COHORT PASS — 30 Oct 2026:** The operator successfully ran `prepare_wp3_independent_cohort_windows.ps1` read-only preflight + local private manifest: 240 new Bliss23-valid songs, **exactly 15 per each of 16 Tempo/centroid bins**, strict known artist/album/recording disjoint from old 100 and within 240, old 100 excluded, unknown new recording MBIDs conservatively excluded, no Essentia scores or listening labels. `benchmark-wp3-independent-cohort-586d7988747e4087b9cf1315492a34fc/private-independent-cohort.json` stays private on Windows; never upload/commit. [Full actual selection evidence + new WP3-R6 preregistered blind diagnostic](wp3-blind-student-validation-pilot-20261030.md). WP3-R6 research-only code can now recheck this 240-song manifest and fit the fixed MoodTheme Ridge(alpha 10) student on the old 100 development songs only, then prepare **24 optional blind original-Bliss vs WP3-student pairs** (6 raw wins in rank / 6 student wins / 12 random, 48 distinct songs; sealed score audit and all training weights private). Original 25 group-holdout songs from R3 become development inputs for this *refit*; they are NOT external evaluation of the new fitted model. New 240 have NO Essentia or human ratings. **R6 has not yet been executed by the user** and is not a quality result; CI uses only synthetic sources. Next operator step if desired: git pull research branch then `& .\scripts\prepare_wp3_blinded_bliss_student_pilot_windows.ps1` on Windows PS. No compulsory listening, audio/ONNX scans, LMS queue/restarter, production or PR #16 changes. WP1 General and WP2 optional Personal remain active, separate.


> **30 Oct 2026 NEXT WP3 R5 IMPLEMENTED, REAL EXECUTION PENDING:** The user's authenticated genuine 100-song teacher study remains the last real measurement; its 75/25 group-heldout MoodTheme student teacher-distance Spearman was 0.442049 original Bliss -> 0.540662 student but **no human perceptual lift established**. A machine-readable MoodTheme Ridge(alpha 10) *hypothesis-only* spec is now frozen; [WP3 R5 new-cohort protocol](wp3-independent-cohort-validation-plan-20261030.md) and [single self-contained Windows PowerShell planner](../scripts/prepare_wp3_independent_cohort_windows.ps1) were added on isolated research branch. The planner proposes 240 NEW songs (existing Bliss only) from the operator's Lyrion/Bliss databases, excludes every existing 100-song ID and all shared source-grounded credited artists (incl. collaborations), albums and known recording MBIDs; rejects missing new MBIDs and samples balanced seeded Tempo/MeanSpectralCentroid quartile proxies. It must not run Essentia/audio, request listening labels, reveal private song keys in stdout, or claim validation. Private output manifest is ignored/not shareable. **No real independent cohort has yet been selected**, CI remains synthetic; subsequent human/perceptual comparison and any audio analysis require separate authorization. Next Windows operator step once tests pass: git pull research branch and run `& .\scripts\prepare_wp3_independent_cohort_windows.ps1`. WP1/WP2 remain separate; PR #16/main unchanged.



> **CURRENT HANDOVER — real WP3 teacher experiment COMPLETE (30 October 2026):** The user successfully ran `scripts/build_wp3_research_db_windows.ps1` from PowerShell using Python 3.15.0, genuine local copies of LMS `library.db` + BlissMixerLab `artist-repeat-identities.sqlite`, and already computed Bliss23/native Essentia Genre87/MoodTheme56. The new private grouped research SQLite is `benchmark-wp3-research-20261030-091600-8c93d55f/wp3-research.sqlite` with aggregate `aggregate-teacher-research.json`, neither committed. **100/100 source identities verified, 88 artist/album/recording-connected groups, 75 train / 25 group-disjoint holdout, one unknown recording MBID grouped conservatively.** In real heldout teacher-vector prediction, Genre87 PLS improved MAE **6.92%** and MoodTheme56 Ridge **13.04%** relative to training-mean baselines. Bliss-only Ridge distance geometry versus Essentia teacher: Genre Spearman **0.557959 -> 0.569599** (+0.011640), MoodTheme **0.442049 -> 0.540662** (+0.098613). PCA-CCA teacher cross-view Pearson **0.632409** Genre / **0.815130** MoodTheme. All results are **exploratory**: the 100 songs had already been used for 3,289 full-cohort correlations; 25 group-disjoint holdout songs are **not** untouched confirmatory data. Teacher head numeric parity is not validated, cross-analysis audio-byte identity and pretrained-teacher overlap are not certified, there is no independent musical/human similarity gain or deployment. **Next:** freeze the MoodTheme Ridge student *candidate configuration* and protocol, acquire a genuinely NEW artist/album/recording-disjoint diverse cohort with separate human/perceptual similarity reference, compare against original Bliss and WP1 baselines, report group-aware uncertainty, and progress WP2 optional personal/blend separately. Never fit/adjust on the 25 songs and call it an independent test. [Detailed source-grounded results](wp3-real-grouped-teacher-study-results-20261030.md). Earlier dated note blocks below remain historical and do not override this status.


> **30 Oct 2026 authentic metadata gate PASS:** Latest user-provided console output from Windows PowerShell shows successful real Lyrion Pi SQLite online backup, SCP, Python 3.15 copied SQLite quick_check and entire exact Bliss/Essentia/LMS grouping preflight. 100/100 tracks with verified actual artist, album, LMS ID and URLMD5; 88 independent connected identity groups; 75 train / 25 group-heldout; only 1 missing recording MBID handled conservatively. `ready_for_grouped_study=true`, `blocking_reason_code=null`. Previous source-provenance blocker is now cleared. No audio scans or trained teacher metric yet. Local private metadata snapshots exist and must not be uploaded/committed. Next run existing `build_wp3_research_db_windows.ps1` with exact private metadata env variables to produce a new versioned grouped research SQLite and exploratory train-only teacher-fit; original group-free snapshot remains intact. Caveat: original whole-100-song correlation exploration exposes holdout to selection bias; group disjoint != untouched confirmatory independent perceptual test, and teacher reconstruction != improved WP1 song similarity. Preserve general/personal/teacher separation and PR #16/main. [WP3 source evidence](wp3-consolidated-research-sqlite-20261029.md).


> **30 Oct 2026 Pi SQLite transport fix after actual user attempt:** Real online SQLite backups/SCP worked in first one-off attempt, but PowerShell `python -c` quote stripping blocked local validation, remote cleanup left WAL/SHM; second attempt with the repository launcher failed on its very first `set -eu` at `sh -s`, likely Windows CRLF from PowerShell-to-SSH stdin. The old UUID staging dir was inspected and contains only 32KB library.db-shm and 0B library.db-wal. Research branch launcher now transmits isolated one-line SSH commands, with read-only original DB SQLite online backup by echo-to-sqlite3 and explicit nonrecursive cleanup of two output DBs and their WAL/SHM. Exact authentic LMS artist/album/recording checks have **NOT YET RUN**; CI is synthetic and cannot verify live SSH. Retry on Windows PS after git pull, then collect actual aggregate; do not train, deploy or relax independent group-disjoint gates. See WP3 consolidated research SQLite document.


> **30 Oct 2026 verified remote Lyrion identities and PowerShell repair:** Real pCP server identified two genuine data sources via read-only SQLite: LMS Cache/library.db 79,005 tracks and 6,228 albums, Lab Cache/BlissMixerLab/artist-repeat-identities.sqlite 77,517 track identities and 76,870 artist-credit rows. Schema identity v1, scan 1793339060, expected columns exist. Remote SQLite online backups and SCP to Windows worked, but PowerShell-native Python -c lost double quotes causing SyntaxError at local validation, so the real group preflight never ran. The cleanup multi-line SSH script also failed with EOF; old exact /tmp/wp3-metadata-f15ad4f9c54340818830fcb14c08eeca may need bounded cleanup. Isolated branch adds new Python-file read-only metadata quick_check/schema inspector, full PowerShell 5.1/7 standalone transfer+preflight with safe one-line cleanup, synthetic Python/Windows CI. Actual Windows+Pi re-run still needed; no independent group holdout or teacher-quality gain exists. Full evidence + instructions in wp3-consolidated-research-sqlite-20261029.md.


> **30 October 2026 WP3 actual robustness findings:** Anonymized 100-song aggregate confirms 253/253 valid Bliss↔Bliss correlations, 22 absolute Spearman >=0.7, seven >=0.9; Chroma11–Chroma12 +0.968089, Chroma12–Chroma13 +0.957912, Zcr–Rolloff +0.969277. Essentia metal/hard +0.832871, soft/romantic +0.928557; metal/soft −0.701494. All 16 POST-SELECTED cross-feature correlations kept sign across 200 strongly overlapping 80%-subsamples; maximal leave-one-out absolute rho shift 0.024519. Therefore observations are not isolated-outlier artifacts within the cohort, but heavily REDUNDANT and still subject to 3,289-way selection bias, artist/album dependence and teacher-model confounds. No additional fitted weights/metric/deployment should proceed on the same 100 songs. Authentic LMS artist, album and recording IDs and a diverse independent grouped holdout take priority; WP1 General and WP2 optional Personal retain their own independent quality baselines. Original private research DB still only on Windows; no new audio analysis occurred. [Method/results and next gate](wp3-consolidated-research-sqlite-20261029.md).


> **30 October 2026 WP3 post-hoc redundancy/robustness next slice:** Real 100-song feature join and descriptive 3,289 correlation analysis have succeeded. Frozen 16 strongest earlier feature/class pairs are explicitly marked POST-SELECTED (Chroma6/11/12/13, flatness to Genre hard/metal/easylistening/improvisation and MoodTheme soft/nature/romantic). Added stdlib Python 3.15 analyzer and one-command PS 5.1/7 runner for all 253 Bliss intrafeature pair correlations, 21 selected cross-Essentia-class redundancy pairs, leave-one-out sensitivity and 200 seeded 80%-song-without-replacement perturbations. Reports anonymized aggregate only to new ignored file, original SQLite read-only. Scientifically this measures within-sample perturbation and NOT independent artist/album holdout or corrected significance. Previous native C++ scan created features, one-DB builder simply copied and validated previously analyzed rows (explains execution in seconds). Main and PR #16 remain unmodified. See WP3 single SQLite document.


> **30 October 2026 WP3 research status:** Real operator-supplied output confirms successful creation of a private single research SQLite: 100 eligible native Essentia 87D/56D vectors joined exactly to Bliss 23D, no exclusions, source hashes unchanged. **Lyrion artist/album/recording grouping is missing** (not a failed feature join). New group-free **descriptive** Pearson/Spearman across all 3,289 cross-model class/feature pairs is runnable against the EXISTING one SQLite using [Windows entrypoint](../scripts/analyze_wp3_snapshot_correlations_windows.ps1) or [Python stdlib script](../scripts/analyze_wp3_snapshot_correlations.py). No teacher fitting, global similarity winner, statistical independence or multiple-test significance inferred from the 100-song pilot. The genuine BlissMixerLab snapshot is created under the LMS OS-specific cache directory, not at a verified Windows path. Preserve optional verified group gate for WP2/WP3 learning; continue WP1 independent music-quality validation separately. See [full single-DB source and method documentation](wp3-consolidated-research-sqlite-20261029.md). No PR #16/main changes.


> **WP3 single-DB decision and implementation (29 Oct 2026):** User approved creation of a **new local private research SQLite** instead of manually supplying four DB paths. Preferred new [read-only source builder](../scripts/build_wp3_research_db.py) and [one-command Windows 3.15 launcher](../scripts/build_wp3_research_db_windows.ps1) documented in [WP3 consolidated research SQLite](wp3-consolidated-research-sqlite-20261029.md). Known real 100-song native Essentia C++ schema-v3 source is D:\LMS\bliss-mood-poc\benchmark-native-similarity-100-20261029\native-features.sqlite, alongside D:\LMS\bliss-mood-poc\bliss.db. Builder joins only exact keys from original feature vectors; no audio rescans, no rewriting sources, no directory guessing. New private research SQLite contains Bliss23/Genre87/MoodTheme56, model/audio provenance and optional *verified* artist/album/recording groups. If the actual Lab snapshot and Lyrion SQLite library DB are not available, the file is created with group status NOT_AVAILABLE, teacher/metric learning withheld; do not fabricate labels or infer from filenames. Self-contained grouped WP3 teacher runner now accepts --research-db but refuses to train if group gate did not pass. This is an engineering implementation supported by synthetic CI, not completed real-data metric evidence. WP1 General Similarity, WP2 optional Personal, native parity study and PR #16 remain intact.


> **Windows PowerShell 5.1 runtime quoting fix (29 October 2026):** The user's first attempt after selecting Python 3.15 failed **before reading any data**: PowerShell's native argument forwarding removed the nested double quotes in `python -c 'import sys; print(str(sys.version_info.major) + "." + ... )'`, yielding `SyntaxError`. The Python 3.15 installation is correct and does not need reinstalling. The one-block launcher now obtains the version with `python --version` and regex-checks 3.15 without quoted Python string literals. Its later scientific-package check uses a quote-free `python -c` argument. The read-only source preflight passes its list of arguments via explicit PowerShell variable splatting. The dedicated WP3 CI now **executes** this exact launcher runtime path on Windows PowerShell **5.1** and **7**, rather than only parser-validating the script. The existing four-source real-data preflight has **not yet been executed on the user's local databases** as of this change. Latest bugfix is isolated on `feat/general-pairwise-similarity-research`; no PR #16, main, Python runtime installations, native scans, or personal song data were changed.


> **Current local operator decision, 29 October 2026:** User requests **Python 3.15 exclusively**; the earlier recommendation to install Python 3.13 was unnecessary and withdrawn. The Windows launcher now invokes the installed `python` (version 3.15) for **both** phases, creates its isolated venv with the same interpreter, and uses `research/requirements-wp3-py315.txt` (NumPy 2.5.4, SciPy 1.18.1, scikit-learn 1.9.1, joblib 1.5.2, threadpoolctl 3.6.0). No second Python installation or downgrade is performed or suggested. Synthetic Windows/Linux CI runs on Python 3.15. The earlier native-comparison status `PASS_EXPLORATORY_TOLERANCES` is NOT a WP3 real Bliss/Essentia correlation or General Metric improvement. Next: git pull on research branch and invoke the standalone PowerShell script; diagnose the actual four read-only sources before running any statistical work. Private data stay local. PR #16, main, learner and plugin repos unchanged.






> **CURRENT NEXT ACTION (29 October 2026):** The [local grouped research script](../scripts/run_grouped_bliss_essentia_research_windows.ps1) now performs a **pure Python standard-library, read-only, no-output preflight** of the four actual input SQLite databases before any numerical dependency installation, private group serialization or WP3 statistics. The preflight returns nonidentifying source-coverage counts, train/holdout group counts and `blocking_reason_code`; it fails closed on incomplete snapshot scan/roots metadata, stale LMS track URLMD5/artist/album provenance, insufficient paired Bliss+Essentia features and shared/undersized recording groups. See [source provenance and preflight documentation](bliss-essentia-lyrion-existing-metadata-source-20261029.md). This is the next handoff for an operator with access to the real existing DBs: execute the complete Windows source-read-only script, retain all private outputs locally and share only high-level aggregate counts/status if desired. **No access to those real source databases has been established in this conversation; do not invent correlation results or ask for new listening.** WP1 General, WP2 optional Personal, PR #16, existing native scans and related repos remain unchanged.


> **LATEST SOURCE INVENTORY / 29 OCTOBER 2026 (WP3 existing Lyrion metadata reuse):** A concrete source for **real artist and album identities** has been found in the existing [BlissMixerLab RepeatIdentitySnapshot and Lyrion library.db](bliss-essentia-lyrion-existing-metadata-source-20261029.md), removing the *manual group JSON* prerequisite **when those sources are actually present and coherent**. New [read-only exact-key artist/album/recording grouping adapter](../scripts/derive_lyrion_research_groups.py) verifies snapshot schema and each selected LMS track ID, urlmd5, artist credits, album and recording MBID; it merges collaborators and conservatively groups missing recording MBIDs. A [complete single-block Windows launcher](../scripts/run_grouped_bliss_essentia_research_windows.ps1) fetches only the isolated branch into a detached worktree, checks the four existing input SQLite SHA256s, verifies Python dependencies, derives private groups and produces aggregate-only existing WP3 teacher statistics with no audio or model rebuild. Synthetic real-schema integration and PowerShell syntax PASSED on Windows/Linux. **No access to real user databases is established and no real Bliss↔Essentia correlations were measured.** The first real experimental gate is verifying that the Bliss DB, Essentia sidecar, Lab cache snapshot and Lyrion SQLite library DB are actually accessible and share valid identifiers; never invent paths or silently relax the holdout. WP1 General, WP2 optional Personal and the completed native/12-pair work remain unchanged.


> **LATEST HANDOVER (29 October 2026): WP3-R3 and WP2-P3 executable research adapters DONE on separate branch.** See [local Bliss↔Essentia study and verified original learner execution contracts](bliss-essentia-local-study-verified-learner-20261029.md). WP3 code reads Bliss 23D and coherent Essentia 87D/56D model cohorts plus explicit private artist/album/recording groups, fails closed on missing groups, evaluates grouped Pearson/Spearman/Ridge/PLS/PCA-CCA and Bliss-only Essentia-distilled distance proxy, writes aggregate JSON only; *not yet executed with real music*. WP2 accepts a prior SHA256-bound training-only mini SQLite/triplet bundle and independently pinned existing learner executable; verifies complete train-only song universe and the resulting PSD/symmetric legacy matrix before writing a **private** run manifest; *not yet executed with real personal votes*. CI passed Windows+Ubuntu for both synthetic workflows. Respect WP1 General fallback; no compulsory listening, PR #16 edits, native rescans, worker tuning, guessed private DB/group paths or uncertified Personal activation. Next: license- and identity-verified multi-source paired feature data (WP3), independent real preference holdout if voluntarily available (WP2), and independent musical-quality labels for Bliss-only improvement. Old instructions to start WP3-R0/R1/R2 or WP2-P0/P1/P2 are historical and superseded by the actual status.


> **IMPLEMENTATION HANDOFF 2026-10-29 — WP3-R2 and WP2-P2:** The separate research branch now includes [grouped, train-only scikit-learn Ridge/PLS/PCA-limited CCA, Bliss-only teacher-geometry distillation, and SHA256-bound private train-only Bliss learner staging](bliss-essentia-teacher-models-train-only-learner-20261029.md). WP3 model fitting is on group-disjoint train data only; the teacher-geometry proxy consumes only 23D Bliss at inference and compares against Essentia **pseudo-teacher** distances (not human musical quality). WP2 isolates the unchanged Rust learner's future inputs to a NEW private SQLite containing ONLY training song features and a training-only triplet JSON. A private manifest records exact input/output hashes; **no learner has run, no personal model or real correlations have been measured, and no additional compulsory listening is requested**. Both synthetic workflow families passed Ubuntu and Windows. Next: permissioned group/source-verified real paired-feature study for Bliss-only downstream quality and separately authorized train-only Rust learner execution with heldout validation. Continue WP1 concurrently; PR #16 and related repos remain unmodified.


> **LATEST HANDOVER, 29 October 2026 — WP3-R1 / WP2-P1 implemented:** Read [grouped relationships + personal evaluation protocol](bliss-essentia-grouped-relationships-personal-evaluation-20261029.md) before starting new work. This separate research branch now contains (1) group-disjoint artist/album/recording/same-triplet component splitting, fail-closed if no independent holdout; (2) Pearson/Spearman 23 Bliss × 87 Genre and 23 × 56 Mood coefficients, strongest pairs selected on train only and evaluated on separate group-holdout; (3) the old Bliss 23D Euclidean triplet baseline plus old 23×23 Mahalanobis format/distance validation, **requiring an explicit declared training-only partition** for descriptive learned-matrix assessment. All are synthetic, privacy-preserving and no trained personal quality gain or real feature correlation is claimed. The previous WP3-R0 exact-key join and WP2-P0 safe 0–100% blending stay intact. Next: plan WP3-R2 authorized multi-source paired data with grouped fit-on-train CCA/PLS plus Bliss-only metric A/B; WP2-P2 reuse existing learner in a strictly train-only separate process with verifiable manifest and independent user holdout. No PR #16, original repo, rating, native scan or worker modification.


> **LATEST CODE HANDOFF / 29 OCT 2026:** WP3-R0 and WP2-P0 are implemented on the isolated research branch. See [the exact-key feature-join and Personal contract handoff](bliss-essentia-join-personal-contracts-20261029.md). New code: [Bliss 23D/Essentia 87D/56D read-only audit](../scripts/audit_bliss_essentia_join.py) (optional pinned 1280D existing sidecar coverage) and [General/Personal full-query scorer gate](../scripts/general_personal_blend_contract.py), with privacy/symmetry/fail-closed synthetic tests under the dedicated Windows/Linux CI. **No real private Bliss DB has been read and no Personal model trained.** New priority: WP3-R1 paired source/artist/album grouping and correlations; WP2-P1 grouped learner protocol/calibration and low-complexity baseline, while maintaining WP1. Never repeat earlier completed native work or demand new listening. All earlier instructions to *start* WP3-R0 or WP2-P0 are historical now.


**Current canonical plan:**
[Unified three-workstream similarity strategy](similarity-three-workstreams-strategy-20261029.md).
This replaces prior *narrowly general-only* next-task interpretations,
without discarding the valid PR #16 general/personal decision or completed
technical experiments. **Read the strategy before implementing code.**

## Verified branches and non-interference

- `main`: no research changes authorized.
- Draft PR #16 `feat/similarity-metric-evaluation`:
  canonical prior scientific A/B/C benchmarking and original
  [General/Personal blend specification](similarity-general-personal-blending-architecture.md).
  Remains **unchanged**, originally read at
  `2204ec91d8d8a773872f266397b0656178b481ee`.
- `feat/native-similarity-cohort-validation`: earlier real native
  same-100 engineering continuity test **completed** with report
  `PASS_EXPLORATORY_TOLERANCES`. Its successful scan and
  comparison must not be rerun.
- `feat/general-pairwise-similarity-research`: **independent research
  branch**, forked from PR #16, owns all new strategy documents,
  opt-in global fusion prototypes and exploratory MTT CI.
  It is not to be mistaken for a PR #16 commit.

## The three permanent research work packages

1. **WP1 General Similarity Metric:** always-available, label-free
   global songpair similarity. Compare Bliss 23D, Essentia Genre
   87D/Mood 56D/Embedding 1280D, and justified multi-signal
   methods on genuinely task-aligned independent evidence.
   Existing MTT (293 decided out of 346 triplets), FMA screened
   80-song VAL, filtered DEAM 240 and 12/11 rated-song pilot are
   exploratory development evidence, **not new independent holdouts**.
   Four current affine global fusion prototypes are not a metric winner.
2. **WP2 Personal Metric Learning and 0–100% blend:** **active in
   parallel** at protocol and reusability level now. Reuse actual
   functioning `chrober/bliss-learner` (23D regularized/probit/STE
   Mahalanobis with L-BFGS and lambda CV) and
   `chrober/lms-blissmixer-lab` (triplets, survey, model lifecycle)
   as references rather than reimplementing fundamentals. Existing
   Lab `learned_blend` is **not** the new General/Personal
   setting. The existing learner's random triplet holdout is
   **not artist-/album-disjoint**. Freeze independent per-user
   data/identity/score-calibration/quality/fallback contract;
   test `alpha_effective=0` for absent/incompatible personal
   model. No use of user's 12 diagnostic pair ratings to
   fit a personal model; any future votes strictly voluntary.
3. **WP3 Bliss ↔ Essentia Feature Relationships and Bliss-only
   improvement:** **start now** with exact-key, read-only Bliss
   23D/Essentia 87D/56D/1280D paired-feature availability and
   synthetic fixture, then descriptive/partial correlation,
   grouped clustering/PCA, regularized CCA and PLS, ridge
   predictors, student/teacher distillation and careful
   learned Bliss-only metric transforms. Compare transformed
   Bliss **without needing Essentia at serving time** against
   original Bliss, and separately evaluate direct Bliss+
   Essentia fusion. Demonstrate **independent musical similarity
   improvement**, not merely teacher-output predictability;
   artist/album/source leakage and ONNX pseudo-ground-truth
   errors are critical.

**Work ordering:** WP1 baseline/coverage + WP3 paired-data contract
**in parallel now**, WP2 scorer/interface/triplet/reuse contract
**in parallel now**. Later model fitting and real-quality validation
are conditional on licensed, grouped independent data, not on a
perfect general metric or fresh mandatory personal ratings.

## Technical safety gates

- Native same-100 test confirmed 100 songs, 4,950 pairs and
  near-identical five pair-rank rhos; **it did not validate
  perceptual or transition quality**, and does not establish
  Bliss 23D coverage of the 100-song cohort.
- This branch's standalone new MTT global fusion workflow
  [run 40881326086](https://github.com/chrober/bliss-mood-poc/actions/runs/40881326086)
  **FAILED** during 1,019-clip sparse cache build due to
  publisher HTTP range timeout (curl 28 / HTTP 000), after
  synthetic and metadata gates. No real new MTT fusion
  statistics exist; do not fabricate or select a winner.
  No blind repeated archive requests in lieu of this work package.
- Do not change existing private `bliss.db`, original
  feature SQLite, source audio, personal triplets,
  original ratings or Lyrion queues. No schema rewrites, no
  native rescans and no additional worker auto-tuning.
- MTT is already fully explored; FMA official TEST remains
  untouched; DEAM head-vs-embedding replay remains unavailable
  until publisher/archive access is independently proven.
- Extract Bliss `TracksV2.File` exact 23D columns from source,
  validate finite feature values and upstream ordering. Join
  Essentia on the **exact** original `track_file`, not rowids
  or names. Source/model fingerprint and artist/album group
  evidence required before any actual paired real-music claim.
- Independent performance evidence must be group-aware and
  multi-library where feasible; never optimize solely to one
  Windows/Ryzen or one private music collection.
- Windows local work, if required, must be delivered as a
  complete directly runnable automated PowerShell `& { ... }`
  block with isolated worktree update, verified necessary
  binaries/CI run and hashes, dependencies and fail-closed
  pre-existing-output policy; never ask the user to manually
  assemble several Git or download fragments.

## Next substep (R6) — privately fit frozen student and offer optional blinded 24-pair diagnostic

**WP3-R5 was actually executed successfully**, producing 240 new Bliss23
songs with no recorded artist/album/recording identities shared with
the old 100 or mutually within the new selection, exactly 15 in each
of 16 Tempo/MeanSpectralCentroid quartile bins. No new song has
Essentia or human similarity labels.

**WP3-R6 is implemented but not run on the user's real data.** The
[research-only pilot](wp3-blind-student-validation-pilot-20261030.md)
revalidates the exact private R5 manifest against all original sources,
fits the frozen MoodTheme Ridge(α=10) student on all 100 old development
songs only, then proposes 24 optional blind review pairs from 240 NEW
Bliss23 songs (6 original-Bliss-preferred / 6 student-preferred / 12
random controls; 48 distinct songs). Private teacher-student weights,
pair-identity CSV with EMPTY labels, and method-specific SEALED audit
stay locally ignored. No audio/ONNX scans, no Lyrion queue operations,
no compulsory listening. Because half the pairs are purposefully
discordant, this is a diagnostic sample, not unbiased population
perceptual validation.

After successful CI and branch update, the next optional operator
step is `& .\scripts\prepare_wp3_blinded_bliss_student_pilot_windows.ps1`
from Windows PowerShell. The *next actual scientific result* still
requires volunteered blind human/perceptual judgments from a
larger independent protocol; do not claim student improvement from
model-score analysis or prepared pairs alone.

## Current next assignment (as of 30 October 2026)

**WP3-MOOD-VALIDATION and WP1/WP2 coordination; no re-run of already completed group-source preflight.** The first actual authentic artist/album/recording group-heldout 100-song teacher study is complete. Its empirical evidence is in [WP3 real grouped teacher study](wp3-real-grouped-teacher-study-results-20261030.md), and full input/backup/debug chronology is in [consolidated WP3](wp3-consolidated-research-sqlite-20261029.md).

- Record and freeze the experimental **MoodTheme56 Ridge student** with the run's fixed hyperparameters (Ridge alpha 10, train-only preprocessing), not an unverified production model/learned weight package. Original Bliss23 distance, standardized Bliss, existing Genre/Mood and 1280D/fusion metrics remain necessary independent comparison baselines.
- Design a **new** preregistered diverse, larger, artist+album+recording-disjoint cohort. Block cross-cohort duplicate recordings and attribution overlap, and avoid selecting/tuning using this future final test. Use genuinely independent listener-rated song similarity (or a justified external benchmark) as the primary outcome; compare teacher reconstruction only as secondary analysis, with uncertainty clustered by song/artist and correction for searching many hypotheses.
- Maintain explicit uncertainty: this first 25-track group-heldout is still post-hoc with respect to earlier 100-song inspections; 300 holdout pairs share songs and cannot be counted as 300 independent examples. Genre improvement in distance geometry was small; MoodTheme improvement is teacher-proxy, not perceptual.
- Keep WP1 **General Metric** primary with source-quality/calibration gates and WP2 **optional Personal Metric Learning** active; fully functional 100% General fallback without personal data, optional calibrated 0–100% blend. Do not conflate teacher student, general scorer and user preference learner.
- No new audio/ONNX rescans, worker tuning, mandatory listening, scanner/BlissMixerLab deployments, or PR #16/main edits. User commands must remain a **single complete Windows PowerShell block** using existing Python 3.15 and explicit private read-only source paths; keep song identities and original research DBs private.

## Historical first assignment (29 October 2026 — completed/superseded)

**Next technical implementation should be WP3-R0 + WP2-P0 contracts,
in parallel with any resumed WP1 A/B results.** First implement
synthetic, read-only exact-key Bliss↔Essentia 23D/87D/56D/
1280D *metadata join and aggregate QC* plus synthetic
personal/blend compatibility and fallback tests using the known
learner/host formats. No real private read until a separate
safe, consented, deterministic local procedure exists. No new
compulsory ratings. No unauthorized edits to the other repos.
## Copy/paste handover prompt — 30 October 2026, after approval of full native Essentia 240-song R6

> Continue Lyrion: Mood Analysis on the isolated research branch
> `feat/general-pairwise-similarity-research`. Read
> [the complete WP3-R6 original Essentia C++ 240-song plan](wp3-r6-native-240-essentia-protocol-20261030.md),
> [predeclared machine-readable evaluation](../research/wp3-r6-full-teacher-evaluation-v1.json),
> [the genuine 100-song grouped teacher experiment](wp3-real-grouped-teacher-study-results-20261030.md),
> [the real 240-song R5 source cohort](wp3-independent-cohort-validation-plan-20261030.md)
> and [the WP1/WP2/WP3 permanent strategy](similarity-three-workstreams-strategy-20261029.md)
> before continuing.
>
> ALREADY COMPLETE in the user's Windows environment:
> 100/100 real exact Bliss23/Essentia Genre87/MoodTheme56 + Lyrion identity
> source join; 88 artist/album/recording groups, 75 train / 25 group-disjoint
> exploratory holdout; MoodTheme teacher-distance Spearman raw Bliss 0.442049
> vs train-only Ridge student 0.540662 (NOT human quality and old 25 not
> untouched confirmation). R5 metadata-only real operator run also produced
> a fixed, private 240-song manifest, 15 songs in each of 16 Tempo/centroid
> bins, with no source-recorded artist/album/recording overlap within 240
> or with the old 100. No new 240 Essentia scores or human labels exist yet.
>
> The user EXPLICITLY AUTHORIZED analyzing ALL 240 with original native
> Essentia C++ and producing Genre87, MoodTheme56, Voice2 and one normalized
> pooled 1280D EffNet embedding per song. Do NOT run the previously proposed
> 24-pair Bliss-only pilot as the immediate next step: it is DEFERRED.
> New research-only code exists:
> `scripts/wp3_r6_native_240.py` (R5 source rederivation, frozen SHA/model/
> scanner/native worker/source audio checks and postscan exact 240 heads/
> embeddings validation); `scripts/run_wp3_r6_native_240_windows.ps1`
> (single local Windows PowerShell 5.1/7 wrapper `-Stage Prepare|Scan|Verify|All`);
> `scripts/evaluate_wp3_r6_240.py` (predeclared out-of-cohort teacher
> MAE and 28,680 DEPENDENT distance-pair correlations). CI uses synthetic
> source-shaped data and cannot access private NAS/worker runtime.
>
> The exact previously used Windows binary source SHA is
> `da8fecee23930c2e52abcb473a62b8178b2d5474`, EXE SHA256
> `00a41687fd79c53a536b6de6bf865647ef2d6f9ee453419cc69ca00911f5d82d`,
> verified local binary directory
> `D:\LMS\bliss-mood-private\verified-scanner-40758319812`,
> native C++ worker `D:\LMS\essentia-cli-test\essentia-worker\bliss-essentia-worker.exe`,
> official weights under repo `models`, verified previously reachable
> NAS audio root `\\192.168.1.100\music`. Any absent or drifted
> local prerequisite is a BLOCKER, never excuse to use an unknown binary,
> Rust DSP fallback or public native DLL bundle. Native licensing and
> distribution remain explicitly BLOCKED for unresolved notices.
>
> Next: validate Windows/Linux CI, pull only the research branch, then use
> the complete Windows PowerShell launcher first in `-Stage Prepare`
> (no inference); after source/hash PASS, explicitly choose `-Stage Scan`
> and `-Stage Verify` on the printed private plan, or `-Stage All` only
> with understanding that it performs actual 240 audio analyses.
> Do not change scanner worker tuning: native `--workers auto` is
> fixed-once CPU policy capped at eight, `--threads 1`.
> Scans write exclusively to private ignored native 240 sidecar and
> embedding directory, scanner logs remain PRIVATE, no LMS/playlist
> changes, service restarts or old SQLite overwrites. Request user to
> provide **only anonymous JSON aggregates**, NEVER private manifest,
> source audio, embeddings, model weights, track identities or logs.
>
> The frozen MoodTheme Ridge(alpha 10) student and Genre PLS2 are fit
> ONLY on all previous 100 DEVELOPMENT tracks, and then compared
> on the new source-disjoint 240 teacher results without tuning.
> 28,680 paired song distances share 240 observations and do not
> represent 28,680 independent subjects. Essentia heads are
> pseudo-teachers, not ground truth; they do not show better human
> music similarity even if WP3 distance reconstruction improves.
> WP1 General must remain separately validated and functional;
> WP2 optional Personal learning + calibrated 0–100% blend must
> retain a complete General fallback. Real human/external similarity
> quality evidence needs a separate, consented independent gate.
> Update English research and handover docs with actual findings.
> No changes to `main`, Draft PR #16, Lyrion, other repos or
> native worker performance tuning.
