# Feature-Dokumentation

Jedes Feature hat eine eigene `.md`-Datei. Neues Feature = neue Datei,
Feature bearbeitet = Doku aktualisieren.

## Auftragsverwaltung & Erfassung

| Datei | Feature | Karten |
|---|---|---|
| [auftragsverwaltung.md](auftragsverwaltung.md) | Auftrag CRUD, Stammdaten, Unternehmenskontext, Status, Vertraulichkeit | #283, #286, #302, #303, #309 |
| [standortverwaltung.md](standortverwaltung.md) | Standort CRUD, Internetanbindungen, Löschschutz | #295, #307 |
| [technikobjekt-erfassung.md](technikobjekt-erfassung.md) | Schema-getriebene Formulare, sichtbar_wenn, Mehrfachauswahl, Listenfelder | #296, #297, #298, #299, #354 |
| [schema-system.md](schema-system.md) | YAML-Schemas, Feldtypen, Textbausteine, standortbezug | #299 |
| [hersteller-modelllisten.md](hersteller-modelllisten.md) | Pro-Hersteller Modell-Auswahllisten mit Freitext-Fallback | #355 |
| [erfassungs-wizard.md](erfassungs-wizard.md) | Geführter Modus, 13 Schritte, Wiederaufnahme, automatische Baustein-Erstellung | #325, #361 |
| [cloud-bausteine.md](cloud-bausteine.md) | Bausteine ohne Standortbezug (M365, Organisation & Prozesse) | #315 |

## Analyse & Bewertung

| Datei | Feature | Karten |
|---|---|---|
| [rule-engine.md](rule-engine.md) | Automatische Risikoanalyse aus rules/*.yaml | — |
| [bewertungssystem.md](bewertungssystem.md) | Evaluator, Kategorien, Skala, Ampel-Scores | #294 |
| [findings-management.md](findings-management.md) | Findings, Status-Workflow, Finding->Massnahme | — |
| [massnahmenkatalog.md](massnahmenkatalog.md) | Massnahmen CRUD, Dringlichkeit, Förderprogramm | #322 |
| [offene-punkte.md](offene-punkte.md) | Hierarchische Gliederung, Priorisierung, Akkordeon | #287, #314, #369 |

## Bericht & Export

| Datei | Feature | Karten |
|---|---|---|
| [berichtsexport.md](berichtsexport.md) | DOCX, Markdown, CSV, Management-Summary, Vertraulichkeitsfilter | #292, #310 |
| [netzwerktopologie.md](netzwerktopologie.md) | Mermaid-Generator, interaktive Web-UI, Offline | #324, #362, #372, #402 |

## Auftragserweiterungen

| Datei | Feature | Karten |
|---|---|---|
| [beteiligte-support-matrix.md](beteiligte-support-matrix.md) | Kontakte, Notfallkontakt, SLAs, Objekt-Verknüpfung | #321 |
| [vertraege.md](vertraege.md) | Wartungsverträge, Kündigungsfrist, Laufzeit, Kosten | #316 |
| [unterlagen.md](unterlagen.md) | Dokumentenanforderungen mit Status | #316 |
| [projektrahmen.md](projektrahmen.md) | Zugänge, Zutrittsregelung, NDA, Beobachtungen vor Ort | #316 |
| [versionierung.md](versionierung.md) | Versions-Snapshots von Auftragsdaten | — |

## Spezial-Features

| Datei | Feature | Karten |
|---|---|---|
| [m365-lizenzmatrix.md](m365-lizenzmatrix.md) | Lizenzfeld, lizenz-bewusste Regeln, Matrix-Lookup, Evidenzstatus | #405, #407, #408 |
| [zahlparser.md](zahlparser.md) | Deutsche Tausenderpunkte, internationale Formate | #319 |

## Infrastruktur & Sicherheit

| Datei | Feature | Karten |
|---|---|---|
| [security-auth.md](security-auth.md) | Security Headers, CSRF, Entra ID SSO, IP-Beschränkung | #301, #373 |
| [konflikterkennung.md](konflikterkennung.md) | Optimistic Concurrency, atomares Schreiben, Konflikt-Banner | #305, #308 |
| [deployment.md](deployment.md) | install.sh, update.sh, systemd, nginx, Docker | #301 |

## UX & Navigation

| Datei | Feature | Karten |
|---|---|---|
| [sidebar-navigation.md](sidebar-navigation.md) | Scrollbare Sidebar, Übersicht/Erfassung-Trennung, Fortschrittsanzeige | #275, #306, #326, #402 |
| [barrierefreiheit-ux.md](barrierefreiheit-ux.md) | Label-Verknüpfung, Fehlerseiten, Print, Dialog-UX, ungespeicherte Änderungen | #357, #364, #374, #375, #403 |
