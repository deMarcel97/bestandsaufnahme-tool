# Rule Engine

Automatische Risikoanalyse: Überprüft Erfassungsdaten gegen konfigurierbare Regelwerke in `rules/*.yaml`.

## Beteiligte Dateien

| Datei | Rolle |
|---|---|
| `app/services/rule_engine.py` | `RuleEngine`-Singleton: lädt Regeln, wertet Bedingungen aus, generiert Findings |
| `rules/*.yaml` | 18 Regelwerk-Dateien (eine pro Baustein-Typ + standort) |

## Funktionsweise

### Regelstruktur

```yaml
schema_version: 1
regeln:
  - id: usv_batterie_alt
    gilt_fuer: usv                    # Baustein-Typ
    bedingung:
      alle:                           # alle|eines (AND|OR)
        - feld: batterie_alter_jahre
          operator: groesser          # gleich|groesser|datum_vor_heute|ist_leer|...
          wert: 4
    schweregrad: hoch                  # hoch|mittel|niedrig|empfehlung
    befund: "USV-Batterie älter als 4 Jahre"
    risiko: "Ausfall bei Stromausfall"
    empfehlung: "Batterie austauschen"
    referenz: "BSI IT-Grundschutz"
    massnahme_vorschlag:
      bezeichnung: "USV-Batterie austauschen"
      beschreibung: "..."
      kosten_richtwert: 500
      aufwand_richtwert: 2
```

### Auswertung

1. `RuleEngine` lädt alle `rules/*.yaml` beim Start.
2. Für jedes `TechnikObjekt` eines Auftrags werden alle Regeln mit passendem `gilt_fuer` ausgewertet.
3. Bedingung prüft Felder in `TechnikObjekt.daten` gegen Operatoren.
4. Bei Treffer: `Finding` wird generiert mit `quelle: regel_id`, `schweregrad`, `befund`, `risiko`, `empfehlung`.
5. `massnahme_vorschlag` wird als Vorlage für den Massnahmenkatalog angelegt.

### Operatoren

| Operator | Beschreibung |
|---|---|
| `gleich` | Feldwert equals Vergleichswert |
| `groesser` | Feldwert > Vergleichswert |
| `datum_vor_heute` | Datum liegt in der Vergangenheit |
| `ist_leer` | Feld ist leer/nicht gesetzt |
| `enthaelt` | Feld enthält Wert (für Listen) |

### Schweregrade

| Grad | Bedeutung |
|---|---|
| `hoch` | Kritische Schwachstelle |
| `mittel` | Wichtiger Hinweis |
| `niedrig` | Empfehlung |
| `empfehlung` | Hinweis ohne Handlungsdruck |

### Verfügbare Regelwerke

`usv`, `access_point`, `backup`, `firewall`, `server_cluster`, `switch`, `organisation_prozesse`, `server_virtualisierung`, `vm`, `m365_security`, `standort`, `netzwerkschrank`, `backup_storage`, `clients`, `storage`, `software`, `serverraum`, `m365_lizenzmatrix`.

### Sichtbarkeitsfilter (#369)

- `sichtbar_wenn` in `progress.py::collect_offene_punkte` integriert, um irrelevante Warnungen bei inaktiven Sub-Feldern zu vermeiden.
