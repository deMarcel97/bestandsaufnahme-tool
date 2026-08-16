# Changelog

Alle nennenswerten Änderungen am IT-Bestandsaufnahme-Tool werden hier dokumentiert.

Format angelehnt an [Keep a Changelog](https://keepachangelog.com/), Versionierung nach [Semantic Versioning](https://semver.org/) (MAJOR.MINOR.PATCH): MAJOR = Breaking Change, MINOR = neue Funktionalität (abwärtskompatibel), PATCH = Bugfix.

## [2.7.18] - 2026-08-16

### Changed
- **Design-Handoff-Vorlagen aktualisiert (#311)**: `Design änderung/handoff/app/` mit dem aktuellen Stand von `app/templates/` und `app/static/` synchronisiert. Veraltete Einzeldateien (wie `edit.html`) entfernt und die neue Modulstruktur (Beteiligte, Verträge, Unterlagen, Projektrahmen, Stammdaten/Kontext-Trennung) sowie die Dokumentation in `README.md` nachgezogen.

## [2.7.17] - 2026-08-16

### Fixed
- **Zahlparser unterstützt deutsche Tausenderpunkte und internationale Formate (#319)**: `parse_float_german()` und `parse_int_german()` erkennen Tausenderpunkte in Beträgen und Mengenangaben (z. B. `"1.249,90"`, `"1.000.000"`, `"10.000"`), ohne Dezimalzahlen wie `"1.5"` oder `"0.123"` zu verfälschen. Verhindert stillen Datenverlust auf `0.0` bei Verträgen, Bandbreiten, SLA-Zeiten und Bausteinfeldern.

## [2.7.16] - 2026-08-16

### Fixed
- **`scratch/` in `.gitignore` aufgenommen (#318)**: Verhindert, dass temporäre Hilfsskripte oder Arbeitsdateien versehentlich im öffentlichen Git-Repository mitversioniert werden.

## [2.7.15] - 2026-08-16

### Added
- **`HANDOFF_antigravity.md` (#320)**: Fahrplan für die Weiterarbeit in Antigravity (`agy`). Er wiederholt `CLAUDE.md` nicht, sondern nennt, was für diese Umgebung eigen ist — Superthread und GitHub sind dort in `~/.gemini/config/mcp_config.json` bereits als MCP-Server eingetragen, und `agy --print-timeout` verlangt eine Zeiteinheit (`90s`, nicht `90`). Letzteres sah ohne Meldung wie ein hängender Login aus und hat am 15.08.2026 Stunden gekostet.
- **Reihenfolge der offenen Karten (#320)**: getrennt nach „ohne Rückfrage machbar" (#319, #318) und „erst entscheiden lassen" (#311, #314, #315, #312). Karten der zweiten Gruppe gehören nicht in eine Sitzung, in der gerade niemand mitliest — sie enden sonst in einer Umsetzung, die anschliessend verworfen wird.

## [2.7.14] - 2026-08-16

### Added
- **Vier neue Erfassungsseiten für bisher unerreichbare Felder (#316)**: „Beteiligte" (Kontakte bei Kunde und Dienstleistern inkl. „zuständig für Thema", E-Mail, Telefon), „Verträge" (Wartungsverträge mit Kündigungsfrist, Laufzeit und monatlichen Kosten), „Unterlagen" (angeforderte Dokumentation mit Status) und „Projektrahmen" (benötigte Zugänge, Zutrittsregelung, NDA, Wartungsfenster, Analysewerkzeuge, Ergebnisartefakte sowie manuelle Beobachtungen vor Ort).
- **Beobachtungen vor Ort im Bericht (#316)**: `positive_aspekte`/`negative_aspekte` erscheinen als Anhang „Beobachtungen vor Ort". Bewusst getrennt von den Findings: die entstehen automatisch aus den Regeln, dies hier ist der Eindruck des Bearbeiters, den keine Regel erkennen kann. Bei Ziel „anonymisiert" entfällt der Anhang, weil Freitext den Kunden identifizierbar macht.
- **Gemeinsamer Parser für wiederholbare Unterformulare (#316)**: `app/web/formular_listen.py::parse_unterobjekte()` liest Felder der Form `<praefix>_<feld>_<index>` und holt sich die Feldnamen aus dem Modell. Er bedient alle fünf neuen Listen; das Muster gab es bisher nur einmal für die Internetanbindungen am Standort.

### Fixed
- **Der Analysebericht hatte Abschnitte, die nie gefüllt werden konnten (#316)**: `geschaeftskritische_systeme`, `geplante_aenderungen` und `vertraege` wurden von `report_builder.py` gelesen, `dokumentenanforderung` von `progress.py` — nur schrieb sie **kein einziges Formular**. Betriebskritische Systeme und Verträge blieben im Kundenbericht zwangsläufig leer, die Schleife über die Dokumentenanforderungen lief immer über eine leere Liste. Neun Felder im `Auftrag`-Modell waren auf diese Weise tot.
- **Leere Zeilen mit Auswahlfeld wurden gespeichert (#316)**: Der neue Parser prüfte zunächst nur auf einen nicht-leeren Rohwert. Ein `<select>` schickt aber immer einen Wert mit — eine hinzugefügte, aber nicht ausgefüllte Zeile wäre als leerer Datensatz in der Ablage gelandet. Verglichen wird jetzt gegen den Vorgabewert des Modells.
- **Ziel der offenen Dokumentenanforderungen (#316)**: Die Liste „Offene Punkte" verwies für Unterlagen auf `/stammdaten`, wo das Feld nie lag. Jetzt zeigt sie auf die neue Seite „Unterlagen".

### Changed
- **Stammdaten und Unternehmenskontext erweitert (#316)**: `zweck` (Mehrfachauswahl, serverseitig geprüft wie in #309), `abgrenzung`, `aufwand_geplant` und `aufwand_ist` stehen in der Auftragssteuerung; die betriebskritischen Systeme und geplanten Änderungen auf der Kontextseite, wo sie sachlich hingehören — sie liegen im Modell innerhalb von `Unternehmenskontext`, nicht direkt am Auftrag.
- **`aktuelle_version()` liegt jetzt in `shared_context.py` (#316)**: Die Konflikterkennung aus #308 gilt inzwischen für fünf Auftrags-Unterseiten, und der Helfer stand in jedem Route-Modul als eigene Kopie. Als private Kopie wäre absehbar der Tag gekommen, an dem eine davon nicht mitgezogen wird.

### Known Issues
- **Tausenderpunkte gehen in Zahlfeldern verloren (#319)**: `parse_float_german("1.249,90")` ergibt `0.0` statt `1249.90`, ohne Fehlermeldung. Betrifft die neuen Vertragskosten ebenso wie bestehende Felder (Bandbreiten, SLA-Zeiten). Der Fehler ist älter als #316; `tests/test_formular_listen.py::test_tausenderpunkt_geht_noch_verloren` hält den Stand fest, damit er nicht unbemerkt bleibt.

## [2.7.13] - 2026-08-16

### Fixed
- **Auswahlfelder werden serverseitig geprüft (#309)**: `create_auftrag()` und `stammdaten_submit()` schrieben `grundlage`, `status` und `vertraulichkeit_default` ungeprüft ins Modell, während `update_auftrag_status()` und `update_auftrag_vertraulichkeit()` längst gegen ihre Listen prüften. Über die Oberfläche liess das Dropdown nichts Ungültiges zu, ein direkter POST schon — der Wert wäre still gespeichert worden und später in Berichten aufgetaucht.
- **Dieselbe Lücke stand bei `vertraulichkeit` an Standort und Technik-Objekt (#309)**: `routes_standort.py` und `routes_objekt.py` übernahmen den Formularwert an vier Stellen ungeprüft. Das wiegt schwerer als bei `grundlage`, weil an diesem Feld die Filterung beim Export hängt — genau das Szenario aus #310, nur eine Ebene früher.

### Changed
- **Eine Regel statt zweier Varianten (#309)**: Ein unbekannter Wert wird verworfen, nie gespeichert. Beim Bearbeiten ist der Rückfall der **bereits gespeicherte** Wert — ein fehlerhafter POST überschreibt damit nichts, statt den Datensatz auf einen Vorgabewert zurückzusetzen; die übrigen Felder des Formulars werden trotzdem gespeichert. Nur beim Neuanlegen, wo es nichts zu bewahren gibt, greift der Vorgabewert, bei der Vertraulichkeit also `intern` (die schützende Stufe, #310). Umgesetzt als `gueltiger_wert()` im neuen Modul `app/web/optionen.py`.
- **Die Auswahllisten haben genau eine Quelle (#309)**: `STATUS_OPTIONS`, `GRUNDLAGE_OPTIONS` und das neue `VERTRAULICHKEIT_OPTIONS` liegen in `app/web/optionen.py`. Die Vertraulichkeitsstufen standen vorher literal in `routes_auftrag.py` **und** in fünf Templates; sie kommen jetzt als Jinja-Global `vertraulichkeit_options`, weil die betroffenen Templates von drei verschiedenen Route-Modulen bedient werden und ein Durchreichen über den Kontext fünf Stellen zum Vergessen geboten hätte. Ein eigenes Modul, weil `templates.py` sonst aus einem Route-Modul importieren müsste und ein Importzyklus entstünde.
- **Ungenutzte Importe entfernt (#309)**: `Termine`, `Unternehmenskontext` und `parse_float_german` in `routes_auftrag.py` — die Namen kamen nur noch in Kommentartexten vor.

## [2.7.12] - 2026-08-16

### Fixed
- **`HANDOFF_claude_code.md` beschrieb ein Projekt, das es nicht mehr gibt (#317)**: Die Datei hatte den Stand vom 13.08.2026 — „Storage als YAML/**JSON**-Dateien" (es ist YAML, derselbe Fehler wie in `TODO.md` bei #312), „54 Tests" (es sind 171), „10 Bausteine" (es sind 13 Schemas), offene Punkte als `#9`/`#10`/`#11` nach einer Zählung, die durch die Superthread-Karten-IDs abgelöst wurde. Beim Beginn einer neuen Sitzung ist das die Datei, die zuerst gelesen wird; sie führte damit als Erstes in die Irre.

### Changed
- **Der Handoff verweist jetzt, statt zu wiederholen (#317)**: Arbeitsregeln stehen in `CLAUDE.md`, das Projekt im README, der Aufgabenstand auf dem Board — eine Übergabe, die all das dupliziert, veraltet innerhalb einer Woche, und genau das war passiert. Übrig bleibt, was nirgends sonst steht: wo gearbeitet wird (Hauptcheckout statt Worktree, weil der Dev-Server nur diesen bedient), die Architektur in fünf Sätzen, die Fallstricke aus #305/#308, #310, #311 und #316 — und der Hinweis, dass der Gesprächsverlauf einer Sitzung nicht mitwandert, weil er unter einem Pfad-Slug des Arbeitsverzeichnisses liegt.

## [2.7.11] - 2026-08-16

### Fixed
- **Rückfallwerte der Vertraulichkeit wählen jetzt die schützende Stufe (#310)**: Seit #302 gilt „intern" als Vorgabe — die Freigabe für Kundenunterlagen soll eine bewusste Entscheidung sein. Der Export folgte dem noch nicht: `getattr(o, "vertraulichkeit", "kundentauglich")` in `app/services/exporter.py` nahm im Zweifel die freizügigere Stufe an. Umgestellt auf `"intern"`.
- **Der eigentliche Rückfallwert saß eine Ebene tiefer (#310)**: `VertraulichkeitsStufe.parse()` gab für **jeden** unbekannten Wert `KUNDENTAUGLICH` zurück. Anders als der `getattr`-Vorgabewert war das erreichbar — ein Tippfehler in einer YAML-Datei (`vertraulichkeit: intren`) hätte den Datensatz in Kundenunterlagen befördert. `parse()` verlangt den Rückfallwert jetzt als Argument, und die Aufrufstellen setzen ihn je nach Richtung: für einen erfassten Datensatz `INTERN` (fliegt aus Kundenunterlagen heraus), für das Ziel eines Exports `ANONYMISIERT` (gibt am wenigsten preis). Ein gemeinsamer Vorgabewert wäre in einer der beiden Richtungen immer die riskante Wahl gewesen — beim Exportziel, das als Adressparameter aus der URL kommt, hätte `INTERN` einen vollständigen internen Bericht ausgeliefert.

### Changed
- **`ziel_vertraulichkeit` ist keine optionale Angabe mehr (#310)**: Die stillen Vorgabewerte `= "kundentauglich"` in sechs Signaturen von `exporter.py` und in `report_builder.build_analysebericht()` sind entfallen; wo die Parameterreihenfolge es erzwingt, ist die Angabe benannt zu übergeben. Ein vergessener Aufruf fällt damit sofort auf, statt still die freizügigere Stufe zu wählen — `tests/test_exporter.py::test_csv_exporter` war genau so ein Aufrufer.

## [2.7.10] - 2026-08-16

### Fixed
- **Standorte lassen sich löschen (#307)**: `storage.delete_standort()` existierte seit jeher, wurde aber von keiner Route aufgerufen — Standorte liessen sich schlicht nicht entfernen, während Aufträge und Technik-Objekte längst löschbar waren. Besonders unangenehm, weil der Unternehmenskontext über `anzahl_standorte_kunde` Standorte automatisch anlegt: wer sich dort vertippte, wurde sie nicht wieder los. Neue Route `POST /auftrag/{id}/standort/{id}/loeschen` und eine Schaltfläche in der Erfassungsansicht.

### Added
- **Schutz vor unbeabsichtigtem Datenverlust beim Standort-Löschen (#307)**: Hängen noch Technik-Objekte am Standort, wird das Löschen mit HTTP 409 abgelehnt und die blockierenden Objekte werden namentlich mit Link aufgeführt. Bewusst kein Kaskadenlöschen und kein automatisches Umhängen — was mit den erfassten Objekten geschehen soll, weiss nur der Bearbeiter. Zum Verschieben genügt die bereits vorhandene Standort-Auswahl im Objektformular. In der Erfassungsansicht ist die Schaltfläche in diesem Fall deaktiviert und nennt im Tooltip die Anzahl der Objekte, statt den Klick erst ins Leere laufen zu lassen.

## [2.7.9] - 2026-08-16

### Fixed
- **Konflikterkennung greift jetzt über die Dauer eines geöffneten Formulars (#308)**: Zähler und Prüfung gibt es seit v2.7.4 (#305), sie konnten aber nie anschlagen — die POST-Handler luden den Datensatz unmittelbar vor dem Speichern frisch von der Platte, wodurch die Version zwangsläufig übereinstimmte. Zwei Benutzer mit demselben geöffneten Formular überschrieben sich weiterhin stillschweigend. Die vier Bearbeitungsformulare (Stammdaten, Unternehmenskontext, Standort, Technik-Objekt) führen den beim Laden gesehenen Stand jetzt als verstecktes `version`-Feld mit, und die Handler in `routes_auftrag.py`, `routes_standort.py` und `routes_objekt.py` übernehmen ihn vor dem Speichern. Fehlt das Feld — etwa bei einem Formular aus einer älteren Programmversion —, bleibt es beim bisherigen Verhalten, statt das Speichern zu blockieren.
- **Eingaben gehen bei einem Konflikt nicht mehr verloren (#308)**: Statt der allgemeinen Hinweisseite liefern die vier Formulare sich selbst mit den gerade eingegebenen Werten und einem Warnbanner zurück (HTTP 409, neues Teil-Template `app/templates/_konflikt_banner.html`). Das versteckte Feld trägt dabei den inzwischen auf der Platte liegenden Stand, sodass ein zweites Speichern die fremde Änderung bewusst überschreibt, statt in derselben Meldung hängenzubleiben. Die zentrale 409-Seite in `app/main.py` bleibt als Auffangnetz für alle übrigen Speicherstellen bestehen.

## [2.7.8] - 2026-08-15

### Fixed
- **Karten ohne GitHub-Verknüpfung (#313)**: Vier Karten (#302, #303, #304, #306) blieben in Superthread ohne Link zu ihrem Pull Request, obwohl Branch-Name und PR-Titel die Karten-ID korrekt trugen. Ursache war nicht das Namensformat, sondern der Merge-Weg: die vier PRs wurden über einen gemeinsamen Integrationszweig geschlossen, weil sich alle Karten an Version und CHANGELOG überschnitten. Superthread hängt seine Verknüpfung an die PR-Ereignisse — ein so geschlossener PR erzeugt sie nicht, und nachträglich lässt sich das nicht heilen (Neusetzen des PR-Titels an #302 getestet, ohne Wirkung). `CLAUDE.md` hält jetzt als Regel fest, PRs immer über `gh pr merge` zu schliessen und Konflikte im jeweiligen Feature-Branch aufzulösen statt auf einem Integrationszweig. Für die vier betroffenen Karten wurde der Link als Kommentar nachgetragen.

## [2.7.7] - 2026-08-15

### Changed
- **TODO als Entscheidungsauftrag statt Ideensammlung (#312)**: Die Erkenntnisse aus der Konkurrenzanalyse (#290) standen in `TODO.md` als reine Liste — ein Rechercheergebnis ohne Auftrag, das in dieser Form nie umgesetzt worden wäre. Ergänzt um einen ausdrücklichen TODO-Block: die Liste muss zerlegt werden, pro Idee mit einer von drei Antworten („bauen wir" / „später" / „bauen wir nicht"), und die Maßnahmenkatalog-Punkte sind zuerst zu bewerten, weil dort laut Recherche die eigentliche Marktlücke liegt.

### Fixed
- **Veraltete Angaben in `TODO.md` (#312)**: Der Kopf nannte Version 2.5.0 und „84 Tests" (tatsächlich 2.7.7 und 141) sowie „Storage als **JSON**-Dateien" — die Ablage ist YAML (`yaml.dump` in `app/services/storage.py`). Dieselbe Verwechslung stand auch in der Projektstruktur des README. Ergänzt: Hinweis auf den Serverbetrieb.

## [2.7.6] - 2026-08-15

### Changed
- **„Übersicht & Erfassung" ist jetzt zwei Menüpunkte (#306)**: Der Sidebar-Eintrag vereinte zwei Dinge, die im Arbeitsalltag getrennt genutzt werden — den Blick auf den Stand und das eigentliche Erfassen. Neu: **„Übersicht"** (`/auftrag/{id}`, unverändert erreichbar) mit den vier Kennzahlen-Kacheln und **„Erfassung"** (`/auftrag/{id}/erfassung`, neues Template `app/templates/auftrag/erfassung.html`) mit Standorten, Bausteinauswahl und den erfassten Objekten.
- **Weniger Rechenarbeit pro Seitenaufruf (#306)**: Die gemeinsame Route lud beides zusammen. Die teure `evaluator_service.evaluate_auftrag(...)` läuft jetzt nur noch auf der Übersicht, wo die Kennzahlen sie brauchen — die Erfassungsseite kommt ohne sie aus. `build_sidebar_context()` nimmt Standorte und Objekte optional entgegen, damit dieselben Dateien nicht zweimal von der Platte gelesen werden.
- **Weiterleitung nach dem Speichern (#306)**: Wer ein Objekt oder einen Standort anlegt, bearbeitet, dupliziert oder löscht, landet jetzt auf der **Erfassung** statt auf der Übersicht — das ist der Arbeitsfluss, in dem man sich dann befindet. Die „Abbrechen"- und „Zurück"-Links der Formulare führen entsprechend dorthin zurück.

## [2.7.5] - 2026-08-15

### Fixed
- **Reihenfolge von Standorten, Objekten und Aufträgen war zufällig (#304)**: `list_standorte()`, `list_objekte()` und `list_auftraege()` in `app/services/storage.py` gaben die Einträge in der Reihenfolge zurück, in der `glob()` bzw. `iterdir()` sie vom Dateisystem bekamen. Das ist auf APFS die Hash-Reihenfolge der Verzeichniseinträge — weder alphabetisch noch nach Anlagezeitpunkt, abhängig vom Dateisystem, und sie ändert sich, sobald Einträge dazukommen oder wegfallen. In der Oberfläche sah das aus, als springe die Standortliste nach jedem Speichern. Die drei Listen sind jetzt fest sortiert: Standorte alphabetisch nach Bezeichnung (die Spalte, die der Benutzer sieht — die `id` ist nur der Slug der Bezeichnung zum Zeitpunkt der Anlage und würde nach einer Umbenennung falsch einsortieren), Objekte nach Typ und dann Bezeichnung (entspricht den ersten beiden Spalten der Objekttabelle, gleichartige Objekte stehen damit beieinander), Aufträge nach Kunde und dann Bezeichnung (die automatisch vergebenen Projektnummern `PROJEKT-2`/`PROJEKT-10` würden sich alphabetisch falsch einsortieren). Sortiert wird über einen gemeinsamen Schlüssel, der Groß-/Kleinschreibung ignoriert und Umlaute wie `ae/oe/ue` einordnet — dieselbe Transliteration, die auch die IDs erzeugt; die `id` als letztes Kriterium hält gleichnamige Einträge stabil.

## [2.7.4] - 2026-08-15

### Fixed
- **Schreibvorgänge konnten Daten zerstören (#305)**: Alle fünf Schreibstellen in `app/services/storage.py` nutzten `open(fpath, "w")` + `yaml.dump`. `open(..., "w")` leert die Zieldatei sofort — bevor der neue Inhalt geschrieben ist. Brach der Prozess in diesem Fenster ab (Dienst-Neustart, OOM, Stromausfall), blieb eine leere oder abgeschnittene YAML-Datei zurück und der Auftrag war nicht veraltet, sondern kaputt. Neu schreibt `write_yaml_atomic()` vollständig in eine Nachbardatei, erzwingt `fsync()` und benennt erst dann per `os.replace()` um (auf POSIX atomar) — es existiert damit immer entweder der alte oder der neue Stand. Das Risiko bestand unabhängig von Mehrbenutzerbetrieb und traf auch die Einzelnutzung.

### Added
- **Konflikterkennung beim Speichern (#305)**: `Auftrag`, `Standort` und `TechnikObjekt` führen einen `version`-Zähler. Weicht er beim Speichern vom Stand auf der Platte ab, hat jemand anderes zwischenzeitlich gespeichert — statt die fremden Änderungen stillschweigend zu überschreiben (bisher galt „wer zuletzt speichert, gewinnt", ohne jede Meldung), wird ein `KonfliktFehler` ausgelöst. Ein zentraler Exception-Handler in `app/main.py` beantwortet ihn mit HTTP 409 und einer verständlichen Seite. Bestandsdaten ohne `version`-Feld bleiben ladbar und starten bei 1.

  **Abgrenzung:** Die Formulare führen die Version noch nicht als verstecktes Feld mit. Da die POST-Handler den Datensatz frisch laden, greift die Prüfung deshalb bislang auf Ebene der Speicher-Schnittstelle, noch nicht über die Dauer eines geöffneten Formulars hinweg. Das Nachziehen der Formulare ist der nächste Schritt und braucht Dateien, die derzeit parallel umgebaut werden.

  `findings.yaml` und `massnahmen.yaml` werden als ganze Liste geschrieben und bekommen vorerst nur das atomare Schreiben, keine Versionsprüfung.

## [2.7.3] - 2026-08-15

### Changed
- **„Stammdaten & Kontext" ist jetzt zwei Menüpunkte (#303)**: Die bisherige Sammelseite vereinte vier Abschnitte auf einer Seite. Neu trennt die Sidebar zwischen **Stammdaten** (`/auftrag/<id>/stammdaten`: Stammdaten, Auftragssteuerung, Termine — alles, was den Auftrag steuert) und **Unternehmenskontext** (`/auftrag/<id>/unternehmenskontext`: alles, was den Kunden beschreibt). Beide Seiten binden `build_sidebar_context()` ein, die Fortschrittsanzeige bleibt also überall sichtbar.
- **Getrenntes Speichern ohne Datenverlust (#303)**: Jede der beiden Seiten hat einen eigenen POST-Handler, der ausschliesslich seine eigenen Felder entgegennimmt und setzt. Der frühere Sammel-Handler schrieb alle Felder aus einem Formular — getrennte Seiten hätten damit beim Speichern jeweils die Felder der anderen Seite auf ihre Defaults zurückgesetzt. Zwei Tests in `tests/test_integration_routes.py` belegen beide Richtungen und prüfen dabei gegen die tatsächlich abgeschickten Werte statt gegen einen Schnappschuss, damit ein Zurücksetzen auf Defaults nicht unbemerkt bleibt.
- **Alte Adresse bleibt gültig (#303)**: `GET /auftrag/<id>/einstellungen` leitet auf die Stammdaten-Seite weiter, sodass Lesezeichen und die in offenen Punkten hinterlegten Ziel-Links weiter funktionieren. Der zugehörige Sammel-POST entfällt ersatzlos.

## [2.7.2] - 2026-08-15

### Added
- **Grundlage „Analyse" (#302)**: Die Auswahl „Grundlage" beim Anlegen und Bearbeiten eines Auftrags kennt jetzt zusätzlich „Analyse" — Aufträge, die aus einer vorangegangenen Analyse hervorgehen, mussten bisher als „Sonstiges" abgelegt werden. Reihenfolge: Ausschreibung, Angebot, Analyse, Rahmenvertrag, Sonstiges.

### Changed
- **Grundlage-Auswahl zentralisiert (#302)**: Die Optionsliste stand doppelt hart kodiert in `auftrag/list.html` und `auftrag/edit.html`, sodass eine neue Option an beiden Stellen nachgetragen werden musste. Sie kommt jetzt als `GRUNDLAGE_OPTIONS` aus `app/web/routes_auftrag.py` (analog zu `STATUS_OPTIONS`) und wird über den Template-Kontext durchgereicht. Ein Test schlägt an, falls die Liste wieder in ein Template wandert.
- **Vertraulichkeit standardmässig „intern" (#302)**: Neue Aufträge, Standorte und Objekte sind jetzt per Vorgabe „intern" statt „kundentauglich". Die Freigabe für Kundenunterlagen ist damit eine bewusste Entscheidung und kein Nebeneffekt der Vorbelegung. Betrifft die Modell-Defaults (`auftrag.py`, `standort.py`, `technik.py`), die Formular-Defaults der Auftragsrouten und die Vorauswahl im Anlege-Dialog. Bereits gespeicherte Werte bleiben unverändert.


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
