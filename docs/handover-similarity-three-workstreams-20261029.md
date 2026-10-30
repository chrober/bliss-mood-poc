# Handover: Lyrion General + Personal + Bliss↔Essentia research (29 October 2026)

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

## Next substep (R5) — independent NEW cohort *selection*, not rescanning

The independent identity-disjoint, 240-song **planning/manifest** implementation is available but has not been executed against the user's actual private databases. After synthetic CI gates pass, operator may run the complete [Windows PowerShell launcher](../scripts/prepare_wp3_independent_cohort_windows.ps1) and report anonymous counts. That is a preparation gate, NOT the independently validated listening-quality metric, an Essentia scan, or new model weights. Freeze candidate, then separately plan any future authorized audio and human validation. [Full protocol](wp3-independent-cohort-validation-plan-20261030.md).

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
## Copy/paste handover prompt (updated 30 October 2026)

> Continue project Lyrion: Mood Analysis on branch
> `feat/general-pairwise-similarity-research`. Read
> [the three-workstream research strategy](similarity-three-workstreams-strategy-20261029.md),
> [the current WP3 consolidated provenance/runbook](wp3-consolidated-research-sqlite-20261029.md)
> and [the FIRST genuine 100-song grouped teacher-study findings](wp3-real-grouped-teacher-study-results-20261030.md)
> **before planning any work**.
>
> The authentic Bliss23 / Essentia Genre87/MoodTheme56 / Lyrion library /
> BlissMixerLab artist identity join was successfully verified **100/100**,
> with **88 identity-connected groups** and a **75 train / 25 group-disjoint
> holdout**. The real Windows Python 3.15 teacher-study is **already completed**.
> Genre PLS cut classifier-output MAE **6.92%** and MoodTheme Ridge **13.04%**
> relative to the training-mean baseline. A Bliss-only Ridge student improved
> MoodTheme teacher-distance Spearman from **0.442049 to 0.540662** versus original
> Bliss Euclidean on 300 dependent pairs, while Genre changed only from
> **0.557959 to 0.569599**. This does NOT validate human musical similarity,
> does NOT certify Essentia head numerical parity / audio-byte identity /
> teacher-training independence, and the holdout is NOT untouched because
> the complete same 100-song cohort was explored beforehand.
>
> The MoodTheme candidate architecture is now frozen *without fitted weights* in
> [research/wp3-moodtheme-student-candidate-v1.json](../research/wp3-moodtheme-student-candidate-v1.json).
> The [WP3 R5 240-song new-cohort selector](wp3-independent-cohort-validation-plan-20261030.md)
> has been implemented but NOT yet run on real future songs; the next operator
> step is the source-only Windows PowerShell planner (no audio or listening).
>
> After that: preserve these exploratory findings; freeze *candidate architecture
> and evaluation protocol only*, design a genuinely NEW, more representative,
> group-disjoint independent perceptual/listener evaluation against
> original Bliss and current WP1 Genre/Mood/embedding/fusion baselines,
> then report group-aware statistical uncertainty. WP1 General Metric
> remains primary and available with zero personalization. WP2 optional
> Personal Metric Learning and calibrated 0–100% general/personal blend
> remain separate active development threads with complete no-model fallback.
> WP3 is teacher-distilled Bliss representation research, not automatically
> a new production metric. Do not tune to these 25 songs and call it independent.
> No audio rescans, Pi restart, worker autotuning, obligatory listening or
> deployment without explicit authorization. Preserve private music data,
> use English Markdown docs, and provide one executable complete Windows
> PowerShell block for any local steps. Leave main, Draft PR #16 and
> other repositories untouched.
