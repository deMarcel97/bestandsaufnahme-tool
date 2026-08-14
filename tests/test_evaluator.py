import pytest
from app.services.evaluator import EvaluatorService
from app.models.technik import TechnikObjekt

def test_evaluator_worst_value_principle():
    evaluator = EvaluatorService()

    # 2 Firewalls: Firewall 1 is < 3 yrs (5 pts), Firewall 2 is > 5 yrs (0 pts)
    fw1 = TechnikObjekt(
        id="fw-1", typ="firewall", bezeichnung="FW 1", auftrag_id="a1", standort_id="s1",
        daten={"hardware_alter": "unter_3_jahre", "security_abo_vorhanden": "ja"}
    )
    fw2 = TechnikObjekt(
        id="fw-2", typ="firewall", bezeichnung="FW 2", auftrag_id="a1", standort_id="s1",
        daten={"hardware_alter": "ueber_5_jahre", "security_abo_vorhanden": "ja"}
    )

    res = evaluator.evaluate_auftrag(["firewall"], [fw1, fw2])
    hw_kat = next(k for k in res.kategorien if k.id == "hardware_und_software")
    alter_krit = next(kr for kr in hw_kat.kriterien if kr.kriterium_id == "hardware_alter")

    # Enforce worst value principle: 0 points (from FW 2) must be used!
    assert alter_krit.erreichte_punkte == 0.0

def test_calculate_objekt_status_thresholds():
    evaluator = EvaluatorService()

    # 1. Fully empty object -> "unbekannt"
    empty_fw = TechnikObjekt(
        id="fw-empty", typ="firewall", bezeichnung="Empty FW", auftrag_id="a1", standort_id="s1",
        daten={}
    )
    assert evaluator.calculate_objekt_status(empty_fw) == "unbekannt"

    # 2. Partially filled object (missing mandatory/rule fields) -> "teilweise"
    partial_fw = TechnikObjekt(
        id="fw-part", typ="firewall", bezeichnung="Partial FW", auftrag_id="a1", standort_id="s1",
        daten={"hersteller": "Sophos"}
    )
    assert evaluator.calculate_objekt_status(partial_fw) == "teilweise"

    # 3. All required & rule-relevant fields filled -> "vollständig"
    full_fw = TechnikObjekt(
        id="fw-full", typ="firewall", bezeichnung="Full FW", auftrag_id="a1", standort_id="s1",
        daten={
            "hersteller": "Sophos",
            "hardware_alter": "unter_3_jahre",
            "wartungsvertrag_vorhanden": "ja",
            "wartungsvertrag_bis": "2028-12-31",
            "security_abo_vorhanden": "ja",
            "security_abo_bis": "2028-12-31",
            "firmware_eol": "nein",
            "letztes_firmware_update": "2026-01-01",
            "dokumentation_vorhanden": "vollstaendig",
            "konfigurationssicherung_aktuell": "ja",
            "konfig_sicherung_automatisch": "ja",
            "zugangsschutz_standort": "abgeschlossener_raum",
            "alarmanlage_vorhanden": "ja",
            "ersatzgeraet_vorhanden": "ja",
            "web_protection_aktiv": "ja",
            "ips_aktiv": "ja",
            "exchange_onprem_dahinter": "nein",
            "mfa_fuer_vpn": "ja",
            "vlan_konzept_umgesetzt": "ja"
        }
    )
    assert evaluator.calculate_objekt_status(full_fw) == "vollständig"

def test_unrated_fields_excluded_from_numerator_and_denominator():
    evaluator = EvaluatorService()

    # Nur ein Feld gesetzt, und das mit "unbekannt" -> nichts wirklich beantwortet.
    fw = TechnikObjekt(
        id="fw-1", typ="firewall", bezeichnung="FW 1", auftrag_id="a1", standort_id="s1",
        daten={"hardware_alter": "unbekannt"}
    )

    res = evaluator.evaluate_auftrag(["firewall"], [fw])
    # Bugfix (2026-08): unbeantwortete Kriterien fallen aus Zähler UND Nenner raus,
    # statt fälschlich als 0 Punkte gewertet zu werden (das hätte Teil-Erfassungen
    # unfair schlecht bewertet). Da hier nichts beantwortet wurde, darf keine Kategorie
    # ins Ergebnis aufgenommen werden und der Erfassungsgrad bleibt bei 0.
    assert res.kategorien == []
    assert res.erfassungsgrad_bewertet_anzahl == 0

def test_partially_rated_object_only_counts_answered_fields():
    evaluator = EvaluatorService()

    fw = TechnikObjekt(
        id="fw-1", typ="firewall", bezeichnung="FW 1", auftrag_id="a1", standort_id="s1",
        daten={"hardware_alter": "unbekannt", "security_abo_vorhanden": "ja"}
    )

    res = evaluator.evaluate_auftrag(["firewall"], [fw])
    all_krit_ids = [kr.kriterium_id for kat in res.kategorien for kr in kat.kriterien]
    # Das unbeantwortete Feld darf in keiner Kategorie als Kriterium auftauchen...
    assert "hardware_alter" not in all_krit_ids
    # ...während das beantwortete Feld (kriterium_id laut Schema: security_abo_firewall)
    # ganz normal mitgezählt wird.
    assert "security_abo_firewall" in all_krit_ids
    assert res.erfassungsgrad_bewertet_anzahl == 1

def test_stufe2_objekt_status_zero_false_empty_list():
    evaluator = EvaluatorService()

    # 0 and False are valid filled values; [] is empty/unfulfilled
    fw_zero_false = TechnikObjekt(
        id="fw-zf", typ="firewall", bezeichnung="Zero False FW", auftrag_id="a1", standort_id="s1",
        daten={
            "hersteller": "Fortinet",
            "hardware_alter": "unter_3_jahre",
            "wartungsvertrag_vorhanden": False,
            "wartungsvertrag_bis": "2026-01-01",
            "security_abo_vorhanden": False,
            "security_abo_bis": "2026-01-01",
            "firmware_eol": False,
            "letztes_firmware_update": "2026-01-01",
            "dokumentation_vorhanden": "vollstaendig",
            "konfigurationssicherung_aktuell": False,
            "konfig_sicherung_automatisch": False,
            "zugangsschutz_standort": "abgeschlossener_raum",
            "alarmanlage_vorhanden": False,
            "ersatzgeraet_vorhanden": False,
            "web_protection_aktiv": False,
            "ips_aktiv": False,
            "exchange_onprem_dahinter": False,
            "mfa_fuer_vpn": False,
            "vlan_konzept_umgesetzt": False
        }
    )
    assert evaluator.calculate_objekt_status(fw_zero_false) == "vollständig"

    fw_empty_list = TechnikObjekt(
        id="fw-el", typ="firewall", bezeichnung="Empty List FW", auftrag_id="a1", standort_id="s1",
        daten={"hersteller": []}
    )
    assert evaluator.calculate_objekt_status(fw_empty_list) == "unbekannt"

def test_stufe2_worst_standort_tracking():
    evaluator = EvaluatorService()

    good_fw = TechnikObjekt(
        id="fw-good", typ="firewall", bezeichnung="Good FW", auftrag_id="a1", standort_id="s1",
        daten={"hardware_alter": "unter_3_jahre", "security_abo_vorhanden": "ja"}
    )
    bad_fw = TechnikObjekt(
        id="fw-bad", typ="firewall", bezeichnung="Bad FW", auftrag_id="a1", standort_id="s2",
        daten={"hardware_alter": "ueber_5_jahre", "security_abo_vorhanden": "nein"}
    )

    res = evaluator.evaluate_auftrag(["firewall"], [good_fw, bad_fw])
    assert res.schlechtester_standort_id == "s2"
    assert res.schlechtester_standort_prozent is not None

