# Einzelnen ChatGPT-Chat per vollständiger URL als JSON exportieren

> **Stand: 31. Oktober 2026; in Firefox praktisch bestätigt.**  
> **Inoffizielles Verfahren mit nicht dokumentierten ChatGPT-Backend-Endpunkten.**
> OpenAI unterstützt und garantiert diese Schnittstelle nicht; sie kann sich jederzeit ändern.

## Kurzfassung: Der funktionierende Weg

Dieses Verfahren exportiert **einen bestimmten Original-Chat** aus dem angemeldeten Browser, nicht den gesamten Chatverlauf des Kontos. Die Auswahl erfolgt anhand der **Conversation-ID aus der vollständigen Chat-URL**, nicht anhand des möglicherweise mehrfach vergebenen Chat-Titels. Auch Projekt-URLs mit dem Pfad /g/.../c/... werden unterstützt.

**Voraussetzungen:** Zugriff auf den Original-Chat in der eigenen ChatGPT-Sitzung, Firefox/Chrome/Edge mit Browser-Konsole und ausreichender freier Arbeitsspeicher/Plattenplatz. Ein öffentlicher Share-Link ist kein Original-Chat und funktioniert hier nicht.

**Schritt für Schritt:**

1. Gewünschten **Original-Chat** in chatgpt.com öffnen (die Adresszeile enthält /c/ mit der Chat-ID).
2. **F12 → Konsole / Console** öffnen.
3. Im folgenden **vollständigen Code genau die Konstante CHAT_URL** durch die URL aus der Adresszeile ersetzen; der Titel ist **nicht** nötig. Die Projektpfad-Komponente darf enthalten sein. Außerhalb des angemeldeten Original-Chats ist ein bloßes Einfügen einer fremden URL nicht ausreichend.
4. Gesamten Code in die Konsole kopieren und mit Enter ausführen. Nur selbst geprüften Konsolencode ausführen; Browser können vor dem Einfügen eine Freigabe verlangen.
5. Die Seite **nicht neu laden**. Bis **=== EXPORT ABGESCHLOSSEN ===** laufen lassen. Ein zunächst angezeigtes Promise mit Zustand pending ist normal.
6. Im Browser-Downloadverzeichnis die Datei **chatgpt-conversation-<conversation-id>.json** finden; Dateigröße, JSON-Inhalt und Audit-Werte kontrollieren.

**Nur eine Zeile konfigurieren:** Die beispielhafte URL mit Nullen ist ein nicht-personenbezogener Platzhalter und **muss** vor der Ausführung gegen eine echte URL ausgetauscht werden.

## Vollständiges, praxiserprobtes JavaScript (V2)

Der Code basiert auf dem am **31.10.2026 erfolgreich ausgeführten URL-basierten V2-Exporter**. Das Abruf-, Validierungs-, Wiederanlauf- und Downloadverfahren ist unverändert; lediglich die Beispiel-URL ist anonymisiert. Das gesamte Snippet kann direkt in die Browser-Konsole kopiert werden.

```javascript
(async function chatgptSingleConversationExport() {
    "use strict";

    // ============================================================
    // KONFIGURATION: NUR DIESE URL ERSETZEN
    // ============================================================
    const CHAT_URL = "https://chatgpt.com/c/00000000-0000-0000-0000-000000000000";

    const NUM_TURNS = 1;
    const MAX_PAGES = 5000;
    const MAX_ATTEMPTS = 4;
    const REQUEST_DELAY_MS = 250;

    // ============================================================
    // URL VALIDIEREN UND CHAT IDENTIFIZIEREN
    // ============================================================
    const sourceUrl = new URL(CHAT_URL);

    if (sourceUrl.origin !== "https://chatgpt.com") {
        throw new Error("Ungueltige ChatGPT-Domain.");
    }

    function extractConversationId(url) {
        return new URL(url).pathname.match(
            /\/c\/([0-9a-f-]{36})(?:\/|$)/i
        )?.[1] ?? null;
    }

    const conversationId = extractConversationId(CHAT_URL);
    const currentId = extractConversationId(location.href);

    if (!conversationId) {
        throw new Error("Die angegebene URL enthaelt keine gueltige Chat-ID.");
    }
    if (!currentId) {
        throw new Error("Bitte den Original-Chat im Browser oeffnen.");
    }
    if (currentId !== conversationId) {
        throw new Error(
            "Die angegebene Chat-URL gehoert nicht zum aktuell geoeffneten Chat."
        );
    }

    // ============================================================
    // EXPORTSTATUS: RESUME IM SELBEN TAB (OHNE RELOAD)
    // ============================================================
    const STATE_KEY = "__chatgpt_url_export_v2";
    const existingState = window[STATE_KEY];

    if (existingState && existingState.conversationId !== conversationId) {
        throw new Error(
            "Vorhandener Exportstatus gehoert zu einem anderen Chat. " +
            "Bitte Browserseite neu laden."
        );
    }

    const state = existingState ?? {
        conversationId,
        sourceUrl: sourceUrl.href,
        pages: [],
        nextCursor: null,
        completed: false,
        running: false
    };
    window[STATE_KEY] = state;

    if (state.running) {
        console.warn("Ein Export laeuft bereits.");
        return;
    }
    state.running = true;

    const sleep = ms =>
        new Promise(resolve => setTimeout(resolve, ms));

    // ============================================================
    // BESTEHENDE CHATGPT-SITZUNG VERWENDEN
    // ============================================================
    async function getHeaders() {
        const response = await fetch("/api/auth/session", {
            credentials: "include"
        });
        if (!response.ok) {
            throw new Error(
                "ChatGPT-Sitzung nicht verfuegbar: HTTP " + response.status
            );
        }

        const session = await response.json();
        const token = session.accessToken ?? session.access_token;
        const headers = { Accept: "application/json" };

        // Nicht ausgeben oder in Exportdateien schreiben.
        if (token) {
            headers.Authorization = `Bearer ${token}`;
        }
        return headers;
    }

    // ============================================================
    // PAGINIERTER ABRUF, RETRIES BEI TEMPORAEREN FEHLERN
    // ============================================================
    async function fetchPage(headers, beforeCursor) {
        const params = new URLSearchParams({
            include_has_versions: "true",
            num_turns: String(NUM_TURNS)
        });
        if (beforeCursor) {
            params.set("before", beforeCursor);
        }

        const endpoint =
            `/backend-api/conversations/${conversationId}` +
            `/messages?${params.toString()}`;

        for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
            try {
                const response = await fetch(endpoint, {
                    credentials: "include",
                    headers,
                    cache: "no-store"
                });

                if (!response.ok) {
                    const body = await response.text();
                    const error = new Error(
                        `HTTP ${response.status}: ` + body.slice(0, 200)
                    );
                    error.retryable =
                        [429, 500, 502, 503, 504].includes(response.status);
                    throw error;
                }
                return await response.json();
            } catch (error) {
                const retryable =
                    error.retryable === true || error instanceof TypeError;
                if (!retryable || attempt === MAX_ATTEMPTS) {
                    throw error;
                }
                const delay = 1500 * Math.pow(2, attempt - 1);
                console.warn(
                    `Versuch ${attempt} fehlgeschlagen: ${error.message}. ` +
                    `Wiederholung nach ${delay} ms.`
                );
                await sleep(delay);
            }
        }
    }

    // ============================================================
    // SEITEN VALIDIEREN
    // ============================================================
    function validatePage(page) {
        if (!page || !Array.isArray(page.messages) ||
            page.messages.length === 0) {
            throw new Error("Leere oder ungueltige Nachrichtenseite.");
        }

        const info = page.page_info;
        if (!info || typeof info.has_previous_page !== "boolean") {
            throw new Error("Paginierungsinformation fehlt.");
        }
        if (info.has_previous_page && !info.start_cursor) {
            throw new Error("Start-Cursor fehlt.");
        }
        if (page.messages.some(message => !message || !message.id)) {
            throw new Error("Nachricht ohne ID gefunden.");
        }
        return info;
    }

    // ============================================================
    // ORIGINALDATEN UND SEITENMETADATEN ERHALTEN
    // ============================================================
    function buildExport() {
        const messages = [];
        const seen = new Map();
        let duplicates = 0;
        let rawRecords = 0;

        // Seiten kamen von neu nach alt; Ausgabe von alt nach neu.
        for (const page of [...state.pages].reverse()) {
            for (const message of page.messages) {
                rawRecords++;
                const previous = seen.get(message.id);

                if (previous) {
                    duplicates++;
                    if (JSON.stringify(previous) !== JSON.stringify(message)) {
                        throw new Error(
                            "Widerspruechliche Nachrichten-ID: " + message.id
                        );
                    }
                    continue;
                }
                seen.set(message.id, message);
                messages.push(message);
            }
        }

        const pageMetadata = state.pages.map((page, index) => {
            const { messages: originalMessages, ...metadata } = page;
            return {
                page_number: index + 1,
                message_count: originalMessages.length,
                first_message_id: originalMessages[0]?.id ?? null,
                last_message_id: originalMessages.at(-1)?.id ?? null,
                ...metadata
            };
        });

        return {
            export_format: "chatgpt-paginated-conversation-v2",
            source_url: sourceUrl.href,
            conversation_id: conversationId,
            messages,
            page_metadata: pageMetadata,
            local_export_audit: {
                exported_at: new Date().toISOString(),
                pages_loaded: state.pages.length,
                raw_records: rawRecords,
                unique_records: messages.length,
                duplicate_records: duplicates,
                pagination_verified:
                    state.completed &&
                    state.pages.at(-1)?.page_info
                        ?.has_previous_page === false,
                attachments_fetched_separately: false
            }
        };
    }

    // ============================================================
    // JSON-DATEI LOKAL HERUNTERLADEN
    // ============================================================
    function downloadJson(data) {
        const json = JSON.stringify(data, null, 2);
        const blob = new Blob([json], {
            type: "application/json;charset=utf-8"
        });
        const blobUrl = URL.createObjectURL(blob);
        const fileName =
            `chatgpt-conversation-${conversationId}.json`;
        const link = document.createElement("a");

        link.href = blobUrl;
        link.download = fileName;
        document.body.appendChild(link);
        link.click();
        link.remove();

        setTimeout(() => URL.revokeObjectURL(blobUrl), 60000);
        return { fileName, sizeBytes: blob.size };
    }

    // ============================================================
    // EXPORT STARTEN / FORTSETZEN
    // ============================================================
    try {
        console.log("=== CHATGPT JSON-EXPORT V2 ===");
        console.log("Quell-URL:", sourceUrl.href);
        console.log("Conversation-ID:", conversationId);

        if (state.pages.length > 0) {
            console.log(
                "Vorhandenen Export fortsetzen:",
                state.pages.length, "Seiten gespeichert."
            );
        }

        const headers = await getHeaders();
        const knownCursors = new Set(
            state.pages.map(page => page.page_info?.start_cursor)
                .filter(Boolean)
        );

        while (!state.completed) {
            if (state.pages.length >= MAX_PAGES) {
                throw new Error(
                    "Sicherheitsgrenze fuer Seiten erreicht."
                );
            }

            const started = performance.now();
            const page = await fetchPage(headers, state.nextCursor);
            const info = validatePage(page);
            const cursor = info.start_cursor;

            if (cursor && knownCursors.has(cursor)) {
                throw new Error("Wiederholter Cursor: " + cursor);
            }
            if (cursor) {
                knownCursors.add(cursor);
            }

            // Erst nach Validierung in den In-Memory-Status uebernehmen.
            state.pages.push(page);
            state.nextCursor = cursor ?? null;
            state.completed = info.has_previous_page === false;

            const rawCount = state.pages.reduce(
                (sum, page) => sum + page.messages.length, 0
            );
            const duration = Math.round(performance.now() - started);

            console.log(
                `Seite ${state.pages.length}: ` +
                `${page.messages.length} Datensaetze | ` +
                `Gesamt: ${rawCount} | ` +
                `Dauer: ${duration} ms | ` +
                `Weitere aeltere Seiten: ${info.has_previous_page}`
            );

            if (!state.completed) {
                await sleep(REQUEST_DELAY_MS);
            }
        }

        console.log("=== PAGINATION ABGESCHLOSSEN ===");
        const output = buildExport();

        if (!output.local_export_audit.pagination_verified) {
            throw new Error("Paginierung nicht vollstaendig bestaetigt.");
        }
        const download = downloadJson(output);

        console.log("=== EXPORT ABGESCHLOSSEN ===");
        console.table(output.local_export_audit);
        console.log("Dateiname:", download.fileName);
        console.log(
            "Dateigroesse:",
            (download.sizeBytes / 1024 / 1024).toFixed(2), "MiB"
        );
        console.log("Quell-URL:", output.source_url);
    } catch (error) {
        console.error("EXPORT UNTERBROCHEN:", error.message);
        console.warn("Bereits gespeicherte Seiten:", state.pages.length);
        console.warn(
            "Zur Fortsetzung dasselbe Script im selben Browser-Tab " +
            "erneut ausfuehren."
        );
    } finally {
        state.running = false;
    }
})();
```

## Was der Exporter technisch macht

- Prüft, ob CHAT_URL auf den HTTPS-Origin chatgpt.com zeigt, und vergleicht die dortige Conversation-ID mit der ID des **aktuell geöffneten** Original-Chats. Eine Projekt-ID ist zum Abruf nicht erforderlich.
- Verwendet die vorhandene Browser-Sitzung (Session-Endpunkt /api/auth/session), ohne den Sitzungstoken zu protokollieren oder in die Datei aufzunehmen.
- Ruft **nicht** zuerst die gesamte Unterhaltung ab, sondern direkt den bei langen Chats funktionierenden Endpunkt:
  `/backend-api/conversations/{conversation-id}/messages?include_has_versions=true&num_turns=1`.
- Folgt der API-Paginierung mit `before=<page_info.start_cursor>` so lange, bis `page_info.has_previous_page === false`; verhindert wiederholte Cursor und bricht bei leeren/ungültigen Seiten ab.
- Lädt sequenziell; 250 ms Pause nach jeder nicht-letzten Seite; maximal vier Versuche bei HTTP 429, 500, 502, 503, 504 oder Netzwerkfehlern (exponentielle Pausen).
- Bewahrt die vollständigen **Nachrichtenobjekte** (`id`, `author`, `content`, `metadata`, `recipient` usw.) sowie die sonstigen **Metadaten je API-Seite** auf. Gleiche Nachrichten-IDs werden dedupliziert; widersprüchliche Duplikate brechen ab.
- Hält abgerufene Seiten unter `window.__chatgpt_url_export_v2` im **RAM des aktuellen Browser-Tabs**. Nach einem Abbruch denselben Code dort erneut ausführen; nach Neuladen, Tab-Schließen oder Browser-Neustart ist dieser Zwischenstand weg. Es gibt keine automatische Persistierung auf Festplatte.
- Erst nach bestätigtem Paginierungsende erstellt das Script ein lokales JSON mit `export_format`, `source_url`, `conversation_id`, `messages`, `page_metadata` und `local_export_audit`; anschließend wird der reguläre Browser-Download ausgelöst.

### Was 'vollständig' bedeutet – und was nicht

`pagination_verified: true` bedeutet **nur**, dass die von der API angebotene Cursor-Seitenfolge bei `has_previous_page=false` endete. Es beweist nicht unabhängig, dass alle historischen Chat-Verzweigungen/Versionen gespeichert wurden. Die API kann technische Nachrichten enthalten, die im Chat-UI nicht sichtbar sind. Externe Anhänge werden **nicht** separat heruntergeladen (`attachments_fetched_separately: false`); es können nur Verweise/Metadaten vorhanden sein.

Die Reihenfolge der API-Seiten wird vor dem Zusammenführen umgekehrt. Die Nachrichten innerhalb jeder Seite werden in ihrer gelieferten Reihenfolge belassen. Das ist **keine** verifizierte Sortierung sämtlicher Branches nach Zeitstempel.

## Reproduzierter Praxistest vom 31. Oktober 2026

Bei einer sehr langen technischen ChatGPT-Projekt-Unterhaltung schlug der Standardabruf von `/backend-api/conversations/{id}` nach ungefähr 30 Sekunden mit `HTTP 500 {"detail":"Request timeout"}` fehl. Auch der nicht-paginierte Messages-Abruf mit großer Seitenanforderung war ungeeignet. Der gezielte Abruf mit `num_turns=1` lieferte dagegen HTTP 200. Auffälligkeit: `num_turns=1` begrenzt **Turns**, nicht die Anzahl einzelner API-Datensätze; aufeinanderfolgende Seiten hatten beispielsweise 366, 1, 144 und 1 Datensätze.

Der **explizit URL-basierte V2-Exporter** wurde anschließend mit einer vollständigen Projekt-Chat-URL erfolgreich erneut ausgeführt:

| Prüfkriterium | Bestätigter Wert |
| --- | ---: |
| Abgerufene API-Seiten | **64** |
| Originaldatensätze (`raw_records`) | **4.970** |
| Eindeutige Datensätze (`unique_records`) | **4.970** |
| Duplikate | **0** |
| Letzte Seite (`has_previous_page`) | **false** |
| `pagination_verified` | **true** |
| JSON-Dateigröße | **55,35 MiB** |
| JSON-Download | **angestoßen und lokal bestätigt** |
| Separater Anhang-Download | **nein** |

Diese Zahlen sind **Testbeobachtungen, keine für andere Chats zu erwartenden Sollwerte**. Aus Datenschutzgründen werden die konkrete Chat-URL, UUID, private Nachrichtentexte und die erzeugte JSON-Datei **nicht** im öffentlichen Repository hinterlegt.

## Kontrolle, Fehler und Grenzen

| Beobachtung | Bedeutung / Vorgehen |
| --- | --- |
| `Promise { <state>: "pending" }` | Normal bei asynchronem Konsolencode; erst die Abschlussmeldung zählt. |
| `=== EXPORT ABGESCHLOSSEN ===` | Exporter hat JSON zusammengestellt und Browser-Download ausgelöst; tatsächliche Datei im Downloadverzeichnis überprüfen. |
| `HTTP 500 / Request timeout` auf dem gesamten Conversation-Endpunkt | Bei sehr langen Chats beobachtet. Der V2-Exporter verwendet **direkt den paginierten Messages-Endpunkt**. |
| `EXPORT UNTERBROCHEN` | Fehler ansehen; im **gleichen unveränderten Tab** denselben Code erneut ausführen, um ab der zuletzt validierten Seite fortzufahren. |
| Wiederholter Cursor / leere Seite / fehlende ID | Export wird absichtlich abgebrochen, statt eine möglicherweise unvollständige Datei als Erfolg auszugeben. |
| Ungültige Chat-ID / falscher geöffneter Chat | CHAT_URL mit der Adresszeile des **Original-Chats** abgleichen. |
| Große Datei, Browser speichert nicht | Download-Berechtigung, freien Platz und Browser-RAM kontrollieren; bei erfolgreicher Konsole zusätzlich Datei prüfen. |
| Firefox `WEBGL_debug_renderer_info is deprecated` | Eine unabhängige Browser-/Grafik-Warnung, **kein Fehler des Export-Scripts**. |
| Öffentliche `/share/...`-URL | Nicht geeignet; dieser Exporter benötigt Zugriff auf den Original-Chat. |

**Sicherheit und Datenschutz:** Browser-Konsolencode läuft mit den Rechten der angemeldeten ChatGPT-Sitzung. Nur den hier überprüften Code und nur für eigene/berechtigte Unterhaltungen verwenden. Das Script ruft ausschließlich relative ChatGPT-Endpunkte auf und erstellt einen lokalen Browser-Download; es lädt die Inhalte **nicht** zu GitHub oder Drittservern hoch. Die erzeugte Datei kann dennoch hochsensible Prompts, Pfade, Tool-Ausgaben oder Referenzen enthalten: **niemals in dieses öffentliche Repository committen**. Für den offiziell unterstützten Export des **gesamten** Kontos steht ChatGPT → Einstellungen → Datenkontrollen → Daten exportieren zur Verfügung; das ist jedoch kein gezielter Ein-Chat-Export.

## Warum die ältere Anleitung ersetzt wurde

Der alte Ansatz rief zuerst `/backend-api/conversations/{id}` auf und fiel erst **nach erfolgreicher Antwort** auf den separaten Messages-Endpunkt zurück. Bei `HTTP 500 Request timeout` trat dieser Fallback daher nie in Kraft. Außerdem erforderte er einen unter Umständen nicht eindeutigen `expectedTitle`. Die bestätigte V2-Fassung löst **beide** Probleme: eindeutige URL/Conversation-ID und direkter, paginierter Nachrichtenabruf.
