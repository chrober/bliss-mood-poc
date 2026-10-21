## Einstieg: zentrale Roadmap und aktuelle Phasenzuordnung (21.10.2026)

**Bitte als erstes lesen:** [Song-Similarity bis Lyrion-Integration – Roadmap Phase 0–6](similarity-lyrion-roadmap.md).
Vier GitHub-renderbare Mermaid-Diagramme, Status und
kleine Stop-/Go-Pakete. Dieses Dokument ist der
**aktuelle Gesamtplan**; historische Handover-Abschnitte
darunter können mittlerweile abgeschlossene Arbeiten
noch als „offen“ bezeichnen und sind chronologisch
zu interpretieren.

**„Analysierte Song-Features“:**
Phase **0** erzeugt 87D Genre, 56D Mood und
optional 1280D Audio-Embeddings offline;
Phase **2** prüft / vervollständigt die drei
Repräsentationen auf **denselben** lokalen
Library-Songs ohne Full-Rescan;
Phase **6** umfasst erst nach Qualitäts-, Lizenz-
und Ressourcenprüfung produktive Vollständigkeit.
Die 1280D-Embeddings sind nicht automatisch
in der lokalen schema-v3-Feature-DB vorhanden.

**Nächster Schritt:** isolierter DEAM-Host-/SHA-Preflight;
bei weiter bestehendem externem Blocker lokal
read-only Feature-Completeness L0,
danach gesonderter 12-Kontraste-Hörpilot.
FMA-80-Selected-Clip-Cache wurde warm
und cross-workflow erfolgreich verifiziert.
PR #16 bleibt Draft, keine Produktionsänderung.

## AKTUELLER FORSCHUNGSHANDOVER — Repräsentation statt nur Metrik (21.10.2026)

**Bitte in der nächsten Chat-Session ZUERST lesen:**
[Ausführlicher Drei-Ansätze-Handover](similarity-three-representation-approaches-handover-2026-10-21.md).
Dieser Abschnitt ist die **neue Arbeitspriorität**; ältere Meldungen darunter
dokumentieren abgeschlossene Implementierung und Benchmarks.

Wir möchten die **musikalische Ähnlichkeit zweier analysierter Songs**
bestimmen. Bisher wurde nur die Frage getestet, welche von sieben
Distanz-/Similarity-Metriken auf **87D Genre- und 56D Mood/Theme-
Klassifikationsvektoren** gut funktioniert. Jetzt muss zusätzlich
die **Repräsentation** selbst untersucht werden:

1. **A — Classifier-Vektoren:** Genre 87D / Mood 56D getrennt;
   bereits implementiert und auf FMA, DEAM und MagnaTagATune
   gegen externe Referenzen getestet. Genre-/Mood-Cosine,
   Centered Cosine und Weighted Jaccard bleiben Baselines.
2. **B — Audio-Embeddings:** den **1280D Discogs-EffNet-Patch-Vektor
   vor den beiden ONNX-Klassifikationsköpfen** als Song-Embedding
   (anfangs Patch-Mittelwert, dann L2/Cosine) experimentell
   bereitstellen und validieren. Externes Beispiel:
   [cosine.club FAQ](https://cosine.club/about); außerdem
   [Essentia-Embedding- und Contrastive-Modelle](https://essentia.upf.edu/models.html).
   **Im derzeitigen Feature-Sidecar NICHT persistiert oder evaluiert.**
   Der Encoder erzeugt 1280D intern; echtes Rust-v5-Ausgabeschema,
   Pooling und numerische Essentia-Parität sind offen.
3. **C — Fusion:** normalisierte/kalibrierte Similarity aus 1280D
   Audio + 87D Genre + 56D Mood mit **festen Ablationen**,
   erst später Development-only-Gewichtsoptimierung.
   **B und C wurden noch nicht auf unseren Datensätzen gemessen.**

**Unbedingt zwei Ebenen unterscheiden:**
Die obigen drei **Feature-Repräsentationsansätze** sind NICHT
die drei *Lyrion-Kandidatenstrategien*
**Bliss-first / Mood-/Genre-/Embedding-first / Hybrid
aus Kandidatenquellen**; letztere sind eine davon getrennte
Produkt-/Host-Entscheidung. Ein Feature-Fusion-Score kann
auch in einem Bliss-first-Reranking verwendet werden.
Siehe [Lyrion-Integrationskonzept](lyrion-bliss-mood-genre-integration.md).

**Evidenz / Grenzen:** Auf MTT alle **346** einzigartigen Triple-Fragen
(293 eindeutige Menschen-Mehrheiten, 1019 Clips) nur für A evaluiert;
**kein MTT-Holdout** mehr. FMA Validierungs-Audit fand **42/800**
mögliche MTG-Jamendo Künstler-/Titel-Katalogtreffer (kein
Nachweis von Audio-/Trainingsidentität); der gefilterte
FMA-Validierungslauf mit 80 anderen Songs PASS, offizieller
FMA-TEST-Split unberührt. DEAM Mood Valence/Arousal ist nur
ein Proxy für die 56D-Kategorien. Keine der Metriken ist
als Produktionsstandard bewiesen. Siehe
[Cross-Dataset-Evidenz](similarity-cross-dataset-evidence-2026-10-21.md).

**Konkret als Nächstes:** Den gepinnten, korrigierten
Rust-v5-Encoder aus PR #17 (immutable Revision
`2c3d44401436b3b41b6e067199016a1ed2335fbf`)
prüfen; minimalinvasiv versionierte 1280D-Ausgabe
plus Patch-Pooling bereitstellen, gegen Essentia
numerisch prüfen, auf identischen lizenzierten
Entwicklungsclips zuerst **A vs B** testen,
anschließend **C** mit vorab festgelegten Gewichten.
Vier isolierte GH-Actions-Worker / kuratierter
119.689.247-Byte-MTT-Audiocache und gepinnter
Rust-v5-Binary-Cache sind bereits vorhanden;
nur Versions-/Cache-Anpassungen nach Änderungen,
keinen privaten Bibliotheks-Rescan und keinen
FMA-TEST-Zugriff. Keine Produktionsänderung und
kein Merge nach `main`; PR #16 Draft,
PR #13 und PR #17 nicht verändern.
Bei neuen Resultaten diesen Handover **und** den
ausführlichen Drei-Ansätze-Handover aktualisieren.

---

> **NEUER HAUPT-HANDOVER — 21.10.2026: DREI REPRÄSENTATIONSANSÄTZE FÜR SONG-SIMILARITY**
>
> **Eindeutige Lesereihenfolge für die nächste Chat-Session:**
> 1. [**Maßgebliches Drei-Ansätze-Handover**](similarity-three-representation-approaches-handover-2026-10-21.md) — Entscheidungsebene, Ziele, Ist-Stand und konkrete E1-Implementierungsaufgabe.
> 2. [**Technischer Anhang zu A/B/C**](similarity-representation-comparison-handover-2026-10-21.md) — Formeln, Persistenz-/Poolingvertrag, Messplan, Benchmarks und Qualitäts-Gates.
> Beide Dokumente behandeln denselben Forschungswechsel; keines enthält eine bereits gemessene Überlegenheit von B oder C.
>
> | Neuer Similarity-Ansatz | Repräsentation | Implementierungsstand |
> | --- | --- | --- |
> | **A Klassifikations-Similarity** | 87D Genre und 56D Mood/Theme Sigmoid-Score-Vektoren; sieben bisher untersuchte Metriken pro Kopf | **Vorhanden**; FMA Validation, DEAM VA-Proxy und volle MTT-Tripel explorativ evaluiert; kein eindeutiger Sieger |
> | **B Direkte Audio-Embedding-Similarity** | **1.280D Discogs-EffNet-Embedding vor dem Klassifikationskopf**; Song-Pooling, L2-Normierung und Cosine als erste Baseline | **Pro Patch schon intern berechnet**, aber **nicht als Song-Level-Vektor gespeichert oder evaluiert** |
> | **C Späte Fusion** | Getrennte, kalibrierte/rangbasierte Kombination von Embedding-, Genre- und Mood-Nähe für ein definiertes Musikziel | **Hypothese**, noch nicht getestet oder produktiv gewählt |
>
> **Zwei Ebenen nicht verwechseln:** A/B/C sind Audio-*Repräsentationen*
> und Similarity-/Rank-Policies. `Bliss-first`, `Mood-/Genre-first`
> und `Hybrid` sind eigenständige *Lyrion-Kandidaten-/Mixstrategien*
> ([Strategieentscheid](lyrion-bliss-mood-genre-integration.md)).
> Embedding-/Head-Fusion (C) ist nicht dasselbe wie eine
> `Hybrid`-Kandidatengenerierung in Lyrion.
>
> **Technisches Faktum:** `src/features.rs` besitzt je Patch
> bereits einen Float32-1280D-Vektor aus
> `discogs-effnet-bsdynamic-1.onnx`, der die Head-Scores erzeugt.
> Der gegenwärtige schema-v3-Sidecar speichert nur die 87/56D
> Head-Aggregate (`feature_tracks.scores_f32_le`), **keine 1280D-
> Song-Embeddings**. Für B zuerst einen **optionalen, versionierten
> Song-Embedding-Export** ergänzen: rohe Patches mitteln, erst
> danach Song-Vektor für Cosine L2-normalisieren; Encoder-/Modell-
> Hash, Pooling-Version, Patchcount, Floatformat, CRC/Nullnorm-
> Grenzen und Rust-v5-Head-Parität prüfen. Kein zweiter Encoder-
> Lauf für identische Patches nötig.
>
> **Externe Vorbilder:** Offizieller Essentia-Katalog beschreibt
> separate *kontrastive* Artist/Label/Release/Track/Multi-Modelle;
> diese sind **andere Gewichte/Ziele** und dürfen nicht stillschweigend
> gegen unseren aktuellen Style-Klassifikations-Encoder ausgetauscht
> werden. [cosine.club](https://cosine.club/about) nutzt bereits
> **Discogs-EffNet-1280D + Cosine** für produktive Musikähnlichkeitssuche
> (Beleg für Realisierbarkeit, **nicht** für bessere Lyrion-Qualität).
>
> **Priorität der nächsten Session:** (P0) Schema/Pooling/Regression für B
> implementieren und gegen Essentia-/Python-Referenz prüfen; (P1) B auf
> denselben vorhandenen, rechtmäßig erreichbaren FMA-/DEAM-/MTT-Tracks
> mit A vergleichen, Kosten/CI/Abstentionen messen; (P2) C mit
> wenigen eingefrorenen Gewicht-/Rank-Policies testen, **ohne**
> unberührten FMA-TEST zu öffnen oder MTT wieder als Holdout
> auszugeben. Erst danach separater Lyrion-Bliss-first/Feature-first/
> Hybrid- und Hörtest. GitHub Actions mit Cache, Path-Triggern,
> passenden Workern und Stage-Zeiten betreiben.
>
> **Forschungsgates:** 346 MTT-Tripel schon komplett exploriert
> (53 menschliche Mehrheits-Ties, 293 auswertbar; **kein MTT-Holdout**).
> FMA official TEST weiterhin gesperrt; FMA Validation 42/800 mögliche
> Artist-/Title-Katalogtreffer gegen MTG, **keine bewiesenen Trainings-
> Duplikate**; DEAM VA kein direktes 56-Tag-Ground-Truth.
> B/C sind **noch nicht** evaluiert; keine behauptete Embedding-
> Überlegenheit, keine fixen Fusionsgewichte und **kein**
> Produktionsmetrikwinner. Kein Scan privater Musik, keine Audio-
> Weitergabe, `main`/PR #13/#17 unberührt, Draft PR #16.
>

> **CURATED CACHE REAL MISS→HIT VERIFIED (21 OCT 2026):**

> **FMA CATALOG-FILTERED GENRE VALIDATION FINISHED (21 OCT 2026):**
> [Real filtered run 39606850307](https://github.com/chrober/bliss-mood-poc/actions/runs/39606850307)
> **PASS**, [aggregate artifact 12349595666](https://github.com/chrober/bliss-mood-poc/actions/runs/39606850307/artifacts/12349595666).
> The preflight removed **42 possible exact FMA VALIDATION /
> MTG-Jamendo artist+title catalog matches among 800**,
> including 35/100 Hip-Hop. All 80 selected validation
> MP3s then analyzed with distinct artists, 10 per
> top-level genre, pinned corrected Rust-v5, official
> publisher music, **no FMA TEST use**. Verified Rust-v5
> binary cache HIT and no Cargo build; no FMA audio cached
> or uploaded.
>
> Filtered FMA Genre **Precision@5**:
> RMS **0.3000**, Cosine **0.3200**, Centered Cosine
> **0.3225**, Weighted Jaccard **0.3000**, old cutoff
> Top-K WJ **0.3025**, Ranked Top-6 **0.3125**, Ranked
> Top-12 **0.3050**. Centered Cosine leads narrowly
> on filtered P@5 and mAP@10 (**0.1781**), Ranked
> Top-6 on filtered nDCG@10 (**0.3048** versus
> Centered **0.3043**). Random P@5 expected **0.113924**;
> all seven metrics had 80 query scores.
> Previous unfiltered 80-song FMA validation numbers
> are from a DIFFERENT cohort; comparing them is
> descriptive, **NOT a paired estimate of overlap
> effects, not proof of ONNX training disjointness**.
> A corpus-level metadata coincidence does NOT
> establish shared audio or training usage.
>
> Completed [FMA catalog research doc](fma-mtg-catalog-overlap-2026-10-21.md)
> and [FMA plan](fma-genre-benchmark-plan.md) should
> be read with [cross-dataset evidence](similarity-cross-dataset-evidence-2026-10-21.md).
> **Next:** preregister expanded validation and
> paired-query Genre scoring, audit actual model
> training split/encoder provenance, only then
> unlock FMA TEST as a single independent check;
> consider separate human transition judgments.
> PR #16 Draft; no merge, no local/private music
> scan or updates to PR #13/#17.
>

> **FMA–MTG CATALOG SCREEN COMPLETED / FILTERED VALIDATION RUNNING (21 OCT 2026):**
> Metadata-only [GitHub Actions 39605675932](https://github.com/chrober/bliss-mood-poc/actions/runs/39605675932)
> **PASS**, aggregate [artifact 12347897819](https://github.com/chrober/bliss-mood-poc/actions/runs/39605675932/artifacts/12347897819).
> On FMA-Small **TRAINING**: 121/6,400 possible exact
> artist+title MTG-Jamendo catalog matches, 260 artist-only
> matches. On official **VALIDATION**: **42/800 possible
> exact matches**, 68 artist-only; of those exact matches,
> **35 of 100 Hip-Hop validation songs**. TEST's 800 records
> were counted only for official split-size checking; NO
> TEST artist/title/genre/MP3/prediction was examined.
> These are **possible metadata matches, not verified
> recordings or actual ONNX training examples**.
> Existing 80-song unfiltered VALIDATION result is NOT
> guaranteed MTG-independent.
>
> Added `scripts/audit_fma_mtg_overlap.py`, synthetic tests,
> [.github/workflows/fma-mtg-overlap-audit.yml](../.github/workflows/fma-mtg-overlap-audit.yml);
> extended `scripts/benchmark_fma_genre.py` with
> `--exclude-mtg-catalog-matches --mtg-metadata-tsv PATH`
> for **validation-only**, filtering potential exact matches
> BEFORE artist-distinct sample selection and inference.
> The official TEST partition is now skipped before
> even parsing its song ID in this discovery CLI.
> [Linux+Windows Python CI 39606799883](https://github.com/chrober/bliss-mood-poc/actions/runs/39606799883)
> PASS after correcting synthetic sealed TEST-row fixture.
> New [filtered FMA workflow 39606850307](https://github.com/chrober/bliss-mood-poc/actions/runs/39606850307)
> has verified its source/42-match metadata preflight,
> a TRUE pinned Rust-v5 binary-cache HIT, and is downloading
> the official 7.2-GiB FMA-Small ZIP (no audio caching).
> **CHECK final PASS/artifact before reporting filtered
> genre-retrieval scores or new walltimes**. New sample
> differs from old unfiltered 80-track cohort; score
> deltas CANNOT be interpreted as a controlled causal effect.
>
> Research details:
> [FMA/MTG catalog methodology](fma-mtg-catalog-overlap-2026-10-21.md),
> [FMA genre validation plan](fma-genre-benchmark-plan.md),
> [cross-dataset evidence](similarity-cross-dataset-evidence-2026-10-21.md).
> No TEST evaluation, PR merge, Lyrion queue/library scan,
> or production metric selection; PR #16 remains Draft.
>

> **MTT FOUR-WORKER BINARY+MUSIC CACHE A/B COMPLETED (21 OCT 2026):**
> [Four-worker run 39602865932](https://github.com/chrober/bliss-mood-poc/actions/runs/39602865932)
> **PASS** ([aggregate artifact 12346509848](https://github.com/chrober/bliss-mood-poc/actions/runs/39602865932/artifacts/12346509848)).
> It reused BOTH caches: previously verified **119,689,247-byte
> 1,019-clip** research package and source-keyed Linux Rust-v5
> binary, verified its cached checksum and CLI; original 2.77-GiB
> download and Cargo toolchain/build **SKIPPED**.
> Four independent Rust-v5 processes (ONNX `--threads 1` each)
> processed all 1,019 clips against the identical 346-triplet
> human questions. **Actual 4-worker inference+SQLite merge:
> 172.324 s**, score 0.929 s. The completed 2-worker paired
> [run 39602475906](https://github.com/chrober/bliss-mood-poc/actions/runs/39602475906)
> needed **291.251 s** inference+merge, 1.053 s score. Thus
> **118.927 s / 40.8% faster observed inference** in these
> two runs; full actual job execution from first/last logs
> **~228 s vs ~367 s**, BUT 2-worker run compiled Rust and
> hosted-runner variability is large. Not a controlled claim
> of general speedup. All **14 metric/head scorecard rows
> and 8 displayed paired contrast rows match exactly** between
> completed two- and four-worker reports; per-track float-bit parity
> not checked from aggregate-only reports.
>
> **COMPLETED PAIRED EVIDENCE:** real 2-worker paired
> [39602475906](https://github.com/chrober/bliss-mood-poc/actions/runs/39602475906)
> PASS, aggregate artifact 12347665613; on the common 293
> MTT human-majority-scorable triplets, Cosine minus
> Centered Cosine **0.0 pp Genre (5/5 discordance),
> −0.3 pp Mood (8/9 discordance)**. Exploratory
> paired IID-triplet and artist-weight sensitivity intervals
> straddle zero in both heads, NOT independent population
> confidence intervals. Cosine minus old Top-K WJ
> +5.1 pp Genre and +21.2 pp Mood when abstentions
> counted as errors. No production winner or independent
> MTT holdout. See
> [paired/performance document](magnatagatune-paired-analysis-2026-10-21.md)
> and [cross-dataset evidence](similarity-cross-dataset-evidence-2026-10-21.md).
> Keep 4 fixed workers provisionally in expensive exploratory
> GH workflow, only change with matched A/B evidence;
> adaptive local scanner not active in this GH runner.
> PR #16 Draft, `main`, PR #13/#17 and private library untouched.
>

> **MTT PAIRED EVIDENCE AND RUST-V5 BINARY CACHE (21 OCT 2026):**
> The confirmed full [curated-audio cache HIT run 39600498519](https://github.com/chrober/bliss-mood-poc/actions/runs/39600498519)
> reported **346 unordered triplets; 53 human-majority ties; 293
> common scorable questions**, 1,019 clips, two Rust-v5 subprocess
> workers, 231.053 seconds inference + merge; complete GitHub run
> 327 seconds. The 1,019-clip audio package was just **119,689,247
> bytes**, CRC-verified against original publisher metadata, and
> prevented the full 2.77-GiB download.
>
> Real scores on a COMMON 293-question denominator, with metric
> abstentions counted as incorrect: **Genre** RMS 63.5%, Cosine
> 65.2%, Centered Cosine 65.2%, Weighted Jaccard 63.8%,
> old Top-K Weighted Jaccard 60.1%, Ranked Top-6 61.8%,
> Ranked Top-12 64.5%. **Mood** respectively 54.6%, 65.5%,
> 65.9%, 61.1%, **44.4% old Top-K with only 71.7% coverage**,
> 62.5%, 64.8%. Cosine-Centered Mood difference ~0.4pp;
> **NOT enough for a metric-winner claim**, same corpus and
> no unseen holdout.
>
> [scripts/mtt_paired_evidence.py](../scripts/mtt_paired_evidence.py)
> and [tests/test_mtt_paired_evidence.py](../tests/test_mtt_paired_evidence.py)
> implement 21 paired contrasts/head (42 total) on the identical
> 293 human-scorable questions, metric abstentions as zero,
> deterministic 600x shared-triplet bootstrap intervals and
> artist-weight dependency *sensitivity* intervals. These are
> **not valid population CIs or a formal independent-cluster
> bootstrap**: all 214 artists are connected. No per-song
> ID, vector or answer is exported. Linux and Windows
> [Python CI 39602141111](https://github.com/chrober/bliss-mood-poc/actions/runs/39602141111)
> PASS. The first synthetic CI failure was a test wording assertion
> only and was corrected without changing math.
> Actual paired 2-worker benchmark
> [39602475906](https://github.com/chrober/bliss-mood-poc/actions/runs/39602475906)
> requires final PASS/artifact verification before quoting
> numerical paired intervals.
>
> Workflow now also caches the pinned exact **Rust-v5 compiled
> binary**, separate from licensed clip cache; verifies SHA256 and
> CLI before use; a MISS builds with locked Cargo and saves it.
> To A/B runtime, the next automatic
> [39602865932](https://github.com/chrober/bliss-mood-poc/actions/runs/39602865932)
> is configured with **four** isolated workers, ONNX 1 thread
> each, vs previous **two** on the same 1,019-clip cohort.
> Do NOT claim a 4-worker speedup or metric parity before
> real run completion.
> Full detailed [scientific/performance handover](magnatagatune-paired-analysis-2026-10-21.md).
> Next: verify both runs, compare paired uncertainty and A/B
> walltimes, cross-reference DEAM/FMA, seek independent perceptual
> test, no production choice. PR #16 Draft; main, PR #13/#17,
> private music unchanged.
>
> [First curated run 39599548243](https://github.com/chrober/bliss-mood-poc/actions/runs/39599548243)
> **PASS**: `scripts/mtt_selected_clip_cache.py` packed exactly
> 1,019 CRC-verified referenced MagnaTagATune MP3s into
> **119,689,247 bytes (114.14 MiB)**; all official CRCs/lengths
> verified before Rust-v5. Packaging took **1.18 s**, full recheck
> **0.59 s**. Only this package was saved in `actions/cache`;
> original 2.77-GiB publisher files were deleted and never cached.
> Actual Actions cache storage approx 130.5 MB.
> The exact two-worker Genre/Mood 346-triple benchmark again
> passed with Mood-Cosine **0.6552901** valid-prediction
> majority accuracy. Its analysis+merge took **244.677 s** vs
> **145.505 s** on earlier full-source run: avoid claiming a
> controlled inference speedup from cache alone.
> [Second run 39600498519](https://github.com/chrober/bliss-mood-poc/actions/runs/39600498519)
> verified a **true cache HIT**: publisher source ZIP download
> and repack steps were SKIPPED, package reverified from original
> 8-MiB central-directory tail; check final Actions result and
> fourteen-row head×metric scorecard before reporting total timings.
> Dedicated offline tests for complete, corrupt/missing clip caches
> and scorecard run in Linux/Windows
> [Python CI 39600399370](https://github.com/chrober/bliss-mood-poc/actions/runs/39600399370)
> PASS. The 346 unique triplets are fully exploratory, with
> **NO independent MagnaTagATune holdout** remaining.
> Further tasks: compare MISS/HIT true stage times, compile
> all-metric coverage/abstention scorecard, improve build
> reuse and do dependence-aware uncertainty analysis across
> co-occurring artists; corroborate on DEAM, FMA, and independent
> human similarity sources before any production metric choice.
> No music in git or upload-artifact; GH caches not confidential.
>

> **CURATED MTT AUDIO CACHE — 21 OCT 2026:**
> User approved caching **ONLY 1,019 actually referenced MagnaTagATune
> MP3 clips**, rather than the 2.77-GiB original ZIP parts. New
> [scripts/mtt_selected_clip_cache.py](../scripts/mtt_selected_clip_cache.py)
> builds a lossless, deterministic **ZIP_STORED curated research cache**
> of approximately 117 MB (real size must be checked in Actions), with
> SHA-256-hashed internal names, exact 1,019-file cardinality, and
> original-publisher MP3 length + CRC cross-checks. Original 3-part
> archive downloaded *once on cache miss*, immediately deleted after
> packing and never uploaded or cached. Cache hit only fetches original
> CSV metadata plus 8-MiB ZIP directory tail, validates all 1,019 audio
> payloads, then Rust-v5's **two independent workers** process cached
> bytes. Automated feature-branch workflow uses
> [actions/cache/restore](../.github/workflows/magnatagatune-all-exploratory.yml)
> and cache/save with fixed source identity, manual `cache_audio`
> defaults true and can be disabled. GitHub caches **are not private**,
> third-party CC BY-NC-SA research audio remains subject to access and
> license conditions; no music is ever uploaded as an artifact or git.
>
> **REAL QUALITY BASELINE VERIFIED:**
> [346-triplet run 39597229438](https://github.com/chrober/bliss-mood-poc/actions/runs/39597229438)
> PASS: 1,019 real clips, all seven metrics/both heads,
> two parallel isolated SQLite workers; **145.505 s inference+merge**,
> 145.714 s audio-analysis+scoring, 0.209 s evaluation alone.
> Mood cosine ~**0.6553** majority agreement on *defined*
> predictions (not all-question/holdout accuracy). All 346 triplets
> exploratory => **NO independent MTT holdout remains**.
> Curated-cache seed run
> [39599548243](https://github.com/chrober/bliss-mood-poc/actions/runs/39599548243)
> must be examined for completed outcome and actual saved package
> size; **a second true cache-hit run is required** to measure any
> build/download speedup. The synthetic 1,019-member CRC/cache tests
> [Python CI 39599073019](https://github.com/chrober/bliss-mood-poc/actions/runs/39599073019)
> passed Linux/Windows. See the
> [updated sparse-audio benchmark doc](magnatagatune-sparse-audio-benchmark-2026-10-21.md).
> Next: verify cache MISS→HIT timing and metric parity, run
> paired / artist-sensitive confidence intervals on 346 triplets,
> cross-check DEAM/FMA/MTG and seek independent human similarity
> reference for final production metric choice. Do not use MTT as
> an independent held-out test, merge PRs, or rescan private music.
>

> **FULL 346-TRIPLET EXPLORATORY MTT & CACHE POLICY (21 Oct 2026):**
> The user decided to score **ALL 346 unique unordered triplets /
> 1,019 distinct MagnaTagATune clips**, consuming the 48
> previously untouched artist-holdout candidates. This is explicitly
> **exploratory only; there is NO remaining independent MTT holdout**.
> New `scripts/benchmark_magnatagatune.py --selection-mode all-exploratory`
> uses pinned source file hashes and exact 346/1019 cardinality.
> New `scripts/mtt_parallel_workers.py` uses **2 concurrent isolated
> Rust-v5 processes, --threads 1 each**, separate schema-v3 SQLite
> sidecars, validated/merged only after completion; no shared
> concurrent SQLite writer. `scripts/mtt_local_archive.py` can read
> ZIP members from the three staged publisher files without per-clip
> HTTP calls. Real job
> [39597229438](https://github.com/chrober/bliss-mood-poc/actions/runs/39597229438)
> was triggered; check actual completed outcome/artifacts BEFORE
> claiming 346-triplet scores or parallel performance.
> Workflow [.github/workflows/magnatagatune-all-exploratory.yml](../.github/workflows/magnatagatune-all-exploratory.yml)
> runs only on its own file update or manual dispatch.
>
> **Audio cache is opt-in** via manual `workflow_dispatch`
> `cache_audio: true`, not enabled by default. The full licensed
> archive is 2.77 GiB, a large fraction of GitHub default
> 10-GiB repository cache; default inactivity eviction ~7 days.
> Caches are accessible to certain PRs/forks, so review research
> CC BY-NC-SA 3.0 rights and accessibility before storing the audio.
> Even a cache hit must pass publisher size + MP3 CRC checks; always
> measure hit/restore vs publisher download, not assume it is faster.
> No raw audio, per-track features or private data in run artifacts.
> See [sparse audio doc](magnatagatune-sparse-audio-benchmark-2026-10-21.md).
>

> **NEW MTT ARTIST-FROZEN DEVELOPMENT BENCHMARK, 21 OCT 2026:**
> `scripts/benchmark_magnatagatune.py --selection-mode frozen-development`
> and workflow [magnatagatune-development.yml](../.github/workflows/magnatagatune-development.yml)
> implement **all 31 artist-only development triplets** using the locked
> 128/256 SHA-256 artist split. The script verifies both count and
> triplet fingerprint BEFORE audio. It excludes the **56** holdout
> candidates and **259** mixed triples, and NEVER scores the
> **48 still-unexposed holdout questions**.
> Synthetic coverage includes leakage prevention on Linux and Windows.
> First real run [39593423801](https://github.com/chrober/bliss-mood-poc/actions/runs/39593423801)
> failed on a transient HTTP 000 / curl exit 28 when downloading
> clip 22 of 92; 21 legitimate clips already analyzed, no scores
> reported. Bounded HTTP retries with preserved 206/CRC/size guards
> implemented and verified by [Python tests 39594080260](https://github.com/chrober/bliss-mood-poc/actions/runs/39594080260).
> Corrected repeat [39594161136](https://github.com/chrober/bliss-mood-poc/actions/runs/39594161136)
> was started: CHECK real completion / artifact before quoting scores.
> Documented in [MTT sparse audio benchmark](magnatagatune-sparse-audio-benchmark-2026-10-21.md).
> Keep stage runtime, worker count and Rust build/download trade-offs
> visible. No holdout optimization, production metric choice, merge, local
> user library scan or raw audio artifact.
>
# Chat handover — adaptive offline feature scans (2026-10-19)

> **UPDATED MTT HOLDOUT METADATA AUDIT, 21 OCT 2026:**
> [GitHub Action 39592331265](https://github.com/chrober/bliss-mood-poc/actions/runs/39592331265)
> successfully checked artist-hash sensitivity without any new audio
> inference or human metric inspection: cutoff 51/256 gives 162 dev /
> 4 candidate holdout / 180 excluded mixed; cutoff 85 gives 86/13/247;
> cutoff 128 gives **31 dev / 56 potential holdout / 259 excluded**.
> Under cutoff 128, 8 of 56 potential holdout triplets share artists
> with the prior four-question smoke; the remaining **48** were not
> exposed in that run. This DOES NOT eliminate the one-giant-artist
> component or establish population/generalization reliability.
> Freeze one artist split and exclusions BEFORE scoring the 48
> candidate test questions, and never optimize using their labels
> or model performance. See
> [sparse-audio methodology](magnatagatune-sparse-audio-benchmark-2026-10-21.md).
>
> **MTT SPARSE REAL AUDIO E2E PASS + HOLDOUT LIMIT, 21 OCT 2026:**
> [ZIP membership 39589694423](https://github.com/chrober/bliss-mood-poc/actions/runs/39589694423)
> **PASS** using only 8 MiB HTTP Range tail: all **1,019** referenced MP3s
> found among 25,863 ZIP members, 0 ambiguous/missing. Three consecutive
> ZIP parts total 2,972,769,864 bytes; needed compressed MP3 member sizes
> sum to 116,910,845 bytes. **533 ordered records reduce to 346 unique
> unordered triplets**, requiring aggregated clip-ID votes.
> [Real Rust-v5 sparse-audio workflow 39590801662](https://github.com/chrober/bliss-mood-poc/actions/runs/39590801662)
> **PASS**: 4 deliberately high-consensus artist-disjoint DEVELOPMENT triples,
> 12 clips CRC checked, 12 bounded HTTP 206 requests transferring only
> **1,385,735 bytes**, 14.48 seconds transfer+feature inference.
> Both heads and seven metrics ran, result aggregate-only. Mood cosine
> got 3/4 majority choices, **NOT generalization evidence**; most job
> overhead was building Rust-v5 (~88 sec). See
> [sparse audio benchmark doc](magnatagatune-sparse-audio-benchmark-2026-10-21.md).
>
> **CRITICAL SCIENTIFIC FINDING:** artist-group preflight
> [39591601421](https://github.com/chrober/bliss-mood-poc/actions/runs/39591601421)
> shows **ALL 214 artists + 346 unordered triples in ONE connected
> artist co-occurrence component**. Strict component-disjoint 80/20
> holdout impossible without dropping triples. Hash-based artist
> split gave 162 development, only **4** held-out, 180 mixed excluded.
> This is scientifically inadequate for metric selection. Do NOT
> present four selected development triples as independent test data.
> Future work: larger descriptive MTT evaluation with dependence/vote
> uncertainty disclosed, plus separate human-similarity confirmation.
> No production decision, no merge, no private music, PR #16 Draft.
>
> **LATEST MTT REAL AUDIO + ARTIST HOLDOUT (21 OCT 2026):**
> Original 3-part ZIP full central-directory membership:
> [39589694423](https://github.com/chrober/bliss-mood-poc/actions/runs/39589694423)
> PASS. Only 8 MiB ZIP tail downloaded; 25,863 ZIP MP3s;
> all 1,019 required clips matched, 346 unique unordered triplets
> from 533 rows, 116,910,845 compressed MP3 bytes required in total.
> Sparse HTTP range-only Rust-v5 end-to-end
> [39590801662](https://github.com/chrober/bliss-mood-poc/actions/runs/39590801662)
> PASS: 4 high-consensus artist-disjoint development triplets,
> 12 real clips analyzed, 1,385,735 audio-range bytes, 14.5 seconds
> for download+analysis, all seven similarity metrics and both
> genre/mood heads, aggregate artifact only. Test is smoke, not
> independent held-out evidence.
>
> Subsequent metadata-only holdout feasibility PASS
> [39592331265](https://github.com/chrober/bliss-mood-poc/actions/runs/39592331265):
> Artist graph is a **single 214-artist/346-triple component**;
> strict connected-component holdout impossible. SHA-256 artist-hash
> 50/50 preferred split: 31 dev, 56 holdout, 259 mixed excluded.
> Eight holdout triplets share an artist with prior smoke and must be
> excluded, leaving **48 unexposed holdout triplets**. No model
> outputs were used to select the split; frozen before further
> audio evaluations. The benchmark code **does not yet enforce**
> this new split for future audio studies; do that next, with tests,
> before any expansion. See
> [MTT sparse-audio + holdout details](magnatagatune-sparse-audio-benchmark-2026-10-21.md).
> Synthetic Linux/Windows CI [39592264225](https://github.com/chrober/bliss-mood-poc/actions/runs/39592264225)
> PASS, metadata audit PASS. Keep PR #16 Draft, no main/PR #13/17
> merge, no user music, no production metric winner.
>
> **MTG/MAGNATAGATUNE REAL METADATA PREFLIGHT PASS (21 OCT 2026):**
> Both agreed metadata-only workflows now completed successfully,
> with **no audio downloads**. MTG-Jamendo split-0 / official
> Essentia JSON classes audited at
> [39586686845](https://github.com/chrober/bliss-mood-poc/actions/runs/39586686845):
> 87 Genre head classes, train/validation/test 32572/11043/11479;
> 56 Mood/Theme, 9949/3802/4231; zero artist-ID/track-ID
> overlap across official splits (not proof of exact ONNX training
> provenance or no encoder training overlap).
>
> MagnaTagATune schema + **human votes and clip joins** validated
> in [39587323227](https://github.com/chrober/bliss-mood-poc/actions/runs/39587323227):
> 533 odd-one-out triple questions, 7650 human votes, 1019 distinct
> referenced MP3 paths, 903 apparent song groups, 214 artist
> strings; 87 tied top-vote questions, 228 unique >=70% consensus
> questions, 160 unanimous. The source clip catalog has 31382 rows,
> of which 5519 have empty MP3 path. These are research metadata
> only. The corrected parser detects original CSV delimiters;
> continuous synthetic Linux/Windows CI
> [39587511195](https://github.com/chrober/bliss-mood-poc/actions/runs/39587511195)
> PASSED. No unfiltered audio benchmark executed or metric selected.
> See [formal preflight results](external-evidence-preflight-results-2026-10-21.md).
>
> **NEXT:** Plan a rights-compliant, bounded study processing the
> 1019 distinct MTT clips only; first verify physical ZIP member
> mapping and archive integrity/disk budget, then paired, artist-grouped
> human triplet agreement and uncertainty against all seven metrics.
> For MTG-Jamendo, consider auxiliary human classification annotations
> on official split-0 test data, but DO NOT pretend these are
> independent evidence of original ONNX training. Every audio workflow
> gets stage walltimes, worker counts, peak RAM and throughput.
> No main/PR #13/PR #17 merges.
>
> **EXTERNAL EVIDENCE ROADMAP / PERFORMANCE POLICY — 21 Oct 2026:**
> The user explicitly wants **continued GitHub Actions runtime optimization
> alongside musical evidence research**. See the detailed
> [MTG-Jamendo + MagnaTagATune plan](similarity-external-evidence-roadmap-2026-10-21.md).
> Priority: (1) metadata-only MagnaTagATune comparison/vote/clip schema and
> licensing audit (533 human odd-one-out triples, ~7650 votes, CC BY-NC-SA
> 3.0 dataset, GPLv3 scripts); (2) in parallel, metadata/split/model-provenance
> audit of MTG-Jamendo 87-Genre/56-Mood heads and derived human annotations;
> (3) only after rights/metadata validation, bounded MagnaTagATune
> audio benchmark with corrected pinned Rust-v5, triplet voting agreement,
> human consensus and paired uncertainty; (4) final independent testing
> and Lyrion playlist validation. **Do not download huge Jamendo audio
> collections or MagnaTagATune split archives until validated.**
> Every expensive workflow must report elapsed times for build, download,
> inference and evaluation; worker count, CPU/RAM and throughput;
> optimize measured bottlenecks. External per-track analyze-features
> loops remain serial; adaptive scan-features workers are not enabled
> there. No production metric selection or merge.
>
> **FMA GENRE VALIDATION E2E PASS, 21 Oct 2026:** Corrected
> [run 39583233757](https://github.com/chrober/bliss-mood-poc/actions/runs/39583233757)
> passed. Official FMA-Small archive has **3 size-anomalous MP3s**,
> safely excluded, with 7,997 usable MP3s. The **80** seeded, artist-unique
> validation tracks (10 per genre, FMA test split untouched) were processed
> by pinned genuine Rust-v5, and an
> [aggregate-only artifact](https://github.com/chrober/bliss-mood-poc/actions/runs/39583233757/artifacts/12338242831)
> published. P@5 random expectation .1139; RMS .3175, cosine .3500,
> centered cosine .3525, weighted Jaccard .3550, old Top-K .3150,
> ranked Top-6 .3150 and ranked Top-12 .3400. Exploratory ONLY,
> no metric chosen. See docs/fma-genre-benchmark-plan.md and
> docs/github-actions-trigger-and-worker-audit-2026-10-21.md.
> Trigger change to push-only CI and docs-only skip is verified;
> Rust adaptive workers are not used by per-song AnalyzeFeatures.
>
> **GH CI / FMA FOLLOW-UP — 21 Oct 2026:** The real FMA validation
> run [39581435733](https://github.com/chrober/bliss-mood-poc/actions/runs/39581435733)
> failed **before inference**, after downloading the archives, because
> `scripts/benchmark_fma_genre.py` rejected one unexpectedly sized MP3
> anywhere in the archive. The code now excludes isolated size anomalies
> and fails closed on excessive damage; synthetic tests were added.
> The corrected GH validation run is
> [39583233757](https://github.com/chrober/bliss-mood-poc/actions/runs/39583233757):
> **verify completion/artifact before claiming FMA retrieval results**.
> General CI was split into Rust-only and Python/PowerShell-only workflows;
> both now use path-filtered **push** triggers (not push+pull_request),
> so each in-repository commit runs a check at most once per relevant
> workflow, and docs-only changes do not execute those checks. See
> [GitHub Actions audit](github-actions-trigger-and-worker-audit-2026-10-21.md).
> FMA/DEAM audio analysis is currently **serial** (`analyze-features` for
> each track, `--threads 1`); adaptive workers belong to `scan-features`
> and are not active. Benchmark fixed-two-worker vs serial only after
> an isolated, validated batch/sidecar implementation.
>
> **UPDATED CURRENT STATUS 21 OCT 2026 — 240-song DEAM and FMA validation:**
> Two 240-song DEAM GitHub Actions benchmarks passed: unfiltered
> [39577605466](https://github.com/chrober/bliss-mood-poc/actions/runs/39577605466),
> conservatively exact MTG-catalog-match-filtered
> [39579552118](https://github.com/chrober/bliss-mood-poc/actions/runs/39579552118).
> Full metadata-only DEAM/MTG screening passed
> [39579084649](https://github.com/chrober/bliss-mood-poc/actions/runs/39579084649):
> **75 possible metadata matches**, not proof of model-training usage.
> Filtered Mood VA-proximity query Spearman: weighted Jaccard .2888,
> cosine .2868, centered .2813, rms .2711, ranked top-6 .2721,
> ranked top-12 .2745, historical cutoff top-K .1903
> (216/240 comparable anchor queries). Different samples, no winner.
>
> FMA-Small metadata-only workflow passed
> [39580107275](https://github.com/chrober/bliss-mood-poc/actions/runs/39580107275):
> 8,000 tracks, 8 exactly balanced genres, artist-disjoint official
> training/validation/test split counts 6,400/800/800.
> New scripts/benchmark_fma_genre.py + regression tests implement
> real Genre retrieval metrics and bounded artist-unique VALIDATION
> evaluation; first live 80-song workflow
> [39581435733](https://github.com/chrober/bliss-mood-poc/actions/runs/39581435733)
> was started, check final run logs/artifact before reporting its result.
> The official FMA test split is reserved. All research workflows use
> corrected pinned Rust-v5 source from PR #17 in separate checkout,
> without merging PR #17. See docs/deam-similarity-benchmark.md,
> docs/fma-genre-benchmark-plan.md and the dated detailed handover.
> No user music rescans, subjective relabels, selected production metric,
> PR merge or main changes.
>
> **DEAM v5 END-TO-END PASS, 21 Oct 2026:** Official DEAM data
> successfully downloaded; **1,802** audio/annotation matches; **12**
> human-annotated DEAM songs analyzed with corrected Rust-v5,
> all seven similarity metrics compared, aggregate-only report uploaded.
> [Successful GitHub Action](https://github.com/chrober/bliss-mood-poc/actions/runs/39576010217),
> [report artifact](https://github.com/chrober/bliss-mood-poc/actions/runs/39576010217/artifacts/12333973414).
> Rust-v5 analyzer came from **separate pinned PR #17 source checkout**
> at 2c3d44401436b3b41b6e067199016a1ed2335fbf without
> merging/editing PR #17. Prior failures intentionally caught missing
> Cargo.lock (PR #16) and v4 preprocessing mismatches. See
> [DEAM benchmark document](deam-similarity-benchmark.md) for complete
> provisional VA correlations. Do **not** choose a metric from 12 songs,
> claim DEAM independent of MTG-Jamendo training, or treat Genre-vs.-VA
> as Genre validation. Next: larger controlled DEAM study, training
> overlap audit, then FMA Genre reference. No main merge.
>
> **CURRENT PRIORITY 21 OCT 2026 — automatic scientific DEAM benchmark, PR #16.**
> The user explicitly shifted away from further manual eight-pair listening
> studies. A reproducible DEAM Valence/Arousal benchmark now lives in
> [docs/deam-similarity-benchmark.md](deam-similarity-benchmark.md) with
> scripts/benchmark_deam.py, test_benchmark_deam.py and
> .github/workflows/deam-benchmark.yml. Synthetically tested on Linux/Windows
> in GitHub Actions. Official DEAM audio and annotations plus official models
> will be fetched only by the runner; only aggregate research results can be
> uploaded. First real workflow run failed because Cargo.lock is not yet
> committed and --locked prevented build; updated workflow removed --locked.
> Check DEAM GitHub Actions run 39575405139 (or latest) before claiming any
> end-to-end result. DEAM's CC BY-NC license, possible MTG-Jamendo train set
> overlaps and the status of Valence/Arousal **as a similarity proxy** must
> remain explicit. No metric winner, user-library scan, public music
> artifacts, mixing decision, main merge or PR #13/#17 changes.
>
> **CURRENT HANDOVER (21 October 2026): Similarity-Metriken auf Rust-v5-Daten, Draft-PR #16.**
> Das folgende Scanner-/Worker-Handover vom 19. Oktober ist historisch,
> nicht die aktuelle Aufgabenliste. Maßgeblich ist das
> [Similarity-Hörtest-Handover vom 21.10.2026](similarity-listening-review-handover-2026-10-21.md).
> **Neuer Status: Die ersten acht menschlichen Hörurteile liegen vor; der
> read-only Evaluator lief erfolgreich.** Genre: 0 positive und 8 negative
> Paare (keine ROC-AUC definierbar); Mood/Theme: 4 positive, 4 negative
> Paare, Cosine und Centered Cosine je AUC 0,5625, andere Metriken
> 0,3125–0,5000. Historisches Mood-Top-K mit absolutem Cutoff liefert
> für alle vier positiven Pilotpaare Null. Keine fehlenden Vektoren.
> Dies sind **unsichere, selektiv ausgewählte Piloturteile**, keine
> unabhängige Validierung und kein Nachweis für eine beste Metrik.
> Nächsten Evaluations- bzw. Hörschritt **mit dem Benutzer vereinbaren**;
> vorher keine eigenmächtigen Experimente oder Änderungen an Queue/Code.
> Private CSV, JSON, Auswahl-Audit, Feature-DB und Audiodateien lokal
> belassen. PR #13 und #17 bleiben separat und Draft, `main` unverändert.
> Bei Bedarf ausschließlich vollständige PowerShell-`& { ... }`-Blöcke.


> **21.10.2026 – Current executable next step:** PR #16 now includes
> a targeted read-only --pair-details-only option in
> scripts/evaluate_similarity.py. It supports semicolon CSVs and
> generates seven score values per head/per human-reviewed pair without
> random sampling, audio analysis, queue changes or changes to labels.
> The original first-eight CSV and saved JSON remain private and
> unchanged. Ask the user to run this option with the saved Rust-v5
> SQLite sidecar and return the new local pair-details report, verifying
> that its labeled AUCs match the existing saved report. The aggregate
> Mood cosine high-scoring negative is 0.9769996802 but its identity
> is not established without the per-pair values. All musical
> conclusions remain explicitly exploratory and uncertain.

> **Purpose:** Start a new development chat without losing the current project
> state. The detailed performance experiment, raw benchmark measurements,
> implementation details and open questions are in
> [adaptive-scan-performance-handover.md](adaptive-scan-performance-handover.md).
>
> **Source of truth:** Always re-check current GitHub `main` before making
> claims or changing code. This handover was prepared against
> `55b35dab1a873c3e61ecd639b7430caf0b09034c` (PR #5 merged), before the
> documentation-only handover PR. Do not assume that SHA is still the latest.

## Project and boundaries

Repository: [chrober/bliss-mood-poc](https://github.com/chrober/bliss-mood-poc).
Experimental Rust/ONNX offline audio analysis to complement Lyrion/Bliss,
**not** an instruction to change production mixers, plugins or Bliss Guidance
SPI. The generic CLI handles **three independent heads** sharing one
Discogs-EffNet embedding per song:

- `moodtheme` — 56-label MTG-Jamendo Mood/Theme (Sigmoid).
- `genre` — 87-label MTG-Jamendo Genre (Sigmoid).
- `voice` — Voice/Instrumental, 2 labels (Softmax). Not vocal-technique or
  percentage-of-vocal-time detection.

Original `bliss.db` and audio are read-only. Experimental results live in a
separate SQLite sidecar, schema v3, keyed by exact `TracksV2.File` identity.
Old Mood-only CLI and legacy rows remain untouched. Real-world prediction
quality is **not** production-validated; verified synthetic Essentia numerical
parity is not evidence of musical usefulness. See
[feature-provider-architecture.md](feature-provider-architecture.md) and
[offline-mood-database.md](offline-mood-database.md).

## What has shipped

1. Generic Mood + Genre + Voice analysis, shared encoder, model registry,
   per-head caching and validated numerical parity.
2. Incremental `scan-features` with bounded, parallel *songs*, independent
   per-worker ONNX Sessions and a single transaction-safe SQLite writer.
3. Corrected ONNX Runtime process-global Environment (earlier concurrent
   `ort::init().build()` attempts failed on Windows).
4. `--max-new N` means **at most N newly attempted tracks**, not N
   successes; `--max-errors N` aborts repeatedly failing scans.
5. `--workers auto` keeps Windows responsive (roughly 25% CPU headroom,
   cap eight), `--workers N` is explicit; for parallel use `--threads 1`.
6. [PR #5](https://github.com/chrober/bliss-mood-poc/pull/5), merged:
   opt-in `--adaptive-workers` with `--workers 6 --min-workers 4
   --max-workers 8`; per-song decode/preprocessing/inference/hash/load
   stage totals; OS CPU/RAM monitoring; logged worker adjustments.
   The fixed-worker interface remains available and unchanged.

Important source entry points:

- `src/features.rs`: `FeatureEngine`, `scan_parallel`,
  `save_completion`, `ScanSummary`, `ScanDiagnostics`.
- `src/parallel.rs`: `worker_count`, `AdaptiveWorkers::observe`.
- `src/resources.rs`: OS-level load sampling.
- `src/main.rs`: CLI flags and validation.
- `src/storage.rs`: read-only upstream Bliss access and SQLite sidecar.
- `model-registry.json` and
  `.github/workflows/voice-parity.yml`: model contract and integration tests.
- `README.md`: usage and caveats.

## Real test setup

User machine: Windows 11, HP Laptop 15-fc0xxx, AMD Ryzen 7 7730U,
8 physical cores / 16 logical CPUs, ~16 GB physical RAM; Wi-Fi 6 Realtek
RTL8852BE-VS at negotiated 600 Mbit/s. Music on NAS UNC share
`\\192.168.1.100\music`, local checkout
`D:\LMS\bliss-mood-poc`, 64,062 eligible Bliss tracks.

Deterministic local 100-song fixture:
`D:\LMS\bliss-mood-poc\benchmark-workers-20261019-060347\sample-100.db`
(seed 20261018). Benchmark sidecars:
`features-6.db`, `features-8.db`, `features-10.db`,
`features-12.db`; raw samples `resources-*.csv`, `summary.csv`
and `summary-with-6.csv`. Keep this suite for apples-to-apples work;
do **not** upload personal music or database to GitHub.

**Fixed-worker results over the same 100 tracks**:

| Workers | Wall time | Songs/min | System CPU avg | RAM max | Analyzer RAM max |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 6 | 80.48 s | 74.6 | 47.9% | 85.0% | 0.66 GB |
| 8 | 80.18 s | 74.8 | 63.5% | 89.5% | 1.17 GB |
| 10 | 82.29 s | 72.9 | 70.8% | 91.6% | 1.94 GB |
| 12 | 112.79 s | 53.2 | 83.2% | 97.5% | 3.21 GB |

All 300 model vectors per run were **byte-identical**. With six workers:
CPU max 87%, WLAN receive mean 24.05 MiB/s, max 39.08 MiB/s. Six fixed
workers are the measured efficiency baseline; eight have similar throughput
at much higher resource pressure.

**First adaptive run**, reported after PR #5 from a database within the
same benchmark directory:
`adaptive-20261019-080350.db`; 100/100 successful, zero failures,
**120.66 s (49.7 songs/min)**; workers initial/final/max **6/6/6**,
CPU avg 51.26%, peak RAM 86.33%, 38 OS-load samples, **no adjustments**.
Per-song *summed overlapping* durations: decoding 173.52 s, Mel/patches
100.82 s, ONNX 343.09 s, SHA-256 reread 66.54 s, session init 1.63 s,
sum of song durations 685.61 s. These are NOT sequential wall-clock or
exclusive CPU durations.

The adaptive controller's low-load rule is **CPU <=65% AND RAM <=79%
for 3 consecutive resource observations**. High-load rule is **CPU >=90%
OR RAM >=88% for 2 consecutive observations**. Changes are inhibited
until >=24 completed songs and at least 20 s since the last adjustment
(or creation). The observed near-86% RAM can sit in the deadband for the
entire run. Therefore **no worker change is not proof of a bug**. The
report shows only maximum RAM, not every sample: inspect actual timelines
and effective conditions before concluding why no adjustment occurred.
Whether the ~50% longer adaptive runtime is reproducible, and whether
the command truly used an identical track set/cache/priority, remain OPEN.

## Next work — priority order

1. **Investigate the adaptive performance regression** on exactly the
   existing `sample-100.db` and music source. Compare fixed six vs adaptive
   six under equivalent environment and process priority; alternate run
   order/repeat measurements, inspect NAS/OS caching, thermal/power throttling,
   and runtime phases. Do not conclude adaptive scheduling is at fault merely
   because of one timing difference.
2. **Make decisions explainable**: record per-resource sample time, CPU/RAM,
   consecutive low/high counters, cooldown, controller state, real in-flight
   count and why it held or changed. Check for starvation caused by samples
   only being taken when job results arrive.
3. **Evaluate safe policy options**, with tests: explicit pressure-only guard
   (reduce at high RAM/CPU), separate throughput-seeking tuning policy, or
   thresholds based on available memory + CPU/queue throughput rather than
   CPU/RAM fixed cutoffs alone. A correct policy may intentionally stay at six.
   Do not blindly force an adjustment.
4. **Measure NAS versus local SSD** on identical files with controlled
   cache state; distinguish SMB latency, network throughput and CPU
   preprocessing/inference. File hashing reads the source twice overall.
5. Regression CI: deterministic simulated resource timelines (high, low,
   deadband, missing samples, cooldown); verify real in-flight changes,
   maximum attempts, error stop and byte-identical feature vectors.
6. Only after evidence, optimize the controller and maybe expose explicit
   `--max-workers` defaults; keep fixed-worker behavior stable. Later:
   full-library progress/ETA and resumable/interruptible UX.

## Rules for the next chat

- Fetch fresh `main` SHA and review these docs + source **first**.
- Diagnose rather than assert adaptive is broken: 6/6/6 can be correct.
- Prefer a reproducible minimal PR; run Rust tests, Clippy, Windows x64,
  and required Essentia/model parity before merge.
- No production mixer/plugin changes. Keep `bliss.db`/music read-only;
  new SQLite benchmark DBs only; never commit music, model weights,
  local sidecar DBs or personal track lists.
- Always bound experiments: `--max-new`, `--max-errors`, timeouts;
  `--threads 1` when parallel. Retain `--workers N` and
  `--adaptive-workers` as optional.
- The user prefers actionable full PowerShell blocks (`& { ... }`) and
  measured evidence over speculative optimizations.


## Mandatory GitHub Actions / local testing workflow (2026-10-19)

**User preference and delivery contract for all future chats:**

1. **Never build Rust binaries on the user's Windows laptop.** Do not put
   `cargo build` or local Rust compilation in a PowerShell test script.
   Source code, unit tests, and release binaries are built and verified by
   GitHub Actions.
2. Make development changes on a feature branch and open a PR. PR events
   automatically trigger the existing **Windows x64 binary** workflow
   (workflow ID `387992797`) along with Rust checks and model parity checks.
   Do not assume that a documentation-only `main` commit also generated a
   Windows executable. Inspect the PR **head SHA** and matching Actions runs.
3. **Do not stop after reporting a queued/in-progress build.** Check the
   triggered Windows workflow to completion; verify that its conclusion is
   `success`, its head SHA matches the exact code under test, and that its
   non-expired artifact **`bliss-mood-windows-x64`** exists. Check all
   relevant Rust and model-parity workflows too. If any check fails, diagnose
   and fix first; never claim the binary is available prematurely.
4. Whenever the user is asked to run a local test, provide a **complete
   executable PowerShell script in `& { ... }` form**, containing the
   **literal, verified numeric Actions run ID** (not a placeholder, an
   automatically selected run, or instructions for the user to look it up).
   Embed the actual binary download, for example:
   `gh run download $runId --repo chrober/bliss-mood-poc --name bliss-mood-windows-x64 --dir $binDir`,
   followed by verification of `bliss-mood.exe`. Download to a run-ID-specific
   path such as `bin\windows-x64\$runId` and reuse only that matching binary.
   The script must check workflow head SHA/conclusion and fail safely if they
   do not match, use a fresh benchmark sidecar, and report useful diagnostics.
5. Preserve the user's existing setup: repo
   `D:\LMS\bliss-mood-poc`, source music `\\192.168.1.100\music`,
   stable 100-song sample
   `benchmark-workers-20261019-060347\sample-100.db`,
   `--models moodtheme,genre,voice --threads 1`. Audio files and original
   `bliss.db` are read-only. Do not commit personal media or benchmark DBs.
6. If testing code on a PR branch, don't require the user's local checkout
   to be on `main`; the binary must match the chosen PR SHA. Do not merge
   before CI and local validation where required.
7. Continue gathering evidence rather than changing worker behavior based
   solely on one timing result. Keep fixed worker modes and model-score
   identity intact.

**Previously verified example:** PR #7 Windows run `39236884182`,
artifact `bliss-mood-windows-x64`, head
`d34e2c4941d008caae089640dc4b75925da5c3e6`. PR #7 was squash-merged
into main as `8ee29972999caf1e543dbb7ce63d57868fdd16f2`.
Do **not** reuse that run ID for subsequently modified code.


## PR #10 pre-worker baseline measurement (2026-10-19)

**New benchmark requirement:** capture and report the system's RAM **and CPU
baseline before any scanner worker starts**, plus available physical RAM
and analyzer process Working Set and Private Bytes. For CPU, a single
instantaneous OS counter is meaningless: use a **one-second interval** before
workers are spawned, and expose the actual elapsed measurement window.
Do **not** feed this baseline into the adaptive worker controller or
normal runtime samples. On Linux and Windows this is measured at the start of
the parallel scan, after opening the input and sidecar DB and before
creating ONNX worker sessions. The one-second baseline measurement is
included in wall-clock scan elapsed time.

The JSON location is `diagnostics.baseline`:
`system_cpu_percent`, `cpu_measurement_seconds`,
`system_ram_percent`, `system_available_ram_mib`,
`process_working_set_mib`, `process_private_bytes_mib`.
These baseline values reflect **pre-worker** machine load, not a completely
idle Windows system before the application was launched. Compare changes
with runtime extrema; extrema can occur at different instants and do not
prove the analyzer was the cause of overall RAM pressure.

Use the mandatory PR-triggered GitHub Actions Windows artifact workflow
and exact-run PowerShell download rules documented above; never suggest
local cargo builds.


## Current product priority: Bliss + Mood/Genre Lyrion integration (2026-10-19)

**Read [lyrion-bliss-mood-genre-integration.md](lyrion-bliss-mood-genre-integration.md) before new product changes.** The immediate engineering task is F1: reliable exact `TracksV2.File` joining and read-only model-provenance-aware Mood/Genre SQLite retrieval for a bounded Bliss/Lyrion candidate set. The first strategy is **Bliss-first with optional Mood/Genre reranking in BlissMixerLab** through guidance SPI v2, with hard eligibility and original Bliss untouched, separate per-head influence, experimental preview opt-in and neutral fallback. Current provider host transmits candidate IDs/urlmd5, but exact file keys are not yet guaranteed; do not silently join by title/artist. Do not enable stored unvalidated model scores for production playlist generation by default.

The cross-platform worker and Raspberry Pi runtime/resource strategy is **deferred**, documented in [platform-resource-roadmap.md](platform-resource-roadmap.md). The user explicitly does not want tuning for one benchmark laptop; development focus now is meaningful playlist fusion, not scanner performance.

## Three-way mixing decision and local workfiles (2026-10-19)

The mixing architecture remains **undecided** between **Bliss-first**,
**Mood-/Genre-first**, and **Hybrid**. The first integration vertical slice
uses Bliss-first because the existing SPI v2 can already rerank a Bliss
candidate pool, **not** because Bliss-first has won a listening/coverage
comparison. All three must be compared on equivalent seeds, constraints,
coverage, transition quality, drift/diversity and Pi budgets before choosing.
See [lyrion-bliss-mood-genre-integration.md](lyrion-bliss-mood-genre-integration.md).

Root-level `benchmark-*/`, `bin/`, local `mood-full.json` and
`mood-quality-*.csv` are excluded by `.gitignore`; keep personal
music paths/analysis outputs out of commits. Do **not** ignore
`Cargo.lock`: this binary application's dependency lockfile should
be separately versioned once. Git status will continue showing it as
untracked until added/committed.


## PR #16: Audio-Embedding-Repräsentationsvergleich, erste Umsetzung (21.10.2026)

Maßgeblicher Forschungsplan:
[similarity-three-representation-approaches-handover-2026-10-21.md](similarity-three-representation-approaches-handover-2026-10-21.md).
Implementierungsvertrag:
[similarity-representation-comparison-handover-2026-10-21.md](similarity-representation-comparison-handover-2026-10-21.md).

Nach dem repräsentationszentrierten Handover wurde im PR-#16-Branch
ein **optionaler** `--embedding-out`-Forschungs-Overlay für den
**unveränderten und exakten** Rust-v5-Commit
`2c3d44401436b3b41b6e067199016a1ed2335fbf`
implementiert. Separates JSON-v1-Sidecar mit Encoder/Audio-Hash,
1280D, f64-Rohpatchmittel, songweiser L2-Norm und
Fingerprints. Schema-v3-Genre/Mood sowie Mixer bleiben unverändert.
Erster Smoke: Rust-Unit-Tests und Release-Kompilierung bestanden,
synthetischer Audio-Lauf zunächst an fehlendem `ffprobe`
gescheitert; Workflow inzwischen korrigiert, finale Actions-
Bestätigung prüfen.

MTT-A/B-Recherche ist ebenfalls vorbereitet: über den kuratierten
1019-Clip-Actions-Cache (bei Miss kein großer Archivdownload)
privater Embedding-Export aus **demselben** Vier-Prozess-Inferenzlauf,
danach fünf Methoden auf denselben 346 explorativen Fragen /
293 eindeutigen menschlichen Mehrheiten. Keine neuen
klanglichen Resultate behaupten, bevor der
[MTT A/B Workflow](../.github/workflows/research-mtt-embedding-ab.yml)
vollständig PASS mit aggregiertem Report ist.
FMA-TEST unangetastet; die zwei Hybrid-Begriffe weiterhin trennen.
PR #13, PR #17, `main` und produktiven Lyrion-Mixer nicht verändern.

## Verifiziert: erster vollständiger Embedding-A/B auf identischer MTT-Cohort (21.10.2026)

**Achtung – ersetzt die oben noch als ausständig bezeichnete
A/B-Messung.** [Run 39617159250](https://github.com/chrober/bliss-mood-poc/actions/runs/39617159250)
ist **PASS**; 1019 Cache-Clips CRC-validiert, exakt 346
explorative Menschenfragen, davon 293 mehrheitsentscheidbar.
Auf denselben Aufnahmen lieferte **direkte 1280D-Cosine
182/293 = 62,12 %**, Genre-Cosine **191/293 = 65,19 %**,
Mood-Cosine **192/293 = 65,53 %** und
Mood-Centered-Cosine **193/293 = 65,87 %**.
Alle vier hatten wie das Embedding **100 % Abdeckung**.
Das Embedding lag gegenüber Mood-Centered-Cosine um
**−3,754 Prozentpunkte** zurück (nur Embedding korrekt 27,
nur Mood-Centered korrekt 38). Naives gepaartes
95-%-Tripel-Resampling für den Unterschied:
**−9,215 bis +1,365 Prozentpunkte**; wegen
Abhängigkeiten **kein unabhängiges Populations-CI**.
Auch Künstlergewichts-Sensitivitäten sind kein valides
Konfidenzintervall. Die Kausalinterpretation und
Generalisierbarkeit bleiben offen.

Der vorherige unabhängige synthetische Rust-Smoke
[Run 39616222834](https://github.com/chrober/bliss-mood-poc/actions/runs/39616222834)
bestand Rust-Unit-Tests und Release-Kompilierung,
brach aber beim externen Modell-Download wegen
`essentia.upf.edu`-Netzwerk-Timeout ab. Deshalb
wurde ein **synthetisches off/on/Pooling/Threads-Paritätsgate
vor den 1019er-Lauf** des neuen A/B-Workflows
hinzugefügt; dessen nachfolgenden Run erst auf
PASS prüfen, bevor dieses Gate als bestätigt gilt.

Vollständiger Studienbericht mit Methoden,
Paar-Discordanzen, statistischer Unsicherheit,
CI-Runs, Fingerprints, Limitierungen und nächstem
Evidenz-Gate:
[Audio-Embedding vs. Kopf-Baselines: MTT-A/B-Resultate](similarity-audio-embedding-ab-results-2026-10-21.md).
**Keine Fusion-Kalibrierung, keine Produktionsentscheidung,
kein erneuter MTT-Holdout, kein FMA-TEST, kein Merge.**

## C-Fusion: vier gleichgewichtete, **untrainierte** lokale Rangablationen (21.10.2026)

Nach dem ersten B-vs-A-Resultat wurden die vier Kombinationen
Audio+Genre, Audio+Mood, Genre+Mood und Audio+Genre+Mood
als **explorative** und explizit nicht optimierte
Rangfusionen implementiert. Jede Cosine-Verteilung wird
ausschließlich **innerhalb der jeweiligen Drei-Song-Frage**
in die Midranks 0/0,5/1 transformiert, danach werden die
enthaltenen Repräsentationen gleich gewichtet.
Ranggleichstand zählt als Nichtvorhersage (im 293er
Nenner falsch). **Das ist keine global kalibrierte
Song-Similarity und darf nicht als Produktionsmetrik
oder Playlist-Mixer eingesetzt werden.**
Das feststehende Verfahren, die vier Kombinationen,
Datenabhängigkeiten, Split-Grenzen und
Anwendungsszenarien:
[Similarity Fixed-Rank Fusion Research](similarity-fixed-rank-fusion-research-2026-10-21.md).
Implementierung:
[`scripts/fixed_rank_fusion.py`](../scripts/fixed_rank_fusion.py),
optionales Evaluator-Flag `--fixed-rank-fusions`,
separates Aggregate v2 und
[`tests/test_fixed_rank_fusion.py`](../tests/test_fixed_rank_fusion.py).
Python-Tests Linux/Windows [Run 39619643950](https://github.com/chrober/bliss-mood-poc/actions/runs/39619643950)
sind PASS. Ein tatsächlicher Fusion-Lauf
[39619708040](https://github.com/chrober/bliss-mood-poc/actions/runs/39619708040)
wurde ausgelöst; seine Ergebnisse müssen für
wissenschaftliche Schlussfolgerungen **noch abgelesen**
werden. Die 346 MTT-Fragen sind bereits vollständig
exploriert, daher keinesfalls Fusionsgewichte aus ihnen
tunen.

## Verifiziert: vollständiger explorativer A/B/C-Durchgang (21.10.2026)

Die vorab implementierten **vier untrainierten Equal-Midrank-Fusionen**
wurden zusammen mit den fünf bisherigen A/B-Methoden
im [Actions Run 39619708040](https://github.com/chrober/bliss-mood-poc/actions/runs/39619708040)
vollständig erfolgreich auf **exakt denselben 1019
MagnaTagATune-Clips und 293 mehrheitsentscheidbaren
Tripelfragen** ausgewertet. Synthetisches 1280D
Original-Patchpooling-/Head-Off-On-/SQLite-/Thread-
Paritätsgate erneut **PASS**.

Die Fusions-Genauigkeit auf dem gemeinsamen 293er-Nenner
(Abstentions als falsch): Audio+Genre **163/293 = 55,63 %**
(Coverage 234/293), Audio+Mood **170/293 = 58,02 %**
(241/293), Genre+Mood **167/293 = 57,00 %**
(230/293), Audio+Genre+Mood **192/293 = 65,53 %**
(283/293). Der bisherige Mood-Centered-Baselinewert
bleibt **193/293 = 65,87 %** mit 100 % Abdeckung.
Keine der vier einfachen, *tripellokalen* Rangfusionen
verbessert diese Referenz. Die vielen Paargleichstände
der Zweierkombinationen erklären den niedrigen
Gesamtnenner-Erfolg; Quote auf nur vorhergesagten
Fällen darf nicht isoliert verglichen werden.

**Keine Kalibrierung/Optimierung aus diesen
Ergebnissen.** Diese post-hoc MTT-Fusionsexperimente
sind weder eine globale Song-Cosine-Kalibrierung
noch eine unabhängige Validierung oder ein
Lyrion-Übergangstest. Vollständige Rechenschritte,
Gleichstands-/Coverageanalyse, Paardifferenzen,
Caveats und Folgeexperimente:
[Fixed-Rank Fusion Research Results](similarity-fixed-rank-fusion-research-2026-10-21.md).
Das reproduzierbare, nur aggregierte
[GitHub-Artefakt](https://github.com/chrober/bliss-mood-poc/actions/runs/39619708040/artifacts/12354537538)
enthält die Ergebnisberichte v1, v2 und
das synthetische Paritätsprotokoll.

## CI-Fehlerkorrektur und nächster Evidenzschritt (21.10.2026, nach A/B/C)

Der [MTT-Run 39621028716, Job 119294123082](https://github.com/chrober/bliss-mood-poc/actions/runs/39621028716/job/119294123082)
brach **beim erweiterten synthetischen Vierprozess-Paritätsgate** ab
(`AssertionError: Expected all four independent process-level worker outputs`).
Es ist ein **Fehler im Python-Test-Harness**, keine im Log nachgewiesene
Rust-Inferenzabweichung: `glob("process-worker-*.json")` nahm sowohl die
vier Embedding-Dateien `process-worker-1.json` … `-4.json` als
auch die vier JSON-Klassifikationsberichte
`process-worker-heads-1.json` … `-4.json` auf. Der Workflow
hatte vorher bereits Rust-Unit-Tests, Release-Build, Downloads
und vier parallele Prozesse erfolgreich abgeschlossen.

**Korrektur ausschließlich in PR #16:**
- `scripts/check_song_embedding_smoke.py` filtert exakt nummerierte
  `process-worker-N.json`-Embedding-Dateien über `fullmatch`;
  `--require-process-workers` zwingt vier vollständige Ausgaben
  und kann nicht stillschweigend bei komplett fehlenden Dateien PASS liefern.
- `.github/workflows/research-mtt-embedding-ab.yml` setzt das
  zusätzliche Flag im neuen Concurrent-Worker-Gate.
- `tests/test_check_song_embedding_smoke.py` bildet den
  ursprünglichen Fehler nach (vier Embeddings plus vier Heads) und
  überprüft fehlende, zusätzliche und insgesamt fehlende Worker;
  `.github/workflows/python-checks.yml` führt diese Tests auf
  Linux **und** Windows aus.

Ein neuer Workflow wurde automatisch durch den
Änderungscommit ausgelöst:
[MTT-Forschungs-Workflow Run 39622530049](https://github.com/chrober/bliss-mood-poc/actions/runs/39622530049).
Die endgültigen Results und den vierten
Worker-Paritätsnachweis erst dann als PASS berichten,
wenn der Run beendet ist. Die zuvor komplett
erfolgreichen A/B/C-Resultate aus Run 39619708040
bleiben unverändert. Ein bloßer Fehler des Testglobs
widerlegt keine vorangegangene Messung.

**Nächste Forschungspriorität – unabhängige, gleichgepaarte
A-vs-B-Replikation, noch keine weitere MTT-Optimierung:**
erst FMA-Small **katalogbereinigte VALIDATION** (80 Songs)
mit unverändertem offiziellen TEST-Split,
danach DEAM-development/validation (Valence/Arousal
nur als Stimmung-Proxy).
Für jeden Datensatz auf den **identischen** Clipausschnitten
1280D-Cosine gegen vorhandene 87D/56D-Baselines,
identische Grundgesamtheit, gültige Vorhersageabdeckung,
katalog-/künstlerbewusste Abhängigkeitsanalyse und
gepaarte Scores gegenüberstellen.
Trainingskatalogüberschneidungen auch beim Encoder beachten.
MTT (346 vollständig erforschte Tripel) ist **kein Holdout**.
Unabhängige menschliche Klangähnlichkeits- und
Playlist-Übergangsreferenzen bleiben das entscheidende
separate Evidenzziel. Kontrastiv trainierte
Discogs-Embedding-Modelle sind eine spätere **eigene
Modellfamilie** mit eigenen Hashes/Provenienz.
Keine Fusion-Gewichte an MTT nachoptimieren und keine
Lyrion-Mixer-Änderung daraus ableiten. PR #16 Draft;
PR #13, PR #17 und `main` unangetastet.

### CI-Nachweis der Harness-Korrektur

[Python and PowerShell tests, Run 39622478825](https://github.com/chrober/bliss-mood-poc/actions/runs/39622478825):
**Linux PASS, Windows PASS**, einschließlich des neuen Offline-Regressionstests für
vier Embedding- plus vier Head-JSONs. [Research-MTT-Recheck Run 39622530049](https://github.com/chrober/bliss-mood-poc/actions/runs/39622530049)
wurde nach Aufnahme des `--require-process-workers`-Flags
automatisch ausgelöst; zum Zeitpunkt dieses Eintrags war sein
vollständiges echtes Parallel-Inferenz-Gate noch **queued**.
Den Run vor Abschluss eines Vierprozess-Determinismusnachweises prüfen.

## FMA-Small katalogbereinigte VALIDATION: eigener Embedding-A/B-Transfer (21.10.2026)

**NEU:** Das nächste kontrollierte Forschungsgate für
Repräsentation A gegen B ist implementiert:
[`scripts/evaluate_fma_embedding_ab.py`](../scripts/evaluate_fma_embedding_ab.py),
optional `--embedding-dir` im bestehenden
[`scripts/benchmark_fma_genre.py`](../scripts/benchmark_fma_genre.py),
[`research-fma-embedding-ab.yml`](../.github/workflows/research-fma-embedding-ab.yml),
synthetische Linux-/Windows-
[`tests/test_evaluate_fma_embedding_ab.py`](../tests/test_evaluate_fma_embedding_ab.py).

Die vorherige **exakte** katalogbereinigte
80-Song-VALIDATION-Kohorte wurde aus
[FMA-Run 39606850307](https://github.com/chrober/bliss-mood-poc/actions/runs/39606850307)
als SHA256 `f4a7a81c0713db7619efdba6eb3d561aa70d6d3cc812b4884793953d93b58509`
übernommen. Ferner sind die drei
Quellen-SHAs (FMA-Metadaten/Audiopaket, MTG-Katalog)
und die früheren Genre-Cosine-Maße
(P@5 0,3200; mAP@10 0,1748759921; nDCG@10
0,2985332322) **als Regressions-Gate fixiert**.
Die neu berechneten direkten 1280D- und
87D/56D-Sidecars stammen im neuen Modus aus
**demselben Encoder-Durchlauf** und werden nach
Audio-SHA, Patchzahl und Modell-/Pooling-Fingerprint
paarweise überprüft.

Jeder der 80 Künstler-distinkten Query-Tracks
vergleicht sich mit exakt denselben 79 Kandidaten;
9 pro Query haben die gleiche FMA-Obergenreklasse.
Verglichen werden Embedding-Cosine, Genre-Cosine
und Centered-Cosine sowie Mood-Cosine/Centered
als **Cross-Task-Kontrolle**. P@5, mAP@10,
nDCG@10, gemeinsame Abdeckung, Abstentions
als 0, stratifizierte gepaarte
Query-Sensitivitätsintervalle. Abhängige Kandidaten,
nur acht Genres und mögliche nicht erkannte
Trainingskatalogüberschneidungen bedeuten:
**kein unabhängiger Holdout/Populations-CI**.
Offizieller FMA-TEST bleibt strikt unberührt.
Audio und Embedding-Sidecars bleiben runner-privat,
Artefakte sind nur aggregierte Reports.

Ausführlicher Studienvertrag:
[Similarity FMA Embedding A/B](similarity-fma-embedding-ab-2026-10-21.md).
Erster Workflow:
[Research FMA 80 Validation A/B](https://github.com/chrober/bliss-mood-poc/actions/workflows/research-fma-embedding-ab.yml).
Solange nicht vollständig `PASS`: **keine neuen
numerischen Ähnlichkeitsresultate behaupten**.
Original FMA-Workflow, Original-Rust-v5-Pin und
PR #13/#17 sowie Mixer unverändert, PR #16 Draft.
Nach FMA ist DEAM Development als nächster
gepaarter Mood-Proxy vorgesehen. Noch keine
Fusion auf FMA VALIDATION optimieren.

## Verifiziert: FMA-80-Embedding A/B Transfer auf katalogbereinigter VALIDATION (21.10.2026)

**NEUER EMPIRISCHER BEFUND – älteren Abschnitt mit
`ausständig` damit überholt:**
[GitHub Actions Run 39625087310](https://github.com/chrober/bliss-mood-poc/actions/runs/39625087310)
**PASS**, [Aggregate-Artefakt 12355954718](https://github.com/chrober/bliss-mood-poc/actions/runs/39625087310/artifacts/12355954718).
Identischer eingefrorener, bereits untersuchter
FMA-Small VALIDATION-Sample-Fingerprint,
**80 Künstler-distinkte Songs**, 8 Genres mit je
10 Songs, pro Song dieselben 79 Kandidaten,
Genre-Katalogscreening (42 mögliche MTG-Overlap-
Treffer ausgeschlossen). Original FMA TEST nicht
angetastet, keine Trainings-Disjointness behauptet.
Die frühere Genre-Cosine-Referenz wurde
**exakt** reproduziert (P@5 `0,3200`,
mAP@10 `0,174876`, nDCG@10 `0,298533`).

| Gepaarte Methode | P@5 | mAP@10 | nDCG@10 | Abdeckung |
| --- | ---: | ---: | ---: | ---: |
| EffNet 1280D Song-L2 + Cosine | **0,2800** | 0,163044 | 0,282363 | 80/80 |
| Genre 87D Cosine | 0,3200 | 0,174876 | 0,298533 | 80/80 |
| Genre 87D Centered Cosine | **0,3225** | **0,178147** | **0,304271** | 80/80 |
| Mood/Theme 56D Cosine (Cross-Task) | 0,2775 | 0,150394 | 0,266065 | 80/80 |
| Mood/Theme 56D Centered Cosine (Cross-Task) | 0,2675 | 0,152847 | 0,270372 | 80/80 |

Embedding − Genre Centered P@5
= **−4,25 Prozentpunkte**, explorativer
95-%-genrestratifizierter gepaarter
Query-Resampling-Sensitivitätsbereich
**−8,76 bis +0,25 Prozentpunkte**;
wegen gemeinsam verwendeter Kandidaten und
bereits explorativ erforschter VALIDATION **kein
independentes Konfidenzintervall/Signifikanzbeweis**.

Damit ergibt sich eine **zweite andere
Aufgaben-/Dataset-Indikation** neben MTT:
das rohe nicht speziell kontrastive
EffNet-Song-Mean-Embedding schlägt die
aufgabenpassenden Genre-/Mood-Kopfvektoren
hier nicht. MTT ist Menschen-Odd-One-Out,
FMA ein **Genre-Label-Proxy**. Beide
Zahlen dürfen nicht gepoolt und nicht
als allgemeiner Produktionssieger gedeutet
werden. Details, Protokoll, Paardifferenzen
und Stage-Zeiten:
[FMA-80-Embedding-A/B-Studie](similarity-fma-embedding-ab-2026-10-21.md).

**Nächster Schritt:** DEAM-Entwicklungs-
/Validierungsvergleich für Valence/Arousal
bei identischen Clips und Modell-Provenienz
als begrenztem Mood-Proxy, anschließend
eigenständige Prüfung kontrastiver
Discogs-Modelle und neue unabhängige
menschliche Klang-/Playlist-Referenzen.
Keine zusätzlichen Fusionsgewichte an
MTT/FMA-VALIDATION optimieren.
PR #16 bleibt Draft; `main`, PR #13,
PR #17 und Lyrion-Produktivmixer unverändert.


## Aktueller Abschluss in kleinen Schritten – FMA-Cache, DEAM-Blocker, Lyrion-Folgetest (21.10.2026)

1. **FMA-Caching FERTIG und verifiziert** nach
   [MagnaTagATune-Cache-Vorbild](https://github.com/chrober/bliss-mood-poc/actions/workflows/magnatagatune-all-exploratory.yml):
   Cold [FMA 39632517381](https://github.com/chrober/bliss-mood-poc/actions/runs/39632517381)
   PASS, ca. 246 s Originalarchiv-Download; Warm
   [FMA 39633485262](https://github.com/chrober/bliss-mood-poc/actions/runs/39633485262)
   PASS, ca. 74 MB Selected-Song-Cache wiederhergestellt,
   7,2 GiB Download SKIPPED. 80-Song-Sample-
   Fingerprint/Original-Archiv-SHA/MP3-SHA werden
   gegen Metadaten verifiziert. Auch unbereinigter
   FMA-Genre-Workflow erhält separaten Cache-Key
   ([39633600832](https://github.com/chrober/bliss-mood-poc/actions/runs/39633600832)
   Cold PASS). Lizenzvorsicht: Actions-Caches
   sind **nicht** vertraulich. Details:
   [FMA 80 Studie](similarity-fma-embedding-ab-2026-10-21.md).

2. **DEAM-Hash-Fehler behoben, CI PASS.**
   Der ältere DEAM-Probenfingerprint benutzt
   literal `\\n` als Trennzeichen, nicht
   echten Zeilenumbruch. Neuer gepaarter
   1280D-Evaluator repariert, Offline-Regressionstest
   Linux/Windows
   [39638092328](https://github.com/chrober/bliss-mood-poc/actions/runs/39638092328)
   PASS. Die frühere exakt wiederholte
   240-Song-Mood-Cosine-VA-Spearman-Referenz
   `0.286784551387186` wurde bereits
   [in 39634196144](https://github.com/chrober/bliss-mood-poc/actions/runs/39634196144)
   bestätigt; dieser Lauf scheiterte erst am
   **Hash-Serialisierungsfehler** nach Inferenz.

3. **Aktuell externer DEAM-Datenblocker:**
   [Run 39638292554](https://github.com/chrober/bliss-mood-poc/actions/runs/39638292554)
   vier HTTPS-TCP-Timeouts beim Publisher
   `cvml.unige.ch:443`, noch vor Musikanalyse.
   [Run 39639506656](https://github.com/chrober/bliss-mood-poc/actions/runs/39639506656)
   beweist Nichterreichbarkeit durch einen
   **neuen Fast-Fail-Preflight vor Rust-Build**.
   **Noch KEIN erfolgreicher neuer
   DEAM-Embedding-vs-Mood-Spearman-Vergleich.**
   Keine alternativen Archive ohne
   Provenienz-SHA- und Lizenzprüfung
   übernehmen. Details:
   [DEAM Benchmark](deam-similarity-benchmark.md).

4. **Nächster unabhängiger Schritt – kleine
   lokale Musik-Library-Hörprobe**:
   [Plan für L0–L3](similarity-local-library-retest-plan-2026-10-21.md).
   Zunächst nur read-only 87D/56D/1280D-
   Provenienz auf begrenzten vorhandenen Songs,
   dann ca. zwölf neue Kontraste mit
   menschlichen Genre-/Mood-/Klang-/Playlist-
   Kriterien und Urteilssicherheit, **noch
   nicht ausgeführt**. Keine private Musik in
   GitHub, keine Queue-/DB-Änderung ohne
   eigenen Vorbereitungsschritt.
   Den früheren 8-Paar-Pilot nicht als
   unabhängige Validierung ausgeben
   (Genre 0 positive). Arbeit strikt
   PR #16 Draft, keine anderen Branches
   oder Produktivkomponenten verändern.
