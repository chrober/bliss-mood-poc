# WP3-R6: complete original Essentia C++ analysis on frozen 240 NEW songs

> **ACTUAL REAL EXECUTION CONFIRMED — 30 OCT 2026:** The operator ran the entire R6 `-Stage All` successfully. Frozen source/model/native SHA gates and 240/240 Genre87/MoodTheme56/Voice2/1280D normalized embedding validation passed. The private, non-identifying R6 aggregate reports 240 NEW songs, old-100-fit MoodTheme Ridge MAE reduction **15.9474%** and Genre PLS2 **12.3069%**, raw Bliss vs Mood teacher Spearman **0.387956** / frozen Ridge **0.439035**, raw Bliss vs Genre teacher **0.430849** / Ridge **0.478136**. All 28,680 pairs are dependent, and this is **teacher proxy, not human similarity**. The real R6 plan is benchmark-wp3-r6-native240-f8c65ca449eb40e8ad6b5b3e817c18b2. This supersedes historical 'not yet scanned' statements below. [Post-R6 exploratory WP3-R7 study](wp3-r7-post-r6-robustness-and-retrieval-20261030.md) now reuses this exact native cohort **without rescanning audio**. Exact head parity and pretraining non-overlap remain unproven.


**Approved research direction, 30 October 2026.** This *supersedes* the former assumption in [the Bliss-only 24-pair blind pilot](wp3-blind-student-validation-pilot-20261030.md) that we should refrain from analyzing the 240 songs with Essentia. The blind pilot remains optional and is **postponed** until after the full-feature analysis and independently evaluated protocols are understood. It was not executed on real user data. The operator's instruction explicitly authorizes planning the 240-song original Essentia C++ analysis, not a production LMS/library scan.

## Confirmed baseline and external-cohort preparation

- First native Essentia research source cohort: 100 paired Bliss23 / Genre87 / MoodTheme56 songs, genuine Lyrion grouping, 88 connected artist+album+recording components; 75 train / 25 within-run grouped holdout. The older 25 had already been exposed during whole-cohort exploration; they are **not untouched confirmation**.
- Existing WP3 student candidate: **Bliss23 -> train-fitted StandardScaler -> Ridge(alpha 10) -> 56D MoodTheme pseudo-teacher -> Euclidean song distance**. On the old exploratory 25, MoodTheme distance-to-teacher Spearman improved 0.442049 to 0.540662; this is not independent human musical similarity.
- The R5 selection was actually executed locally (user's supplied terminal output, 30 October): 240 new valid Bliss23 songs selected, 15 each in 16 Tempo/centroid quartile cells; exact R5 source identities exclude previous 100 keys and known shared artists including collaborators, albums and recording MBIDs, and enforce no mutual overlap within new 240. Private R5 manifest: `benchmark-wp3-independent-cohort-586d7988747e4087b9cf1315492a34fc/private-independent-cohort.json`. The source-identity independence is conditional on recorded metadata; it does **not** rule out missing credits, erroneous MBIDs, teacher pretraining overlap or unchanged live LMS roots.
- **No Essentia ONNX/C++ outputs or human similarity judgments exist for the new 240 as of protocol creation.** Never claim a measurement before the operator runs the verified scanner.

## Freeze scientific comparisons BEFORE seeing any new teacher features

The machine-readable [frozen 240-song protocol](../research/wp3-r6-full-teacher-evaluation-v1.json) was committed before any new 240 Essentia analysis, alongside the earlier [MoodTheme student hypothesis](../research/wp3-moodtheme-student-candidate-v1.json).

1. **Old 100 for fitting only:** Use all the old 100 grouped development songs to fit StandardScaler + Ridge(alpha=10) for MoodTheme56, and separately a fixed StandardScaler + PLSRegression(n_components=2) for Genre87. Do not tune parameters on the 240.
2. **New 240 for out-of-cohort teacher-proxy evaluation only:** Native C++/ONNX must generate Genre87, MoodTheme56, and Voice2 (intermediate head) plus per-song normalized pooled 1280D embeddings. The new Genre/Mood targets are held out from fitting. Report MAE of frozen student/Genre PLS versus **old-100 training-mean** baselines.
3. **Same 240 across all representations:** On all 28,680 unordered pairs, compute Spearman agreement with each teacher head's Euclidean distances for original Bliss23 Euclidean, old-train-standardized Bliss23 Euclidean, frozen Bliss-only Ridge 56D Euclidean, Genre87 cosine dissimilarity, MoodTheme56 cosine and old-train-mean-centered cosine, and 1280D normalized EffNet cosine dissimilarity. All are **descriptive teacher-distance geometry**, not music quality.
4. **Scientific quality remains a separate next gate:** Teacher outputs are pseudo-labels. The pairwise 28,680 observations share the same 240 songs, are not independent and do not constitute a significance sample of 28,680. The source comparison is not human-rated music similarity or a production-metric victory. Independent human/external similarity evidence will be designed separately, with all metric choices locked before final judgments and group-aware uncertainty. If any results on the new 240 guide parameter tuning or subsequent model selection, the 240 cease being an untouched independent confirmatory quality set.
5. **WP1/WP2/WP3:** WP1 General Metric keeps independent Genre/Mood/1280D/Bliss/fusion baselines and fallback; WP2 Personal Metric Learning with optional 0–100% calibrated blend remains separate and works with no personal model; WP3 tests teacher-distilled Bliss. There is no automatic production promotion from either teacher reconstruction or a blinded diagnostic pair proposal.

## Implementation and source provenance

New scripts in isolated `feat/general-pairwise-similarity-research`:

- [Source-locked native scanner adapter](../scripts/wp3_r6_native_240.py): `prepare`, `guard`, `verify`.
- [Windows PowerShell 5.1/7 launcher](../scripts/run_wp3_r6_native_240_windows.ps1): `-Stage Prepare|Scan|Verify|All` (defaults to `Prepare` to prevent accidental audio inference).
- [Frozen 240 experimental evaluator](../scripts/evaluate_wp3_r6_240.py): Python 3.15 and existing private pinned research NumPy/scikit-learn environment; never writes source DBs or trained weights to Git.
- [Synthetic native output validation and source-drift tests](../tests/test_wp3_r6_native_240.py).

The concrete scanner interface comes from successfully integrated original C++ backend and static multi-worker manifest scanner [PR #20](https://github.com/chrober/bliss-mood-poc/pull/20), documented on the exact integration branch in `docs/multi-worker-song-analysis-final.md`. The workflow chooses **previously user-verified** local paths as defaults, not guessed or newly downloaded binaries: Windows scanner binary `D:\LMS\bliss-mood-private\verified-scanner-40758319812\bliss-mood.exe` and worker executable `D:\LMS\essentia-cli-test\essentia-worker\bliss-essentia-worker.exe`, with official model files under the existing repository `models` directory and audio under the verified Windows-accessible NAS root `\\192.168.1.100\music`. Required local paths and hashes are checked, and the worker dependency inventory is rehashed before analysis.

Scanner SHA256 is pinned as `00a41687fd79c53a536b6de6bf865647ef2d6f9ee453419cc69ca00911f5d82d`, build provenance `da8fecee23930c2e52abcb473a62b8178b2d5474` (exact already-known native 100-song verified scanner). The original 100-song native feature DB and model fingerprint/label ordering must match the official ONNX files; any drift rejects the experiment. The separately provisioned native worker with its DLL dependency manifest must already exist; none may be uploaded or distributed.

**Important licensing gate:** Original Essentia C++ native worker distribution and third-party models have unresolved AGPL/FFmpeg/model license-and-notice obligations; a successful local scientific analysis does **not** approve a publicly redistributable worker EXE/DLL package. Never silently download/redistribute licensed assets. No changes to `main`, PR #16, worker policy, original LMS, music or original Bliss/feature SQLites.

## Safe staged execution

Run the existing complete Windows PowerShell script from the research branch after pulling its latest commits:

`& .\scripts\run_wp3_r6_native_240_windows.ps1 -Stage Prepare`

This is **read-only with respect to all input databases and audio**: re-derives the exact R5 selection from 4 genuine sources, requires 240 unique tracks, SHA256-hashes all 240 source audio files, checks all official ONNX weights and class lists against the original 100-song teacher model, scans and fingerprints every native worker DLL/EXE, verifies scanner binary/build SHA and writes a private plan to a **new ignored UUID directory** `benchmark-wp3-r6-native240-*/`. Stage Prepare performs **NO inference**.

The scan stage requires the exact printed plan directory:

`& .\scripts\run_wp3_r6_native_240_windows.ps1 -Stage Scan -PlanDir 'D:\LMS\bliss-mood-poc\benchmark-wp3-r6-native240-...'`

It independently rehashes all source content **before** any inference. It then runs the verified source-pinned scanner with an explicit frozen manifest, `--audio-backend essentia --essentia-worker`, `--models moodtheme,genre,voice --embedding-dir` and `--workers auto --threads 1 --max-errors 3`. `auto` is one-time CPU-based static selection capped at 8, NOT dynamic worker tuning. Native outputs go exclusively into the new private folder's `native-features.sqlite` and `embeddings/`. Scanner stdout/stderr may contain private tracks and are redirected to private local logs; they must NEVER be sent publicly. An error leaves partial outputs intact for diagnosis and blocks blind restart/overwrite.

Once the native scanner succeeds, call:

`& .\scripts\run_wp3_r6_native_240_windows.ps1 -Stage Verify -PlanDir 'D:\LMS\bliss-mood-poc\benchmark-wp3-r6-native240-...'`

This refuses any incomplete, corrupted or foreign row/embedding, validates exactly 240/240 original native C++ 87D/56D/2D heads, correct audio SHA256+patches+native model fingerprints/labels and 240 normalized 1280D JSON, verifies current source hashes against the frozen plan, then runs the **predeclared** frozen old-train-only teacher-proxy evaluator. Anonymous numerical findings go to a **new, never overwritten** private `aggregate-wp3-r6-frozen-teacher-evaluation.json`, while source originals remain query-only.

An optional single explicit `-Stage All` creates a new plan, freezes files, executes real native C++ inference and runs verification/evaluation in one invocation. Never use `-Stage All` accidentally; **the default is Prepare**. If a required existing scanner/worker/model/audio path is missing, stop and investigate the actual user environment instead of substituting a Rust backend, unofficial model, guessed path or downloading a new kit.

Only send the **aggregate summary** or the non-identifying final evaluation JSON back to the research chat, NOT the 240-song manifest, local source logs, embeddings, any music/ratings, native EXE/DLL, model weights or private student parameter matrix.

## Completion/limitations

**Engineering status:** code and synthetic gates must pass GitHub Actions on Windows and Linux; those checks cannot reach the user's private NAS. **No real R6 audio scan, 240 Essentia result or new measured WP1/WP3 student outcome is established until the operator's local run completes**. Upon completion, separately document the actual exact real run, reproducibility fingerprints, coverage and teacher-proxy findings and keep both the source and scientific limitations.

**Next independent human validation:** only a separate consented, blinded listening/external metric protocol can determine whether any WP1 or WP3 representation improves song similarity. The earlier 24-pair diagnostic does **not** replace this evidence and is postponed while the comprehensive Essentia cohort is prepared.
