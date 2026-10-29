# Handover: Lyrion Similarity nach erfolgreichem nativen 100-Song-Preflight (29.10.2026)

**Aktuell verbindlicher Einstieg für die nächste Chat-Session.**
**Forschungsziel: Eine robuste, möglichst gute ALLGEMEINE Song-Ähnlichkeitsmetrik für Lyrion entwickeln, die ohne persönliches Training funktioniert.** Eine erlernte persönliche Metrik sowie ein späteres 0–100%-Blending bleiben optional und nachgeordnet. Keine weiteren verpflichtenden manuellen Songpaare; keine erneute Worker-Autotuning-Forschung.

## 1. Live-Git-Stand beim Handover

Repository: https://github.com/chrober/bliss-mood-poc

| Referenz | Nachweis am 29.10.2026 |
| --- | --- |
| main | af38df464ef2c97aac98c728f684da189e6525c0 |
| Draft PR #16, feat/similarity-metric-evaluation | open, nicht gemergt, HEAD 2204ec91d8d8a773872f266397b0656178b481ee |
| Aktiver separater Forschungsbranch | feat/native-similarity-cohort-validation, vor Handover-Doku HEAD d47c6d8b56b19f7bcafb9f2db101b3861442c996 |
| Native CLI Quellcode | PR #20 integriert; PR #22 ergänzte CI-Fix/Dokumentation |
| Native Bridge CI | Linux + Windows synthetisch PASS, GitHub Actions 40873290274 |
| Dynamische Worker | PR #19 absichtlich ohne Merge geschlossen; Issue #21 nur spätere Forschung |

**Live-Branches, CI und Dokumente zu Beginn erneut prüfen; die obigen SHAs sind historische Nachweise.**
Der native Scanner verwendet persistente originale Essentia-C++-Worker, gemeinsame EffNet-ONNX-Sessions, 87D Genre, 56D Mood/Theme, 2D Voice und gepooltes normalisiertes 1280D-Song-Embedding. Mit --workers auto erfolgt die konservative CPU-Workerwahl einmal am Start (maximal 8); --threads 1 bei Parallelität. Keine dynamische Workeranpassung.

## 2. ECHTER lokaler Meilenstein: PREFLIGHT PASS (100/100)

Der Nutzer führte am 29.10.2026 in Windows PowerShell erfolgreich scripts/bootstrap_native_similarity_preflight.ps1 aus. Die vollständige Konsolenausgabe belegt:

- [PASS] baseline_feature_cohort: die exakt zur originalen PR-#16-Pilotstudie passende deterministisch ausgewählte Rust-v5-Kohorte aus der alten schema-v3-SQLite. Historische zusätzliche Head-/Backend-Zeilen werden unverändert belassen.
- [PASS] baseline_embedding_exports: genau 100 kompatible originale 1280D-Embedding-JSONs.
- [PASS] onnx_model_weights_and_class_metadata: überprüfte Encoder-/Genre-/Mood-/Voice-Gewichte und Klassenreihenfolge.
- [PASS] verified_scanner_and_native_worker: unveränderte GitHub-Actions-Scanner-EXE sowie bereits installiertes natives Essentia-C++-Windows-Kit mit SHA256-geprüfter DLL-Closure.
- [PASS] audio_sha256_001_of_100 bis audio_sha256_100_of_100: **100 von 100 Original-Audiodateien byteidentisch zur eingefrorenen Ausgangskohorte**.
- [PASS] new_output_directory_safety; JSON meldet **PREFLIGHT_VERIFIED_NO_NATIVE_SCAN_YET**, tracks = 100, alte Heads Genre/Mood, neue erwartete Heads Genre/Mood/Voice.

**Nicht durchgeführt:** Noch KEIN nativer Neuscan, noch KEINE neue 100-Song-Feature-SQLite/1280D-Embeddings, noch KEIN numerischer Rust-v5-vs.-C++-Vergleich, KEINE 4.950-paarige Rangstabilitätsmessung und KEINE reproduzierte native Korrelation mit den zwölf Hörurteilen.

### Fingerprints der echten lokalen Preflight-Ausgabe

| Datei / Provenienz | SHA256 |
| --- | --- |
| Eingefrorenes 100-Song-Manifest | f4d359fa1187f4a2626c14b7abe4a34f5d2143ec014c1b9e7f01545cc53e0b77 |
| Alte Rust-v5-SQLite | c8bcf43049bd3c3abeccbb3518969ad357153313928b00f59a248c8566e09865 |
| Originales Embedding-Repräsentations-Fingerprint | 48d6726d346b49aaf9f6d0377778ce0bf46be52285293e2f357ad26832cbc759 |
| Verifizierte bliss-mood.exe | 00a41687fd79c53a536b6de6bf865647ef2d6f9ee453419cc69ca00911f5d82d |
| Originaler nativer Worker | fd6b172f2db84a614c2db5c80b47670f363fbaafa4e2b9db6f02c3fbd262f3da |
| EffNet encoder ONNX | a280825b334797cf677939db8cd5762c0392aedd0ca6415dbc1cd083f045e43c |
| Genre ONNX | 637acf45315191a2c9a87d5977d48f02da6fc823192fe794a1537c55e7c7ce6a |
| Mood/Theme ONNX | 7d6270acaa5f4bba4b115a0d6849aca05ed6bd153dcb6d9da4f6ab9f99ef10ff |
| Voice ONNX | 20155e4c439714b0c45c08644b73c8e12d9dccb173bd4ab9934bf1e5aee837ca |
| Genre JSON labels | b0ae89110ddbdba5ed3ad375910b1cffc738436fbb4138ac4c2801b48fc5ec59 |
| Mood JSON labels | d62cd90263e4d613fa7fcce7a831e339450394794af63685f96e065c1a896ab0 |
| Voice JSON labels | 43ac2c3b055dfaed20f6232e0f10636c287f1c5a6e5bd02c5585860031964c8f |

Der Scanner stammt aus GitHub Actions [40758319812](https://github.com/chrober/bliss-mood-poc/actions/runs/40758319812), Quellcommit da8fecee23930c2e52abcb473a62b8178b2d5474. BUILD.txt, SHA256SUMS.txt und tatsächlicher EXE-SHA wurden verglichen; EXE-SHA ist nicht ZIP-SHA. Native Windows-Original-Essentia-C++-Referenzprüfungen liefen in [40760885061](https://github.com/chrober/bliss-mood-poc/actions/runs/40760885061) erfolgreich, allerdings NICHT auf diesen 100 privaten Songs.

### Lokal installierte, nicht zu veröffentlichende Ressourcen

- Bestehender PR-#16-Checkout: D:\LMS\bliss-mood-poc (nicht checkout/mergen/resetten).
- Separater, sauberer Bridge-Worktree: D:\LMS\bliss-mood-native-bridge (detached HEAD, getrennt aktualisieren).
- Scanner-EXE: D:\LMS\bliss-mood-private\verified-scanner-40758319812\bliss-mood.exe
- Original-Essentia-C++-Worker: D:\LMS\essentia-cli-test\essentia-worker\bliss-essentia-worker.exe einschließlich worker-dependencies.json und nativer DLLs.
- Modelle: D:\LMS\bliss-mood-poc\models
- NAS-Audio-Root, read-only: \\192.168.1.100\music
- Alte Rust-v5-Datenbank, read-only: D:\LMS\bliss-mood-poc\benchmark-rust-v5-workers4-20261020-191946\round-01-workers-04-rust.db
- Alte 100 Embeddings, read-only: D:\LMS\bliss-mood-poc\benchmark-local-song-embeddings-full100-20261021
- **NEU BEREITS VORHANDEN und erfolgreich geprüft:** D:\LMS\bliss-mood-poc\benchmark-native-similarity-100-20261029 mit privaten Dateien exact-100-tracks.txt, provenance.json sowie leerem native-embeddings-Verzeichnis.

**NICHT noch einmal prepare oder bootstrap-preflight auf denselben Ordner anwenden!** Der bestehende Ordner wird absichtlich vor Überwrite geschützt. Das Manifest enthält Songpfade; SHA256-Dateinamen der Embedding-JSONs sind keine Verschlüsselung. Keine Musik, Track-Identitäten, Manifeste, Original-CSV, Audits, Databases, EXE/DLL, Modelle oder Einzelembeddings nach GitHub/CI hochladen.

## 3. Nächster verbindlicher Auftrag: native SCAN → COMPARE

**Jetzt die bereits eingefrorenen 100 Songs mit der nach main integrierten originalen Essentia-C++-CLI in NEUE private Ziele analysieren und mit der originalen Rust-v5-Repräsentation vergleichen.** Keine andere Kohorte wählen. Kein neuer Hörtest.

1. Live-Stände main, PR #16 und Bridge prüfen; lesen: dieses Handover, docs/native-similarity-100-cohort-bridge-20261029.md, docs/multi-worker-song-analysis-final.md, docs/handback-multi-worker-to-similarity-20261028.md, docs/essentia-licensing-distribution-strategy.md; scripts/native_similarity_cohort_bridge.py, scripts/run_native_similarity_cohort.ps1, scripts/bootstrap_native_similarity_preflight.ps1 und deren synthetische Tests/CI. PR-#16-Similarity-Dokumente und Evaluatoren nur LESEND.
2. **User-Anforderung: vollständige, automatische PowerShell-Einstiegsskripte**. Die nächste Session soll den Scan+Compare-Ablauf benutzerfreundlich orchestrieren: Git fetch/sauberes separates Worktree-Update, geprüfte Scanner- und Worker-/DLL-Bundles, bestehendes Manifest/Provenienz-Dateien wiederverwenden, Hash-Gates und strikte Ausgabeziele. Keine unbekannten manuellen Pfadangaben oder einzelnen Download-/Checkout-Schritte verlangen. Der vorhandene Runner scripts/run_native_similarity_cohort.ps1 kennt bereits -Step scan und -Step compare, benötigt aber bisher mehrere explizite Pfade.
3. Nur bei erneut bestätigten SHA256-/Manifest-/Modell-Gates durchführen: scan-features mit --tracks-file exact-100-tracks.txt, --source-root NAS, --db NEUE native-features.sqlite, --embedding-dir NEUER native-embeddings/-Pfad, --models moodtheme,genre,voice --audio-backend essentia --essentia-worker bereits geprüfter Worker --workers auto --threads 1 --max-errors 3 --json. Kein gesamter Libraryscan, keine Modifikation der Original-SQLite, Bliss-/Lyrion-DB oder Musik. Keine Blind-Retries, wenn Native-Ziel bereits (teilweise) existiert.
4. Danach mit scripts/native_similarity_cohort_bridge.py compare ein *neues* anonymisiertes Ergebnis erzeugen: exakte 100 Track-IDs/Audios/ONNX-Hashes, Patchzahlen, getrennte Backend-Fingerprints, 87D/56D-Zahlenabweichung, 1280D-EffNet-Vektordrift sowie Rangkonsistenz aller **4.950** möglichen Paare über **fünf** Verfahren (Genre/Mood cosine und centered cosine, Embedding cosine). Optional die bereits erledigten menschlichen 12 Bewertungen bzw. 11 ohne Nichtmusik-Paar #10 wiederverwenden; ursprüngliche private Auswertung/CSV/Audit nie überschreiben.
5. Tests: synthetisches Linux-/Windows-CI und PowerShell-Parse-Checks an aktuellen Commits; bei realem Scan muss dessen tatsächliche lokale Konsole/JSON und Provenienz vorliegen. **Preflight PASS ≠ Scan PASS ≠ Compare PASS ≠ allgemeiner Metrik-Sieger.**
6. Anschließend General-Metrik-Forschung anhand der bisherigen experimentellen Evidenz und öffentlich verfügbarem MTT/FMA/DEAM fortsetzen. Keine Gewichte an den zwölf Pilotpaaren optimieren und dieselben Daten als unabhängige Evaluation verkaufen.

### Wissenschaftliche Ausrichtung und die vorhandenen Hörurteile

Die zwölf verblindet ausgewählten Songpaare sind alle **bewertet**: 24 verschiedene Tracks, 60/60 numerische Werte, sieben Kommentare. Paar 10 ist ein menschlich markierter gesprochener Interview-/Kommentar-Fall und wird ausschließlich für die 11-Musik-Sensitivität *zusätzlich* ausgeschlossen. Der Hörer möchte **keine** 36–40 weiteren Pflichtbewertungen. Die ursprüngliche Bewertungs-CSV ist tabulatorgetrennt, Windows-1252; die eingefrorene Auswahlprüfung selection-audit-private.json ist privat. Alle fünf Verfahren (Genre Cosine, Genre Centered, Mood Cosine, Mood Centered, Embedding Cosine) wurden mit vier Urteilsachsen bewertet; die kleine, modellselektierte Stichprobe ist nur explorativ. Auf 11 Musikpaaren: Mood Centered vs Playlist-Eignung Spearman rho 0,769463; Embedding Cosine vs Timbre rho 0,765707. **Das ist keine universelle Metrikentscheidung**; mehr unabhängige Evidenz erfordert MTT/FMA/DEAM sowie klare Datensatz-/Holdout-Grenzen. Symmetrische Song-Ähnlichkeit ist nicht identisch mit gerichteter Frage, ob B gut auf A folgt.

Die allgemeine untrainierte Metrik bleibt Pflicht und funktioniert ohne individuelle Urteile; persönliches Metric Learning/Blending bleibt eine spätere zusätzliche Option. Ohne trainiertes persönliches Modell gilt effektiv 100 % general.

## 4. Harte Projekt- und Rechtsgrenzen

- **PR #16, Original-Musik, vorhandene Rust-v5-DB, Lyrion-/Bliss-Datenbanken, alte Embeddings, Hörbewertungen, Methodik und 12-Paar-Scores NICHT ändern**, sofern der Nutzer nicht ausdrücklich separate Änderungen daran beauftragt.
- Nur dedizierter Bridge-Branch für automatische Scan-/Vergleichsskripte und Docs; kein Merge ohne Auftrag. Kein dynamisches Worker-Autotuning, PR #19 / Issue #21 nicht bearbeiten.
- Explorative Diagnoseschwellen der Bridge: maximaler absoluter Klassenscore-Fehler 0,001; minimaler Old/New-Song-Embedding-Cosine 0,999. Sie sind **keine** zertifizierte numerische Original-Essentia-Referenzparität. Bitgenaue Invarianz zwischen Worker-Konfigurationen und toleranzbasierte Referenzparität streng unterscheiden.
- **Native Windows-EXE/DLL-Weiterverteilung BLOCKED**: AGPL/FFmpeg/MSYS2, 17 fehlende installierte License Notices, ONNX-Lizenzfragen. Erfolgreicher Quellcode-Merge oder lokaler Scan ist keine Distributionsfreigabe.
- Nur anonymisierte Aggregate teilen; Song- und Feature-Dateien bleiben lokal.
- Vollautomatische Windows-Skripte müssen vorhandene Ausgangsdateien schützen, konkrete überprüfbare Fehler anzeigen, sauberes Git-/CI-Provenance-Tracking besitzen und vor potenziell destruktiven Aktionen sicher abbrechen.

## 5. Definition of Done und Dokumentationsreihenfolge

**Ziel der nächsten Session:** realer nativer 100-Song-Scan in neuen privaten Zielen + vollständiger 100-Song-/4.950-Paar-Rangvergleich und diagnostischer Vergleich alter/neuer Korrelationen zu denselben 12/11 bereits vorhandenen Hörurteilen; valide SHA-Kette und CI; keine Originaländerungen, keine neue Pflicht-Hörarbeit. Falls ein Gate scheitert, nur den genauen technischen Blocker diagnostizieren und beheben; keine Datenwerte oder Kohortenannahmen weichzeichnen.

Lies: **dieses** Dokument, [aktuellen Prompt](handover-prompt-native-similarity-100-20261029.md), [technisches Runbook](native-similarity-100-cohort-bridge-20261029.md), [native Scanner-Endstand](multi-worker-song-analysis-final.md), [28.10. Multi-Worker-zu-Similarity-Handback](handback-multi-worker-to-similarity-20261028.md), [Lizenzstrategie](essentia-licensing-distribution-strategy.md) und anschließend PR-#16-Similarity-Dateien. Ältere adaptive/Linker-Handover sind **historisch** und keine aktuellen Arbeitsaufträge.
