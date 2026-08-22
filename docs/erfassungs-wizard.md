# Erfassungs-Wizard

Geführter, linearer Durchlauf durch alle 13 IT-Themenbereiche beim Anlegen eines Auftrags.

## Karten

- #325: Erfassungs-Wizard Vollausbau & automatische Baustein-Erstellung
- #361: Direkteinstieg, Wiederaufnahme-Dialog & Meilenstein-Fortschritt

## Beteiligte Dateien

| Datei | Rolle |
|---|---|
| `app/web/routes_wizard.py` | Wizard-Routes: init, goto, back, skip, abbruch, zusammenfassung, abschliessen |
| `app/models/wizard.py` | `WizardStepData`, `WizardProgress` Modelle |
| `app/templates/auftrag/wizard.html` | Wizard-Schritt-Ansicht mit horizontaler Navigationsleiste |
| `app/templates/auftrag/wizard_resume.html` | Wiederaufnahme-Dialog |
| `app/templates/auftrag/wizard_zusammenfassung.html` | Zusammenfassung vor Abschluss mit Key-Facts-Vorschau |

## Funktionsweise

### 13 Schritte

1. Auftragsgrunddaten
2. Standort-Grunddaten
3. Internetanbindung (inkl. redundante Backup-Leitung #402)
4. Firewall
5. Switch
6. WLAN/Access Point
7. Server/Virtualisierung
8. Storage/NAS
9. Backup
10. USV
11. Clients/Arbeitsplätze
12. M365/Cloud
13. Organisation & Prozesse

### Navigation

- Horizontale, klickbare Schritt-Navigationsleiste zum direkten Springen zwischen bereits durchlaufenen Themen.
- `GET/POST /auftrag/{id}/wizard/goto/{step}` -- direktes Anspringen.
- `POST /auftrag/{id}/wizard/back` -- Rückwärts-Navigation.
- `POST /auftrag/{id}/wizard/skip` -- Schritt überspringen.
- `POST /auftrag/{id}/wizard/abbruch` -- Wizard abbrechen.
- HTTP 405-Fehler bei GET/POST-Konflikten behoben (#325).

### Dynamische Felder

- Ein-/Ausblenden von Detailfeldern basierend auf Ja/Nein-Antworten ("Wird eingesetzt?").
- `sichtbar_wenn` wie im Schema-System.

### Wiederaufnahme (#361)

- Bei bestehendem Erfassungsfortschritt: strukturierte Wiederaufnahme-Seite.
- Wahl zwischen "Bestehenden Erfassungsstand fortsetzen & prüfen" und "Interaktive Erfassung neu starten (Zurücksetzen)".
- Checkbox "Direkt mit interaktiver Bestandsaufnahme (Guide) starten" im Anlege-Dialog.

### Meilenstein-Fortschritt (#361, #367)

- Prominente Prozentanzeige und Meilenstein-Leiste im Header.
- Status-Marker: Erfasst (`✓`), Übersprungen (`⊘`), Ausstehend.
- Prozent- und Zählerberechnung angepasst.

### Automatische Baustein-Erstellung (#325)

- Beim Wizard-Abschluss werden alle aktivierten Bausteine und schemakonforme `TechnikObjekt`-Instanzen automatisch erstellt und zugeordnet.

### Key-Facts-Vorschau (#366)

- Ausführliche Key-Facts-Datenvorschau auf der Zusammenfassungsseite für alle 13 Meilensteine.
- Vollständiger Key-Facts-Extraktor mit automatischem Fallback.

### Fortschrittsanzeige (#402)

- Sidebar-Prozentanzeige zählt jetzt alle sichtbaren Schema-Felder (nicht nur Pflichtfelder).
- Anzeige ist realistisch (~40-50 % nach einem schnellen Durchlauf).
