mod preprocess;

use anyhow::{bail, Context, Result};
use clap::{Parser, Subcommand};
use ort::{session::Session, value::TensorRef};
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::{
    collections::BTreeMap,
    fs::File,
    io::Read,
    path::{Path, PathBuf},
    process::Command as ProcessCommand,
    time::Instant,
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
    Ok(output.stdout.chunks_exact(4)
        .map(|four| f32::from_le_bytes([four[0], four[1], four[2], four[3]]))
        .collect())
}

/// This model exposes an auxiliary 1280-dimensional embedding output.
fn embedding(session: &mut Session, patch: &[f32]) -> Result<Vec<f32>> {
    let input = TensorRef::from_array_view(([1usize, 128usize, 96usize], patch))?;
    let outputs = session.run(ort::inputs![input])?;
    for value in outputs.values() {
        let (_, tensor) = value.try_extract_tensor::<f32>()?;
        if tensor.len() == 1280 {
            return Ok(tensor.to_vec());
        }
    }
    bail!("Embedding model did not expose a 1280-dimensional tensor");
}

fn mood_scores(session: &mut Session, vector: &[f32]) -> Result<Vec<f32>> {
    let input = TensorRef::from_array_view(([1usize, 1280usize], vector))?;
    let outputs = session.run(ort::inputs![input])?;
    for value in outputs.values() {
        let (_, tensor) = value.try_extract_tensor::<f32>()?;
        if tensor.len() == 56 && tensor.iter().all(|x| x.is_finite() && (0.0..=1.0).contains(x)) {
            return Ok(tensor.to_vec());
        }
    }
    bail!("Mood classifier did not expose 56 finite sigmoid probabilities");
}

fn analyze(
    path: &Path,
    models_dir: &Path,
    max_patches: Option<usize>,
    threads: usize,
) -> Result<Report> {
    let started = Instant::now();
    if !path.is_file() {
        bail!("Audio file not found: {}", path.display());
    }
    if max_patches == Some(0) || threads == 0 {
        bail!("--max-patches and --threads must be >= 1");
    }
    let paths = [models_dir.join(ENCODER), models_dir.join(CLASSIFIER)];
    for model_path in &paths {
        if !model_path.is_file() {
            bail!(
                "Model missing: {}. Run scripts/download-models.ps1 first.",
                model_path.display()
            );
        }
    }
    let label_content =
        std::fs::read(models_dir.join(LABELS)).context("Cannot read model label metadata")?;
    let meta: serde_json::Value = serde_json::from_slice(&label_content)?;
    let labels: Vec<String> = meta["classes"]
        .as_array()
        .context("Label metadata has no 'classes' array")?
        .iter()
        .map(|v| v.as_str().map(ToOwned::to_owned).context("Non-string class label"))
        .collect::<Result<_>>()?;
    if labels.len() != 56 {
        bail!("Expected 56 labels, found {}", labels.len());
    }

    let decode_started = Instant::now();
    let samples = ffmpeg_pcm_mono_16k(path)?;
    let decode_seconds = decode_started.elapsed().as_secs_f64();

    let features_started = Instant::now();
    let mel = preprocess::mel_spectrogram(&samples)?;
    let patches = preprocess::patches(&mel, max_patches)?;
    let features_seconds = features_started.elapsed().as_secs_f64();

    let model_started = Instant::now();
    let env = ort::init().build()?;
    let mut encoder = Session::builder(&env)?
        .with_intra_threads(threads)?
        .commit_from_file(&paths[0])
        .context("Cannot initialize Discogs-EffNet ONNX model")?;
    let mut classifier = Session::builder(&env)?
        .with_intra_threads(threads)?
        .commit_from_file(&paths[1])
        .context("Cannot initialize MTG-Jamendo Mood/Theme ONNX model")?;
    let model_load_seconds = model_started.elapsed().as_secs_f64();

    let infer_started = Instant::now();
    let n = patches.len();
    let mut totals = vec![0.0_f64; 56];
    for patch in &patches {
        let vector = embedding(&mut encoder, patch)?;
        let scores = mood_scores(&mut classifier, &vector)?;
        for (acc, value) in totals.iter_mut().zip(scores) {
            *acc += f64::from(value);
        }
    }
    let inference_seconds = infer_started.elapsed().as_secs_f64();

    let scores = labels.into_iter()
        .zip(totals.into_iter().map(|v| (v / n as f64) as f32))
        .collect();
    let models_sha256 = paths.iter()
        .map(|p| Ok((p.file_name().unwrap().to_string_lossy().to_string(), sha256_file(p)?)))
        .collect::<Result<_>>()?;

    Ok(Report {
        schema_version: 1,
        preprocessing_version: "experimental-slaney-v1-unvalidated",
        classification_model: CLASSIFIER,
        embedding_model: ENCODER,
        audio_path: path.display().to_string(),
        audio_sha256: sha256_file(path)?,
        models_sha256,
        sample_rate: preprocess::RATE,
        patches_analyzed: n,
        threads,
        aggregation: "arithmetic_mean_of_per_patch_sigmoid_scores",
        validated_against_essentia: false,
        timings: Timing {
            decode_seconds,
            features_seconds,
            model_load_seconds,
            inference_seconds,
            total_seconds: started.elapsed().as_secs_f64(),
        },
        scores,
    })
}

fn main() -> Result<()> {
    match Cli::parse().action {
        Action::Analyze {
            source,
            models_dir,
            max_patches,
            threads,
            json,
        } => {
            let report = analyze(&source, &models_dir, max_patches, threads)?;
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
    }
    Ok(())
}
