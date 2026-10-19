//! Experimental, passive Mood/Genre guidance provider for Bliss-first hosts.
//! Uses only trusted read-only schema-v3 SQLite resources. No model or audio I/O.
use anyhow::{bail, Context, Result};
use rusqlite::{params, Connection, OpenFlags, OptionalExtension};
use serde_json::{json, Value};
use std::collections::{HashMap, HashSet};
use std::io::{self, BufRead, Write};
use std::path::Path;

const PROVIDER: &str = "bliss-feature-guidance";
const RESOURCE: &str = "bliss-feature-sqlite-v3";
const MAX_CANDIDATES: usize = 256;
const MAX_ANCHORS: usize = 64;
const MAX_MESSAGE_BYTES: usize = 1_048_576;
const AGGREGATION: &str = "arithmetic_mean_of_per_patch_sigmoid_scores";

#[derive(Clone)]
struct Vector {
    fingerprint: String,
    values: Vec<f32>,
}
struct Prepared {
    db: Connection,
    anchors: HashMap<String, HashMap<&'static str, Vector>>,
    include_experimental: bool,
    requests: usize,
}
fn error(code: &str, message: &str) -> Value {
    json!({"type":"error","provider_id":PROVIDER,
        "code":code,"message":message,"retryable":false})
}
fn manifest() -> Value {
    json!({
        "type":"manifest","spi_version":2,"provider_id":PROVIDER,
        "provider_version":"0.1.0","protocol":"bliss-guidance-jsonl-v2",
        "capabilities":["global_candidate_guidance","edge_candidate_guidance"],
        "channels":[
            {"channel":"genre","scopes":["global","edge"],
             "supported_host_policies":["bounded_influence"]},
            {"channel":"mood_theme","scopes":["global","edge"],
             "supported_host_policies":["bounded_influence"]}
        ],
        "required_context":["database_file"],
        "configuration_schema":{"type":"object","properties":{
            "include_experimental":{"type":"boolean","default":false}
        },"additionalProperties":false}
    })
}
fn models() -> [(&'static str, &'static str, usize); 2] {
    [("genre","genre",87),("moodtheme","mood_theme",56)]
}
fn valid_vector(values: &[f32]) -> bool {
    if values.is_empty() || values.iter().any(|v| !v.is_finite() || !(0.0..=1.0).contains(v)) {
        return false;
    }
    let mean = values.iter().copied().map(f64::from).sum::<f64>() / values.len() as f64;
    let variance = values.iter().map(|v| (f64::from(*v) - mean).powi(2)).sum::<f64>() / values.len() as f64;
    // An all-zero or uniform vector is not meaningful similarity evidence.
    variance > 1e-10
}
fn fetch_vector(
    db: &Connection, file: &str, id: &str, capability: &str,
    dimensions: usize, include_experimental: bool
) -> Option<Vector> {
    if file.is_empty() || file.contains('\0') { return None; }
    let row: (String, String, String, String, i64, Vec<u8>) = db.query_row(
        "SELECT t.capability,t.model_key,m.aggregation,m.classes_json,\
                m.validated_against_essentia,t.scores_f32_le \
         FROM feature_tracks t JOIN feature_models m ON t.model_key=m.model_key \
         WHERE t.track_file=?1 COLLATE BINARY AND t.model_id=?2",
        params![file,id], |r| Ok((r.get(0)?,r.get(1)?,r.get(2)?,r.get(3)?,r.get(4)?,r.get(5)?))
    ).optional().ok()??;
    if row.0 != capability || row.1.is_empty() || row.2 != AGGREGATION
        || !matches!(row.4, 0 | 1) || (row.4 == 0 && !include_experimental)
        || row.5.len() != dimensions * 4 { return None; }
    let labels: Vec<String> = serde_json::from_str(&row.3).ok()?;
    if labels.len() != dimensions || labels.iter().any(|label| label.is_empty())
        || labels.iter().collect::<HashSet<_>>().len() != dimensions { return None; }
    let values: Vec<f32> = row.5.as_chunks::<4>().0.iter()
        .map(|chunk| f32::from_le_bytes(*chunk)).collect();
    if !valid_vector(&values) { return None; }
    Some(Vector { fingerprint: row.1, values })
}
fn anchors_from_prepare(db: &Connection, request: &Value, experimental: bool)
    -> Result<HashMap<String, HashMap<&'static str, Vector>>> {
    let entries = request["anchors"].as_array().context("prepare.anchors array required")?;
    if entries.len() > MAX_ANCHORS { bail!("too many seed anchors"); }
    let mut anchors = HashMap::new();
    for a in entries {
        let id = a["anchor_id"].as_str().filter(|v| !v.is_empty())
            .context("anchor_id required")?;
        let file = a["database_file"].as_str().filter(|v| !v.is_empty());
        if anchors.contains_key(id) { bail!("duplicate anchor ID"); }
        let mut vectors = HashMap::new();
        if let Some(file) = file {
            for (model, capability, len) in models() {
                if let Some(vector) = fetch_vector(db, file, model, capability, len, experimental) {
                    vectors.insert(model, vector);
                }
            }
        }
        anchors.insert(id.to_owned(), vectors);
    }
    Ok(anchors)
}
fn prepare(request: &Value) -> Result<Prepared> {
    let opts = request["options"].as_object().context("prepare.options object required")?;
    let experimental = match opts.get("include_experimental") {
        None | Some(Value::Bool(false)) => false,
        Some(Value::Bool(true)) => true,
        _ => bail!("include_experimental must be boolean"),
    };
    let resources = request["resources"].as_array().context("prepare.resources array required")?;
    if resources.len() != 1 || resources[0]["kind"] != RESOURCE
        || resources[0]["access"] != "read_only" { bail!("one trusted read-only feature SQLite resource required"); }
    if request["artifacts"].as_array().is_none_or(|a| !a.is_empty()) {
        bail!("feature provider does not accept artifacts");
    }
    let path = resources[0]["path"].as_str().filter(|s| !s.is_empty())
        .context("missing trusted feature sidecar path")?;
    if !Path::new(path).is_file() { bail!("feature sidecar unavailable"); }
    let db = Connection::open_with_flags(path, OpenFlags::SQLITE_OPEN_READ_ONLY)
        .context("feature sidecar could not be opened read-only")?;
    let version: i64 = db.pragma_query_value(None, "user_version", |r| r.get(0))?;
    if version != 3 { bail!("schema v3 feature sidecar required"); }
    // SQLite query_only is an additional safety guard even on a read-only handle.
    db.pragma_update(None, "query_only", "ON")?;
    let anchors = anchors_from_prepare(&db, request, experimental)?;
    Ok(Prepared {db, anchors, include_experimental:experimental, requests:0})
}
fn similarity(seed: &[f32], candidate: &[f32]) -> Option<f64> {
    if seed.len() != candidate.len() || !valid_vector(seed) || !valid_vector(candidate) {
        return None;
    }
    let rms = seed.iter().zip(candidate).map(|(a,b)| {
        let d = f64::from(*a) - f64::from(*b);
        d * d
    }).sum::<f64>();
    let rms = (rms / seed.len() as f64).sqrt();
    Some((1.0 - 2.0 * rms).clamp(-1.0, 1.0))
}
fn score(state: &mut Prepared, request: &Value) -> Result<Value> {
    let request_id = request["request_id"].as_str().filter(|s| !s.is_empty())
        .context("score.request_id required")?;
    let candidates = request["candidates"].as_array().context("score.candidates array required")?;
    if candidates.len() > MAX_CANDIDATES { bail!("candidate batch exceeds limit"); }
    let context = request["context"].as_object().context("score.context required")?;
    let scope = context.get("scope").and_then(Value::as_str).context("context.scope required")?;
    if scope != "global" && scope != "edge" { bail!("unsupported guidance scope"); }

    let mut active = Vec::new();
    let mut seen = HashSet::new();
    if scope == "edge" {
        for field in ["left_anchor_id","right_anchor_id"] {
            if let Some(id) = context.get(field).and_then(Value::as_str) {
                if seen.insert(id.to_owned()) && state.anchors.contains_key(id) {
                    active.push(id.to_owned());
                }
            }
        }
    }
    if let Some(ids) = context.get("context_track_ids").and_then(Value::as_array) {
        for id in ids {
            if let Some(id) = id.as_str() {
                if seen.insert(id.to_owned()) && state.anchors.contains_key(id) {
                    active.push(id.to_owned());
                }
            }
        }
    }
    let mut signals = Vec::new();
    let mut eligible = HashSet::new();
    let mut supported = 0;
    for candidate in candidates {
        let Some(id) = candidate["candidate_id"].as_str().filter(|s| !s.is_empty()) else { continue };
        if !eligible.insert(id.to_owned()) { continue; }
        let Some(file) = candidate["database_file"].as_str().filter(|s| !s.is_empty()) else { continue };
        supported += 1;
        for (model, capability, dims) in models() {
            let Some(vector) = fetch_vector(&state.db, file, model, capability, dims, state.include_experimental) else {continue};
            let mut values = Vec::new();
            for anchor_id in &active {
                let Some(seed) = state.anchors[anchor_id].get(model) else {continue};
                if seed.fingerprint != vector.fingerprint {continue}
                if let Some(v) = similarity(&seed.values, &vector.values) {values.push(v);}
            }
            if values.is_empty() {continue}
            let avg = values.iter().sum::<f64>() / values.len() as f64;
            signals.push(json!({
                "candidate_id":id, "channel":capability, "scope":scope,
                "score":avg, "confidence":values.len() as f64 / active.len().max(1) as f64,
                "rationale":"same-fingerprint Mood/Genre vector proximity"
            }));
        }
    }
    state.requests += 1;
    Ok(json!({
        "type":"scores","provider_id":PROVIDER,"request_id":request_id,
        "signals":signals,
        "diagnostics":{"state":"ready","request_count":state.requests,"failure_count":0,
            "details":{"candidate_count":candidates.len(),"with_file_key":supported,
                "context_anchor_count":active.len(),"signal_count":signals.len()}}
    }))
}
fn response(state: &mut Option<Prepared>, message: &Value) -> Value {
    if message["spi_version"] != 2 {return error("bad_version","SPI v2 required")}
    match message["type"].as_str() {
        Some("describe") => manifest(),
        Some("prepare") => match prepare(message) {
            Ok(prepared) => {
                let count = prepared.anchors.len();
                let valid = prepared.anchors.values().filter(|v| !v.is_empty()).count();
                *state = Some(prepared);
                json!({"type":"prepared","provider_id":PROVIDER,
                    "diagnostics":{"state":"ready","request_count":0,"failure_count":0,
                        "details":{"anchors":count,"with_features":valid}}})
            }
            Err(e) => { *state=None; error("prepare_failed", &format!("{e:#}")) }
        },
        Some("score") => match state {
            Some(s) => match score(s,message) {
                Ok(v) => v, Err(e) => error("score_failed",&format!("{e:#}")),
            },
            None => error("not_prepared","prepare must succeed first"),
        },
        Some("close") => {
            *state = None;
            json!({"type":"closed","provider_id":PROVIDER})
        },
        _ => error("unsupported_message","unsupported provider message"),
    }
}
fn main() -> Result<()> {
    if std::env::args().any(|a| a == "--version") {
        println!("{PROVIDER} 0.1.0 SPI v2");
        return Ok(());
    }
    let stdin = io::stdin();
    let mut output = io::stdout().lock();
    let mut state = None;
    for line in stdin.lock().lines() {
        let line = line?;
        let reply = if line.len() > MAX_MESSAGE_BYTES {
            error("request_too_large","request exceeds one MiB")
        } else {
            match serde_json::from_str::<Value>(&line) {
                Ok(v) => response(&mut state, &v),
                Err(_) => error("malformed_json","invalid JSON request"),
            }
        };
        serde_json::to_writer(&mut output, &reply)?;
        writeln!(output)?;
        output.flush()?;
        if reply["type"] == "closed" { break; }
    }
    Ok(())
}
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn signal_bounds_and_mismatch_guard() {
        let good = vec![0.1,0.3,0.7,0.9];
        let reversed = vec![0.9,0.7,0.3,0.1];
        assert_eq!(similarity(&good,&good),Some(1.0));
        assert!(similarity(&good,&reversed).unwrap() < 1.0);
        assert_eq!(similarity(&[0.5,0.5],&[0.2,0.7]),None);
        assert_eq!(similarity(&good,&[0.5]),None);
        assert!(!valid_vector(&[f32::NAN,0.4]));
    }
    #[test]
    fn bounded_scoring_preserves_bliss_candidate_identity() {
        let db = Connection::open_in_memory().unwrap();
        db.execute_batch(
            "CREATE TABLE feature_models(model_key TEXT PRIMARY KEY,aggregation TEXT,classes_json TEXT,validated_against_essentia INTEGER);
             CREATE TABLE feature_tracks(track_file TEXT,model_id TEXT,capability TEXT,model_key TEXT,scores_f32_le BLOB);"
        ).unwrap();
        let labels = serde_json::to_string(&(0..87).map(|i| format!("genre{i}")).collect::<Vec<_>>()).unwrap();
        db.execute("INSERT INTO feature_models VALUES('same',?1,?2,1)",
            params![AGGREGATION,labels]).unwrap();
        let seed: Vec<u8> = (0..87).flat_map(|i| (if i%2==0 {0.2_f32} else {0.8_f32}).to_le_bytes()).collect();
        let different: Vec<u8> = (0..87).flat_map(|i| (if i%2==0 {0.8_f32} else {0.2_f32}).to_le_bytes()).collect();
        for (file,bytes) in [("Artist/Seed.flac",&seed),("Artist/Same.flac",&seed),("Artist/Different.flac",&different)] {
            db.execute("INSERT INTO feature_tracks VALUES(?1,'genre','genre','same',?2)",
                params![file,bytes]).unwrap();
        }
        let mut anchors = HashMap::new();
        anchors.insert("seed1".to_string(),HashMap::from([(
            "genre",fetch_vector(&db,"Artist/Seed.flac","genre","genre",87,false).unwrap()
        )]));
        let mut prepared = Prepared { db,anchors,include_experimental:false,requests:0 };
        let request = json!({
            "type":"score","spi_version":2,"request_id":"batch1",
            "context":{"scope":"global","context_track_ids":["seed1"]},
            "candidates":[
                {"candidate_id":"bliss-1","database_file":"Artist/Same.flac"},
                {"candidate_id":"bliss-2","database_file":"Artist/Different.flac"},
                {"candidate_id":"bliss-3","database_file":"Artist/Absent.flac"},
                {"candidate_id":"bliss-4","database_file":null}
            ]
        });
        let response = score(&mut prepared,&request).unwrap();
        let signals = response["signals"].as_array().unwrap();
        assert_eq!(signals.len(),2);
        assert_eq!(signals[0]["candidate_id"],"bliss-1");
        assert_eq!(signals[0]["channel"],"genre");
        assert_eq!(signals[0]["score"],1.0);
        assert_eq!(signals[1]["candidate_id"],"bliss-2");
        assert!(signals[1]["score"].as_f64().unwrap() < 1.0);
        assert!(signals.iter().all(|s| s["confidence"] == 1.0));
        assert_eq!(prepared.requests,1);
    }

    #[test]
    fn no_db_cannot_prepare_or_score() {
        let mut state = None;
        let message = json!({"type":"score","spi_version":2,"request_id":"r1",
          "context":{"scope":"global","context_track_ids":[]},"candidates":[]});
        assert_eq!(response(&mut state,&message)["type"],"error");
        assert_eq!(response(&mut state,&json!({"type":"describe","spi_version":2}))["type"],"manifest");
        assert_eq!(response(&mut state,&json!({"type":"close","spi_version":2}))["type"],"closed");
    }
    #[test]
    fn experimental_gate_and_exact_identity_on_sqlite() {
        let db = Connection::open_in_memory().unwrap();
        db.execute_batch(
            "CREATE TABLE feature_models(model_key TEXT PRIMARY KEY,aggregation TEXT,classes_json TEXT,validated_against_essentia INTEGER);
             CREATE TABLE feature_tracks(track_file TEXT,model_id TEXT,capability TEXT,model_key TEXT,scores_f32_le BLOB);"
        ).unwrap();
        let labels = serde_json::to_string(&(0..87).map(|i| format!("genre{i}")).collect::<Vec<_>>()).unwrap();
        let values = (0..87).map(|i| if i % 2 == 0 { 0.2_f32 } else { 0.8_f32 })
            .flat_map(f32::to_le_bytes).collect::<Vec<_>>();
        db.execute("INSERT INTO feature_models VALUES(?1,?2,?3,0)",
            params!["fingerprint", AGGREGATION, labels]).unwrap();
        db.execute("INSERT INTO feature_tracks VALUES(?1,'genre','genre',?2,?3)",
            params!["Artist/Song.flac","fingerprint",values]).unwrap();
        assert!(fetch_vector(&db,"Artist/Song.flac","genre","genre",87,false).is_none());
        assert!(fetch_vector(&db,"artist/Song.flac","genre","genre",87,true).is_none());
        assert!(fetch_vector(&db,"Artist/Song.flac","genre","genre",87,true).is_some());
    }
}
