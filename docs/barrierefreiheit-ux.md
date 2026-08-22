# Barrierefreiheit & UX

Label-Verknüpfung, Fehlerseiten, Print-Stylesheet, Dialog-UX und Warnung bei ungespeicherten Änderungen.

## Karten

- #357: Warnung bei ungespeicherten Änderungen
- #364: Form-Submit im Modal-Dialog (novalidate)
- #374: Formular-Labels mit Eingabefeldern verknüpft
- #375: Custom HTML-Fehlerseiten & Print-Stylesheet
- #403: Dialog-Buttons ausserhalb Viewport, Vorläufig-Hinweis

## Beteiligte Dateien

| Datei | Rolle |
|---|---|
| `app/static/js/unsaved-changes.js` | `beforeunload`-Event, Dirty-Flag-Warnung |
| `app/static/js/dialog.js` | Modal-Dialog-System |
| `app/templates/errors/404.html` | 404-Fehlerseite |
| `app/templates/errors/500.html` | 500-Fehlerseite |
| `app/templates/base.html` | Basis-Template (Print-CSS, JS-Includes) |
| `app/static/css/style.css` | `@media print` Stylesheet, `maxlength`-Attribute |
| `app/templates/auftrag/*.html` | Label-`for`/Input-`id`-Verknüpfungen |

## Funktionsweise

### Label-Verknüpfung (#374)

- `<label for="...">` durchgängig mit `<input id="...">` verknüpft.
- Screen-Reader-Konformität.

### Fehlerseiten (#375)

- `errors/404.html` und `errors/500.html` als benutzerfreundliche HTML-Seiten.
- Error-Handler in `app/main.py` liefern diese Templates.

### Print-Stylesheet (#375)

- `@media print` für sauberen Ausdruck und PDF-Export.
- Navigationselemente ausgeblendet.
- `maxlength`-Attribute für Textfelder (Schutz vor Layout-Bruchen).

### Dialog-UX (#364, #403)

- `novalidate`-Attribut auf Dialog-Formularen (serverseitige Validierung mit klarem Feedback).
- Lange Dialoge begrenzen Höhe, Dialog-Body scrollt intern.
- Titel und Aktions-Buttons bleiben immer sichtbar.
- Vermeidung stiller Blockaden unter Browser-Automation.

### Ungespeicherte Änderungen (#357)

- `beforeunload`-Event auf allen POST-Formularen.
- `unsaved-changes.js` setzt Dirty-Flag bei Änderung.
- Nutzer wird beim Verlassen der Seite mit ungespeicherten Änderungen gewarnt.
- Eingebunden in `base.html`.

### Favicon (#371)

- SVG-Favicon hinzugefügt.
- 404-Fehler für `/favicon.ico` behoben.
