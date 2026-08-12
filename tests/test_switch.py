import pytest
from app.services.rule_engine import RuleEngine
from app.models.standort import Standort
from app.models.technik import TechnikObjekt

def test_switch_rule_triggering():
    re = RuleEngine()
    sto = Standort(id="sto-1", auftrag_id="auf-1", bezeichnung="Zentrale")

    # 1. Bad Switch object -> All 9 switch rules trigger
    bad_switch = TechnikObjekt(
        id="sw-bad",
        typ="switch",
        bezeichnung="Schlechter Switch",
        auftrag_id="auf-1",
        standort_id="sto-1",
        daten={
            "hersteller": "Cisco",
            "management_typ": "unmanaged",  # -> sw-unmanaged
            "netztrennung": "nein",  # -> sw-keine-netztrennung
            "firmware_aktuell": "nein",  # -> sw-firmware-veraltet
            "garantie_bis": "2020-01-01",  # -> sw-garantie-abgelaufen
            "wartungsvertrag_vorhanden": "nein",  # -> sw-kein-wartungsvertrag
            "konfigurationssicherung_aktuell": "nein",  # -> sw-konfig-sicherung-fehlt
            "zugangsschutz_management": "http_telnet",  # -> sw-zugangsschutz-unsicher
            "port_security_aktiv": "nein",  # -> sw-keine-port-security
            "loop_protection_aktiv": "nein"  # -> sw-kein-loop-protection
        }
    )

    findings, open_pts = re.evaluate_all("auf-1", [sto], [bad_switch], [])
    bad_finding_ids = [f.quelle for f in findings if f.objekt_id == "sw-bad" and f.status == "offen"]

    expected_rules = [
        "sw-unmanaged",
        "sw-keine-netztrennung",
        "sw-firmware-veraltet",
        "sw-garantie-abgelaufen",
        "sw-kein-wartungsvertrag",
        "sw-konfig-sicherung-fehlt",
        "sw-zugangsschutz-unsicher",
        "sw-keine-port-security",
        "sw-kein-loop-protection"
    ]

    for rule_id in expected_rules:
        assert rule_id in bad_finding_ids, f"Expected rule {rule_id} to trigger for bad switch"

    # 2. Good Switch object -> 0 rules trigger
    good_switch = TechnikObjekt(
        id="sw-good",
        typ="switch",
        bezeichnung="Guter Switch",
        auftrag_id="auf-1",
        standort_id="sto-1",
        daten={
            "hersteller": "Cisco",
            "management_typ": "fully_managed",
            "netztrennung": "ja",
            "firmware_aktuell": "ja",
            "garantie_bis": "2030-01-01",
            "wartungsvertrag_vorhanden": "ja",
            "konfigurationssicherung_aktuell": "ja",
            "zugangsschutz_management": "mfa_und_ssh_https",
            "port_security_aktiv": "ja",
            "loop_protection_aktiv": "ja"
        }
    )

    findings_good, _ = re.evaluate_all("auf-1", [sto], [good_switch], [])
    good_finding_ids = [f.quelle for f in findings_good if f.objekt_id == "sw-good" and f.status == "offen"]
    assert len(good_finding_ids) == 0, f"Expected 0 findings for good switch, got {good_finding_ids}"
