# Versionierung

Erstellung von Versions-Snapshots der Auftragsdaten.

## Beteiligte Dateien

| Datei | Rolle |
|---|---|
| `app/web/routes_versionierung.py` | Versionierung-Route (GET/POST) |
| `app/models/auftrag.py` | `VersionsEintrag`-Modell, `Auftrag.versionen` |
| `app/templates/auftrag/versionierung.html` | Versionierung-Formular |

## Funktionsweise

### Versions-Snapshot

- `POST /auftrag/{id}/versionierung` erstellt einen Snapshot der aktuellen Auftragsdaten.
- Jeder Snapshot wird als `VersionsEintrag` im `Auftrag.versionen`-Array gespeichert.
- Enthält: Zeitpunkt, Versionszähler, alle relevanten Auftragsdaten.

### Verwendung

- Dokumentation von Zuständen zu bestimmten Zeitpunkten.
- Nachvollziehbarkeit von Änderungen.
- Vergleich zwischen verschiedenen Erfassungsständen.
