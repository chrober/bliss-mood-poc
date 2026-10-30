# WP3-R7: post-R6 song-group bootstrap and neighbor retrieval (30 October 2026)

## Observed WP3-R6 outcome and scientific status

The operator ran the original Essentia C++ pipeline on all 240 NEW songs and provided a private aggregate (never commit): 240/240 complete Genre87, MoodTheme56, Voice2 and normalized pooled 1280D embeddings; source/model checks passed.

| R6 external teacher proxy | Real measured value |
| --- | ---: |
| Frozen MoodTheme Ridge MAE reduction vs old-100 training mean | 15.9474% |
| Frozen Genre PLS(2) MAE reduction vs old-100 training mean | 12.3069% |
| Raw Bliss23 vs Mood teacher distance Spearman | 0.387956 |
| MoodTheme Ridge student vs Mood teacher distance Spearman | 0.439035 |
| Raw Bliss23 vs Genre teacher distance Spearman | 0.430849 |
| MoodTheme Ridge student vs Genre teacher distance Spearman | 0.478136 |
| Unordered song pairs (NOT independent observations) | 28,680 |
| New song identity groups under R5 provenance | 240 |

New 240 are source-group-disjoint from the old 100 under recorded metadata. Original 25 group-holdout songs were reused in model development; no longer untouched. The R6 cohort was already observed when R7 was designed, so **R7 is post-hoc exploratory, NOT a second independent confirmation**. Neither experiment measures human musical similarity. Exact Essentia head numeric parity, complete upstream model pretraining non-overlap, and true audio/perceptual matching remain uncertified.

## R7 methods

The new Python evaluator (scripts/evaluate_wp3_r7_240.py) first re-executes the complete frozen R6 evaluation and requires all stored R6 aggregate keys and numerical outputs to reproduce. It rechecks the frozen 100-song development / 240-song source inputs, original manifest, model protocol, and private native DB/embedding provenance. Additionally it verifies *within the 240* that no credited artist (including collaborators), LMS album ID, or recording MBID is reused. A missing identity blocks evaluation. Source DBs are always read-only and no NEW teacher values are used for model fitting.

**Bootstrap:** 300 seeded, paired, song-group bootstrap replicates on the 240 distinct source-identity groups, not on 28,680 dependent pairs. Sampling songs with replacement implicitly weights the original pairs by their resampled multiplicity; self-comparisons of repeated draws of *the same original song* are removed. For each replicate recompute Spearman against the same teacher distances and the difference versus raw Bliss23. Report 95% percentile intervals as *exploratory descriptive uncertainty*, not adjusted p-values or confirmatory confidence. Fixed seed: 20261030.

Three paired deltas: frozen MoodTheme Ridge minus raw Bliss against Mood teacher; the same Ridge minus raw Bliss against Genre teacher; frozen old-100-fit Genre PLS(2) minus raw Bliss against Genre teacher.

**Teacher-neighbor Top-k retrieval:** Each song queries the other 239 songs. Rank by Euclidean or cosine dissimilarity, stable song-source order for ties; report mean per-query |candidate nearest k intersection teacher nearest k| / k, for k = 5, 10, 20. The teacher views are actual MoodTheme56 / Genre87 **Euclidean** distances. Query observations share the same catalog: no IID per-query confidence intervals. These scores indicate teacher-neighbor reconstruction, NOT human playlist quality.

Compare eight methods: raw Bliss23 Euclidean; old-train-standardized Bliss23 Euclidean; old-train-fit MoodTheme Ridge56 Euclidean; old-train-fit Genre PLS2 87D Euclidean; Genre87 cosine; MoodTheme56 cosine; old-training-mean-centered MoodTheme56 cosine; normalized pooled EffNet1280 cosine. All but the new Genre PLS *distance* view were already described in R6. All historical R6 distance correlations are checked numerically for consistency.

## Operator execution / privacy

The single Windows PowerShell 5.1/7 launcher (scripts/run_wp3_r7_240_windows.ps1) uses the exact previously verified private R6 directory, the existing 100-song research SQLite, Bliss database, R5 manifest, frozen protocol and existing Python 3.15 scientific venv. It never calls the scanner, ONNX, worker, SSH, LMS, player queue, or audio decoder. It creates an exclusive new ignored private benchmark-wp3-r7-posthoc-* output directory, leaving the prior R6 result and ALL sources untouched.

From Windows PowerShell, execute this complete block:

~~~powershell
& {
    $ErrorActionPreference = 'Stop'
    $Repo = 'D:\LMS\bliss-mood-poc'
    git -C $Repo switch feat/general-pairwise-similarity-research
    if ($LASTEXITCODE -ne 0) { throw 'Wrong research branch.' }
    git -C $Repo pull --ff-only origin feat/general-pairwise-similarity-research
    if ($LASTEXITCODE -ne 0) { throw 'Research-branch update failed.' }
    & (Join-Path $Repo 'scripts\run_wp3_r7_240_windows.ps1')
    if (-not $?) { throw 'R7 experiment failed.' }
}
~~~

Default input is the operator-confirmed R6 directory benchmark-wp3-r6-native240-f8c65ca449eb40e8ad6b5b3e817c18b2. An explicit -PlanDir can choose another existing verified R6 cohort; paths are never guessed. Private result: aggregate-wp3-r7-song-bootstrap-retrieval.json, in a fresh ignored directory. Only this anonymized aggregate and non-identifying console summary may be shared with the research chat. **Do not upload or commit any individual tracks, manifest, SQLites, embeddings, model weights, audio, logs, DLLs or private learned matrices.**

The dedicated GitHub Actions synthetic-only workflow (research-wp3-r7-synthetic.yml) checks Python 3.15 on Linux/Windows with pinned packages, historical R6 regression and synthetic R7 assertions, plus Windows PowerShell parser. CI does not access the actual private user dataset and is not a real R7 numerical result.

## Next scientific decision

Interpret bootstrap intervals and teacher-neighbor overlap as **exploratory quality proxies**. Keep WP1 General similarity external benchmark work and WP2 Personal preference metric with fallback/blending distinct from WP3 teacher distillation. No weights, production metric, personal learner or music similarity gain are selected here. Human-perceptual benefit needs an independent predeclared, task-appropriate quality study on a *new* cohort; do not represent the reused R6 sample as untouched. Leave PR #16, main, production Lyrion, and native worker policy unchanged.
