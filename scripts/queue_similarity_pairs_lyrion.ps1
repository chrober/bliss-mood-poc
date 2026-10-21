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

        # Direct 1-song lookup from the actual Raspberry Pi music-root path.
        # songinfo url: expects Lyrion's FULL file URL, not TracksV2.File.
        $MusicRoot = [string]$env:LYRION_MUSIC_ROOT
        if ([string]::IsNullOrWhiteSpace($MusicRoot)) {
            throw 'LYRION_MUSIC_ROOT fehlt (Beispiel: /mnt/music).'
        }
        $MusicRoot = $MusicRoot.Replace('\', '/').TrimEnd('/')
        if (-not $MusicRoot.StartsWith('/')) {
            throw 'LYRION_MUSIC_ROOT muss ein absoluter Linux-Pfad sein.'
        }

        function Test-ExactLyrionFileUrl {
            param([string]$FoundUrl, [string]$ExpectedPath)
            # CLI URLs can be encoded multiple times; do not compare by title.
            $url = $FoundUrl
            for ($depth = 0; $depth -lt 5; $depth++) {
                if ($url.StartsWith('file:///', [System.StringComparison]::OrdinalIgnoreCase)) {
                    $path = $url.Substring(7)
                    if ($path.Equals($ExpectedPath, [System.StringComparison]::Ordinal)) {
                        return $true
                    }
                }
                $next = [System.Uri]::UnescapeDataString($url)
                if ($next -ceq $url) { break }
                $url = $next
            }
            return $false
        }

        function Get-LyrionFileUrlCandidates {
            param([string]$FullPath)
            $escapedSegments = @(
                $FullPath.Split('/') | ForEach-Object {
                    [System.Uri]::EscapeDataString($_)
                }
            )
            $encoded = 'file://' + ($escapedSegments -join '/')
            $double = $encoded.Replace('%', '%25')
            $raw = 'file://' + $FullPath
            $urls = [System.Collections.Generic.List[string]]::new()
            foreach ($u in @($encoded, $double, $raw)) {
                if (-not $urls.Contains($u)) { $urls.Add($u) }
            }
            return $urls.ToArray()
        }

        Write-Host '=== GEZIELTE SONGINFO-ABFRAGEN (KEIN GESAMTKATALOGSCAN) ==='
        Write-Host "Musikroot auf dem Pi: $MusicRoot"
        $ids = [System.Collections.Generic.List[string]]::new()
        $cache = [System.Collections.Generic.Dictionary[string,string]]::new(
            [System.StringComparer]::Ordinal
        )
        $pairNumber = 0
        foreach ($pair in $pairs) {
            $pairNumber++
            Write-Host "Paar $($pairNumber):"
            foreach ($side in @('left', 'right')) {
                $key = ([string]$pair.$side).Replace('\', '/')
                if ([string]::IsNullOrWhiteSpace($key) -or
                    $key.StartsWith('/') -or $key -match '(^|/)\.\.?(/|$)') {
                    throw "Ungueltiger relativer CSV-Schluessel ($side): $key"
                }
                if (-not $cache.ContainsKey($key)) {
                    $pathOnPi = $MusicRoot + '/' + $key
                    $validIds = [System.Collections.Generic.HashSet[string]]::new(
                        [System.StringComparer]::Ordinal
                    )
                    foreach ($candidateUrl in @(Get-LyrionFileUrlCandidates $pathOnPi)) {
                        $info = Invoke-Lyrion '0' @(
                            'songinfo', 0, 100, ('url:' + $candidateUrl), 'tags:u'
                        )
                        if ([string]$info.rescan -eq '1') {
                            throw 'Lyrion scannt die Bibliothek; spaeter erneut versuchen.'
                        }
                        $responseIds = [System.Collections.Generic.List[string]]::new()
                        $responseUrls = [System.Collections.Generic.List[string]]::new()
                        if ($null -ne $info.id) { $responseIds.Add([string]$info.id) }
                        if ($null -ne $info.url) { $responseUrls.Add([string]$info.url) }
                        foreach ($entry in @($info.songinfo_loop)) {
                            if ($null -ne $entry) {
                                if ($null -ne $entry.id) { $responseIds.Add([string]$entry.id) }
                                if ($null -ne $entry.url) { $responseUrls.Add([string]$entry.url) }
                            }
                        }
                        $verified = $false
                        foreach ($u in $responseUrls) {
                            if (Test-ExactLyrionFileUrl $u $pathOnPi) {
                                $verified = $true
                                break
                            }
                        }
                        if ($verified) {
                            foreach ($songId in $responseIds) {
                                if ($songId -match '^[0-9]+$') {
                                    [void]$validIds.Add($songId)
                                }
                            }
                        }
                    }
                    if ($validIds.Count -ne 1) {
                        throw (
                            "Fuer '$key' wurden $($validIds.Count) exakte " +
                            "Lyrion-IDs gefunden (erwartet: 1). Queue unveraendert. " +
                            "Musikroot/URL-Encoding mit der LMS-Konfiguration abgleichen."
                        )
                    }
                    foreach ($songId in $validIds) {
                        $cache.Add($key, $songId)
                    }
                }
                $ids.Add($cache[$key])
                Write-Host ("  {0}: ID {1} | {2}" -f $side, $cache[$key], $key)
            }
        }
        Write-Host "Eindeutig aufgeloeste Dateien: $($cache.Count)"

        # All URL/ID lookups above completed without changing the queue.
        # The old single playlistcontrol track_id:1,2,2,3 request may
        # collapse duplicate track IDs within ONE request (seen on real LMS).
        # Append one numeric ID per request to preserve all CSV positions.
        function Get-QueueTailIds {
            param([int]$RequestedPositions)
            $tracksResult = Invoke-Lyrion $PlayerId @('playlist', 'tracks', '?')
            if ([string]$tracksResult._tracks -notmatch '^[0-9]+$') {
                throw 'Lyrion liefert keine gueltige Queue-Laenge.'
            }
            $total = [int]$tracksResult._tracks
            $length = [Math]::Min($total, $RequestedPositions)
            if ($length -eq 0) {
                return @{ total = 0; ids = @() }
            }
            $start = $total - $length
            $status = Invoke-Lyrion $PlayerId @(
                'status', $start, $length, 'tags:u'
            )
            $tail = @($status.playlist_loop | Where-Object { $null -ne $_ })
            if ($tail.Count -ne $length) {
                throw "Lyrion status lieferte $($tail.Count) statt $length Queue-Eintraege."
            }
            $readIds = [System.Collections.Generic.List[string]]::new()
            foreach ($item in $tail) {
                if ([string]$item.id -notmatch '^[0-9]+$') {
                    throw 'Status ohne numerische Track-ID; sichere Queue-Pruefung nicht moeglich.'
                }
                $readIds.Add([string]$item.id)
            }
            return @{ total = $total; ids = $readIds.ToArray() }
        }

        function Test-QueueTailMatches {
            param([string[]]$Actual, [string[]]$Expected)
            if ($Expected.Count -gt $Actual.Count) { return $false }
            $startIndex = $Actual.Count - $Expected.Count
            for ($j = 0; $j -lt $Expected.Count; $j++) {
                if ($Actual[$startIndex + $j] -cne $Expected[$j]) {
                    return $false
                }
            }
            return $true
        }

        $shuffle = Invoke-Lyrion $PlayerId @('playlist', 'shuffle', '?')
        if ($null -eq $shuffle._shuffle) {
            throw 'Shuffle konnte nicht geprueft werden; keine Queue-Aenderung.'
        }
        if ([string]$shuffle._shuffle -ne '0') {
            throw 'Shuffle ist aktiviert; bitte zuerst im Lyrion-Player ausschalten.'
        }

        $expected = @($ids.ToArray())
        $uniqueOrdered = [System.Collections.Generic.List[string]]::new()
        $uniqueSeen = [System.Collections.Generic.HashSet[string]]::new(
            [System.StringComparer]::Ordinal
        )
        foreach ($songId in $expected) {
            if ($uniqueSeen.Add($songId)) { $uniqueOrdered.Add($songId) }
        }
        $queueBefore = Get-QueueTailIds -RequestedPositions $expected.Count
        Write-Host '=== QUEUE-VORSCHAU ==='
        Write-Host "Bestehende Eintraege: $($queueBefore.total)"
        Write-Host "Anzuhaengende Paare: $($pairs.Count)"
        Write-Host "Gewuenschte Queue-Positionen: $($expected.Count)"
        Write-Host "Unterschiedliche Song-IDs: $($uniqueOrdered.Count)"
        if ($expected.Count -ne $uniqueOrdered.Count) {
            Write-Host 'Hinweis: Wiederholte Songs sind fuer die Paarreihenfolge beabsichtigt.'
        }

        if (-not $Apply) {
            Write-Host '=== DRY RUN: NICHTS VERAENDERT ==='
            Write-Host 'Bestehende Queue bleibt unveraendert.'
            Write-Host 'Erst nach vollstaendiger Pruefung LYRION_APPLY=true setzen.'
        }
        else {
            # Fail closed if a previous run already appended the desired
            # 16-position sequence or an older bulk request added just the
            # unique 15 IDs. IMPORTANT: never blindly retry on a thrown
            # post-append validation error.
            if (Test-QueueTailMatches -Actual $queueBefore.ids -Expected $expected) {
                throw 'Hörtest-Sequenz liegt bereits am Queue-Ende; NICHT erneut anhaengen.'
            }
            if ($uniqueOrdered.Count -lt $expected.Count -and
                (Test-QueueTailMatches -Actual $queueBefore.ids -Expected $uniqueOrdered.ToArray())) {
                throw (
                    'Alte playlistcontrol-Sammelanfuegung ist bereits am Queue-Ende ' +
                    '(Dubletten innerhalb des Aufrufs kollabiert). ' +
                    'Keine zweite Kopie angehaengt. Die vorhandene Queue kann genutzt werden.'
                )
            }
            # Also guard likely partial appends from an interrupted per-ID
            # attempt, to prevent duplicate replay from the beginning.
            for ($prefixLength = $expected.Count - 1; $prefixLength -ge 2; $prefixLength--) {
                $prefix = @($expected[0..($prefixLength - 1)])
                if (Test-QueueTailMatches -Actual $queueBefore.ids -Expected $prefix) {
                    throw (
                        "Queue-Ende entspricht bereits den ersten $prefixLength " +
                        'geplanten Eintraegen. Moegliche Teilanfuegung! ' +
                        'Vor weiteren Writes Queue manuell pruefen.'
                    )
                }
            }

            Write-Host '=== QUEUE EINZELN UND IN PAARREIHENFOLGE ERWEITERN ==='
            $previousLength = $queueBefore.total
            $completed = 0
            foreach ($songId in $expected) {
                # A single ID per CLI command avoids SQL IN-style duplicate
                # removal within one track_id:comma,list request.
                $answer = Invoke-Lyrion $PlayerId @(
                    'playlistcontrol', 'cmd:add', ('track_id:' + $songId)
                )
                if ([string]$answer.rescan -eq '1' -or
                    [string]$answer.count -ne '1') {
                    throw (
                        "Unklare Serverbestaetigung nach $completed erfolgreichen " +
                        "Anfuegungen; Queue inspizieren, KEINESFALLS blind wiederholen."
                    )
                }
                $newLength = Invoke-Lyrion $PlayerId @('playlist', 'tracks', '?')
                if ([string]$newLength._tracks -notmatch '^[0-9]+$' -or
                    [int]$newLength._tracks -ne ($previousLength + 1)) {
                    throw (
                        "Queue-Laenge nach Anfuegung nicht wie erwartet. " +
                        "Bisher $completed bestaetigt; vor erneutem Versuch Queue pruefen."
                    )
                }
                $completed++
                $previousLength++
            }

            # Read back the actual positions, not just playlistcontrol count.
            $verified = Get-QueueTailIds -RequestedPositions $expected.Count
            if ($verified.total -ne $previousLength -or
                -not (Test-QueueTailMatches -Actual $verified.ids -Expected $expected)) {
                throw (
                    '16 Songs wurden angefuegt, aber Queue-Endreihenfolge weicht ' +
                    'ab. NICHT wiederholen; Playlist pruefen.'
                )
            }
            Write-Host "=== ERFOLG: $completed Queue-Positionen in Paarreihenfolge angehaengt ==="
            Write-Host 'Auch wiederholte Songs werden mehrfach gespielt.'
            Write-Host 'Bereits bestehende Songs unveraendert; keine Wiedergabe gestartet.'
        }
    }
    finally {
        $client.Dispose()
    }
}
