import pytest
from app.services.rule_engine import RuleEngine
from app.models.standort import Standort
from app.models.technik import TechnikObjekt

def test_usv_rule_triggering():
    re = RuleEngine()
    sto = Standort(id="sto-1", auftrag_id="auf-1", bezeichnung="Zentrale")

    # 1. Bad USV object -> All 8 USV rules should trigger
    bad_usv = TechnikObjekt(
        id="usv-bad",
        typ="usv",
        bezeichnung="Schlechte USV",
        auftrag_id="auf-1",
        standort_id="sto-1",
        daten={
            "hersteller": "APC",
            "ueberbrueckungszeit_minuten": 3,  # < 5 -> triggers usv-ueberbrueckung-kurz
            "auslastung_prozent": 85,  # > 80 -> triggers usv-ueberlastet
            "batterie_alter": "ueber_5_jahre",  # -> triggers usv-batterie-alt
            "garantie_geraet_bis": "2020-01-01",  # -> triggers usv-garantie-abgelaufen
            "garantie_batterie_bis": "2020-01-01",  # -> triggers usv-batteriegarantie-abgelaufen
            "wartungsvertrag_vorhanden": "nein",  # -> triggers usv-kein-wartungsvertrag
            "letzter_batterietest": "2020-01-01",  # -> triggers usv-kein-batterietest
            "abschaltsignal_an_server": "nein"  # -> triggers usv-kein-abschaltsignal
        }
    )

    findings, open_pts = re.evaluate_all("auf-1", [sto], [bad_usv], [])
    bad_finding_ids = [f.quelle for f in findings if f.objekt_id == "usv-bad" and f.status == "offen"]

    expected_rules = [
        "usv-batterie-alt",
        "usv-kein-batterietest",
        "usv-kein-abschaltsignal",
        "usv-ueberlastet",
        "usv-kein-wartungsvertrag",
        "usv-garantie-abgelaufen",
        "usv-batteriegarantie-abgelaufen",
        "usv-ueberbrueckung-kurz"
    ]

    for rule_id in expected_rules:
        assert rule_id in bad_finding_ids, f"Expected rule {rule_id} to trigger for bad USV object"

    # 2. Good USV object -> 0 rules trigger
    good_usv = TechnikObjekt(
        id="usv-good",
        typ="usv",
        bezeichnung="Gute USV",
        auftrag_id="auf-1",
        standort_id="sto-1",
        daten={
            "hersteller": "APC",
            "ueberbrueckungszeit_minuten": 20,  # >= 5 -> no trigger
            "auslastung_prozent": 45,  # <= 80 -> no trigger
            "batterie_alter": "unter_3_jahre",  # -> no trigger
            "garantie_geraet_bis": "2030-01-01",  # -> no trigger
            "garantie_batterie_bis": "2030-01-01",  # -> no trigger
            "wartungsvertrag_vorhanden": "ja",  # -> no trigger
            "letzter_batterietest": "2026-06-01",  # recent -> no trigger
            "abschaltsignal_an_server": "ja"  # -> no trigger
        }
    )

    findings_good, _ = re.evaluate_all("auf-1", [sto], [good_usv], [])
    good_finding_ids = [f.quelle for f in findings_good if f.objekt_id == "usv-good" and f.status == "offen"]
    assert len(good_finding_ids) == 0, f"Expected 0 findings for good USV object, got {good_finding_ids}"
