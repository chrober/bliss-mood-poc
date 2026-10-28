//! Phase C vertical slice: a bounded, versioned IPC protocol to a supervised
//! instance of this executable. No ONNX or audio is sent yet; the real
//! FeatureEngine remains on its validated thread path until parity is proven.
#![allow(dead_code)] // Supervised client is staged until the actual ONNX migration.
use anyhow::{bail, Context, Result};
use serde::{Deserialize, Serialize};
use std::{
    io::{Read, Write},
    path::Path,
    process::{Child, ChildStdin, ChildStdout, Command, Stdio},
    sync::{
        atomic::{AtomicBool, Ordering},
        mpsc, Arc,
    },
    thread,
    time::{Duration, Instant},
};

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
pub fn serve_stdio() -> Result<()> {
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
        };
        let response = WorkerResponse {
            version: PROTOCOL_VERSION, request_id: request.request_id, reply,
        };
        write_frame(&mut writer, RESPONSE, &serde_json::to_vec(&response)?)?;
        if stop { break; }
    }
    Ok(())
}

struct OwnedChild(Child);

impl Drop for OwnedChild {
    fn drop(&mut self) {
        let _ = self.0.kill();
        let _ = self.0.wait();
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
        let mut child = OwnedChild(command.spawn()
            .with_context(|| format!("Cannot start feature worker {}", executable.display()))?);
        let stdin = child.0.stdin.take().context("Feature-worker stdin unavailable")?;
        let stdout = child.0.stdout.take().context("Feature-worker stdout unavailable")?;
        Ok(Self {
            child: Some(child), stdin: Some(stdin), stdout: Some(stdout),
            handshake_pending: true, timeout, cancellation,
        })
    }

    pub fn request(&mut self, request: WorkerRequest) -> Result<WorkerResponse> {
        require_valid_request(&request)?;
        if self.cancellation.load(Ordering::Acquire) {
            bail!("Feature-worker request cancelled before dispatch");
        }
        let mut child = self.child.take().context("Feature worker not running")?;
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
