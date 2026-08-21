# Changelog

Alle nennenswerten Änderungen am IT-Bestandsaufnahme-Tool werden hier dokumentiert.

Format angelehnt an [Keep a Changelog](https://keepachangelog.com/), Versionierung nach [Semantic Versioning](https://semver.org/) (MAJOR.MINOR.PATCH): MAJOR = Breaking Change, MINOR = neue Funktionalität (abwärtskompatibel), PATCH = Bugfix.

## [2.7.38] - 2026-08-21

### Added
- **M365-Lizenzmatrix: Fundament (Lizenzfeld, Regel-Generator, Fix Tier-Blindheit) (#408)**:
  - Neues Mehrfachauswahl-Feld `m365_lizenzen` im Schema `m365_security` mit allen 15 gängigen M365/O365- und Standalone-Lizenz-SKUs.
  - Lizenz-bewusste Regeln in `rules/m365_lizenzmatrix.yaml` für die 3 Pilot-Features: Conditional Access (`conditional_access`), Defender for Office 365 (`defender_o365_p1`) und Purview Audit Standard (`audit_standard`).
  - Trennung in Lizenz-Fehlt-Trigger (Advisory/Upgrade) und Fehlkonfigurations-Trigger (lizenziert, aber nicht aktiv/konfiguriert).
  - Veraltete tier-blinde Regeln in `rules/m365_security.yaml` entfernt.
  - Schweregrad von Defender for Office 365 bei Fehlkonfiguration von "mittel" auf "hoch" angehoben.

## [2.7.37] - 2026-08-21

### Fixed
- **Netzwerktopologie: Platzhalter-Werte in Labels bereinigt, echte Anbindungsdaten auf Kanten (#402)**:
  - Platzhalter wie "sonstige"/"unbekannt"/"diverse" werden aus Hersteller-/Modell-Labels gefiltert (`clean_brand_model`), keine redundanten Label-Zeilen mehr im Netzplan.
  - WAN-/Firewall-/Switch-Kanten zeigen echte erfasste Anbindungsdaten (Anschlussart, LAG-Typ, Geschwindigkeit) statt hartcodierter Platzhaltertexte ("Uplink"/"Server LAN"/"LAN").
- **Wizard: redundante 2. Internetleitung erfassbar (#402)**:
  - Schritt 3 ("Internetanbindung") erfasst jetzt Anbieter, Anschlussart, Bandbreite und Failover-Verfahren einer redundanten Backup-Leitung, sobald "Ja (Fallback vorhanden)" gewählt wird. Fließt als eigenes Anbindungs-Objekt in Standort und Topologie ein.
- **Fortschrittsanzeige widersprach sich (#402)**: Sidebar-Prozentanzeige zählte bisher nur Pflichtfelder und stand nach einem Wizard-Durchlauf sofort auf 100 %, obwohl die Objekttabelle "teilweise" zeigte. Zählt jetzt alle sichtbaren Schema-Felder, Anzeige ist realistisch (~40-50 % nach einem schnellen Durchlauf).
- **Bewertungskachel: Vorläufig-Hinweis bei unvollständiger Erfassung (#403)**: Die KPI-Kachel "Gesamtbewertung" zeigt bei niedrigem Erfassungsstand jetzt "Vorläufig: <Stufe>" mit Badge "Erfassungsstand: X %" direkt in der Kachel statt nur in einer kleinen Box darunter — konsistent auf allen drei Seiten (Bewertung, Auftrag-Übersicht, Auftrag-Detail).
- **Dialog-Buttons außerhalb Viewport (#403)**: Lange Dialoge (z. B. "Neuen Auftrag anlegen") begrenzen jetzt ihre Höhe, der Dialog-Body scrollt intern, Titel und Aktions-Buttons bleiben immer sichtbar.

## [2.7.36] - 2026-08-19

### Fixed
- **Netzwerktopologie: Phantom-Backup-ISP entfernt (#362)**:
  - Backup-Leitungen werden nur noch gerendert, wenn `redundante_anbindung` = "ja" gesetzt ist. Verhindert Phantom-ISP-Knoten in der Topologie bei Kunden ohne redundante Anbindung.
  - `redundante_anbindung`-Feld zum `Internetanbindung`-Modell hinzugefügt (wurde zuvor vom Wizard uebergeben aber vom Modell ignoriert).
  - Standard-Uplink-Labels ("Trunk / LAG 10G", "Server Uplink (10G/LAG)", "PoE+ / 1G", "Trunk Uplink") durch generisches "Uplink" ersetzt - keine erfundenen Verbindungstypen mehr.

### Added
- **Warnung bei ungespeicherten Aenderungen (#357)**:
  - `beforeunload`-Event auf allen POST-Formularen. Nutzer wird beim Verlassen der Seite mit ungespeicherten Aenderungen gewarnt.
  - Neue `static/js/unsaved-changes.js`, in `base.html` eingebunden.

## [2.7.35] - 2026-08-19

### Added
- **Security & Due-Diligence Standards (#373)**:
  - Globale Security-Headers Middleware hinzugefügt (`X-Frame-Options: SAMEORIGIN`, `X-Content-Type-Options: nosniff`, `X-XSS-Protection: 1; mode=block`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy`, `Content-Security-Policy`).
- **Offline-Fähigkeit für Mermaid.js (#372)**:
  - `mermaid.min.js` als lokales Asset unter `/static/js/mermaid.min.js` gebündelt — vollständige Visualisierung der Netzwerktopologie ohne externe Internetverbindung vor Ort beim Kunden.
- **Custom HTML-Fehlerseiten & Print-Stylesheet (#375)**:
  - Benutzerfreundliche HTML-Fehlerseiten `errors/404.html` und `errors/500.html` für Web-Browser.
  - Print-Stylesheet (`@media print`) für sauberen Ausdruck und PDF-Export ohne Navigationselemente.
  - `maxlength`-Attribute für Textfelder zum Schutz vor Layout-Brüchen.
- **Accessibility / Barrierefreiheit (#374)**:
  - Formular-Labels (`<label for="...">`) durchgängig mit Eingabefeldern (`<input id="...">`) verknüpft (Screen-Reader-Konformität).
- **Priorisiertes Dashboard für Offene Punkte (#369)**:
  - 3-stufige Priorisierung (Kritisch, Wichtig, Hinweise) mit Dashboard-Kennzahlen und interaktiven Filter-Tabs.

### Fixed
- **Form-Submit im Modal-Dialog (#364)**:
  - `novalidate`-Attribut auf Dialog-Formularen und serverseitige Validierung mit klarem Feedback zur Vermeidung stiller Blockaden unter Browser-Automation.
- **Baustein-Modellnamen im Wizard (#376)**:
  - `format_baustein_bezeichnung` priorisiert das Modell, um präzise Baustein-Namen zu generieren (z. B. `Firewall FortiGate 60F`, `Switch Catalyst 9200-24T`, `Server PowerEdge R740`).
- **Wizard-Zusammenfassung Key-Facts Datenvorschau (#366)**:
  - Vollständiger Key-Facts-Extraktor mit automatischem Fallback für alle 13 Meilensteine.

## [2.7.34] - 2026-08-19

### Added
- **Software-Review Befunde & Wizard UX-Optimierungen (#363, #364-#371)**:
  - **#364**: Formular-Submit-Zuverlässigkeit in Dialogen und Abschlussformularen optimiert (`#neu-auftrag-modal`, `#form-wizard-abschliessen`).
  - **#365**: Baustein-Kategorien im Auftrags-Modal und auf der Stammdaten-Seite in 5 thematische Fachbereiche gruppiert (Netzwerk & Perimeter, Server & Rechenzentrum, Speicher & Sicherung, Clients & Workplace, Cloud & Governance).
  - **#366**: Ausführliche Key-Facts-Datenvorschau auf der Wizard-Zusammenfassungsseite (`wizard_zusammenfassung.html`) für alle 13 Meilensteine.
  - **#367**: Differenzierte Status-Marker im Wizard: Erfasst (`✓`), Übersprungen (`⊘`) und Ausstehend mit angepasster Prozent- und Zählerberechnung.
  - **#369**: Sichtbarkeits-Filter (`sichtbar_wenn`) in `progress.py::collect_offene_punkte` integriert, um irrelevante Warnungen bei inaktiven Sub-Feldern zu vermeiden.
  - **#370**: Konsistente Groß-/Kleinschreibung und Markenbezeichnungen bei auto-generierten Technik-Objekten (z. B. `Backup Veeam`, `Storage Synology`, `USV APC`).
  - **#371**: SVG-Favicon hinzugefügt und 404-Fehler für `/favicon.ico` behoben.

## [2.7.33] - 2026-08-19

### Added
- **Interaktiver Erfassungs-Wizard: Direkteinstieg, Wiederaufnahme-Dialog & Meilenstein-Fortschritt (#361)**:
  - Checkbox „Direkt mit interaktiver Bestandsaufnahme (Guide) starten“ im Dialog „Neuen Auftrag anlegen“ mit automatischer Weiterleitung in den Wizard.
  - Strukturierte Wiederaufnahme-Seite (`wizard_resume.html`) bei bestehendem Erfassungsfortschritt mit klarer Wahl zwischen „Bestehenden Erfassungsstand fortsetzen & prüfen“ und „Interaktive Erfassung neu starten (Zurücksetzen)“.
  - Prominente Prozentanzeige und Meilenstein-Leiste im Header des Erfassungs-Wizards mit Status-Häkchen (✓), aktivem Schritt-Fokus und Prozentbalken.
  - Prominente Einstiegspunkte für den interaktiven Guide in der Sidebar, auf der Auftragsübersicht und in der Erfassungsansicht.
  - Reorganisation der Sidebar-Navigation: „Stammdaten“ vor „Erfassung“ platziert (`Übersicht` → `Stammdaten` → `Erfassung`).

## [2.7.32] - 2026-08-18

### Added
- **Erfassungs-Wizard Vollausbau & automatische Baustein-Erstellung (#325)**:
  - Vollausbau des Erfassungs-Wizards von 6 auf alle 13 relevanten IT-Themenbereiche der Bestandsaufnahme (Auftragsgrunddaten, Standort, Internetanbindung, Firewall, Switch, WLAN/AP, Server/Virtualisierung, Storage/NAS, Backup, USV, Clients/Arbeitsplätze, M365/Cloud, Organisation & Prozesse).
  - Automatisches Erstellen und Zuordnen aller aktivierten Bausteine und schemakonformen `TechnikObjekt`-Instanzen beim Wizard-Abschluss.
  - Horizontale, klickbare Schritt-Navigationsleiste zum direkten Springen zwischen bereits durchlaufenen Themen.
  - Dynamische Feld-Einblendungen je nach Vorhandensein ("Wird eingesetzt? Ja/Nein").

### Fixed
- **Navigations- und Methoden-Fehler im Erfassungs-Wizard (#325)**:
  - HTTP 405 Method Not Allowed Fehler bei Überspringen- und Abbrechen-Links behoben (Unterstützung für GET und POST).
  - Korrekte Rückwärts-Navigation über `/auftrag/{id}/wizard/back` und direktes Anspringen über `/auftrag/{id}/wizard/goto/{step}`.

## [2.7.31] - 2026-08-18


### Fixed
- **Doppeltes Kommentarfeld in Technik-Formular (#354)**: Das hartcodierte "Notizen"-Feld aus `technik/form.html` entfernt — jedes Schema definiert bereits ein `kommentar`-Feld, sodass zwei Kommentarboxen übereinander erschienen. Das Modellfeld `notiz` bleibt für Standort-Formulare erhalten.

## [2.7.30] - 2026-08-17

### Added
- **Modell-Auswahllisten pro Hersteller (#355)**: Recherche und Ergaenzung echter Modellreihen (2011-2026) fuer Firewall (Fortinet, Sophos, Palo Alto, Cisco, WatchGuard, SonicWall, Juniper, Check Point, Barracuda), Switch (Cisco, Aruba/HPE, Dell, Ubiquiti), Server (Dell PowerEdge, HPE ProLiant, Lenovo ThinkSystem, Fujitsu PRIMERGY), USV (APC, Eaton) und Access Point (Cisco, Aruba/HPE, Ubiquiti). Pro Hersteller ein eigenes Auswahlfeld mit `sichtbar_wenn`-Bedingung; Freitext-Fallback fuer Sonstiges. Template-Fix fuer numerische Modell-Werte (Check Point 600/700).

## [2.7.29] - 2026-08-17

### Added
- **Hersteller-Listen erweitert (#355)**: Recherche und Ergänzung aller relevanten Hardware-Hersteller der letzten 15 Jahre (2011–2026) für sechs Baustein-Schemas: Firewall (+SonicWall, Juniper, Check_Point, Barracuda, Zyxel, Stormshield), Switch (+Juniper, Extreme_Networks, Zyxel, D-Link, TP-Link, Brocade_Ruckus, Allied_Telesis), Server (+Cisco_UCS, Huawei, ASUS, Gigabyte), Storage (+Pure_Storage, IBM, Hitachi, Fujitsu, Lenovo, Buffalo), USV (+Generex, Socomec, CyberPower, FSP), Access Point (+Ruckus, Zyxel, TP-Link, DrayTek, LANCOM, Extreme_Networks). Jeder Eintrag mit Textbaustein fuer den Analysebericht.

## [2.7.28] - 2026-08-16

### Added
- **Erfassungs-Wizard / Interaktive Erfassung (#325)**: Geführter, linearer Durchlauf durch die wichtigsten Bausteine beim Anlegen eines Auftrags. Button "Interaktive Erfassung starten" auf der Stammdaten-Seite. 7 Schritte: Auftragsgrunddaten, Standort-Grunddaten, Internetanbindungen, Firewall, Switch, Backup, Zusammenfassung. Dynamisches Ein-/Ausblenden von Detailfeldern basierend auf Ja/Nein-Antworten. Fortschrittsspeicherung in `wizard_progress.yaml` pro Auftrag mit Wiedereinstieg. Überspringen nicht-relevanter Schritte möglich. Zusammenfassung aller erfassten Daten am Ende. (Noch ohne automatisches Anlegen der Bausteine — TODO).

## [2.7.27] - 2026-08-16

### Added
- **Maßnahmenkatalog: Dringlichkeitsachse und Förderprogramm (#322)**: Erweiterte Priorisierung um `dringlichkeit`-Feld (hoch/mittel/niedrig) als zweite Achse neben `prioritaet` — ermöglicht zweiachsiges Modell (Kosten × Dringlichkeit) analog DIN SPEC 27076. Neues `foerderprogramm`-Feld für optionale Metadaten (z. B. "Mittelstand Digital", "BSI-Förderung"). Ändert: Modell, Formular, Tabelle, MD/CSV-Export, Berichts-Generator.

## [2.7.26] - 2026-08-16

### Added
- **Verweis auf lokale Arbeitsnotizen in `CLAUDE.md` (#327)**: `TODO.md` und `ARBEITSPROTOKOLL.md` liegen ab jetzt in `../001_bestandsaufnahme_tool-notizen/`, einem Geschwisterordner ausserhalb der Versionskontrolle — im selben Muster wie der bestehende Verweis auf `deploy/server.local.env`. Grund: Antigravity hatte ein gleichwertiges Protokoll bereits in `scratch/` geführt, das seit #318 gitignored ist und damit weder einen Clone noch den Server noch einen Subagenten im Worktree erreichte.

### Changed
- **Zwei unabhängig entstandene Arbeits-Manifeste zusammengeführt**: Claude Code und Antigravity hatten je ein eigenes Dokument für Marcels Arbeitsvorlieben angelegt. Beide lagen zufällig schon am selben externen Ort; zusammengeführt in `ARBEITSWEISE.md` (nicht Teil dieses Repos), ergänzt um die QA-Subagent-Pflicht und `Closes #<id>` im PR-Body aus dem Antigravity-Manifest.

## [2.7.25] - 2026-08-16

### Fixed
- **Mermaid-Topologie Edge-Escaping & HTMX Event Listener**:
  - Sämtliche Verbindungspfeil-Labels im Mermaid-Diagramm (`topology_generator.py`) mit Anführungszeichen abgesichert, um Syntaxfehler bei Sonderzeichen (wie Klammern `(10G/LAG)`) zu verhindern.
  - Event-Listener `htmx:afterSwap` in `topology.js` sicher an `document` gebunden.

## [2.7.24] - 2026-08-16

### Added
- **Netzwerktopologie: Automatischer Netzplan aus Verbindungsdaten (#324)**:
  - **Topologie-Generator (`app/services/topology_generator.py`)**: Funktion `generate_network_topology_mermaid` generiert strukturierte, farbcodierte Mermaid-Flowcharts mit vollständiger Hierarchie: WAN/Internet (Anbindungen & Bandbreiten) -> Perimeter (Firewalls, HA-Cluster) -> Core-Switching (Trunk, LAG, Stacking) -> Access-Switching (Edge, PoE) -> Server & Storage (Hypervisoren, SAN/NAS, iSCSI, FC) -> Virtuelle Maschinen (VMs mit OS, Specs, Rollen) -> WLAN Access Points (Wi-Fi Standards, PoE+, Gast-WLAN) -> Endgeräte & Clients.
  - **Analysebericht & DOCX-Export**: Integration in Kapitel 4 („Technische Infrastruktur und Fachkapitel") mit eigenem Unterabschnitt „Netzwerktopologie" pro Standort. Im Word-Export (.docx) als formatierter Mermaid-Diagrammblock integriert.
  - **Interaktive Web-UI Darstellung (`erfassung.html` & `uebersicht.html` / `detail.html`)**: Automatische Einbettung via Mermaid.js mit Zoom In (+), Zoom Out (-), 1:1 Reset, Maus-Pan (Drag & Drop), Mausrad-Zoom und Vollbild-Modus. Schnelle Vorschau per Knopfdruck auf der Übersichtsseite.
  - **Umfassende Testabdeckung**: Dedizierte Unittests in `tests/test_topology_generator.py`.

## [2.7.23] - 2026-08-16

### Changed
- **Sidebar-Layout & Scrollbarkeit (#326)**:
  - **Scrollbarkeit**: Linke Auftrags-Sidebar mit `height: 100vh`, `max-height: 100vh` und dezentem `overflow-y: auto` scrollbar gemacht.
  - **Kompaktere Navigation**: Zeilenabstände, Schriftgrößen und Paddings der Menüpunkte (Übersicht, Erfassung, Stammdaten, Beteiligte etc.) optimiert.
  - **Kompaktere Baustein-Listen & Chips**: Reduzierte Abstände für Fortschrittszeilen, Balken und „Noch nicht erfasst"-Chips im unteren Bereich der Sidebar.

## [2.7.22] - 2026-08-16
 
### Added
- **Trennung Storage vs. Backup & Neuer Baustein Organisation & Prozesse (#323)**:
  - **Neuer Baustein Storage (`storage.yaml` & `rules/storage.yaml`)**: Detaillierte Erfassung von Bereitstellungsart (Shared SAN/NAS vs. Local Host/HCI), Herstellern (NetApp, Dell, Huawei, HPE, Synology, QNAP, TrueNAS), Protokollen (iSCSI, FC, NFS, SMB, SAS), Controller-Redundanz, lokalen Technologien (ZFS, LVM-Thin, Hardware-RAID, Software-RAID, Ceph/vSAN), Medientypen (NVMe, SSD, Hybrid, HDD), Kapazitäten, Füllgrad und Wartungsvertragsstatus inkl. automatischer Regelauswertung und Risikobewertung.
  - **Neuer Baustein Backup & Recovery (`backup.yaml` & `rules/backup.yaml`)**: Detaillierte Erfassung von Backup-Software (Veeam, Synology Active Backup, Datto, Acronis, Proxmox Backup Server, Commvault, M365 Backup), Sicherungsumfang (Mehrfachauswahl), primären & sekundären Offsite-Zielen (S3 Object Storage, 2. Standort, Band/Tape, RDX), Unveränderbarkeit (Immutability / Ransomware-Schutz), RPO, RTO, Wiederherstellungstests und Monitoring/Alerting inkl. dedizierter BSI-konformer Bewertungsregeln.
  - **Neuer Baustein Organisation & Prozesse (`organisation_prozesse.yaml` & `rules/organisation_prozesse.yaml`)**: Standortübergreifender Baustein (`standortbezug: false`) zur Erfassung und Bewertung von IT-Notfallhandbuch, Wiederanlaufplan (Disaster Recovery), IT-Infrastrukturdokumentation, unterschriebenen Sicherheitsrichtlinien, Passwort-Policies & MFA, Passwort-Managern, BYOD-Regelung, Gäste-WLAN-Segmentierung, Awareness-Schulungen, Zutrittskontrolle Serverraum, standardisiertem Offboarding-Prozess und DSGVO-Auftragsverarbeitungsverträgen.
  - **Unterstützung für Mehrfachauswahl-Felder**: Erweiterung von `schema_loader.py`, `routes_objekt.py`, `rule_engine.py`, `report_builder.py` und Web-Formularen zur Unterstützung des Feldtyps `mehrfachauswahl`.

## [2.7.21] - 2026-08-16
 
### Added
- **Beteiligte: Support-Matrix mit Technik-Verknüpfung, Notfallkontakt & SLAs (#321)**:
  - **Erweitertes Modell `Beteiligter`**: Neue Felder `objekt_id` (Verknüpfung zu Technik-Objekt), `notfall_telefon` (Notfallnummer / 24/7 Hotline), `erreichbarkeit` (Service-Zeiten) und `sla_reaktionszeit` (vereinbarte SLA / Reaktionszeit).
  - **Erfassungsformular (`/auftrag/{id}/beteiligte`)**: Dropdown zur direkten Zuweisung eines Technik-Objekts (`Typ: Bezeichnung`) oder `-- Allgemein / Gesamt-IT --`, Eingabefelder für Notfallkontakt, Erreichbarkeit und SLAs, Direktlink `+ Neues Technik-Objekt anlegen ↗` sowie Info-Hinweis bei noch fehlenden Objekten.
  - **Analysebericht & DOCX-Export**: Neues Kapitel 2 „Ansprechpartner & Support-Matrix" mit formatierter Übersichtstabelle (Spalten: System/Bereich, Ansprechpartner & Rolle, Service- & Notfallkontakt, Service-Zeiten & SLA). Automatische Maskierung persönlicher Daten im anonymisierten Export.

## [2.7.20] - 2026-08-16

### Changed
- **Cloud-Bausteine ohne Standortzuweisung (#315)**: Bausteine mit `standortbezug: false` (wie Microsoft 365 & Security) können jetzt ohne Zuweisung zu einem physischen Standort erfasst und verwaltet werden.
- **Formulare & Modellierung (#315)**: `TechnikObjekt.standort_id` ist optional (`Optional[str] = None`). Bei Schemas mit `standortbezug: false` zeigt das Formular ein deaktiviertes Feld „Standortübergreifend (Cloud)" und sendet leere `standort_id`.
- **Erfassungsübersicht & Bericht (#315)**: Eigener Abschnitt „Standortübergreifend / Cloud-Dienste" auf der Erfassungsseite (`/auftrag/{id}/erfassung`) sowie im generierten Analysebericht unter Kapitel 3 („Standortübergreifende Infrastruktur & Cloud-Dienste") und Kapitel 4.

## [2.7.19] - 2026-08-16

### Changed
- **Offene Punkte hierarchisch nach Standort und Thema strukturiert (#314)**: Die Seite `/auftrag/{id}/offene_punkte` gliedert offene Punkte jetzt nach Standort (z. B. Standort 1, Standort 2, Standortübergreifend) und darunter nach Themenbereichen/Bausteinen (z. B. M365 Security, Firewall, Dokumente & Unterlagen).
- **Ausklappbare Toggles & Zähler (#314)**: Standorte und Themenbereiche lassen sich per Klick ein- und ausklappen (`<details>`/`<summary>`-Akkordeon mit Zähler-Badges). Schnellauswahl über „Alle aufklappen" und „Alle zuklappen".

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
