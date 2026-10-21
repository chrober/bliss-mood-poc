& {
    # Complete copy/paste script. Dry-run by default.
    $ErrorActionPreference = 'Stop'
    # Set the following three environment variables in your local shell.
    # Do not commit private LAN addresses, player IDs or audio paths.
    $Server = [string]$env:LYRION_SERVER_URL
    $PlayerId = [string]$env:LYRION_PLAYER_ID
    $Csv = [string]$env:LYRION_LISTENING_CSV

    if ([string]::IsNullOrWhiteSpace($Server) -or
        [string]::IsNullOrWhiteSpace($PlayerId) -or
        [string]::IsNullOrWhiteSpace($Csv)) {
        throw 'Set LYRION_SERVER_URL, LYRION_PLAYER_ID and LYRION_LISTENING_CSV before running this script.'
    }
    $Apply = $false  # Safe default.
    if ([string]$env:LYRION_APPLY -ceq 'true') {
        $Apply = $true
    }

    Add-Type -AssemblyName System.Net.Http
    $client = [System.Net.Http.HttpClient]::new()
    $client.Timeout = [TimeSpan]::FromSeconds(20)

    function Invoke-Lyrion {
        param(
            [Parameter(Mandatory = $true)][string]$TargetId,
            [Parameter(Mandatory = $true)][object[]]$Command
        )
        # Preserve nested params [player, [CLI command, arguments...]].
        $rpcParams = [object[]]::new(2)
        $rpcParams[0] = $TargetId
        $rpcParams[1] = $Command
        $requestJson = @{
            id = 1
            method = 'slim.request'
            params = $rpcParams
        } | ConvertTo-Json -Depth 12 -Compress
        $content = [System.Net.Http.ByteArrayContent]::new(
            [System.Text.Encoding]::UTF8.GetBytes($requestJson)
        )
        $content.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse(
            'application/json; charset=utf-8'
        )
        $response = $null
        try {
            $response = $client.PostAsync($Server, $content).GetAwaiter().GetResult()
            if (-not $response.IsSuccessStatusCode) {
                throw "Lyrion HTTP status $([int]$response.StatusCode)"
            }
            $bytes = $response.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult()
            $answer = [System.Text.Encoding]::UTF8.GetString($bytes) | ConvertFrom-Json
            if ($null -ne $answer.error) {
                throw "Lyrion RPC error: $($answer.error | ConvertTo-Json -Compress)"
            }
            if ($null -eq $answer.result) {
                throw "No JSON-RPC result for: $($Command -join ' ')"
            }
            return $answer.result
        }
        finally {
            if ($null -ne $response) { $response.Dispose() }
            $content.Dispose()
        }
    }

    try {
        Write-Host '=== PLAYER-ID PRUEFEN ==='
        $players = Invoke-Lyrion '0' @('players', 0, 100)
        $player = @($players.players_loop | Where-Object {
            [string]$_.playerid -ieq $PlayerId
        })
        if ($player.Count -ne 1) {
            throw "Player ID $PlayerId nicht eindeutig gefunden."
        }
        if ([string]$player[0].connected -ne '1') {
            throw "Player $PlayerId ist offline."
        }
        Write-Host "Player-ID: $PlayerId (verbunden)"

        if (-not (Test-Path -LiteralPath $Csv -PathType Leaf)) {
            throw "CSV fehlt: $Csv"
        }
        $pairs = @(Import-Csv -LiteralPath $Csv -Encoding UTF8)
        if ($pairs.Count -lt 1 -or $pairs.Count -gt 100) {
            throw 'Erwartet werden 1 bis 100 Songpaare.'
        }
        $columns = @($pairs[0].PSObject.Properties.Name)
        if ('left' -notin $columns -or 'right' -notin $columns) {
            throw 'CSV benoetigt die Spalten left und right.'
        }

        # Exact suffix identity over URL-escaped LMS file paths. Lyrion
        # songinfo url:... requires the FULL server URL, not the relative
        # TracksV2.File key from the CSV. 'titles ... tags:u' returns id+URL.
        # Never select by album/artist/title heuristics.
        function Get-FileUrlPathVariants {
            param([string]$RawUrl)
            $variants = [System.Collections.Generic.List[string]]::new()
            if (-not $RawUrl.StartsWith('file:', [System.StringComparison]::OrdinalIgnoreCase)) {
                return $variants.ToArray()
            }
            $value = $RawUrl
            for ($decodeCount = 0; $decodeCount -le 2; $decodeCount++) {
                if (-not $value.StartsWith('file:', [System.StringComparison]::OrdinalIgnoreCase)) {
                    break
                }
                $valuePath = $value.Substring(5).Replace('\', '/')
                if (-not $variants.Contains($valuePath)) {
                    $variants.Add($valuePath)
                }
                $decoded = [System.Uri]::UnescapeDataString($value)
                if ($decoded -ceq $value) { break }
                $value = $decoded
            }
            return $variants.ToArray()
        }

        Write-Host '=== LMS-SONGKATALOG LESEN (NUR LESEND) ==='
        $uniqueKeys = [System.Collections.Generic.HashSet[string]]::new(
            [System.StringComparer]::Ordinal
        )
        foreach ($pair in $pairs) {
            foreach ($side in @('left', 'right')) {
                $key = ([string]$pair.$side).Replace('\', '/')
                if ([string]::IsNullOrWhiteSpace($key)) {
                    throw "CSV enthaelt leeren Track-Key ($side)."
                }
                if ($key.StartsWith('/') -or $key -match '(^|/)\.\.(/|$)') {
                    throw "Unerwarteter nicht-relativer CSV-Key: $key"
                }
                [void]$uniqueKeys.Add($key)
            }
        }

        # Fast exact basename prefilter; always validate ALL path components.
        $byFilename = [System.Collections.Generic.Dictionary[string,object]]::new(
            [System.StringComparer]::Ordinal
        )
        $matchesByKey = [System.Collections.Generic.Dictionary[string,object]]::new(
            [System.StringComparer]::Ordinal
        )
        foreach ($key in $uniqueKeys) {
            $name = $key.Substring($key.LastIndexOf('/') + 1)
            if (-not $byFilename.ContainsKey($name)) {
                $byFilename.Add(
                    $name, [System.Collections.Generic.List[string]]::new()
                )
            }
            $byFilename[$name].Add($key)
            $matchesByKey.Add(
                $key, [System.Collections.Generic.HashSet[string]]::new(
                    [System.StringComparer]::Ordinal
                )
            )
        }

        $batchSize = 500
        $offset = 0
        $total = $null
        $seen = [System.Collections.Generic.HashSet[string]]::new(
            [System.StringComparer]::Ordinal
        )
        while ($null -eq $total -or $offset -lt $total) {
            $page = Invoke-Lyrion '0' @(
                'titles', $offset, $batchSize, 'tags:u'
            )
            if ([string]$page.rescan -eq '1') {
                throw 'Lyrion scannt gerade; Songkatalog nicht stabil. Queue unveraendert.'
            }
            if ([string]$page.count -notmatch '^[0-9]+$') {
                throw 'Lyrion titles liefert keine gueltige Gesamtanzahl.'
            }
            $pageTotal = [int]$page.count
            if ($pageTotal -gt 250000) {
                throw 'Songkatalog groesser als das Sicherheitslimit von 250000 Eintraegen.'
            }
            if ($null -eq $total) {
                $total = $pageTotal
            }
            elseif ($total -ne $pageTotal) {
                throw 'Lyrion-Songkatalog hat sich waehrend der Abfrage geaendert.'
            }

            $rows = @($page.titles_loop | Where-Object { $null -ne $_ })
            if ($rows.Count -eq 0 -and $offset -lt $total) {
                throw "Lyrion liefert bei Offset $offset keine weiteren Songs."
            }
            foreach ($row in $rows) {
                $id = [string]$row.id
                $url = [string]$row.url
                if ($id -notmatch '^[0-9]+$') { continue }
                if ([string]::IsNullOrWhiteSpace($url)) { continue }
                [void]$seen.Add($id)
                foreach ($urlPath in @(Get-FileUrlPathVariants $url)) {
                    $lastSlash = $urlPath.LastIndexOf('/')
                    $filename = $urlPath.Substring($lastSlash + 1)
                    if (-not $byFilename.ContainsKey($filename)) { continue }
                    foreach ($key in $byFilename[$filename]) {
                        if ($urlPath.Equals($key, [System.StringComparison]::Ordinal) -or
                            $urlPath.EndsWith(
                                '/' + $key, [System.StringComparison]::Ordinal
                            )) {
                            [void]$matchesByKey[$key].Add($id)
                        }
                    }
                }
            }
            $offset += $rows.Count
            if ($offset -ge $total -or (($offset % 5000) -lt $batchSize)) {
                Write-Host "Katalog: $offset / $total Song-Eintraege gelesen"
            }
        }

        Write-Host '=== EINDEUTIGE LMS-TRACK-IDS PRUEFEN ==='
        $idByKey = [System.Collections.Generic.Dictionary[string,string]]::new(
            [System.StringComparer]::Ordinal
        )
        foreach ($key in $uniqueKeys) {
            $candidates = $matchesByKey[$key]
            if ($candidates.Count -ne 1) {
                throw (
                    "Exakte Pfadzuordnung fuer '$key' ergibt " +
                    "$($candidates.Count) LMS-Song-IDs (erwartet: 1). " +
                    "Keine Queue-Aenderung. Bei 0: Musikroot/URL-Encoding " +
                    "pruefen; bei >1: doppelte Dateipfade in Musikroots."
                )
            }
            foreach ($foundId in $candidates) {
                $idByKey.Add($key, [string]$foundId)
            }
        }

        $ids = [System.Collections.Generic.List[string]]::new()
        $pairNumber = 0
        foreach ($pair in $pairs) {
            $pairNumber++
            Write-Host "Paar $($pairNumber):"
            foreach ($side in @('left', 'right')) {
                $key = ([string]$pair.$side).Replace('\', '/')
                $ids.Add($idByKey[$key])
                Write-Host ("  {0}: ID {1} | {2}" -f $side, $idByKey[$key], $key)
            }
        }
        Write-Host "Eindeutige Tracks: $($uniqueKeys.Count); gescannte Katalog-IDs: $($seen.Count)"

        $shuffle = Invoke-Lyrion $PlayerId @('playlist', 'shuffle', '?')
        if ($null -eq $shuffle._shuffle) {
            throw 'Shuffle konnte nicht geprueft werden; keine Queue-Aenderung.'
        }
        if ([string]$shuffle._shuffle -ne '0') {
            throw 'Shuffle ist aktiviert; bitte zuerst im Lyrion-Player ausschalten.'
        }
        $queue = Invoke-Lyrion $PlayerId @('playlist', 'tracks', '?')
        Write-Host '=== QUEUE-VORSCHAU ==='
        Write-Host "Bestehende Eintraege: $($queue._tracks)"
        Write-Host "Anzuhaengende Paare: $($pairs.Count)"
        Write-Host "Anzuhaengende Tracks: $($ids.Count)"

        if (-not $Apply) {
            Write-Host '=== DRY RUN: NICHTS VERAENDERT ==='
            Write-Host 'Alle IDs pruefen; danach $Apply = $true setzen.'
        }
        else {
            # Single append preserves left/right order. Repeating this call
            # adds duplicates: inspect queue before retrying after any error.
            $result = Invoke-Lyrion $PlayerId @(
                'playlistcontrol', 'cmd:add', ('track_id:' + ($ids -join ','))
            )
            if ($null -eq $result.count -or
                [string]$result.count -notmatch '^[0-9]+$') {
                throw 'Keine gueltige count-Bestaetigung; Queue vor Wiederholung pruefen.'
            }
            if ([int]$result.count -ne $ids.Count) {
                throw "Nur $($result.count) von $($ids.Count) bestaetigt; Queue pruefen."
            }
            Write-Host "Erfolgreich $($result.count) Songs angehaengt."
            Write-Host 'Bestehende Queue erhalten; Wiedergabe nicht gestartet.'
        }
    }
    finally {
        $client.Dispose()
    }
}
