# Autotune: vier reale 100-Song-End-to-End-Messkampagnen und Produktentscheidung

**Stand: 28.10.2026 — empirischer Befund, nicht Implementierungsvorgabe.**  
**PR:** [#19](https://github.com/chrober/bliss-mood-poc/pull/19), `feat/ram-safe-online-autotune` (auf PR #18 aufbauend).  
**Detaillierter technischer Verlauf:** [online-autotune-phase-b.md](online-autotune-phase-b.md).

## 1. Versuchsgrundlage und Versionsabgrenzung

Vier **tatsächlich abgeschlossene**, lokal/private Realmusik-Kampagnen mit je **10 vollständigen Scans**: zwei in umgekehrter Reihenfolge ausbalancierte Wiederholungen für `fixed6`, `fixed8`, `fixed10`, `fixed12` und `autotune` (Start/Minimum 6, Maximum 12). Pro Scan **100 identische Songs**, **27.617 EffNet-Patches**, originale persistente Essentia-C++-Worker, die ONNX-Heads `moodtheme`, `genre` und `voice`, inklusive Embeddings. Je Kampagne meldet das Harness `exact_numeric_parity=true`. **Keine Musikdateien, Songnamen, privaten SQLite-DBs oder Scanner-Rohberichte in Git einchecken.**

| Kampagne | Lokales privates Ergebnisverzeichnis | Getesteter Scanner-Source-Commit | Bedeutende Algorithmus-Eigenschaft |
|---|---|---|---|
| 1, ca. 15:59 | `benchmark-autotune-e2e-20261028-155959` | `32cba98c229bbfbbeb329badb84212446c3b3721` | Verfrühte Exploration-Budget-Sperre, bei 6 Workern blockiert |
| 2, ca. 16:41 | `benchmark-autotune-e2e-20261028-164136` | `091842b347f910e40a6b81b4b1aca3aa873575c8` | Erste Grobsuche vollständig, steigende Reihenfolge |
| 3, ca. 17:43 | `benchmark-autotune-e2e-20261028-174322` | `c705cffc8348c42272efc0302b5a94bd6f089c2f` | Weit entfernter Grenzwert zuerst; RAM-safe deferred retry, Drain-Telemetrie |
| 4, ca. 18:54 | `benchmark-autotune-e2e-20261028-185443` | `25ffa672bc8e25b20f711c5b774100743101250d` | Konsistente Bestenauswahl und kein nicht-sicherheitsbedingter Tail-Resize unter Mindestfenster |

Alle Kennzahlen sind **beschreibend**; pro Worker-Modus und Kampagne liegen nur **zwei** Wiederholungen vor. Sie sind nicht als formal signifikanter Vergleich, hardwareübergreifende Rangfolge oder Kausalschätzung für eine einzelne Controlleränderung geeignet.

## 2. Vier Kampagnen im direkten Vergleich

**Median der vollständigen Wall-Clock-Scanzeit in Sekunden; kleiner ist besser.**

| Kampagne | fixed6 | fixed8 | fixed10 | fixed12 | autotune | Schnellste getestete Einstellung |
|---|---:|---:|---:|---:|---:|---|
| 1 | 90,079 | 82,562 | 73,055 | **70,560** | 87,559 | fixed12 |
| 2 | 91,583 | 89,594 | **80,066** | 85,245 | 107,091 | fixed10 |
| 3 | 125,631 | 112,673 | **107,621** | 121,752 | 118,112 | fixed10 |
| **4 (aktuell)** | **114,647** | **114,633** | **90,119** | **106,276** | **129,247** | **fixed10** |

`autotune` war in **keiner der vier Kampagnen** die schnellste getestete Betriebsart. Dagegen wechselte der beste **feste** Vergleichswert zwischen den Kampagnen (einmal 12, dreimal 10). Die Unterschiede bei identischen festen Einstellungen über den Tagesverlauf sind groß: `fixed10`-Median zwischen **73,055 und 107,621 s**, `fixed12` zwischen **70,560 und 121,752 s**. Unterschiedliche Umgebungszustände (CPU-, NAS-/I/O-Last, Cache, thermische Effekte, asynchrone Jobs usw.) sind mögliche **Hypothesen**, nicht isoliert gemessene Ursachen. Die balancierte Reihenfolge und gleicher Input beseitigen diese Störfaktoren nicht vollständig.

**Wichtig zum Verständnis der relativen Veränderungen:** Die dritte Kampagne zeigte einen geringeren relativen Rückstand des Autotuners zu fixed10 als die zweite; die vierte zeigte wieder einen wesentlich größeren. Weder eine Verbesserung noch eine Verschlechterung kann ohne gleichzeitige Kontrolle der Umgebungsbedingungen kausal einem einzelnen Code-Fix zugeschrieben werden.

## 3. Vierte Kampagne: vollständige Messwerte und Erkenntnisse

### Gesamtscan, Runden und Ressourcen

| Modus | Runde 1 Wall s | Runde 2 Wall s | Median Wall s | Median Songs/min | Peak Prozessbaum private MiB |
|---|---:|---:|---:|---:|---:|
| fixed6 | 89,058 | 140,236 | 114,647 | 55,078 | 645,44 |
| fixed8 | 101,104 | 128,162 | 114,633 | 53,081 | 780,07 |
| **fixed10** | **83,090** | **97,147** | **90,119** | **66,987** | **1.026,02** |
| fixed12 | 94,188 | 118,365 | 106,276 | 57,197 | 1.178,51 |
| **autotune** | 118,118 | 140,376 | **129,247** | **46,769** | **1.245,13** |

Das Harness berichtet die folgenden **gepaarten pro-Runde-Speedups** des Autotuners (positiv = autotune schneller; Median der beiden pro-Runde-Prozentsätze, **nicht** der Quotient aus zwei Kampagnenmedianen):

| Vergleich | Median gepaarter Speedup | Runden mit schnellerem autotune |
|---|---:|---:|
| vs fixed6 | −12,352 % | 0 / 2 |
| vs fixed8 | −11,553 % | 0 / 2 |
| vs fixed10 | **−30,225 %** | **0 / 2** |
| vs fixed12 | −17,970 % | 0 / 2 |

Für `fixed10` liegt der Unterschied der Median-Wall-Zeiten bei **39,128 Sekunden** (129,247 minus 90,119 s); als relative **Wall-Zeit-Zunahme** sind das etwa **43,4 %**. Das ist **eine andere Größe** als der berichtete gepaarte Durchsatz-Speedup von −30,225 %. Beide Werte dürfen nicht verwechselt werden.

**Algorithmusdiagnostik:** Beide Autotune-Runden haben jeweils **5 Probes**, `search_completed=true`, `replication_completed=false`, je **4 Workerwechsel** und `exploration_budget_holds=1`. Der beste getestete Kandidat war **8 in Runde 1**, **12 in Runde 2**. Workeränderungen nach 12/30/56/79 bzw. 8/28/53/72 abgeschlossenen Songs. Letzter Worker laut den aggregierten Reports 8 (R1) und 12 (R2). Damit ist der in der dritten Kampagne beobachtete *late resize nach Song 91* nicht mehr sichtbar; die gesamte Scanzeit ist aber weiterhin schlechter als alle festen Vergleichsmodi. Es ist methodisch falsch, damit die genaue Performancewirkung des Tail-Fixes zu beziffern.

**Speicher / Datenintegrität:** `exact_numeric_parity=true`; der RAM-Guard meldet in sämtlichen Scans einen positiven Mindestabstand über der 1.536-MiB-Sicherheitsreserve, pro Autotune-Run mindestens **3.659,2 MiB** guarded available RAM (Kampagnenminimum über alle Modi **3.383 MiB**). Der größte gemessene private Prozessbaum in dieser Kampagne war im Autotune-Modus **1.245,13 MiB** und bei fixed10 **1.026,02 MiB**. Die größere Autotune-Speicherbelegung allein erklärt **nicht** den Zeitverlust.

### Einordnung der bisherigen technischen Erkenntnisse

- **Phase 1 (erstes Experiment):** Eine falsch berechnete Mindestrestarbeit verhinderte jede Exploration. Korrigiert; vollständige erste Grobsuche seit Experiment 2 in beiden Wiederholungen.
- **Phase 2 (zweites Experiment):** 5 kurze Messfenster und vollständige erste Grobsuche, aber keine wirtschaftlich finanzierbare vollständige Replikation. Beste Workerzahl je Runde schwankte.
- **Phase 3 (drittes Experiment):** Priorisierung des entfernten Randpunkts und RAM-sicherer Retry funktionieren unter den vorhandenen Tests; die echte Messreihe zeigte weiterhin ungünstige E2E-Laufzeiten und einen **nachgewiesenen** Auswahlfehler: in R1 Bestwert 8, späterer Wechsel 8→12 nach Song 91 bei nur 2 nicht dispatchten Songs. Produktive Admission-Drains 12→8 von **22,399 / 23,948 s** gemessen, **keine reinen Leerlaufwerte**.
- **Phase 4 (viertes Experiment):** Scored-Best-/Tail-Fix in Source `25ffa672` numerisch korrekt und CI-validiert; kompletter erster Sweep wieder in beiden Runden, kein beobachteter späte Song-91-Wechsel, aber `autotune` **in keiner Runde** schneller als irgendeine feste Vergleichsworkerzahl.
- **Über alle Experimente:** Keine Evidenz für einen universellen besten festen Wert oder eine statistisch belastbare Online-Auswahl; **keine Evidenz für eine Überlegenheit des jetzigen Autotuners auf 100-Song-Scans**. Das bedeutet nicht, dass der Controller bei erheblich längeren Bibliotheksscans nutzlos sein muss – diese wurden noch **nicht** mit derselben E2E-Testmethodik durchgemessen.

## 4. Neue Produkt- und Architekturhypothese: Autotune nur bei ausreichend großer Restarbeit

**Vorschlag (Diskussionsstand, noch NICHT implementiert und nicht validiert):**

1. **Kleine Scan-Aufträge:** Kein online-autotune. Weiterhin Standard-`--adaptive-policy resource` oder manuelle, explizit gesetzte feste Workerzahl mit bestehenden Ressourcengrenzen. Dabei **nicht** pauschal die bestehende ressourcenbasierte Anpassung deaktivieren: `resource` ist von der teuren explorativen `autotune`-Policy zu unterscheiden.
2. **Große Scan-Aufträge:** Experimentelles Autotune optional erst aktivieren, wenn sich die Explorations- und Replikationskosten über ausreichende **noch wirklich zu analysierende Songs** amortisieren können (nicht bloß Anzahl aller Titel im Katalog). Neue Candidate- oder Drain-Kosten vor jeder Erweiterung gegen einen ausreichend langen Ausnutzungshorizont abwägen.
3. **Konservative Abbruch- und Fallback-Regel:** Wenn die Restarbeit oder die messbare Stabilität nicht ausreichen, auf den ressourcenbasierten bzw. gewählten festen Modus zurückfallen; keine letzten teuren Resizes ohne wirtschaftlichen Nutzen. Fail-closed RAM-Watchdog und CPU-/cgroup-Grenzen gelten unabhängig von der Policy.
4. **Keine unbelegte Schwelle:** Unsere bisherige Messbasis umfasst ausschließlich **100 Songs pro vollständigem Scan**. Daraus lässt sich **keine belastbare numerische Aktivierungsschwelle** (100, 200, 500, 1.000 usw.) ableiten. Ein etwaiger Mindestwert müsste mit längeren Scans, repräsentativen Beobachtungsfenstern, Wechselkosten und mindestens einem zweiten System überprüft werden, bevor er Default-Verhalten ändert.

Die Messungen sprechen dafür, **den gegenwärtigen Autotuner nicht als produktiven Default zu aktivieren** und Entwicklungsschwerpunkte vorerst auf sichere Ressourcensteuerung, zuverlässig manuell konfigurierbare Workerzahlen und die eigentliche Musik-/Similarity-Funktionalität zu legen. PR #19 bleibt vorerst experimentell; **keine Entscheidung über Merge, endgültige Entfernung oder automatisches Umschalten ab einer bestimmten Trackzahl ist hiermit getroffen.**

## 5. Nächste Evidenz und klare Entscheidungsgrenzen

Keine weiteren identischen **10×100-Song**-Durchläufe allein zur Feinabstimmung durchführen: Die vier Kampagnen haben die Problematik wiederholter kurzer Scans bereits sichtbar gemacht. Falls Autotune weiter erforscht werden soll, zunächst ein diskriminierendes Langscan-Versuchsdesign entwickeln (mehrere Scanlängen, gleiche Modelle/Eingaben, Ressourcen- und CPU-/NAS-Telemetrie, dokumentierte Drain-/Session-Kosten, gleichberechtigte feste Baselines, reproduzierbare Artefakt-SHA und keinerlei private Rohdaten in Git). Erfolgsmaßstab ist **vollständiger end-to-end Durchsatz bei akzeptablen Speichergrenzen**, nicht allein `search_completed` oder maximales Patches/s eines einzelnen Fensters.

**Versionsgrenze:** Die vierte Kampagne testete `25ffa672`. Etwaige spätere Dokumentationscommits oder neue hypothetische Scanlängen-Gates sind **nicht in der vierten Messkampagne enthalten**.
