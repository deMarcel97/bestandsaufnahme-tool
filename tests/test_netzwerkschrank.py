import pytest
from app.services.rule_engine import RuleEngine
from app.models.standort import Standort
from app.models.technik import TechnikObjekt

def test_netzwerkschrank_rule_triggering():
    re = RuleEngine()
    sto = Standort(id="sto-1", auftrag_id="auf-1", bezeichnung="Zentrale")

    # 1. Bad Netzwerkschrank object -> All rules trigger
    bad_schrank = TechnikObjekt(
        id="schrank-bad",
        typ="netzwerkschrank",
        bezeichnung="Schlechter Schrank",
        auftrag_id="auf-1",
        standort_id="sto-1",
        daten={
            "art": "offen_im_raum",  # -> nwschrank-offen
            "abschliessbar": "nein",  # -> nwschrank-nicht-abschliessbar
            "belueftung": "keine",  # -> nwschrank-keine-belueftung
            "patchpanel_vorhanden": "ja",
            "patchpanel_beschriftung": "keine",  # -> nwschrank-patchpanel-unbeschriftet
            "verkabelungsdokumentation": "keine",  # -> nwschrank-keine-verkabelungsdoku
            "ausfuehrung_durch": "gewachsen_ohne_dokumentation",  # -> nwschrank-gewachsen
            "kabeltyp": "cat5",  # -> nwschrank-cat5
            "verkabelung_alter": "ueber_10_jahre",  # -> nwschrank-verkabelung-alt
            "erweiterungsreserve": "keine"  # -> nwschrank-keine-reserve
        }
    )

    findings, open_pts = re.evaluate_all("auf-1", [sto], [bad_schrank], [])
    bad_finding_ids = [f.quelle for f in findings if f.objekt_id == "schrank-bad" and f.status == "offen"]

    expected_rules = [
        "nwschrank-offen",
        "nwschrank-nicht-abschliessbar",
        "nwschrank-keine-belueftung",
        "nwschrank-patchpanel-unbeschriftet",
        "nwschrank-keine-verkabelungsdoku",
        "nwschrank-gewachsen",
        "nwschrank-cat5",
        "nwschrank-verkabelung-alt",
        "nwschrank-keine-reserve"
    ]

    for rule_id in expected_rules:
        assert rule_id in bad_finding_ids, f"Expected rule {rule_id} to trigger for bad netzwerkschrank"

    # 2. Good Netzwerkschrank object -> 0 rules trigger
    good_schrank = TechnikObjekt(
        id="schrank-good",
        typ="netzwerkschrank",
        bezeichnung="Guter Schrank",
        auftrag_id="auf-1",
        standort_id="sto-1",
        daten={
            "art": "19_zoll_schrank",
            "abschliessbar": "ja",
            "belueftung": "aktiv_klimatisiert",
            "patchpanel_vorhanden": "ja",
            "patchpanel_beschriftung": "vollstaendig",
            "verkabelungsdokumentation": "vollstaendig",
            "ausfuehrung_durch": "fachfirma",
            "kabeltyp": "cat7",
            "verkabelung_alter": "unter_5_jahre",
            "erweiterungsreserve": "ausreichend"
        }
    )

    findings_good, _ = re.evaluate_all("auf-1", [sto], [good_schrank], [])
    good_finding_ids = [f.quelle for f in findings_good if f.objekt_id == "schrank-good" and f.status == "offen"]
    assert len(good_finding_ids) == 0, f"Expected 0 findings for good netzwerkschrank, got {good_finding_ids}"

def test_netzwerkschrank_ohne_patchpanel_kein_beschriftungs_finding():
    # Kein Patchpanel vorhanden -> die Beschriftungsfrage ist im Formular ausgeblendet
    # und darf auch bei stehengebliebenem/leerem Wert kein Finding erzeugen.
    re = RuleEngine()
    sto = Standort(id="sto-1", auftrag_id="auf-1", bezeichnung="Zentrale")
    schrank_ohne_patchpanel = TechnikObjekt(
        id="schrank-ohne-patchpanel",
        typ="netzwerkschrank",
        bezeichnung="Schrank ohne Patchpanel",
        auftrag_id="auf-1",
        standort_id="sto-1",
        daten={
            "patchpanel_vorhanden": "nein",
            "patchpanel_beschriftung": "",
        }
    )
    findings, _ = re.evaluate_all("auf-1", [sto], [schrank_ohne_patchpanel], [])
    finding_ids = [f.quelle for f in findings if f.objekt_id == "schrank-ohne-patchpanel" and f.status == "offen"]
    assert "nwschrank-patchpanel-unbeschriftet" not in finding_ids
