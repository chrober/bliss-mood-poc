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
const MAX_RETAINED_ADJUSTMENTS: usize = 256;
const RECENT_SAMPLES_PER_WORKER: usize = 8;

#[derive(Clone, Debug, Serialize)]
pub struct Probe {
    pub workers: usize,
    pub completed_songs: usize,
    pub patches: usize,
    pub elapsed_seconds: f64,
    pub patches_per_second: f64,
    pub songs_per_minute: f64,
    /// Only work not yet dispatched; in-flight jobs are intentionally not
    /// counted as new exploration opportunities.
    pub remaining_undispatched_songs: usize,
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
    pub exploration_budget_holds: usize,
    pub unsafe_best_holds: usize,
    pub local_refinement_probes: usize,
}

/// The most recent work-horizon decision, for diagnosing incomplete scans
/// without exposing track names, audio or model output.
#[derive(Clone, Debug, Serialize)]
pub struct ExplorationBudgetSample {
    pub phase: &'static str,
    pub remaining_undispatched_songs: usize,
    pub unmeasured_candidate_windows: usize,
    pub estimated_songs_per_window: usize,
    pub reserved_exploitation_songs: usize,
    pub required_songs: usize,
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
    /// Drain duration until all jobs admitted at the previous capacity finish.
    /// This includes productive in-flight work; it is NOT pure idle overhead.
    pub drain_seconds: Option<f64>,
    pub drained_songs: Option<usize>,
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
    pub last_exploration_budget: Option<ExplorationBudgetSample>,
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
    /// A RAM-gated candidate can be deferred once to permit safer intermediate
    /// steps; this set ensures repeated failed admissions cannot spin forever.
    deferred_for_ram: BTreeSet<usize>,
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
    sweep_in_progress: bool,
    draining: bool,
    drain_started_at: Option<Instant>,
    drain_started_completed: usize,
    // Once the remaining scan cannot amortize another sweep, do not restart
    // exploration just because a later epoch completed.
    exploration_budget_exhausted: bool,
    typical_probe_songs: usize,
    last_exploration_budget: Option<ExplorationBudgetSample>,
    refinement_started: bool,
    refinement_queue: VecDeque<usize>,
    refinement_active: Option<usize>,
}

fn candidate_schedule(minimum: usize, maximum: usize, initial: usize) -> Vec<usize> {
    let stride = (maximum - minimum).div_ceil(4).max(1);
    let mut all = BTreeSet::from([minimum, maximum, initial]);
    let mut count = minimum;
    while count < maximum {
        all.insert(count);
        count = count.saturating_add(stride);
    }
    // Measure both ends of the feasible concurrency range early. Otherwise a
    // short scan can consume most of its exploration budget walking through
    // slow intermediate counts before ever checking the opposite endpoint.
    // This is an information-ordering heuristic, not a monotonicity claim:
    // all interior candidates remain in the first sweep.
    let mut ordered = vec![initial];
    let endpoints = if initial.abs_diff(maximum) >= initial.abs_diff(minimum) {
        [maximum, minimum]
    } else {
        [minimum, maximum]
    };
    for endpoint in endpoints {
        if endpoint != initial && !ordered.contains(&endpoint) {
            ordered.push(endpoint);
        }
    }
    let interior: Vec<_> = all.into_iter()
        .filter(|worker| !ordered.contains(worker)).collect();
    ordered.extend(interior);
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
            next_candidate: 0, deferred_for_ram: BTreeSet::new(), epoch_start: now, epoch_songs: 0,
            epoch_patches: 0, epoch_baseline_completed: 0,
            epoch_baseline_patches: 0, best: None, probes: Vec::new(),
            evidence: BTreeMap::new(), visited: BTreeSet::new(),
            adjustments: Vec::new(), counters: TuningCounters::default(),
            last_available_mib: available, exploit_epochs: 0,
            reverse_sweep: false, sweep_in_progress: true, draining: false,
            drain_started_at: None, drain_started_completed: 0,
            exploration_budget_exhausted: false,
            typical_probe_songs: MIN_EPOCH_SONGS,
            last_exploration_budget: None,
            refinement_started: false,
            refinement_queue: VecDeque::new(), refinement_active: None,
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
        if let Some(started) = self.drain_started_at.take() {
            if let Some(last) = self.adjustments.last_mut() {
                last.drain_seconds = Some(now.saturating_duration_since(started).as_secs_f64());
                last.drained_songs =
                    Some(completed.saturating_sub(self.drain_started_completed));
            }
        }
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
            self.reset_epoch(now, completed, total_patches);
            self.change(self.active - 1, completed, "memory pressure: reduce admissions");
            self.counters.memory_pressure_reductions += 1;
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
            remaining_undispatched_songs: remaining_hint,
        });
        self.counters.probes += 1;
        if self.refinement_active == Some(self.active) {
            self.counters.local_refinement_probes += 1;
        }
        self.visited.insert(self.active);
        let entry = self.evidence.entry(self.active).or_default();
        if entry.len() == RECENT_SAMPLES_PER_WORKER {
            entry.pop_front();
        }
        entry.push_back(measure);
        self.select_best_observed();
        // Use the actual observed work per probe (not a fixed, host-specific
        // count) to budget candidate windows on heterogeneous hardware.
        self.typical_probe_songs = self.epoch_songs.max(MIN_EPOCH_SONGS);
        self.reset_epoch(now, completed, total_patches);
        // Preserve enough outstanding work for a useful epoch; otherwise use
        // the best already observed configuration rather than thrash at the end.
        if remaining_hint < MIN_EPOCH_SONGS {
            self.counters.insufficient_work_holds += 1;
            self.exploit_safe_best(completed, headroom, "end of scan: best sampled throughput");
            return Ok(());
        }
        if self.exploration_budget_exhausted {
            self.exploit_safe_best(completed, headroom, "end of scan: insufficient search payback");
            return Ok(());
        }
        // One *completed* first sweep is more important than replicating a
        // candidate: the latter cannot rule out an unvisited faster setting.
        // Previously we charged the already measured incumbent again and
        // required TWO epochs for every candidate before even testing a
        // challenger. On real short scans this locked out every alternative.
        //
        // Discovery: reserve one observed-sized epoch for each still UNTESTED
        // candidate, plus one for exploitation. No worker count is privileged.
        // Replication/refinement: optional, charge the still outstanding
        // measurement windows before attempting further exploration.
        // Window size is measured, not tuned for a particular machine.
        if self.sweep_in_progress && self.next_candidate >= self.candidates.len() {
            self.counters.completed_coarse_sweeps += 1;
            self.sweep_in_progress = false;
        }
        let unvisited = self.candidates.iter()
            .filter(|&&worker| !self.visited.contains(&worker)).count();
        let (phase, pending_windows) = if self.refinement_active.is_some()
            || !self.refinement_queue.is_empty() {
            let current = self.refinement_active.map(|worker|
                self.evidence.get(&worker)
                    .map_or(2, |samples| 2_usize.saturating_sub(samples.len())))
                .unwrap_or(0);
            ("local-refinement", current + self.refinement_queue.len().saturating_mul(2))
        } else if unvisited > 0 {
            ("first-coarse-discovery", unvisited)
        } else if self.candidates.len() <= 1 {
            ("single-candidate", 0)
        } else if self.next_candidate >= self.candidates.len() {
            // The first complete sweep has finished. Its second reverse pass
            // is valuable for noise rejection, but NEVER a prerequisite for
            // testing every coarse candidate once.
            ("replication", self.candidates.iter().filter(|&&worker|
                self.evidence.get(&worker).is_none_or(|samples| samples.len() < 2)
            ).count())
        } else {
            ("replication", self.candidates.len() - self.next_candidate)
        };
        let reserve_songs = self.typical_probe_songs;
        let required_songs = reserve_songs.saturating_mul(pending_windows.saturating_add(1));
        self.last_exploration_budget = Some(ExplorationBudgetSample {
            phase,
            remaining_undispatched_songs: remaining_hint,
            unmeasured_candidate_windows: pending_windows,
            estimated_songs_per_window: self.typical_probe_songs,
            reserved_exploitation_songs: reserve_songs,
            required_songs,
        });
        if pending_windows > 0 && remaining_hint < required_songs {
            self.exploration_budget_exhausted = true;
            self.counters.exploration_budget_holds += 1;
            self.exploit_safe_best(completed, headroom,
                "stop exploration: insufficient remaining scan to repay probes");
            return Ok(());
        }
        // Complete bounded local refinement only after both coarse sweeps.
        // High peaks BETWEEN sampled worker counts would otherwise be missed.
        if self.refinement_active.is_some() || !self.refinement_queue.is_empty() {
            self.advance_refinement(completed, headroom);
            return Ok(());
        }
        // Run a reverse-ordered second sweep immediately after the first
        // complete coarse pass. This gives comparable candidates two windows
        // before ordinary exploitation, mitigating systematic time drift.
        // Later revisit the entire safe set only on a bounded cadence.
        if self.next_candidate >= self.candidates.len() {
            let second_pass = self.counters.completed_coarse_sweeps == 1
                && self.candidates.len() > 1;
            if !second_pass && self.counters.completed_coarse_sweeps == 2
                && !self.refinement_started {
                self.refinement_started = true;
                self.plan_local_refinement();
                if !self.refinement_queue.is_empty() {
                    self.advance_refinement(completed, headroom);
                    return Ok(());
                }
            }
            if second_pass {
                self.reverse_sweep = true;
                self.next_candidate = 0;
                self.sweep_in_progress = true;
            } else {
                self.exploit_epochs += 1;
                if self.exploit_epochs.is_multiple_of(4) {
                    self.reverse_sweep = !self.reverse_sweep;
                    self.next_candidate = 0;
                    self.sweep_in_progress = true;
                } else {
                    self.exploit_safe_best(completed, headroom, "exploit best safe measured throughput");
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
            if target == self.active {
                // The reversed sweep's first candidate is often the current
                // one; give it a second genuine window before moving away.
                if self.reverse_sweep && self.evidence.get(&target)
                    .is_none_or(|scores| scores.len() < 2) {
                    return Ok(());
                }
                continue;
            }
            let extra = target.saturating_sub(self.active);
            if extra > 0 && (extra as f64 * self.incremental_worker_mib) > headroom {
                self.counters.memory_gate_holds += 1;
                // When the opposite endpoint is not yet RAM-admissible, try
                // smaller pending steps first, then recheck that same endpoint
                // from the newly admitted concurrency. Preserve all original
                // candidates and never retry a deferred worker more than once
                // in this first sweep. No memory reservation is bypassed.
                if self.sweep_in_progress && !self.reverse_sweep
                    && self.next_candidate < self.candidates.len()
                    && self.deferred_for_ram.insert(target)
                {
                    self.candidates.remove(index);
                    self.candidates.push(target);
                    self.next_candidate -= 1;
                }
                continue;
            }
            self.change(target, completed, "non-monotonic coarse exploration");
            return Ok(());
        }
        self.exploit_safe_best(completed, headroom, "exploit best safe measured throughput");
        Ok(())
    }

    /// Search only the immediate missing neighbors of the best replicated
    /// coarse setting. It is independent of monotonic assumptions, bounded
    /// to two candidates and never blocks the initial sweep to the maximum.
    fn plan_local_refinement(&mut self) {
        if let Some((center, _)) = self.best {
            for worker in [center.checked_sub(1), center.checked_add(1)].into_iter().flatten() {
                if (self.minimum..=self.maximum).contains(&worker)
                    && !self.visited.contains(&worker) {
                    self.refinement_queue.push_back(worker);
                }
            }
        }
    }

    fn advance_refinement(&mut self, completed: usize, headroom: f64) {
        if let Some(worker) = self.refinement_active {
            // The single first window cannot displace a replicated winner;
            // require a second real epoch before evaluating the challenger.
            if self.evidence.get(&worker).is_none_or(|samples| samples.len() < 2) {
                return;
            }
            self.refinement_active = None;
        }
        while let Some(worker) = self.refinement_queue.pop_front() {
            let extra = worker.saturating_sub(self.active);
            if (extra as f64 * self.incremental_worker_mib) > headroom {
                self.counters.memory_gate_holds += 1;
                continue;
            }
            self.refinement_active = Some(worker);
            self.change(worker, completed, "local refinement around replicated coarse winner");
            return;
        }
        self.exploit_safe_best(completed, headroom, "exploit after local refinement");
    }

    /// The best historical setting may no longer be RAM-admissible after a
    /// change in memory pressure. Even exploitation must honor the same
    /// additional-worker reservation as exploratory increases.
    fn exploit_safe_best(&mut self, completed: usize, headroom: f64, reason: &str) {
        let mut selected = None;
        for (&worker, samples) in &self.evidence {
            let extra = worker.saturating_sub(self.active);
            if (extra as f64 * self.incremental_worker_mib) > headroom {
                continue;
            }
            if let Some(score) = median(samples) {
                if selected.is_none_or(|(_, highest)| score > highest) {
                    selected = Some((worker, score));
                }
            }
        }
        if let Some((target, _)) = selected {
            if self.best.is_some_and(|(best, _)| best != target) {
                self.counters.unsafe_best_holds += 1;
            }
            self.change(target, completed, reason);
        } else if self.best.is_some_and(|(best, _)| best > self.active) {
            self.counters.unsafe_best_holds += 1;
        }
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
        self.drain_started_at = Some(self.epoch_start);
        self.drain_started_completed = completed;
        eprintln!("ONLINE AUTOTUNE {from} -> {target} after {completed} songs: {reason}");
        if self.adjustments.len() == MAX_RETAINED_ADJUSTMENTS {
            self.adjustments.remove(0);
        }
        self.adjustments.push(TuningAdjustment {
            after_completed_songs: completed, from_workers: from,
            to_workers: target, reason: reason.to_owned(),
            available_ram_mib: self.last_available_mib,
            drain_seconds: None,
            drained_songs: None,
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
            last_exploration_budget: self.last_exploration_budget,
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
        // Sufficient effective RAM for a direct jump to the far endpoint.
        let mut t = OnlineAutotuner::new(6, 6, 12, Some(5000.0), now).unwrap();
        let (mut done, mut patches) = (0, 0);
        let mut tried = Vec::new();
        for elapsed in [18, 12, 28, 20] {
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
        let mut t = OnlineAutotuner::new(6, 6, 12, Some(5000.0), now).unwrap();
        let (mut done, mut patches) = (0, 0);
        let mut seen = Vec::new();
        for duration in [18, 19, 28, 12, 13, 28, 19, 18] {
            seen.push(t.active);
            run_epoch(&mut t, &mut done, &mut patches, 8, duration, 150, &mut now);
        }
        assert_eq!(seen, [6, 12, 8, 10, 10, 8, 12, 6]);
        let diag = t.into_diagnostics();
        assert!(diag.replication_completed);
        assert!(diag.search_completed);
        assert!(diag.counters.completed_coarse_sweeps >= 2);
    }

    #[test]
    fn far_boundary_is_not_forced_through_ram_gate() {
        let now = Instant::now();
        let mut t = OnlineAutotuner::new(6, 6, 12, Some(8000.0), now).unwrap();
        // A sudden loss of free RAM makes a direct 6 -> 12 expansion unsafe
        // under the already established conservative per-worker estimate.
        t.observe(8, 400, Some(4000.0), 120,
            now + Duration::from_secs(20)).unwrap();
        assert_eq!(t.active, 8);
        assert_eq!(t.counters.memory_gate_holds, 1);
        assert!(t.draining());
        assert!(!t.visited.contains(&12));
        t.settle(8, 400, now + Duration::from_secs(21));
        t.observe(16, 800, Some(4000.0), 120,
            now + Duration::from_secs(40)).unwrap();
        assert_eq!(t.active, 10);
        assert_eq!(t.counters.memory_gate_holds, 1);
        // The original large 6 -> 12 jump was refused; from 10 the same
        // final destination is checked AGAIN, with a smaller increment.
        t.settle(16, 800, now + Duration::from_secs(41));
        t.observe(24, 1200, Some(4000.0), 120,
            now + Duration::from_secs(60)).unwrap();
        assert_eq!(t.active, 12);
        assert_eq!(t.counters.memory_gate_holds, 1);
        assert!(t.draining());
    }

    #[test]
    fn permanently_ram_blocked_candidates_do_not_cycle_forever() {
        let now = Instant::now();
        let mut t = OnlineAutotuner::new(2, 2, 8, Some(5000.0), now).unwrap();
        // All larger settings are RAM-gated by the large observed pressure.
        // Deferrals must be bounded; the coordinator must remain dispatchable.
        t.observe(8, 800, Some(2200.0), 200,
            now + Duration::from_secs(20)).unwrap();
        assert_eq!(t.active, 2);
        assert!(!t.draining());
        assert!(t.counters.memory_gate_holds >= 1);
        let diag = t.into_diagnostics();
        assert!(!diag.search_completed);
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

    // Pure deterministic simulations use the same admission/observation API
    // as production. 20 songs per epoch keeps every duration >=12s even
    // for 88 songs/min; no audio files, wall-clock sleeps or fixed host count.
    fn simulate_rate(t: &mut OnlineAutotuner, total: &mut usize,
        patches: &mut usize, now: &mut Instant, songs_per_min: f64,
        remaining: usize, free_mib: f64) -> f64 {
        const SONGS: usize = 20;
        let seconds = SONGS as f64 * 60.0 / songs_per_min;
        *total += SONGS;
        *patches += SONGS * 5;
        *now += Duration::from_secs_f64(seconds);
        t.observe(*total, *patches, Some(free_mib), remaining, *now).unwrap();
        if t.draining() { t.settle(*total, *patches, *now); }
        seconds
    }

    #[test]
    fn benchmark_curve_reaches_twelve_past_both_local_declines() {
        let mut now = Instant::now();
        let mut tuner = OnlineAutotuner::new(6, 6, 12, Some(8000.0), now).unwrap();
        let (mut songs, mut patches) = (0, 0);
        let rates = [(6, 70.98), (12, 88.17), (8, 70.42), (10, 63.75)];
        for (worker, rate) in rates {
            assert_eq!(tuner.active, worker);
            let remaining = 400 - (songs + 20);
            simulate_rate(&mut tuner, &mut songs, &mut patches,
                &mut now, rate, remaining, 6500.0);
        }
        let diagnostics = tuner.into_diagnostics();
        assert_eq!(diagnostics.best_tested_workers, Some(12));
        assert!(diagnostics.search_completed);
        assert!(!diagnostics.replication_completed);
        assert_eq!(diagnostics.probes.len(), 4);
        // This synthetic winner is conditional on RAM and horizon, not
        // a universal optimum for a Ryzen or any other machine.
        assert!(diagnostics.probes[1].songs_per_minute
            > diagnostics.probes[0].songs_per_minute);
        assert!(diagnostics.probes[3].songs_per_minute
            < diagnostics.probes[2].songs_per_minute);
    }

    #[test]
    fn monotone_up_down_and_flat_noise_choose_safely() {
        for (curve, expected) in [
            ([55.0, 85.0, 65.0, 75.0], 12),
            ([85.0, 55.0, 75.0, 65.0], 6),
            ([70.0, 70.7, 70.5, 69.9], 6),
        ] {
            let mut now = Instant::now();
            let mut t = OnlineAutotuner::new(6, 6, 12, Some(8000.0), now).unwrap();
            let (mut songs, mut patches) = (0, 0);
            for rate in curve {
                let remaining = 400 - (songs + 20);
                simulate_rate(&mut t, &mut songs, &mut patches,
                    &mut now, rate, remaining, 6500.0);
            }
            assert_eq!(t.best.unwrap().0, expected);
            assert!(t.visited.contains(&12));
        }
    }

    #[test]
    fn narrow_peak_between_coarse_candidates_is_refined_after_two_sweeps() {
        let mut now = Instant::now();
        let mut t = OnlineAutotuner::new(6, 6, 12, Some(9000.0), now).unwrap();
        let (mut completed, mut patches) = (0, 0);
        for (workers, rate) in [
            (6, 65.0), (12, 78.0), (8, 73.0), (10, 85.0),
            (10, 85.0), (8, 73.0), (12, 78.0), (6, 65.0),
        ] {
            assert_eq!(t.active, workers);
            let remaining = 800 - (completed + 20);
            simulate_rate(&mut t, &mut completed, &mut patches, &mut now,
                rate, remaining, 7600.0);
        }
        assert_eq!(t.best.unwrap().0, 10);
        // With a long enough remaining scan the algorithm investigates
        // unsampled neighbors of 10 after sweeping all coarse candidates.
        assert_eq!(t.active, 9);
        for (worker, rate) in [(9, 77.0), (9, 77.0), (11, 94.0), (11, 94.0)] {
            assert_eq!(t.active, worker);
            let remaining = 800 - (completed + 20);
            simulate_rate(&mut t, &mut completed, &mut patches, &mut now,
                rate, remaining, 7600.0);
        }
        assert_eq!(t.best.unwrap().0, 11);
        assert!(t.visited.contains(&12));
        assert!(t.counters.local_refinement_probes >= 4);
    }

    #[test]
    fn short_horizon_stops_search_but_long_horizon_can_amortize_it() {
        let mut now = Instant::now();
        let mut short = OnlineAutotuner::new(6, 6, 12, Some(8000.0), now).unwrap();
        let (mut done, mut patches) = (0, 0);
        simulate_rate(&mut short, &mut done, &mut patches,
            &mut now, 70.98, 20, 6500.0);
        assert_eq!(short.active, 6);
        assert!(short.exploration_budget_exhausted);
        assert_eq!(short.counters.exploration_budget_holds, 1);
        assert!(!short.draining());
        let mut long_time = Instant::now();
        let mut long = OnlineAutotuner::new(6, 6, 12, Some(8000.0), long_time).unwrap();
        let (mut completed, mut p) = (0, 0);
        let mut scan_seconds = 0.0;
        for rate in [70.98, 88.17, 70.42, 63.75,
                     63.75, 70.42, 88.17, 70.98] {
            let remaining = 400 - (completed + 20);
            scan_seconds += simulate_rate(&mut long, &mut completed,
                &mut p, &mut long_time, rate, remaining, 6500.0);
        }
        assert!(long.counters.completed_coarse_sweeps >= 2);
        assert_eq!(long.best.unwrap().0, 12);
        long.exploit_safe_best(completed, 5000.0, "synthetic exploitation");
        assert_eq!(long.active, 12);
        // Illustrative whole-scan model with 2 s switching overhead, not
        // empirical wall-time. Tuning can beat fixed 6 on this *long*
        // synthetic scan yet still lose to a prescient fixed-12 oracle.
        let hypothetical_seconds = scan_seconds
            + 240.0 * 60.0 / 88.17 + long.adjustments.len() as f64 * 2.0;
        assert!(hypothetical_seconds < 400.0 * 60.0 / 70.98);
        assert!(hypothetical_seconds > 400.0 * 60.0 / 88.17);
    }

    #[test]
    fn measured_memory_gate_is_rechecked_during_exploitation() {
        let now = Instant::now();
        let mut t = OnlineAutotuner::new(6, 6, 12, Some(6000.0), now).unwrap();
        for (worker, score) in [(6, 70.0), (8, 72.0), (10, 64.0), (12, 88.0)] {
            t.evidence.insert(worker, VecDeque::from(vec![score, score]));
        }
        t.counters.probes = 8;
        t.select_best_observed();
        assert_eq!(t.best.unwrap().0, 12);
        t.exploit_safe_best(80, 600.0, "synthetic low-RAM");
        assert_eq!(t.active, 8); // two extra slots fit; six do not
        assert_eq!(t.counters.unsafe_best_holds, 1);
        t.settle(80, 400, now);
        t.exploit_safe_best(80, 3000.0, "synthetic RAM recovery");
        assert_eq!(t.active, 12);
    }

    #[test]
    fn drifted_and_noisy_rolling_evidence_can_reselect_winner() {
        let now = Instant::now();
        let mut t = OnlineAutotuner::new(6, 6, 12, Some(8000.0), now).unwrap();
        t.counters.probes = 8;
        t.evidence.insert(6, VecDeque::from(vec![70.0, 71.0]));
        t.evidence.insert(12, VecDeque::from(vec![88.0, 87.0]));
        t.select_best_observed();
        assert_eq!(t.best.unwrap().0, 12);
        // An eight-sample rolling window replaces stale observations after
        // a sustained change of load; isolated single outliers are not enough.
        for i in 0..RECENT_SAMPLES_PER_WORKER {
            for (worker, score) in [(6, 96.0), (12, 59.0)] {
                let samples = t.evidence.get_mut(&worker).unwrap();
                if samples.len() == RECENT_SAMPLES_PER_WORKER { samples.pop_front(); }
                samples.push_back(score + (i % 3) as f64 * 0.2);
            }
        }
        t.select_best_observed();
        assert_eq!(t.best.unwrap().0, 6);
    }

    #[test]
    fn measured_short_scan_sweep_explores_all_candidates_before_optional_replication() {
        // Real October 2026 host measurement windows, with no media or
        // host-specific throughput preference built into the policy.
        // Old formula: first 12-song epoch * 4 candidates * 2 = 96
        // undispatched songs required, while only ~82 were left, so it
        // never attempted any challenger. The incumbent has already been
        // measured and should not be charged a second time.
        let mut now = Instant::now();
        let mut t = OnlineAutotuner::new(6, 6, 12, Some(8000.0), now).unwrap();
        let (mut completed, mut patches) = (0, 0);
        let windows = [
            (6, 12, 2844, 12.53709, 82),
            (12, 17, 4591, 12.2542338, 65),
            (8, 18, 4043, 12.0519457, 47),
            (10, 8, 4010, 17.0551454, 39),
        ];
        for (worker, count, patch_count, seconds, remaining) in windows {
            assert_eq!(t.active, worker);
            completed += count;
            patches += patch_count;
            now += Duration::from_secs_f64(seconds);
            t.observe(completed, patches, Some(6500.0), remaining, now).unwrap();
            if worker == 6 {
                let decision = t.last_exploration_budget.as_ref().unwrap();
                assert_eq!(decision.phase, "first-coarse-discovery");
                assert_eq!(decision.unmeasured_candidate_windows, 3);
                assert_eq!(decision.required_songs, 48);
                assert_eq!(decision.remaining_undispatched_songs, 82);
            }
            if t.draining() { t.settle(completed, patches, now); }
        }
        let diagnostics = t.into_diagnostics();
        assert!(diagnostics.search_completed);
        assert_eq!(diagnostics.probes.iter().map(|probe| probe.workers)
            .collect::<Vec<_>>(), [6, 12, 8, 10]);
        assert_eq!(diagnostics.counters.completed_coarse_sweeps, 1);
        assert_eq!(diagnostics.counters.memory_gate_holds, 0);
        assert!(diagnostics.last_exploration_budget.is_some());
    }

    #[test]
    fn general_short_horizon_still_limits_search_and_single_mode_needs_no_sweep() {
        let now = Instant::now();
        let mut short = OnlineAutotuner::new(2, 1, 4, Some(6000.0), now).unwrap();
        short.observe(12, 1000, Some(5500.0), 16,
            now + Duration::from_secs(13)).unwrap();
        assert_eq!(short.active, 2);
        assert!(short.exploration_budget_exhausted);
        let decision = short.last_exploration_budget.as_ref().unwrap();
        assert_eq!(decision.phase, "first-coarse-discovery");
        assert_eq!(decision.unmeasured_candidate_windows, 3);
        assert_eq!(decision.required_songs, 48);
        assert_eq!(decision.remaining_undispatched_songs, 16);
        assert_eq!(short.counters.exploration_budget_holds, 1);
        let mut single = OnlineAutotuner::new(1, 1, 1, Some(6000.0), now).unwrap();
        single.observe(12, 1000, Some(5500.0), 13,
            now + Duration::from_secs(13)).unwrap();
        assert!(!single.exploration_budget_exhausted);
        assert_eq!(single.counters.exploration_budget_holds, 0);
    }

    #[test]
    fn real_drain_timing_tracks_productive_old_capacity_work_without_reclassification() {
        let now = Instant::now();
        let mut t = OnlineAutotuner::new(3, 3, 7, Some(5000.0), now).unwrap();
        // First admitted window: 12 songs. A transition may have other work
        // already in-flight; do not charge it to the next candidate's rate.
        t.observe(12, 1200, Some(4500.0), 100,
            now + Duration::from_secs(13)).unwrap();
        assert!(t.draining());
        assert_eq!(t.adjustments.len(), 1);
        assert_eq!(t.adjustments[0].drain_seconds, None);
        t.settle(14, 1350, now + Duration::from_secs(18));
        assert_eq!(t.adjustments[0].drained_songs, Some(2));
        assert_eq!(t.adjustments[0].drain_seconds, Some(5.0));
        assert!(!t.draining());
        t.observe(22, 2500, Some(4400.0), 100,
            now + Duration::from_secs(31)).unwrap();
        let diag = t.into_diagnostics();
        assert_eq!(diag.probes.len(), 2);
        assert_eq!(diag.probes[0].workers, 3);
        assert_eq!(diag.probes[0].completed_songs, 12);
        assert_eq!(diag.probes[1].workers, 7);
        assert_eq!(diag.probes[1].completed_songs, 8);
        assert_eq!(diag.probes[1].patches, 1150);
    }

    #[test]
    fn candidate_schedule_covers_beyond_a_bad_local_peak() {
        assert_eq!(candidate_schedule(6, 12, 6), [6, 12, 8, 10]);
        assert_eq!(candidate_schedule(6, 12, 12), [12, 6, 8, 10]);
        let plan = candidate_schedule(1, 16, 8);
        assert_eq!(plan[0], 8);
        assert_eq!(plan[1], 16);
        assert_eq!(plan[2], 1);
        assert!(plan.contains(&9));
    }
}
