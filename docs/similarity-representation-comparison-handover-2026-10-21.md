# Handover: Drei Repräsentationsansätze für Song-Similarity

**Stand:** 21. Oktober 2026 · **Repository:** [chrober/bliss-mood-poc](https://github.com/chrober/bliss-mood-poc) · **Branch:** `feat/similarity-metric-evaluation` · **PR:** [#16 (Draft)](https://github.com/chrober/bliss-mood-poc/pull/16).

**Kernfrage:** Wie berechnen wir aus offline analysierten Audioaufnahmen musikalisch nützliche **Song-zu-Song-Ähnlichkeit**, und welche Repräsentation eignet sich für welchen Zweck? **Noch keine Produktionsentscheidung.** Die bisherige Forschung testete sieben Distanzen/Ähnlichkeiten auf *Klassifikationsvektoren*. Der nächste wissenschaftlich wichtige Vergleich ist **Klassifikationsvektoren vs. direkte Audio-Embeddings vs. kombinierte Signale**; die Metrikwahl allein löst nicht die Repräsentationsfrage.

## 0. Begriffe und zwei strikt getrennte Entscheidungsebenen

- **Repräsentation:** Welcher Vektor beschreibt einen Track? Zum Beispiel 87 Genre-Scores, 56 Mood/Theme-Scores oder ein 1.280D Audio-Embedding.
- **Similarity-Metrik:** Welche mathematische Funktion vergleicht *zwei Vektoren derselben Repräsentation* (Cosine, Centered Cosine, Weighted Jaccard, RMS usw.)? Die Transformation `1 - cosine_distance` und normalisierte Richtung haben eine andere Semantik als kalibrierte Wahrscheinlichkeiten; absoluter Score ist **keine** Wahrscheinlichkeit für eine gute Überleitung.
- **Fusion/Ranking:** Wie kombinieren wir *verschiedene* Ähnlichkeitsinformationen für eine bestimmte Aufgabe (Genre-Treue, Mood-Treue, allgemeine Klangnähe, Übergangsqualität)?
- **Lyrion-Kandidatengenerierung/Mixing:** **Andere Ebene:** `Bliss-first`, `Mood-/Genre-first` und `Hybrid` sind **drei alternative Quellen- und Mischstrategien** in [lyrion-bliss-mood-genre-integration.md](lyrion-bliss-mood-genre-integration.md). Der hier behandelte **dritte Repräsentationsansatz (Fusion)** ist **NICHT** automatisch die Lyrion-Mixing-Strategie `Hybrid`. Jede Kombination ist technisch mit mehreren Kandidatenstrategien vereinbar.

### Ist-Zustand im Repository (durch Quellcode geprüft)

`model-registry.json` referenziert `discogs-effnet-bsdynamic-1.onnx` als gemeinsamen Encoder (`embedding_dimensions: 1280`) und die beiden MTG-Jamendo-Klassifikationsköpfe `genre` (87 **Sigmoid**-Klassen) und `moodtheme` (56 **Sigmoid**-Klassen); optional `voice` (2 Softmax). Diese unabhängigen Sigmoid-Werte sind **keine auf 1 summierten Wahrscheinlichkeitsverteilungen**.

`src/features.rs::FeatureEngine::analyze` extrahiert **je Patch** einen **1.280-dimensionalen Float32-Embedding-Vektor** (`tensor.len() == 1280`) aus ONNX, übergibt ihn an beide Köpfe und mittelt anschließend **die jeweiligen Klassifikationswerte** über Patches. Die bisherige schema-v3-Persistenz in `feature_tracks.scores_f32_le` speichert **Head-Scores**, **keine persistierten 1.280D-Song-Embeddings**. Daraus folgt: *Ein gemeinsamer 1.280D-Song-Vektor wird derzeit nicht als nachgewiesene Version/Semantik gespeichert.* Für einen Embedding-Vergleich brauchen wir zunächst eine optionale, getrennte, versionierte Ausleitung/Poolung; ein einfaches SQL-Auslesen der bestehenden 87/56D-Sidecars reicht nicht.

Die Rust-v5-Numerik wurde gegenüber der bisherigen Essentia-Implementierung für die bestehenden Klassifikationsköpfe geprüft. **Diese Parität belegt noch keine neue Song-Level-Embedding-Poolung oder deren Cosine-Ranking.**

```mermaid
flowchart TD
    A[Audio eines Songs] --> B[Essentia-kompatibles Preprocessing / Patches]
    B --> C[Discogs-EffNet ONNX / 1280D pro Patch]
    C --> G[Genre-Kopf / 87D Sigmoid pro Patch]
    C --> M[Mood/Theme-Kopf / 56D Sigmoid pro Patch]
    G --> GA[Genre-Scores über Patches mitteln]
    M --> MA[Mood-Scores über Patches mitteln]
    GA --> S1[Ansatz 1: Klassifikations-Similarity]
    MA --> S1
    C --> P[NEU: Song-Embedding poolen / versioniert speichern]
    P --> S2[Ansatz 2: Direkte Embedding-Similarity]
    S1 --> F[Ansatz 3: Late Fusion / aufgabenabhängiges Ranking]
    S2 --> F
    F --> R[Offline-Evaluation und späterer Lyrion-Ranker]
```

## 1. Ansatz A — Ähnlichkeit der interpretierten Genre-/Mood-Klassifikationsvektoren

**Daten:** `G(song) ∈ [0,1]^87` und `M(song) ∈ [0,1]^56`, beide bereits in schema-v3-Sidecars vorhanden. Berechnungen pro Kopf getrennt, keine unkalibrierte Zusammenrechnung.

**Sieben derzeit untersuchte Metriken** (siehe [similarity-metric-evaluation.md](similarity-metric-evaluation.md) / `scripts/evaluate_similarity.py`): RMS-basierte Similarity, Cosine, Centered Cosine, Weighted Jaccard, ursprüngliches Cutoff-Top-K Weighted Jaccard sowie rangbasiertes Top-6 und Top-12 Jaccard. *Centered Cosine ist kein Verfahren für embeddingspezifische Zentrierung des gesamten Datensatzes; es subtrahiert den Mittelwert innerhalb jedes Vektors.*

**Stärken:** Interpretiert / diagnostizierbar nach Genre und Mood; direkte Regeln wie „Genre hoch, Mood eher frei“ möglich; kompakt (87+56 Float32 ≈ **572 Byte/Song** vor SQLite-Metadaten); Head-spezifisches Validieren ist sinnvoll.

**Schwächen:** Beide Köpfe komprimieren die reichhaltigere Audio-Information auf ihre jeweiligen Annotations-Taxonomien; allgemeine Klangähnlichkeit (Instrumentierung, Produktion, Sounddesign, rhythmische Feinheiten) wird womöglich nicht vollständig repräsentiert. Mehrere kleine Sigmoid-Outputs können die Metriken verzerren. Genre-/Mood-Kategorien sind nicht automatisch ground truth für *gute Songübergänge*.

**Nachgewiesene Forschung, nicht „Sieger“:**
- MagnaTagATune: **346 unterschiedliche ungeordnete Tripel / 1.019 Clips**, **53 menschliche Mehrheits-Gleichstände** und **293 auswertbare Fragen**. Auf 293 gemeinsamen Fragen, Abstentionen als falsch, Genre: Cosine **65,2 %**, Centered Cosine **65,2 %**. Mood: Cosine **65,5 %**, Centered Cosine **65,9 %**. Cosine minus Centered beim paarweisen Vergleich: **0,0 Prozentpunkte Genre** (5/5 diskordante Richtiger) und **−0,3 Prozentpunkte Mood** (8/9). Der alte Top-K-Cutoff deckt Mood nur **71,7 %** der auswertbaren Fragen ab. Dies ist **explorativ**, kein unabhängiger Holdout. Quelle: [magnatagatune-paired-analysis-2026-10-21.md](magnatagatune-paired-analysis-2026-10-21.md).
- FMA-Small: offizieller **VALIDATION**-Split, 80 Katalog-bereinigte, künstlerunterschiedliche Tracks aus acht groben Genres: Genre **P@5 Cosine 0,3200**, **Centered Cosine 0,3225**, Weighted Jaccard 0,3000; dies ist **eine andere Stichprobe** als die frühere unbereinigte Validation (nicht paarweise vergleichbar). Der offizielle FMA-**TEST**-Split bleibt **unberührt**. Quelle: [fma-mtg-catalog-overlap-2026-10-21.md](fma-mtg-catalog-overlap-2026-10-21.md).
- DEAM: **Valence/Arousal** als *Proxy* für Mood-Nähe, **nicht** als direktes Label für alle 56 Mood-Klassen und **nicht** als menschliche Genre-/Übergangsähnlichkeit; filtrierte Stichprobe von 240 Tracks, Mood-Cosine Spearman **0,2868**, Weighted Jaccard **0,2888**. Quelle: [similarity-cross-dataset-evidence-2026-10-21.md](similarity-cross-dataset-evidence-2026-10-21.md).

**Status:** Ansatz A implementiert und mehrfach extern explorativ untersucht, **keine Produktionswahl**.

## 2. Ansatz B — Direkte Ähnlichkeit von 1.280D Audio-Embeddings

**Daten:** Der **gleiche** vorhandene `discogs-effnet-bsdynamic-1.onnx` erzeugt pro Audio-Patch einen 1.280D-Vektor **vor** Genre-/Mood-Klassifikation. Ein Song-Level-Vektor `E(song) ∈ ℝ^1280` muss anhand einer expliziten Aggregation definiert werden.

**Minimal-Baseline:** Arithmetischer Mittelwert der Float32-Patch-Embeddings in Float64-Akkumulatoren, anschließend optional L2-Normierung für Cosine. **Vorher** festlegen und protokollieren, ob Patch-Embeddings einzeln L2-normalisiert werden oder nur der gepoolte Song-Vektor. Diese Varianten sind **nicht äquivalent**. Eine erste Vergleichsversion: `mean(raw patch embeddings) → L2-normalize(song mean) → cosine`. Nicht unbemerkt durch normierte Patch-Mittel ersetzen.

`cosine(Ea, Eb) = dot(Ea, Eb) / (||Ea||₂ · ||Eb||₂)`, mit endlichen Werte-/Dimensions-/Nullnorm-Checks. Nicht automatisch auf `[0,1]` clampen; ein Cosine über reale Embeddings liegt grundsätzlich in `[-1,1]`. Kann zum Ranking per ANN/Nearest-Neighbor indexiert werden (Index und Suchstrategie sind **separate** Entscheidungen).

**Stärken:** Höhere Ausdrucksstärke und potenziell Klang-/Stilähnlichkeit jenseits der festen 87/56 Tags; gleicher ONNX-Encoder wird bereits aufgerufen, daher prinzipiell **keine zweite Encoder-Inferenz** nötig. Song-Level-Speicherbedarf: **1.280 × Float32 = 5.120 Byte/Song**, etwa **9×** die 87+56D-Head-Nutzdaten; für eine Million Songs ca. **5,12 GB** rohe Vektoren (dezimal, ohne Datenbankindizes/Overhead). ANN und Vorfilterung sind erst für große Kataloge nötig.

**Schwächen:** Weniger erklärbar als Tags; hohe Dimension ist keine Garantie für Mood-/Playlist-Kohärenz; Modelltraining prägt Ähnlichkeit. Bei längeren Songs kann der globale Durchschnitt dramaturgische Abschnitte ausmitteln. Alternative Mehrsegment-/robuste Poolung ist eine **spätere** Hypothese, keine stillschweigende Vorgabe. Numerische Parität für neuen Export muss separat geprüft werden.

**Externe Evidenz (kein direktes Benchmark-Ergebnis für unser Projekt):**
- [cosine.club — About/FAQ](https://cosine.club/about) beschreibt produktiv die Verwendung von **Discogs-EffNet**, **1.280D-Audio-Embeddings** und **Cosine Similarity** für Klangähnlichkeitssuche über einen großen Katalog. Dies zeigt technische Praxistauglichkeit, **nicht** superiority gegenüber unserem 87/56D-Ansatz oder gute Lyrion-Übergänge.
- [Essentia Modellkatalog](https://essentia.upf.edu/models.html) dokumentiert die Discogs-EffNet-Klassifikationsmodelle und **separate kontrastiv trainierte Embedding-Modelle** für Artist-, Label-, Release-, Track- und Multi-Ähnlichkeitsziele (Alonso-Jiménez, Serra, Bogdanov, ISMIR 2022). Diese spezifischen **kontrastiven** Modelle sind **andere Modellgewichte/Ziele** als unser aktueller `discogs-effnet-bsdynamic-1.onnx`; die dokumentierte Existenz ist kein Beleg, dass die bisherige Head-Numerik damit unverändert bleibt.
- Essentia nennt [cosine.club in seinen Demos](https://essentia.upf.edu/demos.html) als Beispiel für Klangähnlichkeitssuche auf Discogs-EffNet-Embeddings.

**Status:** Der 1.280D-Vektor existiert aktuell **intern pro Patch**, aber **Ansatz B ist als Song-Level-Sidecar und Benchmark noch nicht implementiert/evaluiert**. Primärer nächster Implementierungsschritt.

## 3. Ansatz C — Fusion von Audio-Embedding, Genre und Mood

**Idee:** Drei unterschiedliche Evidenzquellen pro Songpaar berechnen und erst **nach separater Definition/Kalibrierung** fusionieren:
`s_E(a,b)` aus 1.280D-Embedding, `s_G(a,b)` aus 87D Genre, `s_M(a,b)` aus 56D Mood. Grundform als **Baseline-Hypothese**: `s(a,b | task) = w_E·f_E(s_E) + w_G·f_G(s_G) + w_M·f_M(s_M)`, `w_i >= 0`, `Σ w_i = 1`.

**Wichtig:** `f_E/f_G/f_M` sind **reproduzierbare, auf Entwicklungsdaten eingefrorene** Normalisierungs-/Kalibrierfunktionen (z.B. trainingsstatistikbasierte rank/quantile-Scores). Rohwerte nicht addieren: Cosine auf Embeddings, Cosine auf Sigmoids und RMS unterscheiden sich in Verteilung und Aufgabe. Naive gleiche Gewichte sind ein **zu testender Baseline-Kandidat**, kein gerechtfertigter Default. Eine alternative robuste Fusion ist **Rank Aggregation** von je Kopf sortierten Kandidaten (nur dann, wenn definierte gemeinsame Kandidatenbasis, Abstention- und Missing-Head-Regel).

**Beispielhafte Aufgabenhypothesen (keine validierten Parameter):**
- **Allgemeine klangliche Nähe:** `w_E` möglicherweise dominant, `G/M` zusätzliche semantische Kontrollsignale.
- **„Ähnlicher Stil/Genre“:** hoher `w_G`, aber Embedding gegen rein taxonomische Fehl-Nachbarn.
- **„Gleiche Stimmung, Genre darf wechseln“:** höherer `w_M` und gelockerter Genreanteil.
- **Playlist-Sequenz/Übergänge:** Neben Songpaar-Similarity auch Stil-Drift, Monotonie, Tempo/Energie, Nachbarabstände, Artist-Repeats und Lyrion-Hard-Constraints im *übergeordneten* Mixing evaluieren; „maximale Similarity überall“ ist nicht automatisch eine gute Playlist.

**Stärken:** Anwendungsfall-spezifische Kontrolle und Interpretierbarkeit mit reichhaltigem Klangsignal; ggf. besserer Trade-off zwischen akustischer Nähe, Mood/Genre-Kohärenz und Vielfalt. **Schwächen:** Zusätzliche Gewicht-/Kalibrierparameter erhöhen Overfitting-Risiko, besonders auf winzigen, nicht unabhängigen Musikdatensätzen. Missing-Vector-Strategie, Korrelation zwischen Embedding und Heads und Verzerrung durch Artist-/Albumwiederholung explizit behandeln.

**Status:** Nur Architekturhypothese, **nicht** in unseren wissenschaftlichen Benchmarks gemessen und **nicht** als gewählte Mixing-Strategie implementiert. Erst nach belastbarer B-Baseline und vorab eingefrorenem Entwicklungs-/Holdout-Plan testen.

## 4. Bereits vorhandene Evidenz und ihre Grenzen

| Korpus | Menschliche / externe Referenz | Für A vorhanden | Für B und C | Harte Grenze |
| --- | --- | --- | --- | --- |
| **FMA-Small** | Acht grobe Genre-Labels, Retrieval P@5/mAP/nDCG | Ja, 80 Validation (unbereinigt sowie anders gezogene katalogbereinigte Stichprobe) | **Noch nicht** | Official **TEST versiegelt**, potentielle MTG-Katalogtreffer, kleine Stichprobe |
| **DEAM** | Kontinuierliche Valence/Arousal-Bewertungen | Ja, 240-Song-Proxy-Benchmark | **Noch nicht** | VA ≠ 56 Mood-Klassen oder Übergangsqualität |
| **MagnaTagATune** | Allgemeine menschliche Odd-one-out-Urteile | Ja, volle 346 Tripel, 293 ohne Menschenmehrheits-Tie | **Noch nicht** | Alle Tripel bereits exploriert, **kein unangetasteter MTT-Holdout**; ein gemeinsamer Artist-Zusammenhang |
| **MTG-Jamendo** | Klassifikationslabels + Modell-/Trainingsprovenienz | Catalog overlap audit | **Noch nicht** | Kein genereller unabhängiger Ähnlichkeits-/Playlist-Referenzdatensatz |

**Nicht verschiedene Metriken aufsummieren:** FMA-Genre P@5, DEAM Mood-/VA-Spearman und MagnaTagATune Odd-one-out-Accuracy erfassen **unterschiedliche Zielgrößen**. Der A/B/C-Vergleich soll **innerhalb jedes Datensatzes** identische Tracks, Patches, Referenzurteile, Evaluationslogik und Missing-Policy verwenden.

**Data leakage / Lizenz:** Ein MTG-Katalogname kann mit FMA oder DEAM übereinstimmen, ohne dass die Aufnahme oder ONNX-Trainingszugehörigkeit belegt wäre. Der Discogs-Encoder hat einen eigenen möglichen Overlap. Die bisherige FMA-TEST-Sperre bewahren; kein privater Lyrion-Audioscan, keine Musikdateien/Vektoren in öffentlich lesbaren Artefakten. Die 1.019-MTT-Clip-Research-Cache-Datei beinhaltet weiterhin lizenzgebundenes Drittaudio und darf nicht als öffentliches GitHub-Artefakt verteilt werden.

## 5. Priorisierter technischer Plan für die nächste Chat-Session

### P0 — Technische Verträge und Regressionen einfrieren

1. Branch `feat/similarity-metric-evaluation`, Draft PR #16, aktuellen Repo-Head prüfen. Keine Merges oder Änderungen an `main`, PR #13/#17 oder dem Produktionsmixer. Quelltexte `src/features.rs`, `src/storage.rs`, `src/main.rs`, `model-registry.json` auf aktuellen Stand prüfen.
2. **Kleines, versionsgebundenes Embedding-Exportformat** entwerfen, nicht die Semantik alter `feature_tracks`-Head-Scores überschreiben: eigenständiges Modell-/Embedding-Profil mit Encoder-SHA256, Layer/Output, Preprocessing, Pooling, Normalisierung, Anzahl Patches, Dimension 1280, Float32-Endian, Audio/Track-Key und Schema-Version. Eine neue Tabelle oder separate Sidecar ist zulässig; proprietäre Original-Track-IDs bleiben lokal.
3. Ein Songanalyse-Durchlauf berechnet patchweise 1.280D-Embeddings **einmal** und speist dieselben unveränderten Patches in Genre/Mood-Head. Für neuen Export `mean(raw patches)`, dann L2-Norm für Vergleich; gegen Nullnorm/NaN/Inf und Ton-/Audio-Längenartefakte absichern. **Keine zweite ONNX-Inferenz für die Baseline nötig.**
4. **Regression/Parität**: Mit exakt fixierter Audiodatei und Modellen prüfen, dass bestehende 87/56D-Head-Vektoren und numerische Rust-v5-Paritätsaussage **unverändert** sind; neue Embedding-Poolung mit Referenzimplementierung in Python/Essentia vergleichen. Unterschiedliche Aggregationsdefinitionen nicht als dieselbe Referenz behandeln. Nullnorm-, extreme Patch-Anzahl-, Determinismus- und mehrere Worker-Tests.

### P1 — Vergleich B gegen A auf identischer Kohorte

5. Erst einen kleinen, **ergebnisblinden** CI-Smoke aus schon legal/correct zugänglichem Audio, dann kostensparende volle MTT-Explorationskohorte mit vorhandenen 1.019-Clip-Cache und gepinnter Rust-v5-CLI wiederverwenden. Keine unberechtigte Behauptung, MTT sei nachträglich held-out.
6. In paralleler Vergleichsausgabe, je identischem Songpaar/Tripel: `cosine(E_mean)` vs beste **bereits eingefrorene** Genre-/Mood-Baselines (`cosine`, `centered_cosine` und je nach Aufgabe `weighted_jaccard`). Ergebnisse durch MTT-Fallgleichheit, gleiche humane Mehrheits-Ties und abstention-inclusive denominator vergleichen. Auch FMA Validation Genre und DEAM VA-Mood auf **denselben jeweiligen** Tracks vergleichen; nicht aus unbereinigt/bereinigt neu gesampelten Gruppen künstlich einen Paarvergleich bauen.
7. Qualität **und** Zeit dokumentieren: Caches nur bei verträglichem Daten-/Lizenzzugriff, Modell-Hash, Feature-Persistenz/Peak-RSS, GH runners mit 1/2/4 isolierten Workern, Patches pro Song und NN-Index erst bei Bedarf. Bestehende GH Workflows bereits mit Audio-Cache (MTT: 1.019 selektierte MP3s ≈114 MiB) und gepinntem Binary; Build- und Download-Time separat messen.

### P2 — Fusion C als Experiment, nicht Default

8. A, B, C als reproduzierbare `representation_id` / `ranking_policy` dokumentieren. Fusionsvarianten nur wenige, **vorher festgelegte** (`E-only`, `G-only`, `M-only`, `E+G`, `E+M`, `E+G+M`, ggf. rank aggregation), mit separatem Genre-/Mood-/General-Human-Evaluationsreport. Gewichtung/Kalibrierung nur an Entwicklungskorpus fitten, unabhängigen späteren Korpus unangetastet lassen.
9. Ergänzend **kontrastive Discogs-EffNet-Varianten** aus dem offiziellen Essentia-Katalog **als eigene Modellstudie** betrachten, nicht als austauschbare ONNX-Schicht des jetzigen Klassifikationsmodells. Vor Einbezug in Rust prüfen: verfügbares ONNX, Lizenz/Verteilung, Feature-Protokoll, Vergleichsreferenz, inferenzseitige CPU/RAM-Kosten.
10. **Finale Entscheidung** erst nach unabhängiger Bestätigung mit getrennten Zielkriterien (Genre Retrieval, VA Mood, allgemeines human similarity, echte Lyrion-Übergänge) und später blindem Lyrion-Playlist-Hörtest, inklusive Drift, Vielfalt und Repeat-Constraints. Kandidatenstrategien `Bliss-first/Mood-Genre-first/Hybrid` **nachgelagert separat** auf identischem Korpus/Seed testen.

### Qualitäts- und Daten-Gates

- Keine neue Modellüberlegenheit oder „bestes Verfahren“ behaupten, bevor B/C **auf echten gemeinsamen Daten** gemessen wurden.
- Bereits untersuchte MTT-Tripel nicht als unabhängiges Holdout deklarieren. FMA offizielles **TEST** nicht für explorative Optimierung öffnen.
- Einheitliche Seed-/Audio-/Modell-/Pooling-Provenienz, exakte Vektordimension und Normalisierung dokumentieren; hohe absolute Cosine-Werte nicht als kalibrierte Prozentwahrscheinlichkeiten ausgeben.
- Keine Audiodateien / Song-Identitäten / per-Song-Vektoren / per-Tripel Rohlabels als öffentliches GH Artifact oder Commit. Kein Scannen privater Lyrion-Musik. Forschung und Produkt-Mixer strikt getrennt.
- Dokumente und Handover im Repository fortlaufend aktualisieren; alle langen GH Workflows nur mit relevanten Pfad-/Workflow-Triggern, Build-Caches, Benchmark-Stufenzeiten. Bestehende Python/Rust CI auf Linux/Windows respektieren.

## 6. Quellen und Wegweiser

**Externe belegte Quellen:**
- Offizielle [Essentia Modelle](https://essentia.upf.edu/models.html) — Discogs-EffNet, Unterschiede zwischen Style-Klassifikation und separat kontrastiv trainierten Artist/Label/Release/Track/Multi-Varianten, 1.280D Embeddings und Head-Anbindung.
- [Essentia Demos](https://essentia.upf.edu/demos.html) — verlinkt Klangähnlichkeitssuche mit Discogs-EffNet.
- [cosine.club FAQ](https://cosine.club/about) — konkretes Beispiel: Discogs-EffNet-Embedding und Cosine-basierte Musikähnlichkeitssuche; **Demonstration, nicht unabhängige Qualitätsstudie**.
- Alonso-Jiménez, Serra, Bogdanov (2022), *Music Representation Learning Based on Editorial Metadata from Discogs*, ISMIR; Referenz im Essentia-Modellkatalog.

**Repo-Unterlagen:**
- [Genre/Mood Metriken und Datenstruktur](similarity-metric-evaluation.md).
- [Datensatzübergreifende Evidenz und methodische Einschränkungen](similarity-cross-dataset-evidence-2026-10-21.md).
- [MTT gepaarte Auswertung und Laufzeiten](magnatagatune-paired-analysis-2026-10-21.md).
- [FMA-MTG-Katalogüberschneidung](fma-mtg-catalog-overlap-2026-10-21.md).
- [Lyrion Mix-Strategien: Bliss-first vs Feature-first vs Hybrid](lyrion-bliss-mood-genre-integration.md).
- [Feature-Provider-Architektur](feature-provider-architecture.md).

**Handover-Status:** Die nächste Session beginnt **nicht** mit einer weiteren reinen Cosine-vs-Weighted-Jaccard-Diskussion. Sie beginnt mit einem **reproduzierbaren, optionalen 1.280D-Embedding-Export aus dem vorhandenen Rust-v5-EffNet-Pfad** und anschließender auf denselben Musiktiteln paarweise vergleichbarer A/B/C-Evaluation. Keine bereits existierenden qualitativen Ergebnisse auf den neuen Embedding-/Fusion-Ansätzen unterstellen.
