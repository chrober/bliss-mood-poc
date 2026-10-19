# Genre/Mood similarity metric comparison

**Research only. No selected production metric or calibrated similarity probability.**

The benchmark compares 87-dimensional Genre and 56-dimensional Mood/Theme
Sigmoid classification vectors independently. It never modifies BlissMixerLab
or music files, opens the existing schema-v3 SQLite database read-only,
and never runs ONNX, inference or audio decoding.

## What is compared?

| Metric | Range | What it measures |
|---|---|---|
| RMS transformed to 1-2×RMS | [-1,1] | Baseline vector distance; agreement on many low class values may inflate scores |
| Cosine | [0,1] for nonnegative inputs | Similar direction of class activation patterns |
| Centered cosine | [-1,1] | Class patterns after subtracting each track's mean activation |
| Weighted Jaccard | [0,1] | Sum of classwise minima / maxima; shared zeros add no similarity |
| Top-6 weighted Jaccard | [0,1] | Union of each song's strongest six classes, ignoring activations below 0.10 |

Top-K and 0.10 are **experimental parameters**, not validated defaults.
Scores on different scales or between Genre and Mood are not interchangeable.

The previous genre=0.8380 and mood=0.9067 for a 4 Non Blondes versus
Amorphis pair are not 83.8% and 90.67% musical similarity. RMS can yield
high scores for two unrelated songs sharing many inactive classes.
The prototype's confidence=1.0 reflects seed coverage, **not** certainty.

## Run against existing library

Only Python standard library is required; no Rust compiler.

```powershell
cd D:\LMS\bliss-mood-poc
git fetch origin
git switch feat/similarity-metric-evaluation
git pull --ff-only

$db = 'D:\LMS\bliss-mood-poc\benchmark-baseline-20261019-134244\adaptive.db'
$out = 'D:\LMS\bliss-mood-poc\benchmark-similarity-local'
New-Item -ItemType Directory -Force $out | Out-Null

python .\scripts\evaluate_similarity.py `
    --db $db --include-experimental `
    --limit 300 --pairs 3000 --seed 20261019 --examples 5 `
    > (Join-Path $out 'similarity-report.json')

if ($LASTEXITCODE -ne 0) { throw 'Similarity evaluation failed' }
```

Adjust the database path if your feature sidecar is elsewhere. The output
path is inside the repository's ignored benchmark-* tree, because report
JSON includes local music filenames; do not commit it.

The script selects the largest compatible model-fingerprint cohort for
each head, checks its labels/aggregation/dimensions and filters bad or
degenerate vectors. **No different model keys are mixed.** It reservoir
samples from all eligible library tracks (not alphabetically first artists)
and uses deterministic random song pairs. The unlabelled report gives
p05/median/p95 distributions and top-neighbor *listening prompts* per
head/metric. No quality claims are made from these numbers alone.

Experimental and unvalidated prediction vectors are **excluded by default**;
--include-experimental deliberately enables them for this offline analysis,
without changing their stored validation status.

## Evaluate manually judged pairs

Create a CSV in the same ignored directory. Each row uses exact feature DB
track_file identities and a *listening judgment*, not automatically derived
same-artist, same-album, file naming, or Bliss neighbor labels:

```csv
left,right,label
Artist A/Album X/Song 1.flac,Artist B/Album Y/Song 2.flac,1
Artist A/Album X/Song 1.flac,Artist C/Album Z/Song 3.flac,0
```

Here 1 means musically suitable for the intended playlist context;
0 means unsuitable. Include clearly similar songs, clearly dissimilar
songs, **hard negatives** (same production but different mood/genre),
cross-artist positives, and diverse styles. Do not infer a song's
compatibility only from file names or genre labels.

```powershell
python .\scripts\evaluate_similarity.py `
    --db $db --include-experimental `
    --limit 300 --pairs 3000 --seed 20261019 `
    --labels (Join-Path $out 'judged-pairs.csv') `
    > (Join-Path $out 'similarity-labeled.json')
```

This adds positive/negative distributions, missing-vector counts, and a
tie-aware **ROC-AUC** separately for each metric and each head. AUC
requires positive and negative examples. Higher raw score is not
necessarily better; a useful metric ranks *actually similar* pairs above
dissimilar ones, consistently across genres and seeds.

## Calibration and selection gates

1. Check model predictions against real-song references. Passing synthetic
   numeric parity does **not** establish real-world semantic quality.
2. Collect sufficient human listening judgments including negative and
   difficult counterexamples. Avoid using artist/album identity as truth.
3. Divide labeled examples into development and held-out evaluation groups
   by seed or recording/artist, to reduce data leakage. Select top-K,
   threshold, metric and preprocessing on development data only.
4. Measure ROC-AUC, ranking precision and variance on the held-out group,
   separately for Genre and Mood. Only then consider head-specific
   normalization or score-to-probability calibration with held-out
   verification.
5. Compare Bliss-only, Bliss-first, Mood-first and Hybrid playlists
   with identical eligibility constraints and blind listening. Measure
   transition coherence, diversity, drift and Pi latency. Do **not**
   choose a mixing strategy based on score distributions.
6. Until this evidence exists, keep provider influence neutral by default.

The evaluator does **not** change the native guidance scorer, mixer
weighting, plugin defaults, or original music library.
