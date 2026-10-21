#!/usr/bin/env python3
"""Apply an explicitly scoped research overlay to immutable PR-17 Rust-v5 checkout.

The overlay is maintained exclusively on PR #16. It refuses any source
revision other than the pinned, numerically reviewed Rust-v5 commit.
It never cherry-picks or merges PR #17 into this branch.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess

PIN = "2c3d44401436b3b41b6e067199016a1ed2335fbf"


def once(data: str, old: str, new: str, label: str) -> str:
    count = data.count(old)
    if count != 1:
        raise ValueError(f"{label}: expected one exact source anchor, found {count}")
    return data.replace(old, new, 1)


def patch_features(data: str) -> str:
    data = once(
        data,
        "    encoder: Session,\n    heads: Vec<(Profile, Session)>,",
        "    encoder: Session,\n    heads: Vec<(Profile, Session)>,\n"
        "    embedding_enabled: bool,\n"
        "    last_song_embedding: Option<crate::song_embedding::SongEmbedding>,",
        "engine fields",
    )
    data = once(
        data,
        "counted_load: false, threads, frontend,",
        "counted_load: false, threads, frontend,\n"
        "            embedding_enabled: false, last_song_embedding: None,",
        "engine constructor",
    )
    data = once(
        data,
        "    pub fn analyze(&mut self, path: &Path, max_patches: Option<usize>) -> Result<FeatureReport> {",
        """    /// Explicit opt-in on a one-song research command, never on normal scans.
    pub fn request_song_embedding(&mut self) {
        self.embedding_enabled = true;
    }

    pub fn take_song_embedding(&mut self) -> Option<crate::song_embedding::SongEmbedding> {
        self.last_song_embedding.take()
    }

    pub fn analyze(&mut self, path: &Path, max_patches: Option<usize>) -> Result<FeatureReport> {
        self.last_song_embedding = None;""",
        "opt-in API",
    )
    data = once(
        data,
        "        let count = patches.len();\n        let mut sums: Vec<Vec<f64>>",
        "        let count = patches.len();\n"
        "        let mut embedding_sums = self.embedding_enabled.then(|| vec![0.0_f64; crate::song_embedding::DIMENSIONS]);\n"
        "        let mut sums: Vec<Vec<f64>>",
        "optional accumulator",
    )
    data = once(
        data,
        '            let vector = vector.context("EffNet did not output a 1280-dimensional embedding")?;\n',
        '            let vector = vector.context("EffNet did not output a 1280-dimensional embedding")?;\n'
        '            if let Some(ref mut embedding_sums) = embedding_sums {\n'
        '                crate::song_embedding::add_patch(embedding_sums, &vector)?;\n'
        '            }\n',
        "raw patch aggregation",
    )
    data = once(
        data,
        "        let audio_hash = sha256_file(path)?;\n        let hash_seconds = at_hash.elapsed().as_secs_f64();",
        """        let audio_hash = sha256_file(path)?;
        if let Some(ref embedding_sums) = embedding_sums {
            let profile = &self.heads[0].0;
            let model = &profile.descriptor.embedding_model;
            let model_sha256 = profile.hashes.get(model)
                .context("No encoder SHA256 for embedding export")?;
            self.last_song_embedding = Some(crate::song_embedding::build(
                embedding_sums, count, model, model_sha256, self.preprocessing, &audio_hash,
            )?);
        }
        let hash_seconds = at_hash.elapsed().as_secs_f64();""",
        "post-inference embedding assembly",
    )
    return data


def patch_main(data: str) -> str:
    data = once(data, "mod features;\n", "mod features;\nmod song_embedding;\n", "module")
    data = once(
        data,
        """        #[arg(long)]
        track_key: Option<String>,
    },
    /// Incremental, model-independent sidecar analysis; legacy mood_tracks remain untouched.""",
        """        #[arg(long)]
        track_key: Option<String>,
        /// Write a separate, versioned song embedding JSON; off by default.
        #[arg(long)]
        embedding_out: Option<PathBuf>,
    },
    /// Incremental, model-independent sidecar analysis; legacy mood_tracks remain untouched.""",
        "analyze-features CLI opt-in",
    )
    data = once(
        data,
        """            essentia_worker, essentia_timeout_seconds, max_patches, threads, json, db, track_key,
        } => {""",
        """            essentia_worker, essentia_timeout_seconds, max_patches, threads, json, db, track_key,
            embedding_out,
        } => {""",
        "CLI destructuring",
    )
    data = once(
        data,
        """            let mut engine = features::FeatureEngine::with_backend(profiles, threads, &backend)?;
            let report = engine.analyze(&source, max_patches)?;
            if let (Some(db), Some(key)) = (db.as_deref(), track_key.as_deref()) {""",
        """            let mut engine = features::FeatureEngine::with_backend(profiles, threads, &backend)?;
            if embedding_out.is_some() {
                engine.request_song_embedding();
            }
            let report = engine.analyze(&source, max_patches)?;
            if let Some(output) = embedding_out.as_deref() {
                let mut embedding = engine.take_song_embedding()
                    .context("Requested embedding was not produced")?;
                embedding.track_file = track_key.clone();
                song_embedding::write_new(output, &embedding)?;
            }
            if let (Some(db), Some(key)) = (db.as_deref(), track_key.as_deref()) {""",
        "CLI export and existing DB path",
    )
    return data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--module", type=Path, default=Path("research/song_embedding.rs"))
    args = parser.parse_args()
    checkout = args.checkout.resolve()
    head = subprocess.check_output(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True,
    ).strip()
    if head != PIN:
        raise SystemExit(f"Refusing non-pinned Rust-v5 revision: {head}")
    features = checkout / "src/features.rs"
    main_rs = checkout / "src/main.rs"
    modified_features = patch_features(features.read_text(encoding="utf-8"))
    modified_main = patch_main(main_rs.read_text(encoding="utf-8"))
    if not args.module.is_file():
        raise FileNotFoundError(args.module)
    # All anchors verified prior to any filesystem changes.
    features.write_text(modified_features, encoding="utf-8")
    main_rs.write_text(modified_main, encoding="utf-8")
    shutil.copyfile(args.module, checkout / "src/song_embedding.rs")
    print(f"Overlay applied to pinned Rust-v5 {PIN}; original git tree remains available for diff")


if __name__ == "__main__":
    main()
