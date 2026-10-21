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

## 21 October 2026 — restart on numerically checked Rust v5 vectors (PR #17 NOT required)

The original Essentia C++ investigation established genuine numerical
parity for the **same 100 real MP3 tracks** using corrected Rust v5.
The saved *read-only* v5 sidecar is:

`D:\LMS\bliss-mood-poc\benchmark-rust-v5-workers4-20261020-191946\round-01-workers-04-rust.db`

The original C++/Rust parity gate passed **14,500 class scores**, zero
Mel-patch mismatches and worst score error 1.2695789337158203e-5
(unchanged 0.001 tolerance). A separate six-worker Rust-v5 run
was bitwise equal to the fixed-four v5 scores. These observations
validate numerical implementation on the tested tracks; they do **not**
validate musical meaning or turn raw sigmoid activations into
calibrated percentages. The previous v4 similarity-score behavior will
likely be similar but should not be assumed bit-identical without a
direct check.

**No Rust/Essentia C++ build, native DLL, model download, new music
scan or merge of PR #17 is needed to resume PR #16.** Python only
reads the existing schema-v3 SQLite feature sidecar. No `main`,
PR #13 or PR #17 changes belong to this similarity experiment.

### A small listening *pilot*, without pre-filling subjective labels

The new `scripts/propose_similarity_listening_pairs.py` makes this
step reproducible. It draws a **bounded set (24 by default)** from a
deterministically sampled matching Genre+Mood cohort. The candidate
pool is capped at 20,000 pairs, with 300 input tracks maximum.
Selection attempts to cover eight *sampling* strata: strong similarity
according to both heads; genre-high/mood-low; mood-high/genre-low;
both-low; Genre or Mood metric disagreement between cosine and
ranked Top-6 Jaccard; low absolute Mood activity; and random controls.
It rotates strata, limits overused tracks when possible and shuffles
pair order. These strata are **model-generated selection heuristics,
NOT correct human genre/mood labels**. Some may be absent in a given
cohort. They **cannot** be used as ground truth or as scientific
proof one metric ranks music better.

It outputs two files inside a **new ignored local benchmark directory**:

- `listening-pairs.csv` with exactly
  `left,right,genre_label,mood_label`; every label cell is **blank**
  until somebody actually hears the recordings. Song keys match
  `TracksV2.File` and CSV quoting preserves commas/Unicode.
- `selection-audit-private.json`: a private, separate document
  containing the models' numerical scores, sampling strata and
  candidate pool percentiles. **Do not inspect it until after
  listening** if you want to avoid knowing the tested methods' answers.

The reviewer is not blind to song filenames/artists (they are needed
to play the recordings), but is **blind to the metric scores and
sampling stratum** while listening. A genuinely double-blind listening
evaluation would require separate randomized audio playback and
artist-label masking, which this script does not provide.

**Ready-to-run Windows PowerShell:**

~~~powershell
& {
    $ErrorActionPreference = 'Stop'
    $repo = 'D:\LMS\bliss-mood-poc'
    $db = Join-Path $repo 'benchmark-rust-v5-workers4-20261020-191946\round-01-workers-04-rust.db'
    $output = Join-Path $repo (
        'benchmark-similarity-v5-pilot-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
    )

    Set-Location $repo
    git switch feat/similarity-metric-evaluation
    if ($LASTEXITCODE -ne 0) { throw 'Cannot switch to PR16 branch' }
    git pull --ff-only
    if ($LASTEXITCODE -ne 0) { throw 'Cannot update PR16' }

    python -m unittest discover -s tests -p 'test_evaluate_similarity.py'
    if ($LASTEXITCODE -ne 0) { throw 'Similarity evaluator tests failed' }
    python -m unittest discover -s tests -p 'test_propose_similarity_listening_pairs.py'
    if ($LASTEXITCODE -ne 0) { throw 'Pilot selector tests failed' }

    Write-Host "`n=== STRICT RUST V5 SIDE-CAR, NO AUDIO/ONNX ==="
    python scripts/propose_similarity_listening_pairs.py `
        --db $db --out-dir $output --require-v5 `
        --count 24 --limit 300 --pool-pairs 20000 --seed 20261021
    if ($LASTEXITCODE -ne 0) {
        throw 'Pilot selection failed. Verify original local v5 SQLite DB and model fingerprint'
    }

    python scripts/evaluate_similarity.py `
        --db $db --include-experimental --limit 300 `
        --pairs 3000 --seed 20261021 --examples 5 `
        > (Join-Path $output 'unlabeled-metric-diagnostics.json')
    if ($LASTEXITCODE -ne 0) { throw 'Unlabeled evaluation failed' }
    Write-Host "Private pilot directory: $output"
    Write-Host 'Fill only genuine independent listening verdicts; never auto-label.'
}
~~~

The pilot's `--require-v5` enforces the exact corrected Rust
preprocessing identity `experimental-essentia-audio-v5-f32-src-ratio-unvalidated`
for both heads, avoiding accidental reuse of old Rust-v4 or mismatched
C++ feature cohorts. This is a fingerprint check, **not an override
of the database's validation flag**; `--include-experimental` remains
required for these diagnostic-only vectors.

### What to judge, and what to do afterward

Do not assign labels because two filenames share a genre, album or
artist. Listen to the music. Grade `genre_label` as similarity of
musical style (0/1), and `mood_label` independently as felt mood and
energy (0/1). A blank cell is explicitly *not judged for that head*,
but the evaluator requires at least **one** of these two labels for
**every retained row**. Delete any pair you deliberately skip, or
judge at least one dimension.

Once you have listening judgments, run the existing evaluator with
`--labels $csv` and `--include-experimental`, retaining an
unchanged private copy of both the judged CSV and output JSON.
This reports per-head positive/negative distributions and tie-aware
ROC-AUC only for the actual supplied labels.

**Methodological limit:** The model and metric heuristics influenced
which pairs were selected. ROC-AUC on this *actively selected pilot*
is therefore **selection-biased**, even if humans supply independent
labels. Use the pilot to find failure modes and refine rating criteria,
**not to pick a universally winning metric**. For a final metric
choice, collect a new untouched held-out cohort with independently
randomized or explicitly stratified design and separate train/test
artist or seed groups; report both heads independently. Candidate
coverage and real playlist listening remain essential.

---

## Evaluate manually judged pairs

Create a CSV in the same ignored directory. Each row uses exact feature DB
track_file identities and a *listening judgment*, not automatically derived
same-artist, same-album, file naming, or Bliss neighbor labels:

```csv
left,right,genre_label,mood_label
Artist A/Album X/Song 1.flac,Artist B/Album Y/Song 2.flac,1,0
Artist A/Album X/Song 1.flac,Artist C/Album Z/Song 3.flac,0,1
```

**Genre and Mood require independent human labels.** A pair can share
its mood but not its genre, or its genre but not its mood. Here
`genre_label=1` means reasonably similar musical style, while
`mood_label=1` means similar felt mood/energy in the specific recording.
`0` means not similar in that dimension. An empty label cell indicates
**not judged for that dimension**; at least one of the two must be
judged for every pair. The old single `label` column is now rejected
because reusing one verdict for both heads would distort the experiment.

Include clear positives, clear negatives, difficult negatives
(e.g. similar style with different mood; different style with similar
mood), cross-artist positives, varied recordings and diverse musical
contexts. File names and metadata help find the audio, **not** assign
the labels automatically. For paths containing commas, quote the CSV
field or use PowerShell `Export-Csv` so they are escaped correctly.

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

This adds independent positive/negative distributions, per-head judged
pair counts, per-head missing-vector counts, and tie-aware **ROC-AUC**
separately for each metric and head. An empty dimension is ignored;
ROC-AUC requires both positive and negative judgments **for that head**. Higher raw score is not
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
