# Standortverwaltung

Standort CRUD, Internetanbindungen als wiederholbare Unterformulare, Löschschutz bei referenzierten Objekten.

## Karten

- #295: Ampelfarben Standortübersicht korrigiert
- #307: Standorte lassen sich löschen (mit Schutz vor Datenverlust)

## Beteiligte Dateien

| Datei | Rolle |
|---|---|
| `app/web/routes_standort.py` | Standort CRUD-Routes, Internetanbindungen-Parser |
| `app/models/standort.py` | `Standort`, `Internetanbindung` Modelle |
| `app/templates/standort/form.html` | Standort-Formular mit dynamischen Anbindungs-Zeilen |
| `app/web/formular_listen.py` | `parse_unterobjekte()` für wiederholbare Unterformulare |

## Funktionsweise

### Standort-CRUD

- Anlegen unter `/auftrag/{id}/standort/neu`, Bearbeiten unter `.../standort/{sid}/bearbeiten`.
- Standorte sind alphabetisch nach Bezeichnung sortiert (#304, in `storage.py`).
- `Standort.vertraulichkeit` ist optional, neue Standorte übernehmen den Auftrag-Default.

### Internetanbindungen

- Wiederholbares Unterformular: mehrere Anbindungen pro Standort (Anbieter, Anschlussart, Bandbreite, Failover).
- `redundante_anbindung`-Feld für redundante Backup-Leitung (#362).
- Parser in `formular_listen.py::parse_unterobjekte()` liest Felder der Form `<praefix>_<feld>_<index>`.

### Löschschutz (#307)

- `POST /auftrag/{id}/standort/{sid}/loeschen` löscht den Standort.
- Hängen noch TechnikObjekte am Standort, wird das Löschen mit HTTP 409 abgelehnt.
- Blockierende Objekte werden namentlich mit Link aufgeführt.
- Kein Kaskadenlöschen, kein automatisches Umhängen -- Entscheidung liegt beim Bearbeiter.
- Schaltfläche in der Erfassungsansicht ist deaktiviert, wenn Objekte vorhanden (Tooltip nennt Anzahl).

### Ampelfarben (#295)

- Vollständig = grün, Teilweise = gelb/orange, Noch nicht erfasst/Unbekannt = grau.
- Korrigiert in `style.css` und Templates.
