"""Tests zum gemeinsamen Parser für wiederholbare Unterformulare (Karte #316).

Der Parser bedient fünf Erfassungsseiten. Ein Fehler hier wirkt sich überall
gleichzeitig aus, deshalb steht er hier für sich statt nur mittelbar über die
Seitentests.
"""

from app.models.auftrag import (
    Aspekt,
    Beteiligter,
    Dokumentenanforderung,
    Ergebnisartefakt,
    Vertrag,
)
from app.web.formular_listen import parse_unterobjekte


def test_leere_zeile_mit_select_vorgabe_wird_verworfen():
    """Der Fall, an dem eine naive Prüfung scheitert: ein `<select>` schickt
    **immer** einen Wert mit, auch für eine Zeile, die der Benutzer hinzugefügt
    und dann nicht ausgefüllt hat. Ohne Vergleich gegen den Vorgabewert wäre
    jede solche Zeile als Eingabe durchgegangen und hätte einen leeren Datensatz
    hinterlassen."""
    form = {
        "dokument_bezeichnung_0": "",
        "dokument_status_0": "offen",          # Vorauswahl des <select>
        "dokument_bemerkung_0": "",
        "dokument_angefordert_am_0": "",
    }
    assert parse_unterobjekte(form, "dokument", Dokumentenanforderung) == []


def test_abweichende_auswahl_zaehlt_als_eingabe():
    """Gegenprobe: wer die Auswahl bewusst umstellt, hat etwas eingetragen —
    auch wenn sonst nichts in der Zeile steht."""
    form = {"dokument_bezeichnung_0": "", "dokument_status_0": "erhalten"}
    ergebnis = parse_unterobjekte(form, "dokument", Dokumentenanforderung)
    assert len(ergebnis) == 1
    assert ergebnis[0].status == "erhalten"


def test_mehrere_zeilen_behalten_ihre_reihenfolge():
    form = {
        "beteiligter_name_0": "Anna Meier",
        "beteiligter_email_0": "anna@example.org",
        "beteiligter_name_1": "Bert Schulz",
        "beteiligter_email_1": "bert@example.org",
    }
    ergebnis = parse_unterobjekte(form, "beteiligter", Beteiligter)
    assert [b.name for b in ergebnis] == ["Anna Meier", "Bert Schulz"]


def test_luecken_in_der_nummerierung_stoeren_nicht():
    """Wer die mittlere Zeile im Browser entfernt, hinterlässt eine Lücke in
    den Indizes. Das Formular neu durchzunummerieren wäre Aufgabe des
    JavaScripts — verlassen darf sich der Parser nicht darauf."""
    form = {"beteiligter_name_0": "Anna", "beteiligter_name_7": "Bert"}
    ergebnis = parse_unterobjekte(form, "beteiligter", Beteiligter)
    assert [b.name for b in ergebnis] == ["Anna", "Bert"]


def test_deutsches_dezimalkomma_wird_gelesen():
    form = {"vertrag_bezeichnung_0": "Wartung", "vertrag_monatliche_kosten_0": "49,90"}
    ergebnis = parse_unterobjekte(form, "vertrag", Vertrag)
    assert ergebnis[0].monatliche_kosten == 49.90


def test_tausenderpunkt_geht_noch_verloren():
    """Hält den Stand fest, **nicht** das gewünschte Verhalten: `parse_float_german`
    macht aus „1.249,90" die ungültige Zahl „1.249.90" und fällt still auf 0.0
    zurück. Beim Bau dieses Parsers aufgefallen, als eigener Fehler auf Karte
    #319 notiert — er ist älter als #316 und betrifft auch Bandbreiten und
    SLA-Zeiten am Standort.

    Der Test steht hier, damit der Fehler nicht unbemerkt bleibt: wer #319
    behebt, sieht ihn fehlschlagen und weiss, dass er hier die Erwartung
    umdrehen muss."""
    form = {"vertrag_bezeichnung_0": "Wartung", "vertrag_monatliche_kosten_0": "1.249,90"}
    ergebnis = parse_unterobjekte(form, "vertrag", Vertrag)
    assert ergebnis[0].monatliche_kosten == 0.0, "Ist #319 behoben? Dann hier 1249.90 erwarten."


def test_leeres_optionales_datum_wird_none_nicht_leerstring():
    """Sonst steht im YAML ein leerer String, wo das Modell None meint."""
    form = {"vertrag_bezeichnung_0": "Wartung", "vertrag_laufzeit_bis_0": ""}
    assert parse_unterobjekte(form, "vertrag", Vertrag)[0].laufzeit_bis is None


def test_fremde_felder_erzeugen_keine_zeilen():
    """Im selben Formular stehen weitere Felder. Ein `anzahl_2` darf keine
    leere Zeile 2 erzeugen — deshalb prüft der Parser gegen die Feldnamen des
    Modells statt gegen „alles, was auf eine Zahl endet"."""
    form = {"anzahl_2": "5", "beteiligter_name_0": "Anna"}
    assert len(parse_unterobjekte(form, "beteiligter", Beteiligter)) == 1


def test_aspekt_und_artefakt_nutzen_denselben_weg():
    """Beide Modelle laufen über denselben Parser — hier festgehalten, damit
    niemand für eines von beiden doch wieder einen eigenen schreibt."""
    form = {"positiv_titel_0": "Backup", "positiv_text_0": "läuft sauber getrennt"}
    assert parse_unterobjekte(form, "positiv", Aspekt)[0].titel == "Backup"

    form = {"artefakt_bezeichnung_0": "Bericht", "artefakt_typ_0": "Analysebericht"}
    ergebnis = parse_unterobjekte(form, "artefakt", Ergebnisartefakt)
    assert len(ergebnis) == 1
    assert ergebnis[0].bezeichnung == "Bericht"
