# TODO / Planungs-Handoff – Bestandsaufnahme-Tool

**Stand:** 2026-08-15, erstellt von Claude Code (Sonnet 5) als Übergabe an eine andere KI-Session (Opus 4.6) zur Weiterplanung. Dies ist eine **Planungsgrundlage**, keine fertige Spezifikation — die größeren Punkte unten sind bewusst noch nicht ausformuliert und sollten mit Marcel durchgesprochen werden, bevor sie umgesetzt werden (siehe Leitplanken unten).

## Projektkontext

IT-Systemhaus-Tool zur einmaligen Vor-Ort-Bestandsaufnahme von Kunden-IT-Infrastruktur: strukturierte Erfassung → automatische Risikobewertung (Ampel-Score) → generierter .docx-Kundenbericht mit Handlungsempfehlungen. Zielgruppe: Kunden von 5 bis 1000 PCs mit **einem einzigen** Tool (siehe Leitplanke 1 unten). Kein Scanner, keine Zugangsdaten nötig — ein Termin reicht (siehe Konkurrenzanalyse unten für die Positionierung).

## Repo & Stack

- Pfad: `/Users/marcel/001_Vibe_Code/001_bestandsaufnahme_tool` (Hauptcheckout — **hier läuft der Dev-Server**, siehe Leitplanke 5)
- GitHub: `https://github.com/deMarcel97/bestandsaufnahme-tool`, Branch `main`
- Stack: FastAPI + Jinja2 + Pydantic v2 + PyYAML, Storage als YAML-Dateien unter `data/` (kein DB-Server)
- Läuft zusätzlich als Dienst auf einem internen Server — Zugang und Arbeitsweise siehe `CLAUDE.md` und `deploy/`
- Aktuelle Version: 2.7.7 (siehe `CHANGELOG.md` für volle Historie)
- Tests: `PYTHONPATH=. venv/bin/pytest` (Stand jetzt: 141 Tests, alle grün)

### Architektur-Kurzreferenz (wichtig, bevor man Neues plant)

Alles ist **schema-getrieben**, kein Code pro Objekttyp:
- Jeder „Baustein" (Firewall, Switch, Software, …) = eine YAML-Datei in `schemas/<typ>.yaml` (Formularfelder in `abschnitte`/`felder`) + eine passende `rules/<typ>.yaml` (Risiko-Regeln, die gegen erfasste Daten ausgewertet werden). Neue Datei in `schemas/` = automatisch neuer wählbarer Baustein, kein Registry-Eintrag nötig (`app/services/schema_loader.py`).
- Feldtypen: `text, mehrzeiliger_text, zahl, datum, ja_nein, ja_nein_unbekannt, ja_nein_nicht_relevant, auswahl, mehrfachauswahl, liste, objekt_referenz`.
- Bedingte Feld-Sichtbarkeit: `sichtbar_wenn: {feld, operator, wert}` — lässt sich verketten (Feld A → Feld B → Feld C), siehe `schemas/software.yaml` als Referenzbeispiel (Kategorie → Anbieter-Dropdown → Freitext-Fallback bei „sonstige"). Wichtig: verkettete Sichtbarkeit brauchte serverseitig eine Nachbereinigung (`app/web/routes_objekt.py::_ist_sichtbar`), damit ausgeblendete Feldwerte beim Speichern nicht als Karteileichen ins Datenmodell wandern.
- Scoring-Kategorien (fix, nicht erweitern ohne Grund): `it_security`, `rechtliche_anforderungen`, `hardware_und_software`, `betriebsrisiken` (`bewertung/kategorien.yaml`).
- Auftrags-Sidebar (`_sidebar.html`, „Aktive Bausteine"-Fortschritt + „Noch nicht erfasst"-Chips) braucht `progress_data`/`findings`/`offene_punkte`/`massnahmen` im Template-Kontext — zentral gebündelt in `app/web/shared_context.py::build_sidebar_context()`.

## Aktueller Stand (zuletzt fertiggestellt)

- **v2.6.0 (2026-08-15)**: Alle 10 offenen Backlog-Karten (#281, #283, #284, #286, #287, #295, #296, #297, #298, #299) wurden implementiert, getestet (88/88 Tests grün) und in `main` konsolidiert:
  1. ✅ **#281 – QA-Testdaten bereinigen**: Bereinigung der „QA Inspector Team"-Reste aus den Testaufträgen.
  2. ✅ **#283 – Auftragsstatus & Vertraulichkeit editierbar**: Vertraulichkeit und Status lassen sich nun direkt aus Auftragsübersicht und Detailansicht ändern und persistieren.
  3. ✅ **#284 – Automatische Empfehlung bei Stammdaten-Änderung**: Client- und modellseitige Empfehlungen im Kontext (Rufbereitschaft bei 24/7, IT-Dienstleister bei fehlender IT).
  4. ✅ **#286 – Trennung Stammdaten & Kontext**: Visuelle Aufteilung im Bearbeitungsformular in getrennte Fieldsets für Stammdaten, Auftragssteuerung und Kontext.
  5. ✅ **#287 – Offene Punkte strukturieren**: Hierarchische Gruppierung nach Standort und Baustein/Hardware-Typ.
  6. ✅ **#295 – Status-Anpassungen / Ampelfarben**: Ampelfarben in der Standortübersicht vereinheitlicht (Vollständig=grün, Teilweise=gelb/orange, Unbekannt=grau).
  7. ✅ **#296 – Server-Detailfragen**: Schema um `standort_rack` (Rack/Höheneinheit) und `baujahr` erweitert.
  8. ✅ **#297 – Server & Virtualisierung: Pflichtfeld & Sichtbarkeit**: `wird_virtualisiert` als Pflichtfeld ganz oben; Hypervisor-spezifische Fragen nur sichtbar bei „ja".
  9. ✅ **#298 – Feld Festplatten-Slots**: `festplatten_slots` als `liste`-Typ mit Anbindungstypen (SATA/SAS/NVMe/M.2) in `server_virtualisierung` und `backup_storage`.
  10. ✅ **#299 – Feld Kommentar**: Kommentarfeld in allen 13 Schemas einheitlich ans Ende des letzten Abschnitts verschoben.
- **PR #6 (gemerged)**: Business-Software-Themenblock (CRM/DMS/ERP).
- **PR #7 (gemerged)**: „Noch nicht erfasst"-Leiste auf allen Auftragsseiten.
- Superthread-Board „Bestandsaufnahme-Tool" (Space „Software", board_id 15) enthält die laufende Kartenhistorie aller Änderungen.

## Abgeschlossene Backlog-Karten (v2.6.0)

Alle 10 Karten aus der ursprünglichen Backlog-Liste wurden erfolgreich umgesetzt und verifiziert.

## Größere offene strategische Fragen (noch nicht im Detail geplant — hier ansetzen)

Diese Punkte sind bewusst nur als Merkposten notiert, nicht als fertige Spezifikation:

1. **Themenblöcke / Organisation & Prozesse als eigener Baustein.** Laut Referenzmaterial macht organisatorischer/prozessualer Content ~2/3 des eigentlichen Assessment-Inhalts aus (Governance, Prozesse, Verantwortlichkeiten) — im Tool aktuell fast nur Technik-Bausteine vorhanden. Business-Software (CRM/DMS/ERP) war ein erster Schritt in diese Richtung. Verinice (BSI-IT-Grundschutz-Tool) behandelt Organisation als gleichwertiges Objekt neben Technik (ORP-/CON-Bausteine) — als Referenz-Architektur relevant.
2. **Generelles Objektmodell.** Server, Storage etc. sollten als saubere Basis-Objekte definiert sein, *bevor* weitere Themenblöcke draufgesetzt werden — aktuell historisch gewachsen (server_virtualisierung/server_cluster/vm als Geschwister-Schemas). Klärungsbedarf, wie das sauber vereinheitlicht wird, ohne bestehende Daten/Reports zu brechen.
3. **Backup & Recovery** als nächster großer Themenblock nach Firewall (im Sinne der Themenblock-Architektur wie Business-Software). DIN-SPEC-27076 trennt „Reaktion" von „Wiederherstellung" — als Bauplan relevant.
4. **Weitere Business-Software-Kategorien** über CRM/DMS/ERP hinaus (z. B. HR-Software, E-Commerce/Shop-Systeme) — aktuell nicht abgedeckt, das `software`-Schema mit Kategorie-Selector ist aber genau für diese Erweiterung gebaut.
5. **Referenzpreis-Katalog für Maßnahmen.** `kosten_richtwert`/`aufwand_richtwert` sind pro Regel in `rules/*.yaml` gepflegt (seit v2.1.0), aber `kosten_quelle` bleibt bis zur manuellen Bestätigung `"offen"`. Prüfen, ob das für den Verkaufsprozess ausreicht oder ob ein editierbarer globaler Preiskatalog nötig ist. Laut Konkurrenzanalyse (#290, siehe unten) ist ein fertiger, gestaffelter Maßnahmenkatalog mit Kostenschätzung eine echte Marktlücke — kein Konkurrenzprodukt bietet das.
6. **Cross-Objekt VLAN-Status.** Wenn Switch/Firewall den VLAN-Status auf Netzwerkebene erfassen, könnte das Access-Point-Feld `gast_wlan_isoliert` redundant werden. Eigene Design-Diskussion nötig, wie objektübergreifende Konsistenz sauber modelliert wird, ohne Doppelerfassung zu erzeugen.
7. **Erkenntnisse aus der Konkurrenzanalyse (Karte #290, Recherche vom 15.08.2026, von Marcel noch nicht gegengeprüft)** — konkrete Ideen für die Roadmap.

   > **TODO (Karte #312):** Diese Liste ist ein Rechercheergebnis, kein Auftrag — solange sie als ein Block dasteht, wird nichts davon umgesetzt. Sie muss mit Marcel durchgegangen und **zerlegt** werden: pro Idee entweder „bauen wir" (eigene Karte mit klarem Umfang), „später" (Backlog, mit Begründung) oder „bauen wir nicht" (begründet verworfen, damit die Frage nicht in einem halben Jahr erneut auftaucht). Zuerst zu bewerten sind die Maßnahmenkatalog-Punkte: der Kernbefund von #290 ist, dass **kein** recherchiertes Konkurrenzprodukt einen gestaffelten Maßnahmenkatalog mit Kostenschätzung bietet — dort liegt der Unterschied zum Markt, nicht bei Netzplänen oder zusätzlichen Kennzahlen. Beim Durchgehen sind zwei Punkte aus #290 zu streichen, die inzwischen erledigt sind: die Trennung Stammdaten/Kontext (#286 → umgesetzt in #303) und der Hinweis, Multiuser weiche vom Offline-Laptop-Prinzip ab (durch das Server-Deployment #301 beantwortet).

   Die Ideen im Einzelnen:
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
