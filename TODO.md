# TODO / Planungs-Handoff – Bestandsaufnahme-Tool

**Stand:** 2026-08-22 (v2.7.41). Diese Datei behandelt größere strategische Fragen. Der laufende Sitzungsfortschritt steht in `../001_bestandsaufnahme_tool-notizen/TODO.md` und `ARBEITSPROTOKOLL.md`. Feature-Dokumentation liegt unter `docs/` (pro Feature eine `.md`).

## Projektkontext

IT-Systemhaus-Tool zur einmaligen Vor-Ort-Bestandsaufnahme von Kunden-IT-Infrastruktur: strukturierte Erfassung → automatische Risikobewertung (Ampel-Score) → generierter .docx-Kundenbericht mit Handlungsempfehlungen. Zielgruppe: Kunden von 5 bis 1000 PCs mit **einem einzigen** Tool (siehe Leitplanke 1 unten). Kein Scanner, keine Zugangsdaten nötig — ein Termin reicht (siehe Konkurrenzanalyse unten für die Positionierung).

## Repo & Stack

- Pfad: `/Users/marcel/001_Vibe_Code/001_bestandsaufnahme_tool` (Hauptcheckout — **hier läuft der Dev-Server**, siehe Leitplanke 5)
- GitHub: `https://github.com/deMarcel97/bestandsaufnahme-tool`, Branch `main`
- Stack: FastAPI + Jinja2 + Pydantic v2 + PyYAML, Storage als YAML-Dateien unter `data/` (kein DB-Server)
- Läuft zusätzlich als Dienst auf einem internen Server — Zugang und Arbeitsweise siehe `CLAUDE.md` und `deploy/`
- Aktuelle Version: 2.7.41 (siehe `CHANGELOG.md` für volle Historie)
- Tests: `PYTHONPATH=. venv/bin/pytest` (Stand jetzt: 294+ Tests, alle grün)
- Feature-Dokumentation: `docs/` (pro Feature eine `.md`, Index in `docs/README.md`)

### Architektur-Kurzreferenz (wichtig, bevor man Neues plant)

Alles ist **schema-getrieben**, kein Code pro Objekttyp:
- Jeder „Baustein" (Firewall, Switch, Software, …) = eine YAML-Datei in `schemas/<typ>.yaml` (Formularfelder in `abschnitte`/`felder`) + eine passende `rules/<typ>.yaml` (Risiko-Regeln, die gegen erfasste Daten ausgewertet werden). Neue Datei in `schemas/` = automatisch neuer wählbarer Baustein, kein Registry-Eintrag nötig (`app/services/schema_loader.py`).
- Feldtypen: `text, mehrzeiliger_text, zahl, datum, ja_nein, ja_nein_unbekannt, ja_nein_nicht_relevant, auswahl, mehrfachauswahl, liste, objekt_referenz`.
- Bedingte Feld-Sichtbarkeit: `sichtbar_wenn: {feld, operator, wert}` — lässt sich verketten (Feld A → Feld B → Feld C), siehe `schemas/software.yaml` als Referenzbeispiel (Kategorie → Anbieter-Dropdown → Freitext-Fallback bei „sonstige"). Wichtig: verkettete Sichtbarkeit brauchte serverseitig eine Nachbereinigung (`app/web/routes_objekt.py::_ist_sichtbar`), damit ausgeblendete Feldwerte beim Speichern nicht als Karteileichen ins Datenmodell wandern.
- Scoring-Kategorien (fix, nicht erweitern ohne Grund): `it_security`, `rechtliche_anforderungen`, `hardware_und_software`, `betriebsrisiken` (`bewertung/kategorien.yaml`).
- Auftrags-Sidebar (`_sidebar.html`, „Aktive Bausteine"-Fortschritt + „Noch nicht erfasst"-Chips) braucht `progress_data`/`findings`/`offene_punkte`/`massnahmen` im Template-Kontext — zentral gebündelt in `app/web/shared_context.py::build_sidebar_context()`.

## Aktueller Stand (zuletzt fertiggestellt)

- **v2.7.41 (2026-08-22)**: Feature-Dokumentation unter `docs/` eingeführt (#416).
- **v2.7.40 (2026-08-21)**: HANDOFF_antigravity.md/HANDOFF_claude_code.md aus dem Repo entfernt (#415), Duplikat des Notizen-Ordners.
- **v2.7.39 (2026-08-21)**: Dark Mode global kaputt seit #379-Fix behoben (#413).
- **v2.7.38 (2026-08-21)**: M365-Lizenzmatrix Fundament (#408) -- lizenz-bewusste Regeln, Tier-Blindheit-Fix.
- **v2.7.37 (2026-08-21)**: Topologie-Bereinigungen (#402), Vorläufig-Hinweis (#403), Dialog-UX (#403).
- **v2.7.36 (2026-08-19)**: Phantom-Backup-ISP (#362), ungespeicherte Änderungen (#357).
- **v2.7.35 (2026-08-19)**: Security Headers (#373), Offline-Mermaid (#372), Fehlerseiten/Print (#375), Barrierefreiheit (#374), Priorisierung (#369), Form-Submit (#364), Baustein-Bezeichnung (#376), Key-Facts (#366).
- **v2.7.34 (2026-08-19)**: Software-Review Befunde & Wizard UX (#363, #364-#371).
- **v2.7.33 (2026-08-19)**: Erfassungs-Wizard Direkteinstieg & Wiederaufnahme (#361).
- **v2.7.32 (2026-08-18)**: Wizard Vollausbau 13 Schritte + automatische Baustein-Erstellung (#325).
- **v2.7.30 (2026-08-17)**: Hersteller- und Modelllisten pro Hersteller (#355).
- **v2.7.28 (2026-08-16)**: Erfassungs-Wizard initial (#325).
- **v2.7.27 (2026-08-16)**: Massnahmenkatalog Dringlichkeit & Förderprogramm (#322).
- **v2.7.24 (2026-08-16)**: Netzwerktopologie Generator (#324).
- **v2.7.22 (2026-08-16)**: Storage/Backup-Trennung + Organisation & Prozesse (#323).
- **v2.7.21 (2026-08-16)**: Beteiligte & Support-Matrix (#321).
- **v2.7.20 (2026-08-16)**: Cloud-Bausteine ohne Standort (#315).
- **v2.7.19 (2026-08-16)**: Offene Punkte hierarchisch (#314).
- **v2.7.14 (2026-08-16)**: Beteiligte/Verträge/Unterlagen/Projektrahmen (#316).
- **v2.7.0 (2026-08-15)**: Server-Deployment (#301).
- **v2.6.0 (2026-08-15)**: 10 Backlog-Karten (#281-#299).

Siehe `CHANGELOG.md` für die vollständige Historie und `docs/` für Feature-Dokumentation.

## Größere offene strategische Fragen (noch nicht im Detail geplant — hier ansetzen)

Diese Punkte sind bewusst nur als Merkposten notiert, nicht als fertige Spezifikation:

1. **~~Themenblöcke / Organisation & Prozesse als eigener Baustein.~~** ERLEDIGT (#323, v2.7.22): Baustein `organisation_prozesse` mit `standortbezug: false` implementiert. Siehe `docs/cloud-bausteine.md`.
2. **~~Generelles Objektmodell.~~** TEILWEISE ERLEDIGT: Storage/Backup-Trennung (#323), Server-Cluster/VM-Verknüpfung (#298). Historisch gewachsene Schemas bleiben bestehen, aber sauber getrennt. Siehe `docs/schema-system.md`.
3. **~~Backup & Recovery als nächster grosser Themenblock.~~** ERLEDIGT (#323, v2.7.22): `backup.yaml` & `rules/backup.yaml` mit BSI-konformer Bewertung. Siehe `docs/technikobjekt-erfassung.md`.
4. **Weitere Business-Software-Kategorien** über CRM/DMS/ERP hinaus (z. B. HR-Software, E-Commerce/Shop-Systeme) -- aktuell nicht abgedeckt, das `software`-Schema mit Kategorie-Selector ist dafür gebaut.
5. **Referenzpreis-Katalog für Massnahmen.** `kosten_richtwert`/`aufwand_richtwert` sind pro Regel gepflegt. `kosten_quelle` bleibt bis zur manuellen Bestätigung `"offen"`. Prüfen, ob ein editierbarer globaler Preiskatalog nötig ist.
6. **Cross-Objekt VLAN-Status.** Wenn Switch/Firewall den VLAN-Status erfassen, könnte Access-Point `gast_wlan_isoliert` redundant werden. Design-Diskussion nötig.
7. **~~Erkenntnisse aus der Konkurrenzanalyse (Karte #290).~~** GROSSTEILS ERLEDIGT:
   - ~~Kosten x Dringlichkeit zweiachsig~~ -> ERLEDIGT (#322, v2.7.27). Siehe `docs/massnahmenkatalog.md`.
   - ~~Förderprogramm-Feld~~ -> ERLEDIGT (#322, v2.7.27).
   - ~~Netzwerktopologie-Diagramm~~ -> ERLEDIGT (#324, v2.7.24). Siehe `docs/netzwerktopologie.md`.
   - ~~Executive-Abschnitt im Bericht~~ -> ERLEDIGT (`export_managementsummary`).
   - Getrennte Kennzahlen (Risk-Score vs. Issues-Score) -- offen.
   - Optionaler Diff-/Update-Modus für Folgebesuche -- offen.
   - Positionierung "Kein Scanner, ein Termin reicht" als USP -- offen (Vermarktung, nicht Technik).

## Leitplanken (aus bisherigen Diskussionen mit Marcel — bitte einhalten)

1. **Ein einheitliches Tool für alle Kundengrößen** (5-PC- bis 1000-PC-Kunden) — keine Fragen, die nur für eine Größenordnung relevant sind. Kein separates „Enterprise-Modus".
2. **Bei Feld-Abhängigkeits-/UX-Fragen zuerst Optionen durchsprechen**, nicht direkt umsetzen — Marcel möchte hier mitentscheiden, bevor Code entsteht. Bei eindeutigen Bugs (kein Design-Ermessen nötig) ist direktes Fixen dagegen in Ordnung.
3. **Jede Änderung bekommt eine Karte auf dem Superthread-Board** „Bestandsaufnahme-Tool" (Space „Software", space_id 6, board_id 15), getaggt Feature/Bug, mit Kommentaren „Lösungsweg" (Ursachenanalyse) und „Lösung" (was umgesetzt wurde, inkl. PR-Link) getrennt vom Beschreibungstext der Karte.
4. **Jede Änderung bekommt eine neue Versionsnummer** (SemVer) + Eintrag in `CHANGELOG.md` + Sync in `README.md`.
5. **Jede Änderung muss sowohl lokal sichtbar sein als auch als GitHub-PR landen.** Wichtig: Der laufende Dev-Server (Port 8000, `reload=True`) bedient **ausschließlich** den Hauptcheckout `/Users/marcel/001_Vibe_Code/001_bestandsaufnahme_tool` — niemals eine `.claude/worktrees/*`-Kopie. Arbeitsweise: neuer Branch von `main` **im Hauptcheckout selbst**, dort implementieren (Dev-Server zieht Änderungen automatisch), committen, pushen, PR öffnen (`gh pr create`). Ein reiner Branch-Wechsel im Hauptcheckout (z. B. für ein unabhängiges Thema) lässt den Dev-Server währenddessen den jeweils ausgecheckten Stand zeigen — das ist normal, aber gut zu wissen, falls „das Feature ist plötzlich weg" auftaucht.
6. **Keine Features/Abstraktionen über die gestellte Aufgabe hinaus.** Drei ähnliche Zeilen sind besser als eine verfrühte Abstraktion für einen hypothetischen Zukunftsfall.
