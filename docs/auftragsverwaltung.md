# Auftragsverwaltung

Auftrag CRUD, Stammdaten, Unternehmenskontext, Status und Vertraulichkeit.

## Karten

- #283: Auftragsstatus & Vertraulichkeit editierbar
- #286: Stammdaten & Kontext visuell trennen
- #302: Grundlage "Analyse", Vertraulichkeit default "intern"
- #303: Stammdaten & Kontext als zwei Menüpunkte
- #309: Auswahlfelder serverseitig prüfen

## Beteiligte Dateien

| Datei | Rolle |
|---|---|
| `app/web/routes_auftrag.py` | Haupt-Route-Modul: Auftrag CRUD, Stammdaten, Unternehmenskontext, Bewertung auslösen |
| `app/models/auftrag.py` | Pydantic-Modelle: `Auftrag`, `Beteiligter`, `Vertrag`, `Dokumentenanforderung`, `Unternehmenskontext`, `Termine`, `Rahmenbedingungen` etc. |
| `app/web/optionen.py` | `STATUS_OPTIONS`, `GRUNDLAGE_OPTIONS`, `VERTRAULICHKEIT_OPTIONS`, `gueltiger_wert()` |
| `app/web/shared_context.py` | `build_sidebar_context()`, `aktuelle_version()` |
| `app/web/templates.py` | Gemeinsame Jinja2Templates-Instanz, `vertraulichkeit_options` als Global |
| `app/templates/auftrag/list.html` | Auftragsübersicht mit Status/Vertraulichkeit-Dropdowns |
| `app/templates/auftrag/detail.html` | Auftragsdetail |
| `app/templates/auftrag/stammdaten.html` | Stammdaten-Formular |
| `app/templates/auftrag/unternehmenskontext.html` | Unternehmenskontext-Formular |

## Funktionsweise

### Auftrag-CRUD

- Anlegen über Dialog (`/auftrag/neu`), Liste unter `/auftrag`.
- Status (`geplant`, `in_bearbeitung`, `abgeschlossen`, `pausiert`) und Vertraulichkeit (`intern`, `kundentauglich`, `anonymisiert`) sind als Dropdown direkt aus der Liste und Detailansicht umschaltbar (#283).
- `grundlage` kennt: Ausschreibung, Angebot, Analyse, Rahmenvertrag, Sonstiges (#302).

### Stammdaten vs. Unternehmenskontext (#303, #286)

- **Stammdaten** (`/auftrag/{id}/stammdaten`): Stammdaten, Auftragssteuerung, Termine.
- **Unternehmenskontext** (`/auftrag/{id}/unternehmenskontext`): Alles, was den Kunden beschreibt (betriebskritische Systeme, geplante Änderungen, IT-Reife etc.).
- Jede Seite hat einen eigenen POST-Handler, der ausschliesslich seine Felder setzt -- getrenntes Speichern ohne Datenverlust.
- Alte Adresse `/auftrag/{id}/einstellungen` leitet auf Stammdaten weiter.

### Vertraulichkeit (#302, #309, #310)

- Neue Aufträge, Standorte und Objekte sind per Default `intern` (bewusste Freigabe nötig).
- `VertraulichkeitsStufe.parse()` verlangt den Rückfallwert als Argument: für erfasste Datensätze `INTERN`, für Exportziele `ANONYMISIERT`.
- `gueltiger_wert()` in `optionen.py` prüft Auswahlfelder serverseitig; unbekannte Werte werden verworfen, nie gespeichert.

### Serverseitige Validierung (#309)

- `grundlage`, `status`, `vertraulichkeit` werden beim Speichern gegen ihre Optionslisten geprüft.
- Beim Bearbeiten ist der Rückfall der bereits gespeicherte Wert (kein Zurücksetzen auf Defaults bei fehlerhaftem POST).
- Optionslisten haben genau eine Quelle (`optionen.py`), verteilt als Jinja-Global.
