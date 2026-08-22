# Verträge

Erfassung von Wartungsverträgen mit Kündigungsfrist, Laufzeit und monatlichen Kosten.

## Karten

- #316: Vier neue Erfassungsseiten (Verträge)

## Beteiligte Dateien

| Datei | Rolle |
|---|---|
| `app/web/routes_vertraege.py` | Verträge-Formular (GET/POST) |
| `app/models/auftrag.py` | `Vertrag`-Modell |
| `app/templates/auftrag/vertraege.html` | Verträge-Formular |
| `app/web/formular_listen.py` | `parse_unterobjekte()` für wiederholbare Unterformulare |

## Funktionsweise

### Vertrag-Modell

| Feld | Beschreibung |
|---|---|
| `bezeichnung` | Vertragsname |
| `typ` | Vertragstyp |
| `kuendigungsfrist` | Kündigungsfrist |
| `laufzeit` | Laufzeit |
| `monatliche_kosten` | Monatliche Kosten |
| `vertraulichkeit` | Vertraulichkeitsstufe |

### Erfassung

- Wiederholbares Unterformular: mehrere Verträge pro Auftrag.
- Parser `parse_unterobjekte()` liest Felder der Form `vertrag_<feld>_<index>`.
- Leere Zeilen mit Auswahlfeld werden nicht gespeichert (Vergleich gegen Modell-Vorgabewert).

### Bericht

- Verträge erscheinen im Analysebericht.
- Kosten fliessen in den Massnahmenkatalog ein (bei Bedarf).
