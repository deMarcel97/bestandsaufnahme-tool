import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.utils.number_parser import parse_float_german, parse_int_german
from app.models.finding import Finding
from app.models.standort import Standort, Internetanbindung

client = TestClient(app)

@pytest.fixture(autouse=True)
def temp_storage(tmp_path):
    from app.services.storage import storage
    old_dir = storage.data_dir
    storage.data_dir = tmp_path
    yield
    storage.data_dir = old_dir

def test_1_1_anbindungsblocks_select_only_and_no_phantom():
    from app.services.storage import storage
    client.post("/auftrag/neu", data={"bezeichnung": "Test 1.1", "kunde": "K1", "projekt_nummer": "P1-1"})
    auftrag_id = "auf-test-1-1"

    # 1. Select-only line 2
    res = client.post(f"/auftrag/{auftrag_id}/standort/neu", data={
        "bezeichnung": "Hauptstandort",
        "anbieter_0": "Telekom",
        "art_0": "Glasfaser_FTTH",
        "bandbreite_down_mbit_0": 1000,
        "anbieter_1": "",
        "art_1": "Kabel",
        "ist_backup_leitung_1": "ja"
    }, follow_redirects=True)
    assert res.status_code == 200

    sto = storage.load_standort(auftrag_id, "sto-hauptstandort")
    assert sto is not None
    assert len(sto.anbindungen) == 2
    assert sto.anbindungen[1].art == "Kabel"
    assert sto.anbindungen[1].ist_backup_leitung == "ja"

    # 2. Form submission with actual form delivered inputs (without backup pre-selection) -> 0 connections
    res_empty = client.post(f"/auftrag/{auftrag_id}/standort/neu", data={
        "bezeichnung": "Leerer Standort",
        "anbieter_0": "",
        "art_0": "DSL",
        "symmetrisch_0": "nein",
        "feste_ip_0": "nein",
        "ist_backup_leitung_0": "nein",
        "anbieter_1": "",
        "art_1": "DSL",
        "symmetrisch_1": "nein",
        "feste_ip_1": "nein",
        "ist_backup_leitung_1": "nein"
    }, follow_redirects=True)
    assert res_empty.status_code == 200

    sto_empty = storage.load_standort(auftrag_id, "sto-leerer-standort")
    assert sto_empty is not None
    assert len(sto_empty.anbindungen) == 0

def test_1_2_sla_entstoerzeit_persistence():
    from app.services.storage import storage
    client.post("/auftrag/neu", data={"bezeichnung": "Test 1.2", "kunde": "K1", "projekt_nummer": "P1-2"})
    auftrag_id = "auf-test-1-2"

    res = client.post(f"/auftrag/{auftrag_id}/standort/neu", data={
        "bezeichnung": "SLA Standort",
        "anbieter_0": "Telekom",
        "sla_entstoerzeit_0": "4"
    }, follow_redirects=True)
    assert res.status_code == 200

    sto = storage.load_standort(auftrag_id, "sto-sla-standort")
    assert sto is not None
    assert len(sto.anbindungen) == 1
    assert sto.anbindungen[0].sla_entstoerzeit == 4.0

def test_1_3_anschlusstyp_removed():
    from pathlib import Path
    html = (Path("app") / "templates" / "standort" / "form.html").read_text(encoding="utf-8")
    assert "anschlusstyp" not in html

def test_1_4_ist_backup_leitung_options_selected():
    from pathlib import Path
    html = (Path("app") / "templates" / "standort" / "form.html").read_text(encoding="utf-8")
    assert "not anb and idx > 0" not in html

def test_1_5_anbindung_block_fields_aligned():
    from pathlib import Path
    html = (Path("app") / "templates" / "standort" / "form.html").read_text(encoding="utf-8")
    for f in ["anbieter", "art", "bandbreite_down_mbit", "bandbreite_up_mbit", "symmetrisch", "feste_ip", "ist_backup_leitung", "failover_verfahren", "sla_entstoerzeit", "ip_adressen", "subnetzmaske"]:
        assert f in html

def test_1_6_finding_without_begruendung_and_resilient_storage(tmp_path):
    from app.services.storage import storage
    client.post("/auftrag/neu", data={"bezeichnung": "Test 1.6", "kunde": "K1", "projekt_nummer": "P1-6"})
    auftrag_id = "auf-test-1-6"

    client.post(f"/auftrag/{auftrag_id}/standort/neu", data={"bezeichnung": "Sto 1.6"})
    
    # 1. Submit verworfen status without begruendung -> HTTP 400
    res_bad = client.post(f"/auftrag/{auftrag_id}/finding/find-1/status", data={
        "status": "verworfen",
        "begruendung": "   "
    })
    assert res_bad.status_code == 400
    assert "Begründung zwingend erforderlich" in res_bad.text

    # 2. Corrupt findings.yaml manually with an invalid item
    fpath = storage.get_auftrag_dir(auftrag_id) / "findings.yaml"
    import yaml
    corrupted_data = [
        {"id": "valid-1", "auftrag_id": auftrag_id, "standort_id": "sto-1-6", "befund": "Gültiger Befund", "status": "offen"},
        {"id": "invalid-1", "auftrag_id": auftrag_id, "standort_id": "sto-1-6", "status": "verworfen", "begruendung": ""}
    ]
    with open(fpath, "w", encoding="utf-8") as f:
        yaml.dump(corrupted_data, f)

    # 3. Verify storage.list_findings skips corrupt item and loads valid item
    loaded = storage.list_findings(auftrag_id)
    assert len(loaded) == 1
    assert loaded[0].id == "valid-1"

def test_1_7_delete_massnahme_resets_linked_findings():
    from app.services.storage import storage
    client.post("/auftrag/neu", data={"bezeichnung": "Test 1.7", "kunde": "K1", "projekt_nummer": "P1-7"})
    auftrag_id = "auf-test-1-7"

    f = Finding(
        schema_version=1,
        id="f-1.7",
        auftrag_id=auftrag_id,
        standort_id="sto-1",
        befund="Test Befund",
        status="uebernommen",
        massnahme_id="m-1.7"
    )
    storage.save_findings(auftrag_id, [f])

    from app.models.massnahme import Massnahme
    m = Massnahme(
        schema_version=1,
        id="m-1.7",
        bezeichnung="Test Maßnahme",
        findings=["f-1.7"]
    )
    storage.save_massnahmen(auftrag_id, [m])

    res = client.post(f"/auftrag/{auftrag_id}/massnahme/m-1.7/loeschen", follow_redirects=True)
    assert res.status_code == 200

    findings_after = storage.list_findings(auftrag_id)
    assert len(findings_after) == 1
    assert findings_after[0].status == "bestaetigt"
    assert findings_after[0].massnahme_id is None

def test_1_8_uebernommen_finding_status_change():
    from app.services.storage import storage
    client.post("/auftrag/neu", data={"bezeichnung": "Test 1.8", "kunde": "K1", "projekt_nummer": "P1-8"})
    auftrag_id = "auf-test-1-8"

    f = Finding(
        schema_version=1,
        id="f-1.8",
        auftrag_id=auftrag_id,
        standort_id="sto-1",
        befund="Uebernommen Befund",
        status="uebernommen",
        massnahme_id="m-1.8"
    )
    storage.save_findings(auftrag_id, [f])

    # 1. Check UI GET /findings includes uebernommen finding
    res_get = client.get(f"/auftrag/{auftrag_id}/findings")
    assert res_get.status_code == 200
    assert "Uebernommen Befund" in res_get.text

    # 2. Change status back to bestaetigt
    res_post = client.post(f"/auftrag/{auftrag_id}/finding/f-1.8/status", data={
        "status": "bestaetigt"
    }, follow_redirects=True)
    assert res_post.status_code == 200

    f_after = storage.list_findings(auftrag_id)[0]
    assert f_after.status == "bestaetigt"
    assert f_after.massnahme_id is None

def test_1_9_reevaluation_preserves_confirmed_status():
    from app.services.storage import storage
    from app.services.rule_engine import rule_engine
    client.post("/auftrag/neu", data={"bezeichnung": "Test 1.9", "kunde": "K1", "projekt_nummer": "P1-9"})
    auftrag_id = "auf-test-1-9"

    f = Finding(
        schema_version=1,
        id="fw-security-abo-abgelaufen-fw-1",
        auftrag_id=auftrag_id,
        standort_id="sto-1",
        objekt_id="fw-1",
        quelle="fw-security-abo-abgelaufen",
        schweregrad="hoch",
        befund="Befund",
        status="bestaetigt"
    )
    storage.save_findings(auftrag_id, [f])

    from app.models.technik import TechnikObjekt
    good_fw = TechnikObjekt(
        id="fw-1",
        typ="firewall",
        bezeichnung="Good FW",
        auftrag_id=auftrag_id,
        standort_id="sto-1",
        daten={"security_abo_vorhanden": "ja", "security_abo_bis": "2099-01-01"}
    )
    sto = Standort(id="sto-1", auftrag_id=auftrag_id, bezeichnung="Sto 1")

    updated_findings, _ = rule_engine.evaluate_all(auftrag_id, [sto], [good_fw], [f])
    f_res = next(item for item in updated_findings if item.id == "fw-security-abo-abgelaufen-fw-1")
    assert f_res.status == "bestaetigt"
    assert "Regel greift laut aktuellen Daten nicht mehr" in f_res.begruendung

def test_1_10_unbekannt_field_preserves_finding_status():
    from app.services.storage import storage
    from app.services.rule_engine import rule_engine
    auftrag_id = "auf-test-1-10"

    f = Finding(
        schema_version=1,
        id="fw-security-abo-abgelaufen-fw-10",
        auftrag_id=auftrag_id,
        standort_id="sto-1",
        objekt_id="fw-10",
        quelle="fw-security-abo-abgelaufen",
        schweregrad="hoch",
        befund="Befund",
        status="offen"
    )

    from app.models.technik import TechnikObjekt
    unknown_fw = TechnikObjekt(
        id="fw-10",
        typ="firewall",
        bezeichnung="Unknown FW",
        auftrag_id=auftrag_id,
        standort_id="sto-1",
        daten={"security_abo_vorhanden": "unbekannt"}
    )
    sto = Standort(id="sto-1", auftrag_id=auftrag_id, bezeichnung="Sto 1")

    updated_findings, open_points = rule_engine.evaluate_all(auftrag_id, [sto], [unknown_fw], [f])
    f_res = next(item for item in updated_findings if item.id == "fw-security-abo-abgelaufen-fw-10")
    assert f_res.status == "offen"
    assert len(open_points) > 0

def test_1_12_uncheck_all_modules():
    from app.services.storage import storage
    client.post("/auftrag/neu", data={"bezeichnung": "Test 1.12", "kunde": "K1", "projekt_nummer": "P1-12"})
    auftrag_id = "auf-test-1-12"

    res = client.post(f"/auftrag/{auftrag_id}/stammdaten", data={
        "kunde": "Kunde Neu",
        "bezeichnung": "Test 1.12",
        "aktive_bausteine": []
    }, follow_redirects=True)
    assert res.status_code == 200

    auftrag_after = storage.load_auftrag(auftrag_id)
    assert auftrag_after.aktive_bausteine == []

def test_1_13_raw_json_confidentiality_filter():
    from app.services.exporter import exporter_service
    from app.models.auftrag import Auftrag
    from app.models.technik import TechnikObjekt
    from app.models.massnahme import Massnahme

    auftrag = Auftrag(id="auf-1.13", kunde="Kunde Geheim", bezeichnung="Auftrag 1.13", projekt_nummer="P1.13")
    sto = Standort(id="sto-1", auftrag_id="auf-1.13", bezeichnung="Sto 1")
    obj_intern = TechnikObjekt(id="fw-intern", typ="firewall", bezeichnung="Internal FW", auftrag_id="auf-1.13", standort_id="sto-1", vertraulichkeit="intern", daten={})
    obj_kundentauglich = TechnikObjekt(id="fw-kunden", typ="firewall", bezeichnung="Kunden FW", auftrag_id="auf-1.13", standort_id="sto-1", vertraulichkeit="kundentauglich", daten={})
    
    f_intern = Finding(id="f-int", auftrag_id="auf-1.13", standort_id="sto-1", objekt_id="fw-intern", quelle="manuell", befund="Internes Finding", schweregrad="hoch")
    f_kunden = Finding(id="f-kun", auftrag_id="auf-1.13", standort_id="sto-1", objekt_id="fw-kunden", quelle="manuell", befund="Kunden Finding", schweregrad="hoch")

    m_intern = Massnahme(id="m-int", bezeichnung="Interne Maßnahme", findings=["f-int"])
    m_kunden = Massnahme(id="m-kun", bezeichnung="Kunden Maßnahme", findings=["f-kun"])

    json_str = exporter_service.export_raw_json(auftrag, [sto], [obj_intern, obj_kundentauglich], [f_intern, f_kunden], [m_intern, m_kunden], ziel_vertraulichkeit="kundentauglich")
    import json
    parsed = json.loads(json_str)

    obj_ids = [o["id"] for o in parsed["objekte"]]
    finding_ids = [f["id"] for f in parsed["findings"]]

    assert "fw-kunden" in obj_ids
    assert "fw-intern" not in obj_ids
    assert "f-kun" in finding_ids
    assert "f-int" not in finding_ids

    # Check massnahmen exports signature and execution with ziel_vertraulichkeit
    md_mass = exporter_service.export_massnahmenkatalog_md([m_kunden], ziel_vertraulichkeit="kundentauglich")
    csv_mass = exporter_service.export_massnahmenkatalog_csv([m_kunden], ziel_vertraulichkeit="kundentauglich")
    assert "Kunden Maßnahme" in md_mass
    assert "Kunden Maßnahme" in csv_mass

def test_1_14_german_number_parsing():
    assert parse_float_german("100,5") == 100.5
    assert parse_float_german("-5,25") == -5.25
    assert parse_float_german("invalid", default=0.0) == 0.0
    assert parse_int_german("25,0") == 25
    assert parse_int_german("invalid", default=0) == 0

    # #319: Tausenderpunkte und internationale Formate
    assert parse_float_german("1.249,90") == 1249.90
    assert parse_float_german("12.345,67") == 12345.67
    assert parse_float_german("1.000.000,50") == 1000000.50
    assert parse_float_german("1.000.000") == 1000000.0
    assert parse_float_german("1.000") == 1000.0
    assert parse_float_german("10.000") == 10000.0
    assert parse_float_german("1.249") == 1249.0
    assert parse_float_german("-1.249,90") == -1249.90
    assert parse_float_german(" 1 249,90 ") == 1249.90
    assert parse_float_german("1,249.90") == 1249.90
    assert parse_float_german("1249.90") == 1249.90
    assert parse_float_german("1.5") == 1.5
    assert parse_float_german("0.123") == 0.123
    assert parse_float_german("1249.500") == 1249.500

    assert parse_int_german("1.249") == 1249
    assert parse_int_german("1.249,90") == 1249
    assert parse_int_german("1.000.000") == 1000000
    assert parse_int_german("100") == 100

