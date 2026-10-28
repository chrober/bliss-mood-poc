//! Phase C vertical slice: a bounded, versioned IPC protocol to a supervised
//! instance of this executable. Its hidden child already supports the real
//! ONNX FeatureEngine; scan-features is not migrated until real-audio parity.
#![allow(dead_code)] // Supervised client is staged until the actual ONNX migration.
use anyhow::{bail, Context, Result};
use serde::{Deserialize, Serialize};
use std::{
    collections::BTreeMap,
    io::{Read, Write},
    path::{Path, PathBuf},
    process::{Child, ChildStdin, ChildStdout, Command, Stdio},
    sync::{
        atomic::{AtomicBool, Ordering},
        mpsc, Arc,
    },
    thread,
    time::{Duration, Instant},
};

#[cfg(unix)]
use std::os::unix::process::CommandExt;

// The child starts its *own* process group, allowing a RAM emergency to
// terminate its original Essentia/FFmpeg descendants without bare-PID killing.
// This narrow Unix FFI avoids adding an unrelated native runtime dependency.
#[cfg(unix)]
unsafe extern "C" {
    #[link_name = "kill"]
    fn signal_process_group(process_group: i32, signal: i32) -> i32;
}

// Windows 8+ supports nested Job Objects. The worker is assigned before
// any IPC is dispatched, so it cannot launch Essentia/FFmpeg descendants
// outside the Job between creation and assignment. Fail closed on any error.
#[cfg(windows)]
mod windows_job {
    use anyhow::{Context, Result};
    use std::{ffi::c_void, io, mem, os::windows::io::AsRawHandle, process::Child, ptr};
    type Handle = *mut c_void;
    const EXTENDED_LIMIT_INFO: i32 = 9;
    const KILL_ON_JOB_CLOSE: u32 = 0x2000;

    #[repr(C)]
    struct BasicLimits {
        per_process_user_time: i64,
        per_job_user_time: i64,
        limit_flags: u32,
        minimum_working_set: usize,
        maximum_working_set: usize,
        active_process_limit: u32,
        affinity: usize,
        priority_class: u32,
        scheduling_class: u32,
    }
    #[repr(C)]
    struct IoCounters {
        read_ops: u64, write_ops: u64, other_ops: u64,
        read_bytes: u64, write_bytes: u64, other_bytes: u64,
    }
    #[repr(C)]
    struct ExtendedLimits {
        basic: BasicLimits,
        io: IoCounters,
        process_memory_limit: usize,
        job_memory_limit: usize,
        peak_process_memory: usize,
        peak_job_memory: usize,
    }
    #[link(name = "kernel32")]
    unsafe extern "system" {
        fn CreateJobObjectW(attributes: *const c_void, name: *const u16) -> Handle;
        fn SetInformationJobObject(job: Handle, class: i32, data: *const c_void, len: u32) -> i32;
        fn AssignProcessToJobObject(job: Handle, process: Handle) -> i32;
        fn CloseHandle(handle: Handle) -> i32;
    }

    pub(super) struct OwnedJob(Handle);
    impl OwnedJob {
        pub(super) fn attach(child: &Child) -> Result<Self> {
            // SAFETY: no attributes or name; the returned handle is owned here.
            let handle = unsafe { CreateJobObjectW(ptr::null(), ptr::null()) };
            if handle.is_null() {
                return Err(io::Error::last_os_error()).context("CreateJobObjectW failed");
            }
            let job = Self(handle);
            // SAFETY: zeroed repr(C) POD has valid representation.
            let mut limits: ExtendedLimits = unsafe { mem::zeroed() };
            limits.basic.limit_flags = KILL_ON_JOB_CLOSE;
            // SAFETY: valid owned Job handle and pointer to a live C ABI struct.
            let configured = unsafe {
                SetInformationJobObject(job.0, EXTENDED_LIMIT_INFO,
                    (&raw const limits).cast(), mem::size_of::<ExtendedLimits>() as u32)
            };
            if configured == 0 {
                return Err(io::Error::last_os_error())
                    .context("Windows Job Object KILL_ON_JOB_CLOSE setup failed");
            }
            // SAFETY: Child owns a live process handle with assignment rights.
            // No IPC request is sent before this function returns successfully.
            let assigned = unsafe {
                AssignProcessToJobObject(job.0, child.as_raw_handle().cast())
            };
            if assigned == 0 {
                return Err(io::Error::last_os_error())
                    .context("AssignProcessToJobObject failed");
            }
            Ok(job)
        }
    }
    impl Drop for OwnedJob {
        fn drop(&mut self) {
            // SAFETY: close exactly the unique handle created above.
            unsafe { CloseHandle(self.0); }
        }
    }

    #[cfg(test)]
    mod tests {
        use super::*;
        use std::{io::BufRead, io::BufReader, process::{Command, Stdio}};
        #[link(name = "kernel32")]
        unsafe extern "system" {
            fn OpenProcess(access: u32, inherit: i32, pid: u32) -> Handle;
            fn IsProcessInJob(process: Handle, job: Handle, in_job: *mut i32) -> i32;
            fn WaitForSingleObject(handle: Handle, timeout_ms: u32) -> u32;
        }
        #[test]
        fn kill_on_close_terminates_actual_windows_grandchild() {
            // Powershell is available on windows-2022. Entirely synthetic
            // 20-second sleepers, no music, models or private artifacts.
            let script = "$p=Start-Process -FilePath powershell.exe -ArgumentList @('-NoProfile','-NonInteractive','-Command','Start-Sleep -Seconds 20') -PassThru -WindowStyle Hidden; [Console]::WriteLine($p.Id); Start-Sleep -Seconds 20";
            let mut cmd = Command::new("powershell.exe");
            cmd.args(["-NoProfile", "-NonInteractive", "-Command", script])
                .stdin(Stdio::null()).stdout(Stdio::piped()).stderr(Stdio::inherit());
            let mut root = super::super::OwnedChild::attach(
                cmd.spawn().expect("spawn root")
            ).expect("root must be in a kill-on-close Job");
            let mut line = String::new();
            BufReader::new(root.child.stdout.take().unwrap())
                .read_line(&mut line).expect("read descendant PID");
            let pid: u32 = line.trim().parse().expect("descendant PID");
            const SYNCHRONIZE: u32 = 0x0010_0000;
            const QUERY_LIMITED: u32 = 0x1000;
            // SAFETY: pid was just returned by Start-Process; handle is retained.
            let descendant = unsafe { OpenProcess(SYNCHRONIZE | QUERY_LIMITED, 0, pid) };
            assert!(!descendant.is_null(), "cannot inspect descendant");
            let mut in_job = 0;
            // SAFETY: handles are valid; in_job points to a writable BOOL.
            let result = unsafe {
                IsProcessInJob(descendant, root.job.as_ref().unwrap().0, &mut in_job)
            };
            assert_ne!(result, 0, "IsProcessInJob failed");
            assert_ne!(in_job, 0, "grandchild escaped its Job");
            drop(root); // must kill root AND grandchild.
            // SAFETY: OpenProcess kept the descendant object live for waiting.
            let waited = unsafe { WaitForSingleObject(descendant, 5000) };
            unsafe { CloseHandle(descendant); }
            assert_eq!(waited, 0, "grandchild survived Job close");
        }
    }
}

const PROTOCOL_VERSION: u16 = 1;
const MAX_FRAME_BYTES: usize = 64 * 1024;
const MAX_TEST_DELAY_MS: u64 = 10_000;
const HELLO: &[u8; 4] = b"FWP1";
const REQUEST: &[u8; 4] = b"REQ1";
const RESPONSE: &[u8; 4] = b"RES1";
const POLL: Duration = Duration::from_millis(100);

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(tag = "op", rename_all = "snake_case")]
pub enum WorkerOperation {
    Ping { nonce: u64 },
    Shutdown,
    /// Bounded synthetic delay to test timeout and hard process cancellation.
    TestDelay { millis: u64 },
    /// Initialize once per persistent worker. Model fingerprinting and
    /// semantics are validated by the existing FeatureEngine loader.
    Initialize {
        models_dir: PathBuf,
        registry: Option<PathBuf>,
        models: String,
        audio_backend: String,
        essentia_worker: Option<PathBuf>,
        essentia_timeout_seconds: u64,
        threads: usize,
        export_embedding: bool,
    },
    /// Only accepted after successful initialization; no SQLite writes.
    AnalyzeSong { source: PathBuf, max_patches: Option<usize> },
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct WorkerRequest {
    pub version: u16,
    pub request_id: u64,
    pub operation: WorkerOperation,
}

impl WorkerRequest {
    pub fn ping(request_id: u64, nonce: u64) -> Self {
        Self { version: PROTOCOL_VERSION, request_id, operation: WorkerOperation::Ping { nonce } }
    }
    pub fn test_delay(request_id: u64, millis: u64) -> Self {
        Self { version: PROTOCOL_VERSION, request_id, operation: WorkerOperation::TestDelay { millis } }
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum WorkerReply {
    Pong { nonce: u64 },
    Stopping,
    DelayComplete,
    Initialized {
        models: Vec<String>,
        /// Cache/model fingerprints computed from exact selected model files.
        model_keys: BTreeMap<String, String>,
    },
    Analyzed {
        report: serde_json::Value,
        embedding: Option<serde_json::Value>,
    },
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct WorkerResponse {
    pub version: u16,
    pub request_id: u64,
    pub reply: WorkerReply,
}

fn write_frame(writer: &mut impl Write, magic: &[u8; 4], payload: &[u8]) -> Result<()> {
    if payload.is_empty() || payload.len() > MAX_FRAME_BYTES {
        bail!("Feature-worker IPC frame outside 1..={MAX_FRAME_BYTES} bytes");
    }
    writer.write_all(magic)?;
    writer.write_all(&(payload.len() as u32).to_le_bytes())?;
    writer.write_all(payload)?;
    writer.flush()?;
    Ok(())
}

fn read_frame(reader: &mut impl Read, magic: &[u8; 4]) -> Result<Option<Vec<u8>>> {
    let mut header = [0u8; 8];
    if reader.read(&mut header[..1])? == 0 {
        return Ok(None);
    }
    reader.read_exact(&mut header[1..])?;
    if &header[..4] != magic {
        bail!("Feature-worker IPC invalid frame magic");
    }
    let length = u32::from_le_bytes(header[4..8].try_into()?) as usize;
    if length == 0 || length > MAX_FRAME_BYTES {
        bail!("Feature-worker IPC invalid frame length: {length}");
    }
    let mut payload = vec![0u8; length];
    reader.read_exact(&mut payload)?;
    Ok(Some(payload))
}

fn require_valid_request(request: &WorkerRequest) -> Result<()> {
    if request.version != PROTOCOL_VERSION || request.request_id == 0 {
        bail!("Unsupported feature-worker protocol version or zero request ID");
    }
    Ok(())
}

/// Hidden stdin/stdout worker mode; never writes media, models, or SQLite.
/// The callback owns any FeatureEngine session state: this framing module
/// stays testable without loading the heavy ONNX runtime.
pub fn serve_stdio(
    mut analyze: impl FnMut(&WorkerOperation) -> Result<WorkerReply>,
) -> Result<()> {
    let input = std::io::stdin();
    let output = std::io::stdout();
    let mut reader = input.lock();
    let mut writer = output.lock();
    writer.write_all(HELLO)?;
    writer.flush()?;
    let mut last_request_id = 0_u64;
    while let Some(payload) = read_frame(&mut reader, REQUEST)? {
        let request: WorkerRequest = serde_json::from_slice(&payload)
            .context("Malformed feature-worker request")?;
        require_valid_request(&request)?;
        if request.request_id <= last_request_id {
            bail!("Feature-worker request IDs must increase monotonically");
        }
        last_request_id = request.request_id;
        let (reply, stop) = match request.operation {
            WorkerOperation::Ping { nonce } => (WorkerReply::Pong { nonce }, false),
            WorkerOperation::Shutdown => (WorkerReply::Stopping, true),
            WorkerOperation::TestDelay { millis } => {
                if millis > MAX_TEST_DELAY_MS {
                    bail!("Feature-worker synthetic delay exceeds test bound");
                }
                thread::sleep(Duration::from_millis(millis));
                (WorkerReply::DelayComplete, false)
            }
            operation @ WorkerOperation::Initialize { .. }
            | operation @ WorkerOperation::AnalyzeSong { .. } =>
                (analyze(&operation)?, false),
        };
        let response = WorkerResponse {
            version: PROTOCOL_VERSION, request_id: request.request_id, reply,
        };
        write_frame(&mut writer, RESPONSE, &serde_json::to_vec(&response)?)?;
        if stop { break; }
    }
    Ok(())
}

struct OwnedChild {
    child: Child,
    #[cfg(windows)]
    job: Option<windows_job::OwnedJob>,
}

impl OwnedChild {
    fn attach(child: Child) -> Result<Self> {
        #[cfg(windows)]
        {
            let mut child = child;
            let job = match windows_job::OwnedJob::attach(&child) {
                Ok(job) => job,
                Err(error) => {
                    // Never dispatch an ONNX request without containment.
                    let _ = child.kill();
                    let _ = child.wait();
                    return Err(error);
                }
            };
            Ok(Self { child, job: Some(job) })
        }
        #[cfg(not(windows))]
        {
            Ok(Self { child })
        }
    }
}

impl Drop for OwnedChild {
    fn drop(&mut self) {
        #[cfg(windows)]
        {
            // Close Job first to kill descendants before reaping the leader.
            drop(self.job.take());
        }
        #[cfg(unix)]
        {
            // Signal the owned process group before reaping the leader.
            if let Ok(group) = i32::try_from(self.child.id()) {
                if group > 0 {
                    // SAFETY: negative PGID is for the still-owned child group.
                    unsafe { signal_process_group(-group, 9); }
                }
            }
        }
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

/// Not wired into the real scanner yet. This owner has a bounded deadline,
/// cancellation checks, and always reaps the *direct* owned child on errors.
pub struct FeatureWorkerProcess {
    child: Option<OwnedChild>,
    stdin: Option<ChildStdin>,
    stdout: Option<ChildStdout>,
    handshake_pending: bool,
    timeout: Duration,
    cancellation: Arc<AtomicBool>,
}

impl FeatureWorkerProcess {
    pub fn spawn(executable: &Path, timeout: Duration, cancellation: Arc<AtomicBool>) -> Result<Self> {
        if timeout.is_zero() || timeout > Duration::from_secs(7200) {
            bail!("Feature-worker timeout outside 1ms..=7200s");
        }
        if cancellation.load(Ordering::Acquire) {
            bail!("Feature-worker scan cancelled before startup");
        }
        let mut command = Command::new(executable);
        command.arg("internal-feature-worker")
            .stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::inherit());
        #[cfg(unix)]
        command.process_group(0);
        let mut child = OwnedChild::attach(command.spawn()
            .with_context(|| format!("Cannot start feature worker {}", executable.display()))?)
            .context("Cannot confine feature-worker child")?;
        let stdin = child.child.stdin.take().context("Feature-worker stdin unavailable")?;
        let stdout = child.child.stdout.take().context("Feature-worker stdout unavailable")?;
        Ok(Self {
            child: Some(child), stdin: Some(stdin), stdout: Some(stdout),
            handshake_pending: true, timeout, cancellation,
        })
    }

    pub fn request(&mut self, request: WorkerRequest) -> Result<WorkerResponse> {
        require_valid_request(&request)?;
        if self.cancellation.load(Ordering::Acquire) {
            // A scan-level memory alarm must release an idle worker's ONNX
            // allocations too, not merely reject the next request.
            drop(self.child.take());
            self.stdin.take();
            self.stdout.take();
            bail!("Feature-worker request cancelled before dispatch");
        }
        let child = self.child.take().context("Feature worker not running")?;
        let mut stdin = self.stdin.take().context("Feature-worker stdin missing")?;
        let mut stdout = self.stdout.take().context("Feature-worker stdout missing")?;
        let first = self.handshake_pending;
        let expected_id = request.request_id;
        let bytes = serde_json::to_vec(&request)?;
        let (tx, rx) = mpsc::sync_channel(1);
        let transport = thread::spawn(move || {
            let result = (|| -> Result<(WorkerResponse, ChildStdin, ChildStdout)> {
                if first {
                    let mut hello = [0u8; 4];
                    stdout.read_exact(&mut hello)?;
                    if &hello != HELLO { bail!("Unexpected feature-worker handshake"); }
                }
                write_frame(&mut stdin, REQUEST, &bytes)?;
                let frame = read_frame(&mut stdout, RESPONSE)?
                    .context("Feature worker exited before replying")?;
                let reply: WorkerResponse = serde_json::from_slice(&frame)?;
                if reply.version != PROTOCOL_VERSION || reply.request_id != expected_id {
                    bail!("Feature-worker response version or request ID mismatch");
                }
                Ok((reply, stdin, stdout))
            })();
            let _ = tx.send(result);
        });
        let started = Instant::now();
        let outcome = loop {
            if self.cancellation.load(Ordering::Acquire) {
                break Err(anyhow::anyhow!("Feature worker cancelled by scan RAM watchdog"));
            }
            let remain = self.timeout.saturating_sub(started.elapsed());
            if remain.is_zero() {
                break Err(anyhow::anyhow!("Feature-worker IPC hard timeout"));
            }
            match rx.recv_timeout(POLL.min(remain)) {
                Ok(result) => break result,
                Err(mpsc::RecvTimeoutError::Timeout) => continue,
                Err(mpsc::RecvTimeoutError::Disconnected) =>
                    break Err(anyhow::anyhow!("Feature-worker IPC transport disconnected")),
            }
        };
        // Do not accept a successful response after a concurrent RAM alarm.
        let outcome = if self.cancellation.load(Ordering::Acquire) {
            Err(anyhow::anyhow!("Feature-worker request cancelled by RAM watchdog"))
        } else { outcome };
        // A failed request must not leave a live worker in the background.
        if outcome.is_err() {
            drop(child);
            let _ = transport.join();
            return outcome.map(|(reply, _, _)| reply);
        }
        let _ = transport.join();
        let (response, new_stdin, new_stdout) = outcome?;
        if response.reply == WorkerReply::Stopping {
            drop(child);
        } else {
            self.child = Some(child);
            self.stdin = Some(new_stdin);
            self.stdout = Some(new_stdout);
            self.handshake_pending = false;
        }
        Ok(response)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn rejects_invalid_protocol_and_oversized_frames_without_allocating_payload() {
        let mut malformed = Vec::new();
        malformed.extend_from_slice(REQUEST);
        malformed.extend_from_slice(&(MAX_FRAME_BYTES as u32 + 1).to_le_bytes());
        assert!(read_frame(&mut malformed.as_slice(), REQUEST).is_err());
        let mut wrong = Vec::new();
        write_frame(&mut wrong, RESPONSE, b"x").unwrap();
        assert!(read_frame(&mut wrong.as_slice(), REQUEST).is_err());
        assert!(write_frame(&mut Vec::new(), REQUEST, &vec![0; MAX_FRAME_BYTES + 1]).is_err());
        assert!(read_frame(&mut (&b""[..]), REQUEST).unwrap().is_none());
    }

    #[test]
    fn versioned_analyzed_reply_preserves_1280d_f32_bits_and_multiple_heads() {
        let embedding: Vec<f32> = (0..1280).map(|i| {
            ((i as f64 * 0.073).sin() * 0.17) as f32
        }).collect();
        let response = WorkerResponse {
            version: PROTOCOL_VERSION,
            request_id: 8,
            reply: WorkerReply::Analyzed {
                report: serde_json::json!({
                    "schema_version": 3,
                    "patches_analyzed": 837,
                    "classifications": {
                        "moodtheme": {"scores": {"happy": 0.125_f32}},
                        "genre": {"scores": {"rock": 0.875_f32}},
                        "voice": {"scores": {"instrumental": 0.625_f32}}
                    }
                }),
                embedding: Some(serde_json::json!({
                    "dimension": 1280,
                    "vector_f32": embedding,
                })),
            },
        };
        let mut stream = Vec::new();
        write_frame(&mut stream, RESPONSE, &serde_json::to_vec(&response).unwrap()).unwrap();
        let payload = read_frame(&mut stream.as_slice(), RESPONSE).unwrap().unwrap();
        let restored: WorkerResponse = serde_json::from_slice(&payload).unwrap();
        assert_eq!(restored.request_id, 8);
        match restored.reply {
            WorkerReply::Analyzed { report, embedding: Some(vector) } => {
                assert_eq!(report["patches_analyzed"], 837);
                assert_eq!(report["classifications"].as_object().unwrap().len(), 3);
                let decoded: Vec<f32> =
                    serde_json::from_value(vector["vector_f32"].clone()).unwrap();
                assert_eq!(decoded.len(), 1280);
                for (index, element) in decoded.into_iter().enumerate() {
                    let expected = ((index as f64 * 0.073).sin() * 0.17) as f32;
                    assert_eq!(element.to_bits(), expected.to_bits());
                }
            }
            _ => panic!("Lost embedding payload over framed IPC"),
        }
    }

    #[cfg(target_os = "linux")]
    #[test]
    fn owned_unix_process_group_reaps_actual_grandchild() {
        use std::{io::{BufRead, BufReader}, os::unix::process::CommandExt};
        // This shell launches one background descendant in its own dedicated
        // process group (not the runner's group). No private files are opened.
        let mut command = Command::new("sh");
        command.args(["-c", "sleep 30 & echo $!; wait"])
            .stdin(Stdio::null()).stdout(Stdio::piped()).stderr(Stdio::null());
        command.process_group(0);
        let mut root = OwnedChild::attach(command.spawn().expect("spawn shell"))
            .expect("own process group");
        let mut line = String::new();
        BufReader::new(root.child.stdout.take().unwrap())
            .read_line(&mut line).expect("read sleep PID");
        let grandchild: u32 = line.trim().parse().expect("valid child PID");
        let proc_stat = format!("/proc/{grandchild}/stat");
        let running = || {
            std::fs::read_to_string(&proc_stat)
                .ok()
                .and_then(|stat| stat.rsplit_once(") ")
                    .and_then(|(_, tail)| tail.chars().next()))
                .is_some_and(|state| !matches!(state, 'Z' | 'X'))
        };
        assert!(running(), "sleep descendant must be alive before teardown");
        drop(root);
        // The orphan may temporarily remain a zombie under PID 1; treating
        // zombie as terminated avoids assuming the runner promptly reaps it.
        let deadline = Instant::now() + Duration::from_secs(5);
        while running() && Instant::now() < deadline {
            thread::sleep(Duration::from_millis(20));
        }
        assert!(!running(), "process-group descendant survived owner teardown");
    }

    #[cfg(unix)]
    #[test]
    fn owned_unix_group_closes_descendant_pipes_on_teardown() {
        use std::{io::{BufRead, BufReader, Read}, os::unix::process::CommandExt};

        // Non-interactive sh inherits stdout into a background sleep process.
        // The parent shell waits for sleep. Killing just the shell cannot
        // close the pipe: EOF requires that its descendant also exits.
        // No /proc dependency, so this exercises both Linux and macOS.
        let mut command = Command::new("sh");
        command.args(["-c", "sleep 30 & echo $!; wait"])
            .stdin(Stdio::null()).stdout(Stdio::piped()).stderr(Stdio::null());
        command.process_group(0);
        let mut child = OwnedChild::attach(command.spawn().expect("spawn shell"))
            .expect("own Unix process group");
        let mut reader = BufReader::new(child.child.stdout.take().unwrap());
        let mut pid_line = String::new();
        reader.read_line(&mut pid_line).expect("shell must report descendant PID");
        let descendant_pid: u32 = pid_line.trim().parse().expect("valid descendant PID");
        assert!(descendant_pid > 0);

        let (tx, rx) = mpsc::sync_channel(1);
        let transport = thread::spawn(move || {
            let mut rest = Vec::new();
            let _ = tx.send(reader.read_to_end(&mut rest));
        });
        // The background process is still alive, so an EOF already here
        // would make the subsequent teardown assertion meaningless.
        assert!(matches!(
            rx.recv_timeout(Duration::from_millis(150)),
            Err(mpsc::RecvTimeoutError::Timeout)
        ), "descendant pipe unexpectedly closed before teardown");

        drop(child); // SIGKILL entire owned Unix group; reap its shell.
        let result = rx.recv_timeout(Duration::from_secs(5))
            .expect("descendant retained stdout after process-group termination");
        result.expect("failed draining descendant pipe");
        transport.join().expect("pipe reader thread panicked");
    }

    #[test]
    fn bounded_protocol_roundtrip_and_version_checks() {
        let request = WorkerRequest::ping(42, 7);
        let mut bytes = Vec::new();
        write_frame(&mut bytes, REQUEST, &serde_json::to_vec(&request).unwrap()).unwrap();
        let value: WorkerRequest = serde_json::from_slice(
            &read_frame(&mut bytes.as_slice(), REQUEST).unwrap().unwrap()).unwrap();
        assert_eq!(value.request_id, 42);
        assert!(require_valid_request(&value).is_ok());
        let mut bad = value;
        bad.version = 42;
        assert!(require_valid_request(&bad).is_err());
    }
}
