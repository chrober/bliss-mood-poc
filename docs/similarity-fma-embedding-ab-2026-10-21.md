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
