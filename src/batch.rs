//! Incremental analysis of the exact file identities already present in bliss.db.
//! No write access to Bliss and no implicit deletion/pruning of old Mood rows.
use anyhow::{bail, Context, Result};
use serde::Serialize;
use std::{path::{Path, PathBuf}, time::{Instant, UNIX_EPOCH}};

use crate::{engine::{ModelProfile, MoodEngine}, storage};

#[derive(Debug, Serialize)]
pub struct ScanSummary {
    pub bliss_tracks: usize,
    pub checked: usize,
    pub up_to_date: usize,
    pub pending: usize,
    pub analyzed: usize,
    pub missing_files: usize,
    pub failures: usize,
    pub limit_reached: bool,
    pub elapsed_seconds: f64,
    pub model_sessions_initialized: bool,
    pub experimental_results: bool,
}

#[derive(Debug)]
pub struct ScanOptions<'a> {
    pub bliss_db: &'a Path,
    pub mood_db: &'a Path,
    pub models_dir: &'a Path,
    pub source_root: Option<&'a Path>,
    pub library_root: Option<&'a str>,
    pub max_new: Option<usize>,
    pub threads: usize,
    pub dry_run: bool,
}

/// Convert a stored Bliss path to the analysis host's path.
/// Without root mapping, the exact Bliss path is used directly.
fn source_path(
    track_key: &str,
    library_root: Option<&str>,
    source_root: Option<&Path>,
) -> Result<PathBuf> {
    match (library_root, source_root) {
        (None, None) => Ok(PathBuf::from(track_key)),
        (Some(prefix), Some(root)) => {
            let prefix = prefix.trim_end_matches(&['/', '\\'][..]);
            if prefix.is_empty() || root.as_os_str().is_empty() {
                bail!("Path mapping roots must be non-empty");
            }
            let relative = track_key.strip_prefix(prefix)
                .context("Track path does not start with declared library root")?;
            let relative = relative.strip_prefix(&['/', '\\'][..])
                .context("Library prefix must be followed by a path separator")?;
            if relative.is_empty() {
                bail!("Track key points to a directory, not a song");
            }
            let mut result = root.to_path_buf();
            for part in relative.split(&['/', '\\'][..]) {
                if part.is_empty() || part == "." || part == ".." || part.contains(':') {
                    bail!("Unsafe or ambiguous path component in Bliss track key");
                }
                result.push(part);
            }
            Ok(result)
        }
        _ => bail!("--library-root and --source-root must be provided together"),
    }
}

fn file_stat(file: &Path) -> Result<(i64, i64)> {
    let meta = std::fs::metadata(file)
        .with_context(|| format!("Unable to stat {}", file.display()))?;
    if !meta.is_file() {
        bail!("Not a regular music file: {}", file.display());
    }
    let size = i64::try_from(meta.len()).context("File length overflows SQLite integer")?;
    let since_epoch = meta.modified()?.duration_since(UNIX_EPOCH)
        .context("File has modification time before Unix epoch")?;
    let modified_ns = i64::try_from(since_epoch.as_nanos())
        .context("Modification time outside SQLite integer range")?;
    Ok((size, modified_ns))
}

pub fn scan(options: ScanOptions<'_>) -> Result<ScanSummary> {
    let started = Instant::now();
    if options.threads == 0 || options.max_new == Some(0) {
        bail!("--threads and --max-new must be >= 1");
    }
    if options.source_root.is_some() != options.library_root.is_some() {
        bail!("--source-root and --library-root must be passed together");
    }
    // The source library is opened read-only and sorted by its canonical File key.
    let tracks = storage::bliss_files(options.bliss_db)?;
    let mut profile = Some(ModelProfile::load(options.models_dir)?);
    let model_key = profile.as_ref().expect("profile").model_key.clone();
    let conn = storage::open_scan_db(options.mood_db)?;
    let mut engine: Option<MoodEngine> = None;
    let mut summary = ScanSummary {
        bliss_tracks: tracks.len(),
        checked: 0, up_to_date: 0, pending: 0, analyzed: 0,
        missing_files: 0, failures: 0, limit_reached: false,
        elapsed_seconds: 0.0,
        model_sessions_initialized: false,
        experimental_results: true,
    };
    let mut conn = conn;
    for track in tracks {
        summary.checked += 1;
        let source = match source_path(
            &track, options.library_root, options.source_root
        ) {
            Ok(path) => path,
            Err(e) => {
                summary.failures += 1;
                eprintln!("MAPPING ERROR {track}: {e:#}");
                continue;
            }
        };
        let (size, modified) = match file_stat(&source) {
            Ok(meta) => meta,
            Err(e) => {
                summary.missing_files += 1;
                eprintln!("SOURCE UNAVAILABLE {}: {e:#}", source.display());
                continue;
            }
        };
        if storage::is_current(&conn, &track, size, modified, &model_key)? {
            summary.up_to_date += 1;
            continue;
        }
        summary.pending += 1;
        if options.dry_run {
            continue;
        }
        if options.max_new.is_some_and(|max| summary.analyzed >= max) {
            summary.limit_reached = true;
            break;
        }
        if engine.is_none() {
            engine = Some(MoodEngine::new(profile.take().expect("profile only loaded once"), options.threads)?);
            summary.model_sessions_initialized = true;
        }
        let result = engine.as_mut().expect("model initialized").analyze(&source, None);
        match result.and_then(|report| {
            // New scores are committed only after all model stages succeed.
            storage::persist_scanned(&mut conn, &track, &report, size, modified)
        }) {
            Ok(()) => {
                summary.analyzed += 1;
                eprintln!("ANALYZED {} ({}/{})", track, summary.analyzed, summary.pending);
            }
            Err(error) => {
                summary.failures += 1;
                eprintln!("ANALYSIS FAILED {track}: {error:#}");
            }
        }
    }
    summary.elapsed_seconds = started.elapsed().as_secs_f64();
    Ok(summary)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn supports_native_identity_and_mapped_roots() {
        assert_eq!(source_path("/mnt/music/a.flac", None, None).unwrap(),
                   PathBuf::from("/mnt/music/a.flac"));
        assert_eq!(
            source_path("/mnt/music/Rock/a.flac", Some("/mnt/music"), Some(Path::new("D:/Music"))).unwrap(),
            PathBuf::from("D:/Music").join("Rock").join("a.flac")
        );
        assert!(source_path("/mnt/musical/a.flac", Some("/mnt/music"), Some(Path::new("D:/Music"))).is_err());
        assert!(source_path("/mnt/music/../secret", Some("/mnt/music"), Some(Path::new("D:/Music"))).is_err());
        assert!(source_path("/mnt/music/song", Some("/mnt/music"), None).is_err());
    }
}
