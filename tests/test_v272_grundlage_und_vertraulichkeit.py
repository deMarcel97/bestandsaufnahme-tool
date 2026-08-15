"""Tests zu Karte #302: Grundlage "Analyse" und Default-Vertraulichkeit "intern".

Drei Dinge werden hier festgehalten:
1. Die Auswahl "Grundlage" hat genau eine Quelle (GRUNDLAGE_OPTIONS) und
   enthaelt "Analyse" an der richtigen Stelle.
2. Neue Auftraege sind per Vorgabe "intern", nicht mehr "kundentauglich" —
   bereits gespeicherte Werte bleiben davon unberuehrt.
3. Neue Standorte und Objekte uebernehmen die Vorgabe des Auftrags, sowohl
   in der Formular-Vorauswahl als auch beim Speichern ohne das Feld.
"""

import re

import pytest
from fastapi.testclient import TestClient

from app.config import BASE_DIR
from app.main import app
from app.models.auftrag import Auftrag
from app.models.standort import Standort
from app.models.technik import TechnikObjekt
from app.web.routes_auftrag import GRUNDLAGE_OPTIONS

client = TestClient(app)

TEMPLATE_DIR = BASE_DIR / "app" / "templates" / "auftrag"


@pytest.fixture(autouse=True)
def temp_storage(tmp_path):
    from app.services.storage import storage
    old_dir = storage.data_dir
    storage.data_dir = tmp_path
    yield
    storage.data_dir = old_dir


def _auftrag_anlegen(auftrag_id_erwartet: str, **felder) -> str:
    daten = {"kunde": "Test GmbH", "bezeichnung": "Karte 302"}
    daten.update(felder)
    res = client.post("/auftrag/neu", data=daten, follow_redirects=True)
    assert res.status_code == 200
    return auftrag_id_erwartet


# ── 1. Grundlage ────────────────────────────────────────────────────────

def test_grundlage_optionen_enthalten_analyse_in_richtiger_reihenfolge():
    assert GRUNDLAGE_OPTIONS == [
        "Ausschreibung", "Angebot", "Analyse", "Rahmenvertrag", "Sonstiges"
    ]


def test_grundlage_steht_nur_noch_an_einer_stelle():
    """Vorher war die Liste in beiden Templates hart kodiert. Wenn hier wieder
    ein literaler Eintrag auftaucht, ist die Zentralisierung aufgeweicht."""
    for name in ("list.html", "edit.html"):
        inhalt = (TEMPLATE_DIR / name).read_text(encoding="utf-8")
        for wert in GRUNDLAGE_OPTIONS:
            if wert == "Sonstiges":
                continue  # bleibt als Vorauswahl-Bedingung im Anlege-Dialog
            assert wert not in inhalt, f"{name} kodiert '{wert}' wieder hart"


def test_anlegedialog_bietet_analyse_an():
    res = client.get("/auftrag")
    assert res.status_code == 200
    optionen = re.findall(r'<option value="(Ausschreibung|Angebot|Analyse|Rahmenvertrag|Sonstiges)"', res.text)
    assert optionen == GRUNDLAGE_OPTIONS


def test_einstellungen_bieten_analyse_an():
    auftrag_id = _auftrag_anlegen("auf-karte-302", grundlage="Analyse")
    res = client.get(f"/auftrag/{auftrag_id}/einstellungen")
    assert res.status_code == 200
    optionen = re.findall(r'<option value="(Ausschreibung|Angebot|Analyse|Rahmenvertrag|Sonstiges)"', res.text)
    assert optionen == GRUNDLAGE_OPTIONS
    assert '<option value="Analyse" selected>' in res.text


def test_grundlage_analyse_wird_gespeichert():
    from app.services.storage import storage

    auftrag_id = _auftrag_anlegen("auf-karte-302", grundlage="Analyse")
    assert storage.load_auftrag(auftrag_id).grundlage == "Analyse"


# ── 2. Default-Vertraulichkeit "intern" ─────────────────────────────────

def test_modell_defaults_sind_intern():
    assert Auftrag(id="auf-x").vertraulichkeit_default == "intern"
    assert Standort(id="sto-x", auftrag_id="auf-x").vertraulichkeit == "intern"
    assert TechnikObjekt(id="obj-x", typ="firewall", auftrag_id="auf-x",
                         standort_id="sto-x").vertraulichkeit == "intern"


def test_neuer_auftrag_ohne_angabe_ist_intern():
    from app.services.storage import storage

    auftrag_id = _auftrag_anlegen("auf-karte-302")
    assert storage.load_auftrag(auftrag_id).vertraulichkeit_default == "intern"


def test_einstellungen_ohne_angabe_fallen_auf_intern_zurueck():
    from app.services.storage import storage

    auftrag_id = _auftrag_anlegen("auf-karte-302", vertraulichkeit_default="anonymisiert")
    res = client.post(f"/auftrag/{auftrag_id}/einstellungen", data={
        "kunde": "Test GmbH",
        "bezeichnung": "Karte 302",
    }, follow_redirects=True)
    assert res.status_code == 200
    assert storage.load_auftrag(auftrag_id).vertraulichkeit_default == "intern"


def test_anlegedialog_hat_intern_vorausgewaehlt():
    """Ohne bestehende Auftraege enthaelt die Seite nur die Selects des
    Anlege-Dialogs — die Zeilen-Selects der Tabelle koennen also nicht stoeren."""
    res = client.get("/auftrag")
    assert res.status_code == 200
    assert '<option value="intern" selected>' in res.text
    assert '<option value="kundentauglich" selected>' not in res.text


def test_bestandsdaten_behalten_ihre_vertraulichkeit():
    """Der geaenderte Default darf nur fuer neue Datensaetze gelten."""
    from app.services.storage import storage

    auftrag = Auftrag(id="auf-bestand", kunde="Alt GmbH", bezeichnung="Altauftrag",
                      vertraulichkeit_default="kundentauglich")
    storage.save_auftrag(auftrag)
    standort = Standort(id="sto-bestand", auftrag_id="auf-bestand",
                        bezeichnung="Alt-Standort", vertraulichkeit="kundentauglich")
    storage.save_standort(standort)

    assert storage.load_auftrag("auf-bestand").vertraulichkeit_default == "kundentauglich"
    assert storage.load_standort("auf-bestand", "sto-bestand").vertraulichkeit == "kundentauglich"


# ── 3. Vorbelegung aus dem Auftrag ──────────────────────────────────────

def test_standortformular_waehlt_auftragsvorgabe_vor():
    auftrag_id = _auftrag_anlegen("auf-karte-302", vertraulichkeit_default="anonymisiert")
    res = client.get(f"/auftrag/{auftrag_id}/standort/neu")
    assert res.status_code == 200
    assert '<option value="anonymisiert" selected>' in res.text
    assert '<option value="intern" selected>' not in res.text


def test_objektformular_waehlt_auftragsvorgabe_vor():
    auftrag_id = _auftrag_anlegen("auf-karte-302", vertraulichkeit_default="anonymisiert")
    res = client.get(f"/auftrag/{auftrag_id}/objekt/neu?typ=firewall")
    assert res.status_code == 200
    assert '<option value="anonymisiert" selected>' in res.text
    assert '<option value="intern" selected>' not in res.text


def test_neues_objekt_erbt_vertraulichkeit_default_vom_auftrag():
    """Gegenstueck zum Standort-Test: ohne 'vertraulichkeit' im POST muss die
    Auftragsvorgabe greifen, nicht der Modell-Default."""
    from app.services.storage import storage

    auftrag_id = _auftrag_anlegen("auf-karte-302", vertraulichkeit_default="anonymisiert")
    client.post(f"/auftrag/{auftrag_id}/standort/neu", data={"bezeichnung": "Zentrale"},
                follow_redirects=True)
    res = client.post(f"/auftrag/{auftrag_id}/objekt/neu", data={
        "typ": "firewall",
        "bezeichnung": "Perimeter FW",
        "standort_id": "sto-zentrale",
    }, follow_redirects=True)
    assert res.status_code == 200

    objekte = storage.list_objekte(auftrag_id, typ="firewall")
    assert len(objekte) == 1
    assert objekte[0].vertraulichkeit == "anonymisiert"
