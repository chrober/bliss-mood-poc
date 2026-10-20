//! Shared Rust audio decoder used by both the production Rust-ONNX frontend
//! and the standalone (ONNX-free) native Essentia DSP parity harness.
//! This isolates the exact reference DSP behavior without duplicating it.
use crate::preprocess;
use anyhow::{bail, Context, Result};
use std::{path::Path, process::Command as ProcessCommand};

/// Match Essentia MonoLoader(resampleQuality=4) rather than FFmpeg's default
/// downmix and sample-rate converter.  Essentia averages stereo samples at
/// 0.5/0.5 and its streaming Resample uses libsamplerate SRC_LINEAR (quality 4).
pub(crate) fn essentia_linear_resample(samples: &[f32], input_rate: usize) -> Vec<f32> {
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

pub(crate) fn ffmpeg_pcm_mono_16k(input: &Path) -> Result<Vec<f32>> {
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
