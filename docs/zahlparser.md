# Zahlparser

Parser für deutsche und internationale Zahlenformate in Formularfeldern.

## Karten

- #319: Tausenderpunkte unterstützen

## Beteiligte Dateien

| Datei | Rolle |
|---|---|
| `app/utils/number_parser.py` | `parse_float_german()`, `parse_int_german()` |
| `app/web/formular_listen.py` | Verwendet Parser für Zahlenfelder in Unterformularen |
| `tests/test_formular_listen.py` | Tests für Zahlparser |
| `tests/test_stufe1.py` | Tests für Zahlparser |

## Funktionsweise

### Problem (#319)

- `parse_float_german("1.249,90")` ergab `0.0` statt `1249.90` -- stiller Datenverlust.
- Betraf: Vertragskosten, Bandbreiten, SLA-Zeiten, Bausteinfelder.

### Lösung

`parse_float_german()` und `parse_int_german()` erkennen:

| Format | Beispiel | Ergebnis |
|---|---|---|
| Deutsche Tausenderpunkte | `"1.249,90"` | `1249.90` |
| Deutsche Tausenderpunkte (gross) | `"1.000.000"` | `1000000` |
| Englische Tausenderkommas | `"1,249.90"` | `1249.90` |
| Dezimalzahlen | `"1.5"`, `"0.123"` | `1.5`, `0.123` |
| Leerzeichen-Trennung | `"10 000"` | `10000` |

### Schutz

- `tests/test_formular_listen.py::test_tausenderpunkt_geht_noch_verloren` hielt den Fehler fest, bevor er behoben wurde.
- Nach der Korrektur: Test verifiziert korrekte Parsung.
