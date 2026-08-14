import pytest
from app.services.rule_engine import ConditionEvaluator, RuleEngine, RuleValidationError
from app.models.standort import Standort, Internetanbindung
from app.models.technik import TechnikObjekt
from app.models.finding import Finding

def test_condition_evaluator_operators():
    # gleich / ungleich
    sat, miss = ConditionEvaluator.evaluate_condition({"feld": "f", "operator": "gleich", "wert": "ja"}, {"f": "ja"})
    assert sat and not miss

    sat, miss = ConditionEvaluator.evaluate_condition({"feld": "f", "operator": "gleich", "wert": "ja"}, {"f": "nein"})
    assert not sat and not miss

    # missing/unbekannt/rueckfrage creates missing_info flag and NOT satisfied
    sat, miss = ConditionEvaluator.evaluate_condition({"feld": "f", "operator": "gleich", "wert": "ja"}, {"f": "unbekannt"})
    assert not sat and miss

    sat, miss = ConditionEvaluator.evaluate_condition({"feld": "f", "operator": "gleich", "wert": "ja"}, {"f": "rueckfrage"})
    assert not sat and miss

    # groesser / kleiner
    sat, _ = ConditionEvaluator.evaluate_condition({"feld": "val", "operator": "groesser", "wert": 5}, {"val": 10})
    assert sat

    sat, _ = ConditionEvaluator.evaluate_condition({"feld": "val", "operator": "kleiner", "wert": 5}, {"val": 10})
    assert not sat

def test_rule_engine_evaluate_all():
    re = RuleEngine()
    
    sto = Standort(id="sto-1", auftrag_id="auf-1", bezeichnung="Zentrale", anbindungen=[
        Internetanbindung(anbieter="Telekom", art="DSL")
    ])

    obj = TechnikObjekt(
        id="fw-1",
        typ="firewall",
        bezeichnung="Firewall 1",
        auftrag_id="auf-1",
        standort_id="sto-1",
        daten={
            "security_abo_vorhanden": "nein",
            "exchange_onprem_dahinter": "ja"
        }
    )

    findings, open_points = re.evaluate_all("auf-1", [sto], [obj], [])
    
    # Check triggered findings
    triggered_ids = [f.id for f in findings if f.status == "offen"]
    assert "standort-ohne-failover-sto-1" in triggered_ids
    assert "fw-security-abo-abgelaufen-fw-1" in triggered_ids
    assert "fw-exchange-onprem-fw-1" in triggered_ids

def test_all_firewall_and_standort_rules():
    re = RuleEngine()
    sto = Standort(id="sto-1", auftrag_id="auf-1", bezeichnung="Zentrale", anbindungen=[
        Internetanbindung(anbieter="Telekom", art="DSL"),
        Internetanbindung(anbieter="Vodafone", art="LTE_5G", ist_backup_leitung="ja")
    ])

    # 1. Good Firewall object -> No firewall findings triggered
    good_obj = TechnikObjekt(
        id="fw-good",
        typ="firewall",
        bezeichnung="Gute Firewall",
        auftrag_id="auf-1",
        standort_id="sto-1",
        daten={
            "security_abo_vorhanden": "ja",
            "exchange_onprem_dahinter": "nein",
            "firmware_eol": "nein",
            "hardware_alter": "unter_3_jahre",
            "ersatzgeraet_vorhanden": "ja",
            "wartungsvertrag_vorhanden": "ja",
            "konfigurationssicherung_aktuell": "ja",
            "konfig_sicherung_automatisch": "ja",
            "ips_aktiv": "ja",
            "web_protection_aktiv": "ja",
            "mfa_fuer_vpn": "ja",
            "vlan_konzept_umgesetzt": "ja",
            "zugangsschutz_standort": "abgeschlossener_raum",
            "dokumentation_vorhanden": "vollstaendig"
        }
    )

    findings, open_pts = re.evaluate_all("auf-1", [sto], [good_obj], [])
    active_findings = [f for f in findings if f.status == "offen" and f.objekt_id == "fw-good"]
    assert len(active_findings) == 0, f"Expected 0 findings for good object, got {[f.id for f in active_findings]}"

    # 2. Bad Firewall object -> All 13 firewall rules trigger Findings
    bad_obj = TechnikObjekt(
        id="fw-bad",
        typ="firewall",
        bezeichnung="Schlechte Firewall",
        auftrag_id="auf-1",
        standort_id="sto-1",
        daten={
            "security_abo_vorhanden": "nein",
            "exchange_onprem_dahinter": "ja",
            "firmware_eol": "ja",
            "hardware_alter": "ueber_5_jahre",
            "ersatzgeraet_vorhanden": "nein",
            "wartungsvertrag_vorhanden": "nein",
            "konfigurationssicherung_aktuell": "nein",
            "konfig_sicherung_automatisch": "nein",
            "ips_aktiv": "nein",
            "web_protection_aktiv": "nein",
            "mfa_fuer_vpn": "nein",
            "vlan_konzept_umgesetzt": "nein",
            "zugangsschutz_standort": "frei_zugaenglich",
            "dokumentation_vorhanden": "keine"
        }
    )

    findings, open_pts = re.evaluate_all("auf-1", [sto], [bad_obj], [])
    active_bad_findings = [f for f in findings if f.status == "offen" and f.objekt_id == "fw-bad"]
    assert len(active_bad_findings) == 14, f"Expected 14 findings for bad object, got {len(active_bad_findings)}"

def test_empty_field_creates_open_point_not_finding():
    re = RuleEngine()
    sto = Standort(id="sto-1", auftrag_id="auf-1", bezeichnung="Zentrale", anbindungen=[])
    obj = TechnikObjekt(
        id="fw-1",
        typ="firewall",
        bezeichnung="Firewall 1",
        auftrag_id="auf-1",
        standort_id="sto-1",
        daten={
            "security_abo_vorhanden": "unbekannt" # missing info!
        }
    )
    findings, open_points = re.evaluate_all("auf-1", [sto], [obj], [])
    fw_finding = next((f for f in findings if f.id == "fw-security-abo-abgelaufen-fw-1"), None)
    assert fw_finding is None or fw_finding.status != "offen"
    assert len(open_points) > 0

def test_massnahme_richtwerte_transfer(tmp_path):
    from app.services.storage import storage
    from app.services.rule_engine import rule_engine
    from app.web.routes_findings import create_massnahme_from_finding
    from app.models.auftrag import Auftrag

    old_dir = storage.data_dir
    storage.data_dir = tmp_path

    # Synthetic rule with null richtwerte (all real rules now have values filled in)
    test_rule = {
        "id": "rule-without-richtwert",
        "gilt_fuer": "firewall",
        "befund": "Abo abgelaufen",
        "massnahme_vorschlag": {
            "bezeichnung": "Test Maßnahme ohne Richtwert",
            "kosten_richtwert": None,
            "aufwand_richtwert": None
        }
    }
    rule_engine.rules.append(test_rule)

    try:
        auf = Auftrag(id="auf-a2-test", projekt_nummer="P-A2", kunde="A2 Kunde", bezeichnung="A2 Test")
        storage.save_auftrag(auf)

        # Finding from rule with null richtwert
        f1 = Finding(id="f1", auftrag_id="auf-a2-test", standort_id="s1", quelle="rule-without-richtwert", befund="Abo abgelaufen", schweregrad="hoch", status="bestaetigt")
        storage.save_findings("auf-a2-test", [f1])

        create_massnahme_from_finding("auf-a2-test", "f1")
        massnahmen = storage.list_massnahmen("auf-a2-test")
        m1 = next(m for m in massnahmen if "f1" in m.findings)
        assert m1.kosten_quelle == "offen"
        assert m1.investitionskosten == 0.0
    finally:
        rule_engine.rules = [r for r in rule_engine.rules if r.get("id") != "rule-without-richtwert"]
        storage.data_dir = old_dir

def test_massnahme_richtwert_rule_transfer_and_manual_override(tmp_path):
    from app.services.storage import storage
    from app.services.rule_engine import rule_engine
    from app.web.routes_findings import create_massnahme_from_finding
    from app.models.auftrag import Auftrag

    old_dir = storage.data_dir
    storage.data_dir = tmp_path

    test_rule = {
        "id": "rule-with-richtwert",
        "gilt_fuer": "firewall",
        "massnahme_vorschlag": {
            "bezeichnung": "Test Maßnahme mit Richtwert",
            "kosten_richtwert": 1500.0,
            "aufwand_richtwert": 4.0
        }
    }
    rule_engine.rules.append(test_rule)

    try:
        auf = Auftrag(id="auf-b4-test", projekt_nummer="P-B4", kunde="B4 Kunde", bezeichnung="B4 Test")
        storage.save_auftrag(auf)

        f1 = Finding(id="f-b4", auftrag_id="auf-b4-test", standort_id="s1", quelle="rule-with-richtwert", befund="Richtwert Test", schweregrad="hoch", status="bestaetigt")
        storage.save_findings("auf-b4-test", [f1])

        # 1. Richtwert transfer
        create_massnahme_from_finding("auf-b4-test", "f-b4")
        massnahmen = storage.list_massnahmen("auf-b4-test")
        m1 = next(m for m in massnahmen if "f-b4" in m.findings)
        assert m1.investitionskosten == 1500.0
        assert m1.zeitaufwand == 4.0
        assert m1.kosten_quelle == "regelwerk"

        # 2. Manual override preservation
        m1.investitionskosten = 2000.0
        m1.kosten_quelle = "manuell"
        storage.save_massnahmen("auf-b4-test", [m1])

        reloaded_m1 = next(m for m in storage.list_massnahmen("auf-b4-test") if m.id == m1.id)
        assert reloaded_m1.investitionskosten == 2000.0
        assert reloaded_m1.kosten_quelle == "manuell"
    finally:
        rule_engine.rules = [r for r in rule_engine.rules if r.get("id") != "rule-with-richtwert"]
        storage.data_dir = old_dir
