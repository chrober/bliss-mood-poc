# New-chat continuation prompt — original Essentia C++ Windows linker

Copy the prompt below into a new ChatGPT session. It refers to
the active **draft** PR #17; its live head/CI must be checked at session start.

---

Wir setzen das Projekt **Lyrion: Mood Analysis / bliss-mood-poc** fort.

Arbeite direkt mit dem verbundenen GitHub-Repository
https://github.com/chrober/bliss-mood-poc
auf dem Feature-Branch `feat/essentia-cpp-worker-backend`, Draft-PR #17:
https://github.com/chrober/bliss-mood-poc/pull/17

Lies zuerst die aktuellen Handover-Dokumente im Branch:
1. `docs/handover-essentia-cpp-20261020.md` — Architektur, Entscheidungen, CI-Matrix, erledigte und offene Gates.
2. `docs/handover-essentia-windows-linker-20261020.md` — exakter Windows-Linkerfehler, Build-Provenienz, Symbol-Diagnostik und nächster Implementierungsplan.
Ergänzend: `docs/essentia-cpp-worker-architecture.md`, `docs/essentia-cpp-windows-native-build.md` und `docs/essentia-cpp-windows-packaging.md`.

**Letzter explizit überprüfter Programmstand vor dem Handover:**
`efda3f27e1965d65ebf73fad7de35bcba1dd907a`; 7 von 8 CI-Prüfungen bestanden.
Einzige gescheiterte Prüfung: `Native original Essentia C++ Windows x64 (experimental)`,
https://github.com/chrober/bliss-mood-poc/actions/runs/39382026896 .
Durch die Handover-Dokumentationscommits hat sich die Branch-Spitze danach verschoben — überprüfe deshalb beim Start zuerst den LIVE-Stand von PR #17 und seinen CI-Läufen.

**Erreichter technischer Meilenstein:** Original upstream Essentia C++ wird unter Windows mit MinGW64 und FFmpeg 9 erfolgreich als `essentia.dll` gebaut und installiert; der echte `bliss-essentia-worker.cpp` kompiliert, aber das Linken der EXE scheitert an undefinierten Symbolen (z. B. `essentia::init()`, `essentia::shutdown()`, `essentia::Logger::debug()`, `essentia::ParameterMap::add()`, `essentia::nameOfType`). Die folgenden echten Windows-Audio- und Paketierungsschritte wurden noch nicht ausgeführt. Die vorherigen Linux-Original-Essentia-Tests einschließlich WAV/FLAC/MP3, EffNet 1280D und 87/56/2 Klassifikationswerten sind hingegen grün.

**Deine unmittelbare Aufgabe:** Gehe den Windows-Linkerfehler praktisch an. Inspiziere die echte PE-Exporttabelle der erzeugten `essentia.dll`, eventuell erzeugte MinGW-Importbibliotheken, `pkg-config --libs essentia` und die vollständige CMake-Linkkommandozeile. Kläre nachweisbar, ob Symbole nicht exportiert sind oder die EXE die falsche/keine Importbibliothek bzw. ein anderes ABI verwendet. Korrigiere den Build auf dem Feature-Branch mit möglichst wenig lokal zu wartendem Code. Bevorzuge den originalen upstream Essentia-C++-Quellcode und passende Build-/Link-Flags; erwäge ggf. einen kontrollierten statischen Link, falls das upstream Shared-Export-Modell nicht funktioniert. Keine Dummy-Stubs, keine neue DSP-Nachimplementierung, kein `essentia-rs`.

Danach führe echte Windows-IPC-/WAV/FLAC/MP3-Smokes mit dem Original-C++-Worker durch, überprüfe seine native DLL-Closure/Hashes und validiere **erneut** die numerische Mel-/EffNet-/Genre-/Mood-/Voice-Parität unter Windows. Achte besonders darauf, dass die Windows-Upstream-Version (`b0661db99be4a8e2c6fabbe90a996f89786fdd8e`, noch nicht gemergter Upstream-PR #1540) eine andere ist als die bereits validierte Linux-Referenz (`9ceef0a3a7900ad51eb42aa5b6c6789b4bec6a47`). Nach bestandener Parität ist das vorbereitete 1/2/4/6-Worker-A/B-Benchmark-Harness an der Reihe.

**Feste Projektregeln:** Den bestehenden Rust-Orchestrator inkl. adaptiver Multi-Worker-Steuerung, Rust-ONNX-Sessions, SQLite-Single-Writer und Prozess-RAM-Metriken beibehalten. Standardbackend bleibt `rust`; Original-Essentia ist opt-in. `main` nicht verändern und PR #17 NICHT mergen/aus Draft nehmen. Keine Änderungen an `lms-blissmixer-lab`. Keine echten Musikdateien oder privaten Benchmark-SQLite-Dateien committen. Lizenz-/AGPL-Verpflichtungen und Windows-DLL-Provenienz weiter beachten. Für jedes PowerShell-Beispiel ausnahmslos einen äußeren Block `& { ... }` verwenden.

Setze die Implementierung ohne erneute Grundsatzdiskussion fort, prüfe die GitHub Actions nach jeder relevanten Änderung, dokumentiere getestete Resultate sauber und unterscheide strikt erfolgreich, fehlgeschlagen und noch nicht getestet.
