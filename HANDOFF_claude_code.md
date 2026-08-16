# Übergabe an eine neue KI-Sitzung

Diese Datei ist der Einstieg, wenn eine Sitzung neu beginnt — im Terminal
(`claude`), in der Desktop-App oder mit einem anderen Werkzeug.

Wer in **Antigravity** (`agy`) arbeitet, liest zusätzlich
[HANDOFF_antigravity.md](HANDOFF_antigravity.md): dort stehen die Eigenheiten
dieser Umgebung und eine Reihenfolge der offenen Karten, getrennt nach „ohne
Rückfrage machbar" und „braucht erst eine Entscheidung".

**Sie wiederholt bewusst nicht, was anderswo steht.** Arbeitsregeln stehen in
[CLAUDE.md](CLAUDE.md), das Projekt in [README.md](README.md), die Historie in
[CHANGELOG.md](CHANGELOG.md), der Aufgabenstand auf dem Superthread-Board. Eine
Übergabe, die all das dupliziert, veraltet innerhalb einer Woche — genau das war
mit der Vorgängerfassung passiert (#317).

## Zuerst lesen

1. **[CLAUDE.md](CLAUDE.md)** — die verbindlichen Arbeitsregeln: Karte vor Code,
   Benennung nach Karten-ID, PR über GitHub mergen, Version an vier Stellen
   bumpen, lokal *und* GitHub, bei UX-Fragen erst besprechen.
2. **Superthread-Board „Bestandsaufnahme-Tool"** (space_id 6, board_id 15) —
   der tatsächliche Aufgabenstand. Die Karten tragen die Begründungen; die
   Kommentare „Lösungsweg" und „Lösung" halten fest, warum etwas so gebaut wurde.
3. **[README.md](README.md)** für den Aufbau, **[TODO.md](TODO.md)** für die
   grösseren strategischen Fragen.

## Wo gearbeitet wird

Der laufende Dev-Server bedient **ausschliesslich den Hauptcheckout**
`/Users/marcel/001_Vibe_Code/001_bestandsaufnahme_tool`, niemals eine Kopie unter
`.claude/worktrees/*`. Wer in einem Worktree arbeitet, sieht seine Änderung im
Browser erst nach dem Merge nach `main` und einem `git pull` im Hauptcheckout.

```bash
PYTHONPATH=. venv/bin/pytest       # muss vor jedem PR grün sein
venv/bin/python run.py             # Dev-Server, Port 8000, reload aktiv
```

Das `venv` liegt im Hauptcheckout und wird von Worktrees nicht mitgeliefert.

Zum Live-Server siehe [CLAUDE.md](CLAUDE.md) — Adressen stehen in
`deploy/server.local.env` und bewusst nicht im Repo, weil dieses öffentlich ist.
**Ausrollen gehört zu jeder neuen Version dazu**, nicht nur bei grossen
Änderungen.

## Architektur in fünf Sätzen

Alles ist schema-getrieben, es gibt keinen Code pro Objekttyp. Ein Baustein ist
eine YAML-Datei in `schemas/` (Formularfelder) plus eine in `rules/`
(Risikoregeln) — eine neue Datei dort genügt, kein Registry-Eintrag. Sämtliche
Technik-Objekte teilen sich ein Modell (`app/models/technik.py`), die Felder
landen in `daten`. Bedingte Sichtbarkeit über `sichtbar_wenn`, serverseitig
nachbereinigt in `routes_objekt.py::_ist_sichtbar`, damit ausgeblendete Werte
nicht als Karteileichen gespeichert werden. Erfasst wird nach `data/` als YAML,
ohne Datenbank.

## Fallstricke, die schon Zeit gekostet haben

- **Konflikterkennung (#305, #308):** Formulare führen den beim Laden gesehenen
  Stand als verstecktes `version`-Feld mit; die POST-Handler übernehmen ihn vor
  dem Speichern. **Neue Bearbeitungsformulare müssen das mitmachen**, sonst
  überschreiben sich zwei Benutzer wieder stillschweigend.
- **Vertraulichkeit (#310):** `VertraulichkeitsStufe.parse()` verlangt den
  Rückfallwert als Argument, weil die schützende Richtung nicht überall dieselbe
  ist — für einen Datensatz `INTERN`, für ein Exportziel `ANONYMISIERT`.
  `ziel_vertraulichkeit` ist keine optionale Angabe mehr.
- **Tote Modellfelder (#316):** Mehrere Felder in `app/models/auftrag.py` werden
  vom Bericht gelesen, lassen sich aber durch kein Formular füllen. Wer dort
  etwas erwartet, sucht vergeblich.
- **Veraltete Kopien:** `Design änderung/handoff/` enthält eingefrorene
  Template-Stände, die nicht mehr dem Live-Code entsprechen (#311).

## Übergabe zwischen Sitzungen

Der Gesprächsverlauf einer Sitzung wandert **nicht** mit — er liegt unter
`~/.claude/projects/<pfad-slug>/`, und der Slug enthält das Arbeitsverzeichnis.
Eine Sitzung aus einem Worktree taucht deshalb im Hauptcheckout nicht auf.
Übertragbar sind: diese Datei, die Karten auf dem Board und die Projektnotizen
unter `~/.claude/projects/-Users-marcel-001-Vibe-Code-001-bestandsaufnahme-tool/memory/`.
Wer Entscheidungen festhalten will, schreibt sie als Kommentar an die Karte —
dort findet die nächste Sitzung sie.
