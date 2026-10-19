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
| Top-6 weighted Jaccard (cutoff 0.10) | [0,1] | Old sparse baseline; can reject *every* class for a quiet Mood vector |
| Top-6 ranked Jaccard (no cutoff) | [0,1] | Compare each song's six strongest activations, regardless of absolute magnitude |
| Top-12 ranked Jaccard (no cutoff) | [0,1] | Sensitivity check: whether widening active ranks stabilizes similarity |

The old cutoff-based Top-K is retained strictly for before/after research,
not recommended for production. The real 100-track sample had an Aretha
Franklin Mood vector with maximum class activation 0.0815, so the old
threshold removed **all 56 features** and produced zero overlap for
92 of 99 other tracks, with seven comparisons undefined. This is
a parameter artifact, not evidence that these songs share no mood.
Rank-only Top-K removes the arbitrary 0.10 eligibility threshold
while keeping a fixed number of compared classes. No absolute output
should be read as a calibrated probability; K=6 or 12 is not yet
validated.
Scores on different scales or between Genre and Mood are not interchangeable.

The previous genre=0.8380 and mood=0.9067 for a 4 Non Blondes versus
Amorphis pair are not 83.8% and 90.67% musical similarity. RMS can yield
high scores for two unrelated songs sharing many inactive classes.
The prototype's confidence=1.0 reflects seed coverage, **not** certainty.

## Run against existing library

Only Python standard library is required; no Rust compiler.

```powershell
& {
    Set-Location 'D:\LMS\bliss-mood-poc'
    git fetch origin
    if ($LASTEXITCODE -ne 0) { throw 'Git fetch failed' }
    git switch feat/similarity-metric-evaluation
    if ($LASTEXITCODE -ne 0) { throw 'Git switch failed' }
    git pull --ff-only
    if ($LASTEXITCODE -ne 0) { throw 'Git pull failed' }

    $db = 'D:\LMS\bliss-mood-poc\benchmark-baseline-20261019-134244\adaptive.db'
    $out = 'D:\LMS\bliss-mood-poc\benchmark-similarity-local'
    New-Item -ItemType Directory -Force $out | Out-Null

    python .\scripts\evaluate_similarity.py `
        --db $db --include-experimental `
        --limit 300 --pairs 3000 --seed 20261019 --examples 5 `
        > (Join-Path $out 'similarity-report.json')
    if ($LASTEXITCODE -ne 0) { throw 'Similarity evaluation failed' }
}
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

## Low output amplitudes and label interpretation

The model heads are MTG-Jamendo **multilabel Sigmoid classifiers**,
not mutually exclusive genre proportions. Official Essentia model
documentation lists the 87 genre and 56 mood/theme labels. The models
were trained on community-tagged music, so they can produce several
low activations even for music with a recognizable style. For Aretha,
the strongest genre labels are pop (0.309), jazz (0.129), rock (0.115)
and soul only 0.052. This is a plausible indication of
**imperfect genre discrimination**, but these raw outputs alone do not
establish bad preprocessing or an incorrect Similarity metric. In the
Mood head, `christmas=0.074` should *not* be interpreted as a positive
Christmas prediction; it is simply one low relative rank.

The read-only report now includes `activation_distribution` for
every sampled track per head: maximum activation, number of classes
above 0.05 and 0.10, and how often the old 0.10 cutoff removes all
classes. Compare `topk6_ranked_jaccard`,
`topk12_ranked_jaccard`, and the original
`topk_weighted_jaccard` on **the same frozen sample and seed pairs**.
A better-looking distribution is not enough: listen to pair examples,
then judge held-out positive and hard-negative song pairs separately
for Genre and Mood.

## Diagnosing the surprising neighbors

The first real-library report (100 valid tracks) exposed a real limitation:
**Top-K Jaccard can have zero common active classes for a seed against every
candidate**. A zero-score tie is *not* a nearest neighbor; formerly the
script printed alphabetically first tracks as its "top matches". It now
omits those zero-overlap neighbors, sets `no_positive_overlap=true`, and
reports `zero_score_candidates`, `positive_overlap_candidates`,
`undefined_score_candidates`, and `zero_fraction` for the relevant
distribution.

A second possibility is that the 56D/87D experimental model predictions
themselves lack useful semantics for the music in this library. Accordingly
the report now includes `unlabeled.{genre,moodtheme}.track_profiles` for
the sampled seeds and returned neighbors. Each profile lists the **six
highest-scoring class labels in exact model order**, their activations,
total number of classes at least 0.10, and the mean/max activity. This is
a way to audit **what the model actually believes a track contains**,
without using names or albums as ground truth.

For the next round, first inspect the strongest labels of known tracks
such as an Aretha Franklin soul recording and a Balkan folk recording.
If the class profiles are implausible, changing the distance metric may
only disguise a classifier or preprocessing problem. Compare Genre and
Mood independently; even when a pair shares one strong class, Top-K
overlap is not proof of similar overall music.

Read the extended report after repeating the documented evaluation command:

```powershell
& {
    $report = 'D:\LMS\bliss-mood-poc\benchmark-similarity-local\similarity-report.json'
    $r = Get-Content -LiteralPath $report -Raw | ConvertFrom-Json

    foreach ($head in 'genre', 'moodtheme') {
        Write-Host "`n=== $head ==="
        $examples = @($r.unlabeled.$head.nearest_neighbor_examples)
        $seeds = @($examples | Select-Object -ExpandProperty seed -Unique)
        foreach ($seed in $seeds) {
            $profile = @($r.unlabeled.$head.track_profiles) |
                Where-Object { $_.file -eq $seed } |
                Select-Object -First 1
            Write-Host "`nSEED: $seed"
            Write-Host "Active classes >= 0.10: $($profile.active_ge_0_10)"
            $profile.top_classes |
                ForEach-Object { "{0:N3} {1}" -f $_.activation, $_.label }
            $topk = $examples |
                Where-Object { $_.seed -eq $seed -and
                    $_.metric -eq 'topk_weighted_jaccard' } |
                Select-Object -First 1
            Write-Host "Top-K positive candidates: $($topk.positive_overlap_candidates)"
            Write-Host "Top-K zero-score candidates: $($topk.zero_score_candidates)"
        }
    }
}
```

This is **diagnostic evidence only**. No model-head class output, score
percentile, or filename association by itself establishes playlist quality.

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
& {
    $db = 'D:\LMS\bliss-mood-poc\benchmark-baseline-20261019-134244\adaptive.db'
    $out = 'D:\LMS\bliss-mood-poc\benchmark-similarity-local'
    Set-Location 'D:\LMS\bliss-mood-poc'
    python .\scripts\evaluate_similarity.py `
        --db $db --include-experimental `
        --limit 300 --pairs 3000 --seed 20261019 `
        --labels (Join-Path $out 'judged-pairs.csv') `
        > (Join-Path $out 'similarity-labeled.json')
    if ($LASTEXITCODE -ne 0) { throw 'Similarity evaluation failed' }
}
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
