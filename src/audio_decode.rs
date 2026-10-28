//! Shared Rust audio decoder used by both the production Rust-ONNX frontend
//! and the standalone (ONNX-free) native Essentia DSP parity harness.
//! This isolates the exact reference DSP behavior without duplicating it.
use crate::preprocess;

/// Cache identity for the corrected original libsamplerate SRC_LINEAR phase.
/// Historical Rust v4 sidecars must stay distinct and never be reused here.
pub(crate) const RUST_PREPROCESSING: &str = "experimental-essentia-audio-v5-f32-src-ratio-unvalidated";
use anyhow::{bail, Context, Result};
use std::{
    io::{self, Read},
    path::Path,
    process::{Command as ProcessCommand, Output, Stdio},
    sync::{atomic::{AtomicBool, Ordering}, mpsc},
    thread,
    time::Duration,
};

const PROCESS_POLL_INTERVAL: Duration = Duration::from_millis(100);
const PROBE_OUTPUT_LIMIT: usize = 1024 * 1024;
const STDERR_LIMIT: usize = 1024 * 1024;
const DECODE_OUTPUT_HARD_CAP: usize = 512 * 1024 * 1024;

/// Unlike std::process::Child, this owner always kills and reaps its direct
/// FFmpeg/ffprobe process if any early error exits the supervising function.
struct OwnedChild(std::process::Child);

impl Drop for OwnedChild {
    fn drop(&mut self) {
        let _ = self.0.kill();
        let _ = self.0.wait();
    }
}

/// Capture subprocess output on two dedicated threads so a full FFmpeg pipe
/// cannot block wait/try_wait. Bound both streams to limit peak allocations.
/// The coordinator retains ownership of Child and kills/reaps on cancellation.
fn capture_limited<R: Read + Send + 'static>(
    mut pipe: R, limit: usize, overflow: mpsc::Sender<()>,
) -> thread::JoinHandle<io::Result<Vec<u8>>> {
    thread::spawn(move || {
        let mut output = Vec::new();
        let mut chunk = [0u8; 32 * 1024];
        loop {
            let size = pipe.read(&mut chunk)?;
            if size == 0 { return Ok(output); }
            if output.len().saturating_add(size) > limit {
                let _ = overflow.send(());
                return Err(io::Error::other("FFmpeg child exceeded bounded output limit"));
            }
            output.extend_from_slice(&chunk[..size]);
        }
    })
}

fn subprocess_output_cancelable(
    command: &mut ProcessCommand, cancellation: Option<&AtomicBool>,
    stdout_limit: usize,
) -> Result<Output> {
    // Preserve the historic output() behavior for all non-autotune callers.
    let Some(token) = cancellation else { return Ok(command.output()?); };
    if token.load(Ordering::Acquire) {
        bail!("FFmpeg subprocess cancelled before launch by RAM watchdog");
    }
    command.stdout(Stdio::piped()).stderr(Stdio::piped());
    let mut child = OwnedChild(command.spawn().context("Unable to start FFmpeg subprocess")?);
    let stdout = child.0.stdout.take().context("Missing FFmpeg child stdout")?;
    let stderr = child.0.stderr.take().context("Missing FFmpeg child stderr")?;
    let (overflow_tx, overflow_rx) = mpsc::channel();
    let stdout_handle = capture_limited(stdout, stdout_limit, overflow_tx.clone());
    let stderr_handle = capture_limited(stderr, STDERR_LIMIT, overflow_tx);
    let mut cancelled = false;
    let mut limit_exceeded = false;
    let status = loop {
        if token.load(Ordering::Acquire) {
            cancelled = true;
        }
        if overflow_rx.try_recv().is_ok() {
            limit_exceeded = true;
        }
        if cancelled || limit_exceeded {
            let _ = child.0.kill();
            break child.0.wait().context("Unable to reap cancelled FFmpeg subprocess")?;
        }
        if let Some(status) = child.0.try_wait()? { break status; }
        thread::sleep(PROCESS_POLL_INTERVAL);
    };
    let output_bytes = stdout_handle.join()
        .map_err(|_| anyhow::anyhow!("FFmpeg stdout capture thread panicked"))?;
    let errors = stderr_handle.join()
        .map_err(|_| anyhow::anyhow!("FFmpeg stderr capture thread panicked"))?;
    if cancelled {
        bail!("FFmpeg subprocess cancelled by RAM watchdog");
    }
    // A fast-producing child can exit before the supervisor polls overflow.
    // Joining reader threads and inspecting the overflow channel closes that
    // race: such an invocation still reports a memory-limit failure.
    if limit_exceeded || overflow_rx.try_recv().is_ok() {
        bail!("FFmpeg subprocess exceeded bounded output limit");
    }
    Ok(Output {
        status,
        stdout: output_bytes.context("Failed reading FFmpeg stdout")?,
        stderr: errors.context("Failed reading FFmpeg stderr")?,
    })
}


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
    // Essentia streaming::Resample computes src_ratio in essentia::Real
    // (float32), then passes that *rounded* ratio to libsamplerate SRC_LINEAR.
    // Using mathematically exact input_rate/16000 here shifts the interpolation
    // phase progressively on real music (up to >1 source sample over a long
    // track). Reproduce Essentia's float32 ratio before reciprocal conversion.
    // Keep the existing output length until streaming end-of-input is compared
    // independently; the Mel patch-count invariant is already verified.
    let src_ratio = preprocess::RATE as f32 / input_rate as f32;
    let step = 1.0_f64 / f64::from(src_ratio);
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
    ffmpeg_pcm_mono_16k_cancelable(input, None, 1)
}

/// Identical audio math to the historical decoder; only when autotune passes
/// a cancellation token do ffprobe/FFmpeg acquire a bounded, supervised Child.
pub(crate) fn ffmpeg_pcm_mono_16k_cancelable(
    input: &Path, cancellation: Option<&AtomicBool>, max_concurrent_decoders: usize,
) -> Result<Vec<f32>> {
    // FFmpeg only decodes to float PCM at the *native* sample rate.
    // Probe stream metadata once to avoid FFmpeg's different default
    // channel weights and its incompatible sample-rate conversion.
    let probe = subprocess_output_cancelable(
        ProcessCommand::new("ffprobe")
            .args(["-v", "error", "-select_streams", "a:0",
                   "-show_entries", "stream=sample_rate,channels", "-of", "json"])
            .arg(input),
        cancellation, PROBE_OUTPUT_LIMIT,
    ).context("ffprobe failed; install the full FFmpeg distribution")?;
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
    // Only the experimental autotuner enforces a physical-memory-relative
    // output bound; do not alter legacy decoding or model fingerprints.
    let max_output = if cancellation.is_some() {
        let free = crate::resources::memory_diagnostics()
            .context("Autotune decoder requires effective free-RAM telemetry")?
            .available_physical_mib;
        // Divide the effective free-RAM budget across the maximum worker
        // pool, even if only a few workers are currently active. A single
        // decoded PCM allocation plus conversion/resampling can multiply
        // memory demand by several times its raw output size.
        let bytes = (free * 1024.0 * 1024.0
            / (4.0 * max_concurrent_decoders.max(1) as f64)) as usize;
        if bytes < 2 * 1024 * 1024 {
            bail!("Autotune decoder lacks 2 MiB PCM budget at {max_concurrent_decoders} configured workers");
        }
        bytes.min(DECODE_OUTPUT_HARD_CAP)
    } else { usize::MAX };
    let output = subprocess_output_cancelable(
        ProcessCommand::new("ffmpeg")
            .args(["-hide_banner", "-nostdin", "-loglevel", "error", "-i"])
            .arg(input)
            .args(["-map", "0:a:0", "-vn", "-acodec", "pcm_f32le",
                   "-f", "f32le", "pipe:1"]),
        cancellation, max_output,
    ).context("FFmpeg failed; install FFmpeg and add it to PATH")?;
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

#[cfg(test)]
mod tests {
    use super::essentia_linear_resample;

    #[cfg(unix)]
    #[test]
    fn cancel_blocked_subprocess_and_reap_child_without_waiting_for_sleep() {
        use std::sync::{Arc, atomic::{AtomicBool, Ordering}};
        let token = Arc::new(AtomicBool::new(false));
        let copy = Arc::clone(&token);
        let cancel = std::thread::spawn(move || {
            std::thread::sleep(std::time::Duration::from_millis(150));
            copy.store(true, Ordering::Release);
        });
        let started = std::time::Instant::now();
        // Direct sleep executable does not leave a grandchild holding pipes.
        let err = super::subprocess_output_cancelable(
            std::process::Command::new("sleep").arg("5"), Some(&token),
            super::PROBE_OUTPUT_LIMIT,
        ).unwrap_err();
        cancel.join().unwrap();
        assert!(format!("{err:#}").contains("cancelled"));
        assert!(started.elapsed() < std::time::Duration::from_secs(3));
    }

    #[cfg(unix)]
    #[test]
    fn subprocess_reports_output_limit_without_waiting_for_more_data() {
        use std::sync::atomic::AtomicBool;
        let token = AtomicBool::new(false);
        let err = super::subprocess_output_cancelable(
            std::process::Command::new("sh").args([
                "-c", "head -c 65536 /dev/zero",
            ]),
            Some(&token), 1024,
        ).unwrap_err();
        assert!(format!("{err:#}").contains("bounded output limit"));
    }

    #[cfg(unix)]
    #[test]
    fn cancelable_subprocess_preserves_exact_stdout_and_stderr() {
        use std::sync::atomic::AtomicBool;
        let token = AtomicBool::new(false);
        let output = super::subprocess_output_cancelable(
            std::process::Command::new("sh").args([
                "-c", "printf 'abc'; printf 'oops' >&2",
            ]),
            Some(&token), 1024,
        ).unwrap();
        assert!(output.status.success());
        assert_eq!(output.stdout, b"abc");
        assert_eq!(output.stderr, b"oops");
    }

    #[test]
    fn src_linear_matches_upstream_libsamplerate_float32_ratio_on_twelve_seconds() {
        // SRC_LINEAR 4, mono 44,100 -> 16,000 Hz; reference values were
        // generated with original libsamplerate src_simple (not from our Rust
        // implementation) using the deterministic full-length input below.
        // Exact-ratio f64 resampling fails this regression by ~0.00146.
        const RATE: usize = 44_100;
        let input: Vec<f32> = (0..RATE * 12)
            .map(|n| {
                let t = n as f64 / RATE as f64;
                (0.7 * (2.0 * std::f64::consts::PI * 300.0 * t).sin()
                    + 0.1 * (2.0 * std::f64::consts::PI * 2453.0 * t).sin()
                    + 0.1 * (2.0 * std::f64::consts::PI * 3650.0 * t).sin()) as f32
            })
            .collect();
        let output = essentia_linear_resample(&input, RATE);
        assert_eq!(output.len(), 192_000);
        // libsamplerate can return one trailing terminal frame on this exact
        // boundary; check matching frames, not its separate EOF behavior.
        let reference = [
            (1, 0.186_830_77_f32),
            (160, 0.035_811_3_f32),
            (65_535, -0.542_090_36_f32),
            (100_000, 0.113_633_87_f32),
            (160_000, -0.115_302_905_f32),
            (191_999, -0.298_430_03_f32),
        ];
        for (index, native) in reference {
            let difference = (output[index] - native).abs();
            assert!(
                difference < 2e-5,
                "SRC_LINEAR mismatch at output sample {index}:                  Rust={} native={native} delta={difference}",
                output[index],
            );
        }
    }

    #[test]
    fn unchanged_rate_is_exact_identity() {
        let samples = [0.25_f32, -0.3_f32, 0.4_f32];
        assert_eq!(essentia_linear_resample(&samples, 16_000), samples);
    }
}
