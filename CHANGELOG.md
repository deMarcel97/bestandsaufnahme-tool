# Changelog

Alle nennenswerten Änderungen am IT-Bestandsaufnahme-Tool werden hier dokumentiert.

Format angelehnt an [Keep a Changelog](https://keepachangelog.com/), Versionierung nach [Semantic Versioning](https://semver.org/) (MAJOR.MINOR.PATCH): MAJOR = Breaking Change, MINOR = neue Funktionalität (abwärtskompatibel), PATCH = Bugfix.

## [2.7.6] - 2026-08-15

### Changed
- **„Übersicht & Erfassung" ist jetzt zwei Menüpunkte (#306)**: Der Sidebar-Eintrag vereinte zwei Dinge, die im Arbeitsalltag getrennt genutzt werden — den Blick auf den Stand und das eigentliche Erfassen. Neu: **„Übersicht"** (`/auftrag/{id}`, unverändert erreichbar) mit den vier Kennzahlen-Kacheln und **„Erfassung"** (`/auftrag/{id}/erfassung`, neues Template `app/templates/auftrag/erfassung.html`) mit Standorten, Bausteinauswahl und den erfassten Objekten.
- **Weniger Rechenarbeit pro Seitenaufruf (#306)**: Die gemeinsame Route lud beides zusammen. Die teure `evaluator_service.evaluate_auftrag(...)` läuft jetzt nur noch auf der Übersicht, wo die Kennzahlen sie brauchen — die Erfassungsseite kommt ohne sie aus. `build_sidebar_context()` nimmt Standorte und Objekte optional entgegen, damit dieselben Dateien nicht zweimal von der Platte gelesen werden.
- **Weiterleitung nach dem Speichern (#306)**: Wer ein Objekt oder einen Standort anlegt, bearbeitet, dupliziert oder löscht, landet jetzt auf der **Erfassung** statt auf der Übersicht — das ist der Arbeitsfluss, in dem man sich dann befindet. Die „Abbrechen"- und „Zurück"-Links der Formulare führen entsprechend dorthin zurück.

## [2.7.1] - 2026-08-15

### Added
- **Version in der Oberfläche sichtbar (#301)**: Die laufende Version steht jetzt dezent in der Kopfzeile (`v2.7.1`), sodass sich auf einen Blick prüfen lässt, welcher Stand auf dem Server tatsächlich läuft. Neue Konstante `APP_VERSION` in `app/config.py` ist dafür die Quelle — auch für den FastAPI-Titel. Neue Tests (`tests/test_version.py`) halten `app/config.py`, `pyproject.toml`, README und CHANGELOG auf derselben Nummer.
- **Gemeinsame Template-Instanz (#301)**: Die acht Route-Module legten jeweils ihre eigene `Jinja2Templates`-Instanz an — achtmal dieselbe Zeile, und keine Stelle, an der sich etwas für alle Templates hinterlegen lässt. Neu: `app/web/templates.py` mit einer gemeinsamen Instanz, über die die Version als Jinja-Global in jedem Template ankommt, ohne dass eine Route sie durchreichen muss.

### Fixed
- **`update.sh` überschrieb sich während der Ausführung (#301)**: Das Skript aktualisiert per `git pull` unter anderem sich selbst. Da Bash Skripte häppchenweise nachliest, konnte der Rest nach einer Größenänderung der Datei an der falschen Byte-Position weiterlaufen. Der gesamte Ablauf steckt jetzt in einer Funktion, die Bash vollständig einliest, bevor sie startet.
- **Laute Health-Check-Ausgabe (#301)**: Die Retry-Schleife in `install.sh`/`update.sh` gab bei jedem Fehlversuch einen `curl`-Fehler aus, obwohl die ersten Sekunden beim Hochfahren normal fehlschlagen — das las sich wie ein gescheiterter Lauf. Fehler werden während der Schleife unterdrückt; scheitert der Check wirklich, erscheinen unverändert die `journalctl`-Logs.

## [2.7.0] - 2026-08-15

### Added
- **Server-Deployment für Debian/Ubuntu (#301)**: Neues Verzeichnis `deploy/` mit idempotentem Install-Skript (`install.sh`), Update-Skript (`update.sh`), systemd-Unit und nginx-Site. Das Tool läuft damit als Dienst hinter einem Reverse Proxy statt nur als lokaler Single-User-Dev-Server. Die systemd-Unit ist gehärtet (`ProtectSystem=strict`, `NoNewPrivileges`, `ReadWritePaths` nur auf das Datenverzeichnis); uvicorn bindet ausschliesslich an `127.0.0.1`, nach aussen geht es nur über nginx.
- **Datenverzeichnis konfigurierbar (#301)**: `BESTANDSAUFNAHME_DATA_DIR` legt fest, wo Auftragsdaten liegen (`app/config.py`). Im Serverbetrieb zeigt die Variable auf `/var/lib/bestandsaufnahme-tool/data`, sodass Code-Updates die Kundendaten nicht berühren. Ohne die Variable bleibt das bisherige Verhalten (`data/` im Projektverzeichnis) unverändert.
- **Zugriffsbeschränkung ohne Login (#301)**: Da Entra-ID-SSO vorerst deaktiviert bleibt, beschränkt die nginx-Site den Zugriff auf konfigurierbare Quell-Netze (`ALLOW_CIDRS`, Default RFC1918). `install.sh` bricht bewusst ab, wenn diese Liste leer ist — das Tool soll nicht unbeabsichtigt ohne jede Zugriffskontrolle im Netz stehen.
- **Host/Port/Reload über Environment (#301)**: `run.py` liest `HOST`, `PORT` und `RELOAD` aus der Umgebung, um auf dem Server parallel zum Dienst eine Testinstanz auf einem anderen Port starten zu können. Defaults entsprechen dem bisherigen lokalen Betrieb.

### Fixed
- **Fehlendes `pillow` im Container (#301)**: Das `Dockerfile` installierte die Abhängigkeiten als handgepflegte Liste, in der `pillow` fehlte — die Diagrammerzeugung im `.docx`-Export wäre im Container fehlgeschlagen. Die Liste liegt jetzt einmalig in `requirements.txt`; `pyproject.toml` liest sie über `[tool.setuptools.dynamic]` ein, `Dockerfile` und `deploy/install.sh` installieren direkt daraus.

### Removed
- **Superthread-Hilfsskript entfernt (#301)**: `scratch/superthread-mcp.js` gelöscht — die Anbindung läuft direkt über den MCP-Server.

## [2.6.0] - 2026-08-15

### Added
- **Auftragsstatus & Vertraulichkeit editierbar (#283)**: Die Vertraulichkeit (intern, kundentauglich, anonymisiert) lässt sich nun, genau wie der Status, direkt aus der Auftragsübersicht (`list.html`) und der Detailansicht (`detail.html`) als Dropdown umschalten und wird gespeichert.
- **Server & Virtualisierung: „Wird virtualisiert?" als Pflichtfeld (#297)**: `wird_virtualisiert` (ja/nein) steht jetzt als Pflichtfeld ganz oben im Schema. Hypervisor-spezifische Fragen (Hypervisor-Typ, Version, VMs, Cluster etc.) werden via `sichtbar_wenn` nur bei „Ja" eingeblendet. Bei „Nein" wird der Server als Bare-Metal-Host behandelt.
- **Server-Detailfragen (#296)**: Schema `server_virtualisierung.yaml` um präzise Felder für `standort_rack` (Standort/Rack inkl. Höheneinheit) und `baujahr` (Baujahr / Anschaffungsjahr) erweitert.
- **Festplatten-Slots mit Anbindungstypen (#298)**: `festplatten_slots` als strukturierter `liste`-Feldtyp in `backup_storage.yaml` integriert und um Anbindungstyp `m2` (M.2) in `server_virtualisierung.yaml` und `backup_storage.yaml` erweitert.
- **Offene Punkte nach Baustein gruppieren (#287)**: Die Liste der offenen Punkte gruppiert nun nicht mehr nur nach Standort, sondern zusätzlich hierarchisch nach dem jeweiligen Baustein-Typ (Firewall, Switch, Server etc.).
- **Stammdaten & Kontext visuell trennen (#286)**: Das Auftragsbearbeitungsformular (`edit.html`) trennt Stammdaten, Auftragssteuerung und Unternehmenskontext jetzt in saubere, eigenständige Abschnitte/Fieldsets.
- **Automatische Empfehlungen bei Stammdaten-Änderungen (#284)**: Clientseitige und modellgestützte Empfehlungen im Unternehmenskontext (z. B. Hinweis auf Rufbereitschaft bei 24/7-Betrieb und Empfehlung eines IT-Dienstleisters bei fehlender IT-Abteilung).

### Fixed
- **Kommentarfeld-Position (#299)**: Das Kommentarfeld wurde über alle 13 Schemas (`schemas/*.yaml`) hinweg konsistent als letztes Feld in den jeweils letzten Abschnitt verschoben.
- **Ampelfarben Standortübersicht (#295)**: Farbskala in `app/static/css/style.css` und Templates korrigiert (Vollständig = grün, Teilweise = gelb/orange, Noch nicht erfasst/Unbekannt = grau).
- **QA-Testdaten bereinigt (#281)**: Reste von „QA Inspector Team" aus den Test-Auftragsdaten bereinigt.

## [2.5.0] - 2026-08-15

### Fixed
- **„Noch nicht erfasst"-Leiste (#275)**: Die Fortschrittsanzeige „Aktive Bausteine" und die klickbare „Noch nicht erfasst"-Chipliste in der Auftrags-Navigation erschienen bisher nur auf der Übersichtsseite eines Auftrags, weil die übrigen Routen (Stammdaten & Kontext, Offene Punkte, Findings, Maßnahmenkatalog, Bewertung, Exporte) den dafür nötigen Kontext nicht an `_sidebar.html` übergaben. Neuer gemeinsamer Helper `app/web/shared_context.py::build_sidebar_context()` liefert diesen Kontext jetzt auf allen sieben Unterseiten. Zusätzlich binden die Formulare „Neues/Objekt bearbeiten" und „Standort anlegen/bearbeiten" (`technik/form.html`, `standort/form.html`), die die Sidebar bisher gar nicht einbanden, sie jetzt ebenfalls ein — man kann so mitten in der Erfassung direkt zu einem anderen fehlenden Baustein springen, ohne erst zur Übersicht zurückzugehen.

## [2.4.0] - 2026-08-15

### Added
- **Neuer Baustein „Software"**: Ein einzelner, unabhängig aktivierbarer Baustein `software` (`schemas/software.yaml` + `rules/software.yaml`) deckt CRM, DMS (Dokumentenmanagement) und ERP als wählbare **Kategorie** ab, statt drei separate Bausteine im Baustein-Picker zu erzeugen. Nach Auswahl der Kategorie blendet sich per `sichtbar_wenn` nur das passende Anbieter-Dropdown ein (CRM/DMS/ERP-Anbieterliste).
- **Anbieter-Dropdown mit Freitext-Fallback**: Neues, wiederverwendbares Muster für Software-Hersteller-Felder — ein `auswahl`-Feld mit fester Herstellerliste plus „sonstige" und `unbekannt`, gekoppelt an ein per `sichtbar_wenn` nur bei „sonstige" eingeblendetes Freitextfeld. Dasselbe Prinzip verschachtelt sich für die Kategorie-Auswahl (Kategorie → Anbieter-Dropdown → Sonstige-Freitext). Dieses Muster ist als Vorlage für künftige Software-Hersteller-Felder gedacht.
- Kategorie DMS unterstützt zusätzlich DATEV DMS als kanzleispezifische Sonderoption (eigener Textbaustein-Hinweis auf die Zielgruppe Steuerberater/Wirtschaftsprüfer); SharePoint wurde bewusst nicht als DMS-Option aufgenommen.

### Changed
- Nutzerseitige Bezeichnung „Gerät"/„Geräte" in Templates und generierten Texten (Offene Punkte, Findings, Export-Defaults) zu „Objekt"/„Objekte" vereinheitlicht, da mit dem neuen Software-Baustein nicht mehr jedes erfasste Objekt ein physisches Gerät ist.

## [2.3.0] - 2026-08-15

### Fixed
- **Setup & Packaging (#293)**: `[tool.setuptools] packages = ["app"]` in `pyproject.toml` ergänzt, sodass `pip install -e .[dev]` auf sauberen Checkouts fehlerfrei durchläuft.
- **DOCX-Export (#292)**: `pillow>=10.0.0` in `pyproject.toml` dependencies deklariert und automatisierten Test hinzugefügt, wodurch DOCX-Chart-Rendering nicht mehr mit `ModuleNotFoundError` abbricht.
- **Doku-Inkonsistenz (#291)**: `README.md` Version und `requires-python = ">=3.10"` mit `pyproject.toml` synchronisiert.
- **Standort-Bezeichnung in Bewertung (#294)**: `EvaluatorService.evaluate_auftrag()` löst nun `schlechtester_standort_bezeichnung` anhand der übergebenen `Standort.bezeichnung` auf statt nur die ID zu duplizieren.

## [2.2.0] - 2026-08-14

### Added
- Chips unter "Noch nicht erfasst" in der Auftrags-Seitenleiste sind jetzt klickbar und springen direkt zur "Neues Objekt anlegen"-Seite für den fehlenden Baustein-Typ.

## [2.1.0] - 2026-08-14

### Added
- Preis-/Aufwand-Richtwerte (`kosten_richtwert`/`aufwand_richtwert`) für alle bestehenden Maßnahmen-Regeln ausgefüllt.
- Neue generische Schema-Feldtypen `liste` (wiederholbare Zeilen, z. B. Festplatten-Slots) und `objekt_referenz` (Objekt-zu-Objekt-Referenz), plus Abschnitt-Level `sichtbar_wenn`.
- Neue Objekttypen `server_cluster` und `vm`; `server_virtualisierung` (Hardware-Ebene, Cluster-Verknüpfung) und `switch` (Uplinks, VLAN, Redundanz) erweitert.
- VMs werden im generierten Bericht unter ihrem Host/Cluster gruppiert.
- "Bitte auswählen"-Platzhalter für die Anschlussart bei Internetanbindungen (kein Pflichtfeld).
- `CHANGELOG.md` eingeführt.

### Fixed
- "Mehrere Geräte"-Knopf im Standort öffnete keinen Dialog (fehlender `dialog.js`-Include + inkonsistentes Modal-Markup).
- Neue Standorte übernahmen nicht die Vertraulichkeitsstufe des Auftrags-Defaults, sondern fielen hart auf "kundentauglich" zurück.

## [2.0.0] - vorher

Baseline vor Einführung dieses Changelogs — siehe Git-Historie für Details.
