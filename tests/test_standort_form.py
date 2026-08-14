import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def temp_storage(tmp_path):
    from app.services.storage import storage
    old_dir = storage.data_dir
    storage.data_dir = tmp_path
    yield
    storage.data_dir = old_dir

def test_standort_edit_and_save():
    from app.services.storage import storage

    # 1. Create Order
    client.post("/auftrag/neu", data={
        "projekt_nummer": "auf-sto-test",
        "kunde": "Test GmbH",
        "bezeichnung": "Standort-Test",
        "grundlage": "Angebot",
        "vertraulichkeit_default": "kundentauglich",
        "aktive_bausteine": ["firewall"]
    })
    auftrag_id = "auf-standort-test"

    # 2. Create Standort
    res = client.post(f"/auftrag/{auftrag_id}/standort/neu", data={
        "bezeichnung": "Zentrale Berlin",
        "strasse": "Hauptstr. 1",
        "plz": "10115",
        "ort": "Berlin",
        "anzahl_user": 50,
        "funktion": "Hauptverwaltung",
        "ansprechpartner_vor_ort": "Erika Muster",
        "redaktionskonzept_backup_leitung": "automatische_umschaltung",
        "trassenfuehrung_getrennt": "ja",
        "usv_fuer_netzwerktechnik": "ja",
        "anbieter_0": "Telekom",
        "art_0": "Glasfaser_FTTH",
        "bandbreite_down_mbit_0": 1000,
        "bandbreite_up_mbit_0": 500,
        "ist_backup_leitung_0": "nein"
    }, follow_redirects=True)
    assert res.status_code == 200

    standort_id = "sto-zentrale-berlin"
    sto = storage.load_standort(auftrag_id, standort_id)
    assert sto is not None
    assert sto.bezeichnung == "Zentrale Berlin"
    assert sto.ansprechpartner_vor_ort == "Erika Muster"
    assert sto.trassenfuehrung_getrennt == "ja"
    assert len(sto.anbindungen) == 1
    assert sto.anbindungen[0].anbieter == "Telekom"

    # 3. Edit Standort and submit new values
    res_edit = client.post(f"/auftrag/{auftrag_id}/standort/{standort_id}/bearbeiten", data={
        "bezeichnung": "Zentrale Berlin Nord",
        "strasse": "Neue Str. 42",
        "plz": "10117",
        "ort": "Berlin",
        "anzahl_user": 100,
        "funktion": "Zentrale",
        "ansprechpartner_vor_ort": "Max Mustermann",
        "redaktionskonzept_backup_leitung": "keine_backup_leitung",
        "trassenfuehrung_getrennt": "nein",
        "usv_fuer_netzwerktechnik": "nein",
        "anbieter_0": "Telekom",
        "art_0": "Glasfaser_FTTH",
        "bandbreite_down_mbit_0": 1000,
        "bandbreite_up_mbit_0": 500,
        "ist_backup_leitung_0": "nein",
        "anbieter_1": "Vodafone",
        "art_1": "Kabel",
        "bandbreite_down_mbit_1": 500,
        "bandbreite_up_mbit_1": 50,
        "ist_backup_leitung_1": "ja"
    }, follow_redirects=True)
    assert res_edit.status_code == 200

    sto_updated = storage.load_standort(auftrag_id, standort_id)
    assert sto_updated is not None
    assert sto_updated.bezeichnung == "Zentrale Berlin Nord"
    assert sto_updated.strasse == "Neue Str. 42"
    assert sto_updated.plz == "10117"
    assert sto_updated.anzahl_user == 100
    assert sto_updated.ansprechpartner_vor_ort == "Max Mustermann"
    assert sto_updated.redaktionskonzept_backup_leitung == "keine_backup_leitung"
    assert sto_updated.trassenfuehrung_getrennt == "nein"
    assert sto_updated.usv_fuer_netzwerktechnik == "nein"
    assert len(sto_updated.anbindungen) == 2
    assert sto_updated.anbindungen[1].anbieter == "Vodafone"

def test_neuer_standort_erbt_vertraulichkeit_default_vom_auftrag():
    from app.services.storage import storage

    client.post("/auftrag/neu", data={
        "projekt_nummer": "auf-vertraulichkeit-test",
        "kunde": "Test GmbH",
        "bezeichnung": "Vertraulichkeit-Test",
        "vertraulichkeit_default": "intern",
        "aktive_bausteine": ["firewall"]
    })
    auftrag_id = "auf-vertraulichkeit-test"

    # Kein 'vertraulichkeit'-Feld im POST -> muss den Auftrags-Default erben, nicht "kundentauglich"
    res = client.post(f"/auftrag/{auftrag_id}/standort/neu", data={
        "bezeichnung": "Filiale Ost",
    }, follow_redirects=True)
    assert res.status_code == 200

    sto = storage.load_standort(auftrag_id, "sto-filiale-ost")
    assert sto is not None
    assert sto.vertraulichkeit == "intern"
