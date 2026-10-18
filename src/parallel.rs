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
