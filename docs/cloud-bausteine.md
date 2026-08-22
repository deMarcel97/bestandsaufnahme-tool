# Cloud-Bausteine

Bausteine mit `standortbezug: false` können ohne Zuweisung zu einem physischen Standort erfasst werden.

## Karten

- #315: Cloud-Bausteine ohne Standortzuweisung (M365 & Co.)

## Beteiligte Dateien

| Datei | Rolle |
|---|---|
| `schemas/m365_security.yaml` | M365-Security-Schema mit `standortbezug: false` |
| `schemas/organisation_prozesse.yaml` | Organisation & Prozesse mit `standortbezug: false` |
| `app/models/technik.py` | `TechnikObjekt.standort_id` ist `Optional[str] = None` |
| `app/models/finding.py` | `Finding.standort_id` optional |
| `app/templates/technik/form.html` | Deaktiviertes Feld "Standortübergreifend (Cloud)" |
| `app/templates/auftrag/erfassung.html` | Eigener Bereich "Standortübergreifend / Cloud-Dienste" |
| `app/services/report_builder.py` | Kapitel 3 um "Standortübergreifende Infrastruktur & Cloud-Dienste" erweitert |

## Funktionsweise

### Prinzip

- Standortlosigkeit ist ein Schema-Merkmal (`standortbezug: false`), kein Sonderfall im Code.
- Bei Schemas ohne Standortbezug zeigt das Formular ein deaktiviertes Feld "Standortübergreifend (Cloud)" und sendet leere `standort_id`.
- Keine Ausnahmeliste im Code, die gepflegt werden muss.

### Erfassung

- Auf `/auftrag/{id}/erfassung` eigener Bereich "Standortübergreifend / Cloud-Dienste".
- Cloud-Bausteine erscheinen nicht in der Standort-Auswahl.

### Bericht

- Im Analysebericht Kapitel 3 um "Standortübergreifende Infrastruktur & Cloud-Dienste" erweitert.
- Auch in Kapitel 4 integriert.

### Betroffene Modelle

- `TechnikObjekt.standort_id`: `Optional[str] = None`
- `OffenerPunktItem.standort_id`: `Optional[str] = None`
- `Finding.standort_id`: `Optional[str] = None`
