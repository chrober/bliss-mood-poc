# FMA-Small: kleiner, prüfbarer Actions-Download-Cache

**Stand:** 21.10.2026, Forschungsbranch
`feat/similarity-metric-evaluation` / Draft PR #16.

## Warum kein 7,2-GiB-Archiv im GitHub-Cache?

Das offizielle `fma_small.zip` ist ca. 7,2 GiB.
GitHub Actions Cache hat standardmäßig **10 GB
Speichergrenze pro Repository** (konfigurierbar,
oberhalb des freien Kontingents gegebenenfalls
kostenpflichtig). Eine vollständige Kopie
würde die vorhandenen Rust/Cargo- und Modell-
Caches verdrängen bzw. Cache-Eviction/Mehrkosten
verursachen. Der vorangegangene FMA-80-A/B-
Lauf benötigte **243,87 s** nur für den Download.

Offizielle FMA-Publikation:
https://github.com/mdeff/fma.
Github-Cache-Dokumentation:
https://docs.github.com/en/actions/reference/dependency-caching-reference.

## Design: Source-pinned selected-song cache

[`scripts/fma_selected_audio_cache.py`](../scripts/fma_selected_audio_cache.py):

1. **Kalter Lauf:** Einmaliger originaler FMA-
   Publisher-Download. Vollständigen
   Publisher-Archive-SHA256
   `f923bbef327820456d50965c3c320c3c7b6dab8456449429fd78f7ec96a5d02c`
   gegen den bereits im echten FMA-A/B-Lauf
   festgeschriebenen Wert verifizieren.
2. Alle `tracks.csv`-Informationen werden
   nur für TRAINING/VALIDATION verwendet;
   offizielle TEST-Zeilen bleiben unangetastet.
   Identische geordnete Song-Selektion
   `seed=20261021`, VALIDATION 8×10.
   Im katalogbereinigten Test 42 exakte
   mögliche MTG-Matches vorab ausschließen.
   Sicherung der **bereits analysierten
   Sample-ID-SHA256**, nicht Neu-Sampling
   aus nur noch 80 Cache-MP3s.
3. Als **private, branch-bounded Actions-Cache-
   Daten** nur eine separate ZIP mit exakt
   den 80 benötigten 30-Sekunden-MP3s
   sowie eine geschützte Quellen-/Auswahl-
   Manifest-JSON anlegen. Ausgewählte
   Clipnamen/-IDs verbleiben im Cache und
   dürfen NICHT als Artefakt, Git-Commit
   oder öffentlicher Log hochgeladen werden.
   Manifest speichert Original-Publisher-ZIP-
   SHA, Metadaten-/MTG-Hash, Auswahl-SHA,
   acht Genres, Seed, Filterstatus und
   **individuelle SHA256 jeder MP3**.
4. Unmittelbar nach erfolgreicher Vorbereitung
   kann die 7,2-GiB-Original-ZIP vom
   ephemeren Runner entfernt werden.
   GitHub `actions/cache/save@v4`
   speichert NUR `fma-private/fma-selected-cache`,
   kein Verzeichnis mit dem Publisher-Gesamtarchiv.
5. **Warmer Lauf:** `actions/cache/restore@v4`,
   Quellhashes und ursprüngliche Kohorte
   strikt verifizieren, einschließlich
   der SHA jedes der 80 Clips, Künstler-
   Einzigartigkeit, Genre-/Sample-
   Fingerprint und erneutem
   MTG-Katalogscreening. Bei Miss
   bleibt der offizielle Download als
   Ersatzpfad erhalten; bei fehlerhaftem
   Hit wird FAIL-closed statt fehlerhaftes
   Audio unbemerkt ausgetauscht.
6. [`benchmark_fma_genre.py`](../scripts/benchmark_fma_genre.py)
   und [`evaluate_fma_embedding_ab.py`](../scripts/evaluate_fma_embedding_ab.py)
   akzeptieren optional
   `--selected-cache-manifest`. Ohne
   Manifest gilt unverändert der
   originale Voll-ZIP-Pfad; mit Manifest
   bleibt der **Original-FMA-Audio-SHA**
   im Report erhalten, ergänzt um
   den Cache-Bundle-SHA.
   Bereits gemessene Genre-Baselines müssen
   **exakt** reproduziert werden.
7. Im Cache-Job die tatsächliche
   `cache-hit`-Variable, Bundlegröße
   sowie Download-/Analysezeiten
   in `GITHUB_STEP_SUMMARY` erfassen.
   **Laufzeitersparnisse erst nach kaltem
   und anschließend warmem erfolgreichen
   Workflow messen**; Cache-Wärme
   nicht aus Code allein folgern.

Die ursprüngliche
[`research-fma-embedding-ab.yml`](../.github/workflows/research-fma-embedding-ab.yml)
nutzt den branch-spezifischen
`fma-small-screened80-selected-v1-f923...`-Cache.

### Speicher, Zugriff und Lizenzen

GitHub Actions **Cache ist kein geschütztes
Lizenzarchiv**, sondern eine von vertrauenswürdigen
Workflows nutzbare Infrastruktur; insbesondere
öffentliche Repository-Caches besitzen
Branch-/PR-Zugriffssemantik. Das ausgewählte
Audio darf nicht in `actions/upload-artifact`,
Git-LFS, Releases oder ein veröffentlichtes
Distributionspaket gelangen. Nur offiziell
angebotene FMA-Forschungsclips,
kein einziges Audio aus der eigenen
Musikbibliothek. Die individuellen
Creative-Commons-Lizenzen der FMA-Titel
sind weiterhin zu respektieren.
Kein Zugriff für untrusted PR-Workflows,
keine externe Weitergabe des Caches,
die tatsächliche Verfügbarkeit wird durch
Retention/Eviction begrenzt.

Ein Vollarchiv-Cache wäre
angesichts der 10-GB-Standardgrenze und
möglichen Lizenz-/Zugriffsfragen keine
sinnvolle Standardeinstellung.
Ein anderer FMA-Sample/FMA-Seed erfordert
eine **separate Cache-Key-/Kohorten-Version**;
keine stillen historischen Vergleichswechsel.

### Prüfgates

[`tests/test_fma_selected_audio_cache.py`](../tests/test_fma_selected_audio_cache.py)
simuliert eine FMA-Struktur inklusive ungültiger
TEST-Zeile; prüft kalten Cache-Pack,
warm verifizierten Restore ohne Publisher-
Gesamtarchiv, Sample-Fingerprint,
gekippte Archiv- und MP3-Hashes,
geänderte Metadaten und No-Overwrite.
Gates laufen unter Linux und Windows.

## Empirische Verifikation: kalter Pack und warmer Restore

**Kalter Lauf PASS:**
[GitHub Run 39632517381](https://github.com/chrober/bliss-mood-poc/actions/runs/39632517381).
Offizieller 7,2-GiB-Audio-Download **246,39 s**,
danach deterministische Auswahl aus 7.197
größenvaliden FMA-Entwicklungs-Audios (3
Größenanomalien verworfen).
Der gespeicherte, checksumgeprüfte
`selected.zip` umfasst **76,51 MiB**
Audio für exakt die eingefrorenen
80 Songs; kein Originalarchiv im Cache.
Vollständiger vorheriger Genre- und neuer
1280D-A/B-Benchmark ebenfalls **PASS**,
d.h. Originalkohorte und P@5 etc.
unverändert.

**Warmer Restore PASS:**
[alter katalogbereinigter Genre-Workflow
39633485262](https://github.com/chrober/bliss-mood-poc/actions/runs/39633485262).
Im Runner explizit
`Cache hit for: fma-small-screened80-selected-v1-f923...`;
der originale
`Download original FMA-Small 7.2 GiB ONLY on cache miss`
wurde mit Status **skipped** protokolliert.
ZIP und alle 80 MP3-SHA256 nach dem
Restore geprüft; wieder **76,51 MiB**.
Die alte Genre-Metrikberechnung
blieb vollständig erfolgreich.
Diese reproduzierbare Verbesserung
eliminiert den großen **Publisher-
Download** bei Cache-Hit; sie ist
**keine** gemessene Gesamtlaufzeit
eines identischen warmen/kalten
Benchmark-Workflows (unterschiedliche
Benchmark-Historie und Rust-Binary-
Cachezustände). Bei Cache-Eviction
fällt der Workflow korrekt auf den
vollständigen Publisher-Download zurück.
