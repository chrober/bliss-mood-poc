# DEAM 240: 1280D-Embedding versus 87D-/56D-Head-Vektoren

**Stand 21.10.2026**, nur Draft PR #16
(`feat/similarity-metric-evaluation`); keine Änderungen
an `main`, PR #13, PR #17 oder dem Produktivmixer.

## Forschungshypothese

Direkte 1280D-Discogs-EffNet-Cosine-Repräsentation
gegen die Klassifikationsköpfe **auf denselben
DEAM-Songs** und denselben menschlichen
Song-Level-Valence/Arousal-Anmerkungen vergleichen.
Ein höherer Zusammenhang mit VA-Nähe bedeutet
*emotionale Ähnlichkeit in dieser Operationalisierung*,
nicht gute Lyrion-Playlist-Übergänge oder unabhängige
menschlich wahrgenommene Klangähnlichkeit.

### Eingefrorene Kohorte – früherer experimenteller Lauf

Vor neuer Embedding-Evaluation vorhandene
[DEAM filtered-240 Run 39579552118](https://github.com/chrober/bliss-mood-poc/actions/runs/39579552118),
aggregiertes [Referenzartefakt 12335578980](https://github.com/chrober/bliss-mood-poc/actions/runs/39579552118/artifacts/12335578980).

- `seed=20261021`, 240 Songs; 197 ältere Excerpts, 43 Full Songs (2015).
- 75 mögliche Artist-/Track-Titel-Überschneidungen mit
  MTG-Jamendo-Metadaten entfernt; 1727 eligible Audiodateien.
  Das ist **kein Nachweis für unabhängige Trainingssamples**.
- Verbindlicher Kohorten-SHA256
  `db12c5d2692285638a4c25af442f29fd75391eb86cd7f1ea88d2f565d12630d0`.
- Original DEAM-Audio-ZIP SHA256
  `e2814325f573ade8caebc697f0efcfdf7207142b737d72558a416117ca591353`.
  Annotationen
  `809b0feb4ba6196c1eda9b2b7b33b892b11fa71457cfceb0d47e832ed1a5f15f`,
  DEAM-Katalog
  `3d1d5ab42e852803a770f2cfbd685c6b464e1ebe76f26b0e10954597902b90f8`;
  MTG `bb1efa2876536cbe1a8b67db5dda15249ca144f0cff69e481b638803cbdc9aca`.
- Vor Embedding-Einführung fixierte Mood-Cosine-Referenz
  mittlere Query-Spearman VA (gemeinsame Kandidaten):
  **0,286784551387186**, Valence **0,16424605171402107**,
  Arousal **0,2726358463243648**.
  Nur innerhalb älterer Ausschnitte VA
  **0,3399893505844028**, innerhalb 2015 Full Songs
  **0,18759773195542612**.
  Referenzen je Achse und Subkohorte sind im Evaluator
  vorregistriert. Ein Baseline-Mismatch lässt CI **FAIL**
  laufen; keine Neuetikettierung.

## Technische Umsetzung

- [`scripts/benchmark_deam.py`](../scripts/benchmark_deam.py):
  optional `--embedding-dir`, **nur** bei
  240 Songs, katalogbereinigtem `--stratify-cohorts`
  und `seed=20261021`.
  Ohne Flag bleibt die alte, bereits verwendete
  DEAM-Benchmark-Pipeline unverändert.
  Mit Flag produziert **derselbe Encoder-Patchlauf**
  beide ONNX-Köpfe plus getrenntes raw-patchmean,
  songweise L2-normiertes 1280D-Sidecar.
- [`scripts/evaluate_deam_embedding_ab.py`](../scripts/evaluate_deam_embedding_ab.py)
  prüft SQLite-v3-Genre/Mood-Patches, Audio-SHA256,
  Song/Encoder-Fingerprint, validiertes
  Embedding-Protokoll und SHA des Ursprungsaudios.
  Pro Song identische **239 Kandidaten**;
  innerhalb früherer bzw. 2015-Kohorte
  auch eigene Rankings über **196** bzw.
  **42 Kandidaten** (nicht mit Gesamtkohorte
  verwechseln).
- Methoden: 1280D Cosine; Mood 56D
  Cosine und Centered Cosine; Genre 87D
  Cosine und Centered Cosine als Cross-Task-Kontrolle.
- Human VA-Proximity der Songs wird als
  `−|ΔValence|`, `−|ΔArousal|` und
  `−sqrt(ΔValence²+ΔArousal²)` gemessen;
  für jede Query die **Spearman-Rangkorrelation**
  zwischen Human-Proximity-Ranking und
  Similarity-Ranking. Berichtet je Achse
  den über **alle** Queries gemittelten Spearman.
- Sobald eine Methode eine Query nicht auf
  *allen* gemeinsamen Kandidaten bewerten kann,
  Abstention für gesamte Query; fehlende
  Vorhersage geht als **0** in die
  240er-Makromittelung ein. Query-Abdeckung
  separat publiziert; keine unbekannten
  oder Null-Score-Fallback-Nachbarn erfinden.
- Delta-Messung **Embedding minus jeweilige
  Head-Methode** auf identischen Songqueries.
  Gleiche deterministic resamples für alle
  Verfahren, nach ursprünglichem DEAM-
  Sammlungsprotokoll 197/43 stratifiziert
  (800 ganze Kohorte, 400 bei Subkohorte).
  Die 95%-Quantile sind wegen gemeinsamen
  Kandidaten **beschreibende Sensitivitätsbereiche,
  keine unabhängigen Populations-CIs**.
- [`research-deam-embedding-ab.yml`](../.github/workflows/research-deam-embedding-ab.yml)
  lädt nur offizielle Quellen auf einen ephemeral
  GH-Runner, baut das gepinnte
  `2c3d444...`-Rust-v5 mit dem
  **separaten 1280D-Research-Overlay**;
  exportiert nur aggregierte JSON-Reports.
  Keine DEAM-Audiodateien, einzelnen Labelzeilen
  oder 1280D-Songvektoren ins Repo oder in
  Actions-Artefakte; diese DEAM-Dateien dürfen
  nur nichtkommerziell gemäß dem ursprünglichen
  Lizenztext genutzt werden.
- Synthetischer Regressionstest
  [`tests/test_evaluate_deam_embedding_ab.py`](../tests/test_evaluate_deam_embedding_ab.py)
  läuft unter Linux und Windows.

Workflow: [DEAM paired-240 Research Actions](https://github.com/chrober/bliss-mood-poc/actions/workflows/research-deam-embedding-ab.yml).
**Keine A/B-Zahlen behaupten, bis ein vollständig
grüner echter Daten-Workflow einschließlich
aller Provenienz-Gates abgeschlossen ist.**

## Lyrion: getrennte lokale Hörtest-Stufe

Weder DEAM-VA noch FMA-Genre oder MTT-Odd-One-Out
ist ein direkter Test, ob Übergänge in **der eigenen
Bibliothek** als ähnlich bzw. passend empfunden werden.
Nach DEAM einen *eigenständigen*, menschlich
beurteilten lokalen A/B-Test durchführen.

Designvorschlag:

1. Auf einer **fest eingefrorenen** lokalen,
   vielfältigen Teilstichprobe von z.B. 150–300
   Musikstücken beide Köpfe und 1280D
   aus derselben korrigierten CLI/ONNX-Version
   erzeugen; keine lokale Rust-Kompilierung
   erzwingen, bevorzugt verifiziertes GH-Binary.
2. Einmalig vorher definierte 24–40
   Anchor-/Alternative-A-/Alternative-B-Trios:
   A und B aus **demselben zulässigen Pool**,
   besonders dort, wo Ranking durch rohe
   Embeddings bzw. Mood-/Genre-Metrik stark
   auseinanderläuft. Zufalls- und Kontrollpaare,
   unterschiedliche Künstler, Genres,
   Jahrzehnte/Qualitäten; identische
   Kandidatenrestriktionen und genügend
   Coverage. Kein Test auf privaten Daten in CI.
3. Seiten A/B und Methoden **verblindet**
   und ausbalanciert präsentieren. Hörer
   bevorzugt Alternative A, B oder
   „gleich/keine passt“ für (a) wahrgenommene
   Klang-/Stimmungsnähe und (b) reale
   Playlist-Übergangsqualität **getrennt**.
   Gelegentliche blinde Wiederholungen für
   Antwortstabilität, klare Evidenz bei
   großen Methodendisagreements.
4. Die bestehende
   [`queue_similarity_pairs_lyrion.ps1`](../scripts/queue_similarity_pairs_lyrion.ps1)
   bleibt zunächst **Dry-run** und wird für
   echte Queue-Aktionen nur explizit lokal
   freigeschaltet; keine Produktionsteuerung
   über GitHub. Persönliche Dateipfade,
   IP-Adressen, Spieler-ID und vollständige
   lokale Sidecars **nie committen**.
5. Nur anonymisierte Aggregationen und
   gepaarte Präferenzzählungen auswerten,
   Abstentions/Ties nicht verstecken,
   Genre und Mood als Fragen getrennt,
   mit blinden Nachtests und möglichst
   neuer Session/personenunabhängiger
   unabhängiger Stichprobe. Kein
   vorheriges Anpassen und nachträgliches
   Testen auf derselben Hörteststichprobe.

**Interpretationsbarriere:** A/B/C ist die
*Feature-Repräsentation* bzw. metrische Fusion.
Davon unabhängig bleibt das Lyrion-Mix-Design
Bliss-first / Mood-first / Hybrid. Zuerst
bloße Similarity-Rankings **außerhalb
des Produktivmixers** vergleichen; eine
neue Candidate-Gating-/Queue-Strategie
ist eine spätere isolierte Frage.
