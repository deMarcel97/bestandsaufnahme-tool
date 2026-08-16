# Oberflächen-Update — Referenz & Handoff

> **Hinweis (#311):** Dieses Verzeichnis enthält die Design-Referenz und UI-Vorlagen. Es wird mit dem aktuellen Stand aus `app/templates/` und `app/static/` synchron gehalten.

```
app/static/css/style.css
app/static/js/dialog.js
app/templates/base.html
app/templates/_sidebar.html
app/templates/_konflikt_banner.html
app/templates/auftrag/list.html
app/templates/auftrag/detail.html
app/templates/auftrag/erfassung.html
app/templates/auftrag/stammdaten.html
app/templates/auftrag/unternehmenskontext.html
app/templates/auftrag/beteiligte.html
app/templates/auftrag/vertraege.html
app/templates/auftrag/unterlagen.html
app/templates/auftrag/projektrahmen.html
app/templates/standort/form.html
app/templates/technik/form.html
app/templates/findings/index.html
app/templates/offene_punkte/index.html
app/templates/massnahmen/index.html
app/templates/bewertung/index.html
app/templates/export/index.html
```

`_preview.html` im Wurzelverzeichnis des Pakets ist nur die gerenderte Vorschau zum Nachschauen und gehört nicht ins Projekt.

## Gestaltung

Schrift Archivo (über Google Fonts), Rot `#ec3013` als einziger Akzent, keine abgerundeten Ecken. Struktur entsteht über Linien: 2px für Abschnittsgrenzen, 1px für Zeilen und Nebengrenzen. Light und Dark laufen weiter über `data-theme` auf `<html>` plus `localStorage`, also unverändert zur bisherigen Logik.

Ein Schema durch alle Seiten:

- **Seitenkopf** — Kleinlabel mit Projektnummer und Kunde, darunter die Überschrift, darunter eine Metazeile. Primäraktion rechts.
- **Abschnitt** — Überschrift über einer 2px-Linie, rechts optional Anzahl oder Aktion.
- **Tabelle** — Kopfzeile als Kleinlabel in Versalien, Zeilen durch 1px getrennt, Zeilenaktionen als Textlinks.
- **Formular** — `fieldset` je Themenblock, Feldbeschriftungen als Kleinlabel, Speichern in einer am unteren Rand klebenden Leiste.
- **Leerzustand** — gestrichelter Rahmen mit einem Satz, was als Nächstes zu tun ist.

## Was sich funktional ändert

- Die Auftrags-Navigation liegt jetzt in `_sidebar.html` und wird per `{% include %}` eingebunden. Sie zeigt die Anzahl offener Punkte, Findings und Maßnahmen, sofern die jeweilige Route sie im Kontext hat, und degradiert sauber, wenn nicht.
- Bausteine mit Fortschritt stehen oben, alle mit 0 % sind darunter als „Noch nicht erfasst“ zusammengefasst.
- Die bisher zehn „+ Baustein“-Buttons pro Standort sind ein Knopf „+ Gerät“ mit Auswahlmenü. Die Ziel-URLs sind identisch.
- Die drei bisherigen Inline-Modale (neuer Auftrag, manuelles Finding, neue Maßnahme) sind echte Dialoge über einem Hintergrund. Öffnen über `data-dialog-open="id"`, schließen über `data-dialog-close`, Klick auf den Hintergrund oder Escape. Die Logik liegt in `app/static/js/dialog.js`.
- Die Farbverlaufsbalken in der Bewertung sind eine fünfstufige Skala. Die Stufen entsprechen `bewertung/skala.yaml` (Kritisch bis Sehr gut).
- Erfassungsstatus erscheint als kleiner Farbpunkt statt als Textwert.
- Ab 900 px Breite klappt die Sidebar über den Inhalt, die Navigation wird zur Chip-Reihe (Tablet).

## Kompatibilität

`style.css` behält alle bisherigen Klassennamen (`.card`, `.card-title`, `.btn`, `.btn-primary`, `.btn-sm`, `.badge`, `.badge-hoch` …, `.alert`, `.form-control`, `.form-row`, `.sidebar`, `.progress-container`, `.field-highlight`) und lässt die alten CSS-Variablen (`--primary-color`, `--border-color` …) auf die neuen Werte zeigen. Eigene Templates, die noch nicht angepasst sind, brechen dadurch nicht.

Neue Klassen: `.eyebrow`, `.workspace`, `.page-head`, `.crumbs`, `.meta-line`, `.kpi-band` / `.kpi-grid` / `.kpi`, `.section-head`, `.standort`, `.fieldset` / `.fieldset-head`, `.subsection`, `.repeat-block`, `.conditional`, `.checkbox-grid`, `.form-bar`, `.dialog-backdrop` / `.dialog`, `.scale`, `.kv`, `.group` / `.subgroup`, `.total-row`, `.download-grid`, `.linkact`, `.status`, `.chip`, `.empty-state`, `.menu`, `.btn-dark`, `.btn-outline`.

## Nicht angefasst

Die Route `routes_objekt.py` liefert `bausteine_labels` nicht mit; das Technik-Formular braucht es auch nicht. Alle übrigen Kontextvariablen wurden 1:1 übernommen.
