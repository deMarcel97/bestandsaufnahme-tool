# Projektrahmen

Erfassung von Projekt-Rahmendethoden: Zugänge, Zutrittsregelung, NDA, Wartungsfenster, Analysewerkzeuge, Ergebnisartefakte und Beobachtungen vor Ort.

## Karten

- #316: Vier neue Erfassungsseiten (Projektrahmen)

## Beteiligte Dateien

| Datei | Rolle |
|---|---|
| `app/web/routes_projektrahmen.py` | Projektrahmen-Formular (GET/POST) |
| `app/models/auftrag.py` | `Rahmenbedingungen`, `Ergebnisartefakt`, `Aspekt` Modelle |
| `app/templates/auftrag/projektrahmen.html` | Projektrahmen-Formular |

## Funktionsweise

### Rahmenbedingungen

- Benötigte Zugänge (Systemzugriffe, VPN etc.)
- Zutrittsregelung (vor Ort beim Kunden)
- NDA (Vertraulichkeitsvereinbarung)
- Wartungsfenster
- Analysewerkzeuge
- Ergebnisartefakte

### Beobachtungen vor Ort (#316)

- `positive_aspekte` / `negative_aspekte` als Freitextfelder.
- Erscheinen als Anhang "Beobachtungen vor Ort" im Analysebericht.
- Bewusst getrennt von den Findings: Findings entstehen automatisch aus Regeln, dies ist der Eindruck des Bearbeiters.
- Bei Ziel `anonymisiert` entfällt der Anhang (Freitext identifizierbar).

### Stammdaten-Erweiterungen (#316)

- `zweck` (Mehrfachauswahl, serverseitig geprüft wie in #309)
- `abgrenzung`, `aufwand_geplant`, `aufwand_ist` in der Auftragssteuerung
- Betriebskritische Systeme und geplante Änderungen auf der Kontextseite
