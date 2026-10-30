# Einzelnen ChatGPT-Chat über die Browser-Konsole als JSON exportieren

> Stand: 30. Oktober 2026. **Inoffizielles, nicht von OpenAI unterstütztes Verfahren.**
> Es wurde beim Kontext-Handover für `Lyrion: Mood Analysis` verwendet, um **einen**
> langen Original-Chat als JSON zu sichern (in jenem Fall zwei paginierte API-Antworten).
> Die internen ChatGPT-Endpunkte und Antwortformate können sich jederzeit ändern.

## Zweck und Abgrenzung

Diese Anleitung lädt **nicht die gesamte ChatGPT-Historie** herunter. Sie exportiert
ausschließlich die aktuell im Browser geöffnete **Original-Unterhaltung**,
einschließlich der von der API zurückgegebenen Nachrichten- und Tool-Datensätze.
Sie eignet sich besonders, um einen langen technischen Chat in einer neuen
ChatGPT-Session auszuwerten und eine unvollständige Druck-PDF zu vermeiden.

- **Erforderlich:** Anmeldung bei ChatGPT und Zugriff auf den **Original-Chat**.
- **Nicht geeignet:** Öffentliche `/share/...`-Links ohne Zugriff auf das Original;
  sie verwenden eine andere ID als `/c/...`.
- **Nicht enthalten:** Automatischer separater Download der referenzierten Anhänge;
  Dateien können im JSON nur als Metadaten/Referenzen erscheinen.
- **Keine Repository-Daten:** Den persönlichen JSON-Export **niemals** committen,
  veröffentlichen oder an unberechtigte Dritte weitergeben.

## Ablauf (Firefox, Edge oder Chrome auf Windows)

1. Auf [chatgpt.com](https://chatgpt.com) anmelden und den **Original-Chat**
   direkt in der eigenen Chatliste beziehungsweise dem Projekt öffnen.
   Die Adresszeile muss eine `/c/<conversation-id>`-Komponente enthalten;
   auch Pfade wie `/g/.../c/<conversation-id>` sind möglich.
2. `F12` drücken und den Tab **Konsole / Console** öffnen.
3. Im folgenden Code ausschließlich `expectedTitle` anpassen.
   Prüfen, dass der Titel mit der geöffneten Unterhaltung übereinstimmt.
4. Den vollständigen Code in die Konsole einfügen und ausführen.
   Browser können vor dem ersten Einfügen eine Bestätigung verlangen.
   **Grundsätzlich niemals unbekannten fremden Konsolencode ausführen.**
5. Die Protokollausgabe einschließlich **EXPORT ABGESCHLOSSEN** prüfen.
   Die Datei wird über die reguläre Browser-Downloadfunktion gespeichert
   (Speicherort gemäß Browser-Einstellungen).

### Browser-Konsole: Nur den geöffneten Chat exportieren

```javascript
(async () => {
    "use strict";

    // An den exakten Titel des gewünschten ORIGINAL-Chats anpassen.
    const expectedTitle = "Similarity Forschung fortsetzen";

    const match = location.pathname.match(
        /\/c\/([0-9a-f-]{36})(?:\/|$)/i
    );
    if (!match) {
        throw new Error("Bitte den Original-Chat öffnen, keinen /share/-Link.");
    }

    const conversationId = match[1];
    const endpoint = `/backend-api/conversations/${conversationId}`;

    // Die bestehende Browser-Sitzung verwenden. Den Zugriffstoken
    // niemals in die Konsole ausgeben, kopieren oder in Dateien speichern.
    const sessionResponse = await fetch("/api/auth/session", {
        credentials: "include"
    });
    if (!sessionResponse.ok) {
        throw new Error(`Sitzung nicht abrufbar: HTTP ${sessionResponse.status}`);
    }

    const session = await sessionResponse.json();
    const token = session.accessToken ?? session.access_token;
    const headers = { Accept: "application/json" };
    if (token) headers.Authorization = `Bearer ${token}`;

    async function getJson(path) {
        const response = await fetch(path, {
            credentials: "include",
            headers,
            cache: "no-store"
        });
        if (!response.ok) {
            throw new Error(`${path}: HTTP ${response.status}`);
        }
        return response.json();
    }

    function unwrap(payload) {
        for (const part of [
            payload,
            payload?.conversation,
            payload?.data?.conversation,
            payload?.data
        ]) {
            if (part && (
                part.mapping ||
                Array.isArray(part.messages)
            )) return part;
        }
        return payload;
    }

    function hasPrevious(page) {
        return page.page_info?.has_previous_page ?? page.has_previous_page;
    }

    function beforeCursor(page) {
        return page.page_info?.start_cursor ?? page.start_cursor;
    }

    console.log("Lade ausschließlich Chat:", conversationId);

    let data = unwrap(await getJson(endpoint));

    // Je nach API-Variante enthält die erste Antwort bereits Nachrichten
    // oder sie müssen über den separaten /messages-Endpunkt geholt werden.
    if (!data.mapping && !Array.isArray(data.messages)) {
        const firstPage = unwrap(await getJson(
            `${endpoint}/messages?include_has_versions=true&num_turns=100`
        ));
        data = { ...data, ...firstPage };
    }

    const actualTitle = data.title ?? data.conversation?.title;
    if (actualTitle && actualTitle !== expectedTitle) {
        throw new Error(`Falscher Chat geöffnet: "${actualTitle}"`);
    }
    if (!actualTitle) {
        console.warn(
            "API liefert keinen Titel: geöffneten Original-Chat manuell prüfen."
        );
    }

    let pagesLoaded = 1;
    let paginationVerified = false;

    if (Array.isArray(data.messages)) {
        const pages = [data.messages];
        const seenCursors = new Set();
        let current = data;

        // Neuere ChatGPT-Antworten können ältere Nachrichtenseiten
        // über before=<start_cursor> nachliefern.
        while (hasPrevious(current) === true) {
            const before = beforeCursor(current);
            if (!before || seenCursors.has(before)) {
                throw new Error("Paginierung fehlt oder läuft im Kreis.");
            }
            seenCursors.add(before);

            current = unwrap(await getJson(
                `${endpoint}/messages?include_has_versions=true` +
                `&num_turns=100&before=${encodeURIComponent(before)}`
            ));

            if (!Array.isArray(current.messages) ||
                current.messages.length === 0) {
                throw new Error("Leere/ungültige Nachrichtenseite.");
            }

            pages.unshift(current.messages);
            pagesLoaded += 1;
            console.log("Seite geladen:", pagesLoaded);

            if (pagesLoaded > 500) {
                throw new Error("Sicherheitsgrenze: mehr als 500 Seiten.");
            }
        }

        if (hasPrevious(current) !== false) {
            throw new Error(
                "Paginierung nicht nachweislich vollständig; kein Export."
            );
        }

        // Eventuelle Seitenüberlappungen anhand vorhandener IDs entfernen.
        const seenIds = new Set();
        data.messages = pages.flat().filter(item => {
            const id = item.id ?? item.message?.id;
            if (!id) return true;
            if (seenIds.has(id)) return false;
            seenIds.add(id);
            return true;
        });
        paginationVerified = true;
    }
    else if (data.mapping && typeof data.mapping === "object") {
        if (hasPrevious(data) === true) {
            throw new Error(
                "Legacy-Mapping weist weitere Seiten aus; kein Teil-Export."
            );
        }
        // Eine Mapping-Antwort ohne expliziten Paginierungsindikator
        // ist nicht beweisbar vollständig.
        paginationVerified = hasPrevious(data) === false;
        if (!paginationVerified) {
            console.warn(
                "Mapping ohne Paginierungsbestätigung: Vollständigkeit unklar."
            );
        }
    }
    else {
        throw new Error("Unbekanntes API-Nachrichtenformat; kein Export.");
    }

    const records = Array.isArray(data.messages)
        ? data.messages.length
        : Object.keys(data.mapping).length;

    // Nur lokale Audit-Metadaten – keine Behauptung über externe Anhänge.
    const output = {
        ...data,
        local_export_audit: {
            conversation_id: conversationId,
            pages_loaded: pagesLoaded,
            records,
            pagination_verified: paginationVerified,
            attachments_fetched_separately: false
        }
    };

    const json = JSON.stringify(output, null, 2);
    const blobUrl = URL.createObjectURL(
        new Blob([json], { type: "application/json;charset=utf-8" })
    );
    const safeName = expectedTitle
        .replace(/[<>:"/\\|?*\x00-\x1f]/g, "_")
        .trim() || "chatgpt-conversation";

    const link = document.createElement("a");
    link.href = blobUrl;
    link.download = `${safeName}.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(blobUrl), 60000);

    console.log("=== EXPORT ABGESCHLOSSEN ===");
    console.log("Titel:", actualTitle ?? "(nicht von API geliefert)");
    console.log("Datensätze:", records);
    console.log("Seiten:", pagesLoaded);
    console.log("Pagination verifiziert:", paginationVerified);
    console.log("JSON-Zeichen:", json.length);
})().catch(error => {
    console.error("EXPORT FEHLGESCHLAGEN:", error.message);
});
```

**Die Datei wird erst nach erfolgreichem Datenabruf erzeugt.**
`pagination_verified: true` bedeutet lediglich, dass die API für den
verwendeten Nachrichten-Endpunkt das Ende der Seitenfolge bestätigt hat.
Es garantiert weder die Präsenz sämtlicher historischer/verzweigter
Nachrichten noch den vollständigen Download von Anhängen.

## Vollständigkeit und Inhalt kontrollieren

1. Die Ausgabe `EXPORT ABGESCHLOSSEN` und die tatsächliche Größe der
   heruntergeladenen JSON-Datei prüfen. Ein `Promise { pending }` unmittelbar
   nach dem Einfügen ist **noch kein** Ergebnis.
2. In der Datei müssen `messages` (Array) oder `mapping` (Objekt)
   mit den erwarteten Gesprächsdaten vorhanden sein.
3. Anfang und Ende des Verlaufs mit dem Original-Chat vergleichen,
   insbesondere die letzten Benutzeranweisungen und Antworten.
4. Eine reine Zahl der API-Einträge ist **nicht** die Anzahl sichtbarer
   Gesprächsrunden: Tool-Aufrufe, Zwischenzustände und andere technische
   Records können zusätzlich enthalten sein.
5. Im Fall einer unterbrochenen oder fehlgeschlagenen ChatGPT-Nachricht
   können zuletzt eingegebene Texte fehlen, obwohl die Paginierung der
   gespeicherten API-Daten vollständig ist.
6. Große JSON-Dateien eher maschinell auswerten als in einem Texteditor
   komplett öffnen. JSON kann sensible Namen, Pfade, Prompts,
   Dateireferenzen oder sonstige private Inhalte enthalten.

## Bekannte Fehler

| Symptom | Ursache / Vorgehen |
| --- | --- |
| `HTTP 403` bei `curl.exe https://chatgpt.com/backend-api/share/...` | Der öffentliche Share-Endpunkt verweigert dem externen HTTP-Client den Zugriff; nicht dieselbe Anfrage endlos wiederholen. |
| `HTTP 404` bei `/backend-api/conversation/<id>` | Dieser **Singular**-Pfad war für den betreffenden Chat nicht verwendbar. Im erfolgreichen Verfahren wurde `/backend-api/conversations/<id>` (**Plural**) verwendet. Keine Garantie für künftige Versionen. |
| `ConvertFrom-Json: Ungültiger JSON-Primitiv` | Häufig wurde eine HTML-Fehlerseite statt JSON gespeichert. HTTP-Status und Content-Type prüfen, bevor geparst wird. |
| `Original-Chat öffnen` | Aktuelle Browser-URL ist ein `/share/...`-Link oder enthält keine `/c/...`-ID. |
| `Sitzung nicht abrufbar`, `401`, `403`, `404` | Anmeldung, Zugriffsrechte und aktuelle API prüfen. Das Verfahren kann durch ChatGPT-Änderungen unbrauchbar werden. |
| `Paginierung ...` | Keine vollständig nachvollziehbare Seitenfolge; Script bricht zur Vermeidung eines scheinbar vollständigen Exports ab. |
| PDF/Drucken enthält leere Antworten | Lange ChatGPT-Seiten können beim Drucken/Markieren nur teilweise geladen oder virtualisiert sein. JSON bevorzugen. |

## Sicherheit und Datenschutz

- **Nur selbst geprüften JavaScript-Code** in der Browser-Konsole ausführen.
  Konsolencode läuft mit den Rechten deiner angemeldeten Browser-Sitzung.
- Dieses Beispiel sendet seine Anfragen nur an den aktuellen
  `chatgpt.com`-Origin und löst den Download lokal über den Browser aus.
  Es überträgt den Export nicht an GitHub oder fremde Server.
- Der Code liest einen Sitzungstoken nur für die authentifizierten
  ChatGPT-Anfragen; er gibt den Token nicht aus und schreibt ihn nicht
  in die JSON-Datei.
- Private Chat-Exporte **nicht** in dieses öffentliche Forschungs-Repository
  einchecken. Für ein neues ChatGPT-Projekt nur gezielt benötigte,
  autorisierte Dateien bereitstellen.
- Für einen offiziell unterstützten Komplett-Export stattdessen die
  ChatGPT-Kontoeinstellung **Datenkontrollen → Daten exportieren** verwenden.
  Das ist jedoch kein gezielter Ein-Chat-Export.

## Hintergrund und Reproduzierbarkeit

Das ursprüngliche Problem betraf einen sehr langen Lyrion-Forschungs-Chat:
PDF und `Strg+A`-Kopien enthielten teilweise nur virtualisierte
Webseiteninhalte. Ein früherer `curl.exe`-Abruf des Share-Links ergab
`HTTP 403`; der direkte Singular-Endpunkt ergab `HTTP 404`.
Die oben dokumentierte Plural-/Messages-Variante ermöglichte dagegen
den gezielten JSON-Export mit paginierten Nachrichten, ohne alle Chats
des Kontos abzurufen.

Diese Anleitung ist bewusst unabhängig von konkreten Chat-IDs,
privaten Chat-Inhalten und benutzerspezifischen Windows-Pfaden.
