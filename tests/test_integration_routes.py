import html
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

def test_full_workflow():
    from app.services.storage import storage
    # Cleanup previous test runs
    existing = storage.list_auftraege()
    for a in existing:
        if a.projekt_nummer == "auf-2026-999":
            storage.delete_auftrag(a.id)

    # 1. List orders
    res = client.get("/auftrag")
    assert res.status_code == 200
    assert "Auftragsübersicht" in res.text

    # 2. Create Order
    res = client.post("/auftrag/neu", data={
        "projekt_nummer": "auf-2026-999",
        "kunde": "Landkreis Teststadt",
        "bezeichnung": "Integrations-Bestandsaufnahme",
        "grundlage": "Angebot",
        "vertraulichkeit_default": "kundentauglich",
        "aktive_bausteine": ["firewall"]
    }, follow_redirects=True)
    assert res.status_code == 200
    assert "Integrations-Bestandsaufnahme" in res.text

    auftrag_id = "auf-integrations-bestandsaufnahme"

    # 3. Add Standort
    res = client.post(f"/auftrag/{auftrag_id}/standort/neu", data={
        "bezeichnung": "Hauptgebäude",
        "ort": "Teststadt",
        "anzahl_user": 25,
        "anbieter_0": "Telekom",
        "art_0": "Glasfaser_FTTH",
        "bandbreite_down_mbit_0": 100,
        "bandbreite_up_mbit_0": 100,
        "ist_backup_leitung_0": "nein"
    }, follow_redirects=True)
    assert res.status_code == 200
    assert "Hauptgebäude" in res.text

    standort_id = "sto-hauptgebaeude"

    # 4. Add Firewall Object with expired security sub & rueckfrage field
    res = client.post(f"/auftrag/{auftrag_id}/objekt/neu?typ=firewall", data={
        "bezeichnung": "Zentrale Firewall",
        "standort_id": standort_id,
        "betreut_durch": "wir",
        "hersteller": "Fortinet",
        "security_abo_vorhanden": "nein", # triggers fw-security-abo-abgelaufen
        "exchange_onprem_dahinter": "ja",
        "dokumentation_vorhanden": "rueckfrage" # creates open point
    }, follow_redirects=True)
    assert res.status_code == 200
    assert "Zentrale Firewall" in res.text

    # 5. Evaluate Rules
    res = client.post(f"/auftrag/{auftrag_id}/bewerten", follow_redirects=True)
    assert res.status_code == 200
    assert "Gesamtbewertung" in res.text

    # 6. Check Findings
    res = client.get(f"/auftrag/{auftrag_id}/findings")
    assert res.status_code == 200
    assert "Firewall ohne aktives Security-Abonnement" in res.text

    # 7. Check Open Points
    res = client.get(f"/auftrag/{auftrag_id}/offene_punkte")
    assert res.status_code == 200
    assert "Rückfrage erforderlich" in res.text

    # 8. Check Measures Catalog
    res = client.get(f"/auftrag/{auftrag_id}/massnahmen")
    assert res.status_code == 200

    # 9. Download Export Analysebericht
    res = client.get(f"/auftrag/{auftrag_id}/export/download/analysebericht.md?ziel_vertraulichkeit=kundentauglich")
    assert res.status_code == 200
    assert "# Analysebericht: IT-Bestandsaufnahme" in res.text
    assert "Als zentrale Firewall kommt ein System des Herstellers Fortinet zum Einsatz." in res.text

def test_path_traversal_delete_is_rejected():
    from app.services.storage import storage
    client.post("/auftrag/neu", data={
        "projekt_nummer": "PROJ-TRAV-1",
        "kunde": "PoC",
        "bezeichnung": "Traversal Delete Test",
    }, follow_redirects=False)
    auftrag_id = "auf-traversal-delete-test"
    assert storage.load_auftrag(auftrag_id) is not None

    # ".." als auftrag_id, %2e-kodiert damit der Client es nicht vorher normalisiert
    res = client.post("/auftrag/%2e%2e/delete", follow_redirects=False)
    assert res.status_code in (303, 404)

    # Der zuvor angelegte Auftrag muss unversehrt sein
    assert storage.load_auftrag(auftrag_id) is not None

def test_projekt_nummer_duplicate_error_is_escaped():
    payload = "PROJ-XSSTEST'); alert(1); //"
    client.post("/auftrag/neu", data={
        "projekt_nummer": payload,
        "kunde": "PoC",
        "bezeichnung": "PoC Order A",
    }, follow_redirects=False)

    res = client.post("/auftrag/neu", data={
        "projekt_nummer": payload,
        "kunde": "PoC2",
        "bezeichnung": "PoC Order B",
    }, follow_redirects=False)
    assert res.status_code == 400
    assert payload not in res.text
    assert html.escape(payload) in res.text

def test_export_defaults_to_auftrag_vertraulichkeit_default():
    client.post("/auftrag/neu", data={
        "projekt_nummer": "PROJ-EXPORT-DEFAULT",
        "kunde": "PoC",
        "bezeichnung": "Export Default Test",
        "vertraulichkeit_default": "intern",
    }, follow_redirects=False)
    auftrag_id = "auf-export-default-test"

    res = client.get(f"/auftrag/{auftrag_id}/export")
    assert res.status_code == 200
    assert "Stufe intern" in res.text

def test_objekt_typ_traversal_rejected():
    from app.services.storage import storage
    client.post("/auftrag/neu", data={
        "projekt_nummer": "PROJ-TT-1",
        "kunde": "PoC",
        "bezeichnung": "Typ Traversal Test",
    }, follow_redirects=False)
    auftrag_id = "auf-typ-traversal-test"

    res = client.post(f"/auftrag/{auftrag_id}/objekt/neu?typ=../../../../tmp/pwn", data={
        "bezeichnung": "Boese Datei",
    }, follow_redirects=False)
    assert res.status_code == 303
    assert storage.list_objekte(auftrag_id) == []

def test_batch_create_objekte():
    from app.services.storage import storage
    client.post("/auftrag/neu", data={
        "projekt_nummer": "PROJ-BATCH-1",
        "kunde": "Batch Kunde",
        "bezeichnung": "Batch Test Order",
        "aktive_bausteine": ["netzwerkschrank"]
    }, follow_redirects=True)
    auftrag_id = "auf-batch-test-order"

    client.post(f"/auftrag/{auftrag_id}/standort/neu", data={
        "bezeichnung": "Hauptstandort"
    }, follow_redirects=True)

    res = client.post(f"/auftrag/{auftrag_id}/objekt/mehrere_anlegen", data={
        "standort_id": "sto-hauptstandort",
        "typ": "netzwerkschrank",
        "anzahl": 3
    }, follow_redirects=True)

    assert res.status_code == 200
    objs = storage.list_objekte(auftrag_id)
    assert len(objs) == 3
    assert any("Netzwerkschrank 1" in o.bezeichnung for o in objs)
    assert any("Netzwerkschrank 2" in o.bezeichnung for o in objs)
    assert any("Netzwerkschrank 3" in o.bezeichnung for o in objs)
