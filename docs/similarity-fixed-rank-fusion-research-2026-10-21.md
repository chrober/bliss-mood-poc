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

## Empirischer Nachtrag: vier Rangfusionen jetzt vollständig ausgewertet

**Erfolg:** [GitHub Actions Run 39619708040](https://github.com/chrober/bliss-mood-poc/actions/runs/39619708040)
ist **vollständig PASS**. Die bislang ausständigen
Fusionsergebnisse wurden ohne geänderte Kombinationen
mit einer wiederholten **1019-Clip-Inferenz** berechnet,
inklusive erneut PASS beim synthetischen 1280D-Patch-,
L2-, SQLite-/Klassifikations- und Thread-Paritätsgate.

**Prüfbarer [Aggregate-Artifact 12354537538](https://github.com/chrober/bliss-mood-poc/actions/runs/39619708040/artifacts/12354537538)**:
`results/mtt-audio-genre-mood-fixed-rank-fusion-exploratory.json`
(schema_version 2), inklusive vollständiger gepaarter
Sensitivität. Der v1-A/B-Bericht blieb als separate Datei erhalten.

### Identischer MTT-Mensch-Nenner

293 Fragen mit eindeutiger Mehrheit, 53 menschliche
Gleichstände. Undefinierte Vorhersage oder
kombinierter Top-Paargleichstand bleibt auf dem
gemeinsamen Nenner als **falsch**; nur dadurch ist
die Zeilen-Gegenüberstellung fair. Alle
Unterschiede nachfolgend sind rein explorativ.

| Methode | Korrekt | Vorhergesagt | Abstention durch Gleichstand | Coverage | Genauigkeit 293er Nenner |
| --- | ---: | ---: | ---: | ---: | ---: |
| Direkte Audio-Embedding Cosine | 182 | 293 | 0 | 100,00 % | 62,116 % |
| Genre Cosine | 191 | 293 | 0 | 100,00 % | 65,188 % |
| Mood Cosine | 192 | 293 | 0 | 100,00 % | 65,529 % |
| Mood Centered Cosine | 193 | 293 | 0 | 100,00 % | **65,870 %** |
| Fix Audio+Genre, Midrank 50:50 | 163 | 234 | 59 | 79,86 % | 55,631 % |
| Fix Audio+Mood, Midrank 50:50 | 170 | 241 | 52 | 82,25 % | 58,020 % |
| Fix Genre+Mood, Midrank 50:50 | 167 | 230 | 63 | 78,50 % | 56,997 % |
| Fix Audio+Genre+Mood, Midrank 1:1:1 | 192 | 283 | 10 | 96,59 % | 65,529 % |

**Interpretation:** Die beiden gleichgewichteten Rang-
Eingänge können widersprechen, sodass ein gemeinsamer
Spitzenrang bei exakt drei Paaren öfter gleich ist.
Das erhöht die Abstentionsrate der Zweierkombinationen
auf **52–63 der 293** menschenentscheidbaren Fragen.
Eine bedingt auf vorhergesagte Fragen berechnete
hohe Quote darf deshalb **nicht** als Produktivvorteil
berichtet werden. Die Dreierkombination reduziert
die Gleichstände auf 10, verbessert den gesamten
293er-Score aber nicht über den reinen Mood-Kopf:
`192/293` statt `193/293` beim Mood Centered Cosine.

**Paarvergleich Dreierfusion minus Mood Centered:**
20 Fragen nur durch Dreierfusion korrekt,
21 nur durch Mood Centered korrekt;
Differenz **−0,341 Prozentpunkte**;
naiver gepaarter 95-%-Bootstrap-
Sensitivitätsbereich **−4,437 bis +3,754 pp**.
Dies ist **kein statistischer Test auf unabhängige
Generalisierung**; Frage- und Künstlerabhängigkeiten,
post-hoc Methodenentwicklung und mögliche
Trainingskatalog-Überlappung verbieten diese Aussage.

**Fazit für diese exakt fixierte Ablation:**
Keine der vier einfachen Rangfusionen schlägt
Mood Centered Cosine auf dem gemeinsamen Nenner.
Das ist **keine allgemeine Widerlegung** von
Feature-/Embedding-Fusionen oder von
auf Entwicklungskohorten kalibrierten
globalen Fusionsmodellen. Die
dreiergruppen-lokale Midrank-Methode hat zudem
keinen unmittelbar produktionsfähigen
Song-zu-Song-Score. Keine Gewichtoptimierung
an den bereits untersuchten MTT-Fragen.

**Noch offen:** separate unabhängige
Song- und Übergangsreferenzen,
Entwicklungs-/Testtrennung, global vergleichbare
Scorekalibrierung, separate klang-/genre-/mood-
spezifische Aufgaben sowie kontrastive Encoder.
FMA offizieller TEST bleibt unberührt,
PR #16 Draft, kein Mixer-/PR17-/main-Merge.
