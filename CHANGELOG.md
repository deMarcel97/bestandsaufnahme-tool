# Changelog

Alle nennenswerten Änderungen am IT-Bestandsaufnahme-Tool werden hier dokumentiert.

Format angelehnt an [Keep a Changelog](https://keepachangelog.com/), Versionierung nach [Semantic Versioning](https://semver.org/) (MAJOR.MINOR.PATCH): MAJOR = Breaking Change, MINOR = neue Funktionalität (abwärtskompatibel), PATCH = Bugfix.

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
