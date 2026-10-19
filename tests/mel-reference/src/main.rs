//! Parity-only executable using the *production* Rust Mel implementation.
//! Excludes ONNX and all classification code to build on older native CI hosts.
#[path = "../../../src/preprocess.rs"]
mod preprocess;

use anyhow::{bail, Context, Result};
use std::{fs, path::PathBuf};

fn parse_fixture_wav(wav: &[u8]) -> Result<Vec<f32>> {
    if wav.len() < 44 || &wav[0..4] != b"RIFF" || &wav[8..12] != b"WAVE" {
        bail!("Test reference requires RIFF/WAVE input");
    }
    let mut cursor = 12usize;
    let mut fmt_ok = false;
    let mut audio = None;
    while cursor.checked_add(8).is_some_and(|x| x <= wav.len()) {
        let chunk = &wav[cursor..cursor + 4];
        let n = u32::from_le_bytes(wav[cursor + 4..cursor + 8].try_into()?) as usize;
        cursor += 8;
        let end = cursor.checked_add(n).context("WAV chunk offset overflow")?;
        if end > wav.len() { bail!("Truncated WAV chunk"); }
        let data = &wav[cursor..end];
        if chunk == b"fmt " {
            if data.len() < 16 { bail!("Invalid WAV fmt block"); }
            let encoding = u16::from_le_bytes(data[0..2].try_into()?);
            let channels = u16::from_le_bytes(data[2..4].try_into()?);
            let rate = u32::from_le_bytes(data[4..8].try_into()?);
            let bits = u16::from_le_bytes(data[14..16].try_into()?);
            fmt_ok = encoding == 1 && channels == 1 && rate == 16000 && bits == 16;
        } else if chunk == b"data" {
            audio = Some(data.to_vec());
        }
        cursor = end.checked_add(n % 2).context("WAV chunk padding overflow")?;
    }
    if !fmt_ok { bail!("Expected uncompressed signed PCM16 mono 16 kHz WAV"); }
    let data = audio.context("WAV has no data chunk")?;
    if data.len() % 2 != 0 { bail!("Odd-length PCM16 samples"); }
    Ok(data.chunks_exact(2)
        .map(|sample| i16::from_le_bytes([sample[0], sample[1]]) as f32 / 32768.0)
        .collect())
}

fn main() -> Result<()> {
    let mut args = std::env::args_os().skip(1);
    let path = PathBuf::from(args.next().context("Usage: essentia-mel-reference WAV")?);
    if args.next().is_some() { bail!("Only one WAV path is supported"); }
    let wav = fs::read(&path).with_context(|| format!("Cannot read {}", path.display()))?;
    let samples = parse_fixture_wav(&wav)?;
    let mel = preprocess::mel_spectrogram(&samples)?;
    println!("{}", serde_json::json!({
        "total_frames": mel.len(),
        "frames": mel,
        "preprocessing_source": "src/preprocess.rs",
        "sample_rate": preprocess::RATE,
    }));
    Ok(())
}
