//! Full end-to-end IPC lifecycle against the actual bliss-mood executable.
//! No ONNX models, audio or SQLite fixtures are required.
#[path = "../src/feature_worker_process.rs"]
mod feature_worker_process;

use feature_worker_process::{FeatureWorkerProcess, WorkerOperation, WorkerReply, WorkerRequest};
use std::{
    io::{Read, Write},
    path::Path,
    process::{Command, Stdio},
    sync::{atomic::{AtomicBool, Ordering}, Arc},
    time::{Duration, Instant},
};

fn binary() -> &'static Path {
    Path::new(env!("CARGO_BIN_EXE_bliss-mood"))
}

#[test]
fn persistent_worker_reuses_process_and_responds_to_validated_ids() {
    let token = Arc::new(AtomicBool::new(false));
    let mut child = FeatureWorkerProcess::spawn(binary(), Duration::from_secs(8), token)
        .expect("start bounded protocol worker");
    let first = child.request(WorkerRequest::ping(1, 0x0102_0304)).unwrap();
    assert_eq!(first.request_id, 1);
    assert_eq!(first.reply, WorkerReply::Pong { nonce: 0x0102_0304 });
    let second = child.request(WorkerRequest::ping(2, 9001)).unwrap();
    assert_eq!(second.request_id, 2);
    assert_eq!(second.reply, WorkerReply::Pong { nonce: 9001 });
    let stop = child.request(WorkerRequest {
        version: 1, request_id: 3, operation: WorkerOperation::Shutdown,
    }).unwrap();
    assert_eq!(stop.reply, WorkerReply::Stopping);
    assert!(child.request(WorkerRequest::ping(4, 0)).is_err());
}

#[test]
fn repeated_request_id_poison_retires_worker_without_implicit_retry() {
    let mut child = FeatureWorkerProcess::spawn(
        binary(), Duration::from_secs(5), Arc::new(AtomicBool::new(false))
    ).unwrap();
    assert!(child.request(WorkerRequest::ping(7, 1)).is_ok());
    let error = child.request(WorkerRequest::ping(7, 2))
        .err().expect("duplicate ID must be rejected by persistent worker");
    assert!(format!("{error:#}").contains("exited") ||
        format!("{error:#}").contains("failed") ||
        format!("{error:#}").contains("fill whole buffer"));
    assert!(child.request(WorkerRequest::ping(8, 3)).is_err(),
        "protocol fault retires worker instead of silently reusing/retrying it");
}

#[test]
fn owned_worker_is_hard_killed_on_timeout() {
    let mut child = FeatureWorkerProcess::spawn(
        binary(), Duration::from_millis(250), Arc::new(AtomicBool::new(false)),
    ).unwrap();
    let start = Instant::now();
    let error = child.request(WorkerRequest::test_delay(1, 5000))
        .err().expect("timeout must stop blocked child");
    assert!(format!("{error:#}").contains("timeout"));
    assert!(start.elapsed() < Duration::from_secs(3));
    assert!(child.request(WorkerRequest::ping(2, 0)).is_err());
    // Retiring the timed-out process must not poison a newly started one.
    let mut replacement = FeatureWorkerProcess::spawn(
        binary(), Duration::from_secs(3), Arc::new(AtomicBool::new(false)),
    ).unwrap();
    assert_eq!(replacement.request(WorkerRequest::ping(1, 123)).unwrap().reply,
        WorkerReply::Pong { nonce: 123 });
}

#[test]
fn cancelling_one_worker_does_not_cancel_another() {
    let cancel_a = Arc::new(AtomicBool::new(false));
    let cancel_b = Arc::new(AtomicBool::new(false));
    let mut a = FeatureWorkerProcess::spawn(binary(), Duration::from_secs(8), Arc::clone(&cancel_a)).unwrap();
    let mut b = FeatureWorkerProcess::spawn(binary(), Duration::from_secs(8), Arc::clone(&cancel_b)).unwrap();
    let signal = std::thread::spawn(move || {
        std::thread::sleep(Duration::from_millis(180));
        cancel_a.store(true, Ordering::Release);
    });
    let now = Instant::now();
    let failure = a.request(WorkerRequest::test_delay(1, 5000)).unwrap_err();
    signal.join().unwrap();
    assert!(format!("{failure:#}").contains("cancelled"));
    assert!(now.elapsed() < Duration::from_secs(3));
    assert_eq!(b.request(WorkerRequest::ping(2, 42)).unwrap().reply,
               WorkerReply::Pong { nonce: 42 });
}

#[test]
fn malformed_oversized_frame_is_rejected_without_payload_allocation() {
    let mut child = Command::new(binary())
        .arg("internal-feature-worker")
        .stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::null())
        .spawn().unwrap();
    let mut hello = [0u8; 4];
    child.stdout.as_mut().unwrap().read_exact(&mut hello).unwrap();
    assert_eq!(&hello, b"FWP1");
    child.stdin.as_mut().unwrap().write_all(b"REQ1").unwrap();
    child.stdin.as_mut().unwrap().write_all(&u32::MAX.to_le_bytes()).unwrap();
    drop(child.stdin.take());
    assert!(!child.wait().unwrap().success());
}
