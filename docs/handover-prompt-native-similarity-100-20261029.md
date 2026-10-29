# Copy-Paste-Handover-Prompt — native 100-Song-Analyse und GENERAL Similarity (29.10.2026)

> **WICHTIGE AKTUALISIERUNG 29.10.2026:** Dieser Prompt beschreibt den inzwischen **erledigten** nativen 100-Song-Scan und ist **historisch**. Die realen Ergebnisse stehen unter [Real Native Results](native-similarity-100-real-results-20261029.md): `PASS_EXPLORATORY_TOLERANCES`, 100/100, 4.950 Paare, fünf Rang-Rhos gerundet 1,0, alle 12/11-Hörkorrelationen unverändert. **NICHT** erneut Preflight, Scan oder Compare auslösen. Für neue Sessions ist jetzt das allgemeine Similarity-Forschungsziel verbindlich: untrainierte Multi-Signal-Metrik, externe MTT/FMA/DEAM-Evidenz, keine weiteren Pflichtbewertungen, keine Worker-Optimierung, PR #16 unverändert. Die PowerShell-Konventionen aus diesem historischen Prompt gelten weiter.


Der folgende Text ist für eine neue ChatGPT-Session im Projekt Lyrion: Mood Analysis bestimmt. **Er enthält den aktuellen erfolgreichen Preflight, nicht bloß die alte Arbeiter-Parallelisierung.**

---

Ich möchte die Similarity Metric Evaluation für **Lyrion: Mood Analysis** im Repository https://github.com/chrober/bliss-mood-poc fortsetzen.

## Fokus / Zielsetzung (verbindlich)

**Primäres Ziel: eine wissenschaftlich und praktisch gut begründete allgemeingültige musikalische Ähnlichkeitsmetrik finden, die für beliebige Musikbibliotheken ohne individuelles Training funktioniert.** Erhalte die getrennten Dimensionen Genre/Stil, Mood/Energie, Klang/Timbre und Playlist-Übergangseignung im Blick. Eine persönliche, trainierbare Metrik und ein 0–100%-Blending kommen erst zusätzlich/optional; ohne persönliches Training gilt 100 % allgemeine Metrik.

**KEINE** weitere Worker-Autotuning-/Parallelisierungsforschung, **KEINE** neuen verpflichtenden manuellen Hörtests (insbesondere nicht 36–40 Paare), **KEINE** ungefragte Änderung der Draft-PR #16 und ihrer bisherigen Hör- und Messdaten.

## Git-/Dokumentenausgangslage

1. **Zuerst Live-GitHub prüfen**: main, Draft-PR #16 auf feat/similarity-metric-evaluation sowie aktuellen separaten Arbeitsbranch feat/native-similarity-cohort-validation. Beim Handback vom 29.10.2026 war main af38df464ef2c97aac98c728f684da189e6525c0, PR #16 offen/Draft mit HEAD 2204ec91d8d8a773872f266397b0656178b481ee. Aktueller Bridge-Branch kann durch die Handover-Commits weitergewandert sein.
2. Lies vorrangig:
   - docs/handover-native-similarity-100-20261029.md **(neue verbindliche Statusquelle)**;
   - docs/native-similarity-100-cohort-bridge-20261029.md;
   - docs/multi-worker-song-analysis-final.md;
   - docs/handback-multi-worker-to-similarity-20261028.md;
   - docs/essentia-licensing-distribution-strategy.md;
   - scripts/bootstrap_native_similarity_preflight.ps1, scripts/run_native_similarity_cohort.ps1, scripts/native_similarity_cohort_bridge.py und tests/test_native_similarity_cohort_bridge.py;
   - aus PR #16 die bestehenden Similarity-Dokumente, bisherigen MTT-/FMA-/DEAM-Ergebnisse, die Hörtest-Evaluation und die drei dokumentierten Vergleichsansätze **nur lesend**.
3. Die statische native Original-Essentia-C++-Multi-Worker-Analyse wurde über PR #20 und Fix PR #22 in main integriert. --workers auto ist eine einmalige CPU-basierte Wahl (maximal 8), **kein** dynamischer Regler; zusammen mit --threads 1. PR #19 wurde absichtlich nicht gemergt, Issue #21 bleibt später.

## BEREITS ERFOLGREICH: lokaler PREFLIGHT PASS, 100/100

Der Nutzer hat am 29.10.2026 auf Windows das **vollautomatische** scripts/bootstrap_native_similarity_preflight.ps1 ausgeführt. Ergebnis:

- baseline_feature_cohort PASS: exakt die ursprüngliche PR-#16-Rust-v5-Genre-/Mood-Kohorte (keine geänderte Auswahl);
- baseline_embedding_exports PASS: 100 kompatible originale 1280D-Embeddings;
- ONNX-Modellgewichte und Klassenmetadaten PASS;
- Scanner-EXE + lokal bereits vorhandener nativer Essentia-C++-Worker + DLL-Closure PASS;
- Audio-SHA256 **001–100: ALLE 100 PASS**;
- new_output_directory_safety PASS;
- JSON-Status **PREFLIGHT_VERIFIED_NO_NATIVE_SCAN_YET**.

Verbindliche Fingerprints: Manifest f4d359fa1187f4a2626c14b7abe4a34f5d2143ec014c1b9e7f01545cc53e0b77; alte Rust-v5-SQLite c8bcf43049bd3c3abeccbb3518969ad357153313928b00f59a248c8566e09865; Scanner-EXE 00a41687fd79c53a536b6de6bf865647ef2d6f9ee453419cc69ca00911f5d82d; Worker EXE fd6b172f2db84a614c2db5c80b47670f363fbaafa4e2b9db6f02c3fbd262f3da. Alle ONNX-/Klassen-/Repräsentations-Hashes stehen im neuen Handover.

**Der Preflight ist abgeschlossen und soll nicht nochmals auf denselben Ordner ausgeführt werden. Es gibt noch KEINEN nativen 100-Song-Scan und KEINEN Rust-v5-vs.-C++-Vergleich.** Sei in Fortschrittsmeldungen präzise.

## KONKRETER NÄCHSTER ARBEITSAUFTRAG

**Führe die technisch kontrollierte native Essentia-C++-Neuanalyse exakt derselben 100 Songs aus bzw. bereite den Windows-Ablauf so weit vollautomatisch vor, wie du aus der Session heraus tatsächlich handeln kannst. Danach den automatischen numerischen und Similarity-Rangvergleich durchführen.**

Benutze die bereits existierenden lokalen Verzeichnisse:

- Repository/PR-#16-Checkout: D:\LMS\bliss-mood-poc — NICHT ändern/wechseln;
- separater Bridge-Worktree: D:\LMS\bliss-mood-native-bridge;
- Preflight-Ordner **existiert bereits**: D:\LMS\bliss-mood-poc\benchmark-native-similarity-100-20261029;
- dort bestehende private Dateien: exact-100-tracks.txt, provenance.json, noch leeres native-embeddings/;
- Scanner: D:\LMS\bliss-mood-private\verified-scanner-40758319812\bliss-mood.exe;
- Worker: D:\LMS\essentia-cli-test\essentia-worker\bliss-essentia-worker.exe;
- ONNX: D:\LMS\bliss-mood-poc\models; Audio: \\192.168.1.100\music;
- ursprüngliche Rust-v5-DB: D:\LMS\bliss-mood-poc\benchmark-rust-v5-workers4-20261020-191946\round-01-workers-04-rust.db;
- alte 100 Embeddings: D:\LMS\bliss-mood-poc\benchmark-local-song-embeddings-full100-20261021.

**Benutzeranforderung:** vollständige selbständige PowerShell-Einstiegsskripte! Git-Fetch/-Worktree-Update, validierte Artefakte/Hashes, bekannte Pfade und Fehlerbehandlung automatisch integrieren. Keine wiederholte Pfadabfrage, kein fragmentiertes manuellen Git-Checkout/Download/Scan/Compare. Nutze die vorhandenen Skripte, verbessere nötigenfalls den Runner auf dem **separaten Bridge-Branch**, synthetische Tests auf Linux/Windows und CI-Parse-Prüfung. Behalte harte Fail-Closed-Gates, vor allem bestehendes Original-Manifest, Quell-Audio, Modelle, Scanner-/Worker-/DLL-/Fingerprint und nur NEUE private Sidecars. Keine blinden Retries gegen einen halbfertigen Scan.

**Verbindliches PowerShell-Lieferformat:** Gib mir **einen vollständigen, direkt kopierbaren und ausführbaren Block `& { ... }`**, alternativ einen ebenso vollständigen Launcher für ein versioniertes Repository-`.ps1`. **Keine** fragmentierten Kommandozeilen, `REPLACE_...`-Platzhalter oder Abfolgen, bei denen ich selbst einen Branch auschecken, Git pull/fetch ausführen, Artifact-Run-IDs recherchieren, Dateien herunterladen, Checksummen prüfen, Pfade zusammensuchen oder mehrere Skriptteile verbinden muss. Automatisiere diese Aufgaben im Skript unter Verwendung **bereits bekannter** lokaler Pfade und einer **konkreten verifizierten GitHub-Actions-Run-ID**. Kein lokaler Rust-/Cargo-Build; erforderliche Windows-CLI kommt aus geprüftem CI-Artefakt. Falls ein wirklich nicht vorhandener oder nicht eindeutig bestimmbarer lokaler Bestandteil fehlt, **mit nachvollziehbarer Diagnose sicher abbrechen**, statt einen Pfad zu erfinden oder unbeabsichtigt native Pakete zu verteilen. Keine blinde Wiederholung von `prepare` (100/100 bereits PASS); bestehendes `exact-100-tracks.txt` und `provenance.json` unverändert weiterverwenden. Den sicheren Scan→Compare-Ablauf so automatisieren, dass ich nur **eine lokale Ausführung** starte und am Ende einen anonymisierten Ergebnisbericht erhalte; bereits existierende, möglicherweise partielle Ausgaben niemals löschen oder überschreiben. Klare Statusmeldungen/Exitcodes. Die Tests und CI-Verifikation vor Auslieferung selbst übernehmen.

**Scan-Aufruf nach bestandenen Gates:** bliss-mood.exe scan-features, --tracks-file exact-100-tracks.txt, --source-root \\192.168.1.100\music, --db nur die NEUE native-features.sqlite, --embedding-dir native-embeddings, --models moodtheme,genre,voice, --audio-backend essentia, --essentia-worker original native Worker, --workers auto, --threads 1, --max-errors 3, --json. Niemals gesamten Katalog scannen oder alte DB/Audio/Bliss/Lyrion verändern.

**Compare danach:** scripts/native_similarity_cohort_bridge.py compare; prüfe exakt 100 Track-IDs, unveränderte Audio-SHA256, Patchzahlen, gleiche ONNX-Modelle/Klassenreihenfolge und separate DSP-Backend-Identitäten. Vergleiche 87D/56D-Scores, 1280D-Song-Embeddings und die Rankings aller **4.950** Kombinationen für Genre Cosine, Genre Centered, Mood Cosine, Mood Centered, Embedding Cosine. Wiederhole mit den originalen 12 menschlichen Bewertungen auch die 11-Musik-Sensitivität ohne menschlich als Nichtmusik markiertes Paar #10. Teile nur die aggregierte anonymisierte Ergebnis-JSON, keine Songnamen/Manifeste/Rating-CSV/Audit/DB.

## Wissenschaftliche Einordnung

Alle zwölf manuell hörbewerteten Paare sind fertig, die Auswahl war bewusst modellbasiert, n=12, ein Hörer, keine unabhängige Generalisierungsvalidierung. Ergebnisse auf 11 Musikpaaren: Mood Centered Cosine vs Playlist-Eignung Spearman rho ≈0,769; Embedding Cosine vs Klang/Timbre ≈0,766. Diese Hinweise nicht überinterpretieren oder Gewichte auf denselben 12 Bewertungen optimieren und dann als unabhängig bewertet darstellen. MTT/FMA/DEAM und die bisherigen mathematischen Ansätze/Kandidaten sollen möglichst effizient automatisiert verglichen werden, **ohne weiteren Pflicht-Hörtest**. Backend-Parität und Ähnlichkeitsqualität sind verschiedene Fragen. Symmetrische Similarity ≠ gerichtete Next-Track-Passung.

## Weitere Grenzen

Quellcodeintegration ist keine Lizenzfreigabe: native Windows-EXE/DLL-Distribution weiterhin **BLOCKED** (17 fehlende installierte Lizenznotices, Essentia AGPL/FFmpeg/MSYS2/ONNX separat berücksichtigen). Kein GitHub-Upload privater Song-/Feature-/Modellfiles. Keine Änderung an PR #16, Hörurteilen, Modellvorhersagen oder bestehenden lokalen Ausgaben. Keine dynamische Workeroptimierung. Unterscheide bitgenaue Worker-Invarianz, toleranzbasierte numerische Originalreferenz-Parität und explorative Backend-Rangstabilität.

**Definition of Done:** Erfolgreicher nativer Scan genau dieser 100 Songs auf neue private Ziele; verifizierter Old/New-Vergleich aller 100 Repräsentationen und 4.950 Songpaare; dokumentierte, reproduzierbare echte Ergebnisse/CI; Interpretation im Hinblick auf die allgemeine Metrik — keine weiteren Songpaare manuell bewerten. Bei einem Gate-Fail technische Ursache nennen, nicht private Daten ändern oder Erfolg behaupten.

Bitte arbeite zielgerichtet weiter, prüfe zuerst die Dokumente und den Git-Live-Stand und liefere komplette automatisch ausführbare PowerShell-Skripte für die noch fehlenden Schritte.
