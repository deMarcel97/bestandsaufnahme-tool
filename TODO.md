# TODO / Planungs-Handoff – Bestandsaufnahme-Tool

**Stand:** 2026-08-15, erstellt von Claude Code (Sonnet 5) als Übergabe an eine andere KI-Session (Opus 4.6) zur Weiterplanung. Dies ist eine **Planungsgrundlage**, keine fertige Spezifikation — die größeren Punkte unten sind bewusst noch nicht ausformuliert und sollten mit Marcel durchgesprochen werden, bevor sie umgesetzt werden (siehe Leitplanken unten).

## Projektkontext

IT-Systemhaus-Tool zur einmaligen Vor-Ort-Bestandsaufnahme von Kunden-IT-Infrastruktur: strukturierte Erfassung → automatische Risikobewertung (Ampel-Score) → generierter .docx-Kundenbericht mit Handlungsempfehlungen. Zielgruppe: Kunden von 5 bis 1000 PCs mit **einem einzigen** Tool (siehe Leitplanke 1 unten). Kein Scanner, keine Zugangsdaten nötig — ein Termin reicht (siehe Konkurrenzanalyse unten für die Positionierung).

## Repo & Stack

- Pfad: `/Users/marcel/001_Vibe_Code/001_bestandsaufnahme_tool` (Hauptcheckout — **hier läuft der Dev-Server**, siehe Leitplanke 5)
- GitHub: `https://github.com/deMarcel97/bestandsaufnahme-tool`, Branch `main`
- Stack: FastAPI + Jinja2 + Pydantic v2 + PyYAML, Storage als JSON-Dateien unter `data/` (kein DB-Server)
- Aktuelle Version: 2.5.0 (siehe `CHANGELOG.md` für volle Historie)
- Tests: `venv/bin/pytest` (Stand jetzt: 84 Tests, alle grün)

### Architektur-Kurzreferenz (wichtig, bevor man Neues plant)

Alles ist **schema-getrieben**, kein Code pro Objekttyp:
- Jeder „Baustein" (Firewall, Switch, Software, …) = eine YAML-Datei in `schemas/<typ>.yaml` (Formularfelder in `abschnitte`/`felder`) + eine passende `rules/<typ>.yaml` (Risiko-Regeln, die gegen erfasste Daten ausgewertet werden). Neue Datei in `schemas/` = automatisch neuer wählbarer Baustein, kein Registry-Eintrag nötig (`app/services/schema_loader.py`).
- Feldtypen: `text, mehrzeiliger_text, zahl, datum, ja_nein, ja_nein_unbekannt, ja_nein_nicht_relevant, auswahl, mehrfachauswahl, liste, objekt_referenz`.
- Bedingte Feld-Sichtbarkeit: `sichtbar_wenn: {feld, operator, wert}` — lässt sich verketten (Feld A → Feld B → Feld C), siehe `schemas/software.yaml` als Referenzbeispiel (Kategorie → Anbieter-Dropdown → Freitext-Fallback bei „sonstige"). Wichtig: verkettete Sichtbarkeit brauchte serverseitig eine Nachbereinigung (`app/web/routes_objekt.py::_ist_sichtbar`), damit ausgeblendete Feldwerte beim Speichern nicht als Karteileichen ins Datenmodell wandern.
- Scoring-Kategorien (fix, nicht erweitern ohne Grund): `it_security`, `rechtliche_anforderungen`, `hardware_und_software`, `betriebsrisiken` (`bewertung/kategorien.yaml`).
- Auftrags-Sidebar (`_sidebar.html`, „Aktive Bausteine"-Fortschritt + „Noch nicht erfasst"-Chips) braucht `progress_data`/`findings`/`offene_punkte`/`massnahmen` im Template-Kontext — zentral gebündelt in `app/web/shared_context.py::build_sidebar_context()`.

## Aktueller Stand (zuletzt fertiggestellt)

- **PR #6 (gemerged)**: Business-Software-Themenblock — ein Baustein `software` mit Kategorie-Auswahl CRM/DMS/ERP statt drei separaten Bausteinen; Anbieter-Dropdown mit „sonstige"+Freitext-Fallback als wiederverwendbares Muster für künftige Software-Hersteller-Felder.
- **PR #7 (offen, noch nicht gemerged)**: „Noch nicht erfasst"-Leiste erschien bisher nur auf der Auftrags-Übersichtsseite, jetzt auf allen Auftragsseiten inkl. der Objekt-/Standort-Erfassungsformulare sichtbar.
- Superthread-Board „Bestandsaufnahme-Tool" (Space „Software", board_id 15) enthält die laufende Kartenhistorie aller Änderungen — dort auch nachlesbar, was zuletzt warum entschieden wurde (Kommentare „Lösungsweg"/„Lösung" pro Karte).

## Offene Backlog-Karten (Superthread, Stand 2026-08-15)

Diese liegen aktuell in der Spalte „Backlog" des Boards und sind noch nicht begonnen:

1. **#299 – Feld Kommentar**: Das Kommentarfeld in der Objekt-Erfassung muss ans Ende des Formulars (aktuell falsch positioniert).
2. **#298 – Feld Festplatten-Slots**: Fehlt aktuell die Anbindung (SATA/SAS/NVMe o.ä.) sowie ein Feld, um mehrere Festplatten auf einmal hinzuzufügen (vermutlich `typ: liste` passend, siehe `server_virtualisierung`/`server_cluster`-Schemas als Vorbild).
3. **#297 – Server & Virtualisierung Feld**: „Wird virtualisiert?" muss ganz nach oben und Pflichtfeld werden; die Hypervisor-spezifischen Folgefragen sollen erst nach „Ja" erscheinen (vorher als Bare-Metal-Host behandeln). Klingt nach demselben `sichtbar_wenn`-Muster wie bei Software-Kategorie → Anbieter.
4. **#296 – Server**: Unterobjekt/Kind-Karte zu #297, vermutlich Detailfragen zum eigentlichen Server-Objekt.
5. **#295 – Status-Anpassungen**: Ampelfarben in der Standortübersicht: Vollständig = grün, Teilweise = gelb/orange, Unbekannt = grau (aktuell offenbar nicht korrekt/konsistent).
6. **#287 – Offene Punkte strukturieren**: Die „Offene Punkte"-Liste soll nicht nur nach Standort, sondern zusätzlich nach Hardware/Baustein gruppiert werden, damit man bei einer langen unübersichtlichen Liste gezielt nachschauen kann, wo noch was fehlt.
7. **#286 – Trennung Stammdaten & Kontext**: Der Unternehmenskontext soll als eigener, klar abgegrenzter Punkt von den reinen Stammdaten getrennt werden.
8. **#284 – Empfehlung bei Stammdaten-Änderung**: Wenn z. B. Geschäftszeiten auf 24/7 gesetzt werden, soll automatisch eine Empfehlung erscheinen, dass eine Rufbereitschaft hinterlegt werden sollte.
9. **#283 – Bei den Aufträgen**: Status und „Vorbereitung" bei Aufträgen sollen editierbar sein (aktuell offenbar nicht/nicht ausreichend).
10. **#281 – QA-Testdaten bereinigen**: Im Test-Auftrag taucht wiederholt „QA Inspector Team (Updated)" in der Betreut-durch-Spalte auf — vom User nicht beauftragt, wirkt wie Testdaten-Reste, die aufgeräumt werden sollten.

Aktuellen Stand vor Umsetzung jeweils per `find_tasks`/`task_get` auf Superthread gegenchecken — Karten können sich zwischen Planung und Umsetzung verschieben.

## Größere offene strategische Fragen (noch nicht im Detail geplant — hier ansetzen)

Diese Punkte sind bewusst nur als Merkposten notiert, nicht als fertige Spezifikation:

1. **Themenblöcke / Organisation & Prozesse als eigener Baustein.** Laut Referenzmaterial macht organisatorischer/prozessualer Content ~2/3 des eigentlichen Assessment-Inhalts aus (Governance, Prozesse, Verantwortlichkeiten) — im Tool aktuell fast nur Technik-Bausteine vorhanden. Business-Software (CRM/DMS/ERP) war ein erster Schritt in diese Richtung. Verinice (BSI-IT-Grundschutz-Tool) behandelt Organisation als gleichwertiges Objekt neben Technik (ORP-/CON-Bausteine) — als Referenz-Architektur relevant.
2. **Generelles Objektmodell.** Server, Storage etc. sollten als saubere Basis-Objekte definiert sein, *bevor* weitere Themenblöcke draufgesetzt werden — aktuell historisch gewachsen (server_virtualisierung/server_cluster/vm als Geschwister-Schemas). Klärungsbedarf, wie das sauber vereinheitlicht wird, ohne bestehende Daten/Reports zu brechen.
3. **Backup & Recovery** als nächster großer Themenblock nach Firewall (im Sinne der Themenblock-Architektur wie Business-Software). DIN-SPEC-27076 trennt „Reaktion" von „Wiederherstellung" — als Bauplan relevant.
4. **Weitere Business-Software-Kategorien** über CRM/DMS/ERP hinaus (z. B. HR-Software, E-Commerce/Shop-Systeme) — aktuell nicht abgedeckt, das `software`-Schema mit Kategorie-Selector ist aber genau für diese Erweiterung gebaut.
5. **Referenzpreis-Katalog für Maßnahmen.** `kosten_richtwert`/`aufwand_richtwert` sind pro Regel in `rules/*.yaml` gepflegt (seit v2.1.0), aber `kosten_quelle` bleibt bis zur manuellen Bestätigung `"offen"`. Prüfen, ob das für den Verkaufsprozess ausreicht oder ob ein editierbarer globaler Preiskatalog nötig ist. Laut Konkurrenzanalyse (#290, siehe unten) ist ein fertiger, gestaffelter Maßnahmenkatalog mit Kostenschätzung eine echte Marktlücke — kein Konkurrenzprodukt bietet das.
6. **Cross-Objekt VLAN-Status.** Wenn Switch/Firewall den VLAN-Status auf Netzwerkebene erfassen, könnte das Access-Point-Feld `gast_wlan_isoliert` redundant werden. Eigene Design-Diskussion nötig, wie objektübergreifende Konsistenz sauber modelliert wird, ohne Doppelerfassung zu erzeugen.
7. **Erkenntnisse aus der Konkurrenzanalyse (Karte #290, Recherche vom 15.08.2026, von Marcel noch nicht gegengeprüft)** — konkrete Ideen für die Roadmap:
   - Kosten × Dringlichkeit als zweiachsiges Priorisierungsmodell im Maßnahmenkatalog (analog DIN SPEC 27076).
   - Optionales Metadatenfeld „Förderprogramm" pro Maßnahme (z. B. Mittelstand Digital) — geringer Aufwand, verkaufsstark.
   - Aus erfassten Verbindungsdaten (Gerät X an Switch-Port Y) automatisches Netzwerktopologie-Diagramm statt Freihand-Zeichnen.
   - Getrennte Kennzahlen (Risk-Score vs. Issues-Score, Vorbild Network Detective) prüfen gegenüber dem bestehenden Scoring-Modell.
   - Kurzer Executive-Abschnitt vorneweg im Bericht statt separatem Dokument.
   - Optionaler Diff-/Update-Modus für Folgebesuche beim selben Kunden.
   - Positionierung: „Kein Scanner, keine Zugangsdaten, ein Termin reicht" explizit als USP gegenüber Docusnap/Network Detective/i-doit kommunizieren.

## Leitplanken (aus bisherigen Diskussionen mit Marcel — bitte einhalten)

1. **Ein einheitliches Tool für alle Kundengrößen** (5-PC- bis 1000-PC-Kunden) — keine Fragen, die nur für eine Größenordnung relevant sind. Kein separates „Enterprise-Modus".
2. **Bei Feld-Abhängigkeits-/UX-Fragen zuerst Optionen durchsprechen**, nicht direkt umsetzen — Marcel möchte hier mitentscheiden, bevor Code entsteht. Bei eindeutigen Bugs (kein Design-Ermessen nötig) ist direktes Fixen dagegen in Ordnung.
3. **Jede Änderung bekommt eine Karte auf dem Superthread-Board** „Bestandsaufnahme-Tool" (Space „Software", space_id 6, board_id 15), getaggt Feature/Bug, mit Kommentaren „Lösungsweg" (Ursachenanalyse) und „Lösung" (was umgesetzt wurde, inkl. PR-Link) getrennt vom Beschreibungstext der Karte.
4. **Jede Änderung bekommt eine neue Versionsnummer** (SemVer) + Eintrag in `CHANGELOG.md` + Sync in `README.md`.
5. **Jede Änderung muss sowohl lokal sichtbar sein als auch als GitHub-PR landen.** Wichtig: Der laufende Dev-Server (Port 8000, `reload=True`) bedient **ausschließlich** den Hauptcheckout `/Users/marcel/001_Vibe_Code/001_bestandsaufnahme_tool` — niemals eine `.claude/worktrees/*`-Kopie. Arbeitsweise: neuer Branch von `main` **im Hauptcheckout selbst**, dort implementieren (Dev-Server zieht Änderungen automatisch), committen, pushen, PR öffnen (`gh pr create`). Ein reiner Branch-Wechsel im Hauptcheckout (z. B. für ein unabhängiges Thema) lässt den Dev-Server währenddessen den jeweils ausgecheckten Stand zeigen — das ist normal, aber gut zu wissen, falls „das Feature ist plötzlich weg" auftaucht.
6. **Keine Features/Abstraktionen über die gestellte Aufgabe hinaus.** Drei ähnliche Zeilen sind besser als eine verfrühte Abstraktion für einen hypothetischen Zukunftsfall.
