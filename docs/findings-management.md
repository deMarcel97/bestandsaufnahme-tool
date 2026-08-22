# Findings-Management

Automatisch (Rule Engine) und manuell generierte Befunde mit Status-Workflow und Umwandlung in Massnahmen.

## Beteiligte Dateien

| Datei | Rolle |
|---|---|
| `app/web/routes_findings.py` | Findings-Liste, manuelle Erstellung, Status-Workflow, Finding->Massnahme, Bulk-Übernahme |
| `app/models/finding.py` | `Finding`-Modell |
| `app/templates/findings/index.html` | Findings-Liste mit Status-Aktionen |

## Funktionsweise

### Finding-Modell

| Feld | Beschreibung |
|---|---|
| `id` | Eindeutige ID |
| `quelle` | `regel_id` (automatisch) oder `manuell` |
| `schweregrad` | `hoch`, `mittel`, `niedrig`, `empfehlung` |
| `befund` | Beschreibung des Befunds |
| `risiko` | Risiko-Beschreibung |
| `empfehlung` | Handlungsempfehlung |
| `status` | Workflow-Status |
| `massnahme_id` | Verknüpfte Massnahme (nach Umwandlung) |
| `standort_id` | Optional (Cloud-Bausteine) |

### Status-Workflow

```
offen -> bestätigt -> kunde_akzeptiert -> behoben
                  \-> verworfen
```

- `offen`: Neu generiert (automatisch oder manuell).
- `bestätigt`: Bearbeiter hat den Befund als relevant bestätigt.
- `verworfen`: Befund ist nicht relevant.
- `kunde_akzeptiert`: Kunde hat das Risiko akzeptiert.
- `behoben`: Massnahme umgesetzt.

### Finding -> Massnahme

- `POST /auftrag/{id}/finding/{fid}/massnahme_erzeugen` -- wandelt ein Finding in eine Massnahme um.
- Setzt `massnahme_id` am Finding und `findings[]` an der Massnahme.

### Bulk-Übernahme

- `POST /auftrag/{id}/findings/alle_uebernehmen` -- alle offenen Findings als Massnahmen übernehmen.
