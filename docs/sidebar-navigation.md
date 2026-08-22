# Sidebar & Navigation

Scrollbare Auftrags-Sidebar, Trennung von Übersicht und Erfassung, Fortschrittsanzeige.

## Karten

- #275: "Noch nicht erfasst"-Leiste auf allen Seiten
- #306: Übersicht & Erfassung als zwei Menüpunkte
- #326: Sidebar Scrollbarkeit & kompakte Abstände
- #402: Fortschrittsanzeige korrigiert

## Beteiligte Dateien

| Datei | Rolle |
|---|---|
| `app/templates/_sidebar.html` | Shared Sidebar-Navigation |
| `app/web/shared_context.py` | `build_sidebar_context()` liefert Kontext auf allen Unterseiten |
| `app/templates/auftrag/uebersicht.html` | Übersichtsseite (Kennzahlen) |
| `app/templates/auftrag/erfassung.html` | Erfassungsseite (Standorte, Bausteine, Objekte) |
| `app/static/css/style.css` | Sidebar-Stile (Scroll, Kompakt) |
| `app/services/progress.py` | `ProgressService` für Baustein-Fortschritt |

## Funktionsweise

### Übersicht vs. Erfassung (#306)

- **Übersicht** (`/auftrag/{id}`): Vier Kennzahlen-Kacheln, Bewertungs-Dashboard.
- **Erfassung** (`/auftrag/{id}/erfassung`): Standorte, Baustein-Auswahl, erfasste Objekte.
- Trennung reduziert Rechenarbeit: `evaluator_service.evaluate_auftrag()` läuft nur auf der Übersicht.
- Nach Speichern von Objekten/Standorten: Weiterleitung zur Erfassung (nicht Übersicht).

### Sidebar-Kontext (#275)

- `build_sidebar_context()` liefert Standorte, Objekte und Fortschritt auf allen sieben Unterseiten.
- Formulare (technik/form.html, standort/form.html) binden Sidebar jetzt ebenfalls ein.
- "Noch nicht erfasst"-Chips sind klickbar und springen direkt zur Anlege-Seite.

### Scrollbarkeit & Kompaktheit (#326)

- `height: 100vh`, `max-height: 100vh`, `overflow-y: auto`, `scrollbar-width: thin`.
- Reduzierte Zeilenabstände/Paddings (5px).
- Kompakte Badges für Navigation und Baustein-Listen.

### Fortschrittsanzeige (#402)

- Sidebar-Prozentanzeige zählt alle sichtbaren Schema-Felder (nicht nur Pflichtfelder).
- Vorher: Stand sofort auf 100 % nach einem Wizard-Durchlauf (obwohl Objekttabelle "teilweise" zeigte).
- Nachher: Realistische Anzeige (~40-50 % nach einem schnellen Durchlauf).

### Navigationsreihenfolge

```
Übersicht -> Stammdaten -> Erfassung -> Beteiligte -> Verträge -> Unterlagen -> Projektrahmen
```

- "Stammdaten" vor "Erfassung" platziert (#361).
