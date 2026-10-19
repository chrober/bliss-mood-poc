//! CLI-only numerical reference for the native Essentia C++ parity workflow.
//! Reuses the ACTUAL existing Rust Mel implementation; never links ONNX Runtime.
//! Restricting the fixture to 16kHz mono PCM16 means hound reads the same
//! lossless decoded sample values used by ffmpeg_pcm_mono_16k.
#[path = "../../../src/preprocess.rs"]
mod preprocess;

use anyhow::{bail, Context, Result};
use std::{env, path::Path};

fn main() -> Result<()> {
    let mut args = env::args_os();
    let _program = args.next();
    if args.next().as_deref() != Some(std::ffi::OsStr::new("mel-dump")) {
        bail!("Usage: rust-mel-reference mel-dump WAV --max-frames 1024");
    }
    let source = args.next().context("Expected WAV source")?;
    if args.next().as_deref() != Some(std::ffi::OsStr::new("--max-frames")) {
        bail!("Expected --max-frames");
    }
    let limit = args.next().context("Missing max-frames value")?
        .to_string_lossy().parse::<usize>()?;
    if !(1..=1024).contains(&limit) || args.next().is_some() {
        bail!("Max frames must be 1..=1024 and no extra arguments are allowed");
    }

    let mut reader = hound::WavReader::open(Path::new(&source))?;
    let spec = reader.spec();
    if spec.channels != 1 || spec.sample_rate != 16_000 ||
        spec.bits_per_sample != 16 || spec.sample_format != hound::SampleFormat::Int
    {
        bail!("Parity reference only supports deterministic mono 16kHz PCM16 WAV");
    }
    let samples = reader.samples::<i16>()
        .map(|v| v.map(|x| f32::from(x) / 32_768.0))
        .collect::<Result<Vec<_>, _>>()?;
    let frames = preprocess::mel_spectrogram(&samples)?;
    println!("{}", serde_json::json!({
        "total_frames": frames.len(),
        "frames": frames.iter().take(limit).collect::<Vec<_>>(),
    }));
    Ok(())
}
