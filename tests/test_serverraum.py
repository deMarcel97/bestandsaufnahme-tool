import pytest
from app.services.rule_engine import RuleEngine
from app.models.standort import Standort
from app.models.technik import TechnikObjekt

def test_serverraum_rule_triggering():
    re = RuleEngine()
    sto = Standort(id="sto-1", auftrag_id="auf-1", bezeichnung="Zentrale")

    # 1. Bad Serverraum object -> Rules trigger
    bad_srvraum = TechnikObjekt(
        id="srvraum-bad",
        typ="serverraum",
        bezeichnung="Schlechter Serverraum",
        auftrag_id="auf-1",
        standort_id="sto-1",
        daten={
            "zugangskontrolle": "frei_zugaenglich",  # -> srv-zugang-frei
            "zutrittsprotokollierung": "nein",  # -> srv-keine-protokollierung
            "zugangsberechtigte_dokumentiert": "nein",  # -> srv-berechtigte-undokumentiert
            "umweltsensorik": "keine",  # -> srv-keine-sensorik
            "brandmeldeanlage": "nein",  # -> srv-keine-brandmeldung
            "loeschanlage": "keine",  # -> srv-keine-loeschanlage
            "stromeinspeisung": "eine_einspeisung",  # -> srv-eine-einspeisung
            "notstromaggregat": "nein",  # -> srv-kein-notstromaggregat
        }
    )

    findings, open_pts = re.evaluate_all("auf-1", [sto], [bad_srvraum], [])
    bad_finding_ids = [f.quelle for f in findings if f.objekt_id == "srvraum-bad" and f.status == "offen"]

    expected_bad_rules = [
        "srv-zugang-frei",
        "srv-keine-protokollierung",
        "srv-berechtigte-undokumentiert",
        "srv-keine-sensorik",
        "srv-keine-brandmeldung",
        "srv-keine-loeschanlage",
        "srv-eine-einspeisung",
        "srv-kein-notstromaggregat"
    ]

    for rule_id in expected_bad_rules:
        assert rule_id in bad_finding_ids, f"Expected rule {rule_id} to trigger for bad serverraum"

    # Test bad serverraum with key & test-alt
    bad_srvraum2 = TechnikObjekt(
        id="srvraum-bad2",
        typ="serverraum",
        bezeichnung="Serverraum 2",
        auftrag_id="auf-1",
        standort_id="sto-1",
        daten={
            "zugangskontrolle": "schluessel_undokumentiert",  # -> srv-schluessel-undokumentiert
            "umweltsensorik": "nur_messung",  # -> srv-sensorik-ohne-alarm
            "notstromaggregat": "ja",
            "notstromaggregat_letzter_test": "2020-01-01"  # -> srv-aggregat-test-alt
        }
    )

    findings2, _ = re.evaluate_all("auf-1", [sto], [bad_srvraum2], [])
    bad2_finding_ids = [f.quelle for f in findings2 if f.objekt_id == "srvraum-bad2" and f.status == "offen"]

    assert "srv-schluessel-undokumentiert" in bad2_finding_ids
    assert "srv-sensorik-ohne-alarm" in bad2_finding_ids
    assert "srv-aggregat-test-alt" in bad2_finding_ids

    # 2. Good Serverraum object -> 0 rules trigger
    good_srvraum = TechnikObjekt(
        id="srvraum-good",
        typ="serverraum",
        bezeichnung="Guter Serverraum",
        auftrag_id="auf-1",
        standort_id="sto-1",
        daten={
            "zugangskontrolle": "transponder_protokolliert",
            "zutrittsprotokollierung": "ja",
            "zugangsberechtigte_dokumentiert": "ja",
            "umweltsensorik": "mit_alarmierung",
            "brandmeldeanlage": "ja",
            "loeschanlage": "gas",
            "stromeinspeisung": "zwei_getrennte_einspeisungen",
            "notstromaggregat": "ja",
            "notstromaggregat_letzter_test": "2026-06-01"
        }
    )

    findings_good, _ = re.evaluate_all("auf-1", [sto], [good_srvraum], [])
    good_finding_ids = [f.quelle for f in findings_good if f.objekt_id == "srvraum-good" and f.status == "offen"]
    assert len(good_finding_ids) == 0, f"Expected 0 findings for good serverraum, got {good_finding_ids}"
