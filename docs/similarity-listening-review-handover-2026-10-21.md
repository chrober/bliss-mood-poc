# Handover – Genre/Mood-Similarity-Hörtest auf korrigierten Rust-v5-Daten

**Stand:** 21. Oktober 2026, Europe/Vienna.  
**Repository:** [chrober/bliss-mood-poc](https://github.com/chrober/bliss-mood-poc)  
**Aktiver Branch:** `feat/similarity-metric-evaluation`  
**Aktiver PR:** [#16 – Evaluate Genre and Mood similarity metrics on real feature sidecars](https://github.com/chrober/bliss-mood-poc/pull/16), **Draft, nicht gemergt**.  
**Referenz-Head beim Erstellen dieses Handovers:** `b5827a6b30c07c874f1570b2e8d9e6a7e1e9f12b`; GitHub beim Fortsetzen auf den dann aktuellen Stand prüfen.

## ZUERST LESEN: Konkreter nächster Schritt – auf den Benutzer warten

**STOPP / WAITING FOR USER.** Der Benutzer hört *jetzt* die ersten **acht Songpaare**
an und trägt seine **eigenen, unabhängigen** Bewertungen in
`genre_label` und `mood_label` der lokalen CSV ein. Er will die Arbeit
erst dann in einer neuen Chat-Session fortsetzen, wenn er **seine
CSV-Analyse, die ausgefüllte CSV oder die Ausgabe des darauf basierenden
Evaluators** liefert.

Die neue Session soll **als erste Aktion nur den Stand bestätigen und
die Ankunft dieser Auswertung abwarten**. Insbesondere bis dahin:

- **Nicht** sofort GitHub-Code ändern, weitere Hörpaare generieren, Songs
  rescannen, die Queue neu befüllen, Metriken wählen oder neue
  Label-Auswertungen mit erfundenen/automatischen Urteilen starten.
- **Nicht** die alte 15-Titel-Queue erneut anhängen: Der frühere
  `playlistcontrol`-Fehler trat *nach* einer tatsächlich ausgeführten
  Queue-Mutation auf.
- **Nicht** den privaten `selection-audit-private.json` während der
  menschlichen Bewertung öffnen/analysieren: Scores und
  Auswahlkategorien könnten die Hörurteile beeinflussen.
- **Keine Background-/Monitoring-Aufgabe** einrichten und keinen
  automatischen späteren Arbeitsabschluss versprechen.

Erst **nach Eingang der echten Bewertungen oder Auswertung**:
Validität/Labelabdeckung kontrollieren; bei Vorliegen der ausgefüllten
CSV gezielt den bestehenden read-only Evaluator verwenden bzw. dem
Benutzer einen vollständigen PowerShell-Aufruf geben; separate
Genre-/Mood-Zahlen interpretieren. Ist nur eine Konsolentabelle
verfügbar, diese zunächst interpretieren, ohne eine CSV zu behaupten.

## Warum wir das machen

Das Lyrion/Bliss-Projekt entwickelt eine **musikalisch sinnvolle
Similarity-Rangfolge** aus experimentellen ONNX Genre- und Mood/Theme
Feature-Vektoren, getrennt für beide Heads. Zu untersuchende Verfahren:

1. RMS-basierte Ähnlichkeit (Baseline).
2. Cosine.
3. Centered Cosine.
4. Weighted Jaccard.
5. Historisches sparsames Top-K mit festem Cutoff 0,10.
6. Top-6 ranked Jaccard ohne absoluten Cutoff.
7. Top-12 ranked Jaccard ohne absoluten Cutoff.

Noch **kein musikalisch validierter Gewinner**, keine kalibrierten
Wahrscheinlichkeiten, keine Produktionsfreigabe. Die spätere
Lyrion-Integration und die Strategie **Bliss-first / Mood-first /
Hybrid** sind eigene Entscheidungen und noch nicht abschließend
geklärt; ähnliche numerische Scores beweisen keinen guten Mix.

Der Umweg über Original-Essentia-C++ endete mit erfolgreicher **numerischer
Parität** auf dem 100-MP3-Korpus und weiteren WAV-/FLAC-Kontrollen.
Rust v5 ist die korrigierte Referenz für diese Analyse: 14.500
Klassenwerte auf 100 echten MP3s, größte Abweichung gegenüber Essentia
C++ ca. `1.27e-5`, keine Mel-Patch-Abweichungen über der Toleranz
`0.001`. Feste vier und adaptive sechs Rust-Worker ergaben bitgleiche
Feature-Ergebnisse. Das **beweist keine musikalische Qualität**.

PR #17 ([experimenteller Essentia-C++-Worker](https://github.com/chrober/bliss-mood-poc/pull/17))
ist **separat, Draft und ungemergt**. PR #16 verwendet die bereits
berechnete Rust-v5-SQLite-Sidecar: **kein Merge von PR #17, kein
neuer Rust/C++-Build, keine neue Musik-Analyse notwendig**.
PR #13 ([experimenteller Lyrion Guidance-SPI-v2-Provider](https://github.com/chrober/bliss-mood-poc/pull/13))
bleibt ebenfalls separat und Draft. `main` ist nicht Ziel dieses
Handover-Schritts.

## Eingefrorene Testdaten und lokale Dateien

Alle folgenden Dateien liegen **ausschließlich lokal auf dem Windows-PC
des Benutzers** und dürfen weder auf GitHub noch in CI-Artefakte
hochgeladen werden:

| Verwendung | Windows-Pfad relativ zu `D:\LMS\bliss-mood-poc` |
| --- | --- |
| Verifizierte Rust-v5-Features | `benchmark-rust-v5-workers4-20261020-191946\round-01-workers-04-rust.db` |
| Pilot-Verzeichnis | `benchmark-similarity-v5-pilot-20261021-074316` |
| 24 ursprünglich vorgeschlagene Paare (unverändert lassen) | `benchmark-similarity-v5-pilot-20261021-074316\listening-pairs.csv` |
| **Aktuell zu bewertende 8 Paare** | **`benchmark-similarity-v5-pilot-20261021-074316\listening-pairs-review-first8.csv`** |
| Versiegelte private Auswahlgründe (vor Hörtest nicht öffnen) | `benchmark-similarity-v5-pilot-20261021-074316\selection-audit-private.json` |
| Bestehende rein numerische Vergleichsausgabe | `benchmark-similarity-v5-pilot-20261021-074316\unlabeled-metric-diagnostics.json` |

Die CSV besitzt die Spalten `left,right,genre_label,mood_label`.
`left/right` sind **exakte relative `TracksV2.File`-Schlüssel**;
bitte nicht umschreiben oder anhand von Künstler/Titel raten.
Bewertungsregeln pro Dimension: `1` = musikalisch ähnlich,
`0` = unähnlich, leer = bewusst nicht bewertet. Pro
behaltener Zeile muss **mindestens eine** der beiden Dimensionen
ausgefüllt sein. Paare mit komplett fehlender Beurteilung entfernen,
nicht erfinden. Getrennte Genreurteile und Mood-/Energie-Urteile;
ein Genre-Positiv darf Mood-Negativ sein und umgekehrt.

Zur Orientierung der bisherige unlabeled Befund (gleiche 100 Songs,
3.000 zufällig gezogene Paarvergleiche pro Head, keine echten Labels):

| Metrik | Genre-Median | Mood-Median | Genre Null-Scores | Mood Null-Scores |
| --- | ---: | ---: | ---: | ---: |
| RMS | 0.8651 | 0.9241 | 0 % | 0 % |
| Cosine | 0.5344 | 0.6564 | 0 % | 0 % |
| Centered Cosine | 0.4481 | 0.4148 | 0 % | 0 % |
| Weighted Jaccard | 0.3115 | 0.4105 | 0 % | 0 % |
| Altes Top-K mit Cutoff | 0.1638 | 0.0000 | 17.2 % | 61.6 % der 2.979 **definierten** Mood-Paare |
| Top-6 ranked | 0.1729 | 0.1826 | 7.7 % | 7.8 % |
| Top-12 ranked | 0.2196 | 0.2149 | 0.1 % | 0.1 % |

8/100 Songs mit maximaler Mood-Aktivierung unter 0,10; Mood-Median
aktiver Klassen >= 0,10 nur 2 (Genre 5). Altes Mood-Top-K lieferte
außerdem 21 undefinierte Werte von 3.000. Diese Verteilungen sind
**technische Eigenschaften**, keine musikalische Evaluation.

Die 24 Pilot-Paare wurden aus allen 4.950 Paaren der 100 Songs nach
acht modellgesteuerten Gruppen ausgewählt: high_both (4),
mood_high_genre_low (4), genre_metric_disagreement (3),
mood_metric_disagreement (3), low_both (3),
low_mood_activation (3), random_control (3),
genre_high_mood_low (1). Die ersten acht sind eine unveränderte
Arbeitskopie. **Aktive Auswahl verzerrt eine ROC-AUC**; selbst mit
echten Labels wäre das nur eine explorative Diagnose, keine
unabhängige Validierung und keine automatische Metrikentscheidung.

## Lyrion-Play-Queue: aktueller realer Stand und Korrektur

Der Benutzer hat zur Wiedergabe der acht Paare den Lyrion-Player
**„Küche“** verwendet. Der Code verwendet eine stabile Player-ID,
weil die vom Server gelieferte Unicode-Schreibweise früher als
`KÃ¼che` fehlcodiert ankam. Lyrion-Datei-URLs werden direkt aus den
**absoluten Pi-Pfaden** (Musikroot im Pi-Dateisystem `/mnt/music`)
abgeleitet; CSV-Schlüssel sind nur relativ. Der Umweg über alle
77.387 Lyrion-Titel war viel zu langsam; das aktuelle Skript nutzt
gezielte `songinfo`-Abfragen und verifiziert die exakten URLs.

Die erste Bulk-Queue-Anfügung hatte **16 beabsichtigte Positionen,
aber nur 15 unterschiedliche Track-IDs**, da ein Song bei Paar 4
rechts und Paar 5 links erneut vorkam. Ein
`playlistcontrol cmd:add track_id:ID1,ID2,...`-Sammelaufruf
fügte tatsächlich nur 15 Einträge hinzu, meldete `count:15`
**nachdem** die Queue bereits verändert wurde. Alte Queue vorher:
41 Tracks; 56 danach ist plausibel, aber ohne zusätzliche
Abfrage nicht als aktueller Zustand zu behaupten. Der Benutzer
hatte entschieden, den bereits geladenen Hörtest dennoch zu nutzen.

**Benutzerseitige Codekorrektur ist bereits auf PR #16!**
Aktuelles Skript:
[`scripts/queue_similarity_pairs_lyrion.ps1`](../scripts/queue_similarity_pairs_lyrion.ps1).
Es hängt bei neuen, ausdrücklich gewollten Läufen **jede der 16
Positionen einzeln an**, kontrolliert jedes `count=1` und das
Wachsen der Queue um genau eins, prüft anschließend via
`status ... playlist_loop` den geordneten Queue-Tail und
verweigert vor dem Schreiben erneutes Anhängen sowohl der
16-Positionen-Sequenz als auch der alten deduplizierten
15-ID-Folge. Unvollständige Präfixe werden ebenfalls erkannt.
Die Mehrschritt-Schreiboperation ist **nicht atomar**; nach
Fehlern Queue zuerst untersuchen, niemals blind wiederholen.
Details unter
[`docs/similarity-metric-evaluation.md`](similarity-metric-evaluation.md)
und Mock-Tests `tests/test_queue_similarity_pairs_lyrion.py`.
**Die neue Chat-Session darf die Queue jetzt nicht ändern.**

## Relevant im Repository

- `scripts/evaluate_similarity.py`: getrennte Genre-/Mood-Auswertung
  mit read-only schema-v3-SQLite, echten 0/1-Labels, Positiv-/Negativ-
  Verteilungen und tie-aware ROC-AUC.
- `scripts/propose_similarity_listening_pairs.py`: einmalig
  verwendete reproduzierbare Auswahl; aktuell **nicht erneut ausführen**.
- `tests/test_evaluate_similarity.py`,
  `tests/test_propose_similarity_listening_pairs.py`,
  `tests/test_queue_similarity_pairs_lyrion.py`: Regressionstests.
- `docs/similarity-metric-evaluation.md`: ausführliche Methodik,
  Modell- und Lyrion-Details.
- `docs/powershell-script-conventions.md`: **verpflichtende**
  Ausgabeform für alle PowerShell-Skripte:
  vollständiges, kopierbares **`& { ... }`**, auch bei Korrekturen.
  Keine isolierten Ersatz-Schnipsel!
- `docs/chat-handover.md`: historischer Einstieg zu Scanner-,
  Worker- und Produktarchitektur; **für den aktuellen PR-#16-Fokus
  ist dieses Dokument maßgeblich**.

## Nur nachdem der Benutzer mit der CSV zurückkommt

1. **Erst die vom Benutzer gelieferten Daten lesen.** Prüfen:
   Dateiformat; tatsächlich beurteilte Zeilen pro Head, Positiv/Negativ
   je Head, leere Felder, Auslassungen und Duplikate; kein
   automatisches Auffüllen. Änderungen an CSV nur mit
   Benutzerfreigabe; Originalkopie erhalten.
2. Falls der Benutzer nur die ausgefüllte CSV hat: read-only
   `scripts/evaluate_similarity.py` auf der **Rust-v5-Sidecar**
   mit `--include-experimental --labels <bewertete-CSV>` ausführen
   (oder einen sicheren lokalen PowerShell-Aufruf bereitstellen).
   **Kein neuer Musik-Scan/ONNX/C++-Build**. In der JSON-Ausgabe:
   `labeled.genre` und `labeled.moodtheme` mit
   `pairs_judged_for_head`, `pairs_missing_compatible_vectors`,
   `metrics.<name>.positives/negatives` und `roc_auc`.
   Für ROC-AUC braucht jeder Head **mindestens ein positives und
   ein negatives** Urteil; sonst `null`/`n/a`.
3. Wenn der Benutzer bereits die Tabellen oder das
   `similarity-first8-labeled.json` liefert, **diese erst
   interpretieren**, statt die Auswertung unnötig zu wiederholen.
   Score-Rangfolgen nur als Pilot-Diagnose lesen, Unsicherheit bei
   acht Paaren ausdrücklich benennen. Kein Schluss `AUC=1` =>
   beste Produktionsmetrik.
4. Die nächsten Schritte **danach** mit dem Benutzer abstimmen:
   Bewertungs-Kriterien prüfen, bei Bedarf restliche 16 Paare
   anhören; anschließend unabhängige/held-out Studie mit
   sauberer Genre/Mood-Trennung und später Lyrion-Mixvergleich.
   Entscheidung zu Bliss-first vs. Mood-first vs. Hybrid
   bis zu kontrolliertem Hörvergleich offen lassen.

Falls erst nach Erhalt der CSV ein lokal auszuführendes Kommando
nötig ist, ausschließlich ein **vollständiges PowerShell-`& { ... }`**
mit überprüften Pfaden/Parametern liefern. Der Evaluator benötigt
`--db`, `--include-experimental`, `--labels` und optional
`--limit 300 --pairs 3000 --seed 20261021 --examples 5`.
Die Ausgabe in einer **neuen** lokalen JSON-Datei ablegen,
bestehende Bewertungen und Reports nicht überschreiben.

## Branch-/CI-/Datenschutzregeln

- **Keine Merges in `main`**, keine Änderungen an PR #13/#17 ohne
  gesonderten Auftrag. PR #16 ist Draft; erst vor neuen Arbeiten
  PR-Head und aktuelle Checks kontrollieren. Letzter geprüfter
  Head vor diesem Handover hatte erfolgreiche Rust-Checks;
  Aussagen über spätere CI immer neu prüfen.
- Keine Veröffentlichung privater Audio-Dateien, Lyrion-Katalog-
  dumps, ausgefüllter Hörtest-CSV oder privater SQLite-Sidecars.
- **Keine lokalen Rust-Builds** auf dem Windows-Laptop; wenn später
  erforderlich, GitHub-Actions-Builds nutzen. Im aktuellen
  Arbeitsschritt ist **gar kein Build nötig**.
- Gesprächs- und PowerShell-Ausgaben **Deutsch**; Scripts immer
  **vollständig als `& { ... }`**. Keine unaufgeforderten
  Repo-Änderungen während der Hörbewertungsphase.

**Letzter Status:** Der Benutzer beginnt jetzt den Hörvergleich und
wird die CSV bearbeiten. **Die nächste Session wartet ausdrücklich
auf seine Analyse.**
