//! Experimental, opt-in hardware-independent online concurrency search.
//! Never assumes throughput increases monotonically with worker count.
//! It controls admission; already-running native sessions are not destroyed.
use anyhow::{bail, Result};
use serde::Serialize;
use std::{collections::{BTreeMap, BTreeSet, VecDeque}, time::{Duration, Instant}};

const WORKER_MEMORY_FLOOR_MIB: f64 = 256.0;
const RESERVE_MIN_MIB: f64 = 512.0;
const MIN_EPOCH_SONGS: usize = 8;
const MIN_EPOCH_DURATION: Duration = Duration::from_secs(12);
const IMPROVEMENT_MARGIN: f64 = 0.05;
const MAX_RETAINED_PROBES: usize = 256;
const RECENT_SAMPLES_PER_WORKER: usize = 8;

#[derive(Clone, Debug, Serialize)]
pub struct Probe {
    pub workers: usize,
    pub completed_songs: usize,
    pub patches: usize,
    pub elapsed_seconds: f64,
    pub patches_per_second: f64,
    pub songs_per_minute: f64,
}

#[derive(Debug, Default, Serialize)]
pub struct TuningCounters {
    pub probes: usize,
    pub completed_coarse_sweeps: usize,
    pub expansions: usize,
    pub reductions: usize,
    pub memory_pressure_reductions: usize,
    pub memory_gate_holds: usize,
    pub insufficient_work_holds: usize,
}

/// Bounded rolling evidence per worker count. The ranges are descriptive,
/// not formal confidence intervals: workloads change between song windows.
#[derive(Debug, Serialize)]
pub struct CandidateEvidence {
    pub workers: usize,
    pub samples: usize,
    pub median_patches_per_second: f64,
    pub minimum_patches_per_second: f64,
    pub maximum_patches_per_second: f64,
}

#[derive(Debug, Serialize)]
pub struct TuningAdjustment {
    pub after_completed_songs: usize,
    pub from_workers: usize,
    pub to_workers: usize,
    pub reason: String,
    pub available_ram_mib: f64,
}

#[derive(Debug, Serialize)]
pub struct TuningDiagnostics {
    pub strategy: &'static str,
    pub initial_workers: usize,
    pub final_workers: usize,
    pub best_tested_workers: Option<usize>,
    pub best_observed_patches_per_second: Option<f64>,
    pub search_completed: bool,
    pub replication_completed: bool,
    pub observed_ranges_separated: bool,
    pub candidate_evidence: Vec<CandidateEvidence>,
    pub total_probes: usize,
    pub retained_probe_limit: usize,
    pub reserve_mib: f64,
    pub estimated_incremental_worker_mib: f64,
    pub probes: Vec<Probe>,
    pub counters: TuningCounters,
    pub adjustments: Vec<TuningAdjustment>,
}

pub struct OnlineAutotuner {
    pub active: usize,
    minimum: usize,
    maximum: usize,
    initial: usize,
    baseline_available_mib: f64,
    reserve_mib: f64,
    incremental_worker_mib: f64,
    candidates: Vec<usize>,
    next_candidate: usize,
    epoch_start: Instant,
    epoch_songs: usize,
    epoch_patches: usize,
    epoch_baseline_completed: usize,
    epoch_baseline_patches: usize,
    best: Option<(usize, f64)>,
    probes: Vec<Probe>,
    evidence: BTreeMap<usize, VecDeque<f64>>,
    visited: BTreeSet<usize>,
    adjustments: Vec<TuningAdjustment>,
    counters: TuningCounters,
    last_available_mib: f64,
    exploit_epochs: usize,
    reverse_sweep: bool,
    draining: bool,
}

fn candidate_schedule(minimum: usize, maximum: usize, initial: usize) -> Vec<usize> {
    let stride = (maximum - minimum).div_ceil(4).max(1);
    let mut all = BTreeSet::from([minimum, maximum, initial]);
    let mut count = minimum;
    while count < maximum {
        all.insert(count);
        count = count.saturating_add(stride);
    }
    // A bad intermediate measurement must never block candidates above it.
    let mut ordered = vec![initial];
    ordered.extend(all.into_iter().filter(|&workers| workers != initial));
    ordered
}

impl OnlineAutotuner {
    pub fn new(
        preferred_initial: usize, minimum: usize, maximum: usize,
        available_mib: Option<f64>, now: Instant,
    ) -> Result<Self> {
        if minimum == 0 || minimum > preferred_initial || preferred_initial > maximum || maximum > 64 {
            bail!("Online autotune requires 1 <= min <= initial <= max <= 64");
        }
        let available = available_mib.filter(|v| v.is_finite() && *v > 0.0)
            .ok_or_else(|| anyhow::anyhow!(
                "Online autotune requires reliable effective free-RAM telemetry; refusing unsafe admission"
            ))?;
        let reserve = RESERVE_MIN_MIB.max(available * 0.10);
        let slots = ((available - reserve) / WORKER_MEMORY_FLOOR_MIB).floor().max(0.0) as usize;
        if slots < minimum {
            bail!("Not enough safe available RAM for {minimum} workers (free {available:.0} MiB; reserve {reserve:.0} MiB)");
        }
        let actual_initial = preferred_initial.min(slots);
        Ok(Self {
            active: actual_initial, minimum, maximum, initial: actual_initial,
            baseline_available_mib: available, reserve_mib: reserve,
            incremental_worker_mib: WORKER_MEMORY_FLOOR_MIB,
            candidates: candidate_schedule(minimum, maximum, actual_initial),
            next_candidate: 0, epoch_start: now, epoch_songs: 0,
            epoch_patches: 0, epoch_baseline_completed: 0,
            epoch_baseline_patches: 0, best: None, probes: Vec::new(),
            evidence: BTreeMap::new(), visited: BTreeSet::new(),
            adjustments: Vec::new(), counters: TuningCounters::default(),
            last_available_mib: available, exploit_epochs: 0,
            reverse_sweep: false, draining: false,
        })
    }

    pub fn reserve_mib(&self) -> f64 { self.reserve_mib }

    pub fn permits_dispatch(&self, in_flight: usize) -> bool {
        !self.draining && in_flight < self.active
    }

    pub fn draining(&self) -> bool { self.draining }

    /// Called only after all previously admitted jobs have completed. This
    /// avoids attributing old-capacity work to the next throughput probe.
    pub fn settle(&mut self, completed: usize, patches: usize, now: Instant) {
        self.draining = false;
        self.reset_epoch(now, completed, patches);
    }

    pub fn observe(
        &mut self, completed: usize, total_patches: usize,
        available_mib: Option<f64>, remaining_hint: usize,
        now: Instant,
    ) -> Result<()> {
        let available = available_mib.filter(|v| v.is_finite() && *v >= 0.0)
            .ok_or_else(|| anyhow::anyhow!(
                "Online autotune lost effective free-RAM telemetry; stop new admission"
            ))?;
        self.last_available_mib = available;
        if available <= self.reserve_mib {
            bail!(
                "Online autotune RAM safety stop: free {available:.0} MiB <= reserve {:.0} MiB",
                self.reserve_mib
            );
        }
        // Increase the cost estimate when observed process/system memory growth
        // suggests higher per-worker usage. Never lower it on the basis of
        // noisy system-wide measurements.
        let observed = (self.baseline_available_mib - available).max(0.0)
            / self.active.max(1) as f64;
        self.incremental_worker_mib = self.incremental_worker_mib.max(observed);
        let headroom = available - self.reserve_mib;
        if headroom < self.incremental_worker_mib {
            if self.active <= self.minimum {
                bail!("Online autotune RAM margin insufficient at minimum concurrency");
            }
            self.change(self.active - 1, completed, "memory pressure: reduce admissions");
            self.counters.memory_pressure_reductions += 1;
            self.reset_epoch(now, completed, total_patches);
            return Ok(());
        }

        if self.draining {
            // Maintain the RAM governor while in-flight old-capacity work
            // finishes, but do not score that work under the new capacity.
            return Ok(());
        }
        // Account for work completed in each measurement epoch. Call once per
        // persisted completion, including completion that was unsuccessful.
        // Diagnostics totals only advance on successful analysis.
        self.epoch_songs = completed.saturating_sub(self.epoch_baseline_completed);
        // Patches are the shared EffNet work unit for all selected heads.
        self.epoch_patches = total_patches.saturating_sub(self.epoch_baseline_patches);
        let elapsed = now.saturating_duration_since(self.epoch_start);
        if self.epoch_songs < MIN_EPOCH_SONGS || elapsed < MIN_EPOCH_DURATION {
            return Ok(());
        }
        let seconds = elapsed.as_secs_f64();
        let measure = self.epoch_patches as f64 / seconds;
        if !measure.is_finite() || measure <= 0.0 {
            self.reset_epoch(now, completed, total_patches);
            return Ok(());
        }
        if self.probes.len() == MAX_RETAINED_PROBES {
            self.probes.remove(0);
        }
        self.probes.push(Probe {
            workers: self.active,
            completed_songs: self.epoch_songs,
            patches: self.epoch_patches,
            elapsed_seconds: seconds,
            patches_per_second: measure,
            songs_per_minute: 60.0 * self.epoch_songs as f64 / seconds,
        });
        self.counters.probes += 1;
        self.visited.insert(self.active);
        let entry = self.evidence.entry(self.active).or_default();
        if entry.len() == RECENT_SAMPLES_PER_WORKER {
            entry.pop_front();
        }
        entry.push_back(measure);
        self.select_best_observed();
        self.reset_epoch(now, completed, total_patches);
        // Preserve enough outstanding work for a useful epoch; otherwise use
        // the best already observed configuration rather than thrash at the end.
        if remaining_hint < MIN_EPOCH_SONGS {
            self.counters.insufficient_work_holds += 1;
            if let Some((best, _)) = self.best {
                self.change(best, completed, "end of scan: best sampled throughput");
            }
            return Ok(());
        }
        // Run a reverse-ordered second sweep immediately after the first
        // complete coarse pass. This gives comparable candidates two windows
        // before ordinary exploitation, mitigating systematic time drift.
        // Later revisit the entire safe set only on a bounded cadence.
        if self.next_candidate >= self.candidates.len() {
            self.counters.completed_coarse_sweeps += 1;
            let second_pass = self.counters.completed_coarse_sweeps == 1
                && self.candidates.len() > 1;
            if second_pass {
                self.reverse_sweep = true;
                self.next_candidate = 0;
            } else {
                self.exploit_epochs += 1;
                if self.exploit_epochs.is_multiple_of(4) {
                    self.reverse_sweep = !self.reverse_sweep;
                    self.next_candidate = 0;
                } else {
                    if let Some((best, _)) = self.best {
                        self.change(best, completed, "exploit best measured throughput");
                    }
                    return Ok(());
                }
            }
        }
        // A bad intermediate probe must not suppress higher worker counts.
        while self.next_candidate < self.candidates.len() {
            let index = if self.reverse_sweep {
                self.candidates.len() - self.next_candidate - 1
            } else { self.next_candidate };
            let target = self.candidates[index];
            self.next_candidate += 1;
            if target == self.active { continue; }
            let extra = target.saturating_sub(self.active);
            if extra > 0 && (extra as f64 * self.incremental_worker_mib) > headroom {
                self.counters.memory_gate_holds += 1;
                continue;
            }
            self.change(target, completed, "non-monotonic coarse exploration");
            return Ok(());
        }
        if let Some((best, _)) = self.best {
            self.change(best, completed, "exploit best measured throughput");
        }
        Ok(())
    }

    /// Retained samples are bounded; ranking uses the rolling median, not the
    /// highest single sample. Once the initial coarse pass is complete, an
    /// unreplicated challenger cannot displace the incumbent.
    fn select_best_observed(&mut self) {
        let initial_pass = self.counters.probes <= self.candidates.len();
        let mut selected = self.best.and_then(|(workers, _)| {
            self.evidence.get(&workers).and_then(|values| {
                median(values).map(|score| (workers, score))
            })
        });
        for (&workers, scores) in &self.evidence {
            if !initial_pass && scores.len() < 2
                && selected.is_some_and(|(current, _)| current != workers) {
                continue;
            }
            if let Some(score) = median(scores) {
                if selected.is_none_or(|(_, best)| score > best * (1.0 + IMPROVEMENT_MARGIN)) {
                    selected = Some((workers, score));
                }
            }
        }
        self.best = selected;
    }

    fn candidate_evidence(&self) -> Vec<CandidateEvidence> {
        self.evidence.iter().filter_map(|(&workers, scores)| {
            let midpoint = median(scores)?;
            Some(CandidateEvidence {
                workers,
                samples: scores.len(),
                median_patches_per_second: midpoint,
                minimum_patches_per_second: scores.iter().copied()
                    .fold(f64::INFINITY, f64::min),
                maximum_patches_per_second: scores.iter().copied()
                    .fold(f64::NEG_INFINITY, f64::max),
            })
        }).collect()
    }

    fn reset_epoch(&mut self, now: Instant, completed: usize, patches: usize) {
        self.epoch_start = now;
        self.epoch_songs = 0;
        self.epoch_patches = 0;
        self.epoch_baseline_completed = completed;
        self.epoch_baseline_patches = patches;
    }

    fn change(&mut self, target: usize, completed: usize, reason: &str) {
        let target = target.clamp(self.minimum, self.maximum);
        if target == self.active { return; }
        let from = self.active;
        if target > from { self.counters.expansions += 1; }
        else { self.counters.reductions += 1; }
        self.active = target;
        self.draining = true;
        eprintln!("ONLINE AUTOTUNE {from} -> {target} after {completed} songs: {reason}");
        self.adjustments.push(TuningAdjustment {
            after_completed_songs: completed, from_workers: from,
            to_workers: target, reason: reason.to_owned(),
            available_ram_mib: self.last_available_mib,
        });
    }

    pub fn into_diagnostics(self) -> TuningDiagnostics {
        let candidates = self.candidate_evidence();
        let replicated = self.candidates.iter().all(|worker|
            self.evidence.get(worker).is_some_and(|samples| samples.len() >= 2));
        let separated = replicated && self.best.is_some_and(|(best, _)| {
            let winner = candidates.iter().find(|c| c.workers == best);
            winner.is_some_and(|w| candidates.iter()
                .filter(|c| c.workers != best)
                .all(|other| w.minimum_patches_per_second >
                    other.maximum_patches_per_second * (1.0 + IMPROVEMENT_MARGIN)))
        });
        TuningDiagnostics {
            strategy: "bounded-nonmonotonic-coarse-explore",
            initial_workers: self.initial, final_workers: self.active,
            best_tested_workers: self.best.map(|p| p.0),
            best_observed_patches_per_second: self.best.map(|p| p.1),
            search_completed: self.candidates.iter().all(|c| self.visited.contains(c)),
            replication_completed: replicated,
            observed_ranges_separated: separated,
            candidate_evidence: candidates,
            total_probes: self.counters.probes,
            retained_probe_limit: MAX_RETAINED_PROBES,
            reserve_mib: self.reserve_mib,
            estimated_incremental_worker_mib: self.incremental_worker_mib,
            probes: self.probes, counters: self.counters, adjustments: self.adjustments,
        }
    }
}

/// Median of at most eight finite nonnegative samples; no additional
/// dependencies or unbounded sample retention.
fn median(values: &VecDeque<f64>) -> Option<f64> {
    if values.is_empty() { return None; }
    let mut ordered: Vec<f64> = values.iter().copied().collect();
    ordered.sort_by(f64::total_cmp);
    let at = ordered.len() / 2;
    Some(if ordered.len().is_multiple_of(2) {
        (ordered[at - 1] + ordered[at]) / 2.0
    } else { ordered[at] })
}

#[cfg(test)]
mod tests {
    use super::*;
    fn run_epoch(t: &mut OnlineAutotuner, total: &mut usize, patches: &mut usize,
        count: usize, elapsed: u64, remaining: usize, now: &mut Instant) {
        *total += count;
        *patches += count * 5;
        *now += Duration::from_secs(elapsed);
        t.observe(*total, *patches, Some(4000.0), remaining, *now).unwrap();
        if t.draining() {
            // A real coordinator must first drain all old-capacity jobs.
            t.settle(*total, *patches, *now);
        }
    }

    #[test]
    fn nonmonotonic_valley_does_not_stop_exploration() {
        let mut now = Instant::now();
        let mut t = OnlineAutotuner::new(6, 6, 12, Some(8000.0), now).unwrap();
        let (mut done, mut patches) = (0, 0);
        let mut tried = Vec::new();
        for elapsed in [18, 20, 28, 12] {
            tried.push(t.active);
            run_epoch(&mut t, &mut done, &mut patches, 8, elapsed, 120, &mut now);
        }
        // Six/eight/ten/twelve are visited regardless of their scores.
        assert!(tried.contains(&6));
        assert!(tried.contains(&8));
        assert!(tried.contains(&10));
        assert!(tried.contains(&12));
        let result = t.into_diagnostics();
        assert_eq!(result.best_tested_workers, Some(12));
        assert!(result.search_completed);
        assert!(!result.replication_completed);
        assert!(!result.observed_ranges_separated);
        assert!(result.probes[2].patches_per_second < result.probes[0].patches_per_second);
    }

    #[test]
    fn second_sweep_reverses_order_without_stopping_at_local_trough() {
        let mut now = Instant::now();
        let mut t = OnlineAutotuner::new(6, 6, 12, Some(8000.0), now).unwrap();
        let (mut done, mut patches) = (0, 0);
        let mut seen = Vec::new();
        for duration in [18, 19, 28, 12, 13, 28, 19, 18] {
            seen.push(t.active);
            run_epoch(&mut t, &mut done, &mut patches, 8, duration, 150, &mut now);
        }
        assert_eq!(seen, [6, 8, 10, 12, 10, 8, 6, 12]);
        let diag = t.into_diagnostics();
        assert!(diag.replication_completed);
        assert!(diag.search_completed);
        assert!(diag.counters.completed_coarse_sweeps >= 2);
    }

    #[test]
    fn drain_boundary_prevents_cross_capacity_admission() {
        let now = Instant::now();
        let mut controller = OnlineAutotuner::new(6, 6, 12, Some(8000.0), now).unwrap();
        controller.observe(
            8, 40, Some(7500.0), 100, now + Duration::from_secs(20)
        ).unwrap();
        assert!(controller.draining());
        assert!(!controller.permits_dispatch(0));
        let next = controller.active;
        controller.settle(8, 40, now + Duration::from_secs(23));
        assert!(!controller.draining());
        assert!(controller.permits_dispatch(0));
        controller.observe(
            16, 80, Some(7500.0), 100, now + Duration::from_secs(40)
        ).unwrap();
        let diag = controller.into_diagnostics();
        assert_eq!(diag.probes.len(), 2);
        assert_eq!(diag.probes[0].workers, 6);
        assert_eq!(diag.probes[1].workers, next);
        assert_eq!(diag.probes[1].completed_songs, 8);
        assert_eq!(diag.probes[1].patches, 40);
    }

    #[test]
    fn ranking_uses_repeated_medians_and_rejects_single_post_pass_outlier() {
        let now = Instant::now();
        let mut tuner = OnlineAutotuner::new(6, 6, 12, Some(8000.0), now).unwrap();
        for (worker, speeds) in [(6, vec![6.0, 6.2]), (8, vec![5.0, 5.3]),
                                 (10, vec![4.0, 4.5]), (12, vec![8.0, 8.2])] {
            tuner.evidence.insert(worker, VecDeque::from(speeds));
            tuner.visited.insert(worker);
        }
        tuner.counters.probes = 8;
        tuner.select_best_observed();
        assert_eq!(tuner.best.map(|v| v.0), Some(12));
        let result = tuner.into_diagnostics();
        assert!(result.replication_completed);
        assert!(result.observed_ranges_separated);
        assert_eq!(result.candidate_evidence.len(), 4);
        assert!((result.best_observed_patches_per_second.unwrap() - 8.1).abs() < 1e-9);

        let mut second = OnlineAutotuner::new(6, 6, 12, Some(8000.0), now).unwrap();
        second.best = Some((12, 8.0));
        second.evidence.insert(12, VecDeque::from(vec![8.0, 8.2]));
        second.evidence.insert(10, VecDeque::from(vec![18.0]));
        second.counters.probes = 9;
        second.select_best_observed();
        assert_eq!(second.best.map(|v| v.0), Some(12),
            "one anomalously fast single probe must not displace the incumbent");
    }

    #[test]
    fn retained_probe_samples_are_bounded_for_library_scans() {
        let now = Instant::now();
        let mut tuner = OnlineAutotuner::new(1, 1, 1, Some(4000.0), now).unwrap();
        let mut total = 0;
        let mut patches = 0;
        for i in 1..=300 {
            total += 8;
            patches += 40;
            tuner.observe(total, patches, Some(3500.0), 10000,
                now + Duration::from_secs(i * 20)).unwrap();
        }
        let diagnostics = tuner.into_diagnostics();
        assert_eq!(diagnostics.total_probes, 300);
        assert_eq!(diagnostics.probes.len(), MAX_RETAINED_PROBES);
        assert_eq!(diagnostics.candidate_evidence[0].samples, RECENT_SAMPLES_PER_WORKER);
    }

    #[test]
    fn ram_preflight_and_runtime_pressure_fail_closed() {
        let now = Instant::now();
        assert!(OnlineAutotuner::new(4, 1, 8, None, now).is_err());
        assert!(OnlineAutotuner::new(4, 1, 8, Some(400.0), now).is_err());
        let mut t = OnlineAutotuner::new(8, 1, 16, Some(1800.0), now).unwrap();
        assert!(t.active < 8);
        assert!(t.observe(1, 5, None, 100, now).is_err());
        assert!(t.observe(1, 5, Some(100.0), 100, now).is_err());
    }

    #[test]
    fn short_scans_do_not_claim_an_optimum() {
        let now = Instant::now();
        let mut t = OnlineAutotuner::new(2, 1, 8, Some(5000.0), now).unwrap();
        t.observe(3, 15, Some(4500.0), 0, now + Duration::from_secs(20)).unwrap();
        let diag = t.into_diagnostics();
        assert!(diag.best_tested_workers.is_none());
        assert!(!diag.search_completed);
    }

    #[test]
    fn candidate_schedule_covers_beyond_a_bad_local_peak() {
        assert_eq!(candidate_schedule(6, 12, 6), [6, 8, 10, 12]);
        let plan = candidate_schedule(1, 16, 8);
        assert!(plan.contains(&16));
        assert_eq!(plan[0], 8);
    }
}
