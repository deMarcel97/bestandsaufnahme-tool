# TechnikObjekt-Erfassung

Schema-getriebene Formulare für IT-Infrastruktur-Objekte mit bedingter Sichtbarkeit, Mehrfachauswahl und Listenfeldern.

## Karten

- #296: Server-Detailfragen (standort_rack, baujahr)
- #297: "Wird virtualisiert?" als Pflichtfeld
- #298: Festplatten-Slots mit Anbindungstypen
- #299: Kommentarfeld-Position konsistent
- #354: Doppeltes Kommentarfeld entfernt

## Beteiligte Dateien

| Datei | Rolle |
|---|---|
| `app/web/routes_objekt.py` | TechnikObjekt CRUD, schema-getriebene Formularerzeugung, Duplizieren, Mehrere anlegen |
| `app/models/technik.py` | `TechnikObjekt`, `OffenerPunktItem` Modelle |
| `app/services/schema_loader.py` | Lädt `schemas/*.yaml`, validiert Felddefinitionen |
| `app/templates/technik/form.html` | Generisches, schema-getriebenes Formular-Template |
| `app/static/js/dialog.js` | Modal-Dialog-System für "Mehrere anlegen" |

## Funktionsweise

### Schema-getriebene Formulare

- Formular wird dynamisch aus `schemas/*.yaml` generiert: Abschnitte -> Felder.
- Feldtypen: `auswahl` (Dropdown), `text`, `bool`, `datum`, `liste` (wiederholbare Zeilen), `mehrfachauswahl` (Checkbox-Gruppen), `objekt_referenz`.
- `sichtbar_wenn`: Bedingte Einblendung von Feldern basierend auf anderen Feldwerten (z. B. Hypervisor-Felder nur bei "wird virtualisiert: ja").
- `pflicht`: Pflichtfelder werden serverseitig validiert.
- `regelrelevant`: Markiert Felder, die für die Rule Engine relevant sind.
- `vertraulichkeit`: Feld-spezifische Vertraulichkeitsstufe für den Export.

### Listenfelder (#298)

- Feldtyp `liste` für wiederholbare Zeilen (z. B. Festplatten-Slots mit Typ, Kapazität, Anbindungstyp).
- Anbindungstypen: `sata`, `sas`, `nvme`, `m2`, `ssd`.

### Mehrfachauswahl (#323)

- Feldtyp `mehrfachauswahl` für Checkbox-Gruppen (z. B. Sicherungsumfang bei Backup).
- Unterstützt in `schema_loader.py`, `routes_objekt.py`, `rule_engine.py`, `report_builder.py` und Web-Formularen.

### Kommentarfeld (#299, #354)

- Kommentarfeld ist konsistent als letztes Feld im jeweils letzten Abschnitt jedes Schemas.
- Das hartcodierte "Notizen"-Feld aus `technik/form.html` wurde entfernt (#354) -- jedes Schema definiert selbst ein `kommentar`-Feld.

### Duplizieren & Mehrere anlegen

- `POST /auftrag/{id}/objekt/{typ}/{oid}/duplizieren` -- kopiert ein Objekt.
- `Mehrere anlegen` öffnet einen Modal-Dialog für Batch-Erfassung.

### Objekt-Referenzen

- Feldtyp `objekt_referenz` für Objekt-zu-Objekt-Verknüpfungen (z. B. VM -> Host/Cluster).
- VMs werden im Bericht unter ihrem Host/Cluster gruppiert.
