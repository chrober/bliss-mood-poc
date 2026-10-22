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

/// Aggregated policy observations; bounded even for full-library scans.
#[derive(Debug, Default, Clone, serde::Serialize)]
pub struct WorkerDecisionCounters {
    pub high_load_samples: usize,
    pub low_load_samples: usize,
    pub neutral_load_samples: usize,
    pub minimum_song_gate_holds: usize,
    pub cooldown_holds: usize,
    pub policy_holds: usize,
    pub increases: usize,
    pub decreases: usize,
}

/// Optional conservative resource guard. It limits the number of concurrent
/// active jobs rather than destroying/recreating expensive ONNX sessions.
/// Never changes the encoder, model scores, SQLite schema or file identity.
pub struct AdaptiveWorkers {
    pub active: usize,
    pub minimum: usize,
    pub maximum: usize,
    pub adjustments: Vec<WorkerAdjustment>,
    pub decisions: WorkerDecisionCounters,
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
            decisions: WorkerDecisionCounters::default(),
            last_change: std::time::Instant::now(),
            consecutive_high: 0,
            consecutive_low: 0,
        })
    }

    /// Admission uses the same cap as the production scan coordinator.
    pub fn permits_dispatch(&self, in_flight: usize) -> bool {
        in_flight < self.active
    }

    pub fn observe(&mut self, completed: usize, sample: crate::resources::LoadSample) {
        self.observe_at(completed, sample, std::time::Instant::now());
    }

    // Explicit time source enables deterministic tests of the real gate and
    // cooldown without sleeping; production observes the monotonic clock.
    fn observe_at(
        &mut self, completed: usize, sample: crate::resources::LoadSample,
        now: std::time::Instant,
    ) {
        let high = sample.system_ram_percent >= 88.0
            || sample.system_cpu_percent >= 90.0;
        let low = sample.system_ram_percent <= 79.0
            && sample.system_cpu_percent <= 65.0;
        if high { self.decisions.high_load_samples += 1; }
        else if low { self.decisions.low_load_samples += 1; }
        else { self.decisions.neutral_load_samples += 1; }
        self.consecutive_high = if high { self.consecutive_high + 1 } else { 0 };
        self.consecutive_low = if low { self.consecutive_low + 1 } else { 0 };

        // Adjust slowly, only after enough analyzed tracks. This avoids
        // chasing random song length and NAS/SMB cache variability.
        if completed < 24 {
            self.decisions.minimum_song_gate_holds += 1;
            return;
        }
        if now.duration_since(self.last_change).as_secs() < 20 {
            self.decisions.cooldown_holds += 1;
            return;
        }
        let from = self.active;
        let reason = if self.consecutive_high >= 2 && self.active > self.minimum {
            self.active -= 1;
            self.decisions.decreases += 1;
            "sustained CPU/RAM pressure"
        } else if self.consecutive_low >= 3 && self.active < self.maximum {
            self.active += 1;
            self.decisions.increases += 1;
            "sustained CPU/RAM headroom"
        } else {
            self.decisions.policy_holds += 1;
            return;
        };
        self.last_change = now;
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
    fn high_ram_reduces_concurrency_and_cooldown_prevents_thrashing() {
        use std::time::Duration;
        let mut ctl = AdaptiveWorkers::new(6, 4, 8).unwrap();
        ctl.last_change -= Duration::from_secs(21);
        let high = crate::resources::LoadSample {
            system_cpu_percent: 62.0,
            system_ram_percent: 91.0,
        };
        ctl.observe(24, high);
        assert_eq!(ctl.active, 6); // One spike is not enough.
        ctl.observe(25, high);
        assert_eq!(ctl.active, 5);
        assert_eq!(ctl.adjustments.len(), 1);
        assert_eq!(ctl.decisions.high_load_samples, 2);
        assert_eq!(ctl.decisions.decreases, 1);
        // The next sample may be high, but the cooldown inhibits changes.
        ctl.observe(26, high);
        ctl.observe(27, high);
        assert_eq!(ctl.active, 5);
        assert_eq!(ctl.decisions.cooldown_holds, 2);
    }

    #[test]
    fn headroom_can_add_one_worker_and_obeys_upper_bound() {
        use std::time::Duration;
        let mut ctl = AdaptiveWorkers::new(6, 4, 7).unwrap();
        let low = crate::resources::LoadSample {
            system_cpu_percent: 40.0, system_ram_percent: 65.0,
        };
        ctl.last_change -= Duration::from_secs(21);
        ctl.observe(24, low);
        ctl.observe(25, low);
        assert_eq!(ctl.active, 6);
        ctl.observe(26, low);
        assert_eq!(ctl.active, 7);
        ctl.last_change -= Duration::from_secs(21);
        for n in 27..34 {
            ctl.observe(n, low);
        }
        assert_eq!(ctl.active, 7);
        assert_eq!(ctl.adjustments.len(), 1);
    }

    #[test]
    fn neutral_samples_never_trigger_a_change() {
        use std::time::Duration;
        let mut ctl = AdaptiveWorkers::new(6, 4, 8).unwrap();
        ctl.last_change -= Duration::from_secs(21);
        let neutral = crate::resources::LoadSample {
            system_cpu_percent: 50.0, system_ram_percent: 85.0,
        };
        for completed in 24..34 { ctl.observe(completed, neutral); }
        assert_eq!(ctl.active, 6);
        assert_eq!(ctl.decisions.neutral_load_samples, 10);
        assert_eq!(ctl.decisions.policy_holds, 10);
    }

    #[test]
    fn admission_cap_changes_after_real_policy_adjustments() {
        use std::time::{Duration, Instant};
        let mut ctl = AdaptiveWorkers::new(2, 1, 3).unwrap();
        let low = crate::resources::LoadSample {
            system_cpu_percent: 40.0, system_ram_percent: 60.0,
        };
        let high = crate::resources::LoadSample {
            system_cpu_percent: 92.0, system_ram_percent: 70.0,
        };
        let t = Instant::now() + Duration::from_secs(21);

        assert!(ctl.permits_dispatch(1));
        assert!(!ctl.permits_dispatch(2));
        // At 23 completed songs the minimum-song gate forbids changes.
        ctl.observe_at(23, low, t);
        assert_eq!(ctl.active, 2);
        ctl.observe_at(24, low, t + Duration::from_millis(1));
        assert_eq!(ctl.active, 2);
        ctl.observe_at(25, low, t + Duration::from_millis(2));
        assert_eq!(ctl.active, 3);
        assert!(ctl.permits_dispatch(2)); // New third task admitted.
        assert!(!ctl.permits_dispatch(3));

        // Sustained pressure within cooldown cannot reduce capacity.
        ctl.observe_at(26, high, t + Duration::from_secs(1));
        assert_eq!(ctl.active, 3);
        ctl.observe_at(27, high, t + Duration::from_secs(22));
        assert_eq!(ctl.active, 2);
        assert!(!ctl.permits_dispatch(2)); // Coordinator drains to below cap.
        assert!(ctl.permits_dispatch(1));
        assert_eq!(ctl.adjustments.len(), 2);
        assert_eq!((ctl.decisions.increases, ctl.decisions.decreases), (1, 1));
    }

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
