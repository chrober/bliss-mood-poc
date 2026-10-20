# Gate: Windows original Essentia C++ versus Rust on real music

**Scope:** PR #17, branch `feat/essentia-cpp-worker-backend`. Goal: demonstrate
numerical and persistence compatibility on an identical **real** selection
of music files, then merge #17 to main **only after** a green review of the
results. Further *similarity metric* research continues separately in draft
PR #16 after its branch is updated to include the merged backend.

## Proven in CI — not the same as this gate

On 2026-10-20, the genuine Windows-x64 CLI development bundle passed original
Essentia build/linkage, isolated DLL closure/startup, synthetic WAV/FLAC/MP3
Mel parity, EffNet 1280D and 87/56/2 heads, two-worker four-file sidecar
scan, repeat-scan cache reuse and a read-only invocation of the **unchanged**
PR #16 similarity evaluator.

- [Successful run #39421541546](https://github.com/chrober/bliss-mood-poc/actions/runs/39421541546)
  at **`bdb281d3a952775d62f4b29786e687a05471f9b1`**.
- Artifact **`bliss-mood-essentia-windows-x64-dev`**, expires
  2026-11-03; read `README.md` and `BUILD-PROVENANCE.txt`.
- Synthetic parity does **not** establish 100-track real-library parity,
  performance or production redistribution clearance.
- The test kit from that run is still valid for the real-audio test.
  The benchmark Python script belongs to the **new PR #17 checkout**,
  which fixes relative `TracksV2.File` source-root handling and
  verifies backend fingerprint separation. No new native binary is
  required for these Python-only fixes.

## Real-music acceptance criteria

1. Select one existing **bounded 2–500-song** `TracksV2` cohort with
   original exact file keys and accessible music; prefer a representative
   existing `sample-100.db` subset with WAV, FLAC, MP3 and diverse styles.
   **Do not pass the full Bliss database** or a feature sidecar as a cohort.
2. Run Rust and original C++ backends on **exactly the same** audio files,
   executable, model weights, worker count and inference settings.
   Write every run to separate, newly created schema-v3 feature sidecars.
   Keep `bliss.db`, NAS audio, prior 100-track feature DB and all models read-only.
3. No missing/errors; the **exact cohort keys**, requested model-head
   coverage (87D Genre, 56D Mood, 2D Voice), and analyzed Mel patch
   counts must match. **Max absolute per-class score drift <= 1e-3**
   across all pairs. Report per-head mean/max differences and worst
   class/track, not just PASS.
4. Both sides must have **different model fingerprint keys** per head
   (different audio frontends); no single sidecar may mix fingerprints.
   Check that underlying ONNX file hashes, exact class-label order and
   aggregation metadata match **despite** the distinct frontend keys.
   The benchmark asserts all these conditions.
5. Run at 1 and 2 workers first (single and persistent multiworker),
   then extend to 1/2/4/6 and two balanced AB/BA repeats only after
   the numerical gate is green and resource use is acceptable.
6. Preserve both data families under separately named paths, and compare
   per-head similarity distribution, nearest-neighbor ranking overlap and
   zero-score rate **on identical song keys**. Earlier Rust-based Mood/Genre
   findings remain hypotheses, not proof of new C++ model behavior.
7. Merge #17 only after the real-cohort numerical gate, CI, review and
   sidecar isolation pass. The license audit remains a separate
   release/distribution gate; merging experimental code is **not**
   production redistribution approval.

## Recovery: inspect existing completed 100-song pair WITHOUT rescan

**2026-10-20 real-library result:** the first single-worker Rust and C++
100-song analyses both completed (567.78s Rust, 508.19s C++); the harness
then stopped before comparing numeric scores because a newly introduced
metadata check mistakenly compared the *entire*
`feature_models.models_sha256_json` dictionaries. C++ intentionally adds
`essentia_cpp_worker_binary_sha256` and, on Windows, the deployment manifest
SHA to that JSON. These extra keys must remain validated for cache identity,
but must not be mistaken for differences in the **shared ONNX encoder/head**.

**Fix in PR #17:** parse the hashes, require equal exact encoder/head ONNX
SHA256 digests, same ordered class labels and aggregation across backends,
validate only the documented extra C++ worker/deployment SHA keys and reject
unknown fields. This remains strict; there is **no tolerance relaxation**.

For the **already completed first two sidecars** in
`benchmark-essentia-real-20261020-160351`, run the following from the
up-to-date PR #17 checkout. This utility reads the v3 SQLite files in
read-only mode and does not invoke any scanner, C++ worker, ONNX or NAS
audio. It checks exact cohort keys, 87/56/2 vector dimensions, patch
counts, separate fingerprints, identical real ONNX SHA256/class
definitions and absolute score drift <= 1e-3.

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $repo = 'D:\LMS\bliss-mood-poc'
    $cohort = Join-Path $repo 'benchmark-workers-20261019-060347\sample-100.db'
    $base = Join-Path $repo 'benchmark-essentia-real-20261020-160351'
    Set-Location $repo
    git switch feat/essentia-cpp-worker-backend
    if ($LASTEXITCODE -ne 0) { throw 'Failed to switch to PR17 branch' }
    git pull --ff-only
    if ($LASTEXITCODE -ne 0) { throw 'Failed to update PR17 code' }

    python -m unittest discover -s tests -p 'test_verify_existing_backend_sidecars.py'
    if ($LASTEXITCODE -ne 0) { throw 'No-rescan audit regression failed' }

    $checkArgs = @(
        'scripts/verify_existing_backend_sidecars.py',
        '--cohort-db', $cohort,
        '--rust-db', (Join-Path $base 'round-01-workers-01-rust.db'),
        '--essentia-db', (Join-Path $base 'round-01-workers-01-essentia.db'),
        '--models', 'genre,moodtheme,voice',
        '--score-max-tolerance', '0.001'
    )
    $raw = & python @checkArgs
    if ($LASTEXITCODE -ne 0) { throw 'Existing v3 sidecar parity failed' }
    $r = ($raw -join "`n") | ConvertFrom-Json
    Write-Host "RESULT: $($r.status) - $($r.song_count) songs"
    foreach ($head in @('genre', 'moodtheme', 'voice')) {
        $d = $r.numerical_parity.per_head.$head
        [pscustomobject]@{
            Head = $head
            Songs = $d.tracks
            MaxAbsError = $d.maximum_absolute_score_difference
            MeanAbsError = $d.mean_absolute_score_difference
            PatchMismatches = $r.numerical_parity.patch_count_mismatches
        }
    }
}
```

On any failure, stop and inspect the exact error. Do **not** rerun all
100 songs just because a metadata assertion failed; all completed sidecar
data remains available. If parity is successful, validate the **two-worker
scenario** with an entirely fresh output directory using the main
benchmark's `--workers 2 --repeats 1` and the verified dev-kit binaries.
Avoid repeating the already-completed one-worker scans.

## Numerischer Drift auf echten Songs — Befund 20.10.2026

Der korrigierte strenge Read-only-Vergleich der beiden vorhandenen
100-Song-Sidecars ist **fehlgeschlagen**: größte bisher gemeldete Abweichung
in `voice`, Klasse 0, bei
`Electric Yawn/2021 - Spice Must Flow/07 Tree Of A Thousand Eyes - Part 2.mp3`:
Rust `0.4835579991340637` gegen original Essentia C++ `0.47973379492759705`;
absolute Differenz `0.003824204206466675`, größer als das vereinbarte
Maximum `0.001`. Dieses Ergebnis blockiert den Merge von PR #17,
bis wir Ursache und akzeptables Paritätskriterium nachvollziehbar bestimmen.
Nicht die Toleranz erhöhen, um den Test grün zu machen.

**Read-only Diagnose aller 100 Songs:** der neue
`scripts/diagnose_backend_drift.py` verarbeitet ausschließlich die
vorhandenen beiden Sidecars, validiert Kohortenschlüssel, Modellidentität,
Fingerprints und Vektordimensionen und wertet pro Genre/Mood/Voice und
Dateiendung `.mp3`/`.flac`/`.wav` die mittleren/maximalen sowie
p50/p90/p95/p99 absoluten Abweichungen aus. Es zählt sowohl betroffene
Songs als auch Score-Komponenten oberhalb `0.001`. Der komplette
lokale JSON-Bericht enthält die 25 auffälligsten Track/Head-Paare.
**`numeric_parity_status: FAIL` bleibt FAIL**, auch wenn das
Diagnoseprogramm technisch erfolgreich durchgelaufen ist.

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $repo = 'D:\LMS\bliss-mood-poc'
    $base = Join-Path $repo 'benchmark-essentia-real-20261020-160351'
    $report = Join-Path $base 'real-audio-drift-diagnostics.json'
    Set-Location $repo

    git switch feat/essentia-cpp-worker-backend
    if ($LASTEXITCODE -ne 0) { throw 'Git branch switch failed' }
    git pull --ff-only
    if ($LASTEXITCODE -ne 0) { throw 'Git pull failed' }

    python -m unittest discover -s tests -p 'test_diagnose_backend_drift.py'
    if ($LASTEXITCODE -ne 0) { throw 'Diagnostic regression tests failed' }
    if (Test-Path -LiteralPath $report) {
        throw "Never overwrite previous diagnostic report: $report"
    }

    $args = @(
        'scripts/diagnose_backend_drift.py',
        '--cohort-db', (Join-Path $repo 'benchmark-workers-20261019-060347\sample-100.db'),
        '--rust-db', (Join-Path $base 'round-01-workers-01-rust.db'),
        '--essentia-db', (Join-Path $base 'round-01-workers-01-essentia.db'),
        '--models', 'genre,moodtheme,voice',
        '--score-max-tolerance', '0.001',
        '--output', $report
    )
    python @args
    if ($LASTEXITCODE -ne 0) { throw 'Read-only diagnostic failed' }

    $r = Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
    Write-Host "`nNumerical parity: $($r.numeric_parity_status)"
    Write-Host "Songs exceeding threshold: $($r.tracks_exceeding_tolerance_any_head)"
    Write-Host "Patch mismatches: $($r.patch_mismatch_count)"

    $heads = foreach ($name in @('genre', 'moodtheme', 'voice')) {
        $x = $r.per_head.$name
        [pscustomobject]@{
            Model = $name
            SongsAffected = $x.tracks_exceeding_tolerance
            ScoresAffected = $x.scores_exceeding_tolerance
            MaxAbsError = $x.maximum_absolute_error
            P95AbsError = $x.p95_absolute_error
            MeanAbsError = $x.mean_absolute_error
        }
    }
    $heads | Format-Table -AutoSize

    $codecs = foreach ($p in $r.per_extension.PSObject.Properties) {
        $x = $p.Value
        [pscustomobject]@{
            Format = $p.Name
            Tracks = $x.tracks
            SongsAffected = $x.tracks_exceeding_tolerance
            MaxAbsError = $x.maximum_absolute_error
            P95AbsError = $x.p95_absolute_error
        }
    }
    $codecs | Format-Table -AutoSize
    Write-Host "Detailed PRIVATE local JSON: $report"
}
```

**Keine neue Audioanalyse notwendig**. Die Quell-DBs und die Musik werden
nur gelesen. Bitte nur die *beiden aggregierten Tabellen* teilen;
die vollständige JSON-Datei enthält private Pfade und bleibt lokal.

**Interpretationsgrenze:** Die Dateiendung allein beweist keine
Codec-Ursache. Falls das Sample ausschließlich MP3 enthält, benötigen
wir für WAV/FLAC-Vergleiche anschließend eine neue sehr kleine, gezielte
Paritätsstichprobe. Weitere gezielte Ursachenanalyse: native Decoder-Ausgabe
gegen Rust-FFmpeg, Mel/Patch-Vergleich pro betroffenem Song, anschließend
Embeddings und Modell-Outputs. Erst nach Erklärung der Differenzen
entscheiden wir über den PR-17-Merge. Kein automatisch hoher Toleranzwert.

## Next controlled root-cause experiment: real MP3 vs shared PCM WAV

**100 real songs (all MP3), strict paired scan, 1 worker:** 23/100 tracks
exceeded absolute class-score difference 0.001, while all patch counts and
actual ONNX weights/class definitions agreed. Results were:

| Head | Affected songs | Components over 0.001 | MAE | Maximum |
| --- | ---: | ---: | ---: | ---: |
| genre (87) | 13 | 31/8700 | 0.0000390 | 0.0034552 |
| moodtheme (56) | 3 | 6/5600 | 0.0000354 | 0.0030841 |
| voice (2) | 11 | 22/200 | 0.0005335 | 0.0038242 |

Across all heads 59/14,500 class scores exceeded 0.001 (0.407%). Voice's
two output classes are a Softmax and can both shift for a single song;
22 above-threshold scores thus represent 11 distinct tracks, not 22.
**This is a FAILED strict parity gate**, not a reason to silently
enlarge the allowed difference.

These 100 real files do not test non-MP3 behavior. The Windows C++ build's
FFmpeg components and the Rust CLI's separately invoked user-PATH FFmpeg
can differ in decoder implementation, build version, gapless handling,
resampling, downmix or DSP arithmetic. **Do not claim the cause is MP3
decoding before isolating it.**

The next inexpensive, targeted test should use the **worst real MP3** from
the *local* numeric drift report. Without rescanning the 100 songs:

1. Decode its complete first audio stream to **one common lossless 32-bit
   float PCM WAV**, preserving its native sample rate and channel count.
2. Run the same Windows \`bliss-mood.exe\` twice on this **same WAV**, once
   Rust and once C++ (identical ONNX weights, one thread, no SQLite output).
3. Compare Genre, Mood and Voice class scores and full-song patch counts.
   The tool also prints the **already recorded** full-song MP3 sidecar
   differences for this same song; no MP3 rescan is necessary.

- If C++/Rust scores match on the shared WAV but differed on the original
  MP3, investigate MP3 decoder version, gapless trimming and PCM conversion.
- If they differ on the shared WAV too, investigate PCM downmix, the
  \`SRC_LINEAR\` resampler, frame layout, Mel coefficients and numerical
  DSP. A WAV mismatch does *not* mean that the MP3 discrepancy necessarily
  has the same cause.
- The test also reports if the WAV patch count differs from the original
  MP3 sidecars (e.g. trimming/encoder delay). **Do not force equivalence
  between different length/trim variants** or raise the original 0.001
  tolerance.

Run on user's machine (requires existing kit, ONNX models and FFmpeg on PATH).
Original audio and existing SQLite are opened read-only. The single
generated WAV and CLI JSON artifacts remain in a new private directory
and may be large. No music/audio or JSON is committed to Git.

~~~powershell
& {
    $ErrorActionPreference = 'Stop'
    $repo = 'D:\LMS\bliss-mood-poc'
    $base = Join-Path $repo 'benchmark-essentia-real-20261020-160351'
    $kit = 'D:\LMS\essentia-cli-test'
    $out = Join-Path $base 'mp3-wav-control-rank1'
    Set-Location $repo
    git switch feat/essentia-cpp-worker-backend
    if ($LASTEXITCODE -ne 0) { throw 'Branch switch failed' }
    git pull --ff-only
    if ($LASTEXITCODE -ne 0) { throw 'Git pull failed' }

    python -m unittest discover -s tests -p 'test_diagnose_mp3_wav_control.py'
    if ($LASTEXITCODE -ne 0) { throw 'Control helper regression tests failed' }
    if (Test-Path -LiteralPath $out) {
        throw "Never overwrite previous control data: $out"
    }
    $args = @(
        'scripts/diagnose_mp3_wav_control.py',
        '--drift-report', (Join-Path $base 'real-audio-drift-diagnostics.json'),
        '--rust-db', (Join-Path $base 'round-01-workers-01-rust.db'),
        '--essentia-db', (Join-Path $base 'round-01-workers-01-essentia.db'),
        '--source-root', '\\192.168.1.100\music',
        '--analyzer', (Join-Path $kit 'bliss-mood.exe'),
        '--essentia-worker',
          (Join-Path $kit 'essentia-worker\bliss-essentia-worker.exe'),
        '--models-dir', (Join-Path $repo 'models'),
        '--output-dir', $out,
        '--rank', '1',
        '--score-max-tolerance', '0.001'
    )
    python @args
    if ($LASTEXITCODE -ne 0) {
        throw "Controlled decoded-WAV test failed. See local logs: $out"
    }
}
~~~

The printed \`original_mp3_by_head\` numbers reflect the preserved 100-song
benchmark; \`wav_control_by_head\` numbers are the two new analyses on shared
PCM. The complete local report contains the private track key and is not to
be uploaded. The tool returns successfully for **diagnostic completeness**;
the boolean \`wav_control_within_tolerance\` is the actual WAV-numerical gate.
Neither value alone certifies full-library or cross-codec parity.

## Real MP3 shared-WAV result and targeted short PCM frontend comparison

On **2026-10-20**, the *worst* of the 100 real MP3 tracks was decoded
once to lossless PCM float32 WAV, then analyzed by both backends using
the same ONNX weights. The absolute maximum score deviations remained
essentially **identical** to the original MP3 scan:

| Model | Real MP3 | Shared decoded WAV |
| --- | ---: | ---: |
| Genre | 0.00345522165 | 0.00345524000 |
| Mood/Theme | 0.00308407843 | 0.00308408000 |
| Voice | 0.00382420421 | 0.00382420000 |

Both backends reported **837 patches**. This makes differences in MP3
decoding alone unlikely to be the primary cause. It does NOT yet
separate downmix, resampling and actual Mel/FFT calculations.

The next bounded test uses the **already existing** decoded shared PCM WAV
at:

    D:\LMS\bliss-mood-poc\benchmark-essentia-real-20261020-160351\mp3-wav-control-20261020-164836\control-from-mp3-decoded-float32.wav

For two 12-second excerpts at offsets **0** and **120 seconds**, create
one WAV preserving the original sample rate/channels, and one FFmpeg-
normalized **16kHz mono float32 WAV**. Analyze each of those 4 short WAVs
with the **original Windows dev kit**, using BOTH Rust/C++ production
backends and all three ONNX heads (no rebuild, no original DB changes).
Also compare the first four [128,96] Mel patches directly using the
production Rust CLI mel-dump and original native Essentia C++ worker's
bounded patch protocol. Report mean/max Mel error, worst frame/band, and
Genre/Mood/Voice score drift.

If the normalized 16k mono WAV agrees but original-rate does not, look
for differences in Rust's linear resampler/downmix approximation. If both
fail, the Mel/FFT processing should be examined against the native
reference. These are diagnostic outcomes, not automatic merge approval.

Run this single **Windows PowerShell** block:

~~~powershell
& {
    $ErrorActionPreference = 'Stop'
    $repo = 'D:\LMS\bliss-mood-poc'
    $base = Join-Path $repo 'benchmark-essentia-real-20261020-160351'
    $kit = 'D:\LMS\essentia-cli-test'
    $inputWav = Join-Path $base 'mp3-wav-control-20261020-164836\control-from-mp3-decoded-float32.wav'
    $output = Join-Path $base ('pcm-frontend-control-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
    Set-Location $repo
    git switch feat/essentia-cpp-worker-backend
    if ($LASTEXITCODE -ne 0) { throw 'Cannot switch to PR17 branch' }
    git pull --ff-only
    if ($LASTEXITCODE -ne 0) { throw 'Cannot update PR17 branch' }
    python -m unittest discover -s tests -p 'test_diagnose_pcm_frontend.py'
    if ($LASTEXITCODE -ne 0) { throw 'PCM frontend regression tests failed' }
    $arguments = @(
        'scripts/diagnose_pcm_frontend.py',
        '--input-wav', $inputWav,
        '--analyzer', (Join-Path $kit 'bliss-mood.exe'),
        '--essentia-worker',
        (Join-Path $kit 'essentia-worker\bliss-essentia-worker.exe'),
        '--models-dir', (Join-Path $repo 'models'),
        '--output-dir', $output,
        '--offsets', '0,120',
        '--duration-seconds', '12'
    )
    python @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "PCM frontend diagnostic failed; see local logs: $output"
    }
    Write-Host "Private detailed report: $output\private-pcm-diagnostic.json"
}
~~~

The script prints four concise per-excerpt results, including Mel and
ONNX score errors. Generated WAV/JSON/log files remain LOCAL and PRIVATE;
do not upload music or private file paths. This diagnostic never treats
a failed numerical parity case as PASS and never modifies PR #16 or main.

## PCM 2×2 control: isolate resampling vs downmix

The **2026-10-20 first controlled 12-second test** used one common
float32 WAV (previously decoded from the real MP3) and compared the
original Essentia C++ DSP with production Rust (same models):

| Offset | Input | Max Mel difference | Mel coefficients over 0.001 | Max Voice difference |
| ---: | --- | ---: | ---: | ---: |
| 0s | native rate/channels | 0.000297233 | 0 | 0.000001740 |
| 0s | pre-normalized 16 kHz mono | 0.000080824 | 0 | 0.000000460 |
| **120s** | **native rate/channels** | **0.005901277** | **1,139** | **0.000345000** |
| **120s** | **pre-normalized 16 kHz mono** | **0.000134826** | **0** | **0.000008700** |

At offset 120s, the Mel max falls by about 44x when both receive
**already-converted 16-kHz mono**. On all four short clips the
aggregated head scores remain within 0.001, but **full-song parity
still FAILS** at 837 patches. The elimination of downmix and
resampling together strongly implicates their combined path, not
necessarily one individually.

The script now supports a **factorial 2×2 control** `--factorial`
requiring stereo source PCM with original sample rate != 16000 Hz:

| Input mode | What Rust and C++ still need to do |
| --- | --- |
| `native-rate` | Stereo downmix **and** resampling |
| `native-rate-mono` | **Only resampling** |
| `16khz-stereo` | **Only stereo downmix** |
| `16khz-mono` | Neither (FFT/Mel control) |

Each clip is generated via FFmpeg *once* and is identical for both
production backends. It uses the already generated local shared-PCM
file, **never rescans the 100 songs** or changes the model, audio
or sidecar data. If only native-rate modes differ, prioritize the Rust
`essentia_linear_resample()` approximation; if the `16khz-stereo`
case also differs, examine the `MonoLoader(downmix="mix")` stereo
path. Do not claim confirmation before the four measurements.

**PowerShell — four 12-second clips at the informative 120s offset:**

~~~powershell
& {
    $ErrorActionPreference = 'Stop'
    $repo = 'D:\LMS\bliss-mood-poc'
    $base = Join-Path $repo 'benchmark-essentia-real-20261020-160351'
    $kit = 'D:\LMS\essentia-cli-test'
    $inputWav = Join-Path $base 'mp3-wav-control-20261020-164836\control-from-mp3-decoded-float32.wav'
    $out = Join-Path $base ('pcm-factorial-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
    Set-Location $repo
    git switch feat/essentia-cpp-worker-backend
    if ($LASTEXITCODE -ne 0) { throw 'Branch switch failed' }
    git pull --ff-only
    if ($LASTEXITCODE -ne 0) { throw 'Git pull failed' }
    python -m unittest discover -s tests -p 'test_diagnose_pcm_frontend.py'
    if ($LASTEXITCODE -ne 0) { throw 'Factorial regression tests failed' }
    $arguments = @(
        'scripts/diagnose_pcm_frontend.py',
        '--input-wav', $inputWav,
        '--analyzer', (Join-Path $kit 'bliss-mood.exe'),
        '--essentia-worker', (Join-Path $kit 'essentia-worker\bliss-essentia-worker.exe'),
        '--models-dir', (Join-Path $repo 'models'),
        '--output-dir', $out,
        '--offsets', '120',
        '--duration-seconds', '12',
        '--factorial'
    )
    python @arguments
    if ($LASTEXITCODE -ne 0) { throw "Factorial diagnostic failed; logs in: $out" }
}
~~~

The output summary exposes the **four** cases with `mel_max`,
`mel_mean`, `mel_count_over_0_001`, `genre_max`, `mood_max`,
`voice_max`. The private JSON and temporary audio stay local;
neither a passing short clip nor a small difference can grant the
full-song or full-library compatibility gate.

## Root cause confirmed: Essentia uses float32 SRC_LINEAR ratio, Rust used float64 exact

**Independent original-source audit (2026-10-20):** Essentia's
`src/algorithms/standard/resample.cpp`, **streaming::Resample::configure**,
calculates `Real factor = outputSampleRate / inputSampleRate`; `Real`
is `float`. This already-rounded float is subsequently assigned to
libsamplerate's double `SRC_DATA.src_ratio`. The original
`libsamplerate/src/src_linear.c` advances the resampling input phase by
`1.0/src_ratio`, not by exact integer `inputRate/outputRate`.
Our Rust `src/audio_decode.rs` incorrectly used the exact float64
`input_rate as f64 / 16000.0`. On 44,100 -> 16,000 this changes the
per-output phase step by approximately **9.45e-8 source samples**,
which accumulates to ~**0.018 source samples after 12 seconds** and
over **one source sample after 14 minutes**. The Mel/ONNX drift comes
from phase, not the already exonerated stereo downmix.

**Reproduced against independent original libsamplerate** `src_simple`
with `SRC_LINEAR=4` on 12-second deterministic 44.1 kHz mono signal:
existing Rust exact-ratio formula produced up to **0.002083823**
PCM absolute difference; corrected Rust equivalent using the **f32
ratio before converting to f64** gave max **2.98e-8** on matching
samples. This independently confirms the exact phase-rounding
mechanism; it does not yet certify a full real-song parity scan.

**Fix implemented only in PR #17**:
- `src/audio_decode.rs` now computes
  `src_ratio = 16000f32 / (input_rate as f32)` and advances by
  `1.0f64 / f64::from(src_ratio)`.
- Source-derived independent libsamplerate PCM oracle regression added
  to Rust `cargo test`; no new native library dependency.
- Rust cache/preprocessing version bumped **v4 -> v5** consistently
  across all feature/mood scanner and Mel/embedding dump commands.
  Existing v4 features are **not reused** under the corrected v5 key.
  Original native C++ fingerprint remains unchanged.
- Deliberately preserve Rust's old *output frame count* behavior until
  its independent end-of-stream effects are measured. Patch counts
  already matched in the real-song experiment.

**Efficient real-music follow-up:** Use the existing 837-patch
float32 WAV, the previous original native Essentia full-song JSON,
and the previous Rust v4 JSON under
`benchmark-essentia-real-20261020-160351/mp3-wav-control-20261020-164836/`.
Run **ONLY one new Rust v5 analysis** on the same WAV and verify
identical audio SHA256, ONNX weights, full-song patch counts, class
identities, separate old/new Rust and C++ fingerprints and 0.001
per-class score tolerance. `scripts/verify_resampler_fix_on_existing_wav.py`
writes a new private report and returns failure if still above
threshold. Even `PASS_THIS_TRACK` is **not** the 100-song gate.

The corrected Windows analyzer was already built successfully by
**Windows x64 Actions run #39450757368**, exact source SHA
`9ca4d3d2e248a528008e70c9ba0951902b2acc67`
([link](https://github.com/chrober/bliss-mood-poc/actions/runs/39450757368)),
and the artifact `bliss-mood-windows-x64` was confirmed available.
The SHA includes the f32 resampling fix **and** the v5 preprocessing
cache identity; subsequent commits before this note modified only
Python helpers, tests, CI and documentation, not Rust. Download this
**pinned verified** Windows binary into a separate directory. The old
Essentia dev kit `bliss-mood.exe` is v4 and must not be used here.
No original C++ binary or full Windows development kit rebuild required.

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $repo = 'D:\LMS\bliss-mood-poc'
    $base = Join-Path $repo 'benchmark-essentia-real-20261020-160351'
    $control = Join-Path $base 'mp3-wav-control-20261020-164836'
    $kit = 'D:\LMS\bliss-mood-rust-v5-test'
    $out = Join-Path $base ('rust-v5-one-track-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
    Set-Location $repo
    git switch feat/essentia-cpp-worker-backend
    if ($LASTEXITCODE -ne 0) { throw 'Switch PR17 branch failed' }
    git pull --ff-only
    if ($LASTEXITCODE -ne 0) { throw 'Updating PR17 branch failed' }

    python -m unittest discover -s tests -p 'test_verify_resampler_fix_on_existing_wav.py'
    if ($LASTEXITCODE -ne 0) { throw 'Report verifier tests failed' }

    gh --version | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'GitHub CLI not available' }
    # Pinned proven successful Windows x64 run 39450757368, SHA 9ca4d3d.
    # It contains the precise v5 Rust resampler and cache fingerprint change;
    # subsequent PR17 commits to date changed ONLY scripts/tests/docs/CI.
    if (Test-Path -LiteralPath $kit) {
        throw "Choose fresh separate v5 kit directory, will not overwrite: $kit"
    }
    gh run download 39450757368 --repo chrober/bliss-mood-poc --name bliss-mood-windows-x64 --dir $kit
    if ($LASTEXITCODE -ne 0) { throw 'Windows binary artifact download failed' }
    $analyzer = Join-Path $kit 'bliss-mood.exe'
    if (-not (Test-Path -LiteralPath $analyzer)) {
        throw 'New v5 scanner binary missing in Windows artifact'
    }
    $arguments = @(
        'scripts/verify_resampler_fix_on_existing_wav.py',
        '--wav', (Join-Path $control 'control-from-mp3-decoded-float32.wav'),
        '--old-rust-json', (Join-Path $control 'rust-wav.json'),
        '--essentia-json', (Join-Path $control 'essentia-wav.json'),
        '--analyzer', $analyzer,
        '--models-dir', (Join-Path $repo 'models'),
        '--output-dir', $out,
        '--score-max-tolerance', '0.001'
    )
    python @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "v5 still fails one-song strict parity or verifier; local report $out"
    }
    Write-Host "Single full-song v5 vs saved original C++ PASS; $out"
}
```

Do not merge #17 solely from this single-track result: once the
new v5 analyzer validates this root cause, check a representative
same-cohort 100-song real-music gate with saved original C++ sidecars
and new Rust v5 data. **Do not alter PR #16 or main.**

## Windows PowerShell quick compatibility test

Prerequisites: local checkout of the #17 branch, unpacked dev kit
`D:\LMS\essentia-cli-test`, external ONNX weights in
`D:\LMS\bliss-mood-poc\models`, and a **real, bounded** Bliss
`TracksV2` subset (the path below is an example of the existing fixture).
Set `$music` to the actual read-only NAS root. For relative keys, pass
`--source-root` alone. For absolute old paths to be remapped, add
`--library-root <original-prefix>`.

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $repo = 'D:\LMS\bliss-mood-poc'
    $kit = 'D:\LMS\essentia-cli-test'
    $cohort = Join-Path $repo 'benchmark-workers-20261019-060347\sample-100.db'
    $models = Join-Path $repo 'models'
    $music = '\\192.168.1.100\music'  # Replace with actual source root
    $out = Join-Path $repo 'benchmark-essentia-cpp-real-parity'
    $analyzer = Join-Path $kit 'bliss-mood.exe'
    $worker = Join-Path $kit 'essentia-worker\bliss-essentia-worker.exe'

    foreach ($path in @($cohort, $analyzer, $worker)) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Required file missing: $path"
        }
    }
    foreach ($path in @($models, $music)) {
        if (-not (Test-Path -LiteralPath $path -PathType Container)) {
            throw "Required directory missing: $path"
        }
    }
    if (Test-Path -LiteralPath $out) {
        throw "Choose a NEW output directory, never overwrite: $out"
    }
    Set-Location $repo
    git fetch origin
    if ($LASTEXITCODE -ne 0) { throw 'Git fetch failed' }
    git switch feat/essentia-cpp-worker-backend
    if ($LASTEXITCODE -ne 0) { throw 'Git switch failed' }
    git pull --ff-only
    if ($LASTEXITCODE -ne 0) { throw 'Git pull failed' }

    python -m unittest discover -s tests -p 'test_benchmark_audio_backends.py'
    if ($LASTEXITCODE -ne 0) { throw 'Benchmark Python regression tests failed' }

    $args = @(
        'scripts/benchmark_audio_backends.py',
        '--cohort-db', $cohort,
        '--analyzer', $analyzer,
        '--essentia-worker', $worker,
        '--models-dir', $models,
        '--source-root', $music,
        '--output-dir', $out,
        '--models', 'genre,moodtheme,voice',
        '--workers', '1,2',
        '--repeats', '1',
        '--seed', '20261020',
        '--score-max-tolerance', '0.001'
    )
    python @args
    if ($LASTEXITCODE -ne 0) {
        throw "Real-music backend parity failed; inspect $out"
    }
    $r = Get-Content -LiteralPath (Join-Path $out 'summary.json') -Raw |
        ConvertFrom-Json
    Write-Host 'Numerical parity by worker count:'
    $r.backend_parity |
        Select-Object workers,tracks_and_heads,compared_scores,
            patch_count_mismatches,maximum_absolute_score_difference,
            mean_absolute_score_difference,fingerprint_heads_checked |
        Format-List
    Write-Host "Validated sidecars, reports, and logs: $out"
}
```

**If this fails:** inspect the error and the run's `*.stderr.txt`.
If scores differ beyond tolerance or patch counts drift, the benchmark
also writes **`parity-failure.json`** with the worst track, class index,
per-head max/mean errors, observed score values and up to ten patch
mismatch examples. Do not change the tolerance to force a pass. A
successful run writes `summary.json` and `runs.csv`. Share only
sanitized diagnostic excerpts; all raw JSON and SQLite files can
contain private music file paths and must stay local.

## Reusing the verified Windows test kit

The original **successful and verified** downloadable artifact is from
run `39421541546`, not an unspecified "latest" run. On Windows with
`gh` authenticated and the repository checkout at
`D:\LMS\bliss-mood-poc`, the package can be downloaded reproducibly:

```powershell
& {
    $ErrorActionPreference = 'Stop'
    Set-Location 'D:\LMS\bliss-mood-poc'
    $kit = 'D:\LMS\essentia-cli-test'
    if (Test-Path -LiteralPath $kit) {
        throw "Kit directory already exists; inspect instead of overwriting: $kit"
    }
    gh run download 39421541546 `
        --repo chrober/bliss-mood-poc `
        --name bliss-mood-essentia-windows-x64-dev `
        --dir $kit
    if ($LASTEXITCODE -ne 0) { throw 'Kit download failed' }
    if (-not (Test-Path -LiteralPath (Join-Path $kit 'essentia-worker\worker-dependencies.json'))) {
        throw 'Expected signed native dependency manifest not found'
    }
    Write-Host "Package: $kit"
}
```

The `bliss-mood.exe` from this immutable artifact is sufficient for the
next **real-data** run because subsequent PR #17 fixes were confined to
the Python benchmark and accompanying tests/docs. This does **not**
claim that a rebuilt CLI at a newer commit has already passed CI.

## After real-music parity

Only if these results pass, evaluate the **new Essentia sidecar**, for
example `round-01-workers-01-essentia.db`, with PR #16's unchanged
`evaluate_similarity.py` using `--include-experimental`. Keep the
previous Rust sidecar separate and check the exact track key intersection
before comparing metric distributions. This is the next investigation,
not part of the initial compatibility acceptance test.

**Not in scope yet:** production mixing metric selection, subjective
similarity truth, Linux/macOS/Raspberry Pi distribution, licensing audit,
or changing the default `--audio-backend rust`.
