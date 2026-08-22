# Unterlagen

Erfassung angeforderter Dokumentation mit Status.

## Karten

- #316: Vier neue Erfassungsseiten (Unterlagen)

## Beteiligte Dateien

| Datei | Rolle |
|---|---|
| `app/web/routes_unterlagen.py` | Unterlagen-Formular (GET/POST) |
| `app/models/auftrag.py` | `Dokumentenanforderung`-Modell |
| `app/templates/auftrag/unterlagen.html` | Unterlagen-Formular |
| `app/web/formular_listen.py` | `parse_unterobjekte()` |

## Funktionsweise

### Dokumentenanforderung-Modell

| Feld | Beschreibung |
|---|---|
| `bezeichnung` | Dokumentname |
| `status` | Status (angefordert, erhalten, fehlt) |
| `vertraulichkeit` | Vertraulichkeitsstufe |

### Erfassung

- Wiederholbares Unterformular: mehrere Dokumentenanforderungen pro Auftrag.
- Status-Tracking: angefordert, erhalten, fehlt.

### Offene Punkte

- Die Liste "Offene Punkte" verweist für Unterlagen auf die Seite "Unterlagen" (nicht mehr auf `/stammdaten`).
- `dokumentenanforderung` wurde von `progress.py` gelesen, aber kein Formular schrieb sie -- behoben in #316.
