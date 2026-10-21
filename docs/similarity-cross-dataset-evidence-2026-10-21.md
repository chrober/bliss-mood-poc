# Cross-dataset similarity evidence, without inventing a common score

**As of 2026-10-21**. Branch `feat/similarity-metric-evaluation`,
Draft PR #16. All values reproduced from documented **completed**
repository workflows, not imputed from any uncompleted follow-up.
Different datasets measure **different constructs**. No metric is
approved for production; do not merge to main.

## Independent evidence channels

| Dataset | What is measured | Scored cohort | Source |
| --- | --- | --- | --- |
| [FMA-Small](fma-genre-benchmark-plan.md) | Genre retrieval vs eight coarse *top-level genre categories* using the 87D Genre head | 80 artist-distinct **VALIDATION** tracks, official TEST untouched | [successful run 39583233757](https://github.com/chrober/bliss-mood-poc/actions/runs/39583233757) |
| [DEAM](deam-similarity-benchmark.md) | Query-macro Spearman of 56D Mood similarity vs **human Valence/Arousal proximity**, a *proxy* for mood | 240 seeded, collection-stratified tracks **after exact catalog artist/title screening** (197 earlier excerpts, 43 full 2015 songs) | [successful run 39579552118](https://github.com/chrober/bliss-mood-poc/actions/runs/39579552118) |
| [MagnaTagATune](magnatagatune-paired-analysis-2026-10-21.md) | Human **odd-one-out** general perceived similarity; majority accuracy | 346 unique unordered triplets / 1,019 MP3s, 53 human-vote ties, **293 eligible**; all 346 evaluated, no MTT holdout | [successful cache HIT 39600498519](https://github.com/chrober/bliss-mood-poc/actions/runs/39600498519) |
| MTG-Jamendo | Source 87D Genre / 56D Mood tagging domain, label vocab and training/test provenance sanity | Official split-0 class names/artist separation checked, **no new prediction accuracy computed** | [successful metadata audit 39586686845](https://github.com/chrober/bliss-mood-poc/actions/runs/39586686845) |

## Metric-by-metric triangulation (different units; do not average rows)

| Metric | FMA Genre P@5 | DEAM filtered Mood VA Spearman | MTT Genre majority accuracy | MTT Mood majority accuracy |
| --- | ---: | ---: | ---: | ---: |
| RMS | 0.3175 | 0.2711 | 63.5% | 54.6% |
| Cosine | 0.3500 | 0.2868 | 65.2% | 65.5% |
| Centered Cosine | 0.3525 | 0.2813 | 65.2% | **65.9%** |
| Weighted Jaccard | **0.3550** | **0.2888** | 63.8% | 61.1% |
| Historical cutoff Top-K | 0.3150 | 0.1903 (216/240 valid DEAM queries) | 60.1% | **44.4%** (~71.7% MTT coverage) |
| Ranked Top-6 Jaccard | 0.3150 | 0.2721 | 61.8% | 62.5% |
| Ranked Top-12 Jaccard | 0.3400 | 0.2745 | 64.5% | 64.8% |

FMA P@5 is a **genre retrieval proportion**, DEAM is a **Spearman
rank correlation coefficient** against continuous human VA proximity,
and MTT numbers are **classification proportions for general musical
triplet judgments**. They MUST NOT be numerically averaged,
standardized as if interchangeable, or treated as a joint
statistical meta-analysis.

### Descriptive observations (hypotheses only)

1. **Cosine** performs relatively consistently across independent
   reference types. Its Genre P@5 is 0.3500 vs the FMA best 0.3550
   (tiny difference on just 80 songs); filtered DEAM Mood
   VA correlation 0.2868 vs best 0.2888; MTT Mood and Genre both ~65%.
2. **Centered Cosine** is very close to Cosine throughout.
   MTT Mood is only ~0.4 percentage points higher than Cosine,
   and Genre is tied. The difference is smaller than plausible
   resampling variation and will be inspected with paired
   within-question tests, NOT interpreted as proven.
3. **Weighted Jaccard** is slightly ahead on FMA and DEAM,
   but behind Cosine in MTT general similarity. A different
   objective can lead to a different appropriate metric;
   no single reference is privileged to determine playlist quality.
4. The **historical cutoff Top-K** exhibits important coverage
   failures and weaker Mood triplet coverage-adjusted results.
   It should never be compared to fully defined metrics only
   on its selectively covered questions.
5. **Genre-vs-VA** numbers are deliberately omitted: Genre
   classifiers have not been validated against VA as Genre ground
   truth. Likewise MTT votes are general similarity, not a
   separate genre and mood human annotation split.

### Why these are not independent confirmations

- DEAM's 75 possible artist/title matches to the Jamendo catalog
  were excluded *before* the filtered 240 sample. This is an
  incomplete catalog screen, not proof of unseen audio in the
  Discogs encoder training sets. The filtered and original
  240-track samples differ, so their scores cannot be paired.
- FMA used **VALIDATION only** and the official TEST split is still
  deliberately reserved. The pretrained encoder's overlapping
  recording provenance is not fully audited.
- All 346 unique MagnaTagATune human triplets were explored.
  The artist co-occurrence graph forms one connected component.
  Its baseline accuracy is therefore descriptive *within-corpus*
  evidence, not strict independent artist-heldout proof.
- Not all rows have identical coverage; old Top-K abstentions
  introduce selection/denominator bias if mishandled.
- Full-song Lyrion playback may react differently from 30-s
  low-bitrate research clips, and pairwise similarity is distinct
  from adjacent-song transition quality.
- Annotation uncertainty is material; MTT had 53 questions tied
  for human majority even after merging ordered permutations.

## Next gates, in order

**A. Paired MTT uncertainty.** Use
[mtt_paired_evidence.py](../scripts/mtt_paired_evidence.py):
compare the SAME 293 questions for all seven metrics and
both heads, treating metric abstentions as incorrect. Report
discordance counts plus descriptive (not population-CI)
question resampling and artist-weight sensitivity.
Await real completed run and actual paired numbers before
asserting a difference is nontrivial.

**B. Operational A/B.** A pinned Rust-v5 binary-cache + 114-MiB
curated MP3 cache allow controlled 2- vs 4-worker same-cohort
runs. Check true cache HIT, audio/model hashes, 14 aggregate
scores, wall time and memory before claiming faster workflows.
Do not imply that an adaptive worker scanner is running:
this GH benchmark uses fixed isolated-process workers.

**C. New independent human evidence.** Find a separately
licensed/accessible perceptual or transition quality reference.
Do not recycle MTT as an unseen holdout.

**D. Final FMA TEST split** only once metrics and analysis rules
are predeclared, and no tuning has been carried out against it.
A blinded actual Lyrion playlist listening/transition assessment
remains necessary before choosing a user-facing similarity policy.

PR #16 stays Draft. No local/private music rescan, no
production mixer change, no merge to main, no commits to PR #13/#17.


## Updated FMA training-provenance warning

[Completed metadata-only FMA/MTG screening
39605675932](https://github.com/chrober/bliss-mood-poc/actions/runs/39605675932)
found **42 possible exact artist/title MTG-Jamendo
catalog matches among 800 FMA VALIDATION songs**,
**35 of 100** in Hip-Hop alone; FMA TRAINING had
121 candidates among 6,400. MTG artist-only matches
were 68 VALIDATION / 260 TRAINING.
**These do NOT establish literal audio duplication or
ONNX training exposure**, nor do their nonmatches
prove training disjointness. The untouched official
FMA TEST split is still reserved.

The [catalog-filtered FMA validation research
workflow](../.github/workflows/fma-genre-filtered-validation.yml)
and its Python parser exclude the 42 potential exact
catalog candidates before validation sampling and
model inference, reusing a pinned Rust-v5 binary.
The new filtered 80-song cohort is **not paired with**
the earlier 80-song FMA validation cohort; comparison
must remain descriptive. The filtered real
[run 39606850307](https://github.com/chrober/bliss-mood-poc/actions/runs/39606850307)
needs a completed result before any updated Genre
P@5/mAP/nDCG statements. Audit and reproducibility:
[FMA-MTG metadata screen](fma-mtg-catalog-overlap-2026-10-21.md).

## Second FMA VALIDATION reference: catalog-screened, independent TEST still reserved

[Confirmed filtered FMA Validation benchmark
39606850307](https://github.com/chrober/bliss-mood-poc/actions/runs/39606850307)
**PASS**: 42 possible exact artist/title catalog matches
with MTG-Jamendo (35/100 Hip-Hop candidates) were excluded
from the 800-song validation pool before an
80-artist-distinct, ten-per-genre selection.
**Filtered FMA Genre P@5** RMS 0.3000, Cosine 0.3200,
Centered Cosine **0.3225**, Weighted Jaccard 0.3000,
old cutoff Top-K 0.3025, Ranked Top-6 0.3125,
Ranked Top-12 0.3050. Filtered mAP@10 favored
Centered Cosine **0.1781** narrowly, filtered
nDCG@10 favored Ranked Top-6 **0.3048**
compared to Centered 0.3043. Random balanced
reference 0.113924.

**Crucial design:** This is a second *development*
reference on **different validation recordings**
from the unfiltered 80-song FMA sample in the main
table above, NOT a controlled paired causal
comparison and NOT confirmed independence from the
model's actual ONNX classifier/Discogs encoder
training data. The original FMA TEST partition
remains unused, and no MTT holdout remains.
[FMA provenance and filtering details](fma-mtg-catalog-overlap-2026-10-21.md).

The cross-dataset qualitative hypothesis remains
that Cosine and Centered Cosine are consistent
baseline/challenger methods; tiny shifts among
several methods on 80 songs cannot identify a
reliable production winner. Use separate Genre
ground truth vs Mood VA vs general human-triplet
judgments, never numerical averaging of these units.

## Next research axis (2026-10-21): Compare *representations*, not just metrics

The current seven metrics have been evaluated on already-pooled **87D Genre / 56D Mood/Theme classifier scores** only. The shared Discogs-EffNet model also internally provides **1,280D audio embeddings per patch**, but schema-v3 currently stores only the classifier heads. **No 1,280D song-level embedding baseline or multi-signal fusion has yet been evaluated.**

The next controlled experiment explicitly compares **A: per-head classification similarity**, **B: pooled direct 1,280D embedding cosine**, and **C: calibrated/rank-based task-aware fusion**, using identical clips and reference questions with strict cohort provenance. See [the canonical new-session handover](similarity-representation-comparison-handover-2026-10-21.md) for definitions, 1280D export/pooling design, reproducibility/parity gates, external Essentia/cosine.club precedents, CI costs, ground-truth caveats and prioritized implementation. Do not confuse fusion of similarity signals with Lyrion's separate Bliss-first / Feature-first / Hybrid candidate-admission strategy choice. Official FMA TEST remains unexamined, full MTT is exploratory, and no production choice has been made.


## Nachtrag: geplanter Repräsentations-A/B statt neue Evidenz (21.10.2026)

Für bereits untersuchte Klassifikationsvektoren bleiben alle
vorherigen FMA/DEAM/MTT-Zahlen unverändert. Der neue
[MTT-Embedding-A/B-Workflow](../.github/workflows/research-mtt-embedding-ab.yml)
und sein [gepaarter Evaluator](../scripts/evaluate_mtt_embedding_ab.py)
führen `embedding_cosine` gegen vier Genre/Mood-Cosine-Varianten
auf exakt denselben Audiodateien und 293 mehrheitsentscheidbaren
menschlichen Tripeln aus. Aus dem Anlegen eines Workflows folgt
**kein empirischer Qualitätssieg**. Ein gültiger A/B-Bericht setzt
cache-verifizierte 1019 Clips, Encoder/Audio-Hash-Parität,
genau 346 Fragen und ein vollständig bestandenes
Research-Smoke-/Python-CI-Gate voraus. Weiterhin kein
unberührter MTT-Holdout, offizieller FMA-TEST ungenutzt
und keine bestätigte Unabhängigkeit vom Trainingskorpus.

## Verifiziert: erster vollständiger Embedding-A/B auf identischer MTT-Cohort (21.10.2026)

**Achtung – ersetzt die oben noch als ausständig bezeichnete
A/B-Messung.** [Run 39617159250](https://github.com/chrober/bliss-mood-poc/actions/runs/39617159250)
ist **PASS**; 1019 Cache-Clips CRC-validiert, exakt 346
explorative Menschenfragen, davon 293 mehrheitsentscheidbar.
Auf denselben Aufnahmen lieferte **direkte 1280D-Cosine
182/293 = 62,12 %**, Genre-Cosine **191/293 = 65,19 %**,
Mood-Cosine **192/293 = 65,53 %** und
Mood-Centered-Cosine **193/293 = 65,87 %**.
Alle vier hatten wie das Embedding **100 % Abdeckung**.
Das Embedding lag gegenüber Mood-Centered-Cosine um
**−3,754 Prozentpunkte** zurück (nur Embedding korrekt 27,
nur Mood-Centered korrekt 38). Naives gepaartes
95-%-Tripel-Resampling für den Unterschied:
**−9,215 bis +1,365 Prozentpunkte**; wegen
Abhängigkeiten **kein unabhängiges Populations-CI**.
Auch Künstlergewichts-Sensitivitäten sind kein valides
Konfidenzintervall. Die Kausalinterpretation und
Generalisierbarkeit bleiben offen.

Der vorherige unabhängige synthetische Rust-Smoke
[Run 39616222834](https://github.com/chrober/bliss-mood-poc/actions/runs/39616222834)
bestand Rust-Unit-Tests und Release-Kompilierung,
brach aber beim externen Modell-Download wegen
`essentia.upf.edu`-Netzwerk-Timeout ab. Deshalb
wurde ein **synthetisches off/on/Pooling/Threads-Paritätsgate
vor den 1019er-Lauf** des neuen A/B-Workflows
hinzugefügt; dessen nachfolgenden Run erst auf
PASS prüfen, bevor dieses Gate als bestätigt gilt.

Vollständiger Studienbericht mit Methoden,
Paar-Discordanzen, statistischer Unsicherheit,
CI-Runs, Fingerprints, Limitierungen und nächstem
Evidenz-Gate:
[Audio-Embedding vs. Kopf-Baselines: MTT-A/B-Resultate](similarity-audio-embedding-ab-results-2026-10-21.md).
**Keine Fusion-Kalibrierung, keine Produktionsentscheidung,
kein erneuter MTT-Holdout, kein FMA-TEST, kein Merge.**

## Verifiziert: vollständiger explorativer A/B/C-Durchgang (21.10.2026)

Die vorab implementierten **vier untrainierten Equal-Midrank-Fusionen**
wurden zusammen mit den fünf bisherigen A/B-Methoden
im [Actions Run 39619708040](https://github.com/chrober/bliss-mood-poc/actions/runs/39619708040)
vollständig erfolgreich auf **exakt denselben 1019
MagnaTagATune-Clips und 293 mehrheitsentscheidbaren
Tripelfragen** ausgewertet. Synthetisches 1280D
Original-Patchpooling-/Head-Off-On-/SQLite-/Thread-
Paritätsgate erneut **PASS**.

Die Fusions-Genauigkeit auf dem gemeinsamen 293er-Nenner
(Abstentions als falsch): Audio+Genre **163/293 = 55,63 %**
(Coverage 234/293), Audio+Mood **170/293 = 58,02 %**
(241/293), Genre+Mood **167/293 = 57,00 %**
(230/293), Audio+Genre+Mood **192/293 = 65,53 %**
(283/293). Der bisherige Mood-Centered-Baselinewert
bleibt **193/293 = 65,87 %** mit 100 % Abdeckung.
Keine der vier einfachen, *tripellokalen* Rangfusionen
verbessert diese Referenz. Die vielen Paargleichstände
der Zweierkombinationen erklären den niedrigen
Gesamtnenner-Erfolg; Quote auf nur vorhergesagten
Fällen darf nicht isoliert verglichen werden.

**Keine Kalibrierung/Optimierung aus diesen
Ergebnissen.** Diese post-hoc MTT-Fusionsexperimente
sind weder eine globale Song-Cosine-Kalibrierung
noch eine unabhängige Validierung oder ein
Lyrion-Übergangstest. Vollständige Rechenschritte,
Gleichstands-/Coverageanalyse, Paardifferenzen,
Caveats und Folgeexperimente:
[Fixed-Rank Fusion Research Results](similarity-fixed-rank-fusion-research-2026-10-21.md).
Das reproduzierbare, nur aggregierte
[GitHub-Artefakt](https://github.com/chrober/bliss-mood-poc/actions/runs/39619708040/artifacts/12354537538)
enthält die Ergebnisberichte v1, v2 und
das synthetische Paritätsprotokoll.

## FMA-Small katalogbereinigte VALIDATION: eigener Embedding-A/B-Transfer (21.10.2026)

**NEU:** Das nächste kontrollierte Forschungsgate für
Repräsentation A gegen B ist implementiert:
[`scripts/evaluate_fma_embedding_ab.py`](../scripts/evaluate_fma_embedding_ab.py),
optional `--embedding-dir` im bestehenden
[`scripts/benchmark_fma_genre.py`](../scripts/benchmark_fma_genre.py),
[`research-fma-embedding-ab.yml`](../.github/workflows/research-fma-embedding-ab.yml),
synthetische Linux-/Windows-
[`tests/test_evaluate_fma_embedding_ab.py`](../tests/test_evaluate_fma_embedding_ab.py).

Die vorherige **exakte** katalogbereinigte
80-Song-VALIDATION-Kohorte wurde aus
[FMA-Run 39606850307](https://github.com/chrober/bliss-mood-poc/actions/runs/39606850307)
als SHA256 `f4a7a81c0713db7619efdba6eb3d561aa70d6d3cc812b4884793953d93b58509`
übernommen. Ferner sind die drei
Quellen-SHAs (FMA-Metadaten/Audiopaket, MTG-Katalog)
und die früheren Genre-Cosine-Maße
(P@5 0,3200; mAP@10 0,1748759921; nDCG@10
0,2985332322) **als Regressions-Gate fixiert**.
Die neu berechneten direkten 1280D- und
87D/56D-Sidecars stammen im neuen Modus aus
**demselben Encoder-Durchlauf** und werden nach
Audio-SHA, Patchzahl und Modell-/Pooling-Fingerprint
paarweise überprüft.

Jeder der 80 Künstler-distinkten Query-Tracks
vergleicht sich mit exakt denselben 79 Kandidaten;
9 pro Query haben die gleiche FMA-Obergenreklasse.
Verglichen werden Embedding-Cosine, Genre-Cosine
und Centered-Cosine sowie Mood-Cosine/Centered
als **Cross-Task-Kontrolle**. P@5, mAP@10,
nDCG@10, gemeinsame Abdeckung, Abstentions
als 0, stratifizierte gepaarte
Query-Sensitivitätsintervalle. Abhängige Kandidaten,
nur acht Genres und mögliche nicht erkannte
Trainingskatalogüberschneidungen bedeuten:
**kein unabhängiger Holdout/Populations-CI**.
Offizieller FMA-TEST bleibt strikt unberührt.
Audio und Embedding-Sidecars bleiben runner-privat,
Artefakte sind nur aggregierte Reports.

Ausführlicher Studienvertrag:
[Similarity FMA Embedding A/B](similarity-fma-embedding-ab-2026-10-21.md).
Erster Workflow:
[Research FMA 80 Validation A/B](https://github.com/chrober/bliss-mood-poc/actions/workflows/research-fma-embedding-ab.yml).
Solange nicht vollständig `PASS`: **keine neuen
numerischen Ähnlichkeitsresultate behaupten**.
Original FMA-Workflow, Original-Rust-v5-Pin und
PR #13/#17 sowie Mixer unverändert, PR #16 Draft.
Nach FMA ist DEAM Development als nächster
gepaarter Mood-Proxy vorgesehen. Noch keine
Fusion auf FMA VALIDATION optimieren.

## Verifiziert: FMA-80-Embedding A/B Transfer auf katalogbereinigter VALIDATION (21.10.2026)

**NEUER EMPIRISCHER BEFUND – älteren Abschnitt mit
`ausständig` damit überholt:**
[GitHub Actions Run 39625087310](https://github.com/chrober/bliss-mood-poc/actions/runs/39625087310)
**PASS**, [Aggregate-Artefakt 12355954718](https://github.com/chrober/bliss-mood-poc/actions/runs/39625087310/artifacts/12355954718).
Identischer eingefrorener, bereits untersuchter
FMA-Small VALIDATION-Sample-Fingerprint,
**80 Künstler-distinkte Songs**, 8 Genres mit je
10 Songs, pro Song dieselben 79 Kandidaten,
Genre-Katalogscreening (42 mögliche MTG-Overlap-
Treffer ausgeschlossen). Original FMA TEST nicht
angetastet, keine Trainings-Disjointness behauptet.
Die frühere Genre-Cosine-Referenz wurde
**exakt** reproduziert (P@5 `0,3200`,
mAP@10 `0,174876`, nDCG@10 `0,298533`).

| Gepaarte Methode | P@5 | mAP@10 | nDCG@10 | Abdeckung |
| --- | ---: | ---: | ---: | ---: |
| EffNet 1280D Song-L2 + Cosine | **0,2800** | 0,163044 | 0,282363 | 80/80 |
| Genre 87D Cosine | 0,3200 | 0,174876 | 0,298533 | 80/80 |
| Genre 87D Centered Cosine | **0,3225** | **0,178147** | **0,304271** | 80/80 |
| Mood/Theme 56D Cosine (Cross-Task) | 0,2775 | 0,150394 | 0,266065 | 80/80 |
| Mood/Theme 56D Centered Cosine (Cross-Task) | 0,2675 | 0,152847 | 0,270372 | 80/80 |

Embedding − Genre Centered P@5
= **−4,25 Prozentpunkte**, explorativer
95-%-genrestratifizierter gepaarter
Query-Resampling-Sensitivitätsbereich
**−8,76 bis +0,25 Prozentpunkte**;
wegen gemeinsam verwendeter Kandidaten und
bereits explorativ erforschter VALIDATION **kein
independentes Konfidenzintervall/Signifikanzbeweis**.

Damit ergibt sich eine **zweite andere
Aufgaben-/Dataset-Indikation** neben MTT:
das rohe nicht speziell kontrastive
EffNet-Song-Mean-Embedding schlägt die
aufgabenpassenden Genre-/Mood-Kopfvektoren
hier nicht. MTT ist Menschen-Odd-One-Out,
FMA ein **Genre-Label-Proxy**. Beide
Zahlen dürfen nicht gepoolt und nicht
als allgemeiner Produktionssieger gedeutet
werden. Details, Protokoll, Paardifferenzen
und Stage-Zeiten:
[FMA-80-Embedding-A/B-Studie](similarity-fma-embedding-ab-2026-10-21.md).

**Nächster Schritt:** DEAM-Entwicklungs-
/Validierungsvergleich für Valence/Arousal
bei identischen Clips und Modell-Provenienz
als begrenztem Mood-Proxy, anschließend
eigenständige Prüfung kontrastiver
Discogs-Modelle und neue unabhängige
menschliche Klang-/Playlist-Referenzen.
Keine zusätzlichen Fusionsgewichte an
MTT/FMA-VALIDATION optimieren.
PR #16 bleibt Draft; `main`, PR #13,
PR #17 und Lyrion-Produktivmixer unverändert.
