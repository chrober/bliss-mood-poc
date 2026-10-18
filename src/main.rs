mod preprocess;
mod storage;
mod engine;
mod batch;

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

fn ffmpeg_pcm_mono_16k(input: &Path) -> Result<Vec<f32>> {
    let output = ProcessCommand::new("ffmpeg")
        .args(["-hide_banner", "-nostdin", "-loglevel", "error", "-i"])
        .arg(input)
        .args([
            "-map", "0:a:0", "-vn", "-ac", "1", "-ar", "16000",
            "-f", "f32le", "-acodec", "pcm_f32le", "pipe:1",
        ])
        .output()
        .context("FFmpeg not found; install FFmpeg and add it to PATH")?;
    if !output.status.success() {
        bail!("FFmpeg failed: {}", String::from_utf8_lossy(&output.stderr));
    }
    if output.stdout.len() % 4 != 0 || output.stdout.is_empty() {
        bail!("FFmpeg produced empty or malformed f32 PCM");
    }
    Ok(output.stdout.as_chunks::<4>().0.iter()
        .map(|four| f32::from_le_bytes([four[0], four[1], four[2], four[3]]))
        .collect())
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
        Action::MelDump { source, max_frames } => {
            if max_frames == 0 || max_frames > 1024 {
                bail!("--max-frames must be between 1 and 1024");
            }
            let samples = ffmpeg_pcm_mono_16k(&source)?;
            let mel = preprocess::mel_spectrogram(&samples)?;
            let frame_count = mel.len();
            let output = serde_json::json!({
                "preprocessing_version": "experimental-slaney-v1-unvalidated",
                "sample_rate": preprocess::RATE,
                "fft_size": preprocess::FFT,
                "hop_size": preprocess::HOP,
                "mel_bands": preprocess::MEL_BANDS,
                "total_frames": frame_count,
                "frames": mel.iter().take(max_frames).collect::<Vec<_>>(),
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
