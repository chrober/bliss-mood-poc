# PowerShell-Skript-Konvention – direkt ausfuehrbare Chat-Beispiele

**Verbindliche Anforderung fuer diesen Projekt-Workflow (21.10.2026):**

Alle vom Assistenten an den Anwender gelieferten PowerShell-Befehle,
insbesondere mehrzeilige Test-, Build-, Audit-, Lyrion- und Git-Skripte,
werden als **vollstaendige, eigenstaendig kopierbare** Script-Bloecke im
folgenden Format ausgegeben:

~~~powershell
& {
    $ErrorActionPreference = 'Stop'

    # Konfiguration, Hilfsfunktionen, Arbeitsschritte und Pruefungen
    # stehen gemeinsam innerhalb dieses einzigen Script-Blocks.
    Write-Host 'Beispiel'
}
~~~

## Regeln

1. **Immer eine aeussere Huelle** mit dem exakten Beginn
   `& {` und dem schliessenden `}` verwenden,
   auch fuer Nachbesserungen oder einzelne PowerShell-Aktionen.
2. Bei Fehlerkorrekturen das **ganze korrigierte Skript** liefern –
   niemals nur den auszutauschenden Teil und niemals voraussetzen,
   dass der Benutzer Code aus mehreren Antworten zusammensetzt.
3. Konfiguration und vorausgesetzte Dateipfade unmittelbar am Anfang
   benennen. Das Skript soll in Windows PowerShell 5.1 und – soweit
   moeglich – PowerShell 7 verwendbar sein; bei Abweichungen explizit
   kennzeichnen.
4. Destruktive, externe oder wiederholt wirksame Aktionen erst nach
   erfolgreichen Vorabpruefungen erlauben. Fuer Queue-Schreibaktionen
   explizites Dry-Run/Apply-Verhalten und bestehende Playlist erhalten.
5. GitHub-CLI-, Python- und externe Prozessfehler pruefen
   (einschliesslich `$LASTEXITCODE`), bevor ein Erfolg gemeldet wird.
6. Eingebettete Unicode-Namen/JSON aus Netzwerkschnittstellen korrekt
   als UTF-8 behandeln. Lyrion-Player nach stabiler Player-ID statt
   nach durch fehlerhafte Zeichencodierung veraendertem Namen finden.
7. Bei JSON-RPC Lyrion extended CLI `songinfo` gibt es typischerweise
   ein `songinfo_loop` mit Feldobjekten; eine direkte
   `result.id` ist nicht die einzige moegliche Darstellung.
   Exakte Song-/URL-Zuordnung pruefen, niemals stillschweigend
   Kuenstler/Titel als Ersatz verwenden.
8. Script-Dateien im Repository, die unmittelbar per PowerShell gestartet
   werden sollen, ebenfalls als `& { ... }` formulieren.
   README oder Handover sollen diese Konvention verlinken.
9. Keine private Songliste oder persoenliche NAS-Pfade in
   oeffentliche CI-Logs uebernehmen. Fuer PR #16 bleiben
   Similarity-Untersuchungen read-only bis zu einem vom Benutzer
   ausdruecklich aktivierten Playlist-Append.

Diese Dokumentation ist unabhaengig von Modell-/DSP-/Similarity-Entscheidungen
und bleibt als Anforderung fuer kuenftige PowerShell-Antworten bestehen.
