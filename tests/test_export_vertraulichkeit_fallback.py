"""Tests für Karte #310: Rückfallwerte der Vertraulichkeit.

Ein Rückfallwert soll im Zweifel die *schützendere* Stufe wählen. Bei einem
Werkzeug, das Kundeninfrastruktur dokumentiert, ist ein versehentlich als
„kundentauglich" behandelter Datensatz der teurere Fehler als ein zu vorsichtig
als „intern" behandelter.

Die Richtung ist dabei nicht überall dieselbe: für einen erfassten Datensatz
schützt INTERN (fliegt aus Kundenunterlagen heraus), für das Ziel eines Exports
dagegen ANONYMISIERT (gibt am wenigsten preis).
"""

import pytest

from app.models.auftrag import Auftrag
from app.models.standort import Standort
from app.models.technik import TechnikObjekt
from app.services.exporter import ExporterService, VertraulichkeitsStufe


@pytest.fixture
def exporter():
    return ExporterService()


@pytest.fixture
def auftrag():
    return Auftrag(id="auf-310", projekt_nummer="AUF-310", kunde="Kunde AG", bezeichnung="Fallback-Test")


# ── Die Stufe selbst ────────────────────────────────────────────────────

@pytest.mark.parametrize("wert", ["intern", "kundentauglich", "anonymisiert", "INTERN", " Intern "])
def test_bekannte_stufen_ignorieren_den_rueckfallwert(wert):
    erwartet = VertraulichkeitsStufe.parse(wert.strip().lower(), VertraulichkeitsStufe.INTERN)
    assert VertraulichkeitsStufe.parse(wert, VertraulichkeitsStufe.ANONYMISIERT) == erwartet


@pytest.mark.parametrize("wert", ["", None, "kundentauglixh", "geheim"])
def test_unbekannter_wert_faellt_auf_den_uebergebenen_wert_zurueck(wert):
    """Vorher war „kundentauglich" fest eingebaut — ein Tippfehler in einer
    YAML-Datei hätte den Datensatz damit in Kundenunterlagen befördert."""
    assert VertraulichkeitsStufe.parse(wert, VertraulichkeitsStufe.INTERN) == VertraulichkeitsStufe.INTERN
    assert VertraulichkeitsStufe.parse(wert, VertraulichkeitsStufe.ANONYMISIERT) == VertraulichkeitsStufe.ANONYMISIERT


def test_rueckfallwert_muss_angegeben_werden():
    """Kein gemeinsamer Vorgabewert: er wäre in einer der beiden Richtungen
    immer die riskante Wahl."""
    with pytest.raises(TypeError):
        VertraulichkeitsStufe.parse("unbekannt")


# ── Auswirkung auf den Export ───────────────────────────────────────────

def test_objekt_mit_unbekannter_stufe_landet_nicht_beim_kunden(exporter, auftrag):
    """Der Kern der Karte: was das Tool nicht einordnen kann, bleibt drin."""
    sto = Standort(id="sto-1", auftrag_id=auftrag.id, bezeichnung="Zentrale", vertraulichkeit="kundentauglich")
    kaputt = TechnikObjekt(
        id="fw-kaputt", typ="firewall", auftrag_id=auftrag.id, standort_id="sto-1",
        bezeichnung="Firewall mit Tippfehler", vertraulichkeit="kundentauglixh",
    )
    sauber = TechnikObjekt(
        id="fw-ok", typ="firewall", auftrag_id=auftrag.id, standort_id="sto-1",
        bezeichnung="Firewall freigegeben", vertraulichkeit="kundentauglich",
    )

    bericht = exporter.export_analysebericht(
        auftrag, [sto], [kaputt, sauber], [], ziel_vertraulichkeit="kundentauglich", findings=[]
    )

    assert "Firewall freigegeben" in bericht
    assert "Firewall mit Tippfehler" not in bericht


def test_standort_mit_unbekannter_stufe_landet_nicht_beim_kunden(exporter, auftrag):
    freigegeben = Standort(id="sto-frei", auftrag_id=auftrag.id, bezeichnung="Zentrale Berlin", vertraulichkeit="kundentauglich")
    kaputt = Standort(id="sto-kaputt", auftrag_id=auftrag.id, bezeichnung="Rechenzentrum Geheim", vertraulichkeit="intren")

    bericht = exporter.export_analysebericht(
        auftrag, [freigegeben, kaputt], [], [], ziel_vertraulichkeit="kundentauglich", findings=[]
    )

    assert "Zentrale Berlin" in bericht
    assert "Rechenzentrum Geheim" not in bericht


def test_unbekanntes_exportziel_gibt_am_wenigsten_preis(exporter, auftrag):
    """Umgekehrte Richtung: `ziel_vertraulichkeit` kommt als Adressparameter aus
    der URL. Ein unbekannter Wert darf nicht dazu führen, dass mehr statt
    weniger herausgegeben wird — er landet deshalb auf „anonymisiert"."""
    sto = Standort(id="sto-1", auftrag_id=auftrag.id, bezeichnung="Zentrale Berlin", ort="Berlin", strasse="Hauptstr. 1")

    bericht = exporter.export_analysebericht(auftrag, [sto], [], [], ziel_vertraulichkeit="quatsch", findings=[])

    assert "Zentrale Berlin" not in bericht
    assert "Hauptstr. 1" not in bericht
    assert "[ANONYMISIERT]" in bericht


def test_intern_bleibt_im_internen_export_sichtbar(exporter, auftrag):
    """Gegenprobe: der schützende Rückfallwert darf den internen Bericht nicht
    leerräumen — sonst wäre die Änderung eine Verschlimmbesserung."""
    sto = Standort(id="sto-1", auftrag_id=auftrag.id, bezeichnung="Zentrale", vertraulichkeit="intern")
    obj = TechnikObjekt(
        id="fw-1", typ="firewall", auftrag_id=auftrag.id, standort_id="sto-1",
        bezeichnung="Interne Firewall", vertraulichkeit="intern",
    )

    bericht = exporter.export_analysebericht(
        auftrag, [sto], [obj], [], ziel_vertraulichkeit="intern", findings=[]
    )

    assert "Interne Firewall" in bericht
