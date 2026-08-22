# Schema-System

YAML-basierte Schemas definieren die Erfassungsstruktur für alle Baustein-Typen.

## Beteiligte Dateien

| Datei | Rolle |
|---|---|
| `schemas/*.yaml` | 16 Schema-Dateien (eine pro Baustein-Typ) |
| `app/services/schema_loader.py` | Lädt und validiert alle Schemas |
| `bewertung/kategorien.yaml` | Bewertungskategorien-Zuordnung |
| `bewertung/skala.yaml` | Bewertungsskala (5 Stufen) |

## Schema-Struktur

```yaml
typ: firewall           # Baustein-Typ (Schlüssel für Regelwerke und Formulare)
bezeichnung_anzeige: ...  # Anzeige-Format für Baustein-Bezeichnung
berichtskapitel: 4       # Kapitel im Analysebericht
standortbezug: true      # false = standortübergreifend (Cloud)
abschnitte:
  - name: ...
    felder:
      - name: hersteller
        typ: auswahl     # auswahl|text|bool|datum|liste|mehrfachauswahl|objekt_referenz
        pflicht: true
        regelrelevant: true
        vertraulichkeit: intern
        sichtbar_wenn:   # Bedingung für Einblendung
          feld: ...
          operator: gleich
          wert: ...
        werte:           # Bei auswahl/mehrfachauswahl
          - wert: fortinet
            textbaustein: "Hersteller: Fortinet"
```

## Verfügbare Schemas

| Schema | Typ | standortbezug |
|---|---|---|
| `firewall.yaml` | firewall | true |
| `switch.yaml` | switch | true |
| `access_point.yaml` | access_point | true |
| `server_virtualisierung.yaml` | server_virtualisierung | true |
| `server_cluster.yaml` | server_cluster | true |
| `vm.yaml` | vm | true |
| `storage.yaml` | storage | true |
| `backup.yaml` | backup | true |
| `backup_storage.yaml` | backup_storage | true |
| `usv.yaml` | usv | true |
| `netzwerkschrank.yaml` | netzwerkschrank | true |
| `serverraum.yaml` | serverraum | true |
| `clients.yaml` | clients | true |
| `software.yaml` | software | true |
| `m365_security.yaml` | m365_security | **false** |
| `organisation_prozesse.yaml` | organisation_prozesse | **false** |

## Feldtypen

| Typ | Beschreibung |
|---|---|
| `auswahl` | Dropdown mit festen Werten + `sonstige` Fallback |
| `text` | Freitext |
| `bool` | Ja/Nein |
| `datum` | Datumsfeld |
| `liste` | Wiederholbare Zeilen (z. B. Festplatten-Slots) |
| `mehrfachauswahl` | Checkbox-Gruppe (z. B. Sicherungsumfang) |
| `objekt_referenz` | Verweis auf anderes TechnikObjekt |

## Textbausteine

- Jeder `wert` in einem `auswahl`-Feld kann einen `textbaustein` definieren.
- Diese Textbausteine fliessen in den Analysebericht ein (`report_builder.py`).
- Bei `sonstige` wird der Freitextwert des Nutzers verwendet.

## Sichtbarkeitsbedingungen (`sichtbar_wenn`)

- Felder können bedingt eingeblendet werden: nur sichtbar, wenn ein anderes Feld einen bestimmten Wert hat.
- Auch auf Abschnitt-Ebene möglich.
- Beispiel: Hypervisor-Felder nur bei `wird_virtualisiert: ja`.
- Produktleitplanke: Felder, die für kleine Kunden irrelevant sind, gehören hinter `sichtbar_wenn` statt ins Standardformular.
