//! Read-only, opt-in IPC for a long-lived *native Essentia C++* DSP child.
//! The child owns all Essentia state. Rust keeps ONNX, scheduling and SQLite.
use anyhow::{bail, Context, Result};
use std::{
    fs,
    io::{Read, Write},
    path::{Path, PathBuf},
    process::{Child, ChildStdin, ChildStdout, Command, Stdio},
    sync::{atomic::{AtomicBool, Ordering}, mpsc, Arc, Mutex},
    thread,
    time::{Duration, Instant},
};
use crate::{preprocess, sha256_file};

const MAX_PATH_BYTES: usize = 16_384;
const MAX_PATCHES: usize = 2_048; // about 96 MiB in Float32 payload
const MAX_ERROR_BYTES: usize = 4_096;
const VALUES_PER_PATCH: usize = preprocess::PATCH_FRAMES * preprocess::MEL_BANDS;
pub const CPP_PREPROCESSING: &str = "experimental-essentia-cpp-dsp-v1-unvalidated";

#[derive(Clone, Debug)]
pub enum BackendChoice {
    Rust,
    Essentia { executable: PathBuf, worker_sha256: String },
}

impl BackendChoice {
    pub fn from_cli(name: &str, worker_path: Option<&Path>) -> Result<Self> {
        match (name, worker_path) {
            ("rust", None) => Ok(Self::Rust),
            ("essentia", Some(path)) => {
                if !path.is_file() {
                    bail!("Essentia worker executable not found: {}", path.display());
                }
                // This fingerprint prevents cache aliasing across different native workers.
                let executable = fs::canonicalize(path)
                    .with_context(|| format!("Invalid Essentia worker path {}", path.display()))?;
                let worker_sha256 = sha256_file(&executable)?;
                Ok(Self::Essentia { executable, worker_sha256 })
            }
            ("rust", Some(_)) => bail!("--essentia-worker requires --audio-backend essentia"),
            ("essentia", None) => bail!("--audio-backend essentia requires --essentia-worker"),
            _ => bail!("--audio-backend must be rust or essentia"),
        }
    }

    pub fn preprocessing(&self) -> &'static str {
        match self {
            Self::Rust => "experimental-essentia-audio-v4-unvalidated",
            Self::Essentia { .. } => CPP_PREPROCESSING,
        }
    }
    pub fn worker_hash(&self) -> Option<&str> {
        match self { Self::Rust => None, Self::Essentia { worker_sha256, .. } => Some(worker_sha256) }
    }
}

pub struct NativePatches {
    pub patches: Vec<Vec<f32>>,
    pub decode_seconds: f64,
    pub features_seconds: f64,
}

enum WatchdogCommand {
    Arm(Duration),
    Disarm,
    Stop,
}

struct ChildIo {
    child: Arc<Mutex<Child>>,
    input: ChildStdin,
    output: ChildStdout,
    watch_tx: mpsc::Sender<WatchdogCommand>,
    watcher: Option<thread::JoinHandle<()>>,
    timed_out: Arc<AtomicBool>,
}

impl ChildIo {
    fn new(child: Child, input: ChildStdin, output: ChildStdout) -> Self {
        let child = Arc::new(Mutex::new(child));
        let timed_out = Arc::new(AtomicBool::new(false));
        let (watch_tx, rx) = mpsc::channel();
        let watch_child = Arc::clone(&child);
        let watch_timeout = Arc::clone(&timed_out);
        let watcher = thread::spawn(move || {
            let mut deadline: Option<Instant> = None;
            loop {
                let command = if let Some(expiry) = deadline {
                    match rx.recv_timeout(expiry.saturating_duration_since(Instant::now())) {
                        Ok(command) => command,
                        Err(mpsc::RecvTimeoutError::Timeout) => {
                            watch_timeout.store(true, Ordering::SeqCst);
                            if let Ok(mut child) = watch_child.lock() {
                                let _ = child.kill();
                            }
                            deadline = None;
                            continue;
                        }
                        Err(mpsc::RecvTimeoutError::Disconnected) => break,
                    }
                } else {
                    match rx.recv() {
                        Ok(command) => command,
                        Err(_) => break,
                    }
                };
                match command {
                    WatchdogCommand::Arm(duration) => {
                        watch_timeout.store(false, Ordering::SeqCst);
                        deadline = Some(Instant::now() + duration);
                    }
                    WatchdogCommand::Disarm => deadline = None,
                    WatchdogCommand::Stop => break,
                }
            }
        });
        Self { child, input, output, watch_tx, watcher: Some(watcher), timed_out }
    }

    fn arm(&self, duration: Duration) -> Result<()> {
        self.watch_tx.send(WatchdogCommand::Arm(duration))
            .context("Native worker watchdog exited")
    }
    fn disarm(&self) {
        let _ = self.watch_tx.send(WatchdogCommand::Disarm);
    }
    fn timeout_failure(&self) -> bool {
        self.timed_out.load(Ordering::SeqCst)
    }
    #[cfg(test)]
    fn pid(&self) -> u32 {
        self.child.lock().unwrap().id()
    }
}

impl Drop for ChildIo {
    fn drop(&mut self) {
        // A blocked reader is unblocked by the watchdog killing the child.
        // This also prevents orphan processes when the parent worker exits.
        let _ = self.watch_tx.send(WatchdogCommand::Stop);
        if let Ok(mut child) = self.child.lock() {
            let _ = child.kill();
        }
        if let Some(watcher) = self.watcher.take() {
            let _ = watcher.join();
        }
        if let Ok(mut child) = self.child.lock() {
            let _ = child.wait();
        }
    }
}

/// One Rust worker thread owns this object. Each C++ child processes tracks
/// serially; the original Essentia library is never called concurrently
/// from unguarded Rust threads in the same process.
pub struct EssentiaWorker {
    executable: PathBuf,
    child: Option<ChildIo>,
    timeout: Duration,
}

impl EssentiaWorker {
    pub fn new(executable: PathBuf) -> Self {
        // Hard default timeout includes NAS I/O, decoding, DSP and IPC
        // transfer. Do not accidentally limit ordinary long music tracks.
        Self { executable, child: None, timeout: Duration::from_secs(600) }
    }

    fn start(&mut self) -> Result<()> {
        if self.child.is_some() { return Ok(()); }
        let mut child = Command::new(&self.executable)
            .stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::inherit())
            .spawn().with_context(|| format!(
                "Failed to launch native Essentia worker {}", self.executable.display()
            ))?;
        let input = child.stdin.take().context("Native worker stdin missing")?;
        let output = child.stdout.take().context("Native worker stdout missing")?;
        let mut io = ChildIo::new(child, input, output);
        io.arm(Duration::from_secs(30))?;
        let mut hello = [0u8; 4];
        let result = io.output.read_exact(&mut hello);
        io.disarm();
        if let Err(err) = result {
            if io.timeout_failure() {
                bail!("Native Essentia worker startup exceeded 30-second deadline");
            }
            return Err(err).context("Native Essentia worker handshake failed");
        }
        if &hello != b"EFW1" {
            bail!("Native Essentia worker protocol mismatch: expected EFW1");
        }
        self.child = Some(io);
        Ok(())
    }

    pub fn analyze(&mut self, path: &Path, max_patches: Option<usize>) -> Result<NativePatches> {
        let path = path.to_str().context("Essentia worker needs a UTF-8 source path")?;
        if path.is_empty() || path.contains('\0') || path.len() > MAX_PATH_BYTES {
            bail!("Native worker source path invalid or too long");
        }
        let cap = max_patches.unwrap_or(0);
        if cap > MAX_PATCHES || max_patches == Some(0) {
            bail!("Essentia patch limit must be between 1 and {MAX_PATCHES}, or omitted");
        }
        self.start()?;
        let io = self.child.as_mut().context("Missing Essentia worker")?;
        io.arm(self.timeout)?;
        let result = (|| {
            io.input.write_all(b"REQ1")?;
            io.input.write_all(&(path.len() as u32).to_le_bytes())?;
            io.input.write_all(&(cap as u32).to_le_bytes())?;
            io.input.write_all(path.as_bytes())?;
            io.input.flush()?;
            read_response(&mut io.output, max_patches)
        })();
        io.disarm();
        let result = if io.timeout_failure() {
            Err(anyhow::anyhow!("Native Essentia worker exceeded {}-second job deadline",
                self.timeout.as_secs_f64()))
        } else { result };
        // Broken IPC or native DSP error invalidates this process, never
        // silently fallback to the Rust frontend / another fingerprint.
        if result.is_err() { self.child = None; }
        result
    }
}

fn u32le(input: &mut impl Read) -> Result<u32> {
    let mut buf = [0u8; 4];
    input.read_exact(&mut buf).context("Truncated native worker response")?;
    Ok(u32::from_le_bytes(buf))
}
fn u64le(input: &mut impl Read) -> Result<u64> {
    let mut buf = [0u8; 8];
    input.read_exact(&mut buf).context("Truncated native worker timing")?;
    Ok(u64::from_le_bytes(buf))
}

fn read_response(input: &mut impl Read, requested_cap: Option<usize>) -> Result<NativePatches> {
    let mut header = [0u8; 5];
    input.read_exact(&mut header).context("Truncated Essentia response header")?;
    if &header[..4] != b"RES1" { bail!("Native worker returned invalid response magic"); }
    let count = u32le(input)? as usize;
    let decode_seconds = u64le(input)? as f64 / 1e9;
    let features_seconds = u64le(input)? as f64 / 1e9;
    match header[4] {
        1 => {
            if count > MAX_ERROR_BYTES { bail!("Native worker error message exceeds protocol limit"); }
            let mut error = vec![0u8; count];
            input.read_exact(&mut error).context("Truncated native worker error")?;
            let message = String::from_utf8(error).context("Invalid worker error UTF-8")?;
            bail!("Essentia C++ frontend error: {message}");
        }
        0 => {
            if count == 0 || count > MAX_PATCHES || requested_cap.is_some_and(|c| count > c) {
                bail!("Essentia worker patch count out of bounds");
            }
            let mut patches = Vec::with_capacity(count);
            for _ in 0..count {
                let mut bytes = vec![0u8; VALUES_PER_PATCH * 4];
                input.read_exact(&mut bytes).context("Truncated native worker patch")?;
                let mut patch = Vec::with_capacity(VALUES_PER_PATCH);
                for chunk in bytes.as_chunks::<4>().0 {
                    let v = f32::from_le_bytes(*chunk);
                    if !v.is_finite() || v < 0.0 {
                        bail!("Native worker returned invalid Mel coefficient");
                    }
                    patch.push(v);
                }
                patches.push(patch);
            }
            Ok(NativePatches { patches, decode_seconds, features_seconds })
        }
        _ => bail!("Native worker response status invalid"),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Cursor;

    fn response(status: u8, count: u32, body: &[u8]) -> Vec<u8> {
        let mut v = b"RES1".to_vec();
        v.push(status);
        v.extend_from_slice(&count.to_le_bytes());
        v.extend_from_slice(&9u64.to_le_bytes());
        v.extend_from_slice(&27u64.to_le_bytes());
        v.extend_from_slice(body);
        v
    }

    #[test]
    fn rejects_corrupt_and_oversized_protocol() {
        assert!(read_response(&mut Cursor::new(b"GARBAGE"), None).is_err());
        assert!(read_response(&mut Cursor::new(response(0, 2049, &[])), None).is_err());
        assert!(read_response(&mut Cursor::new(response(0, 2, &[])), Some(1)).is_err());
        assert!(read_response(&mut Cursor::new(response(0, 1, &[])), None).is_err());
        assert!(read_response(&mut Cursor::new(response(3, 0, &[])), None).is_err());
        assert!(read_response(&mut Cursor::new(response(1, 4097, &[])), None).is_err());
    }

    #[test]
    fn parses_bounded_error_without_confusing_it_with_success() {
        let data = response(1, 4, b"oops");
        let err = read_response(&mut Cursor::new(data), None).err().unwrap();
        assert!(format!("{err:#}").contains("oops"));
    }

    #[test]
    fn validates_exact_float_payload_and_stage_timing() {
        let patch = vec![0.5_f32; VALUES_PER_PATCH];
        let body: Vec<u8> = patch.iter().flat_map(|v| v.to_le_bytes()).collect();
        let p = read_response(&mut Cursor::new(response(0, 1, &body)), Some(1)).unwrap();
        assert_eq!(p.patches.len(), 1);
        assert_eq!(p.patches[0].len(), VALUES_PER_PATCH);
        assert_eq!(p.patches[0][0], 0.5);
        assert!((p.decode_seconds - 9e-9).abs() < 1e-12);
        let mut bad = body.clone();
        bad[0..4].copy_from_slice(&f32::NAN.to_le_bytes());
        assert!(read_response(&mut Cursor::new(response(0, 1, &bad)), None).is_err());
    }

    #[test]
    fn child_protocol_reuses_and_restarts_real_process() {
        let Some(exe) = std::env::var_os("ESSENTIA_IPC_FIXTURE_EXE") else {
            // Native fixture is built in the Rust CI job; local builds do
            // not require any native C++ toolchain or Essentia install.
            return;
        };
        let mut worker = EssentiaWorker::new(PathBuf::from(exe));
        let first = worker.analyze(Path::new("good-one.wav"), None).unwrap();
        assert_eq!(first.patches.len(), 1);
        assert_eq!(first.patches[0][0], 0.25);
        assert!((first.decode_seconds - 0.001).abs() < 1e-6);
        let first_pid = worker.child.as_ref().unwrap().pid();
        let second = worker.analyze(Path::new("good-two.flac"), Some(1)).unwrap();
        assert_eq!(second.patches[0][0], 0.25);
        assert_eq!(worker.child.as_ref().unwrap().child.id(), first_pid,
                   "C++ worker must be reused across consecutive songs");
        assert!(worker.analyze(Path::new("fail.flac"), None).is_err());
        assert!(worker.child.is_none(), "native errors retire the process");
        let after = worker.analyze(Path::new("good-after-error.flac"), None).unwrap();
        assert_eq!(after.patches.len(), 1);
        assert!(worker.analyze(Path::new("crash.flac"), None).is_err());
        assert!(worker.child.is_none(), "native crashes must not poison future jobs");
        assert_eq!(worker.analyze(Path::new("good-restarted.flac"), None)
            .unwrap().patches.len(), 1);
        worker.timeout = Duration::from_millis(250);
        let started = Instant::now();
        let timeout = worker.analyze(Path::new("hang.flac"), None).err().unwrap();
        assert!(format!("{timeout:#}").contains("deadline"));
        assert!(started.elapsed() < Duration::from_secs(3));
        assert!(worker.child.is_none());
        assert_eq!(worker.analyze(Path::new("good-after-timeout.flac"), None)
            .unwrap().patches.len(), 1);
    }

    #[test]
    fn backend_selection_is_explicit() {
        assert!(matches!(BackendChoice::from_cli("rust", None), Ok(BackendChoice::Rust)));
        assert!(BackendChoice::from_cli("unknown", None).is_err());
        assert!(BackendChoice::from_cli("essentia", None).is_err());
        assert!(BackendChoice::from_cli("rust", Some(Path::new("worker"))).is_err());
    }
}
