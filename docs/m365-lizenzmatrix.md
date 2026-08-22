# M365-Lizenzmatrix

Lizenz-bewusste Regelbewertung für Microsoft 365: Trennung von Lizenz-Fehlt- und Fehlkonfigurations-Triggern.

## Karten

- #408: M365-Lizenzmatrix Fundament (Lizenzfeld, Regel-Generator, Fix Tier-Blindheit)

## Beteiligte Dateien

| Datei | Rolle |
|---|---|
| `schemas/m365_security.yaml` | Schema mit neuem Mehrfachauswahl-Feld `m365_lizenzen` |
| `rules/m365_lizenzmatrix.yaml` | Lizenz-bewusste Regeln für 3 Pilot-Features |
| `rules/m365_security.yaml` | Veraltete tier-blinde Regeln entfernt |
| `tests/test_m365_lizenzmatrix.py` | Test-Suite für Lizenzmatrix |

## Funktionsweise

### Lizenzfeld

- Neues Mehrfachauswahl-Feld `m365_lizenzen` im Schema `m365_security`.
- 15 gängige M365/O365- und Standalone-Lizenz-SKUs zur Auswahl.

### Lizenz-bewusste Regeln

Trennung in zwei Trigger-Typen:

1. **Lizenz-Fehlt-Trigger** (Advisory/Upgrade): Feature ist aktiviert, aber die nötige Lizenz fehlt.
2. **Fehlkonfigurations-Trigger** (lizenziert, aber nicht aktiv/konfiguriert): Lizenz ist vorhanden, Feature aber nicht korrekt konfiguriert.

### Pilot-Features

| Feature | Regel-ID | Verhalten |
|---|---|---|
| Conditional Access (`conditional_access`) | Lizenz-bewusst | Lizenz-Fehlt = Advisory; Fehlkonfig = Warning |
| Defender for Office 365 (`defender_o365_p1`) | Lizenz-bewusst | Schweregrad bei Fehlkonfig: **hoch** (von mittel angehoben) |
| Purview Audit Standard (`audit_standard`) | Lizenz-bewusst | Lizenz-Fehlt = Advisory; Fehlkonfig = Warning |

### Tier-Blindheit-Fix

- Vorher: Regeln in `m365_security.yaml` prüften Features ohne Berücksichtigung der lizenzierten SKU.
- Nachher: Regeln prüfen zunächst, ob die nötige Lizenz vorhanden ist, bevor sie eine Fehlkonfiguration melden.
- Veraltete tier-blinde Regeln in `rules/m365_security.yaml` entfernt.
