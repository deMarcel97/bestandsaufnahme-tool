# Massnahmenkatalog

Massnahmen CRUD mit zweiachsiger Priorisierung (Kosten x Dringlichkeit) und Förderprogramm-Metadaten.

## Karten

- #322: Dringlichkeitsachse und Förderprogramm

## Beteiligte Dateien

| Datei | Rolle |
|---|---|
| `app/web/routes_massnahmen.py` | Massnahmen-Liste, Erstellung, Kosten-Bearbeitung, Löschen |
| `app/models/massnahme.py` | `Massnahme`-Modell |
| `app/templates/massnahmen/index.html` | Massnahmenkatalog-Tabelle |

## Funktionsweise

### Massnahme-Modell

| Feld | Beschreibung |
|---|---|
| `id` | Eindeutige ID |
| `bezeichnung` | Titel der Massnahme |
| `findings[]` | Verknüpfte Findings |
| `stufe` | Prioritätsstufe 1-3 |
| `investitionskosten` | Einmalige Kosten |
| `monatliche_kosten` | Wiederkehrende Kosten |
| `zeitaufwand` | Geschätzter Aufwand |
| `prioritaet` | Erste Priorisierungsachse (Kosten) |
| `dringlichkeit` | Zweite Priorisierungsachse: `hoch`, `mittel`, `niedrig` |
| `foerderprogramm` | Optionale Metadaten (z. B. "Mittelstand Digital", "BSI-Förderung") |
| `status` | Umsetzungsstatus |
| `kosten_quelle` | Quellenangabe für Kosten |

### Zweiachsiges Modell (#322)

- **Priorität** (Kosten-Achse): Stufe 1-3.
- **Dringlichkeit** (Zeit-Achse): hoch/mittel/niedrig.
- Analog DIN SPEC 27076: zweiachsige Priorisierung ermöglicht differenziertere Entscheidungen.

### Export

- Markdown-Export (`export_massnahmenkatalog_md`).
- CSV-Export (`export_massnahmenkatalog_csv`).
- Beide inkl. `dringlichkeit` und `foerderprogramm`.
