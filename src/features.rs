//! Opt-in, capability-based classification heads sharing one EffNet embedding pass.
//! No source music or Bliss database is ever opened for writing.
use anyhow::{bail, Context, Result};
use ort::{session::Session, value::TensorRef};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::{
    collections::{BTreeMap, HashSet},
    path::{Component, Path, PathBuf},
    time::Instant,
};

use crate::{ffmpeg_pcm_mono_16k, preprocess, sha256_file, storage, Timing};

const PREPROCESSING: &str = "experimental-essentia-audio-v4-unvalidated";
const AGGREGATION: &str = "arithmetic_mean_of_per_patch_sigmoid_scores";

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Descriptor {
    id: String,
    capability: String,
    embedding_model: String,
    classification_model: String,
    metadata: String,
    embedding_dimensions: usize,
    expected_classes: usize,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Registry {
    schema_version: u32,
    models: Vec<Descriptor>,
}

#[derive(Clone, Debug)]
pub struct Profile {
    descriptor: Descriptor,
    labels: Vec<String>,
    encoder_path: PathBuf,
    head_path: PathBuf,
    hashes: BTreeMap<String, String>,
    pub model_key: String,
}

fn safe_model_name(name: &str) -> bool {
    let path = Path::new(name);
    name.len() <= 180
        && !name.chars().any(|c| matches!(c, '/' | '\\' | ':' | '\0'))
        && path.components().count() == 1
        && matches!(path.components().next(), Some(Component::Normal(_)))
        && name != "." && name != ".."
}

pub fn load_profiles(
    models_dir: &Path, registry_path: Option<&Path>, selected: &str,
) -> Result<Vec<Profile>> {
    let source = match registry_path {
        Some(file) => std::fs::read_to_string(file)
            .with_context(|| format!("Cannot read model registry {}", file.display()))?,
        None => include_str!("../model-registry.json").to_owned(),
    };
    let registry: Registry = serde_json::from_str(&source)?;
    if registry.schema_version != 1 || registry.models.is_empty() {
        bail!("Expected nonempty model registry schema_version=1");
    }
    let ids: Vec<_> = selected.split(',').map(str::trim).collect();
    if ids.is_empty() || ids.iter().any(|id| id.is_empty()) {
        bail!("--models requires comma-separated nonempty model IDs");
    }
    let mut profiles = Vec::new();
    let mut unique = HashSet::new();
    for id in ids {
        if !unique.insert(id.to_owned()) {
            bail!("Duplicate selected model: {id}");
        }
        let descriptor = registry.models.iter().find(|x| x.id == id)
            .with_context(|| format!("Unknown model '{id}' in registry"))?.clone();
        if !safe_model_name(&descriptor.embedding_model)
            || !safe_model_name(&descriptor.classification_model)
            || !safe_model_name(&descriptor.metadata)
            || descriptor.id.trim().is_empty()
            || descriptor.capability.trim().is_empty()
            || !(1..=2048).contains(&descriptor.expected_classes)
            || descriptor.embedding_dimensions != 1280
        {
            bail!("Unsupported or unsafe model registry descriptor for '{id}'");
        }
        if profiles.first().is_some_and(|first: &Profile| {
            first.descriptor.embedding_model != descriptor.embedding_model
        }) {
            bail!("Selected heads require different encoders; analyze them separately");
        }
        let encoder_path = models_dir.join(&descriptor.embedding_model);
        let head_path = models_dir.join(&descriptor.classification_model);
        let metadata_path = models_dir.join(&descriptor.metadata);
        for file in [&encoder_path, &head_path, &metadata_path] {
            if !file.is_file() {
                bail!("Missing model file {} (run scripts/download-models.ps1)", file.display());
            }
        }
        let metadata: serde_json::Value =
            serde_json::from_slice(&std::fs::read(&metadata_path)?)?;
        let labels: Vec<String> = metadata["classes"].as_array()
            .context("Model metadata must contain 'classes' array")?
            .iter()
            .map(|x| x.as_str().map(str::to_owned).context("Invalid nonstring class label"))
            .collect::<Result<_>>()?;
        if labels.len() != descriptor.expected_classes
            || labels.iter().any(|s| s.is_empty())
            || labels.iter().collect::<HashSet<_>>().len() != labels.len()
        {
            bail!("Invalid number of unique labels for '{id}'");
        }
        let hashes = BTreeMap::from([
            (descriptor.embedding_model.clone(), sha256_file(&encoder_path)?),
            (descriptor.classification_model.clone(), sha256_file(&head_path)?),
        ]);
        let model_key = storage::model_key_for(
            &descriptor.embedding_model, &descriptor.classification_model,
            &hashes, PREPROCESSING, AGGREGATION, &labels, false,
        )?;
        profiles.push(Profile {
            descriptor, labels, encoder_path, head_path, hashes, model_key,
        });
    }
    Ok(profiles)
}

#[derive(Clone, Serialize)]
pub struct ClassificationResult {
    pub capability: String,
    pub embedding_model: String,
    pub classification_model: String,
    pub models_sha256: BTreeMap<String, String>,
    pub model_key: String,
    pub validated_against_essentia: bool,
    pub scores: BTreeMap<String, f32>,
}

#[derive(Serialize)]
pub struct FeatureReport {
    pub schema_version: u32,
    pub preprocessing_version: &'static str,
    pub aggregation: &'static str,
    pub audio_path: String,
    pub audio_sha256: String,
    pub sample_rate: usize,
    pub patches_analyzed: usize,
    pub threads: usize,
    pub timings: Timing,
    pub classifications: BTreeMap<String, ClassificationResult>,
}

pub struct FeatureEngine {
    encoder: Session,
    heads: Vec<(Profile, Session)>,
    load_secs: f64,
    counted_load: bool,
    threads: usize,
}

fn classify(session: &mut Session, vector: &[f32], count: usize) -> Result<Vec<f32>> {
    let input = TensorRef::from_array_view(([1usize, 1280usize], vector))?;
    let outputs = session.run(ort::inputs![input])?;
    for output in outputs.values() {
        let (_, values) = output.try_extract_tensor::<f32>()?;
        if values.len() == count
            && values.iter().all(|v| v.is_finite() && (0.0..=1.0).contains(v))
        {
            return Ok(values.to_vec());
        }
    }
    bail!("Classifier did not output {count} finite sigmoid scores")
}

impl FeatureEngine {
    pub fn new(profiles: Vec<Profile>, threads: usize) -> Result<Self> {
        if profiles.is_empty() || threads == 0 {
            bail!("At least one model and one inference thread required");
        }
        let started = Instant::now();
        let env = ort::init().build()?;
        let encoder = Session::builder(&env)?
            .with_intra_threads(threads)
            .map_err(|e| anyhow::anyhow!("{e}"))?
            .commit_from_file(&profiles[0].encoder_path)?;
        let mut heads = Vec::new();
        for profile in profiles {
            let session = Session::builder(&env)?
                .with_intra_threads(threads)
                .map_err(|e| anyhow::anyhow!("{e}"))?
                .commit_from_file(&profile.head_path)?;
            heads.push((profile, session));
        }
        Ok(Self { encoder, heads, load_secs: started.elapsed().as_secs_f64(),
            counted_load: false, threads })
    }

    pub fn analyze(&mut self, path: &Path, max_patches: Option<usize>) -> Result<FeatureReport> {
        if !path.is_file() {
            bail!("Audio file does not exist: {}", path.display());
        }
        let started = Instant::now();
        let at = Instant::now();
        let audio = ffmpeg_pcm_mono_16k(path)?;
        let decode_seconds = at.elapsed().as_secs_f64();
        let at = Instant::now();
        let mel = preprocess::mel_spectrogram(&audio)?;
        let patches = preprocess::patches(&mel, max_patches)?;
        let features_seconds = at.elapsed().as_secs_f64();
        let count = patches.len();
        let mut sums: Vec<Vec<f64>> = self.heads.iter()
            .map(|(profile, _)| vec![0.0; profile.labels.len()]).collect();
        let at = Instant::now();
        for patch in &patches {
            let input = TensorRef::from_array_view(([1usize, 128usize, 96usize], patch.as_slice()))?;
            let outputs = self.encoder.run(ort::inputs![input])?;
            let mut vector = None;
            for output in outputs.values() {
                let (_, tensor) = output.try_extract_tensor::<f32>()?;
                if tensor.len() == 1280 {
                    vector = Some(tensor.to_vec());
                    break;
                }
            }
            let vector = vector.context("EffNet did not output a 1280-dimensional embedding")?;
            for (i, (profile, session)) in self.heads.iter_mut().enumerate() {
                let scores = classify(session, &vector, profile.labels.len())?;
                for (sum, value) in sums[i].iter_mut().zip(scores) {
                    *sum += f64::from(value);
                }
            }
        }
        let inference_seconds = at.elapsed().as_secs_f64();
        let model_load_seconds = if self.counted_load { 0.0 } else { self.load_secs };
        self.counted_load = true;
        let mut classifications = BTreeMap::new();
        for ((profile, _), sums) in self.heads.iter().zip(sums) {
            let scores = profile.labels.iter().cloned()
                .zip(sums.into_iter().map(|v| (v / count as f64) as f32))
                .collect();
            classifications.insert(profile.descriptor.id.clone(), ClassificationResult {
                capability: profile.descriptor.capability.clone(),
                embedding_model: profile.descriptor.embedding_model.clone(),
                classification_model: profile.descriptor.classification_model.clone(),
                models_sha256: profile.hashes.clone(),
                model_key: profile.model_key.clone(),
                validated_against_essentia: false,
                scores,
            });
        }
        Ok(FeatureReport {
            schema_version: 3, preprocessing_version: PREPROCESSING,
            aggregation: AGGREGATION,
            audio_path: path.display().to_string(),
            audio_sha256: sha256_file(path)?,
            sample_rate: preprocess::RATE,
            patches_analyzed: count, threads: self.threads,
            timings: Timing {
                decode_seconds, features_seconds, model_load_seconds,
                inference_seconds,
                total_seconds: started.elapsed().as_secs_f64() + model_load_seconds,
            },
            classifications,
        })
    }
}

pub fn classify_embeddings(
    vectors: &[Vec<f32>], profile: &Profile, threads: usize,
) -> Result<Vec<Vec<f32>>> {
    if vectors.is_empty() || vectors.len() > 64 || threads == 0
        || vectors.iter().any(|v| v.len() != 1280 || v.iter().any(|x| !x.is_finite()))
    {
        bail!("Need 1..64 finite 1280D embeddings and valid thread count");
    }
    let env = ort::init().build()?;
    let mut head = Session::builder(&env)?
        .with_intra_threads(threads)
        .map_err(|e| anyhow::anyhow!("{e}"))?
        .commit_from_file(&profile.head_path)?;
    vectors.iter().map(|v| classify(&mut head, v, profile.labels.len())).collect()
}

pub fn parity_output(
    vectors: &[Vec<f32>], profile: &Profile, threads: usize,
) -> Result<serde_json::Value> {
    let rows = classify_embeddings(vectors, profile, threads)?;
    let mut means = vec![0.0f64; profile.labels.len()];
    for row in &rows {
        for (mean, score) in means.iter_mut().zip(row) {
            *mean += f64::from(*score);
        }
    }
    let means: Vec<f32> = means.into_iter()
        .map(|x| (x / rows.len() as f64) as f32).collect();
    Ok(serde_json::json!({
        "schema_version": 2,
        "validation_status": "experimental-unvalidated",
        "classification_model": profile.descriptor.classification_model,
        "classification_model_sha256": profile.hashes[&profile.descriptor.classification_model],
        "patches_classified": rows.len(),
        "classes": profile.labels,
        "scores_per_patch": rows,
        "mean_scores": means,
        "aggregation": AGGREGATION,
    }))
}

/// Versioned model-independent scores; never changes the legacy mood_tracks table.
pub fn persist(
    db_path: &Path, track_key: &str, report: &FeatureReport,
    state: Option<(i64, i64)>,
) -> Result<()> {
    if track_key.is_empty() || track_key.trim() != track_key || track_key.contains('\0') {
        bail!("Invalid exact Bliss track key");
    }
    if report.patches_analyzed == 0 || report.audio_sha256.len() != 64
        || !report.audio_sha256.bytes().all(|b| b.is_ascii_hexdigit())
        || report.classifications.is_empty()
    {
        bail!("Malformed feature report");
    }
    let mut conn = storage::open_scan_db(db_path)?;
    let tx = conn.transaction()?;
    for (id, classifier) in &report.classifications {
        if id.is_empty() || classifier.scores.is_empty()
            || classifier.scores.len() > 2048
            || classifier.scores.values().any(|x| !x.is_finite() || !(0.0..=1.0).contains(x))
        {
            bail!("Malformed classification results for {id}");
        }
        let labels: Vec<String> = classifier.scores.keys().cloned().collect();
        let key = storage::model_key_for(
            &classifier.embedding_model, &classifier.classification_model,
            &classifier.models_sha256, report.preprocessing_version,
            report.aggregation, &labels, classifier.validated_against_essentia,
        )?;
        if key != classifier.model_key {
            bail!("Model fingerprint mismatch for {id}");
        }
        tx.execute(
            "INSERT OR IGNORE INTO mood_models
               (model_key, embedding_model, classification_model, models_sha256_json,
                preprocessing_version, aggregation, classes_json, validated_against_essentia)
             VALUES(?1,?2,?3,?4,?5,?6,?7,?8)",
            params![key, classifier.embedding_model, classifier.classification_model,
                serde_json::to_string(&classifier.models_sha256)?,
                report.preprocessing_version, report.aggregation,
                serde_json::to_string(&labels)?, classifier.validated_against_essentia],
        )?;
        let scores: Vec<u8> = classifier.scores.values()
            .flat_map(|value| value.to_le_bytes()).collect();
        tx.execute(
            "INSERT INTO feature_tracks
                (track_file, model_id, capability, audio_sha256, model_key, scores_f32_le, patches_analyzed)
             VALUES(?1,?2,?3,?4,?5,?6,?7)
             ON CONFLICT(track_file, model_id) DO UPDATE SET
               capability=excluded.capability, audio_sha256=excluded.audio_sha256,
               model_key=excluded.model_key, scores_f32_le=excluded.scores_f32_le,
               patches_analyzed=excluded.patches_analyzed, analyzed_at=CURRENT_TIMESTAMP",
            params![track_key, id, classifier.capability, report.audio_sha256,
                key, scores, report.patches_analyzed as i64],
        )?;
        tx.execute("DELETE FROM feature_track_state WHERE track_file=?1 AND model_id=?2",
            params![track_key, id])?;
        if let Some((size, modified)) = state {
            tx.execute(
                "INSERT INTO feature_track_state(track_file,model_id,file_size,modified_ns,model_key)
                 VALUES(?1,?2,?3,?4,?5)",
                params![track_key, id, size, modified, key],
            )?;
        }
    }
    tx.commit()?;
    Ok(())
}

fn is_current(
    conn: &Connection, track_key: &str, profiles: &[Profile], state: (i64, i64),
) -> Result<bool> {
    if conn.pragma_query_value(None, "user_version", |row| row.get::<_, i64>(0))? < 3 {
        return Ok(false);
    }
    for profile in profiles {
        let found: i64 = conn.query_row(
            "SELECT count(*) FROM feature_track_state s
               JOIN feature_tracks t ON t.track_file=s.track_file AND t.model_id=s.model_id
             WHERE s.track_file=?1 AND s.model_id=?2 AND s.file_size=?3 AND s.modified_ns=?4
               AND s.model_key=?5 AND t.model_key=?5",
            params![track_key, profile.descriptor.id, state.0, state.1, profile.model_key],
            |row| row.get(0),
        )?;
        if found != 1 { return Ok(false); }
    }
    Ok(true)
}

#[derive(Debug, Serialize)]
pub struct ScanSummary {
    model_ids: Vec<String>,
    bliss_tracks: usize,
    checked: usize,
    up_to_date: usize,
    pending: usize,
    analyzed: usize,
    missing_files: usize,
    failures: usize,
    limit_reached: bool,
    elapsed_seconds: f64,
    model_sessions_initialized: bool,
    experimental_results: bool,
}

pub struct ScanOptions<'a> {
    pub bliss_db: &'a Path,
    pub db: &'a Path,
    pub models_dir: &'a Path,
    pub registry: Option<&'a Path>,
    pub models: &'a str,
    pub source_root: Option<&'a Path>,
    pub library_root: Option<&'a str>,
    pub only_track: Option<&'a str>,
    pub max_new: Option<usize>,
    pub threads: usize,
    pub dry_run: bool,
}

pub fn scan(options: ScanOptions<'_>) -> Result<ScanSummary> {
    let started = Instant::now();
    if options.threads == 0 || options.max_new == Some(0) {
        bail!("--threads and --max-new must be positive");
    }
    let profiles = load_profiles(options.models_dir, options.registry, options.models)?;
    let mut tracks = storage::bliss_files(options.bliss_db)?;
    if let Some(track) = options.only_track {
        tracks.retain(|key| key == track);
        if tracks.is_empty() {
            bail!("Exact --only-track not found in TracksV2");
        }
    }
    let conn = if options.dry_run {
        storage::open_readonly_scan_db(options.db)?
    } else {
        Some(storage::open_scan_db(options.db)?)
    };
    let mut engine = None;
    let mut summary = ScanSummary {
        model_ids: profiles.iter().map(|p| p.descriptor.id.clone()).collect(),
        bliss_tracks: tracks.len(),
        checked: 0, up_to_date: 0, pending: 0, analyzed: 0,
        missing_files: 0, failures: 0, limit_reached: false,
        elapsed_seconds: 0.0, model_sessions_initialized: false,
        experimental_results: true,
    };
    for track in tracks {
        summary.checked += 1;
        let path = match crate::batch::source_path(
            &track, options.library_root, options.source_root,
        ) {
            Ok(path) => path,
            Err(e) => {
                summary.failures += 1;
                eprintln!("MAPPING ERROR {track}: {e:#}");
                continue;
            }
        };
        let state = match crate::batch::file_stat(&path) {
            Ok(stat) => stat,
            Err(error) => {
                summary.missing_files += 1;
                eprintln!("SOURCE UNAVAILABLE {}: {error:#}", path.display());
                continue;
            }
        };
        if conn.as_ref().map(|db| is_current(db, &track, &profiles, state))
            .transpose()?.unwrap_or(false) {
            summary.up_to_date += 1;
            continue;
        }
        summary.pending += 1;
        if options.dry_run { continue; }
        if options.max_new.is_some_and(|max| summary.analyzed >= max) {
            summary.limit_reached = true;
            break;
        }
        if engine.is_none() {
            engine = Some(FeatureEngine::new(profiles.clone(), options.threads)?);
            summary.model_sessions_initialized = true;
        }
        let outcome = engine.as_mut().expect("engine available").analyze(&path, None)
            .and_then(|report| persist(options.db, &track, &report, Some(state)));
        match outcome {
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
    fn rejects_absolute_and_parent_model_paths() {
        for name in ["../head.onnx", "/tmp/head.onnx", r"C:\test.onnx", "foo/bar.onnx"] {
            assert!(!safe_model_name(name));
        }
        assert!(safe_model_name("head.onnx"));
    }

    #[test]
    fn registry_has_independent_capabilities() {
        let registry: Registry = serde_json::from_str(include_str!("../model-registry.json")).unwrap();
        assert_eq!(registry.schema_version, 1);
        assert_eq!(registry.models.len(), 2);
        assert_eq!(registry.models[0].capability, "mood_theme");
        assert_eq!(registry.models[1].capability, "genre");
        assert_eq!(registry.models[1].expected_classes, 87);
        assert_eq!(registry.models[0].embedding_model, registry.models[1].embedding_model);
    }

    #[test]
    fn rejects_unknown_registry_model_without_audio_or_db() {
        let missing = load_profiles(Path::new("models"), None, "unlisted");
        assert!(missing.is_err());
    }
}
