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
    $Apply = $false  # Change to $true only after a complete successful preview.

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

        Write-Host '=== SONG-IDS AUFLOESEN (QUEUE UNVERAENDERT) ==='
        $ids = [System.Collections.Generic.List[string]]::new()
        $cache = [System.Collections.Generic.Dictionary[string,string]]::new(
            [System.StringComparer]::Ordinal
        )
        $pairNumber = 0
        foreach ($pair in $pairs) {
            $pairNumber++
            Write-Host "Paar $($pairNumber):"
            foreach ($side in @('left', 'right')) {
                $key = [string]$pair.$side
                if ([string]::IsNullOrWhiteSpace($key)) {
                    throw "Leerer Pfad fuer $side in Paar $pairNumber"
                }
                if (-not $cache.ContainsKey($key)) {
                    $info = Invoke-Lyrion '0' @(
                        'songinfo', 0, 100, "url:$key", 'tags:u'
                    )
                    if ([string]$info.rescan -eq '1') {
                        throw 'Lyrion scannt noch die Bibliothek. Spaeter wiederholen.'
                    }
                    # songinfo_loop generally contains separate field objects,
                    # e.g. [{id:123},{title:"..."},{url:"..."}].
                    $foundIds = @()
                    if ($null -ne $info.id) {
                        $foundIds += [string]$info.id
                    }
                    foreach ($entry in @($info.songinfo_loop)) {
                        if ($null -ne $entry -and $null -ne $entry.id) {
                            $foundIds += [string]$entry.id
                        }
                    }
                    $foundIds = @($foundIds | Sort-Object -Unique)
                    if ($foundIds.Count -ne 1 -or
                        $foundIds[0] -notmatch '^[0-9]+$') {
                        throw (
                            "Keine eindeutige LMS-Track-ID fuer den exakten Key: $key. " +
                            "Queue unveraendert. Falls TracksV2.File von der " +
                            "LMS-URL abweicht, braucht es eine explizite Pfadabbildung."
                        )
                    }
                    $cache.Add($key, $foundIds[0])
                }
                $ids.Add($cache[$key])
                Write-Host ("  {0}: ID {1} | {2}" -f $side, $cache[$key], $key)
            }
        }

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
