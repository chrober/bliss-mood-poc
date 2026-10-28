//! Independent fail-closed RAM watchdog for experimental online autotuning.
//! Runs while a native song can be blocked in decoding or ONNX inference.
//! A fault stops *new* dispatch and asks native workers to terminate promptly.
use anyhow::{bail, Result};
use serde::Serialize;
use std::{
    sync::{atomic::{AtomicBool, Ordering}, Arc, Mutex},
    thread::{self, JoinHandle},
    time::Duration,
};

const POLL_INTERVAL: Duration = Duration::from_millis(250);

#[derive(Clone, Debug, Default, Serialize)]
pub struct WatchdogDiagnostics {
    pub samples: usize,
    pub minimum_available_mib: Option<f64>,
    pub fault: Option<String>,
}

fn fault_for(available: Option<f64>, reserve_mib: f64) -> Option<String> {
    match available {
        Some(value) if value.is_finite() && value > reserve_mib => None,
        Some(value) if value.is_finite() && value >= 0.0 => Some(format!(
            "RAM watchdog reserve reached: available {value:.1} MiB, required > {reserve_mib:.1} MiB"
        )),
        _ => Some("RAM watchdog missing or invalid effective free-memory telemetry".to_owned()),
    }
}

pub struct MemoryWatchdog {
    stop: Arc<AtomicBool>,
    state: Arc<Mutex<WatchdogDiagnostics>>,
    handle: Option<JoinHandle<()>>,
    stop_native: bool,
}

impl MemoryWatchdog {
    pub fn start(reserve_mib: f64) -> Result<Self> {
        Self::start_with_sampler(
            reserve_mib, POLL_INTERVAL, true,
            || crate::resources::memory_diagnostics().map(|m| m.available_physical_mib),
        )
    }

    fn start_with_sampler(
        reserve_mib: f64, period: Duration, stop_native: bool,
        sampler: impl Fn() -> Option<f64> + Send + 'static,
    ) -> Result<Self> {
        if !reserve_mib.is_finite() || reserve_mib <= 0.0 || period.is_zero() {
            bail!("RAM watchdog needs a positive reserve and sampling interval");
        }
        let state = Arc::new(Mutex::new(WatchdogDiagnostics::default()));
        let stop = Arc::new(AtomicBool::new(false));
        let state_for_thread = Arc::clone(&state);
        let stop_for_thread = Arc::clone(&stop);
        let handle = thread::spawn(move || {
            // First observation occurs immediately. Never silently ignore an
            // invalid sample or failed lock; failure is fatal to autotune.
            while !stop_for_thread.load(Ordering::Acquire) {
                let measured = sampler();
                let fault = fault_for(measured, reserve_mib);
                let mut state = state_for_thread.lock()
                    .unwrap_or_else(std::sync::PoisonError::into_inner);
                state.samples += 1;
                if let Some(value) = measured.filter(|m| m.is_finite() && *m >= 0.0) {
                    state.minimum_available_mib = Some(state.minimum_available_mib
                        .map_or(value, |old| old.min(value)));
                }
                if let Some(reason) = fault {
                    state.fault = Some(reason);
                    if stop_native {
                        crate::resources::request_native_cancellation();
                    }
                    break;
                }
                drop(state);
                thread::sleep(period);
            }
        });
        Ok(Self { stop, state, handle: Some(handle), stop_native })
    }

    pub fn check(&self) -> Result<()> {
        if let Some(reason) = self.snapshot().fault {
            bail!("{reason}");
        }
        Ok(())
    }

    pub fn snapshot(&self) -> WatchdogDiagnostics {
        self.state.lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner).clone()
    }
}

impl Drop for MemoryWatchdog {
    fn drop(&mut self) {
        self.stop.store(true, Ordering::Release);
        if let Some(handle) = self.handle.take() {
            let _ = handle.join();
        }
        if self.stop_native {
            crate::resources::reset_native_cancellation();
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::VecDeque;

    #[test]
    fn validates_samples_without_hiding_unavailable_memory() {
        assert!(fault_for(None, 512.0).is_some());
        assert!(fault_for(Some(f64::NAN), 512.0).is_some());
        assert!(fault_for(Some(-1.0), 512.0).is_some());
        assert!(fault_for(Some(512.0), 512.0).is_some());
        assert!(fault_for(Some(512.01), 512.0).is_none());
        assert!(MemoryWatchdog::start_with_sampler(
            0.0, Duration::from_millis(1), false, || Some(1000.0)
        ).is_err());
    }

    #[test]
    fn watchdog_reports_pressure_while_no_song_finishes() {
        let measurements = Arc::new(Mutex::new(VecDeque::from([
            Some(1800.0), Some(1500.0), Some(500.0),
        ])));
        let copy = Arc::clone(&measurements);
        let watch = MemoryWatchdog::start_with_sampler(
            512.0, Duration::from_millis(2), false,
            move || copy.lock().unwrap().pop_front().unwrap_or(Some(500.0))
        ).unwrap();
        for _ in 0..100 {
            if watch.check().is_err() { break; }
            thread::sleep(Duration::from_millis(2));
        }
        assert!(watch.check().is_err());
        let stats = watch.snapshot();
        assert!(stats.samples >= 3);
        assert_eq!(stats.minimum_available_mib, Some(500.0));
        assert!(stats.fault.unwrap().contains("reserve"));
    }

    #[test]
    fn watchdog_stops_cleanly_without_spurious_fault() {
        let watch = MemoryWatchdog::start_with_sampler(
            512.0, Duration::from_millis(2), false, || Some(2000.0)
        ).unwrap();
        thread::sleep(Duration::from_millis(9));
        assert!(watch.check().is_ok());
        assert!(watch.snapshot().samples > 0);
    }
}
