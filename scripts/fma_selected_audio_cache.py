#!/usr/bin/env python3
"""Private bounded GitHub Actions FMA cache: selection-only ZIP plus provenance.

Do not cache the entire 7.2-GiB FMA-Small ZIP; keep only the deterministic
80 research clips, in an internal branch-scoped actions/cache (NOT artifact).
Use 'pack' after the FIRST publisher download and 'verify' on restore.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile

import benchmark_fma_genre as fma

SCHEMA = "fma-small-private-selected-audio-cache-v1"
ENTRY = re.compile(r"^selected/([0-9]{6})[.]mp3$")
FMA_SMALL_SHA256 = "f923bbef327820456d50965c3c320c3c7b6dab8456449429fd78f7ec96a5d02c"
FMA_METADATA_SHA256 = "d9527a5297a65da31c5676484d5047c3e2b8a8060ce72a46e26158be736bf265"
MTG_SHA256 = "bb1efa2876536cbe1a8b67db5dda15249ca144f0cff69e481b638803cbdc9aca"
FILTERED_SAMPLE_SHA256 = "f4a7a81c0713db7619efdba6eb3d561aa70d6d3cc812b4884793953d93b58509"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sample_digest(chosen):
    return digest(",".join(chosen).encode("ascii"))


def verify(bundle: Path, manifest_path: Path, *, metadata: Path,
           mtg: Path | None, screened: bool, per_genre: int = 10,
           seed: int = 20261021, enforce_publisher_shas: bool = True) -> dict:
    if not bundle.is_file() or not manifest_path.is_file():
        raise ValueError("FMA selected cache requires ZIP and manifest")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {
        "schema":SCHEMA,"official_split":"validation","per_genre":per_genre,
        "seed":seed,"screened":screened,
    }
    if any(manifest.get(k)!=v for k,v in expected.items()):
        raise ValueError("FMA selected cache schema/sampling/screen policy mismatch")
    chosen=manifest.get("chosen")
    entries=manifest.get("entries")
    if (not isinstance(chosen,list) or len(chosen)!=8*per_genre
            or len(set(chosen))!=len(chosen)
            or not isinstance(entries,dict) or set(chosen)!=set(entries)
            or not all(isinstance(id,str) and re.fullmatch("[0-9]{6}",id)
                       for id in chosen)
            or sample_digest(chosen)!=manifest.get("sample_id_sha256")):
        raise ValueError("FMA selected cache sample list or ID fingerprint mismatch")
    if screened and per_genre==10 and seed==20261021 and manifest["sample_id_sha256"] != FILTERED_SAMPLE_SHA256:
        raise ValueError("FMA screened sample changed from registered 80-song cohort")
    if enforce_publisher_shas and (
        manifest.get("publisher_audio_zip_sha256")!=FMA_SMALL_SHA256
        or manifest.get("metadata_zip_sha256")!=FMA_METADATA_SHA256
        or (screened and manifest.get("mtg_tsv_sha256")!=MTG_SHA256)
    ):
        raise ValueError("FMA selected cache publisher source fingerprints changed")
    if fma.sha256_file(metadata)!=manifest["metadata_zip_sha256"]:
        raise ValueError("FMA selected cache metadata archive SHA mismatch")
    if screened and (mtg is None or fma.sha256_file(mtg)!=manifest["mtg_tsv_sha256"]):
        raise ValueError("FMA selected cache MTG-screening metadata mismatch")
    if fma.sha256_file(bundle)!=manifest.get("bundle_zip_sha256"):
        raise ValueError("FMA selected cache ZIP SHA mismatch")
    songs=fma.load_fma_small(metadata,include_artist_title=screened)
    if any(id not in songs or songs[id]["split"]!="validation" for id in chosen):
        raise ValueError("FMA selected cache contains nonvalidation or unknown song")
    if len({songs[id]["artist"] for id in chosen})!=len(chosen):
        raise ValueError("FMA selected cache has duplicate artists")
    counts={}
    for id in chosen:
        genre=songs[id]["genre"]
        counts[genre]=counts.get(genre,0)+1
    if len(counts)!=8 or set(counts.values())!={per_genre}:
        raise ValueError("FMA selected cache genre distribution changed")
    if screened:
        excluded,screen=fma.screen_mtg_catalog_matches(songs,mtg,"validation")
        if set(chosen)&excluded or screen["possible_catalog_matches_excluded"]!=manifest.get("catalog_excluded"):
            raise ValueError("FMA selected cache not correctly MTG-screened")
    with zipfile.ZipFile(bundle) as archive:
        if set(archive.namelist())!={f"selected/{id}.mp3" for id in chosen}:
            raise ValueError("FMA selected cache ZIP extra/missing files")
        for id in chosen:
            if not isinstance(entries[id],dict) or entries[id].get("filename")!=f"selected/{id}.mp3":
                raise ValueError("FMA selected cache manifest name mismatch")
            h=hashlib.sha256()
            with archive.open(entries[id]["filename"]) as stream:
                for block in iter(lambda:stream.read(1024*1024),b""):
                    h.update(block)
            if h.hexdigest()!=entries[id].get("audio_sha256"):
                raise ValueError("FMA selected cache MP3 content mismatch")
    return manifest


def pack(audio: Path, metadata: Path, mtg: Path | None,
         *, screened: bool, bundle: Path, manifest_path: Path,
         per_genre: int = 10, seed: int = 20261021,
         enforce_publisher_shas: bool = True) -> dict:
    if bundle.exists() or manifest_path.exists():
        raise FileExistsError("FMA selected ZIP or manifest already exists")
    orig_hash=fma.sha256_file(audio)
    if enforce_publisher_shas and orig_hash!=FMA_SMALL_SHA256:
        raise ValueError("Publisher FMA-Small audio archive SHA changed")
    songs=fma.load_fma_small(metadata,include_artist_title=screened)
    available=fma.match_audio(audio,songs)
    overlap=None
    if screened:
        if mtg is None:
            raise ValueError("Catalog screening requires MTG metadata")
        excluded,overlap=fma.screen_mtg_catalog_matches(songs,mtg,"validation")
        available={id:name for id,name in available.items() if id not in excluded}
    chosen=fma.balanced_sample(songs,available,"validation",per_genre,seed)
    if screened and per_genre==10 and seed==20261021 and sample_digest(chosen)!=FILTERED_SAMPLE_SHA256:
        raise ValueError("FMA frozen 80-song sample does not match original research run")
    bundle.parent.mkdir(parents=True,exist_ok=True)
    manifest_path.parent.mkdir(parents=True,exist_ok=True)
    entries={}
    try:
        with zipfile.ZipFile(audio) as source,zipfile.ZipFile(bundle,"x",
              compression=zipfile.ZIP_STORED,allowZip64=True) as dest:
            for id in chosen:
                path=f"selected/{id}.mp3"
                h=hashlib.sha256()
                with source.open(available[id]) as inp,dest.open(path,"w") as out:
                    for block in iter(lambda:inp.read(1024*1024),b""):
                        out.write(block)
                        h.update(block)
                entries[id]={"filename":path,"audio_sha256":h.hexdigest()}
        result={
            "schema":SCHEMA,"official_split":"validation","per_genre":per_genre,
            "seed":seed,"screened":screened,
            "publisher_audio_zip_sha256":orig_hash,
            "metadata_zip_sha256":fma.sha256_file(metadata),
            "mtg_tsv_sha256":fma.sha256_file(mtg) if screened else None,
            "sample_id_sha256":sample_digest(chosen),
            "catalog_excluded":overlap["possible_catalog_matches_excluded"] if overlap else None,
            "chosen":chosen,"entries":entries,
            "bundle_zip_sha256":fma.sha256_file(bundle),
        }
        with manifest_path.open("x",encoding="utf8") as out:
            json.dump(result,out,indent=2,allow_nan=False)
        verify(bundle,manifest_path,metadata=metadata,mtg=mtg,screened=screened,
               per_genre=per_genre,seed=seed,enforce_publisher_shas=enforce_publisher_shas)
        return result
    except BaseException:
        bundle.unlink(missing_ok=True)
        manifest_path.unlink(missing_ok=True)
        raise


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode",choices=("pack","verify"))
    p.add_argument("--bundle",type=Path,required=True)
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--source-audio-zip",type=Path)
    p.add_argument("--metadata-zip",type=Path,required=True)
    p.add_argument("--mtg-metadata-tsv",type=Path)
    p.add_argument("--screened",action="store_true")
    p.add_argument("--per-genre",type=int,default=10)
    p.add_argument("--seed",type=int,default=20261021)
    args=p.parse_args()
    if args.mode=="pack":
        if args.source_audio_zip is None:
            p.error("pack requires --source-audio-zip")
        result=pack(args.source_audio_zip,args.metadata_zip,args.mtg_metadata_tsv,
                    screened=args.screened,bundle=args.bundle,manifest_path=args.manifest,
                    per_genre=args.per_genre,seed=args.seed)
    else:
        result=verify(args.bundle,args.manifest,metadata=args.metadata_zip,
                      mtg=args.mtg_metadata_tsv,screened=args.screened,
                      per_genre=args.per_genre,seed=args.seed)
    print(json.dumps({
        "mode":args.mode,"files":len(result["chosen"]),
        "sample_id_sha256":result["sample_id_sha256"],
        "publisher_archive_sha256":result["publisher_audio_zip_sha256"],
        "bundle_mib":round(args.bundle.stat().st_size/1024**2,2),
        "status":"FMA private selected-song cache validated"
    },indent=2))


if __name__=="__main__":
    main()
