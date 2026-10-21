# Lyrion – nächster lokaler Hörvergleich für Song-Repräsentationen

**Stand:** 21.10.2026, Planungsdokument, **noch kein lokaler Test gestartet**.
Arbeitszweig ausschließlich `feat/similarity-metric-evaluation`, PR #16 Draft.
Keine Änderung an `main`, PR #13/#17, Mixer oder privater Musikbibliothek.

## Warum nach FMA, MTT und DEAM noch lokale Hörurteile?

Das FMA-Genre-Retrieval und die vollständige MagnaTagATune-
Tripel-Exploration sprechen in den jeweils untersuchten
Settings nicht für das rohe 1280D-Embedding als universellen Sieger.
DEAM misst Valence/Arousal-Abstände, keine tatsächliche
Playlist-Übergangsqualität; die neue DEAM-A/B-Analyse ist aktuell
durch den zeitweise unerreichbaren Original-Quellserver blockiert.

Der erste reale Lyrion-Hörpilot enthielt acht von
Menschen bewertete Songpaare, **null Genre-positive Paare**
und vier Mood-positive vs. vier Mood-negative Paare.
Bei so wenigen und bereits modellabhängig vorgeschlagenen
Beispielen ist weder eine Genre-AUC noch ein
Produktionsentscheid möglich. Siehe
[Hörtest-Handover](similarity-listening-review-handover-2026-10-21.md).

## Kleine Schritte, kein Vollscan

**Schritt L0 (nur lokal, ohne neue Bewertungen):**
Eine bereits analysierte, eindeutig zuordenbare,
begrenzte Stichprobe aus der vorhandenen
`schema-v3`-Feature-Sidecar-DB wählen. Read-only
prüfen: Trackkeys, Audio-SHA, korrekte
87D-Genre-/56D-Mood-Modell- und Preprocessing-
Fingerprints. Einen getrennten, nur für dieselben
Tracks erzeugten 1280D-Song-Embedding-Sidecar
nach dem experimentellen Research-Protokoll
prüfen. **Keine komplette Library neu analysieren,
keinen globalen Cache hochladen und keine
SQLite-Bestandswerte überschreiben.**
Sollten Song-Embeddings lokal noch fehlen,
einen separaten begrenzten CLI-Export planen –
keine implizite Portierung von PR #17 oder
Änderung am Mixer.

**Schritt L1 (kleiner neuer Hörpilot, ca. 12
Kontraste):** Gleiche Seed-Songs und
Audioschnipsel für alle Vergleichsmethoden,
fixierte randomisierte Reihenfolge.
- Etwa vier menschlich *vorab* als genreähnlich
  eingeschätzte Kontrollpaare, damit die
  ausschließlich negativen Genre-Labels
  des ersten Pilots nicht wieder auftreten.
- Etwa vier offenkundige Genre-/Mood-Kontraste
  als Negativkontrollen.
- Etwa vier interessante Abweichungen, bei denen
  das direkte 1280D-Cosine und die Klassifikations-
  Similarity deutlich unterschiedliche Vorschläge
  machen. **Diese sind aktiv modellselektiert,
  deshalb nur Challenge-/Diagnosesätze, kein
  unabhängiges zufälliges Testset.**
- Kandidatenvarianten und Scores beim Hören
  verbergen; Artist-/Titelnamen zum Auffinden
  der eigenen Musik sind erlaubt. Seiten
  links/rechts zufällig mischen, ohne Labels
  aus Songnamen, ONNX-Aktivierungen oder
  bekannten Mustern automatisch zu generieren.

**Schritt L2 (menschliche Bewertungen):**
Je Kontrast *getrennt* erfassen: gefühlte
**Stil-/Genre-Nähe**, **Stimmung/Energie**,
**klangliche Nähe** und
**Eignung als direkter Nachfolger in einer
Playlist** (jeweils 1–5 oder explizit
unbeurteilbar). Zusätzlich optionale
**Urteilssicherheit** (1–3) und
Freitext. Die vier Achsen nicht zu einer
einzigen „objektiven Ähnlichkeit“ vermengen.
Bestehende acht Urteile nicht rückwirkend ändern.

**Schritt L3 (read-only Auswertung):**
Für dieselben Songpaare/Anker eine
deterministisch gepaarte Auswertung von
Genre-Cosine/Centered-Cosine,
Mood-Cosine/Centered-Cosine und
1280D-Audio-Cosine. Abdeckung,
undefinierte Werte, harte Negativbeispiele,
Trennung von menschlichen Achsen,
kleine Fallzahlen und Auswahlverzerrung
explizit ausweisen. Bei nur 12 neuen
Kontrasten **keine signifikante Überlegenheit
oder Produktionsfreigabe** behaupten.
Fusion C nur als vorregistrierte feste
Explorationsvariante und nicht anhand
derselben Labels tunen.

Erst nach diesem kleinen Probelauf
entscheiden, ob ein eigener 24–40-Paar-
Testblock mit neuen, zuvor ungesehenen,
nach Artist/Album möglichst disjunkten
Tracks sinnvoll ist. MTT-Menschentripel
und FMA VALIDATION dürfen dafür nicht
nachträglich als unabhängiger Holdout
bezeichnet werden.

## Datensicherheit und Lyrion-Bedienung

- Alle Musiktitel, Datei-URLs, Bewertungen,
  Audio-Hashes und pro-Track-Vektoren
  bleiben **auf dem lokalen Rechner**.
  Ins Repo/GitHub Actions gelangen nur
  synthetische Tests, Skripte und
  **aggregierte, nicht identifizierende**
  Auswertungen, falls ausdrücklich gewünscht.
- Vorhandene
  [`queue_similarity_pairs_lyrion.ps1`](../scripts/queue_similarity_pairs_lyrion.ps1)
  kann für bewusst ausgewählte Paarlisten
  verwendet werden; vor echter Queue-Mutation
  **Dry-run/Player-ID/Track-ID-Auflösung**
  und Duplikatsicherung wiederholen.
  Die Musikdatenbank bleibt unverändert;
  keine automatische Queue-Aktion aus dieser
  Planung heraus.
- Der erste Hörpilot hatte bei Semikolon-CSV
  einen Delimiterfehler; beim Export explizit
  CSV-Trennzeichen prüfen oder
  das vorhandene Evaluator-Kommaformat nutzen.
- Alle technischen Änderungen im Research-Branch
  und GitHub Actions, **kein lokaler Rust-Build
  auf Windows** ohne gesonderte Entscheidung.

**Status:** Vorgehen festgehalten;
L0/L1/L2/L3 sind bewusst **nicht ausgeführt**.
Nächster tatsächlicher Schritt erst
nach konkreter lokaler Vorprüfung, nicht
parallel zur DEAM-Quelle-Störung.
