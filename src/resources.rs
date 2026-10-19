//! Lightweight system-wide CPU and physical RAM telemetry.
//! CPU is measured as a delta between OS cumulative counters; no external
//! profiling tools or dependencies required.
use serde::Serialize;
use std::time::{Duration, Instant};

#[derive(Clone, Copy, Debug, Serialize)]
pub struct LoadSample {
    pub system_cpu_percent: f64,
    pub system_ram_percent: f64,
}

/// Optional diagnostic snapshot; does not affect concurrency decisions.
#[derive(Clone, Copy, Debug, Serialize)]
pub struct MemoryDiagnostics {
    pub available_physical_mib: f64,
}

pub fn memory_diagnostics() -> Option<MemoryDiagnostics> {
    native::available_memory_bytes().map(|bytes| MemoryDiagnostics {
        available_physical_mib: bytes as f64 / (1024.0 * 1024.0),
    })
}

pub struct ResourceMonitor {
    previous: Option<(u64, u64)>,
    last: Instant,
}

impl ResourceMonitor {
    pub fn new() -> Self {
        Self {
            previous: cpu_ticks(),
            last: Instant::now(),
        }
    }

    pub fn sample(&mut self) -> Option<LoadSample> {
        if self.last.elapsed() < Duration::from_secs(2) {
            return None;
        }
        self.last = Instant::now();
        let current = cpu_ticks()?;
        let previous = self.previous.replace(current)?;
        let busy = current.0.saturating_sub(previous.0);
        let total = current.1.saturating_sub(previous.1);
        let ram = memory_load()?;
        if total == 0 || !ram.is_finite() {
            return None;
        }
        Some(LoadSample {
            system_cpu_percent: (100.0 * busy as f64 / total as f64).clamp(0.0, 100.0),
            system_ram_percent: ram.clamp(0.0, 100.0),
        })
    }
}

#[cfg(windows)]
mod native {
    #[repr(C)]
    #[derive(Default, Clone, Copy)]
    struct FileTime {
        low: u32,
        high: u32,
    }

    #[repr(C)]
    #[derive(Default)]
    struct MemoryStatusEx {
        length: u32,
        memory_load: u32,
        total_phys: u64,
        avail_phys: u64,
        total_pagefile: u64,
        avail_pagefile: u64,
        total_virtual: u64,
        avail_virtual: u64,
        avail_extended_virtual: u64,
    }

    #[link(name = "kernel32")]
    extern "system" {
        fn GetSystemTimes(idle: *mut FileTime, kernel: *mut FileTime, user: *mut FileTime) -> i32;
        fn GlobalMemoryStatusEx(status: *mut MemoryStatusEx) -> i32;
    }

    fn to_ticks(time: FileTime) -> u64 {
        (u64::from(time.high) << 32) | u64::from(time.low)
    }

    pub fn cpu_ticks() -> Option<(u64, u64)> {
        let (mut idle, mut kernel, mut user) = (FileTime::default(), FileTime::default(), FileTime::default());
        // SAFETY: The OS populates all three fixed-layout structures; no pointers are retained.
        if unsafe { GetSystemTimes(&mut idle, &mut kernel, &mut user) } == 0 {
            return None;
        }
        let total = to_ticks(kernel).saturating_add(to_ticks(user));
        let busy = total.saturating_sub(to_ticks(idle));
        Some((busy, total))
    }

    fn memory_status() -> Option<MemoryStatusEx> {
        let mut info = MemoryStatusEx {
            length: std::mem::size_of::<MemoryStatusEx>() as u32,
            ..MemoryStatusEx::default()
        };
        // SAFETY: Fixed-layout MEMORYSTATUSEX, correct dwLength supplied.
        if unsafe { GlobalMemoryStatusEx(&mut info) } == 0 {
            return None;
        }
        if info.total_phys == 0 { return None; }
        Some(info)
    }

    pub fn memory_load() -> Option<f64> {
        let info = memory_status()?;
        Some(100.0 * (1.0 - info.avail_phys as f64 / info.total_phys as f64))
    }

    pub fn available_memory_bytes() -> Option<u64> {
        Some(memory_status()?.avail_phys)
    }
}

#[cfg(target_os = "linux")]
mod native {
    use std::fs;
    pub fn cpu_ticks() -> Option<(u64, u64)> {
        let stats = fs::read_to_string("/proc/stat").ok()?;
        let line = stats.lines().next()?;
        let mut items = line.split_whitespace();
        if items.next()? != "cpu" {
            return None;
        }
        let values: Vec<u64> = items.take(8).map(str::parse).collect::<Result<_, _>>().ok()?;
        if values.len() < 4 {
            return None;
        }
        let total: u64 = values.iter().sum();
        let idle = values[3].saturating_add(values.get(4).copied().unwrap_or(0));
        Some((total.saturating_sub(idle), total))
    }
    pub fn available_memory_bytes() -> Option<u64> {
        let stats = fs::read_to_string("/proc/meminfo").ok()?;
        let line = stats.lines().find(|line| line.starts_with("MemAvailable:"))?;
        let kib: u64 = line.split_whitespace().nth(1)?.parse().ok()?;
        kib.checked_mul(1024)
    }
    pub fn memory_load() -> Option<f64> {
        let stats = fs::read_to_string("/proc/meminfo").ok()?;
        let get = |prefix: &str| -> Option<f64> {
            stats.lines().find(|line| line.starts_with(prefix))?
                .split_whitespace().nth(1)?.parse().ok()
        };
        let total = get("MemTotal:")?;
        let available = get("MemAvailable:")?;
        if total <= 0.0 { return None; }
        Some(100.0 * (1.0 - available / total))
    }
}

#[cfg(not(any(target_os = "linux", windows)))]
mod native {
    pub fn cpu_ticks() -> Option<(u64,u64)> { None }
    pub fn memory_load() -> Option<f64> { None }
    pub fn available_memory_bytes() -> Option<u64> { None }
}

use native::{cpu_ticks, memory_load};

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn memory_and_cpu_queries_are_optional_but_bounded() {
        if let Some(percentage) = memory_load() {
            assert!((0.0..=100.0).contains(&percentage));
        }
        if let Some((busy, total)) = cpu_ticks() {
            assert!(total >= busy);
        }
        if let Some(detail) = memory_diagnostics() {
            assert!(detail.available_physical_mib.is_finite());
            assert!(detail.available_physical_mib >= 0.0);
        }
        let mut monitor = ResourceMonitor::new();
        // First sample intentionally waits for a nonzero OS counter interval.
        assert!(monitor.sample().is_none());
    }
}
