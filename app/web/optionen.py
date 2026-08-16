"""Die Auswahllisten der Formulare — an einer Stelle, für Prüfung und Anzeige.

Vorher standen sie doppelt: die Route prüfte gegen eine literale Liste, das
Template baute seine `<option>`-Zeilen aus einer zweiten. Eine neue Stufe
hätte an beiden Stellen nachgetragen werden müssen, und ein Vergessen wäre
nicht aufgefallen — das Dropdown hätte den Wert angeboten, die Route ihn
verworfen (Karte #309).

Ein eigenes Modul, weil sowohl die Route-Module als auch `templates.py`
darauf zugreifen; lägen die Listen in einem der Route-Module, entstünde beim
Registrieren der Jinja-Globals ein Importzyklus.
"""

STATUS_OPTIONS = ["Vorbereitung", "Erfassung", "Konsolidierung", "Bewertung", "Abgabe"]

GRUNDLAGE_OPTIONS = ["Ausschreibung", "Angebot", "Analyse", "Rahmenvertrag", "Sonstiges"]

ZWECK_OPTIONS = [
    "Infrastrukturanalyse",
    "Migrationsvorbereitung",
    "Notfalldokumentation",
    "Betriebsuebernahme",
    "Optimierung",
]

# Reihenfolge von der vollständigsten zur zurückhaltendsten Stufe. Die Werte
# sind dieselben, die `VertraulichkeitsStufe.parse()` in
# `app/services/exporter.py` erkennt.
VERTRAULICHKEIT_OPTIONS = ["intern", "kundentauglich", "anonymisiert"]


def gueltiger_wert(wert: str, optionen: list[str], rueckfall: str) -> str:
    """Gibt `wert` zurück, wenn er in `optionen` steht, sonst `rueckfall`.

    Ein unbekannter Wert wird verworfen statt gespeichert. Als `rueckfall`
    gehört beim Bearbeiten der bereits gespeicherte Wert übergeben — ein
    fehlerhafter POST überschreibt dann nichts, statt den Datensatz auf einen
    Vorgabewert zurückzusetzen. Nur beim Neuanlegen, wo es noch nichts zu
    bewahren gibt, ist der Vorgabewert des Modells der richtige Rückfall.
    """
    return wert if wert in optionen else rueckfall
