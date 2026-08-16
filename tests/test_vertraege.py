"""Tests für Karte #316: Erfassungsseite für Verträge (Auftrag.vertraege).

Das Feld existierte im Modell und wurde gespeichert, liess sich aber durch
kein Formular füllen. Die Tests hier decken die neue Seite ab — inklusive
Konflikterkennung nach dem Vorbild aus `test_konflikt_formulare.py` (#308).
"""

import re
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.auftrag import Auftrag

client = TestClient(app)

AUFTRAG_ID = "auf-vertraege-test"


@pytest.fixture(autouse=True)
def temp_storage(tmp_path):
    from app.services.storage import storage
    old_dir = storage.data_dir
    storage.data_dir = tmp_path
    yield
    storage.data_dir = old_dir


@pytest.fixture
def bestand():
    from app.services.storage import storage
    storage.save_auftrag(Auftrag(
        id=AUFTRAG_ID,
        projekt_nummer="PROJEKT-316",
        kunde="Vertrag GmbH",
        bezeichnung="Vertrags-Bestandsaufnahme",
        aktive_bausteine=["firewall"],
    ))
    return storage


def _version_im_formular(seite: str) -> str:
    treffer = re.search(r'name="version"\s+value="(\d+)"', seite)
    assert treffer, "Das Formular führt keine Version mit"
    return treffer.group(1)


def test_vertraege_form_laedt(bestand):
    antwort = client.get(f"/auftrag/{AUFTRAG_ID}/vertraege")
    assert antwort.status_code == 200
    assert "Verträge" in antwort.text


def test_vertrag_anlegen_und_speichern(bestand):
    stand = _version_im_formular(client.get(f"/auftrag/{AUFTRAG_ID}/vertraege").text)
    antwort = client.post(
        f"/auftrag/{AUFTRAG_ID}/vertraege",
        data={
            "version": stand,
            "vertrag_bezeichnung_0": "Wartungsvertrag Server",
            "vertrag_vertragspartner_0": "IT-Dienstleister AG",
            "vertrag_gegenstand_0": "Serverwartung",
            "vertrag_laufzeit_bis_0": "2027-12-31",
            "vertrag_kuendigungsfrist_0": "3 Monate zum Quartalsende",
            "vertrag_monatliche_kosten_0": "150,50",
            "vertrag_ansprechpartner_0": "Herr Mueller",
            "vertrag_bemerkung_0": "Enthaelt Ersatzteile",
        },
        follow_redirects=False,
    )
    assert antwort.status_code == 303

    auftrag = bestand.load_auftrag(AUFTRAG_ID)
    assert len(auftrag.vertraege) == 1
    v = auftrag.vertraege[0]
    assert v.bezeichnung == "Wartungsvertrag Server"
    assert v.vertragspartner == "IT-Dienstleister AG"
    assert v.gegenstand == "Serverwartung"
    assert v.laufzeit_bis == "2027-12-31"
    assert v.kuendigungsfrist == "3 Monate zum Quartalsende"
    assert v.monatliche_kosten == 150.5
    assert v.ansprechpartner == "Herr Mueller"
    assert v.bemerkung == "Enthaelt Ersatzteile"


def test_mehrere_vertraege_werden_gespeichert(bestand):
    stand = _version_im_formular(client.get(f"/auftrag/{AUFTRAG_ID}/vertraege").text)
    client.post(
        f"/auftrag/{AUFTRAG_ID}/vertraege",
        data={
            "version": stand,
            "vertrag_bezeichnung_0": "Vertrag A",
            "vertrag_bezeichnung_1": "Vertrag B",
        },
        follow_redirects=False,
    )
    auftrag = bestand.load_auftrag(AUFTRAG_ID)
    assert [v.bezeichnung for v in auftrag.vertraege] == ["Vertrag A", "Vertrag B"]


def test_leere_zeile_erzeugt_keinen_datensatz(bestand):
    """Wer eine Zeile hinzufügt und wieder entfernt (oder nichts einträgt),
    darf keinen leeren Vertrag hinterlassen — siehe `formular_listen.py`."""
    stand = _version_im_formular(client.get(f"/auftrag/{AUFTRAG_ID}/vertraege").text)
    client.post(
        f"/auftrag/{AUFTRAG_ID}/vertraege",
        data={"version": stand},
        follow_redirects=False,
    )
    auftrag = bestand.load_auftrag(AUFTRAG_ID)
    assert auftrag.vertraege == []


def test_vertrag_entfernen(bestand):
    """Die Liste wird bei jedem Speichern komplett ersetzt — eine Zeile ohne
    mitgeschickte Felder verschwindet also."""
    stand = _version_im_formular(client.get(f"/auftrag/{AUFTRAG_ID}/vertraege").text)
    client.post(
        f"/auftrag/{AUFTRAG_ID}/vertraege",
        data={
            "version": stand,
            "vertrag_bezeichnung_0": "Vertrag A",
            "vertrag_bezeichnung_1": "Vertrag B",
        },
        follow_redirects=False,
    )
    stand2 = _version_im_formular(client.get(f"/auftrag/{AUFTRAG_ID}/vertraege").text)
    client.post(
        f"/auftrag/{AUFTRAG_ID}/vertraege",
        data={
            "version": stand2,
            "vertrag_bezeichnung_0": "Vertrag A",
        },
        follow_redirects=False,
    )
    auftrag = bestand.load_auftrag(AUFTRAG_ID)
    assert [v.bezeichnung for v in auftrag.vertraege] == ["Vertrag A"]


def test_zweiter_benutzer_ueberschreibt_den_ersten_nicht(bestand):
    """Konflikterkennung (#308): A speichert zuerst, B mit demselben
    Ausgangsstand prallt ab und bekommt seine Eingaben zurück."""
    a = client.get(f"/auftrag/{AUFTRAG_ID}/vertraege")
    stand = _version_im_formular(a.text)

    antwort_a = client.post(
        f"/auftrag/{AUFTRAG_ID}/vertraege",
        data={"version": stand, "vertrag_bezeichnung_0": "Von A"},
        follow_redirects=False,
    )
    assert antwort_a.status_code == 303

    antwort_b = client.post(
        f"/auftrag/{AUFTRAG_ID}/vertraege",
        data={"version": stand, "vertrag_bezeichnung_0": "Von B"},
        follow_redirects=False,
    )
    assert antwort_b.status_code == 409
    assert "Nicht gespeichert" in antwort_b.text
    assert "Von B" in antwort_b.text
    assert bestand.load_auftrag(AUFTRAG_ID).vertraege[0].bezeichnung == "Von A"
