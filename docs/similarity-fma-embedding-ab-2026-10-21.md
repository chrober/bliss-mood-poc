# FMA-Small 80-Song VALIDATION: gepaarter 1280D-vs-Genre/Mood-Transfer

**Datum:** 2026-10-21. **PR:** #16 (Draft); ausschließlich
`feat/similarity-metric-evaluation`. Keine Änderungen an PR #13/#17,
`main` oder Lyrion-Produktivmixer.

## Zweck

Reproduzierbarer **gleiche-Songs-/gleiche-Kandidaten**-Vergleich
zwischen direkten Discogs-EffNet-Embeddings (B) und
Genre-/Mood-Klassifikationsvektoren (A). Die vorherige vollständige
MagnaTagATune-Evaluation hatte für direkte 1280D-Cosine 182/293 =
62,12 % und für Mood Centered Cosine 193/293 = 65,87 % ergeben.
**FMA validiert einen *anderen* Proxy:** Retrieval von Titeln
derselben groben 8-Klassen-Genrezuordnung, keine menschlichen
Klangähnlichkeits-/Playlist-Urteile. Ein A/B-Sieg für eine
Repräsentation auf FMA bedeutet keinen universellen Gewinner.

## Kohorten-Fingerprint und Provenienz

Verwendet exakt die frühere, bereits ausgewertete
katalogbereinigte VALIDATION-Stichprobe aus
[Run 39606850307](https://github.com/chrober/bliss-mood-poc/actions/runs/39606850307):

| Festgelegter Wert | Provenienz |
| --- | --- |
| FMA offizieller Split | `validation`; TEST-Zeilen werden vor dem Lesen ihrer ID oder Labels übersprungen |
| Anzahl | 80 Songs, 10 aus jeder der 8 Obergenres |
| Künstler | 80 unterschiedliche Künstler-IDs |
| MTG-Abgleich | 42 mögliche exakte Artist/Title-Überschneidungen von 800 VALIDATION-Titeln ausgeschlossen |
| Noch eligible | 758 VALIDATION-Titel vor Sampling |
| Sampling | `seed=20261021`, unveränderte `balanced_sample`-Implementierung |
| Sample-SHA256 (geordnete IDs, nur Fingerprint publiziert) | `f4a7a81c0713db7619efdba6eb3d561aa70d6d3cc812b4884793953d93b58509` |
| FMA-Metadaten-ZIP SHA256 | `d9527a5297a65da31c5676484d5047c3e2b8a8060ce72a46e26158be736bf265` |
| Offizielles FMA-Small-Audio-ZIP SHA256 | `f923bbef327820456d50965c3c320c3c7b6dab8456449429fd78f7ec96a5d02c` |
| MTG-Metadaten-TSV SHA256 | `bb1efa2876536cbe1a8b67db5dda15249ca144f0cff69e481b638803cbdc9aca` |

**Screening ist nur eine vorsichtige Katalogüberlappungsdiagnose,
kein Beweis für die Trainings-Unabhängigkeit des Encoders
oder der Klassifikationsköpfe.**

Der frühere Genre-Cosine-Lauf lieferte auf genau diesem
Sample P@5 **0,3200**, mAP@10 **0,1748759921**, nDCG@10
**0,2985332322**. Diese **vor dem neuen Embedding-A/B
fixierten** Werte sind ein striktes Regression-Gate:
andere Audiosegmente, andere Samples, andere Kopf-Modelle oder
verschobene Klassifikationswerte sollen nicht still verglichen werden.

## Implementierung und Datenpfad

- [`scripts/benchmark_fma_genre.py`](../scripts/benchmark_fma_genre.py)
  besitzt einen optionalen Forschungsmodus
  `--embedding-dir <privates-verzeichnis>`; ohne Flag bleiben
  die bisherigen sieben Genre-Similarity-Metriken und
  ausschließlich der Genre-Kopf unverändert.
- Mit Flag werden **im selben Encoder-Patchdurchlauf**
  Genre 87D, Mood/Theme 56D und das rohe 1280D-EffNet-
  Song-Embedding berechnet. Die Klassifikationsköpfe
  bleiben voneinander und vom separaten L2-normierten
  Embedding-Sidecar getrennt. Alle Audio-/Track-Hashes,
  Patchzahlen, Encoder-Hashes und
  Repräsentations-Fingerprints werden vom unabhängigen
  [Evaluator](../scripts/evaluate_fma_embedding_ab.py)
  auf Gleichheit geprüft.
- Das separate Forschungs-Overlay
  [`scripts/apply_rust_v5_embedding_export.py`](../scripts/apply_rust_v5_embedding_export.py)
  wird ausschließlich auf den unveränderten temporären
  Runner-Checkout von
  `2c3d44401436b3b41b6e067199016a1ed2335fbf`
  angewendet. Weder der ursprüngliche Feature-Sidecar-
  Vertrag (schema v3) noch PR #17 werden umgebaut.
- [`research-fma-embedding-ab.yml`](../.github/workflows/research-fma-embedding-ab.yml)
  lädt einmal das offizielle FMA-Small-ZIP (7,2 GiB)
  und *extrahiert nicht das gesamte Archiv*.
  Es verwendet Rust/Cargo-Caching und Stage-Timing.
  Keine Veröffentlichung des vollständigen Archivs
  oder unlizenzierter Track/Embedding-Daten;
  Artefakte enthalten nur aggregierte Kennzahlen.
  Im Gegensatz zu MTT wurde **kein global wiederherstellbarer
  FMA-Audio-Cache eingeführt** (Audio-Lizenz/Aufbewahrung
  muss vor einem geteilten CI-Cache abgeklärt werden).

## Mathematischer Vergleich auf identischen Songs

Für jeden der 80 Query-Songs werden genau die übrigen
79 Künstler-fremden Songs als Kandidaten verwendet:
9 relevante (gleiche Obergenreklasse) und
70 andere Genres; Random-Referenz für P@5 ist
`9/79 = 11,39 %`.

Repräsentation/Metrik:

1. Direkte 1280D-Discogs-EffNet-Song-Embeddings, Cosine;
   rohe Patchvektoren f64-gemittelt, anschließend
   songweise L2-normalisiert.
2. 87D Genre-Sigmoidwerte, Cosine und Centered Cosine.
3. 56D Mood/Theme-Sigmoidwerte, Cosine und Centered Cosine
   als **sekundäre Kontroll-/Cross-Task-Baseline**,
   nicht als echte Mood-Ground-Truth.

Jede Methode liefert **P@5, mAP@10, nDCG@10**,
Abdeckung und undefinierte Kandidatenbewertungen.
Tie-Break entspricht exakt der bisherigen FMA-Retrieval-
Implementierung (Score absteigend, danach stabile interne
Track-ID; IDs verlassen den Runner nicht). Kann eine Methode
nicht alle Kandidaten eines Query-Songs bewerten, wird
**die ganze Query als Abstention** mit `0` für
alle drei Maße auf dem gemeinsamen 80er-Nenner gezählt.
Keine bedingt auf Vorhersageabdeckung verkürzten
Stichprobenvergleiche.

Für **Embedding minus jede Kopfmethode** verwendet
der Evaluator dieselben deterministisch gezogenen
genre-stratifizierten Query-Resamples (800 Wiederholungen,
gleicher Seed). Die Quantile sind **Abhängigkeits-
Sensitivitätsmaße, keine Konfidenzintervalle für
independent/out-of-corpus Generalisierung**, weil
alle Query-Songs die Kandidaten teilen und das Genre-
Signal grob ist. Keine p-Werte, keine nicht
vorregistrierten Fusion-Gewichte.

## Technische Gates und nächster Schritt

[`tests/test_evaluate_fma_embedding_ab.py`](../tests/test_evaluate_fma_embedding_ab.py)
enthält nur synthetische Fixtures. Sie prüfen:
v3-SQLite-Read-only, gleiches Kandidatenuniversum
und gleiche Query-Nenner, 1280D-L2/Audio-/Encoder-
Provenienz, Ausschluss von TEST, Kohorten-SHA,
Paar-Resampling, Nullnorm-Abstentions und
Option-Disabled-Baseline. Ausführung im
bestehenden Linux-/Windows-Python-CI.

**Workflow:** [FMA-80-A/B-Actions](https://github.com/chrober/bliss-mood-poc/actions/workflows/research-fma-embedding-ab.yml).
Den Result-Status nach dem Workflowdurchlauf
bewerten, nur bei vollständigem PASS numerische
EffNet-vs-Genre-Resultate als gemessene Evidenz
dokumentieren. Anschließend DEAM
Valence/Arousal auf identischen Audioclips
und Modell-Fingerprints gegen Mood/Embedding
vergleichbar auswerten; den offiziellen
FMA-TEST nicht zum Optimieren benutzen.

**C-Fusion bleibt vorerst gesperrt:** Die
bereits vollständig explorierten MTT-Fragen
und die FMA-VALIDATION-Genreaufgabe sind keine
unabhängigen Optimierungs- und Prüfsets für
Fusion-Gewichte oder Produktionsentscheidungen.

## Verifizierter Endstand – erfolgreicher gepaarter FMA-80-Lauf

**PASS:** [Research FMA 80 A/B, Run 39625087310](https://github.com/chrober/bliss-mood-poc/actions/runs/39625087310)
([nur aggregiertes Artefakt 12355954718](https://github.com/chrober/bliss-mood-poc/actions/runs/39625087310/artifacts/12355954718)).
Dieser Nachtrag ersetzt den vorherigen `noch zu prüfen`-Status
des Workflows. Gesonderte Linux-/Windows-Python-Regressionstests waren
zuvor ebenfalls PASS; Rust-Pooling-Unit-Tests und unverändertes
gepinntes Runner-Overlay waren in diesem Lauf grün.

**Alle 80 identischen Songs, alle 79 identischen
Kandidaten pro Query, alle fünf Verfahren mit 80/80 =
100 % Abdeckung.** Nur die eingefrorene FMA-VALIDATION
wurde gelesen; der offizielle TEST blieb gesperrt.
Das frühere Genre-Cosine-Baseline-Tripel wurde **exakt**
reproduziert: P@5 `0.32000000`, mAP@10
`0.17487599206349208`, nDCG@10
`0.29853323224865014`. Der Cohort-Fingerprint
ist unverändert
`f4a7a81c0713db7619efdba6eb3d561aa70d6d3cc812b4884793953d93b58509`.
Der verwendete originale Encoder
`discogs-effnet-bsdynamic-1.onnx` hatte SHA256
`a280825b334797cf677939db8cd5762c0392aedd0ca6415dbc1cd083f045e43c`;
Pooling- und Preprocessing-Repräsentationsfingerprint:
`48d6726d346b49aaf9f6d0377778ce0bf46be52285293e2f357ad26832cbc759`.

| Repräsentation und metrische Similarity | P@5 | mAP@10 | nDCG@10 | Query coverage |
| --- | ---: | ---: | ---: | ---: |
| B: 1280D Encoder Song-Mean+L2, Cosine | 0,2800 | 0,163044 | 0,282363 | 80/80 |
| A: Genre 87D, Cosine | 0,3200 | 0,174876 | 0,298533 | 80/80 |
| A: Genre 87D, Centered Cosine | **0,3225** | **0,178147** | **0,304271** | 80/80 |
| A: Mood/Theme 56D, Cosine | 0,2775 | 0,150394 | 0,266065 | 80/80 |
| A: Mood/Theme 56D, Centered Cosine | 0,2675 | 0,152847 | 0,270372 | 80/80 |

Random P@5 = `9/79 ≈ 0,1139`.

### Gepaarte Query-Unsicherheit, korrekt interpretiert

Die Differenzen sind **Embedding minus jeweilige
Klassifikationsbaseline**; die folgenden 95-%-Quantile
entstammen 800 geteilten *genrestratifizierten*
Query-Resamples der **identischen 80 Queries**.
Es sind **nur explorative Sensitivitätsbereiche,
keine unabhängig gültigen Konfidenzintervalle**
(gemeinsame Kandidaten, lediglich 8 Obergenres,
bereits untersuchte Entwicklungsstichprobe,
unsichere Encoder-Trainingsüberlappung).

| Embedding − Kopf-Baseline | Differenz P@5 (pp) | 95-%-Sensitivität P@5 (pp) | Differenz mAP@10 (pp) | Differenz nDCG@10 (pp) |
| --- | ---: | ---: | ---: | ---: |
| Genre Cosine | −4,00 | −8,75 bis +0,75 | −1,183 | −1,617 |
| Genre Centered Cosine | −4,25 | −8,76 bis +0,25 | −1,510 | −2,191 |
| Mood Cosine | +0,25 | −3,50 bis +4,01 | +1,265 | +1,630 |
| Mood Centered Cosine | +1,25 | −2,50 bis +5,00 | +1,020 | +1,199 |

Entscheidungsrelevant ist vor allem die
**Genre-gegen-Embedding**-Zeile: Direkte
EffNet-Embeddings verlieren auf diesem **Genre-Proxy**
in der beobachteten Stichprobe 4,00–4,25 pp P@5
gegenüber den passenden Genre-Köpfen. Die
Sensitivitätsbereiche schließen `0` ein.
Mood-Köpfe werden hier nur als
**Cross-Task-Kontrolle**, nicht als unabhängige
Mood-Ähnlichkeitsreferenz bewertet.

### Reproduzierbarkeit, Durchlaufzeiten, nächste Forschung

Messwerte aus diesem erfolgreichen Workflow:
originales FMA-7,2-GiB-Audio-ZIP **243,87 s**
Download, Rust-v5-Releasekompilierung **51,48 s**
(noch ohne vorherige Rust-Unit-Test-Kompilierungszeit),
Inference+ursprüngliche Auswertung der 80 Clips
**48,37 s**, gepaarter Evaluator samt
Archivquellen-SHA256 **12,63 s**. Das
Audioarchiv war der dominante Kostentreiber;
es wird bewusst **nicht** in einem anderen Branches
zugänglichen unkontrollierten Audio-Cache geteilt.
Die Ausgabe enthält **keine** Audio-Dateien,
Clip-IDs, Tracklabels oder Embeddingvektoren.

### Forschungsschlussfolgerung

FMA Genre-Retrieval und die zuvor vollständig
explorierte MagnaTagATune-Menschentripelaufgabe
zeigen **beide im betrachteten Setting keinen
Sieg der direkten 1280D-Cosine** über die
aufgabenpassenden Klassifikationsvektoren.
Das ist **keine Widerlegung** direkter Embeddings:
andere Encoder, insbesondere separat
kontrastiv auf Similarity optimierte Modelle,
andere Poolingvarianten und andere
menschenbasierte Klangnähe-/Übergangsreferenzen
bleiben ungetestet. Aus FMA VALIDATION
darf keine Produktions- oder Fusion-
Gewichtwahl getroffen werden.

**Nächstes Evidenzziel:** DEAM Development/Validation
auf denselben Audiodateien, Valence/Arousal
als unabhängiger, aber nicht identischer
Mood-Proxy; die Klassifikations- und
Embedding-Dimensionen wieder gepaart und
mit exakt gleichen Provenienz-/Coverage-
Regeln. Neue echte Hörreferenzen wären für
Klangnähe/Playlist-Übergänge weiterhin
aussagekräftiger.
