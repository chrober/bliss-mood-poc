# Current research handover: similarity representations and Lyrion integration

> **LATEST 30 OCT 2026 WP3 post-selection sanity study:** The operator uploaded a safe anonymous aggregate from real 100-song Bliss23/Essentia87+56 research SQLite. All 3,289 cross-head correlations were defined; Chroma12 versus moodtheme soft had Spearman −0.830495, Chroma6 versus genre metal +0.723552. This was chosen after examining 3,289 same-sample relationships, NOT independent inference or demonstrated improved similarity. Follow-up implemented on isolated `feat/general-pairwise-similarity-research`: `scripts/analyze_wp3_snapshot_stability.py` plus complete Python-3.15 Windows script `scripts/analyze_wp3_snapshot_stability_windows.ps1` and `tests/test_analyze_wp3_snapshot_stability.py`. Reads existing private SQLite query-only, all 253 intra-Bliss Spearman pairs and 21 candidate inter-Essentia-class redundancy pairs, plus all 16 prior post-selected cross-model associations. Runs leave-one-song-out max Spearman shift and 200 deterministic 80%-subsample p10/median/p90/sign consistency checks. All metrics describe perturbations WITHIN the same 100-song cohort: not bootstrap confidence intervals, group-disjoint holdout, external replication, fitted teacher models, general-metric winner or personal model. No original DB writes/ONNX or further Python versions. Next after successful synthetic CI: git pull research branch and run new stability PowerShell script; request only the anonymized aggregate-wp3-stability-*.json, never private SQLite. The actual 100-song sample remains with `NOT_AVAILABLE` group provenance; real native analysis was done earlier, not by the one-DB builder. Need authentic LMS cache snapshot and Lyrion library DB for future grouped WP3 or WP2. Existing main / PR #16 unchanged. See `docs/wp3-consolidated-research-sqlite-20261029.md`.


> **NEWEST WP3 REAL-DATA RESULT / 30 October 2026:** The user ran the new Python 3.15 one-DB builder successfully against existing Bliss and native 100-song Essentia data. Exactly **100/100** valid exact-key Bliss23/Genre87/MoodTheme56 pairs; 0 bad vectors, 0 provenance rejections, 0 Bliss missing; original sources unchanged. The private `benchmark-wp3-research-20261030-064618-7f8c43a3/wp3-research.sqlite` remains local. `group_provenance=NOT_AVAILABLE` with `LYRION_GROUP_SOURCES_NOT_PROVIDED`; do not claim grouped teacher study or independent metric validation. To make progress WITHOUT fabricating group IDs, new `scripts/analyze_wp3_snapshot_correlations.py` + full `scripts/analyze_wp3_snapshot_correlations_windows.ps1` calculate **3,289 descriptive-only Pearson and tie-aware Spearman correlations** on the existing single SQLite (no new source paths or dependencies beyond Python 3.15); report top associations and aggregate counts only, clearly flag multiple comparisons and lack of independent holdout. Synthetic Linux/Windows CI is separate; no private user features were uploaded. Plugin's metadata snapshot writer uses `Slim::Utils::OSDetect::dirsFor('cache')/BlissMixerLab/artist-repeat-identities.sqlite` on the Lyrion host (actual Windows path NOT yet established), and `library.db` remains an additional authentic source. Documented in [single-DB WP3 report](wp3-consolidated-research-sqlite-20261029.md). Next user action: git pull research branch, run descriptive PowerShell script, share only aggregate result if desired. WP1 General Metric and WP2 optional Personal Metric Learning unaffected; main and PR #16 unchanged.


> **LATEST WP3 ARCHITECTURE / 29 October 2026:** The operator explicitly approved replacing repeated manual four-DB prompts with **a new private single research SQLite created from existing analyses**. Implemented [Python builder](../scripts/build_wp3_research_db.py), [full standalone Python-3.15 Windows launcher](../scripts/build_wp3_research_db_windows.ps1), [schema and operating documentation](wp3-consolidated-research-sqlite-20261029.md) and synthetic integration tests. The default source pairing is the already documented local D:\LMS\bliss-mood-poc\bliss.db plus D:\LMS\bliss-mood-poc\benchmark-native-similarity-100-20261029\native-features.sqlite (the 100 frozen native Essentia songs, no rescan). It strictly validates exact keys/features/model/audio-head provenance before **exclusively creating** a gitignored private benchmark-wp3-research-*/wp3-research.sqlite. Missing actual Lyrion snapshot/library metadata leaves group fields NULL and **blocks supervised train/holdout research**, but feature DB creation is still useful. Optional exact-key identity paths may be explicitly provided as LYRION_REPEAT_SNAPSHOT_DB and LYRION_LIBRARY_DB; no assumed Pi paths and no automatic new scans. Existing grouped teacher entrypoint accepts --research-db for the one-DB dataset and refuses unverified group provenance. Only the existing Python 3.15 is used. This new launcher replaces the former four-path `run_grouped_bliss_essentia_research_windows.ps1` as the preferred local onboarding route; that former path remains for reproducing older grouped studies. Source DBs, main, PR #16, user ratings, worker settings, and adjacent repositories are unchanged. CI uses synthetic (not private) data; do not claim real join counts before the operator's run.


> **Windows PowerShell 5.1 runtime quoting fix (29 October 2026):** The user's first attempt after selecting Python 3.15 failed **before reading any data**: PowerShell's native argument forwarding removed the nested double quotes in `python -c 'import sys; print(str(sys.version_info.major) + "." + ... )'`, yielding `SyntaxError`. The Python 3.15 installation is correct and does not need reinstalling. The one-block launcher now obtains the version with `python --version` and regex-checks 3.15 without quoted Python string literals. Its later scientific-package check uses a quote-free `python -c` argument. The read-only source preflight passes its list of arguments via explicit PowerShell variable splatting. The dedicated WP3 CI now **executes** this exact launcher runtime path on Windows PowerShell **5.1** and **7**, rather than only parser-validating the script. The existing four-source real-data preflight has **not yet been executed on the user's local databases** as of this change. Latest bugfix is isolated on `feat/general-pairwise-similarity-research`; no PR #16, main, Python runtime installations, native scans, or personal song data were changed.


> **LATEST 29 OCT 2026, mandatory operator choice:** User has Python **3.15.0** and explicitly does NOT want Python 3.13 installed. The research branch WP3 PowerShell `run_grouped_bliss_essentia_research_windows.ps1` now uses only `python` 3.15 for read-only no-write source grouping preflight AND a newly isolated Python 3.15 venv for the grouped teacher numerical study. Pinned 3.15 packages: NumPy 2.5.4, SciPy 1.18.1, scikit-learn 1.9.1, joblib 1.5.2, threadpoolctl 3.6.0 (file `research/requirements-wp3-py315.txt`). Do not ask to install 3.13; do not silently install a runtime or change the user's global Python. Real DB access and teacher results remain unverified. Existing `PASS_EXPLORATORY_TOLERANCES` relates to a separate native backend comparison. Run only local four-source provenance checks and then, if ready, real teacher exploration; no new surveys, worker tuning or PR #16 changes.






> **WP3 REAL-DATA PREFLIGHT READY (29 October 2026):** The source-backed Lyrion/BlissMixerLab metadata bridge and complete Windows `& { ... }` launcher now have a **stdlib-only no-write preflight** (`scripts/derive_lyrion_research_groups.py --preflight`), always run **before** private metadata output, numerical package installs or similarity experiments. Aggregate outputs contain `ready_for_grouped_study`, `blocking_reason_code`, verified paired-song counts, missing recording MBIDs and artist/album/recording-disjoint train/holdout counts. No path guessing, no source changes, no audio scan or user labels; require existing snapshot schema **and** scan/root metadata shape, while documenting that active LMS freshness remains unverified. If blocked, fix actual source availability/identity rather than relaxing disjointness. If ready, run only the already implemented local WP3 teacher-development study and then seek independent music-quality labels. No real joined Bliss23/Essentia87/56 data have been accessed here. See [source audit](bliss-essentia-lyrion-existing-metadata-source-20261029.md). WP1/WP2 remain parallel, no new compulsory votes/worker tuning/PR #16 edits.


> **CURRENT RESEARCH HANDOFF / 29 OCT 2026:** WP3 metadata provenance discovery now reuses an ALREADY EXISTING Lab source: chrober/lms-blissmixer-lab/BlissMixerLab/RepeatIdentitySnapshot.pm creates artist-repeat-identities.sqlite with exact relative track_file, Lyrion track ID, urlmd5, recording MBID and credited artist identities. Lyrion SQLite library.db has authoritative tracks.album → albums.id. See [source discovery and remaining actual-data blockers](bliss-essentia-lyrion-existing-metadata-source-20261029.md). [derive_lyrion_research_groups.py](../scripts/derive_lyrion_research_groups.py) safely makes the private grouping JSON from 4 existing read-only DBs; [one-block Windows runner](../scripts/run_grouped_bliss_essentia_research_windows.ps1) handles an isolated branch worktree, Git fetch, Python 3.15, pinned deps, SHA256, private group derivation and aggregate-only WP3 source study. Missing/invalid recording MBIDs form one conservative unknown group, and incomplete artist/album identity causes fail-closed. Linux/Windows source-shaped CI passed; **not executed on real user files**. No new metrics or personalization claimed. Next action should establish source availability, run the real grouped development source study when safe, then independent music-quality holdout; no mandatory new votes, no worker tuning, no native rescans, no PR #16/main/other-repo edits.


> **NEXT SESSION STATE 29 OCT 2026:** The three permanent workstreams are WP1 always-on General Similarity, WP2 optional Personal Metric Learning + calibrated 0–100% General/Personal blending, WP3 Bliss 23D↔Essentia representation relationships with improved Bliss-only geometry. The isolated research branch has completed **synthetic technical WP3-R3** (read-only local real-source Bliss + Essentia exact-key join with explicit private artist/album/recording identities, aggregate Pearson/Spearman, Ridge, PLS, PCA-CCA, teacher-distilled Bliss-only proxy) and **WP2-P3** (existing Rust learner SHA-pinned private train-only bundle runtime gate, complete DB-song-set verification, output matrix numerical checks). See [new source/CI report](bliss-essentia-local-study-verified-learner-20261029.md). Both Linux/Windows end-to-end tests PASS; *no real user data, additional votes, learner training or new musical-quality results*. Next: obtain legal, exact-identity/group-verified real paired source first, no guessed paths, and independent listening/task labels for Bliss-only improvement; user will not be asked for more compulsory ratings. PR #16 and related repos untouched, native same-100 comparison completed, no worker tuning. Windows local launch must be one verified automated PowerShell block after prerequisites known.


> **IMPLEMENTATION HANDOFF 2026-10-29 — WP3-R2 and WP2-P2:** The separate research branch now includes [grouped, train-only scikit-learn Ridge/PLS/PCA-limited CCA, Bliss-only teacher-geometry distillation, and SHA256-bound private train-only Bliss learner staging](bliss-essentia-teacher-models-train-only-learner-20261029.md). WP3 model fitting is on group-disjoint train data only; the teacher-geometry proxy consumes only 23D Bliss at inference and compares against Essentia **pseudo-teacher** distances (not human musical quality). WP2 isolates the unchanged Rust learner's future inputs to a NEW private SQLite containing ONLY training song features and a training-only triplet JSON. A private manifest records exact input/output hashes; **no learner has run, no personal model or real correlations have been measured, and no additional compulsory listening is requested**. Both synthetic workflow families passed Ubuntu and Windows. Next: permissioned group/source-verified real paired-feature study for Bliss-only downstream quality and separately authorized train-only Rust learner execution with heldout validation. Continue WP1 concurrently; PR #16 and related repos remain unmodified.


> **CURRENT SIMILARITY NEXT-SESSION STATE, 29 October 2026:** Three permanent goals: WP1 General Metric; WP2 optional Personal Metric Learning with safe 0–100% blend; WP3 Bliss 23D ↔ Essentia feature relationships and improved Bliss-only similarity. WP2-P0 and WP3-R0 were completed previously; **WP2-P1/WP3-R1 are now implemented** on isolated branch. See [leakage-safe grouped correlation and personal-triplet research](bliss-essentia-grouped-relationships-personal-evaluation-20261029.md): shared artist/album/recording/triplet components, train-only feature selection with separately measured holdout correlations, strict no-holdout fallback rejection, original Bliss Learner Mahalanobis format reuse but **no claim of independent trained model lift**. No real private Bliss/Essentia correlations were measured, no new learner trained, no new compulsory votes. Existing successful native scan and 12-pair review must never be repeated. Source PR #16 and other repositories are still unchanged; continue WP3-R2 data/partial/CCA/PLS with grouped holdouts and WP2-P2 train-only learner provenance in parallel with General research, after real source availability and consent are verified.


> **IMPLEMENTATION STATE UPDATE / 29 OCT 2026:** The parallel WP3-R0 exact-key Bliss→Essentia read-only coverage audit (23D/87D/56D with optional 1280D original research sidecars) and WP2-P0 fail-safe General/Personal blend contract (0–100% personal influence, no valid model ⇒ 100% General), plus existing Bliss learner/survey format inspection, are implemented and synthetically tested on isolated branch. See [WP2/WP3 implementation handoff](bliss-essentia-join-personal-contracts-20261029.md). No private files read, no personal training, no cross-repository code changes, no new native scans, no additional mandatory user listening. The next slices are WP3-R1 group-aware feature relationship analysis and WP2-P1 grouped personal learner evaluation. Do not treat structural learned-matrix compatibility as calibrated Personal scoring or the first 100-song cohort as generalizable new quality evidence.


> **Authoritative next-session strategy — 29.10.2026, isolated research branch:** Read [Unified General + Personal + Bliss↔Essentia Strategy](similarity-three-workstreams-strategy-20261029.md) **before** historic scanner/PR#16 phase instructions. All THREE work packages are active: WP1 General Similarity Metric; WP2 Personal Metric Learning with independently calibrated 0–100% General/Personal blend, genuine usable-model fallback and reuse of `chrober/bliss-learner` / `chrober/lms-blissmixer-lab`; WP3 Bliss 23D ↔ Essentia 87D/56D/1280D correlations, CCA/PLS/prediction and **learning better Bliss-only similarity**, not just additional Essentia ranking. Start WP2 contract/reuse and WP3 read-only paired-feature inventory in parallel with WP1. User's 12 ratings and real native 100-song comparison are COMPLETE; do not solicit more mandatory listening, rerun preflight/scan, or autotune workers. No edits to Draft PR #16, original data or other repos. At this handover MTT global fusion [CI 40881326086](https://github.com/chrober/bliss-mood-poc/actions/runs/40881326086) failed on publisher HTTP-range timeout; it yielded no new real fusion scores. Windows local work must use one complete automatic `& { ... }` script; do not invent file paths or rerun partial private outputs. Older directions below are historical unless consistent with this update.


**Updated:** October 28, 2026. **Read first:**
[Central phase-0-to-6 research and integration roadmap](similarity-lyrion-roadmap.md).
The roadmap contains four Mermaid diagrams, status, research constraints,
and small stop/go work packages. This handover summarizes the current state;
the preserved sections further below record **historical milestones**,
including statements that have since been superseded.

**Critical status correction:** Phase **0 is not completed**.
Offline 87D Genre, 56D Mood/Theme and optional 1280D
EffNet song-feature extraction exist for research;
the full matrix of broad numerical reference parity,
cross-platform correctness, deployment and licensing
release gates is still open. Phase **2** is a bounded
read-only audit of compatible representations for
the **same songs in the user's library**,
not a full rescan. Production-wide feature
lifecycle belongs to phase **6**, after all gates.

## Latest result: human 12-pair pilot completed; ordinal evaluator ready (2026-10-28)

**The user has completed all 12/12 human-rated song pairs**:
24 distinct songs, 60/60 valid numerical values (four 1–5
musical dimensions plus 1–3 confidence), and seven textual
comments. The reviewed Excel file in chat uses **Windows-1252
with tab delimiters**, not the original UTF-8 comma layout.
One comment identifies **pair 10** as a spoken interview/comment,
not a normal music track. The reviewer finished before opening
the locally sealed model-score audit. No original ratings were
uploaded to GitHub.

**Implemented and verified:**
[`scripts/evaluate_local_listening_pilot.py`](../scripts/evaluate_local_listening_pilot.py)
reads this Excel CSV and the original private
`selection-audit-private.json`, verifies all 12 exact
ordered left/right pairs, and calculates model-vs-human
Spearman rho, Kendall tau-b (with ties), leave-one-out
sensitivity and numbered rank disagreements for
**five frozen untrained models × four human rating axes**.
It reports both **12 pairs** and **11 music-only** after
an explicit `--nonmusic-pairs 10` flag. Tests:
[`tests/test_evaluate_local_listening_pilot.py`](../tests/test_evaluate_local_listening_pilot.py),
**Linux/Windows Python CI PASS 40757186145**.
No private filenames, paths, feature vectors or notes
are emitted into the aggregate or numbered reports.

**Current operational blocker:** Only the human CSV was shared
in chat; the frozen private selection-audit JSON was NOT shared.
Therefore **no model-vs-human correlations have yet been
computed on the real 12 pairs**. Run the script **locally**
with the existing original private audit, preserving both
inputs, in a new ignored report directory. The complete
working Windows PowerShell command and interpretation
protocol are in
[12-pair evaluation runbook](similarity-local-listening-pilot12-evaluation-2026-10-28.md).
It is safe to share only the *anonymized aggregate report*
if the owner wants interpretation. The output is exploratory
and cannot establish universal metric superiority or
legitimate general-fusion weights from twelve selected
pairs.

**Next action, not code generation or more inference:**
run the **local** 12-pair evaluator with `--nonmusic-pairs 10`,
inspect the model/rating matrix, explain rank disagreements,
then predeclare a separate larger evaluation block. Keep
primary research on the mandatory untrained GENERAL metric;
personal learning and 0–100% blend remain optional.

## Current binding decision: general-purpose baseline plus optional personal learning (2026-10-22)

**Primary goal UNCHANGED:** determine a strong, independently
evaluated GENERAL song-similarity metric that works for any new
listener without personal training data. It may involve Genre 87D,
Mood 56D, pooled EffNet 1280D, and potentially Bliss 23D after
fair same-song benchmarks and appropriate calibration.
**No general-metric winner, learned weights, production deployment
or final playlist candidate strategy has been established.**

**Optional extension:** each user may learn a *separate* personal
metric from their own odd-one-out / most-similar-pair triplets,
building conceptually on
[`chrober/bliss-learner`](https://github.com/chrober/bliss-learner)
and
[`chrober/lms-blissmixer-lab`](https://github.com/chrober/lms-blissmixer-lab).
A configurable **0–100% PERSONAL influence slider** blends
personal with general similarity **after score calibration**:

```text
alpha_effective = (valid compatible personal model) ? (slider_percent/100) : 0
S_effective = (1-alpha_effective)*S_general + alpha_effective*S_personal
```

**No usable personal model => effective 0% personal, 100% GENERAL,
whatever the stored slider value.** With a valid model, 0% is
exactly general-only, 100% exactly personal-only, and values
between interpolate calibrated scores. On failed/stale/training
models, or incomplete personal-feature query coverage, consistently
fall back to general-only; do not disrupt playback or change
stored user preferences. Regularize personal learning, use
independent held-out triplets, and keep per-user data local
and isolated.

**Four distinctions to preserve in future sessions:**
A/B/C compares *general* representations/feature fusion;
general-vs-personal blending is a second scoring layer;
Bliss-first/feature-first/hybrid are separate candidate-source
strategies; the existing BlissMixerLab `learned_blend`
modifies its own 23D Bliss learned matrix and is **not the new
general/personal slider**. No changes have been made to
those external repositories or to the upstream mixer.

**Canonical requirement and proposed research gates:**
[General-first and optional personalized 0–100% blend](similarity-general-personal-blending-architecture.md).
[Current overall roadmap](similarity-lyrion-roadmap.md) and
[Lyrion integration constraints](lyrion-bliss-mood-genre-integration.md).

## Goal: compare the representation, not just the distance function

Three representations are being investigated:

| Candidate | What it compares | Current status |
| --- | --- | --- |
| **A — Classifier head vectors** | Independent 87D Genre and 56D Mood/Theme Sigmoid scores, using cosine, centered cosine, weighted Jaccard and previous alternatives | Extensively explored on MTT, FMA and DEAM reference tasks |
| **B — Direct audio embedding** | Pooled 1280D Discogs-EffNet patch features, songwise L2 and cosine | Implemented as a separate versioned research export; same-song MTT and FMA studies completed |
| **C — Calibrated fusion** | Genre/Mood and direct audio similarities combined with explicit scale and abstention policy | Four fixed triplet-local rank ablations evaluated; transferable fusion not validated |

**Keep the next level separate:** Bliss-first, feature-first
and hybrid **candidate generation** are Lyrion playlist
architectures. They are not methods A/B/C and
remain undecided. A combination of embeddings and head
scores can be used in any candidate strategy.
See [representation-level contract](similarity-three-representation-approaches-handover-2026-10-21.md),
[technical A/B/C handover](similarity-representation-comparison-handover-2026-10-21.md),
and [Bliss integration plan](lyrion-bliss-mood-genre-integration.md).

## Latest verified research evidence

- **MTT:** 346 unique unordered human odd-one-out questions,
  293 with a unique human majority and 53 human ties;
  1,019 clips. Direct 1280D cosine **182/293 = 62.12%**,
  Genre cosine **191/293 = 65.19%**,
  Mood cosine **192/293 = 65.53%**,
  Mood centered cosine **193/293 = 65.87%**.
  [Full A/B PASS 39617159250](https://github.com/chrober/bliss-mood-poc/actions/runs/39617159250);
  [synthetic numeric replay PASS 39618323154](https://github.com/chrober/bliss-mood-poc/actions/runs/39618323154).
  No MTT human questions remain as a fresh holdout.
- **Fixed rank fusion C (exploratory):**
  [PASS 39619708040](https://github.com/chrober/bliss-mood-poc/actions/runs/39619708040);
  equal-rank Audio+Genre **163/293**,
  Audio+Mood **170/293**, Genre+Mood **167/293**,
  all three **192/293** with **283/293**
  prediction coverage. Unfused Mood centered
  remains **193/293, 100% coverage**.
  A local midrank is not a global per-song score.
- **FMA-Small official VALIDATION:** same 80
  catalogue-screened, artist-distinct recordings
  and 79 candidates per anchor; direct embedding
  cosine P@5 **0.2800**, Genre cosine **0.3200**,
  Genre centered **0.3225**,
  [PASS 39625087310](https://github.com/chrober/bliss-mood-poc/actions/runs/39625087310).
  Potential exact MTG artist/title matches excluded
  (42/800 VALIDATION songs). **FMA official TEST
  remains untouched**; nonmatches are not evidence
  of full model training independence.
- **FMA bounded music cache:** 80 selected MP3s,
  **76.51 MiB**, original archive/per-MP3
  SHA256 verified;
  [cold 39632517381](https://github.com/chrober/bliss-mood-poc/actions/runs/39632517381)
  and [warm cross-workflow 39633485262](https://github.com/chrober/bliss-mood-poc/actions/runs/39633485262)
  **PASS**. The 7.2-GiB download was skipped on
  the restored warm run.
- **DEAM filtered 240 songs:** 197 earlier excerpts
  and 43 full-song 2015 recordings; old Mood-Cosine
  mean-query VA Spearman **0.286784551387186**
  independently replayed. New paired 1280D A/B
  not completed: the evaluator's original
  sample-hash serialization mismatch was fixed,
  [Linux/Windows CI 39638092328](https://github.com/chrober/bliss-mood-poc/actions/runs/39638092328)
  **PASS**; later runs were blocked by the
  official `cvml.unige.ch:443` host outage.
  [Fast-fail source check 39639506656](https://github.com/chrober/bliss-mood-poc/actions/runs/39639506656)
  confirms failure before a costly build.

These reference targets are not interchangeable:
MTT human odd-one-out, FMA coarse Genre,
DEAM valence/arousal proximity and local playlist
transitions measure different things.
All current results are exploratory; there
is **no production winner** or valid
post-hoc weight-fitting holdout.

## Latest verified M1/M2 checkpoint (2026-10-21)

The user completed the 100-song research feature-coverage gate:
**100/100 same-song 87D Genre, 56D Mood and 1280D Embedding vectors**
passed the independent read-only coherence audit. Zero missing embeddings,
invalid exports or audio/encoder mismatches. Phase 0 remains partially open.

M2 preparation is available in
[`scripts/propose_local_embedding_ab_pilot.py`](../scripts/propose_local_embedding_ab_pilot.py)
and passed [Linux/Windows CI 39668802990](https://github.com/chrober/bliss-mood-poc/actions/runs/39668802990).
The user generated the original blinded pilot
(`BLINDED_REVIEW_READY`) using 24 distinct songs and
all 100 matching features. **The human review is now
complete** as of October 28, 2026 (12/12 pairs;
60/60 numeric fields; seven comments). The frozen
private model-score audit remains local and is now
available to the human reviewer for **post-blinding**
evaluation. The selection reported
`earlier_review_pairs_excluded=0`, which does NOT prove
that the prior eight-pair sample is disjoint.
See the [evaluation runbook](similarity-local-listening-pilot12-evaluation-2026-10-28.md).
Never overwrite or commit original human ratings.

## Next actions, prioritized (October 28, 2026)

1. **Immediately run the real 12-pair ordinal evaluation locally**
   against the sealed private `selection-audit-private.json`
   using the new script. Flag interview/nonmusic **pair 10**,
   preserve the full 12-pair analysis and 11-pair sensitivity.
   Publish no private paths, music identities, user CSV or audit.
2. Examine the 5×4 frozen model-vs-human rank metrics,
   ties, leave-one-out ranges and numbered disagreements.
   Expect a tiny, purposively sampled diagnostic study,
   **not a winning general metric**. Do not tune general fusion
   on those twelve labels and report that fit as independent
   evidence. Check any overlap with the original eight pairs.
3. **General-metric research remains primary.** Predeclare a
   disjoint, more representative block of music ratings and
   external MTT/FMA/DEAM controls as sources permit. Continue
   testing A/B/C/general fusion on independent evidence.
4. Design separate, **optional** active triplet selection
   and small regularized personal metric learning, drawing
   on the two existing Bliss/Lab projects. Then evaluate
   separately on held-out personal decisions, without
   modifying the mandatory general baseline or prematurely
   implementing the 0–100% personal-blend control.
5. Retain the distinct candidate-source comparison (Bliss-first,
   feature-first, hybrid); production release remains blocked
   by outstanding phase-0 validation and licensing gates.

**Implementation boundaries:** Only PR #16
(`feat/similarity-metric-evaluation`), kept Draft;
no changes to main, PR #13/#17, upstream Bliss or the
other two repositories without separate authorization.
Keep local files, listening data, track paths and model
vectors private. GitHub Actions for Rust builds;
PowerShell blocks are self-contained `& { ... }`.
The [local phase-2/M2 plan](similarity-local-library-retest-plan-2026-10-21.md)
contains previous Windows/export details.

## Superseded M1 engineering notes (historical, NOT the next action)

The first version of the research-only Windows embedding
CLI erroneously required `--db` when supplied with
`--track-key`, even for `--embedding-out`. The repaired
Windows binary in [run 39664316069](https://github.com/chrober/bliss-mood-poc/actions/runs/39664316069)
and independent ONNX regression
[run 39664440263](https://github.com/chrober/bliss-mood-poc/actions/runs/39664440263)
passed. The user subsequently exported **100/100** local
song embeddings and confirmed **100/100** joined
Genre/Mood/Embedding provenance matches.
The old first-run Windows binary
[39661674510](https://github.com/chrober/bliss-mood-poc/actions/runs/39661674510)
is obsolete. **Do not repeat the old one-song preflight
or the 100-song scan as the current next step.**

## Historical engineering and experiment handover (archival)

The following originally English material covers
earlier scanner work, GitHub Actions binary workflows,
Windows/NAS testing, adaptive workers and
Lyrion SPI architecture. It is retained for
reproducibility, not as an override of the
current roadmap or verified subsequent studies.

# Chat handover — adaptive offline feature scans (2026-10-19)

> **UPDATED MTT HOLDOUT METADATA AUDIT, 21 OCT 2026:**
> [GitHub Action 39592331265](https://github.com/chrober/bliss-mood-poc/actions/runs/39592331265)
> successfully checked artist-hash sensitivity without any new audio
> inference or human metric inspection: cutoff 51/256 gives 162 dev /
> 4 candidate holdout / 180 excluded mixed; cutoff 85 gives 86/13/247;
> cutoff 128 gives **31 dev / 56 potential holdout / 259 excluded**.
> Under cutoff 128, 8 of 56 potential holdout triplets share artists
> with the prior four-question smoke; the remaining **48** were not
> exposed in that run. This DOES NOT eliminate the one-giant-artist
> component or establish population/generalization reliability.
> Freeze one artist split and exclusions BEFORE scoring the 48
> candidate test questions, and never optimize using their labels
> or model performance. See
> [sparse-audio methodology](magnatagatune-sparse-audio-benchmark-2026-10-21.md).
>
> **MTT SPARSE REAL AUDIO E2E PASS + HOLDOUT LIMIT, 21 OCT 2026:**
> [ZIP membership 39589694423](https://github.com/chrober/bliss-mood-poc/actions/runs/39589694423)
> **PASS** using only 8 MiB HTTP Range tail: all **1,019** referenced MP3s
> found among 25,863 ZIP members, 0 ambiguous/missing. Three consecutive
> ZIP parts total 2,972,769,864 bytes; needed compressed MP3 member sizes
> sum to 116,910,845 bytes. **533 ordered records reduce to 346 unique
> unordered triplets**, requiring aggregated clip-ID votes.
> [Real Rust-v5 sparse-audio workflow 39590801662](https://github.com/chrober/bliss-mood-poc/actions/runs/39590801662)
> **PASS**: 4 deliberately high-consensus artist-disjoint DEVELOPMENT triples,
> 12 clips CRC checked, 12 bounded HTTP 206 requests transferring only
> **1,385,735 bytes**, 14.48 seconds transfer+feature inference.
> Both heads and seven metrics ran, result aggregate-only. Mood cosine
> got 3/4 majority choices, **NOT generalization evidence**; most job
> overhead was building Rust-v5 (~88 sec). See
> [sparse audio benchmark doc](magnatagatune-sparse-audio-benchmark-2026-10-21.md).
>
> **CRITICAL SCIENTIFIC FINDING:** artist-group preflight
> [39591601421](https://github.com/chrober/bliss-mood-poc/actions/runs/39591601421)
> shows **ALL 214 artists + 346 unordered triples in ONE connected
> artist co-occurrence component**. Strict component-disjoint 80/20
> holdout impossible without dropping triples. Hash-based artist
> split gave 162 development, only **4** held-out, 180 mixed excluded.
> This is scientifically inadequate for metric selection. Do NOT
> present four selected development triples as independent test data.
> Future work: larger descriptive MTT evaluation with dependence/vote
> uncertainty disclosed, plus separate human-similarity confirmation.
> No production decision, no merge, no private music, PR #16 Draft.
>
> **LATEST MTT REAL AUDIO + ARTIST HOLDOUT (21 OCT 2026):**
> Original 3-part ZIP full central-directory membership:
> [39589694423](https://github.com/chrober/bliss-mood-poc/actions/runs/39589694423)
> PASS. Only 8 MiB ZIP tail downloaded; 25,863 ZIP MP3s;
> all 1,019 required clips matched, 346 unique unordered triplets
> from 533 rows, 116,910,845 compressed MP3 bytes required in total.
> Sparse HTTP range-only Rust-v5 end-to-end
> [39590801662](https://github.com/chrober/bliss-mood-poc/actions/runs/39590801662)
> PASS: 4 high-consensus artist-disjoint development triplets,
> 12 real clips analyzed, 1,385,735 audio-range bytes, 14.5 seconds
> for download+analysis, all seven similarity metrics and both
> genre/mood heads, aggregate artifact only. Test is smoke, not
> independent held-out evidence.
>
> Subsequent metadata-only holdout feasibility PASS
> [39592331265](https://github.com/chrober/bliss-mood-poc/actions/runs/39592331265):
> Artist graph is a **single 214-artist/346-triple component**;
> strict connected-component holdout impossible. SHA-256 artist-hash
> 50/50 preferred split: 31 dev, 56 holdout, 259 mixed excluded.
> Eight holdout triplets share an artist with prior smoke and must be
> excluded, leaving **48 unexposed holdout triplets**. No model
> outputs were used to select the split; frozen before further
> audio evaluations. The benchmark code **does not yet enforce**
> this new split for future audio studies; do that next, with tests,
> before any expansion. See
> [MTT sparse-audio + holdout details](magnatagatune-sparse-audio-benchmark-2026-10-21.md).
> Synthetic Linux/Windows CI [39592264225](https://github.com/chrober/bliss-mood-poc/actions/runs/39592264225)
> PASS, metadata audit PASS. Keep PR #16 Draft, no main/PR #13/17
> merge, no user music, no production metric winner.
>
> **MTG/MAGNATAGATUNE REAL METADATA PREFLIGHT PASS (21 OCT 2026):**
> Both agreed metadata-only workflows now completed successfully,
> with **no audio downloads**. MTG-Jamendo split-0 / official
> Essentia JSON classes audited at
> [39586686845](https://github.com/chrober/bliss-mood-poc/actions/runs/39586686845):
> 87 Genre head classes, train/validation/test 32572/11043/11479;
> 56 Mood/Theme, 9949/3802/4231; zero artist-ID/track-ID
> overlap across official splits (not proof of exact ONNX training
> provenance or no encoder training overlap).
>
> MagnaTagATune schema + **human votes and clip joins** validated
> in [39587323227](https://github.com/chrober/bliss-mood-poc/actions/runs/39587323227):
> 533 odd-one-out triple questions, 7650 human votes, 1019 distinct
> referenced MP3 paths, 903 apparent song groups, 214 artist
> strings; 87 tied top-vote questions, 228 unique >=70% consensus
> questions, 160 unanimous. The source clip catalog has 31382 rows,
> of which 5519 have empty MP3 path. These are research metadata
> only. The corrected parser detects original CSV delimiters;
> continuous synthetic Linux/Windows CI
> [39587511195](https://github.com/chrober/bliss-mood-poc/actions/runs/39587511195)
> PASSED. No unfiltered audio benchmark executed or metric selected.
> See [formal preflight results](external-evidence-preflight-results-2026-10-21.md).
>
> **NEXT:** Plan a rights-compliant, bounded study processing the
> 1019 distinct MTT clips only; first verify physical ZIP member
> mapping and archive integrity/disk budget, then paired, artist-grouped
> human triplet agreement and uncertainty against all seven metrics.
> For MTG-Jamendo, consider auxiliary human classification annotations
> on official split-0 test data, but DO NOT pretend these are
> independent evidence of original ONNX training. Every audio workflow
> gets stage walltimes, worker counts, peak RAM and throughput.
> No main/PR #13/PR #17 merges.
>
> **EXTERNAL EVIDENCE ROADMAP / PERFORMANCE POLICY — 21 Oct 2026:**
> The user explicitly wants **continued GitHub Actions runtime optimization
> alongside musical evidence research**. See the detailed
> [MTG-Jamendo + MagnaTagATune plan](similarity-external-evidence-roadmap-2026-10-21.md).
> Priority: (1) metadata-only MagnaTagATune comparison/vote/clip schema and
> licensing audit (533 human odd-one-out triples, ~7650 votes, CC BY-NC-SA
> 3.0 dataset, GPLv3 scripts); (2) in parallel, metadata/split/model-provenance
> audit of MTG-Jamendo 87-Genre/56-Mood heads and derived human annotations;
> (3) only after rights/metadata validation, bounded MagnaTagATune
> audio benchmark with corrected pinned Rust-v5, triplet voting agreement,
> human consensus and paired uncertainty; (4) final independent testing
> and Lyrion playlist validation. **Do not download huge Jamendo audio
> collections or MagnaTagATune split archives until validated.**
> Every expensive workflow must report elapsed times for build, download,
> inference and evaluation; worker count, CPU/RAM and throughput;
> optimize measured bottlenecks. External per-track analyze-features
> loops remain serial; adaptive scan-features workers are not enabled
> there. No production metric selection or merge.
>
> **FMA GENRE VALIDATION E2E PASS, 21 Oct 2026:** Corrected
> [run 39583233757](https://github.com/chrober/bliss-mood-poc/actions/runs/39583233757)
> passed. Official FMA-Small archive has **3 size-anomalous MP3s**,
> safely excluded, with 7,997 usable MP3s. The **80** seeded, artist-unique
> validation tracks (10 per genre, FMA test split untouched) were processed
> by pinned genuine Rust-v5, and an
> [aggregate-only artifact](https://github.com/chrober/bliss-mood-poc/actions/runs/39583233757/artifacts/12338242831)
> published. P@5 random expectation .1139; RMS .3175, cosine .3500,
> centered cosine .3525, weighted Jaccard .3550, old Top-K .3150,
> ranked Top-6 .3150 and ranked Top-12 .3400. Exploratory ONLY,
> no metric chosen. See docs/fma-genre-benchmark-plan.md and
> docs/github-actions-trigger-and-worker-audit-2026-10-21.md.
> Trigger change to push-only CI and docs-only skip is verified;
> Rust adaptive workers are not used by per-song AnalyzeFeatures.
>
> **GH CI / FMA FOLLOW-UP — 21 Oct 2026:** The real FMA validation
> run [39581435733](https://github.com/chrober/bliss-mood-poc/actions/runs/39581435733)
> failed **before inference**, after downloading the archives, because
> `scripts/benchmark_fma_genre.py` rejected one unexpectedly sized MP3
> anywhere in the archive. The code now excludes isolated size anomalies
> and fails closed on excessive damage; synthetic tests were added.
> The corrected GH validation run is
> [39583233757](https://github.com/chrober/bliss-mood-poc/actions/runs/39583233757):
> **verify completion/artifact before claiming FMA retrieval results**.
> General CI was split into Rust-only and Python/PowerShell-only workflows;
> both now use path-filtered **push** triggers (not push+pull_request),
> so each in-repository commit runs a check at most once per relevant
> workflow, and docs-only changes do not execute those checks. See
> [GitHub Actions audit](github-actions-trigger-and-worker-audit-2026-10-21.md).
> FMA/DEAM audio analysis is currently **serial** (`analyze-features` for
> each track, `--threads 1`); adaptive workers belong to `scan-features`
> and are not active. Benchmark fixed-two-worker vs serial only after
> an isolated, validated batch/sidecar implementation.
>
> **UPDATED CURRENT STATUS 21 OCT 2026 — 240-song DEAM and FMA validation:**
> Two 240-song DEAM GitHub Actions benchmarks passed: unfiltered
> [39577605466](https://github.com/chrober/bliss-mood-poc/actions/runs/39577605466),
> conservatively exact MTG-catalog-match-filtered
> [39579552118](https://github.com/chrober/bliss-mood-poc/actions/runs/39579552118).
> Full metadata-only DEAM/MTG screening passed
> [39579084649](https://github.com/chrober/bliss-mood-poc/actions/runs/39579084649):
> **75 possible metadata matches**, not proof of model-training usage.
> Filtered Mood VA-proximity query Spearman: weighted Jaccard .2888,
> cosine .2868, centered .2813, rms .2711, ranked top-6 .2721,
> ranked top-12 .2745, historical cutoff top-K .1903
> (216/240 comparable anchor queries). Different samples, no winner.
>
> FMA-Small metadata-only workflow passed
> [39580107275](https://github.com/chrober/bliss-mood-poc/actions/runs/39580107275):
> 8,000 tracks, 8 exactly balanced genres, artist-disjoint official
> training/validation/test split counts 6,400/800/800.
> New scripts/benchmark_fma_genre.py + regression tests implement
> real Genre retrieval metrics and bounded artist-unique VALIDATION
> evaluation; first live 80-song workflow
> [39581435733](https://github.com/chrober/bliss-mood-poc/actions/runs/39581435733)
> was started, check final run logs/artifact before reporting its result.
> The official FMA test split is reserved. All research workflows use
> corrected pinned Rust-v5 source from PR #17 in separate checkout,
> without merging PR #17. See docs/deam-similarity-benchmark.md,
> docs/fma-genre-benchmark-plan.md and the dated detailed handover.
> No user music rescans, subjective relabels, selected production metric,
> PR merge or main changes.
>
> **DEAM v5 END-TO-END PASS, 21 Oct 2026:** Official DEAM data
> successfully downloaded; **1,802** audio/annotation matches; **12**
> human-annotated DEAM songs analyzed with corrected Rust-v5,
> all seven similarity metrics compared, aggregate-only report uploaded.
> [Successful GitHub Action](https://github.com/chrober/bliss-mood-poc/actions/runs/39576010217),
> [report artifact](https://github.com/chrober/bliss-mood-poc/actions/runs/39576010217/artifacts/12333973414).
> Rust-v5 analyzer came from **separate pinned PR #17 source checkout**
> at 2c3d44401436b3b41b6e067199016a1ed2335fbf without
> merging/editing PR #17. Prior failures intentionally caught missing
> Cargo.lock (PR #16) and v4 preprocessing mismatches. See
> [DEAM benchmark document](deam-similarity-benchmark.md) for complete
> provisional VA correlations. Do **not** choose a metric from 12 songs,
> claim DEAM independent of MTG-Jamendo training, or treat Genre-vs.-VA
> as Genre validation. Next: larger controlled DEAM study, training
> overlap audit, then FMA Genre reference. No main merge.
>
> **CURRENT PRIORITY 21 OCT 2026 — automatic scientific DEAM benchmark, PR #16.**
> The user explicitly shifted away from further manual eight-pair listening
> studies. A reproducible DEAM Valence/Arousal benchmark now lives in
> [docs/deam-similarity-benchmark.md](deam-similarity-benchmark.md) with
> scripts/benchmark_deam.py, test_benchmark_deam.py and
> .github/workflows/deam-benchmark.yml. Synthetically tested on Linux/Windows
> in GitHub Actions. Official DEAM audio and annotations plus official models
> will be fetched only by the runner; only aggregate research results can be
> uploaded. First real workflow run failed because Cargo.lock is not yet
> committed and --locked prevented build; updated workflow removed --locked.
> Check DEAM GitHub Actions run 39575405139 (or latest) before claiming any
> end-to-end result. DEAM's CC BY-NC license, possible MTG-Jamendo train set
> overlaps and the status of Valence/Arousal **as a similarity proxy** must
> remain explicit. No metric winner, user-library scan, public music
> artifacts, mixing decision, main merge or PR #13/#17 changes.
>
> **Historical status (October 21, 2026): similarity evaluation on corrected Rust-v5, Draft PR #16.**
> The scanner/worker handover from October 19 is historical,
> not the current task list. Refer to the
> [local listening-review handover](similarity-listening-review-handover-2026-10-21.md).
> **The first eight human judgments were received and evaluated read-only.**
> Genre had 0 positive and 8 negative pairs, so ROC-AUC was undefined;
> Mood had 4 positives and 4 negatives, with cosine and centered cosine
> each yielding AUC 0.5625. Other methods ranged from 0.3125 to 0.5000.
> Historical fixed-cutoff Mood Top-K returned zero similarity
> for all four positive pilot pairs. No feature vectors were missing.
> These are uncertain, actively selected pilot ratings, **not independent
> evidence of a best metric**. Plan subsequent diagnostics and listening
> steps with the user; do not autonomously alter the queue,
> private data, or production code. Keep reviewed CSV, JSON,
> selection-audit, feature DB and audio local.
> PR #13 and PR #17 remain separate; `main` is unchanged.
> Any PowerShell commands must be complete `& { ... }` blocks.

> **21.10.2026 – Current executable next step:** PR #16 now includes
> a targeted read-only --pair-details-only option in
> scripts/evaluate_similarity.py. It supports semicolon CSVs and
> generates seven score values per head/per human-reviewed pair without
> random sampling, audio analysis, queue changes or changes to labels.
> The original first-eight CSV and saved JSON remain private and
> unchanged. Ask the user to run this option with the saved Rust-v5
> SQLite sidecar and return the new local pair-details report, verifying
> that its labeled AUCs match the existing saved report. The aggregate
> Mood cosine high-scoring negative is 0.9769996802 but its identity
> is not established without the per-pair values. All musical
> conclusions remain explicitly exploratory and uncertain.

> **Purpose:** Start a new development chat without losing the current project
> state. The detailed performance experiment, raw benchmark measurements,
> implementation details and open questions are in
> [adaptive-scan-performance-handover.md](adaptive-scan-performance-handover.md).
>
> **Source of truth:** Always re-check current GitHub `main` before making
> claims or changing code. This handover was prepared against
> `55b35dab1a873c3e61ecd639b7430caf0b09034c` (PR #5 merged), before the
> documentation-only handover PR. Do not assume that SHA is still the latest.

## Project and boundaries

Repository: [chrober/bliss-mood-poc](https://github.com/chrober/bliss-mood-poc).
Experimental Rust/ONNX offline audio analysis to complement Lyrion/Bliss,
**not** an instruction to change production mixers, plugins or Bliss Guidance
SPI. The generic CLI handles **three independent heads** sharing one
Discogs-EffNet embedding per song:

- `moodtheme` — 56-label MTG-Jamendo Mood/Theme (Sigmoid).
- `genre` — 87-label MTG-Jamendo Genre (Sigmoid).
- `voice` — Voice/Instrumental, 2 labels (Softmax). Not vocal-technique or
  percentage-of-vocal-time detection.

Original `bliss.db` and audio are read-only. Experimental results live in a
separate SQLite sidecar, schema v3, keyed by exact `TracksV2.File` identity.
Old Mood-only CLI and legacy rows remain untouched. Real-world prediction
quality is **not** production-validated; verified synthetic Essentia numerical
parity is not evidence of musical usefulness. See
[feature-provider-architecture.md](feature-provider-architecture.md) and
[offline-mood-database.md](offline-mood-database.md).

## What has shipped

1. Generic Mood + Genre + Voice analysis, shared encoder, model registry,
   per-head caching and validated numerical parity.
2. Incremental `scan-features` with bounded, parallel *songs*, independent
   per-worker ONNX Sessions and a single transaction-safe SQLite writer.
3. Corrected ONNX Runtime process-global Environment (earlier concurrent
   `ort::init().build()` attempts failed on Windows).
4. `--max-new N` means **at most N newly attempted tracks**, not N
   successes; `--max-errors N` aborts repeatedly failing scans.
5. `--workers auto` keeps Windows responsive (roughly 25% CPU headroom,
   cap eight), `--workers N` is explicit; for parallel use `--threads 1`.
6. [PR #5](https://github.com/chrober/bliss-mood-poc/pull/5), merged:
   opt-in `--adaptive-workers` with `--workers 6 --min-workers 4
   --max-workers 8`; per-song decode/preprocessing/inference/hash/load
   stage totals; OS CPU/RAM monitoring; logged worker adjustments.
   The fixed-worker interface remains available and unchanged.

Important source entry points:

- `src/features.rs`: `FeatureEngine`, `scan_parallel`,
  `save_completion`, `ScanSummary`, `ScanDiagnostics`.
- `src/parallel.rs`: `worker_count`, `AdaptiveWorkers::observe`.
- `src/resources.rs`: OS-level load sampling.
- `src/main.rs`: CLI flags and validation.
- `src/storage.rs`: read-only upstream Bliss access and SQLite sidecar.
- `model-registry.json` and
  `.github/workflows/voice-parity.yml`: model contract and integration tests.
- `README.md`: usage and caveats.

## Real test setup

User machine: Windows 11, HP Laptop 15-fc0xxx, AMD Ryzen 7 7730U,
8 physical cores / 16 logical CPUs, ~16 GB physical RAM; Wi-Fi 6 Realtek
RTL8852BE-VS at negotiated 600 Mbit/s. Music on NAS UNC share
`\\192.168.1.100\music`, local checkout
`D:\LMS\bliss-mood-poc`, 64,062 eligible Bliss tracks.

Deterministic local 100-song fixture:
`D:\LMS\bliss-mood-poc\benchmark-workers-20261019-060347\sample-100.db`
(seed 20261018). Benchmark sidecars:
`features-6.db`, `features-8.db`, `features-10.db`,
`features-12.db`; raw samples `resources-*.csv`, `summary.csv`
and `summary-with-6.csv`. Keep this suite for apples-to-apples work;
do **not** upload personal music or database to GitHub.

**Fixed-worker results over the same 100 tracks**:

| Workers | Wall time | Songs/min | System CPU avg | RAM max | Analyzer RAM max |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 6 | 80.48 s | 74.6 | 47.9% | 85.0% | 0.66 GB |
| 8 | 80.18 s | 74.8 | 63.5% | 89.5% | 1.17 GB |
| 10 | 82.29 s | 72.9 | 70.8% | 91.6% | 1.94 GB |
| 12 | 112.79 s | 53.2 | 83.2% | 97.5% | 3.21 GB |

All 300 model vectors per run were **byte-identical**. With six workers:
CPU max 87%, WLAN receive mean 24.05 MiB/s, max 39.08 MiB/s. Six fixed
workers are the measured efficiency baseline; eight have similar throughput
at much higher resource pressure.

**First adaptive run**, reported after PR #5 from a database within the
same benchmark directory:
`adaptive-20261019-080350.db`; 100/100 successful, zero failures,
**120.66 s (49.7 songs/min)**; workers initial/final/max **6/6/6**,
CPU avg 51.26%, peak RAM 86.33%, 38 OS-load samples, **no adjustments**.
Per-song *summed overlapping* durations: decoding 173.52 s, Mel/patches
100.82 s, ONNX 343.09 s, SHA-256 reread 66.54 s, session init 1.63 s,
sum of song durations 685.61 s. These are NOT sequential wall-clock or
exclusive CPU durations.

The adaptive controller's low-load rule is **CPU <=65% AND RAM <=79%
for 3 consecutive resource observations**. High-load rule is **CPU >=90%
OR RAM >=88% for 2 consecutive observations**. Changes are inhibited
until >=24 completed songs and at least 20 s since the last adjustment
(or creation). The observed near-86% RAM can sit in the deadband for the
entire run. Therefore **no worker change is not proof of a bug**. The
report shows only maximum RAM, not every sample: inspect actual timelines
and effective conditions before concluding why no adjustment occurred.
Whether the ~50% longer adaptive runtime is reproducible, and whether
the command truly used an identical track set/cache/priority, remain OPEN.

## Next work — priority order

1. **Investigate the adaptive performance regression** on exactly the
   existing `sample-100.db` and music source. Compare fixed six vs adaptive
   six under equivalent environment and process priority; alternate run
   order/repeat measurements, inspect NAS/OS caching, thermal/power throttling,
   and runtime phases. Do not conclude adaptive scheduling is at fault merely
   because of one timing difference.
2. **Make decisions explainable**: record per-resource sample time, CPU/RAM,
   consecutive low/high counters, cooldown, controller state, real in-flight
   count and why it held or changed. Check for starvation caused by samples
   only being taken when job results arrive.
3. **Evaluate safe policy options**, with tests: explicit pressure-only guard
   (reduce at high RAM/CPU), separate throughput-seeking tuning policy, or
   thresholds based on available memory + CPU/queue throughput rather than
   CPU/RAM fixed cutoffs alone. A correct policy may intentionally stay at six.
   Do not blindly force an adjustment.
4. **Measure NAS versus local SSD** on identical files with controlled
   cache state; distinguish SMB latency, network throughput and CPU
   preprocessing/inference. File hashing reads the source twice overall.
5. Regression CI: deterministic simulated resource timelines (high, low,
   deadband, missing samples, cooldown); verify real in-flight changes,
   maximum attempts, error stop and byte-identical feature vectors.
6. Only after evidence, optimize the controller and maybe expose explicit
   `--max-workers` defaults; keep fixed-worker behavior stable. Later:
   full-library progress/ETA and resumable/interruptible UX.

## Rules for the next chat

- Fetch fresh `main` SHA and review these docs + source **first**.
- Diagnose rather than assert adaptive is broken: 6/6/6 can be correct.
- Prefer a reproducible minimal PR; run Rust tests, Clippy, Windows x64,
  and required Essentia/model parity before merge.
- No production mixer/plugin changes. Keep `bliss.db`/music read-only;
  new SQLite benchmark DBs only; never commit music, model weights,
  local sidecar DBs or personal track lists.
- Always bound experiments: `--max-new`, `--max-errors`, timeouts;
  `--threads 1` when parallel. Retain `--workers N` and
  `--adaptive-workers` as optional.
- The user prefers actionable full PowerShell blocks (`& { ... }`) and
  measured evidence over speculative optimizations.


## Mandatory GitHub Actions / local testing workflow (2026-10-19)

**User preference and delivery contract for all future chats:**

1. **Never build Rust binaries on the user's Windows laptop.** Do not put
   `cargo build` or local Rust compilation in a PowerShell test script.
   Source code, unit tests, and release binaries are built and verified by
   GitHub Actions.
2. Make development changes on a feature branch and open a PR. PR events
   automatically trigger the existing **Windows x64 binary** workflow
   (workflow ID `387992797`) along with Rust checks and model parity checks.
   Do not assume that a documentation-only `main` commit also generated a
   Windows executable. Inspect the PR **head SHA** and matching Actions runs.
3. **Do not stop after reporting a queued/in-progress build.** Check the
   triggered Windows workflow to completion; verify that its conclusion is
   `success`, its head SHA matches the exact code under test, and that its
   non-expired artifact **`bliss-mood-windows-x64`** exists. Check all
   relevant Rust and model-parity workflows too. If any check fails, diagnose
   and fix first; never claim the binary is available prematurely.
4. Whenever the user is asked to run a local test, provide a **complete
   executable PowerShell script in `& { ... }` form**, containing the
   **literal, verified numeric Actions run ID** (not a placeholder, an
   automatically selected run, or instructions for the user to look it up).
   Embed the actual binary download, for example:
   `gh run download $runId --repo chrober/bliss-mood-poc --name bliss-mood-windows-x64 --dir $binDir`,
   followed by verification of `bliss-mood.exe`. Download to a run-ID-specific
   path such as `bin\windows-x64\$runId` and reuse only that matching binary.
   The script must check workflow head SHA/conclusion and fail safely if they
   do not match, use a fresh benchmark sidecar, and report useful diagnostics.
5. Preserve the user's existing setup: repo
   `D:\LMS\bliss-mood-poc`, source music `\\192.168.1.100\music`,
   stable 100-song sample
   `benchmark-workers-20261019-060347\sample-100.db`,
   `--models moodtheme,genre,voice --threads 1`. Audio files and original
   `bliss.db` are read-only. Do not commit personal media or benchmark DBs.
6. If testing code on a PR branch, don't require the user's local checkout
   to be on `main`; the binary must match the chosen PR SHA. Do not merge
   before CI and local validation where required.
7. Continue gathering evidence rather than changing worker behavior based
   solely on one timing result. Keep fixed worker modes and model-score
   identity intact.

**Previously verified example:** PR #7 Windows run `39236884182`,
artifact `bliss-mood-windows-x64`, head
`d34e2c4941d008caae089640dc4b75925da5c3e6`. PR #7 was squash-merged
into main as `8ee29972999caf1e543dbb7ce63d57868fdd16f2`.
Do **not** reuse that run ID for subsequently modified code.


## PR #10 pre-worker baseline measurement (2026-10-19)

**New benchmark requirement:** capture and report the system's RAM **and CPU
baseline before any scanner worker starts**, plus available physical RAM
and analyzer process Working Set and Private Bytes. For CPU, a single
instantaneous OS counter is meaningless: use a **one-second interval** before
workers are spawned, and expose the actual elapsed measurement window.
Do **not** feed this baseline into the adaptive worker controller or
normal runtime samples. On Linux and Windows this is measured at the start of
the parallel scan, after opening the input and sidecar DB and before
creating ONNX worker sessions. The one-second baseline measurement is
included in wall-clock scan elapsed time.

The JSON location is `diagnostics.baseline`:
`system_cpu_percent`, `cpu_measurement_seconds`,
`system_ram_percent`, `system_available_ram_mib`,
`process_working_set_mib`, `process_private_bytes_mib`.
These baseline values reflect **pre-worker** machine load, not a completely
idle Windows system before the application was launched. Compare changes
with runtime extrema; extrema can occur at different instants and do not
prove the analyzer was the cause of overall RAM pressure.

Use the mandatory PR-triggered GitHub Actions Windows artifact workflow
and exact-run PowerShell download rules documented above; never suggest
local cargo builds.


## Current product priority: Bliss + Mood/Genre Lyrion integration (2026-10-19)

**Read [lyrion-bliss-mood-genre-integration.md](lyrion-bliss-mood-genre-integration.md) before new product changes.** The immediate engineering task is F1: reliable exact `TracksV2.File` joining and read-only model-provenance-aware Mood/Genre SQLite retrieval for a bounded Bliss/Lyrion candidate set. The first strategy is **Bliss-first with optional Mood/Genre reranking in BlissMixerLab** through guidance SPI v2, with hard eligibility and original Bliss untouched, separate per-head influence, experimental preview opt-in and neutral fallback. Current provider host transmits candidate IDs/urlmd5, but exact file keys are not yet guaranteed; do not silently join by title/artist. Do not enable stored unvalidated model scores for production playlist generation by default.

The cross-platform worker and Raspberry Pi runtime/resource strategy is **deferred**, documented in [platform-resource-roadmap.md](platform-resource-roadmap.md). The user explicitly does not want tuning for one benchmark laptop; development focus now is meaningful playlist fusion, not scanner performance.

## Three-way mixing decision and local workfiles (2026-10-19)

The mixing architecture remains **undecided** between **Bliss-first**,
**Mood-/Genre-first**, and **Hybrid**. The first integration vertical slice
uses Bliss-first because the existing SPI v2 can already rerank a Bliss
candidate pool, **not** because Bliss-first has won a listening/coverage
comparison. All three must be compared on equivalent seeds, constraints,
coverage, transition quality, drift/diversity and Pi budgets before choosing.
See [lyrion-bliss-mood-genre-integration.md](lyrion-bliss-mood-genre-integration.md).

Root-level `benchmark-*/`, `bin/`, local `mood-full.json` and
`mood-quality-*.csv` are excluded by `.gitignore`; keep personal
music paths/analysis outputs out of commits. Do **not** ignore
`Cargo.lock`: this binary application's dependency lockfile should
be separately versioned once. Git status will continue showing it as
untracked until added/committed.


## Latest PR #16 experiment handover (supersedes earlier drafts)

### Embedding export and parity

The temporary Rust-v5 overlay uses
`--embedding-out` with the immutable
upstream Rust-v5 commit
`2c3d44401436b3b41b6e067199016a1ed2335fbf`.
Direct raw 1280D patch features are averaged
in f64, song-L2-normalized and emitted in
versioned separate JSON with audio/encoder
SHA, patch count, pooling and frontend
fingerprints. Classification data remain in
unchanged SQLite-v3 rows and **PR #17 is not
merged or edited**.

Independent synthetic raw-patch pooling,
1-vs-2 ONNX threads, off/on head and SQLite
equality were verified in
[run 39618323154](https://github.com/chrober/bliss-mood-poc/actions/runs/39618323154).
The maximum independent song-pooling difference
was ~1.0855e−8, with identical model head
outputs and SQLite rows. This is **ONNX-internal
synthetic parity**, not proof of broad
original Essentia C++ real-library parity.
The separate original C++/Rust-v5 parity
work remains governed by its own scope
and release checks.

### MTT concurrent worker smoke test correction

[Run 39621028716](https://github.com/chrober/bliss-mood-poc/actions/runs/39621028716)
failed because a test glob named
`process-worker-*.json` also captured
`process-worker-heads-N.json` classifier
reports, counting eight output files
instead of four actual embedding workers.
Exact basename/full-match discovery fixed
the test harness; both
[Linux and Windows CI 39622478825](https://github.com/chrober/bliss-mood-poc/actions/runs/39622478825)
passed. This was **not** a confirmed
ONNX inference numerical parity failure.

The successful complete MTT A/B, fixed
fusion and FMA A/B results are recorded
with exact cohorts and provenance in:

- [MTT 1280D-versus-heads results](similarity-audio-embedding-ab-results-2026-10-21.md)
- [Fixed rank fusion details](similarity-fixed-rank-fusion-research-2026-10-21.md)
- [FMA 80-song paired A/B](similarity-fma-embedding-ab-2026-10-21.md)
- [FMA curated cache](fma-selected-audio-cache-2026-10-21.md)
- [Cross-dataset evidence](similarity-cross-dataset-evidence-2026-10-21.md)
- [DEAM source blocker and experimental setup](deam-similarity-benchmark.md)
- [Local listening follow-up](similarity-local-library-retest-plan-2026-10-21.md)

### Historical first local listening pilot

The first eight locally rated pairs produced
**0 Genre positives / 8 negatives** and
**4 Mood positives / 4 negatives**.
ROC-AUC for Genre was undefined; Mood Cosine
and Centered Cosine each returned **0.5625**
with only 16 positive-negative comparisons.
The selected eight were metric-informed and
are not independent evidence for production.
Private CSV files were sometimes semicolon
separated; the paired evaluator supports
both and should preserve original labels.
See the
[listening-review handover](similarity-listening-review-handover-2026-10-21.md).

**No unapproved actions:** Do not overwrite
private feature databases, automatically
alter the Lyrion queue, move to production,
merge PRs or publish personal recording
identities. Version and model provenance
must be verified before any new comparison.
