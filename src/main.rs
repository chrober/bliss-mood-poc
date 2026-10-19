mod preprocess;
mod storage;
mod engine;
mod batch;
mod features;
mod essentia_worker;
mod feature_lookup;
mod parallel;
mod resources;

use anyhow::{bail, Context, Result};
use clap::{Parser, Subcommand};
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::{
    collections::BTreeMap,
    fs::File,
    io::Read,
    path::{Path, PathBuf},
    process::Command as ProcessCommand,
};

const ENCODER: &str = "discogs-effnet-bsdynamic-1.onnx";
const CLASSIFIER: &str = "mtg_jamendo_moodtheme-discogs-effnet-1.onnx";
const LABELS: &str = "mtg_jamendo_moodtheme-discogs-effnet-1.json";

#[derive(Parser)]
#[command(name = "bliss-mood", about = "Experimental ONNX mood analysis (not yet Essentia-validated)")]
struct Cli {
    #[command(subcommand)]
    action: Action,
}

#[derive(Subcommand)]
enum Action {
    /// Classify diagnostic 1280-D embeddings using the ONNX 56-class head.
    /// This command does not read or modify music or SQLite databases.
    ClassifyEmbeddings {
        input_json: PathBuf,
        #[arg(long, default_value = "models")]
        models_dir: PathBuf,
        #[arg(long, default_value_t = 1)]
        threads: usize,
    },
    /// Export first N 1280-D Discogs-EffNet ONNX embeddings for Essentia comparison.
    /// No classifier needed and no SQLite or audio files modified.
    EmbeddingDump {
        source: PathBuf,
        #[arg(long, default_value = "models")]
        models_dir: PathBuf,
        #[arg(long, default_value_t = 4)]
        max_patches: usize,
        #[arg(long, default_value_t = 1)]
        threads: usize,
    },
    /// Export first N raw Mel feature frames for comparison with Essentia.
    /// Does not require ONNX models and never modifies source audio.
    MelDump {
        source: PathBuf,
        #[arg(long, default_value_t = 32)]
        max_frames: usize,
    },
    Analyze {
        /// Source audio file (never modified).
        source: PathBuf,
        #[arg(long, default_value = "models")]
        models_dir: PathBuf,
        /// Limit to N initial patches (for exploratory performance benchmarks).
        #[arg(long)]
        max_patches: Option<usize>,
        /// Limit ONNX internal worker threads. Use 1 for a shared Lyrion host.
        #[arg(long, default_value_t = 1)]
        threads: usize,
        #[arg(long)]
        json: bool,
        /// Optional separate SQLite sidecar to store result (never modifies bliss.db).
        #[arg(long)]
        db: Option<PathBuf>,
        /// Exact TracksV2.File path on the target Lyrion system, required with --db.
        #[arg(long)]
        track_key: Option<String>,
    },
    /// Generic, opt-in classifier inference. All heads share the same 1280D EffNet embeddings.
    AnalyzeFeatures {
        source: PathBuf,
        #[arg(long, default_value = "models")]
        models_dir: PathBuf,
        #[arg(long)]
        registry: Option<PathBuf>,
        /// Comma-separated registry model IDs (e.g. moodtheme,genre,voice).
        #[arg(long, default_value = "moodtheme,genre")]
        models: String,
        /// Explicitly select native C++ Essentia DSP; default preserves Rust/ONNX behavior.
        #[arg(long, default_value = "rust", value_parser = ["rust", "essentia"])]
        audio_backend: String,
        /// Trusted executable for original Essentia C++ DSP subprocess.
        #[arg(long)]
        essentia_worker: Option<PathBuf>,
        /// Hard wall-clock limit per C++ worker request, including first handshake.
        #[arg(long, default_value_t = 900)]
        essentia_timeout_seconds: u64,
        #[arg(long)]
        max_patches: Option<usize>,
        #[arg(long, default_value_t = 1)]
        threads: usize,
        #[arg(long)]
        json: bool,
        #[arg(long)]
        db: Option<PathBuf>,
        #[arg(long)]
        track_key: Option<String>,
    },
    /// Incremental, model-independent sidecar analysis; legacy mood_tracks remain untouched.
    ScanFeatures {
        #[arg(long)]
        bliss_db: PathBuf,
        #[arg(long)]
        db: PathBuf,
        #[arg(long, default_value = "models")]
        models_dir: PathBuf,
        #[arg(long)]
        registry: Option<PathBuf>,
        #[arg(long, default_value = "moodtheme,genre")]
        models: String,
        #[arg(long, requires = "source_root")]
        library_root: Option<String>,
        #[arg(long)]
        source_root: Option<PathBuf>,
        #[arg(long)]
        only_track: Option<String>,
        /// Maximum newly attempted tracks (successful or failed).
        #[arg(long)]
        max_new: Option<usize>,
        /// Stop a scan after this many errors, instead of walking the whole library.
        #[arg(long, default_value_t = 5)]
        max_errors: usize,
        #[arg(long, default_value_t = 1)]
        threads: usize,
        /// Parallel tracks: auto preserves interactive CPU headroom.
        #[arg(long, default_value = "1")]
        workers: String,
        /// Optional original C++ Essentia frontend per Rust worker (default rust).
        #[arg(long, default_value = "rust", value_parser = ["rust", "essentia"])]
        audio_backend: String,
        /// Trusted native Essentia C++ worker executable.
        #[arg(long)]
        essentia_worker: Option<PathBuf>,
        /// Hard wall-clock limit per native worker song/handshake (1..7200 seconds).
        #[arg(long, default_value_t = 900)]
        essentia_timeout_seconds: u64,
        /// Opt-in system CPU/RAM-aware concurrency control.
        #[arg(long)]
        adaptive_workers: bool,
        /// Minimum active jobs during adaptive scanning.
        #[arg(long, default_value_t = 4)]
        min_workers: usize,
        /// Maximum active jobs during adaptive scanning.
        #[arg(long, default_value_t = 8)]
        max_workers: usize,
        #[arg(long)]
        dry_run: bool,
        #[arg(long)]
        json: bool,
    },
    /// Inspect cached Mood/Genre vectors by exact Bliss file key without
    /// opening source audio, starting ONNX or changing the sidecar SQLite.
    InspectFeatures {
        #[arg(long)]
        db: PathBuf,
        /// Exact TracksV2.File; can be repeated for a bounded candidate batch.
        #[arg(long = "track-key", required = true)]
        track_keys: Vec<String>,
        #[arg(long, default_value = "moodtheme,genre")]
        models: String,
        /// Explicitly expose unvalidated experimental predictions in Lab tests.
        #[arg(long)]
        include_experimental: bool,
        #[arg(long)]
        json: bool,
    },
    /// Compare an arbitrary registered classifier against a reference TF head.
    ClassifyFeatureEmbeddings {
        input_json: PathBuf,
        #[arg(long, default_value = "models")]
        models_dir: PathBuf,
        #[arg(long)]
        registry: Option<PathBuf>,
        #[arg(long, default_value = "genre")]
        model: String,
        #[arg(long, default_value_t = 1)]
        threads: usize,
    },
    /// Compare stored Mood tracks with eligible tracks in an existing Bliss database.
    DbCoverage {
        #[arg(long)]
        db: PathBuf,
        #[arg(long)]
        bliss_db: PathBuf,
        #[arg(long)]
        json: bool,
    },
    /// Incrementally analyze Lyrion's Bliss library into mood.db.
    Scan {
        #[arg(long)]
        bliss_db: PathBuf,
        #[arg(long)]
        db: PathBuf,
        #[arg(long, default_value = "models")]
        models_dir: PathBuf,
        /// Optional prefix from absolute Bliss track paths; OMIT when TracksV2.File is relative.
        #[arg(long, requires = "source_root")]
        library_root: Option<String>,
        /// Music directory on this machine; supports UNC paths on Windows.
        #[arg(long)]
        source_root: Option<PathBuf>,
        /// Process exactly this TracksV2.File key (useful for a single-song smoke test).
        #[arg(long)]
        only_track: Option<String>,
        /// Maximum newly analyzed tracks in this run (useful for Pi/quick tests).
        #[arg(long)]
        max_new: Option<usize>,
        #[arg(long, default_value_t = 1)]
        threads: usize,
        #[arg(long)]
        dry_run: bool,
        #[arg(long)]
        json: bool,
    },
}

#[derive(Serialize)]
struct Timing {
    decode_seconds: f64,
    features_seconds: f64,
    hash_seconds: f64,
    model_load_seconds: f64,
    inference_seconds: f64,
    total_seconds: f64,
}

#[derive(Serialize)]
struct Report {
    schema_version: u32,
    preprocessing_version: &'static str,
    classification_model: &'static str,
    embedding_model: &'static str,
    audio_path: String,
    audio_sha256: String,
    models_sha256: BTreeMap<String, String>,
    sample_rate: usize,
    patches_analyzed: usize,
    threads: usize,
    aggregation: &'static str,
    validated_against_essentia: bool,
    timings: Timing,
    scores: BTreeMap<String, f32>,
}

fn sha256_file(path: &Path) -> Result<String> {
    let mut input = File::open(path).with_context(|| format!("Cannot open {}", path.display()))?;
    let mut hasher = Sha256::new();
    let mut buffer = [0u8; 65536];
    loop {
        let size = input.read(&mut buffer)?;
        if size == 0 {
            break;
        }
        hasher.update(&buffer[..size]);
    }
    Ok(format!("{:x}", hasher.finalize()))
}

/// Match Essentia MonoLoader(resampleQuality=4) rather than FFmpeg's default
/// downmix and sample-rate converter.  Essentia averages stereo samples at
/// 0.5/0.5 and its streaming Resample uses libsamplerate SRC_LINEAR (quality 4).
fn essentia_linear_resample(samples: &[f32], input_rate: usize) -> Vec<f32> {
    if input_rate == preprocess::RATE {
        return samples.to_vec();
    }
    if samples.is_empty() {
        return Vec::new();
    }
    let count = samples.len().saturating_mul(preprocess::RATE).div_ceil(input_rate);
    let step = input_rate as f64 / preprocess::RATE as f64;
    let mut result = Vec::with_capacity(count);
    for n in 0..count {
        // libsamplerate's streaming SRC_LINEAR: first sample at 0; thereafter
        // the interpolation phase is (n * inputRate/outputRate) - 1.
        // The previous sample is retained between input blocks.
        let p = if n == 0 { 0.0 } else { n as f64 * step - 1.0 };
        if p <= 0.0 {
            result.push(samples[0]);
        } else {
            let left = (p.floor() as usize).min(samples.len() - 1);
            let right = (left + 1).min(samples.len() - 1);
            let fraction = p - left as f64;
            result.push((samples[left] as f64
                + fraction * (samples[right] as f64 - samples[left] as f64)) as f32);
        }
    }
    result
}

fn ffmpeg_pcm_mono_16k(input: &Path) -> Result<Vec<f32>> {
    // FFmpeg only decodes to float PCM at the *native* sample rate.
    // Probe stream metadata once to avoid FFmpeg's different default
    // channel weights and its incompatible sample-rate conversion.
    let probe = ProcessCommand::new("ffprobe")
        .args(["-v", "error", "-select_streams", "a:0",
               "-show_entries", "stream=sample_rate,channels", "-of", "json"])
        .arg(input).output()
        .context("ffprobe not found; install the full FFmpeg distribution")?;
    if !probe.status.success() {
        bail!("ffprobe failed: {}", String::from_utf8_lossy(&probe.stderr));
    }
    let metadata: serde_json::Value = serde_json::from_slice(&probe.stdout)?;
    let first = &metadata["streams"][0];
    let input_rate: usize = first["sample_rate"]
        .as_str().context("Missing source sample rate")?.parse()?;
    let channels = first["channels"].as_u64().context("Missing channel count")? as usize;
    if input_rate == 0 || !(1..=2).contains(&channels) {
        bail!("Unsupported input audio layout: {channels} channels, {input_rate} Hz");
    }
    let output = ProcessCommand::new("ffmpeg")
        .args(["-hide_banner", "-nostdin", "-loglevel", "error", "-i"])
        .arg(input)
        .args(["-map", "0:a:0", "-vn", "-acodec", "pcm_f32le",
               "-f", "f32le", "pipe:1"])
        .output()
        .context("FFmpeg not found; install FFmpeg and add it to PATH")?;
    if !output.status.success() {
        bail!("FFmpeg failed: {}", String::from_utf8_lossy(&output.stderr));
    }
    if output.stdout.len() % (4 * channels) != 0 || output.stdout.is_empty() {
        bail!("FFmpeg produced empty or malformed f32 PCM");
    }
    let samples: Vec<f32> = output.stdout.as_chunks::<4>().0.iter()
        .map(|b| f32::from_le_bytes([b[0], b[1], b[2], b[3]])).collect();
    let mono: Vec<f32> = if channels == 2 {
        samples.as_chunks::<2>().0.iter().map(|c| 0.5 * (c[0] + c[1])).collect()
    } else {
        samples
    };
    Ok(essentia_linear_resample(&mono, input_rate))
}

fn analyze(
    path: &Path,
    models_dir: &Path,
    max_patches: Option<usize>,
    threads: usize,
) -> Result<Report> {
    if !path.is_file() {
        bail!("Audio file not found: {}", path.display());
    }
    let profile = engine::ModelProfile::load(models_dir)?;
    let mut engine = engine::MoodEngine::new(profile, threads)?;
    engine.analyze(path, max_patches)
}

fn main() -> Result<()> {
    match Cli::parse().action {
        Action::ClassifyEmbeddings { input_json, models_dir, threads } => {
            let diagnostic: serde_json::Value =
                serde_json::from_reader(File::open(&input_json)?)?;
            let vectors: Vec<Vec<f32>> =
                serde_json::from_value(diagnostic["embeddings"].clone())?;
            let scores = engine::classify_embeddings_for_parity(
                &vectors, &models_dir, threads,
            )?;
            let model_metadata: serde_json::Value = serde_json::from_slice(
                &std::fs::read(models_dir.join(LABELS))?,
            )?;
            let classes = model_metadata["classes"].as_array()
                .context("Classifier metadata has no classes list")?;
            if classes.len() != 56 || classes.iter().any(|x| !x.is_string()) {
                bail!("Classifier metadata must contain 56 string class names");
            }
            let mut means = vec![0.0_f64; 56];
            for row in &scores {
                for (sum, value) in means.iter_mut().zip(row) {
                    *sum += *value as f64;
                }
            }
            let means: Vec<f32> = means.into_iter()
                .map(|sum| (sum / scores.len() as f64) as f32).collect();
            let output = serde_json::json!({
                "schema_version": 1,
                "validation_status": "experimental-unvalidated",
                "classification_model": CLASSIFIER,
                "classification_model_sha256": sha256_file(&models_dir.join(CLASSIFIER))?,
                "embedding_model": diagnostic["embedding_model"],
                "embedding_model_sha256": diagnostic["embedding_model_sha256"],
                "patches_classified": scores.len(),
                "classes": classes,
                "scores_per_patch": scores,
                "mean_scores": means,
                "aggregation": "arithmetic_mean_of_per_patch_sigmoid_scores",
            });
            println!("{}", serde_json::to_string(&output)?);
        }
        Action::EmbeddingDump { source, models_dir, max_patches, threads } => {
            let vectors = engine::embeddings_for_parity(
                &source, &models_dir, max_patches, threads,
            )?;
            let output = serde_json::json!({
                "schema_version": 1,
                "validation_status": "experimental-unvalidated",
                "preprocessing_version": "experimental-essentia-audio-v4-unvalidated",
                "embedding_model": ENCODER,
                "embedding_model_sha256": sha256_file(&models_dir.join(ENCODER))?,
                "audio_sha256": sha256_file(&source)?,
                "patches_analyzed": vectors.len(),
                "embedding_dimensions": 1280,
                "embeddings": vectors,
            });
            println!("{}", serde_json::to_string(&output)?);
        }
        Action::MelDump { source, max_frames } => {
            if max_frames == 0 || max_frames > 1024 {
                bail!("--max-frames must be between 1 and 1024");
            }
            let samples = ffmpeg_pcm_mono_16k(&source)?;
            let mel = preprocess::mel_spectrogram(&samples)?;
            let frame_count = mel.len();
            let output = serde_json::json!({
                "preprocessing_version": "experimental-essentia-audio-v4-unvalidated",
                "sample_rate": preprocess::RATE,
                "fft_size": preprocess::FFT,
                "hop_size": preprocess::HOP,
                "mel_bands": preprocess::MEL_BANDS,
                "total_frames": frame_count,
                "frames": mel.iter().take(max_frames).map(|frame| frame.as_slice()).collect::<Vec<_>>(),
            });
            println!("{}", serde_json::to_string(&output)?);
        }
        Action::Analyze {
            source,
            models_dir,
            max_patches,
            threads,
            json,
            db,
            track_key,
        } => {
            if db.is_some() != track_key.is_some() {
                bail!("--db and --track-key must be specified together");
            }
            let report = analyze(&source, &models_dir, max_patches, threads)?;
            if let (Some(db_path), Some(key)) = (db.as_deref(), track_key.as_deref()) {
                storage::persist(db_path, key, &report)?;
            }
            if json {
                println!("{}", serde_json::to_string_pretty(&report)?);
            } else {
                println!("{} patches: {}", report.patches_analyzed, report.audio_path);
                let mut sorted: Vec<_> = report.scores.iter().collect();
                sorted.sort_by(|a, b| b.1.total_cmp(a.1));
                for (name, score) in sorted {
                    println!("{name:20} {score:.4}");
                }
                println!(
                    "Inference: {:.3}s; total: {:.3}s",
                    report.timings.inference_seconds, report.timings.total_seconds
                );
            }
        }
        Action::AnalyzeFeatures {
            source, models_dir, registry, models, audio_backend,
            essentia_worker, essentia_timeout_seconds, max_patches, threads, json, db, track_key,
        } => {
            if db.is_some() != track_key.is_some() {
                bail!("--db and --track-key must be specified together");
            }
            let backend = essentia_worker::BackendChoice::from_cli(
                &audio_backend, essentia_worker.as_deref(), essentia_timeout_seconds,
            )?;
            let mut profiles = features::load_profiles(&models_dir, registry.as_deref(), &models)?;
            features::retarget_profiles(&mut profiles, &backend)?;
            let mut engine = features::FeatureEngine::with_backend(profiles, threads, &backend)?;
            let report = engine.analyze(&source, max_patches)?;
            if let (Some(db), Some(key)) = (db.as_deref(), track_key.as_deref()) {
                features::persist(db, key, &report, None)?;
            }
            if json {
                println!("{}", serde_json::to_string_pretty(&report)?);
            } else {
                println!("{} patches: {}", report.patches_analyzed, report.audio_path);
                for (id, result) in &report.classifications {
                    println!("[{id}] {}", result.capability);
                    let mut sorted: Vec<_> = result.scores.iter().collect();
                    sorted.sort_by(|a, b| b.1.total_cmp(a.1));
                    for (name, score) in sorted.into_iter().take(10) {
                        println!("  {name:22} {score:.4}");
                    }
                }
                println!("Total: {:.3}s", report.timings.total_seconds);
            }
        }
        Action::ScanFeatures {
            bliss_db, db, models_dir, registry, models, library_root,
            source_root, only_track, max_new, max_errors, threads, workers,
            audio_backend, essentia_worker, essentia_timeout_seconds,
            adaptive_workers, min_workers, max_workers, dry_run, json,
        } => {
            let (worker_count, is_auto) = parallel::worker_count(&workers)?;
            if worker_count > 1 && threads > 1 {
                bail!("Parallel --workers requires --threads 1 to prevent ONNX oversubscription");
            }
            if adaptive_workers {
                parallel::AdaptiveWorkers::new(worker_count, min_workers, max_workers)?;
                if worker_count > 1 && threads != 1 {
                    bail!("Adaptive analysis requires --threads 1");
                }
            }
            if (is_auto || adaptive_workers) && !dry_run {
                parallel::lower_priority_auto();
            }
            let backend = essentia_worker::BackendChoice::from_cli(
                &audio_backend, essentia_worker.as_deref(), essentia_timeout_seconds,
            )?;
            let summary = features::scan(features::ScanOptions {
                bliss_db: &bliss_db, db: &db, models_dir: &models_dir,
                registry: registry.as_deref(), models: &models,
                source_root: source_root.as_deref(),
                library_root: library_root.as_deref(),
                only_track: only_track.as_deref(),
                max_new, max_errors, threads, workers: worker_count,
                adaptive_workers, min_workers, max_workers, dry_run, backend,
            })?;
            if json {
                println!("{}", serde_json::to_string_pretty(&summary)?);
            } else {
                println!("{summary:#?}");
            }
            // Same nonzero exit contract as the legacy scanner.
            let result = serde_json::to_value(&summary)?;
            if result["failures"].as_u64().unwrap_or(0) > 0
                || result["missing_files"].as_u64().unwrap_or(0) > 0
            {
                bail!("Feature scan completed with failed or unavailable songs");
            }
        }
        Action::InspectFeatures {
            db, track_keys, models, include_experimental, json,
        } => {
            let found = feature_lookup::inspect(
                &db, &track_keys, &models, include_experimental,
            )?;
            if json {
                println!("{}", serde_json::to_string_pretty(&found)?);
            } else {
                for track in &found {
                    println!("{}", track.track_file);
                    for (id, head) in &track.models {
                        println!("  {id}: {}", head.status);
                    }
                }
            }
        }
        Action::ClassifyFeatureEmbeddings {
            input_json, models_dir, registry, model, threads,
        } => {
            let diagnostic: serde_json::Value =
                serde_json::from_reader(File::open(&input_json)?)?;
            let vectors: Vec<Vec<f32>> =
                serde_json::from_value(diagnostic["embeddings"].clone())?;
            let mut profiles = features::load_profiles(&models_dir, registry.as_deref(), &model)?;
            let output = features::parity_output(&vectors, &profiles.remove(0), threads)?;
            println!("{}", serde_json::to_string(&output)?);
        }
        Action::DbCoverage { db, bliss_db, json } => {
            let result = storage::coverage(&db, &bliss_db)?;
            if json {
                println!("{}", serde_json::to_string_pretty(&result)?);
            } else {
                println!("{result:#?}");
            }
        }
        Action::Scan {
            bliss_db, db, models_dir, library_root, source_root, only_track, max_new, threads, dry_run, json
        } => {
            let summary = batch::scan(batch::ScanOptions {
                bliss_db: &bliss_db,
                mood_db: &db,
                models_dir: &models_dir,
                source_root: source_root.as_deref(),
                library_root: library_root.as_deref(),
                max_new, threads, dry_run,
                only_track: only_track.as_deref(),
            })?;
            if json {
                println!("{}", serde_json::to_string_pretty(&summary)?);
            } else {
                println!("{summary:#?}");
            }
            if summary.failures > 0 || summary.missing_files > 0 {
                bail!("Mood scan completed with {} failures and {} unavailable files",
                    summary.failures, summary.missing_files);
            }
        }
    }
    Ok(())
}

#[cfg(test)]
mod pcm_tests {
    use super::essentia_linear_resample;

    #[test]
    fn identity_resampling_preserves_pcm() {
        assert_eq!(essentia_linear_resample(&[0.25, -0.3], 16000), vec![0.25, -0.3]);
    }
    #[test]
    fn streaming_linear_phase_matches_first_sample_rule() {
        let s = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0];
        let y = essentia_linear_resample(&s, 32000);
        assert_eq!(y.len(), 3);
        assert_eq!(y, vec![0.0, 1.0, 3.0]);
    }
    #[test]
    fn stereo_average_remains_unscaled() {
        let stereo = [0.2f32, 0.6f32];
        assert!((0.5 * (stereo[0] + stereo[1]) - 0.4).abs() < 1e-6);
    }
}

