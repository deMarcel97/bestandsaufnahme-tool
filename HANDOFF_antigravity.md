# Weiterarbeiten in Antigravity

Fahrplan für eine `agy`-Sitzung an diesem Projekt. Gegenstück zu
[HANDOFF_claude_code.md](HANDOFF_claude_code.md) — **beide zuerst lesen**, diese
Datei ergänzt nur, was für Antigravity eigen ist.

## Es gilt dasselbe Regelwerk

[CLAUDE.md](CLAUDE.md) ist verbindlich, unabhängig vom Werkzeug: Karte vor
Code, Branch und PR nach Karten-ID, **PR über GitHub mergen** (`gh pr merge`,
niemals über einen Integrationszweig — sonst verliert Superthread die
Verknüpfung, und das lässt sich nachträglich nicht heilen), Version an vier
Stellen anheben, jede Änderung landet lokal *und* auf GitHub *und* auf dem
Live-Server.

Ein zweites Regelwerk gibt es bewusst nicht. Eine Übergabe, die alles
wiederholt, veraltet innerhalb einer Woche — genau das war mit der
Vorgängerfassung des Claude-Code-Handoffs passiert (#317).

## Was in Antigravity anders ist

**MCP ist bereits eingerichtet.** In `~/.gemini/config/mcp_config.json` stehen
Superthread und GitHub als Server. Der dort hinterlegte Superthread-Token war
am 16.08.2026 gültig (gegen den Endpunkt geprüft, HTTP 200). Karten lassen sich
also direkt anlegen und kommentieren, ohne weiteres Zutun.

> Zum Vergleich: in Claude Code war derselbe Dienst mit einem **anderen**,
> widerrufenen Token hinterlegt und lieferte HTTP 401. Dort läuft es seit dem
> 16.08.2026 über OAuth ganz ohne Token. Wer in Antigravity auf 401 stösst,
> weiss damit, wo er zuerst schaut — und `#318` erklärt, warum der alte Token
> gesperrt wurde.

**`--print-timeout` braucht eine Zeiteinheit.**

```bash
agy --print-timeout 90s --print "…"     # richtig
agy --print-timeout 90  --print "…"     # bricht ab
```

Ohne Einheit lehnt das CLI das Flag ab. In Version 1.1.12 geschah das ohne
brauchbare Meldung, weshalb es am 15.08.2026 wie ein hängender Login aussah und
mehrere Stunden Fehlersuche gekostet hat. Seit 1.1.13 wird es sauber gemeldet.
Ein Print-Aufruf antwortet sonst in wenigen Sekunden.

**Das `venv` liegt im Hauptcheckout** und wandert nicht in Worktrees mit. Aus
einem Worktree heraus testen:

```bash
PYTHONPATH=. /Users/marcel/001_Vibe_Code/001_bestandsaufnahme_tool/venv/bin/pytest
```

## Reihenfolge der offenen Karten

Der Zuschnitt richtet sich danach, ob eine Karte eine Entscheidung von Marcel
braucht. **Karten der zweiten Gruppe gehören nicht in eine Sitzung, in der
gerade niemand mitliest** — sie enden sonst in einer Umsetzung, die anschliessend
verworfen wird.

### Ohne Rückfrage machbar

| Karte | Warum sie sich eignet |
|---|---|
| **#319** — Zahlparser verschluckt Tausenderpunkte | Klar umrissener Fehler mit Reproduktion, betroffenen Feldern und einem benannten Randfall (`"1.5"` — englisch 1,5 oder deutsch 15?). `tests/test_formular_listen.py::test_tausenderpunkt_geht_noch_verloren` hält den Ist-Zustand fest und **muss beim Beheben umgedreht werden**. |
| **#318** — `scratch/` absichern | Ein Eintrag in `.gitignore`. Die Karte begründet zugleich, warum die Historie **nicht** umgeschrieben wird; diese Entscheidung ist getroffen und nicht neu aufzurollen. |

Bei #319 lohnt der Blick auf #309: dort wurde für Auswahlfelder entschieden,
dass ein unbekannter Wert verworfen wird statt still den Datensatz zu ändern.
Die Frage, ob eine unlesbare Zahl künftig sichtbar abgelehnt statt still auf
`0.0` gesetzt wird, ist dieselbe — und in der Karte bewusst offen gelassen.

### Erst entscheiden lassen

| Karte | Was offen ist |
|---|---|
| **#311** — veraltete Template-Kopien | Nur eine Ja/Nein-Frage an Marcel: wird `Design änderung/handoff/` noch gebraucht? Danach entweder eine README hineinlegen oder löschen — beides Minuten. |
| **#314** — Offene Punkte anders sortieren | Der Kartentext lautet vollständig „das wie es aktuell ist macht keinen sinn". Ohne die gewünschte Sortierung ist das nicht umsetzbar. |
| **#315** — Cloud-Bausteine ohne Standort | Drei Entwurfsfragen in der Karte, u. a. ob der Standortbezug am Schema oder am Objekt hängt. Achtung: Objekte ohne Standort fielen bisher **stillschweigend aus dem Bericht** (`report_builder.py:120`). |
| **#312** — Konkurrenzanalyse #290 zerlegen | Ausdrücklich ein Gesprächsauftrag: pro Idee „bauen wir" / „später" / „bauen wir nicht". |

### Anschlussfragen aus #316

Beim Bau der vier neuen Erfassungsseiten offen geblieben, noch ohne Karte:

- **Beteiligte stehen nicht im Bericht.** Die Kontakte sind seit v2.7.14
  erfassbar, aber der Analysebericht führt sie nirgends auf. Gehört eine
  Ansprechpartner-Übersicht in den Kundenbericht?

## Fallstricke, die hier schon Zeit gekostet haben

Die vollständige Liste steht in
[HANDOFF_claude_code.md](HANDOFF_claude_code.md). Drei davon treffen jeden, der
ein **neues Formular** baut:

1. **Konflikterkennung (#305, #308).** Jedes Bearbeitungsformular führt den beim
   Laden gesehenen Stand als verstecktes `version`-Feld mit, der POST-Handler
   übernimmt ihn vor dem Speichern und fängt `KonfliktFehler` ab. Fehlt eine
   Hälfte der Kette, überschreiben sich zwei Benutzer stillschweigend — und ein
   `grep` nach `version` meldet trotzdem „vorhanden". Nachweisen lässt es sich
   nur, indem man zwei Benutzer wirklich durchspielt.
2. **Listen im Formular** liest `app/web/formular_listen.py::parse_unterobjekte()`.
   Nicht neu bauen. Er vergleicht gegen den Vorgabewert des Modells, weil ein
   `<select>` **immer** einen Wert mitschickt — ohne diesen Vergleich landet
   jede hinzugefügte, leer gelassene Zeile als leerer Datensatz in der Ablage.
3. **Vertraulichkeit (#310).** `VertraulichkeitsStufe.parse()` verlangt den
   Rückfallwert als Argument, weil die schützende Richtung nicht überall
   dieselbe ist: für einen Datensatz `INTERN`, für ein Exportziel `ANONYMISIERT`.

## Und die Leitplanke

Ein einziges Werkzeug für Kunden von 5 bis 1000 PCs. Neue Felder müssen für
beide Enden taugen; was für einen 5-PC-Betrieb offensichtlich belanglos ist,
gehört hinter eine `sichtbar_wenn`-Bedingung statt ins Standardformular.

Bei Fragen zu Feldabhängigkeiten und Bedienung **erst besprechen, nicht
implementieren**. Klare Fehler dürfen direkt behoben werden.
