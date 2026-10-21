# Handover: drei Repräsentations- und Similarity-Ansätze für Lyrion

**Stand: 21.10.2026 · Branch: feat/similarity-metric-evaluation · Draft PR #16.**
Forschungs-/Architekturentscheidung **OFFEN**. Dieses Dokument ist die
maßgebliche Einstiegshilfe für die nächste Chat-Session. Weder ein neuer
Produktionsalgorithmus noch ein Merge nach `main` wurde beschlossen.

## Das eigentliche Problem

Wir vergleichen Songs anhand bereits offline extrahierter Merkmale. Es
gibt dabei **zwei voneinander unabhängige Entscheidungen**:

1. **Repräsentation:** Welcher Song-Vektor und welche Information sollen
   musikalische Nähe ausdrücken? (87D Genre, 56D Mood, 1280D
   Discogs-EffNet-Embedding oder Kombination)
2. **Vergleich/Ranking:** Welche Metrik wird *innerhalb* der jeweiligen
   Repräsentation verwendet (z. B. Cosine, Centered Cosine, Jaccard) und
   wie werden mehrere Signale zusammengeführt?

Die sieben bereits getesteten Metriken beantworten nur einen Teil von
Punkt 2 **für die Klassifikationsvektoren**. Sie klären NICHT, ob
Genre-/Mood-Klassen überhaupt die beste Basis für *allgemeine*
musikalische Ähnlichkeit sind.

## Drei gleichberechtigt zu untersuchende Ansätze

### A — Klassifikationsvektoren (unser bisheriger, bereits getesteter Pfad)

```text
Audio → Discogs-EffNet (1280D pro Patch)
                        ├── Genre-Kopf → 87 Sigmoid-Werte pro Patch
                        └── Mood/Theme-Kopf → 56 Sigmoid-Werte pro Patch
Song-Level: arithmetischer Mittelwert der Klassifikationswerte
Je Kopf separate Similarity → Genre- und/oder Mood-Ranking
```

**Nutzen:** transparentere Kategorien; explizite Suche nach
Genrenähe und Stimmungsnähe; Kopf-spezifische Gewichte; bereits im
schema-v3-Sidecar und `scripts/evaluate_similarity.py` umgesetzt.
Die Scorewerte sind **mehrere unabhängige Sigmoid-Aktivierungen**,
keine sich zu eins summierende Multinomialverteilung; selbst bei
Aktivierung 0.8 ist keine über Kopf-/Genregrenzen kalibrierte
Wahrscheinlichkeit garantiert.

Sieben bisher verglichene Metriken: **RMS, Cosine, Centered Cosine,
Weighted Jaccard, cutoff Top-K Weighted Jaccard (alte/problematische
Baseline), rankbasiertes Top-6 und Top-12 Jaccard**. Genre und Mood
wurden **getrennt** ausgewertet. Die alte cutoff-Top-K-Variante
abstiniert bei vielen Mood-Tripeln und darf nicht nur auf abgedeckten
Fällen bewertet werden.

**Vorteile:** nachvollziehbare Stimmung/Genre-Interpretation;
kompakte Vektoren; geringer Speicherbedarf; Benchmark-Tools,
Regressionstests und cached GitHub-Daten sind vorhanden.

**Nachteile:** Der 1280D-Raum wird auf 87/56 vorgegebene Klassen
projiziert und kann Information über Klangfarbe, Produktion, Timing,
Instrumentation und andere latente Ähnlichkeit verlieren. Ein
allgemeiner Similarity-Wert auf Klasse-Aktivierungen muss keine
allgemeine musikalische Wahrnehmungsnähe ergeben. Entstehende
Genre- und Mood-Rangfolgen können sich widersprechen.

**Baseline für neue Arbeit:** Cosine auf dem Genre-Kopf, Cosine
auf dem Mood-Kopf sowie Centered Cosine als unmittelbarer Challenger;
Weighted Jaccard als weitere fachlich plausible Alternative.
Das ist keine Entscheidung für einen Produktivstandard.

### B — Direkte 1280D Discogs-EffNet-Audio-Embeddings (neu zu testen)

```text
Audio → Discogs-EffNet → 1280D latentes Embedding pro Audio-Patch
                         ↓
          Song-Level-Pooling, z. B. Mittelwert über Patches
                         ↓
          Normierung und Cosine Similarity
                         ↓
               klangliches Nachbarschaftsranking
```

**Externe Referenz, keine in PR #16 bereits gemessene Lyrion-Evidenz:**
[cosine.club/about](https://cosine.club/about) beschreibt ausdrücklich
die Verwendung desselben **Discogs-EffNet-Modelltyps**, 1280D
Track-Embeddings und **Cosine Similarity** für inhaltliche
Musik-Nachbarschaftssuche in einem Katalog mit über zwei Millionen
Titeln. Das ist eine reale, nutzbare Baseline – **kein Beweis**, dass
dieses Verfahren unsere Genre-, Mood- oder Playlist-Ziele besser
erfüllt. Sein Katalog und seine Zielvorstellung (Audio-Sound-Nähe)
unterscheiden sich von Lyrion.

Die [offizielle Essentia-Modellübersicht](https://essentia.upf.edu/models.html)
dokumentiert den Discogs-EffNet-Embedding-Extraktionspfad sowie
*gesonderte* Artist-, Label- und Multi-Task-**contrastive
embedding**-Modelle, die mit Ähnlichkeitszielen trainiert wurden.
Die contrastive Varianten sind **andere Gewichte/Modelle**:
Nicht stillschweigend behaupten, dass unser vorhandener
Discogs-EffNet-Encoder bereits auf perzeptive Ähnlichkeit
optimiert sei. Andere Embedding-Familien (MusiCNN, OpenL3 etc.)
sind vorerst optionale spätere Vergleichskandidaten, kein Grund,
die aktuelle Portierung erneut großflächig umzubauen.

**Wichtigster überprüfter Implementierungsbefund:**
`src/features.rs` auf dem Similarity-Branch erzeugt in
`FeatureEngine::analyze` den 1280D Patch-Vektor bereits,
gibt ihn an die Klassifikationsköpfe weiter, verwirft ihn dann
aber nach der Patch-Verarbeitung. Das bestehende separate
schema-v3-Sidecar persistiert **87D-/56D-Klassifikationsscores**,
nicht 1280D Song-Embeddings. Der reguläre Source-Tree dieses Branches
und die pinned, numerisch korrigierte **Rust-v5-CLI aus PR #17**
sind zu unterscheiden: Die CI-Forschungsworkflows bauen die
immutable PR-#17-Revision
`2c3d44401436b3b41b6e067199016a1ed2335fbf`.
Vor einer Änderung **die konkrete gepinnte v5-Funktion/CLI prüfen**.
**Keine unbelegte Behauptung**, eine Embedding-Ausgabe sei in dieser
CLI schon implementiert. PR #17 nicht in #16 hineinmergen.

**Minimaler neuer Forschungsbaustein:**
- Pro Audio-Patch tatsächliche **1280 f32** des gleichen Encoders
  erfassen, ohne erneute Audio-Decodierung/zweite ONNX-Inferenz;
  beide Kopfresultate unverändert weiterberechnen.
- Ein einfaches, deterministisches **arithmetisches Patch-Mittel**
  als *vorab festgelegte Song-Repräsentation* testen; pro
  Song danach L2-Normierung für Cosine. Vorab definieren,
  wie 30-s-Exzerpte und ganze Songs behandelt werden, sowie
  Patches mit Abweichungen, Nullnormen, NaN/Inf. Mitteln vor
  oder nach Normierung, Median/trimmed mean, zeitliche
  Segmente und Whitened/PCA sind **gesonderte Ablationen**,
  keine unbemerkten Hyperparameter.
- Embeddings als **eigenständigen Capability/Feature-Typ**
  mit 1280D float32, Patchzahl, Encoder-Gewicht-SHA256,
  Preprocessing-, Pooling- und Normalisierungsversion
  persistieren. Die bisherigen Sigmoid-Prüfungen und
  Genre/Mood-`model_key`-Semantiken dürfen **nicht** für
  signierte latente Embeddings missbraucht werden. Schema v3
  und Legacy-Mood-Felder rückwärtskompatibel erhalten;
  ggf. eigene versionierte Tabelle statt riskanter Migration.
- Output gegen Original-Essentia C++/TensorFlow auf
  **identischen Patches** numerisch prüfen, nicht nur
  Genre-/Mood-Klassifikationsparität ableiten. Prüfen, dass
  zusätzliche Speicherung keine Inferenzwerte oder
  parallele Worker-Deterministik verändert.
- Zunächst **kleines festes bereits lizenziertes
  Forschungscohort**; danach denselben MTT-/FMA-/DEAM-
  Stichproben und den vorhandenen Caches wiederverwenden.
  Nichts aus privater Musikbibliothek hochladen/scannen.

**Hypothese:** Das reichhaltigere Embedding könnte allgemeine
klangliche Ähnlichkeit besser abbilden. Es könnte aber weniger
gut auf *Mood* oder Genre-semantische Gruppierung reagieren.
Das ist empirisch offen.

### C — Hybrides Feature-Ranking (Embedding + Genre + Mood)

```text
                 ┌─ 1280D Audio-Embedding → Cosine ── s_audio
Gleicher Song ───┼─ 87D Genre-Werte     → Cosine ── s_genre
                 └─ 56D Mood-Werte      → Cosine ── s_mood
                                       ↓
                          getrennte Skalierung / Kalibrierung
                                       ↓
                    explizite gewichtete Kombination
                                       ↓
                        finale Songsimilarity / Ranking
```

Ein **Beispiel, noch kein evaluiertes oder kalibriertes Modell**:
`S = w_audio*S_audio + w_genre*S_genre + w_mood*S_mood`,
mit nichtnegativen Gewichten, die zu eins summieren. Die
Cosine-Skalen der verschiedenen Signalräume haben
**unterschiedliche empirische Verteilungen**. Daher nicht
blind die nackten Werte addieren: Auf ausschließlich
**Development-Daten** vorher festlegen/kalibrieren,
z. B. anhand von Rang-/Perzentilverteilungen oder
monotoner Skalierung; Parameter/Fit-Statistiken
**ohne Testset-Leakage** einfrieren.

**Vorab definierte minimale Ablationen statt freier
optimistischer Gewichtssuche:** Nur Audio; nur Genre;
nur Mood; Audio+Genre; Audio+Mood; Genre+Mood;
alle drei mit zunächst gleichen Gewichtungen.
Danach bei ausreichender unabhängiger Ground Truth
höchstens eine kleine, dokumentierte Gewichtsuche
auf Development, klar getrennte Bestätigung.
Nicht das gesamte MTT-Korpus zur Gewichtsauswahl
verwenden und anschließend als unabhängige Bestätigung
ausweisen – alle 346 MTT-Tripel wurden bereits explorativ
gesehen. Genre-, Mood- und Audio-Similarity
müssen auf **denselben Songs und Patches** gerechnet werden.
Nahezu identische Metriken nicht überoptimieren.

**Vorteile:** Audio-Sound-Nähe mit expliziten Mood-
und Genre-Kriterien kombinierbar, steuerbar für
unterschiedliche Nutzerabsichten (Discovery,
Mood-Flow, Genre-Konsistenz). **Nachteile:** zusätzliche
Kalibrierung/Verteilungseffekte, Hyperparameter,
Risiko der Überanpassung bei kleinen Datensätzen,
höherer Speicher-/Indexaufwand, eingeschränkte
Interpretierbarkeit gegenüber Einzelköpfen.

## Verwechslungsgefahr: zwei völlig verschiedene "Hybrid"-Entscheidungen

| Ebene | Frage | Optionen |
| --- | --- | --- |
| **Feature-Repräsentation und Scorefusion** (dieses Dokument) | **Wie** werden zwei Songs verglichen? | (A) Klassifikationsvektoren, (B) Audio-Embedding, (C) Fusion |
| **Lyrion-Kandidatengewinnung / Playlist-Architektur** | **Welche Songs** kommen in die Auswahl? | **Bliss-first**, **Mood-/Genre-/Embedding-first**, **Hybrid aus Kandidatenquellen** |

Die zweite Ebene ist bereits offen dokumentiert in
[lyrion-bliss-mood-genre-integration.md](lyrion-bliss-mood-genre-integration.md)
und [feature-provider-architecture.md](feature-provider-architecture.md).
Ein hybrider Feature-Score kann **innerhalb eines Bliss-first-
Re-Rankings** verwendet werden. Ebenso kann Feature-first
nur Cosine auf Embeddings verwenden. Die zwei Dreiergruppen
sind daher **keine Synonyme und nicht zwangsläufig Alternativen**.
Bliss liefert zusätzlich sein eigenes akustisches
**23D-Feature-System** als Kontrollgruppe, nicht
automatisch als vierter Teil des 1280D-Embeddings.

## Was unsere bisherigen Benchmarks tatsächlich zeigen (A, nicht B/C)

Die bislang erfolgreich abgeschlossenen GitHub-Actions-
Benchmarks nutzen **nur A**, also die Genre-/Mood-Köpfe.
Es gibt **noch keine direkte Messung für B oder C**.

| Datensatz | Referenz/Ziel | Befund und Grenzen |
| --- | --- | --- |
| **MagnaTagATune** | Menschen wählen den musikalisch unähnlichsten von drei Clips | 346 eindeutige *ungeordnete* Triple-Fragen, davon **293** mit eindeutiger menschlicher Mehrheit; 1019 Audiodateien; Mood Cosine ca. **65,5%**, Mood Centered Cosine ca. **65,9%**, Genre beide ca. **65,2%**. Gleiche Tripel für alle Metriken; alle 346 explorativ verwendet, **kein ungesehener MTT-Holdout**. Gemeinsame Künstler/Tracks verhindern unabhängige Fragen. |
| **FMA-Small** | Genre-Retrieval (P@5 etc.), acht grobe Musikrichtungen | Original 80 Validierungs-Songs: Genre Cosine P@5 **0,3500**, Centered **0,3525**, Weighted Jaccard **0,3550**. Separate **andere** 80-Song-Validierungsstichprobe nach möglichem MTG-Katalog-Match-Ausschluss: Cosine **0,3200**, Centered **0,3225**, Weighted Jaccard **0,3000**. **Nicht gepaart, keine kausale Differenz**, offizieller TEST-Split unberührt. |
| **DEAM** | menschliche Valence/Arousal-Nähe als Mood-*Proxy*, nicht dieselbe 56-Label-Taxonomie | Gefiltertes 240-Song-Development, Mood Cosine Query-Spearman **0,2868**, Weighted Jaccard **0,2888**. Kleine Unterschiede, nicht als gleiche Einheit wie FMA-P@5 oder MTT-Accuracy behandeln. |
| **MTG-Jamendo** | Modell-/Labelprovenienz statt zusätzlichem Similarity-Goldstandard | FMA-Validation: **42 von 800** möglichen identischen normalisierten Künstler+Titel-Katalogangaben (35 Hip-Hop); kein Beweis für identische Aufnahme oder ONNX-Trainingszugehörigkeit. |

Ausführliche Einheiten, Modelle, CI-Runs und Einschränkungen:
[Cross-Dataset-Evidenz](similarity-cross-dataset-evidence-2026-10-21.md),
[MTT Paired Analysis](magnatagatune-paired-analysis-2026-10-21.md),
[FMA-MTG-Audit](fma-mtg-catalog-overlap-2026-10-21.md) und
[Genre/Mood-Metrikdokument](similarity-metric-evaluation.md).
Keine globale Rangfolge durch Mittelung verschiedener P@5-,
Spearman- oder Triplet-Accuracy-Werte erstellen.
Kein Produktionsstandard festgelegt.

## Reproduzierbarer neuer Experimentalplan (priorisiert)

1. **E1 — Architektur-Paritätsgate statt sofortigem Großbenchmark.**
   Pinned Rust-v5-CLI und den Essentia-C++-Encoder-Ausgabepunkt
   prüfen; Song-/Patch-Embeddings spezifizieren und dokumentieren.
   Minimalen Sidecar-/CLI-Zugriff auf 1280D-Features im
   Research-Branch implementieren. Feature-Schema/Fingerprints,
   Zero-Vector/NaN, Aggregation, Audio-Identität und identische
   Klassifikationswerte überprüfen. Keine Merge-Operation mit PR #17
   ohne ausdrückliche Freigabe.
2. **E2 — Gleiche Audio-Cohorts fair vergleichen.**
   Erst kleines synthetisches+reales Smoke, dann die bereits
   geprüften MagnaTagATune-Clips (114-MiB kuratierter
   1019-Clip-Actions-Cache, CRC geprüft) und weitere bereits
   zulässig bereitgestellte DEAM/FMA-*Development*-Cohorts.
   Embedding-Cosine als Baseline gegen Genre-/Mood-Cosine
   auf **identischen Clip-IDs**. MTT explizit nur explorativ.
   Bei FMA keine TEST-Titel/Audio vorab inspizieren.
3. **E3 — Fairness/Statistik.** Identische Frage- und
   Retrieval-Splits, Referenzlabels, Coverage/Abstention;
   pro Frage gepaarte Auswertung, Korrelationen durch
   gemeinsame Songs/Künstler berücksichtigen. Hypothesen
   und kleine Suchräume/Poolings vor der nächsten
   unabhängigen Testmenge einfrieren. MTT-Artistgraph
   ist ein zusammenhängender Cluster – "artist bootstrap"
   ist dort **kein valides unabhängiges CI**.
4. **E4 — Vorsichtige Fusion.** Feste einfache Gewichte,
   *Development-only* Scorekalibrierung, Leave-one-head-out,
   Kopf-spezifische Ziele separat; keine neue Metrik
   erfinden ohne evidenzbasierte Notwendigkeit.
5. **E5 — Lyrion-Gate.** Gegen Bliss-only (23D) auf
   identischer Bibliothek und Seeds testen, getrennt
   von Bliss-first/Feature-first/Hybrid-Kandidatenarchitektur.
   Playlist-Übergänge, menschliches Hören, Artist-Repeats,
   Genre/Mood-Drift, Discovery, Coverage, Peak RAM/CPU
   und Raspberry-Pi-Latenz sind relevante Qualitätskriterien.
   Ein besseres MTT-Ergebnis beweist keine bessere DSTM-Queue.

### Performance und praktische Umsetzung

- Die bisherige MTT-Forschungsautomation läuft mit
  **vier isolierten Rust-v5-Prozessen**, je einem ONNX-Thread.
  1019 Clips liegen in einem **119.689.247-Byte**
  (ca. 114 MiB) kuratierten, CRC-verifizierten
  Actions-Cache. Ein zweiter, source-commit-gepinnter
  Cache hält das korrigierte Rust-v5-Binary. Beides
  weiterverwenden, sofern die GitHub-Berechtigungen und
  die Audio-Nutzungsbedingungen das erlauben.
- Für **Embedding-Ausgabe möglichst eine Analyse**
  mit Encoder+Köpfen ausführen, nicht zweimal ffmpeg/ONNX;
  die Embedding-Persistenz braucht neuen Code,
  Messungen und Numerical-Parity-Gates. Neue Cache-Keys
  für veränderte Binärdatei-/Modell-/Schema-Fingerprints.
- Nicht automatisch das gesamte FMA-Small-Archiv oder
  private Musik cachen/hochladen; FMA-Metadatenfilter
  und Split-Sperre erhalten. GH Actions kann
  Download, isolierte Worker, Regressionen und
  Aggregate-Reports vollständig automatisieren.
- Sidecar-Songs/Vektoren, künstlerbezogene Labels
  und Roh-Audio als **private temporäre
  Forschungsdaten** behandeln. Keine Benutzermusik,
  Lyrion-Katalog-Dumps oder fremde Musik in Git
  oder öffentlich herunterladbare Build-Artifacts.
  GitHub-Actions-Caches sind **nicht vertraulich**.

## Konkreter Arbeitsauftrag für die nächste Chat-Session

**Erst den aktuellen PR-Head/CI prüfen.**
Lesen: **dieses Dokument** plus
[docs/chat-handover.md](chat-handover.md),
[docs/similarity-listening-review-handover-2026-10-21.md](similarity-listening-review-handover-2026-10-21.md),
[docs/similarity-metric-evaluation.md](similarity-metric-evaluation.md)
und [docs/lyrion-bliss-mood-genre-integration.md](lyrion-bliss-mood-genre-integration.md).

**Danach ohne weitere Grundsatzdiskussion E1 implementieren**:
Encoder-Output in der **gepinn­ten, numerisch korrigierten Rust-v5**
CLI untersuchen; so wenig neuen Code wie möglich, gleiche
ONNX-Modelle/Decoder/Patches, konsistente Metadaten und
einen schnellen CI-Smoke für 1280D-Mittelwert+Cosine
schaffen. Die drei Ansätze A/B/C sind noch
gleichberechtigte Forschungsalternativen. Erst wenn
Embedding-Parität und identische Clips verifiziert sind,
den Vergleich auf MTT/FMA/DEAM erweitern und Fusion testen.
Alle Handover-Dokumente laufend aktualisieren.

### Grenzen und Schutzregeln

- **Nur Branch feat/similarity-metric-evaluation / Draft PR #16**;
  kein Merge nach `main` ohne ausdrückliches Einverständnis;
  PR #13/PR #17 und Lyrion-Produktivmixer unangetastet.
- Keine lokalen Rust-Builds auf dem Windows-Laptop;
  CI- und Benchmark-Builds auf GitHub.
- Keine private Audio-/Lyrion-Bibliothek scannen,
  verändern, kopieren oder hochladen.
- FMA offizielles TEST unberührt bis zu vorher
  eingefrorenen Auswertungsregeln.
- Source- und Modellversionen pinnen; keine
  unbegründeten oder vorzeitig veröffentlichten
  Qualitäts-/Performancebehauptungen.
- Deutsch berichten; bei Windows-Kommandos vollständige
  PowerShell-`& { ... }`-Blöcke ausgeben.

**Verifizierbare Fremdreferenzen:**
[cosine.club FAQ](https://cosine.club/about),
[Essentia-Modellverzeichnis](https://essentia.upf.edu/models.html),
[Essentia Embedding-Tutorial](https://essentia.upf.edu/tutorial_tensorflow_auto-tagging_classification_embeddings.html).
Das sind etablierte Implementierungs-/Modellbeispiele,
keine unabhängig reproduzierte Überlegenheit von B/C
auf unseren Lyrion-Zielen.
