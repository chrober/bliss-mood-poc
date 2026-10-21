# Explorative C-Ablation: festgewichtete Rangfusion (21.10.2026)

**Status:** Auf PR #16 **implementiert**, [Actions-Lauf der vier
vordefinierten Kombinationen](https://github.com/chrober/bliss-mood-poc/actions/runs/39619708040)
wurde eingereicht; **hier noch keine bestätigten Resultate
oder Gewichtoptimierung**. Baseline B und A sind bereits
[auf MagnaTagATune gemessen](similarity-audio-embedding-ab-results-2026-10-21.md).

## Wissenschaftliche Motivation

Direkte Audio-Embedding-Cosine, Genre-Cosine und Mood-Cosine
liegen in unterschiedlich skalierten Score-Verteilungen.
Eine naive Addition ihrer Rohwerte mit denselben Gewichtzahlen
wäre deshalb schlecht interpretierbar.
Als **erster ausdrücklich nur dreiergruppen-lokaler Vergleich**
wandeln wir jede Repräsentation in einheitliche **Ränge**
um. Das spart jede Label-basierte Kalibrierung und eliminiert
Scale- und Offset-Effekte innerhalb einer Tripelfrage.

Diese Wahl ergibt **keine universelle, songübergreifende
Similarity-Funktion**. Ranking innerhalb der drei Kandidatenpaare
ist transduktiv und von den verfügbaren drei Songs abhängig.
Sie darf nicht als sofort einsetzbare Retrieval-/Lyrion-Metrik
ausgegeben werden. Ein globaler Score benötigt einen
separaten Verteilungs-Kalibrierungsplan auf Entwicklungsdaten.

## Exakter algorithmischer Vertrag

Für drei Clips `a,b,c` und Paarfolge
`((a,b),(a,c),(b,c))`:

1. Jede Repräsentation `h` berechnet drei
   `s_h(i,j) = cosine(v_h(i), v_h(j))`.
   Die Vektoren stammen aus **demselben, hashgeprüften**
   1019er-Audioclipdurchlauf.
2. Die drei Score-Werte werden **nur innerhalb dieser
   Frage** in Midranks überführt: niedrigstes Paar
   `0`, mittleres `0,5`, höchstes `1`.
   Bei Score-Gleichheit innerhalb `1e-12` wird
   der Mittelrang zugeteilt, ohne willkürlich
   eine Paarposition zu bevorzugen.
3. Für eine vorab festgelegte Headmenge `H` gilt
   `R(i,j) = (1 / |H|) * sum(h in H) rank_h(i,j)`.
   Die **höchste einzelne** kombinierte Paarwertung
   benennt das ähnlichste Paar; dessen übriger
   dritter Clip ist die Odd-One-Out-Vorhersage.
   Gleichstand oder undefinierbare Kopfscore-Inputs
   bedeuten **Abstention**, im gemeinsamen Nenner
   als Fehlentscheidung gezählt.

### Vorab fixierte Kombinationen

| Methoden-ID | Enthaltene Cosine-Bereiche |
| --- | --- |
| `rank_audio_genre_equal` | 1280D Encoder + 87D Genre |
| `rank_audio_mood_equal` | 1280D Encoder + 56D Mood |
| `rank_genre_mood_equal` | 87D Genre + 56D Mood |
| `rank_audio_genre_mood_equal` | alle drei |

Alle eingeschlossenen Repräsentationen haben Gewicht
`1/|H|` – **keine Daten-, Klassen- oder
Zielgrößen-optimierten Gewichte**. Der Namen-Satz,
die Verknüpfungsregeln und die Skala sind im
[`fixed_rank_fusion.py`](../scripts/fixed_rank_fusion.py)
konstant kodiert. Die [Offline-Tests](../tests/test_fixed_rank_fusion.py)
decken normale Entscheidungen, Invarianz gegen
positives Reskalieren von Featurevektoren, Ties,
NaN und Nullnorm ab.

## Evaluation, Datenschutz, Statistik

Ein optionales, standardmäßig **deaktiviertes** Flag
`--fixed-rank-fusions` in
[`evaluate_mtt_embedding_ab.py`](../scripts/evaluate_mtt_embedding_ab.py)
erzeugt einen separaten Bericht (schema_version 2)
mit den vier Fusionen **plus den ursprünglichen fünf
unveränderten Baselines**.

Es bleiben exakt 346 MTT-Menschenfragen, davon
293 eindeutig mehrheitlich bewertbar,
und ein gemeinsamer Nenner über alle neun Methoden.
Die vier Fusions-Methoden wurden nach dem ersten
A/B-Befund konzipiert, sind also **post hoc
explorativ**, kein vorspezifiziertes unabhängiges
Experiment. Sämtliche Clips und Features bleiben
runner-privat, nur Aggregate gehen in Actions-Artefakte.

Paarvergleich und Resampling kommen aus
[`mtt_paired_evidence.py`](../scripts/mtt_paired_evidence.py).
Da die Song-/Artist-Verflechtung keine unabhängigen
Cluster zulässt, sind diese Intervalle
**Sensitivitätskennzahlen**, keine
generalisierbaren 95-%-Konfidenzintervalle.

**Verbotene Folgerungen:** Eine günstigere Quote einer
Fusion bedeutet weder statistisch belastbare
Out-of-Corpus-Verbesserung noch eine richtige
Gewichtwahl für Playlist-Übergänge. Keine
Fusion-Produktionsentscheidung ohne neue, saubere
Entwicklungs-/Testtrennung; FMA offizieller TEST
bleibt unangetastet.

## Anwendungsspezifische Forschungsfragen

- **Klangnähe:** 1280D-Encodergewicht isoliert
  auf zukünftigen Audio-Hörreferenzen überprüfen;
  ein eigenes kontrastives Embedding als weitere
  Modellklasse prüfen.
- **Genre-Nähe:** separat FMA VALIDATION
  (Katalogüberschneidungen beachten).
- **Mood-Nähe:** DEAM V/A ist nur ein Proxy;
  Mood-Clustering/Playlist-Übergänge sind zusätzliche
  menschliche Referenzaufgaben.
- **Playlist-Übergänge:** gegebenenfalls gerichtete,
  zeitliche Sequenz-Hörstudie statt Odd-One-Out;
  nicht mit Bliss-first/Feature-first/Hybrid-
  Produkt-Mixing-Strategien verwechseln.

**Operatives Vorgehen:** zuerst das
neue Fusion-Actions-Gate und seine Paarkohorten-
Metadaten auf PASS prüfen, anschließend
den Forschungsbefund dokumentieren. Keine
Kalibrierung anhand der explorativen Ergebnisse.
