import pytest
from app.services.rule_engine import RuleEngine
from app.models.standort import Standort
from app.models.technik import TechnikObjekt

def test_access_point_rule_triggering():
    re = RuleEngine()
    sto = Standort(id="sto-1", auftrag_id="auf-1", bezeichnung="Zentrale")

    # 1. Bad Access Point object -> All 7 AP rules trigger
    bad_ap = TechnikObjekt(
        id="ap-bad",
        typ="access_point",
        bezeichnung="Schlechter Access Point",
        auftrag_id="auf-1",
        standort_id="sto-1",
        daten={
            "hersteller": "Cisco",
            "wlan_standard": "wifi4_oder_aelter",  # -> ap-wlan-veraltet
            "management": "standalone",  # -> ap-standalone
            "gast_wlan_vorhanden": "ja",
            "gast_wlan_isoliert": "nein",  # -> ap-gastnetz-unsicher
            "verschluesselung_wpa3": "nein",  # -> ap-kein-wpa3
            "firmware_aktuell": "nein",  # -> ap-firmware-veraltet
            "garantie_bis": "2020-01-01",  # -> ap-garantie-abgelaufen
            "wartungsvertrag_vorhanden": "nein"  # -> ap-kein-wartungsvertrag
        }
    )

    findings, open_pts = re.evaluate_all("auf-1", [sto], [bad_ap], [])
    bad_finding_ids = [f.quelle for f in findings if f.objekt_id == "ap-bad" and f.status == "offen"]

    expected_rules = [
        "ap-wlan-veraltet",
        "ap-standalone",
        "ap-gastnetz-unsicher",
        "ap-kein-wpa3",
        "ap-firmware-veraltet",
        "ap-garantie-abgelaufen",
        "ap-kein-wartungsvertrag"
    ]

    for rule_id in expected_rules:
        assert rule_id in bad_finding_ids, f"Expected rule {rule_id} to trigger for bad access point"

    # 2. Good Access Point object -> 0 rules trigger
    good_ap = TechnikObjekt(
        id="ap-good",
        typ="access_point",
        bezeichnung="Guter Access Point",
        auftrag_id="auf-1",
        standort_id="sto-1",
        daten={
            "hersteller": "Cisco",
            "wlan_standard": "wifi6",
            "management": "cloud_controller",
            "gast_wlan_vorhanden": "ja",
            "gast_wlan_isoliert": "ja",
            "verschluesselung_wpa3": "ja",
            "firmware_aktuell": "ja",
            "garantie_bis": "2030-01-01",
            "wartungsvertrag_vorhanden": "ja"
        }
    )

    findings_good, _ = re.evaluate_all("auf-1", [sto], [good_ap], [])
    good_finding_ids = [f.quelle for f in findings_good if f.objekt_id == "ap-good" and f.status == "offen"]
    assert len(good_finding_ids) == 0, f"Expected 0 findings for good access point, got {good_finding_ids}"
