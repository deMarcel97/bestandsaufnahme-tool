"""Tests für Karte #307: Standorte löschen.

`storage.delete_standort()` gab es seit jeher, aber keine Route hat sie
aufgerufen — Standorte liessen sich schlicht nicht entfernen. Besonders
unangenehm, weil der Unternehmenskontext Standorte automatisch anlegt: wer
sich bei der Anzahl vertippt, wurde sie nicht wieder los.

Entschieden wurde gegen Kaskadenlöschen: was mit den erfassten Objekten
geschehen soll, weiss nur der Bearbeiter. Das Löschen wird deshalb abgelehnt,
solange noch etwas am Standort hängt.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.auftrag import Auftrag
from app.models.standort import Standort
from app.models.technik import TechnikObjekt

client = TestClient(app)

AUFTRAG_ID = "auf-loeschen-test"


@pytest.fixture(autouse=True)
def temp_storage(tmp_path):
    from app.services.storage import storage
    old_dir = storage.data_dir
    storage.data_dir = tmp_path
    yield
    storage.data_dir = old_dir


@pytest.fixture
def bestand():
    """Zwei Standorte — an einem hängt eine Firewall, der andere ist leer."""
    from app.services.storage import storage

    storage.save_auftrag(Auftrag(
        id=AUFTRAG_ID,
        projekt_nummer="auf-2026-307",
        kunde="Löschen GmbH",
        bezeichnung="Standort-Löschtest",
        aktive_bausteine=["firewall"],
    ))
    for sto_id, name in [("sto-zentrale", "Zentrale"), ("sto-aussenstelle", "Außenstelle")]:
        storage.save_standort(Standort(
            id=sto_id, auftrag_id=AUFTRAG_ID, bezeichnung=name, anzahl_user=10
        ))
    storage.save_objekt(TechnikObjekt(
        id="fw-zentrale",
        typ="firewall",
        auftrag_id=AUFTRAG_ID,
        standort_id="sto-zentrale",
        bezeichnung="Firewall Zentrale",
    ))
    return storage


def _loeschen(standort_id: str):
    return client.post(
        f"/auftrag/{AUFTRAG_ID}/standort/{standort_id}/loeschen", follow_redirects=False
    )


# ── Der eigentliche Zweck ───────────────────────────────────────────────

def test_leerer_standort_laesst_sich_loeschen(bestand):
    antwort = _loeschen("sto-aussenstelle")

    assert antwort.status_code == 303
    assert bestand.load_standort(AUFTRAG_ID, "sto-aussenstelle") is None
    assert [s.id for s in bestand.list_standorte(AUFTRAG_ID)] == ["sto-zentrale"]


def test_standort_mit_objekten_wird_nicht_geloescht(bestand):
    """Kein Kaskadenlöschen: die Firewall soll nicht stillschweigend
    mitverschwinden, nur weil jemand den Standort loswerden will."""
    antwort = _loeschen("sto-zentrale")

    assert antwort.status_code == 409
    assert bestand.load_standort(AUFTRAG_ID, "sto-zentrale") is not None
    assert bestand.load_objekt(AUFTRAG_ID, "firewall", "fw-zentrale") is not None


def test_ablehnung_benennt_die_blockierenden_objekte(bestand):
    """Ohne die Liste müsste der Bearbeiter selbst durchzählen, was noch hängt."""
    antwort = _loeschen("sto-zentrale")

    assert "Firewall Zentrale" in antwort.text
    assert f"/auftrag/{AUFTRAG_ID}/objekt/firewall/fw-zentrale" in antwort.text


def test_nach_dem_verschieben_laesst_sich_der_standort_loeschen(bestand):
    """Der von der Ablehnung vorgezeichnete Weg muss auch tatsächlich gehen:
    Objekt über das Formular umhängen, danach ist der Standort frei."""
    client.post(
        f"/auftrag/{AUFTRAG_ID}/objekt/firewall/fw-zentrale",
        data={"bezeichnung": "Firewall Zentrale", "standort_id": "sto-aussenstelle"},
        follow_redirects=False,
    )
    assert bestand.load_objekt(AUFTRAG_ID, "firewall", "fw-zentrale").standort_id == "sto-aussenstelle"

    assert _loeschen("sto-zentrale").status_code == 303
    assert bestand.load_standort(AUFTRAG_ID, "sto-zentrale") is None


# ── Oberfläche ──────────────────────────────────────────────────────────

def test_erfassung_zeigt_loeschen_nur_fuer_leere_standorte(bestand):
    """Die Schaltfläche soll gleich sagen, warum sie nicht geht — statt den
    Benutzer erst klicken und dann abprallen zu lassen."""
    seite = client.get(f"/auftrag/{AUFTRAG_ID}/erfassung").text

    assert f"/auftrag/{AUFTRAG_ID}/standort/sto-aussenstelle/loeschen" in seite
    assert f"/auftrag/{AUFTRAG_ID}/standort/sto-zentrale/loeschen" not in seite
    assert "verschieben oder löschen" in seite


# ── Randfälle ───────────────────────────────────────────────────────────

def test_unbekannter_standort_fuehrt_zurueck_statt_zu_krachen(bestand):
    antwort = _loeschen("sto-gibt-es-nicht")

    assert antwort.status_code == 303
    assert len(bestand.list_standorte(AUFTRAG_ID)) == 2


def test_objekt_an_einem_anderen_standort_blockiert_nicht(bestand):
    """Gezählt werden darf nur, was wirklich an diesem Standort hängt — sonst
    liesse sich nie wieder ein Standort löschen, sobald irgendwo ein Objekt
    erfasst ist."""
    assert _loeschen("sto-aussenstelle").status_code == 303
