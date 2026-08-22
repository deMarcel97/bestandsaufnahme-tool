# Beteiligte & Support-Matrix

Erfassung von Support- und Notfallparametern mit Verknüpfung zu Technik-Objekten und Darstellung als Support-Matrix im Bericht.

## Karten

- #321: Support-Matrix mit Technik-Verknüpfung, Notfallkontakt & SLAs

## Beteiligte Dateien

| Datei | Rolle |
|---|---|
| `app/web/routes_beteiligte.py` | Beteiligte-Formular (GET/POST) |
| `app/models/auftrag.py` | `Beteiligter`-Modell (erweitert) |
| `app/templates/auftrag/beteiligte.html` | Beteiligte-Formular mit Objekt-Dropdown |
| `app/services/report_builder.py` | Kapitel 2 "Ansprechpartner & Support-Matrix" |
| `app/services/exporter.py` | Anonymisierungsmaskierung im Export |

## Funktionsweise

### Beteiligter-Modell (erweitert #321)

| Feld | Beschreibung |
|---|---|
| `name` | Name des Ansprechpartners |
| `rolle` | Rolle/Funktion |
| `objekt_id` | Verknüpfung zu Technik-Objekt |
| `email` | E-Mail-Adresse |
| `telefon` | Telefonnummer |
| `notfall_telefon` | Notfallnummer / 24/7 Hotline |
| `erreichbarkeit` | Service-Zeiten |
| `sla_reaktionszeit` | Vereinbarte SLA / Reaktionszeit |

### Erfassungsformular

- Dropdown zur direkten Zuweisung eines Technik-Objekts (`Typ: Bezeichnung`).
- Option `-- Allgemein / Gesamt-IT --` für nicht objektspezifische Kontakte.
- Direktlink `+ Neues Technik-Objekt anlegen` (in neuem Tab).
- Info-Hinweis bei noch fehlenden Objekten.

### Bericht

- Kapitel 2 "Ansprechpartner & Support-Matrix" mit formatierter Übersichtstabelle.
- Spalten: System/Bereich, Ansprechpartner & Rolle, Service- & Notfallkontakt, Service-Zeiten & SLA.
- Automatische Maskierung persönlicher Daten im anonymisierten Export.
