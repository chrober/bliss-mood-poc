# Kontrollierter A/B-Vergleich: direkte 1280D-Audio-Embeddings versus Genre/Mood

**Stand:** 21. Oktober 2026. **Arbeitsbranch:** `feat/similarity-metric-evaluation`. **PR:** [#16 (Draft)](https://github.com/chrober/bliss-mood-poc/pull/16).

## Forschungsfrage und Status

Welcher Song-Repräsentationsraum stimmt auf exakt denselben bereits
analysierten Aufnahmen besser mit einem menschlichen
Odd-One-Out-Similarity-Urteil überein: rohe Discogs-EffNet-Embeddings
(B), vorab berechnete Genre-/Mood-Klassifikationswerte (A), oder
später eine separat zu untersuchende Fusion (C)?

**Erster vollständiger B-vs-A-Lauf: PASS.** Das ist **explorative
korrelierende Evidenz**, kein unabhängiger Test, keine Aussage zu
Playlist-Übergängen und kein Produktionsentscheid.

- [GitHub Actions Run 39617159250](https://github.com/chrober/bliss-mood-poc/actions/runs/39617159250):
  vollständiger Erfolg, verifiziertes 1.019-Clip-Forschungs-Cache,
  vier getrennte `bliss-mood`-Prozesse, je ein ONNX-Thread.
  Aggregiertes, audiofreies
  [Ergebnisartefakt](https://github.com/chrober/bliss-mood-poc/actions/runs/39617159250/artifacts/12354255450).
- Die Embeddings stammen **aus exakt demselben Encoder-Durchlauf**
  wie die beiden Klassenköpfe, nicht aus einem zweiten unabhängigen
  Frontend. Decoder und Patchzählung sind identisch.
- Der Rust-v5-Basischeckout blieb exakt
  `2c3d44401436b3b41b6e067199016a1ed2335fbf`.
  Der separate Forschungs-Overlay wird nur im Actions-Runner
  angewendet; weder PR #17 noch sein gepinntes Binary-Cache
  wurden geändert.
- `research/song_embedding.rs` akkumuliert rohe Patch-Embeddings
  in `f64`, mittelt dann über Patches und normiert den
  Song-Vektor mit L2. Die Klassifikationskopf-Scores verbleiben
  im unveränderten SQLite-v3-Sidecar; das Embedding ist ein
  eigenständiges, versioniertes, pro Clip privates JSON.
- Der vorangehende standalone synthetische Smoke
  [Run 39616222834](https://github.com/chrober/bliss-mood-poc/actions/runs/39616222834)
  hatte gültige Rust-Unit-Tests und Release-Build,
  wurde aber durch Netzwerk-Timeout beim Upstream-Modell-Download
  blockiert. Das ist **nicht** als Embedding-Patch-Parität zu
  verbuchen. Zur Schließung dieser Lücke wurde ein synthetisches
  Off/On-/Thread-/Rohpatch-Paritätsgate in den MTT-A/B-Workflow
  aufgenommen; dessen nachfolgender Lauf separat prüfen.

## Exakt gleicher Nenner: 346/293/1019

MagnaTagATune liefert hier **346 unterschiedliche ungeordnete
Tripelfragen** mit **1.019 unterschiedlichen referenzierten Clips**.
**53** menschliche Mehrheitsgleichstände; die verbleibenden
**293** Fragen haben einen eindeutig mehrheitlich als
unähnlichsten gewählten Clip.

Für jede Methode werden dieselben 293 Fragen vorhergesagt.
Die ähnlichste von drei Paarungen bestimmt den Odd-One-Out.
Weder Fragefilter noch Clipset, Zuordnung der Menschenstimmen
oder Mehrheitsdefinition unterscheiden sich zwischen A und B.
Bei fehlender Vorhersage zählt eine Frage im gemeinsamen
Nenner als falsch; im bestätigten Lauf hatten alle hier
aufgeführten Verfahren **293/293 = 100 %** Vorhersageabdeckung.
Der naive Zufallsreferenzwert ist 33,33 %.

| Darstellung und Vergleich | Treffer | Quote, gleicher Nenner |
| --- | ---: | ---: |
| B: 1280D Discogs-EffNet, L2-Song-Mittel, Cosine | 182 / 293 | 62,116 % |
| A: 87D Genre, Cosine | 191 / 293 | 65,188 % |
| A: 56D Mood/Theme, Cosine | 192 / 293 | 65,529 % |
| A: 87D Genre, Centered Cosine | 191 / 293 | 65,188 % |
| A: 56D Mood/Theme, Centered Cosine | 193 / 293 | 65,870 % |

Auf diesen Menschenurteilen ist **direkte EffNet-Cosine in diesem
festgelegten Pooling schlechter** als alle vier kopfbasierten
Baselines. Die theoretisch reichhaltigere Dimensionalität
garantiert keine für diese Aufgabe besser geordnete Nachbarschaft.
Ein möglicher Grund ist, dass der bisherige Encoder
nicht speziell kontrastiv für menschliche
Songsimilarity trainiert wurde; diese Erklärung ist
**Hypothese**, nicht hier nachgewiesene Ursache.

## Gepaarte Differenzen und Unsicherheit

Es sind **gepaarte** Fragen und Methoden; Paare zählen nicht
als unabhängige Songs. `A_only_correct` beziehungsweise
`B_only_correct` zeigen die Fälle, in denen nur eine der
zwei Repräsentationen die menschliche Mehrheitsentscheidung trifft.
Die Angaben stammen aus dem aggregierten Ergebnisartefakt
des erfolgreichen Runs.

| Methode B minus A | Treffer nur B / nur A | Differenz in pp | Naives gepaartes Tripel-Resampling, 95-%-Bereich, pp | Künstlergewichts-Sensitivität, 95-%-Bereich, pp |
| --- | ---: | ---: | ---: | ---: |
| Embedding Cosine − Genre Cosine | 30 / 39 | −3,072 | −8,532 bis +2,048 | −6,235 bis −0,095 |
| Embedding Cosine − Mood Cosine | 27 / 37 | −3,413 | −9,215 bis +2,048 | −6,341 bis −0,268 |
| Embedding Cosine − Genre Centered | 26 / 35 | −3,072 | −8,191 bis +2,048 | −6,122 bis −0,216 |
| Embedding Cosine − Mood Centered | 27 / 38 | −3,754 | −9,215 bis +1,365 | −6,773 bis −0,969 |

**Vorsicht:** Die IID-Frage-Bootstraps sind bei
wiederverwendeten Songs und Künstlern *kein gültiges
Populations-Konfidenzintervall*. Da der MTT-Künstlergraph aus
einer zusammenhängenden Ko-Vorkommenskomponente besteht,
gibt es auch kein unabhängiges Artist-Cluster-Bootstrap.
Die zufälligen Künstlergewichtungen sind **reine
Abhängigkeits-Sensitivitätsdiagnostik**, keine Konfidenzintervalle,
auch wenn sie oben wie Quantile dargestellt sind.
Insbesondere dürfen die negativen Künstlergewichtungsbereiche
nicht als formale Signifikanzbeweise interpretiert werden.
Der naive gepaarte Intervallbereich enthält für alle vier
Vergleiche auch 0 und positive Verbesserungen.

## Reproduzierbarkeit und Ressourcen

- Komplette kontrollierte Repräsentationspipeline:
  [`research-mtt-embedding-ab.yml`](../.github/workflows/research-mtt-embedding-ab.yml),
  [`evaluate_mtt_embedding_ab.py`](../scripts/evaluate_mtt_embedding_ab.py),
  [`mtt_parallel_workers.py`](../scripts/mtt_parallel_workers.py)
  und [`research/song_embedding.rs`](../research/song_embedding.rs).
- Die kuratierte ZIP (119.689.247 Bytes) wurde ohne Download der
  2,77-GiB-Archive aus GitHub Actions Cache wiederhergestellt;
  **alle 1.019 Einträge anhand der offiziellen CRC geprüft**
  (Verification 0,52 s). Nicht cachefähige Archive
  **werden im neuen A/B-Workflow nicht heruntergeladen**;
  stattdessen Fail-Closed.
- Vier isolierte Inferenzprozesse, je ein ONNX-Thread;
  Analyse aller Clips rund 143 s (aus Runner-Schritten
  14:31:15–14:33:39 UTC), gepaarte Scoreberechnung
  **1,07 s**, maximal 108.160 KiB RSS für Scoreprozess.
  Locked-Cargo-Research-Build im Run: **68,94 s**
  Release-Stage, zusätzlich Unit-Test-Kompilierung; die
  Abhängigkeiten wurden anschließend in Rust-Cache gesichert.
- Erste Rust-Pooling-Unit-Tests: **3 PASS**.
  Python-Regressionstests auf Linux und Windows
  [Run 39616940299](https://github.com/chrober/bliss-mood-poc/actions/runs/39616940299):
  **beide Jobs PASS**.
- Referenzdateien bleiben runner-privat; das
  Actions-Artefakt publiziert ausschließlich aggregierte
  Scores, Preflight- und Sensitivitätszusammenfassungen,
  keine Aufnahmen, Einzelidentitäten, Stimmen oder Vektoren.

## Grenzen und nächste kontrollierte Experimente

1. **Technischer E1-Paritätsabschluss:** Den gerade ergänzten
   synthetischen Original-Encoder-Rohpatch-gegen-gepoolten
   Song-Vektor-Test, exakte Klassifikations/SQLite-off-on-
   Gleichheit, 1-vs-2-Thread-Determinismus kontrollieren.
   Bei Pass ist dies **ONNX-interne** Pooling/Regressionsparität,
   weiterhin kein neuer flächiger TensorFlow/Essentia-C++-
   Embedding-Äquivalenzbeweis.
2. **Unabhängige B-Validierung:** Die bisherigen FMA-Small-
   Validation- (offiziellen TEST unangetastet) und DEAM-
   Development-Cohorts prüfen, mit Repräsentation B auf
   *denselben* Tracks und strikt jeweiligen Genre-/Mood-
   Zielgrößen. Ein schlechterer MTT-Befund darf nicht
   als globaler Misserfolg von 1280D abgetan werden.
   Mögliche MTG-Jamendo-Training-Katalog-Überlappungen,
   FMA-MTG-Kandidaten und sonstige Dataset-Leakage explizit
   kennzeichnen.
3. **Später optional:** Gesonderte, kontrastiv auf
   Similarity trainierte Discogs-Modelle aus dem
   Essentia-Katalog mit eigenen neuen SHA/Fingerprints
   als andere Modellfamilie vergleichen. Der vorhandene
   Encoder ist kein Nachweis für deren Leistung.
4. **C Fusion:** Keine auf bereits exploriertem MTT
   getunten Mischgewichte. Vorab festgelegte
   Kombinationen und Development-only-Kalibrierung
   erst bei ausreichendem unabhängigen Referenzmaterial
   untersuchen.
5. **Lyrion Mixing:** Klangnähe/Genre/Mood und
   Playlist-Übergänge getrennt evaluieren. Bliss-first,
   Feature-first und Hybrid als Kandidatengenerierungs-
   strategien sind **andere Entscheidungen** als A/B/C
   Similarity-Repräsentationen. Keine Produktivänderung
   an Bliss Mixer, Lab, PR #13 oder PR #17.

**Entscheid:** Weiter forschen, kein Production Winner,
PR #16 bleibt Draft und `main` unverändert.

## Ergänzendes Paritätsgate: technisch vollständig PASS

Der nachgelagerte [Actions-Run 39618323154](https://github.com/chrober/bliss-mood-poc/actions/runs/39618323154)
hat **sowohl das neue synthetische Rohpatch-Paritätsgate
als auch den vollständigen 1019-Clip-/346-Tripel-A/B**
mit exakt denselben bestätigten fünf Trefferzahlen
**erfolgreich** abgeschlossen. Der rein aggregierte
[Report samt Paritätsprotokoll](https://github.com/chrober/bliss-mood-poc/actions/runs/39618323154)
enthält:

| Verifikationspunkt | Gemessener Wert |
| --- | --- |
| Synthetische WAV-Länge | 6 Sekunden |
| Ausgegebene EffNet-Patches | 4 |
| Song-Embedding-Dimension | 1280 |
| Max. unabhängige Rohpatch-Pooling-Abweichung | 1,0855063 × 10⁻⁸ |
| Abweichung des L2-Normwerts von 1 | 4,1199244 × 10⁻¹⁰ |
| Max. Unterschied 1 vs. 2 ONNX-Threads | **0,0** |
| Genre-/Mood-Werte bei Export aus versus ein | **exakt gleich** |
| SQLite-v3-Modelle/-Trackzeilen ohne/mit Export | **exakt gleich** |
| Audio-MTT-A/B, 1019 Clips / 293 entscheidbare Fragen | **PASS, unveränderte Ergebnisse** |

Die Einheitentest-Gates wurden ebenso bestanden, ohne private
Musikdateien zu analysieren. **Das belegt ONNX-interne
Pooling- und Klassifikationsregressionsparität für diesen
synthetischen Fall; keine vollständig erneute Mehrsong-Parität
zum TensorFlow/C++-Embedding-Original.** Die ältere, allein durch
Upstream-Modell-Timeout gescheiterte Standalone-Smoke-Action
ändert nichts an diesem separat erfolgreich ausgeführten
identischen und zusätzlichen Gate.

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
