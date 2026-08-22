# Konflikterkennung

Optimistic Concurrency: Schutz vor stillschweigendem Überschreiben bei gleichzeitigen Bearbeitungen, plus atomares Schreiben.

## Karten

- #305: Schreibvorgänge konnten Daten zerstören + Konflikterkennung
- #308: Konflikterkennung greift über die Dauer eines geöffneten Formulars

## Beteiligte Dateien

| Datei | Rolle |
|---|---|
| `app/services/storage.py` | `write_yaml_atomic()`, `KonfliktFehler`, `version`-Zähler |
| `app/main.py` | Exception-Handler für `KonfliktFehler` -> HTTP 409 |
| `app/web/shared_context.py` | `aktuelle_version()` |
| `app/templates/_konflikt_banner.html` | Konflikt-Warnbanner in Formularen |
| `app/web/routes_auftrag.py` | Version-Prüfung in POST-Handlern |
| `app/web/routes_standort.py` | Version-Prüfung in POST-Handlern |
| `app/web/routes_objekt.py` | Version-Prüfung in POST-Handlern |

## Funktionsweise

### Atomares Schreiben (#305)

- `write_yaml_atomic()` schreibt vollständig in eine Nachbardatei, erzwingt `fsync()`, benennt per `os.replace()` um (auf POSIX atomar).
- Es existiert immer entweder der alte oder der neue Stand -- niemals eine leere/abgeschnittene Datei.
- Risiko bestand unabhängig von Mehrbenutzerbetrieb.

### Optimistic Concurrency (#305, #308)

- `Auftrag`, `Standort`, `TechnikObjekt` führen einen `version`-Zähler.
- Beim Speichern: Weicht der Zähler vom Stand auf der Platte ab, hat jemand anderes zwischenzeitlich gespeichert.
- Auslösung von `KonfliktFehler` -> HTTP 409.
- Bestandsdaten ohne `version`-Feld bleiben ladbar und starten bei 1.

### Formular-Integration (#308)

- Vier Bearbeitungsformulare (Stammdaten, Unternehmenskontext, Standort, Technik-Objekt) führen den beim Laden gesehenen Stand als verstecktes `version`-Feld mit.
- POST-Handler übernehmen ihn vor dem Speichern.
- Bei Konflikt: Formular liefert sich selbst mit eingegebenen Werten und Warnbanner zurück (HTTP 409).
- Verstecktes Feld trägt den inzwischen auf der Platte liegenden Stand -> zweites Speichern überschreibt bewusst.
- Fehlt das Feld (altes Formular): bisheriges Verhalten, kein Blockieren.

### Ausnahmen

- `findings.yaml` und `massnahmen.yaml` werden als ganze Liste geschrieben: nur atomares Schreiben, keine Versionsprüfung.
- Zentrale 409-Seite in `app/main.py` als Auffangnetz für alle übrigen Speicherstellen.
