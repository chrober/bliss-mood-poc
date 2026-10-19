//! Conservative CPU worker sizing for background offline library analysis.
//! --threads controls ONNX *inside one track*; --workers controls parallel tracks.

use anyhow::{bail, Result};

pub fn worker_count(spec: &str) -> Result<(usize, bool)> {
    let available = std::thread::available_parallelism()
        .map(|n| n.get()).unwrap_or(2);
    if spec.eq_ignore_ascii_case("auto") {
        // Leave at least 2 logical CPUs (where possible) and roughly a
        // quarter of the reported CPU capacity for interactive applications.
        // Avoid many concurrent ONNX sessions and simultaneous NAS reads.
        let reserve = (available / 4).max(2);
        let workers = available.saturating_sub(reserve).clamp(1, 8);
        Ok((workers, true))
    } else {
        let workers: usize = spec.parse().map_err(|_| {
            anyhow::anyhow!("--workers must be 'auto' or a positive integer")
        })?;
        if !(1..=64).contains(&workers) {
            bail!("--workers must be between 1 and 64");
        }
        Ok((workers, false))
    }
}


#[derive(Debug, Clone, serde::Serialize)]
pub struct WorkerAdjustment {
    pub after_completed_songs: usize,
    pub from_workers: usize,
    pub to_workers: usize,
    pub reason: String,
    pub system_cpu_percent: f64,
    pub system_ram_percent: f64,
}

/// Optional conservative resource guard. It limits the number of concurrent
/// active jobs rather than destroying/recreating expensive ONNX sessions.
/// Never changes the encoder, model scores, SQLite schema or file identity.
pub struct AdaptiveWorkers {
    pub active: usize,
    pub minimum: usize,
    pub maximum: usize,
    pub adjustments: Vec<WorkerAdjustment>,
    last_change: std::time::Instant,
    consecutive_high: usize,
    consecutive_low: usize,
}

impl AdaptiveWorkers {
    pub fn new(initial: usize, minimum: usize, maximum: usize) -> Result<Self> {
        if minimum == 0 || minimum > initial || initial > maximum || maximum > 64 {
            bail!("Adaptive worker bounds require 1 <= min <= workers <= max <= 64");
        }
        Ok(Self {
            active: initial,
            minimum,
            maximum,
            adjustments: Vec::new(),
            last_change: std::time::Instant::now(),
            consecutive_high: 0,
            consecutive_low: 0,
        })
    }

    pub fn observe(&mut self, completed: usize, sample: crate::resources::LoadSample) {
        let high = sample.system_ram_percent >= 88.0
            || sample.system_cpu_percent >= 90.0;
        let low = sample.system_ram_percent <= 79.0
            && sample.system_cpu_percent <= 65.0;
        self.consecutive_high = if high { self.consecutive_high + 1 } else { 0 };
        self.consecutive_low = if low { self.consecutive_low + 1 } else { 0 };

        // Adjust slowly, only after enough analyzed tracks. This avoids
        // chasing random song length and NAS/SMB cache variability.
        if completed < 24 || self.last_change.elapsed().as_secs() < 20 {
            return;
        }
        let from = self.active;
        let reason = if self.consecutive_high >= 2 && self.active > self.minimum {
            self.active -= 1;
            "sustained CPU/RAM pressure"
        } else if self.consecutive_low >= 3 && self.active < self.maximum {
            self.active += 1;
            "sustained CPU/RAM headroom"
        } else {
            return;
        };
        self.last_change = std::time::Instant::now();
        self.consecutive_high = 0;
        self.consecutive_low = 0;
        eprintln!(
            "ADAPTIVE WORKERS {} -> {} after {} completed tracks: {} (system CPU {:.1}%, RAM {:.1}%)",
            from, self.active, completed, reason,
            sample.system_cpu_percent, sample.system_ram_percent
        );
        self.adjustments.push(WorkerAdjustment {
            after_completed_songs: completed,
            from_workers: from,
            to_workers: self.active,
            reason: reason.to_owned(),
            system_cpu_percent: sample.system_cpu_percent,
            system_ram_percent: sample.system_ram_percent,
        });
    }
}

/// On Windows, make auto-mode background work lower priority than interactive
/// applications. It does not change priority outside this process.
#[cfg(windows)]
pub fn lower_priority_auto() {
    use std::ffi::c_void;
    #[link(name = "kernel32")]
    extern "system" {
        fn GetCurrentProcess() -> *mut c_void;
        fn SetPriorityClass(process: *mut c_void, priority: u32) -> i32;
    }
    const BELOW_NORMAL_PRIORITY_CLASS: u32 = 0x0000_4000;
    // SAFETY: The pseudo-handle refers only to our own process. The
    // Win32 APIs accept the constant documented priority-class value.
    let success = unsafe {
        SetPriorityClass(GetCurrentProcess(), BELOW_NORMAL_PRIORITY_CLASS)
    };
    if success == 0 {
        eprintln!("WARNING: Could not lower Windows analysis process priority");
    }
}

#[cfg(not(windows))]
pub fn lower_priority_auto() {}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn adaptive_bounds_validate() {
        assert!(AdaptiveWorkers::new(6, 4, 8).is_ok());
        assert!(AdaptiveWorkers::new(6, 7, 8).is_err());
        assert!(AdaptiveWorkers::new(6, 4, 5).is_err());
        assert!(AdaptiveWorkers::new(1, 0, 8).is_err());
    }

    #[test]
    fn resolves_worker_count_and_validates_bounds() {
        let (auto, enabled) = worker_count("auto").unwrap();
        assert!(enabled && (1..=8).contains(&auto));
        assert_eq!(worker_count("1").unwrap(), (1, false));
        assert_eq!(worker_count("4").unwrap(), (4, false));
        for spec in ["0", "65", "-1", "NaN", "4.5", ""] {
            assert!(worker_count(spec).is_err(), "{spec}");
        }
    }
}
