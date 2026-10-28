# Handover prompt — Phase C isolated ONNX feature worker (2026-10-28)

This replaces the outdated Phase A/B-centric prompt. Copy the German prompt below into the next project chat. **Check the live head**: the referenced code SHA is intentionally a historical audit snapshot before subsequent documentation commits.

---

Ich möchte die Entwicklung im Projekt **Lyrion: Mood Analysis** am Repository **[chrober/bliss-mood-poc](https://github.com/chrober/bliss-mood-poc)** fortsetzen. **Übernimm den technischen Kontext und arbeite aktiv im Repository weiter.**

## 1. GitHub-Stand und Lesereihenfolge

- **Draft PR #19:** https://github.com/chrober/bliss-mood-poc/pull/19
- Branch: `feat/ram-safe-online-autotune` (stacked auf PR #18 `feat/manifest-batch-adaptive-worker-analysis`; PR #18 basiert auf PR #17, dem originalen Essentia-C++-Backend).
- Der **zuletzt vollständig geprüfte Implementierungs-Head vor den aktuellen Handover-Commits** war `e2b1a0a4bd256d88e8704abcc8bf158878296ddc`. **Hole zuerst den tatsächlichen aktuellen Head samt Workflow-Ergebnissen, nicht blind diesen SHA verwenden.**
- **Unbedingt zuerst lesen:** `docs/handover-phase-c-isolated-worker-20261028.md` (aktuelle, CI-geprüfte Übergabe); anschließend `docs/onnx-worker-process-isolation.md`, `docs/online-autotune-phase-b.md`, `docs/handover-adaptive-host-sizing-20261028.md` und ggf. `docs/chat-handover.md` (historisch).

## 2. Was bereits implementiert ist

Der ursprüngliche Rust-Scanner koordiniert das originale Essentia-C++-DSP-Backend, die gemeinsame Discogs-EffNet-1280D-Repräsentation und die ONNX-Classifier **Mood/Theme (56 Labels), Genre (87), Voice/Instrumental (2)**. Ein zentraler SQLite-Sidecar-Writer schreibt Ergebnisse; Musik und Bliss-DB bleiben read-only.

**Phase B** hat ein experimentelles, hardwareunabhängiges Online-Autotuning mit CPU-/RAM-Grenzen, fail-closed RAM-Watchdog, scan-spezifischem Abbruchsignal, kontrolliertem FFmpeg, nichtmonotoner Worker-Erkundung mit wiederholten Messfenstern und RAM-gesteuerter Zulassung. Aktivierung ausschließlich per `--adaptive-workers --adaptive-policy autotune`; **`resource` bleibt Standard**. Es gibt **keinen universellen optimalen Workerwert** (nicht anhand Ryzen-Benchmarks festschreiben).

**Phase C (entscheidend!):** Ein separater, versteckter Rust-Workerprozess **führt inzwischen tatsächlich die vorhandene `FeatureEngine` aus**, nicht nur synthetische Ping-Tests. In `src/feature_worker_process.rs` existieren ein versioniertes, auf 64 KiB begrenztes IPC-Protokoll, persistente `Initialize`-/`AnalyzeSong`-Operationen, Zeitlimits und Abbruch; der Parent besitzt den Child-Prozess. Versteckte CLI-Modi: `internal-feature-worker`, `internal-isolated-analyze-features`, `internal-direct-analyze-features`. Der Worker verwendet dieselbe EffNet- und Mood/Genre/Voice-Inferenz wie der ursprüngliche Pfad, kann optional das gepoolte **1280D-Embedding** zurückgeben und schreibt **nicht** in SQLite. Unter Unix wird die Worker-Prozessgruppe beim Abbruch signalisiert; für Windows fehlen Job Objects.

**Wichtig:** Phase C ist **noch NICHT** in den regulären `scan-features`-Pfad integriert. Dort laufen die ONNX-Sessions nach wie vor in Rust-Threads. Kein vollständiger OOM-Schutz, keine gemessene universelle Durchsatzverbesserung.

## 3. Exakter CI-Status der letzten Codeprüfung

Für `e2b1a0a4...` waren erfolgreich: Rust-Tests/Clippy (Runs **40674323791**, **40674316120**), Windows-x64-Binary (**40674323805**), Genre-Parität (**40674323881**) und Voice-Parität (**40674324005**).

**Rot sind zwei native Essentia-Workflows:**
- **Linux original native smoke**, Run **40674323816**: eindeutig **Rust E0433**; das ONNX-freie `native/rust-mel-reference` bindet `src/audio_decode.rs` ein, welches inzwischen `crate::resources::memory_diagnostics()` benutzt, das der Subcrate fehlt. **Zuerst modular und ohne Änderung des Audio-DSP-Verhaltens beheben** (z. B. verfügbare RAM-Daten oder ein Ausgabebudget an den cancelbaren Decoder injizieren; Referenztool ONNX-frei belassen).
- **Windows original native Essentia**, Run **40674323927**: Fehler in `Verify pinned original MTG sources or fetch on cache miss`. **Genauer Grund noch unbestätigt**; überprüfe den Cache, den gepinnten Git-SHA, Remote-URL und den Worktree samt hochgeladenem Diagnoseartefakt. Upstream-Integritätsprüfungen nicht einfach deaktivieren.

Seit `e2b1a0a4` wurden Handover-Dokumente committed und neue CI-Läufe ausgelöst. **Prüfe den aktuellen Head und getrennt alle relevanten Checks**; früher grüne Checks sind nicht automatisch auf späteren SHA übertragbar.

## 4. Nächste konkreten Arbeitsschritte

1. Aktuellen PR-/CI-Stand verifizieren und die beiden nativen Fehler untersuchen und korrekt beheben. Änderungen testen, committen, pushen und die Handovers aktuell halten.
2. Erst nach grüner CI die **bereits implementierte echte Paritätsprüfung** auf einer begrenzten Menge privater realer Songs mit identischem Modell-/Audio-/Backendstand ausführen. `scripts/compare_isolated_feature_worker.py` prüft sämtliche Klassifikationswerte **bitgenau als f32**, Head-Labels, Model-Keys/Fingerprints, Audiohash, Patchzahlen; mit `--embedding` zusätzlich **alle 1280 f32-Bits** gegenüber der versteckten direkten Referenz. Beispiel:
   `python scripts/compare_isolated_feature_worker.py --exe "<CI-verifiziertes Binary>" --source "<read-only Song>" --models-dir "<lokale ONNX-Modelle>" --models moodtheme,genre,voice --audio-backend essentia --essentia-worker "<originaler C++-Worker>" --embedding`
   Das Werkzeug samt synthetischen Tests existiert; **ein erfolgreicher Realmusik-PASS ist bislang nicht dokumentiert**. Keine privaten Daten hochladen oder committen.
3. Prozessisolation absichern: Windows Job Objects zur Beendigung **des gesamten Prozessbaums**; Unix-Prozessgruppen/Child-Reaping unter Fehler-/RAM-Szenarien und Linux cgroups/Pi 4B/macOS testen.
4. **Erst nach erfolgreicher vollständiger Parität und Ressourcenvalidierung** isolierte Worker unter `--adaptive-policy autotune` in den regulären Scanner integrieren. Parent bleibt alleiniger SQLite-Writer, `resource` und Fix-Worker bleiben unverändert. Danach End-to-End-Zeit inklusive Prozessstart und Speicherverbrauch messen.

## 5. Verbindliche Grenzen

- Originalaudio und Bliss-DB **read-only**. Keine private Musik, ONNX-Gewichte, rohe Benchmarks, Songlisten, DB-Dateien oder Embeddings ins Repository.
- PR #16 (Similarity), PR #17/18, Produkt-/Plugin-Integration und Modell-Arithmetik nicht nebenbei ändern. Keine numerische Toleranz aufweichen, um Parität künstlich herzustellen.
- Kein Ryzen-spezifisches Sizing; Host von Windows-Ryzen bis Raspberry Pi 4B muss grundsätzlich unterstützt werden.
- **Windows-Rust-Build über GitHub Actions, commit-matched Artefakt verifizieren**, nicht unkontrolliert lokal bauen.
- PR #19 bleibt **Draft**, solange native CI, private Realmusik-Parität und Cross-Plattform-Kill/OOM-Prüfungen ausstehen.

**Arbeite ohne erneute grundlegende Rückfragen weiter:** Zuerst aktuellen Head/CI prüfen, die nachgewiesene Linux-Buildregression beheben, Windows-Native-Fehler gezielt untersuchen, Tests/Handovers aktualisieren und die nächsten validierten Schritte transparent dokumentieren.

---

## Verified continuation since the initial handover (28 October 2026)

PR #19's most recent development work fixed the ONNX-free Mel reference modularity regression, replaced mutable Windows Essentia/PR #16 upstream refs with pinned, verified source commits, tightened the direct-vs-isolated comparator to demand all requested heads and official 56/87/2 score counts, and corrected hidden CLI annotations. On [Linux native CI 40681621668](https://github.com/chrober/bliss-mood-poc/actions/runs/40681621668), **three actual official-ONNX direct-versus-isolated tests passed** on synthetic mono WAV/stereo FLAC with original Essentia C++ and a Rust frontend WAV, with exact **145 scores plus 1280 pooled embedding f32 components** per case. Linux CI additionally enforces the four prevalidated official ONNX SHA256 pins in a follow-up commit.

The **private read-only multi-song real-audio parity** gate is still outstanding; synthetic CI must not be used as acceptance for production `scan-features`. Windows Job Objects, macOS/Linux/Pi descendant/OOM stress and later autotune-only isolated workerpool integration remain open. Always recheck the live PR #19 HEAD and all commit-matched checks before work; `resource` is still default and PR #16 is unchanged.
