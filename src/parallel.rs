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
    pub min_completed_songs: usize,
    last_change: std::time::Instant,
    consecutive_high: usize,
    consecutive_low: usize,
}

impl AdaptiveWorkers {
    pub fn new(initial: usize, minimum: usize, maximum: usize) -> Result<Self> {
        Self::with_min_completed_songs(initial, minimum, maximum, 24)
    }

    pub fn with_min_completed_songs(
        initial: usize, minimum: usize, maximum: usize, min_completed_songs: usize,
    ) -> Result<Self> {
        if minimum == 0 || minimum > initial || initial > maximum || maximum > 64 {
            bail!("Adaptive worker bounds require 1 <= min <= workers <= max <= 64");
        }
        if !(1..=100_000).contains(&min_completed_songs) {
            bail!("--adaptive-min-completed-songs must be within 1..=100000");
        }
        Ok(Self {
            active: initial,
            minimum,
            maximum,
            adjustments: Vec::new(),
            decisions: WorkerDecisionCounters::default(),
            min_completed_songs,
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
        if completed < self.min_completed_songs {
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

/// Explicit Windows priority is independent of worker count and adaptive policy.
/// Omitted --priority retains the preexisting fixed/auto/adaptive behavior.
#[derive(Clone, Debug, serde::Serialize)]
pub struct PriorityDiagnostics {
    pub requested: String,
    pub policy: String,
    pub effective_scanner: Option<String>,
    pub native_worker_classes: Vec<String>,
    pub native_worker_observation_failures: usize,
}

fn priority_policy(requested: Option<&str>, is_auto: bool, adaptive: bool) -> Result<&'static str> {
    match requested {
        Some("normal") => Ok("normal"),
        Some("below-normal") => Ok("below-normal"),
        Some("above-normal") => Ok("above-normal"),
        None if is_auto || adaptive => Ok("below-normal"),
        None => Ok("unchanged"),
        Some(_) => bail!("Invalid --priority; choose below-normal, normal or above-normal"),
    }
}

pub fn configure_scan_priority(
    requested: Option<&str>, is_auto: bool, adaptive: bool, dry_run: bool,
) -> Result<PriorityDiagnostics> {
    let policy = priority_policy(requested, is_auto, adaptive)?;
    #[cfg(not(windows))]
    if requested.is_some() {
        bail!("--priority is Windows-only; omit it to use platform-native scheduling");
    }

    #[cfg(windows)]
    if !dry_run && policy != "unchanged" {
        let target = match policy {
            "normal" => NORMAL_PRIORITY_CLASS,
            "below-normal" => BELOW_NORMAL_PRIORITY_CLASS,
            "above-normal" => ABOVE_NORMAL_PRIORITY_CLASS,
            _ => unreachable!("validated priority class"),
        };
        if let Err(err) = set_current_windows_priority(target) {
            if requested.is_some() {
                return Err(err);
            }
            eprintln!("WARNING: Cannot lower Windows process priority: {err:#}");
        }
    }
    let effective = current_windows_priority().map(str::to_owned);
    #[cfg(windows)]
    if requested.is_some() && !dry_run && effective.as_deref() != Some(policy) {
        bail!("Windows priority mismatch: requested {policy}, observed {effective:?}");
    }
    // Explicit classes must be passed to CreateProcess for native children:
    // Windows only inherits BelowNormal/Idle, not AboveNormal.
    // Zero means legacy child priority behavior (no creation class flag).
    #[cfg(windows)]
    NATIVE_CHILD_CREATION_CLASS.store(
        if !dry_run && requested.is_some() {
            match policy {
                "normal" => NORMAL_PRIORITY_CLASS,
                "below-normal" => BELOW_NORMAL_PRIORITY_CLASS,
                "above-normal" => ABOVE_NORMAL_PRIORITY_CLASS,
                _ => unreachable!("validated priority class"),
            }
        } else {
            0
        },
        std::sync::atomic::Ordering::SeqCst,
    );
    crate::resources::reset_native_priority_observations();
    Ok(PriorityDiagnostics {
        requested: requested.unwrap_or("default").to_owned(),
        policy: if dry_run { "unchanged" } else { policy }.to_owned(),
        effective_scanner: effective,
        native_worker_classes: Vec::new(),
        native_worker_observation_failures: 0,
    })
}

impl PriorityDiagnostics {
    pub fn collect_native_workers(&mut self) {
        let (classes, failures) = crate::resources::native_priority_observations();
        self.native_worker_classes = classes;
        self.native_worker_observation_failures = failures;
    }
}

#[cfg(windows)]
static NATIVE_CHILD_CREATION_CLASS: std::sync::atomic::AtomicU32 =
    std::sync::atomic::AtomicU32::new(0);

#[cfg(windows)]
const ABOVE_NORMAL_PRIORITY_CLASS: u32 = 0x0000_8000;
#[cfg(windows)]
const NORMAL_PRIORITY_CLASS: u32 = 0x0000_0020;
#[cfg(windows)]
const BELOW_NORMAL_PRIORITY_CLASS: u32 = 0x0000_4000;

#[cfg(windows)]
#[link(name = "kernel32")]
extern "system" {
    fn GetCurrentProcess() -> *mut std::ffi::c_void;
    fn GetPriorityClass(process: *mut std::ffi::c_void) -> u32;
    fn SetPriorityClass(process: *mut std::ffi::c_void, priority: u32) -> i32;
}

#[cfg(windows)]
fn priority_class_name(priority: u32) -> &'static str {
    match priority {
        0x0000_0040 => "idle",
        0x0000_4000 => "below-normal",
        0x0000_0020 => "normal",
        0x0000_8000 => "above-normal",
        0x0000_0080 => "high",
        0x0000_0100 => "realtime",
        _ => "unknown",
    }
}

#[cfg(windows)]
fn set_current_windows_priority(priority: u32) -> Result<()> {
    if unsafe { SetPriorityClass(GetCurrentProcess(), priority) } == 0 {
        bail!("SetPriorityClass failed: {}", std::io::Error::last_os_error());
    }
    Ok(())
}

#[cfg(windows)]
fn current_windows_priority() -> Option<&'static str> {
    let value = unsafe { GetPriorityClass(GetCurrentProcess()) };
    (value != 0).then(|| priority_class_name(value))
}

#[cfg(not(windows))]
fn current_windows_priority() -> Option<&'static str> { None }

/// Add the verified explicit class to CreateProcess before the native worker
/// executes anything. This is essential for AboveNormal, which Windows does
/// not inherit from its parent.
pub fn configure_native_child_command(command: &mut std::process::Command) {
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        let flags = NATIVE_CHILD_CREATION_CLASS.load(std::sync::atomic::Ordering::SeqCst);
        if flags != 0 {
            command.creation_flags(flags);
        }
    }
    #[cfg(not(windows))]
    let _ = command;
}

/// Explicit selection is fail-closed: never analyze tracks under an
/// unexpected native child priority class.
pub fn verify_native_child_priority(child: &std::process::Child) -> Result<()> {
    #[cfg(windows)]
    {
        let expected = NATIVE_CHILD_CREATION_CLASS.load(std::sync::atomic::Ordering::SeqCst);
        if expected != 0 {
            let actual = native_child_priority(child);
            if actual != Some(priority_class_name(expected)) {
                bail!("Native worker scheduling priority mismatch: expected {}, got {actual:?}",
                    priority_class_name(expected));
            }
        }
    }
    #[cfg(not(windows))]
    let _ = child;
    Ok(())
}

/// Query the actual native child process handle immediately after spawn.
#[cfg(windows)]
pub fn native_child_priority(child: &std::process::Child) -> Option<&'static str> {
    use std::os::windows::io::AsRawHandle;
    let value = unsafe { GetPriorityClass(child.as_raw_handle().cast()) };
    (value != 0).then(|| priority_class_name(value))
}

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
    fn configured_gate_eight_accepts_earlier_growth_but_keeps_cooldown() {
        use std::time::{Duration, Instant};
        let low = crate::resources::LoadSample {
            system_cpu_percent: 20.0, system_ram_percent: 65.0,
        };
        let mut early = AdaptiveWorkers::with_min_completed_songs(2, 2, 6, 8).unwrap();
        let mut legacy = AdaptiveWorkers::new(2, 2, 6).unwrap();
        let t = Instant::now() + Duration::from_secs(21);
        for completed in 1..=7 {
            early.observe_at(completed, low, t);
            legacy.observe_at(completed, low, t);
        }
        assert_eq!(early.active, 2);
        early.observe_at(8, low, t);
        legacy.observe_at(8, low, t);
        assert_eq!(early.active, 3);
        assert_eq!(legacy.active, 2);
        early.observe_at(9, low, t + Duration::from_secs(1));
        assert_eq!(early.active, 3);
        assert_eq!(early.decisions.increases, 1);
        assert_eq!(early.decisions.cooldown_holds, 1);
        assert_eq!(legacy.min_completed_songs, 24);
    }

    #[test]
    fn high_load_remains_gated_and_needs_two_samples() {
        use std::time::{Duration, Instant};
        let high = crate::resources::LoadSample {
            system_cpu_percent: 93.0, system_ram_percent: 65.0,
        };
        let mut ctrl = AdaptiveWorkers::with_min_completed_songs(6, 2, 6, 8).unwrap();
        let t = Instant::now() + Duration::from_secs(21);
        ctrl.observe_at(7, high, t);
        assert_eq!(ctrl.active, 6);
        ctrl.observe_at(8, high, t);
        assert_eq!(ctrl.active, 5);
        assert_eq!(ctrl.adjustments[0].after_completed_songs, 8);
    }

    #[test]
    fn adaptive_bounds_validate() {
        assert!(AdaptiveWorkers::new(6, 4, 8).is_ok());
        assert!(AdaptiveWorkers::new(6, 7, 8).is_err());
        assert!(AdaptiveWorkers::new(6, 4, 5).is_err());
        assert!(AdaptiveWorkers::new(1, 0, 8).is_err());
        assert!(AdaptiveWorkers::with_min_completed_songs(2, 1, 6, 0).is_err());
        assert!(AdaptiveWorkers::with_min_completed_songs(2, 1, 6, 100001).is_err());
    }

    #[test]
    fn explicit_priority_policy_decouples_mode_from_process_priority() {
        assert_eq!(priority_policy(None, false, false).unwrap(), "unchanged");
        assert_eq!(priority_policy(None, true, false).unwrap(), "below-normal");
        assert_eq!(priority_policy(None, false, true).unwrap(), "below-normal");
        for mode in [(false, false), (false, true), (true, false)] {
            assert_eq!(priority_policy(Some("normal"), mode.0, mode.1).unwrap(), "normal");
            assert_eq!(priority_policy(Some("below-normal"), mode.0, mode.1).unwrap(), "below-normal");
            assert_eq!(priority_policy(Some("above-normal"), mode.0, mode.1).unwrap(), "above-normal");
        }
        assert!(priority_policy(Some("realtime"), false, false).is_err());
    }

    /// Run priority changes in an isolated test-harness subprocess so other
    /// concurrently running tests never have their own priority changed.
    #[cfg(windows)]
    #[test]
    fn windows_priority_is_applied_and_inherited_by_real_child() {
        const CHILD: &str = "LYRION_TEST_PRIORITY_CHILD";
        if std::env::var_os(CHILD).is_none() {
            let current = std::env::current_exe().unwrap();
            let result = std::process::Command::new(current)
                .args(["--exact",
                    "parallel::tests::windows_priority_is_applied_and_inherited_by_real_child",
                    "--nocapture"])
                .env(CHILD, "yes")
                .output()
                .unwrap();
            assert!(result.status.success(),
                "child test failed: {} {}",
                String::from_utf8_lossy(&result.stdout),
                String::from_utf8_lossy(&result.stderr));
            return;
        }
        for requested in ["below-normal", "normal", "above-normal"] {
            let observed = configure_scan_priority(
                Some(requested), false, false, false,
            ).unwrap();
            assert_eq!(observed.effective_scanner.as_deref(), Some(requested));
            let mut command = std::process::Command::new("powershell.exe");
            command.args(["-NoProfile", "-NonInteractive",
                "-Command", "Start-Sleep -Milliseconds 700"]);
            configure_native_child_command(&mut command);
            let mut child = command.spawn().unwrap();
            assert_eq!(native_child_priority(&child), Some(requested));
            verify_native_child_priority(&child).unwrap();
            child.wait().unwrap();
        }
    }

    #[cfg(windows)]
    #[test]
    fn maps_windows_priority_classes() {
        assert_eq!(priority_class_name(NORMAL_PRIORITY_CLASS), "normal");
        assert_eq!(priority_class_name(BELOW_NORMAL_PRIORITY_CLASS), "below-normal");
        assert_eq!(priority_class_name(ABOVE_NORMAL_PRIORITY_CLASS), "above-normal");
        assert_eq!(priority_class_name(0), "unknown");
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
