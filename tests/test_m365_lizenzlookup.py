"""Tests für Karte #407: Lizenzmatrix als Datenquelle statt Planlisten in Regeln."""

import json

import pytest

from app.services.m365_lizenzmatrix import MATRIX_DATEI, m365_lizenzmatrix
from app.services.rule_engine import RuleEngine, RuleValidationError
from app.models.technik import TechnikObjekt
from app.services.schema_loader import schema_loader

# Die neun Features, die ausschliesslich das "Microsoft 365"-Bundle über EMS
# mitbringt. Genau hier lag der Fehler, an dem Matrix B (#407) gescheitert
# wäre: sie führte E3 nur einmal und hätte einem Office-365-E3-Kunden Intune
# und Conditional Access als vorhanden gemeldet.
NUR_MIT_EMS = [
    "app_protection",
    "autopilot",
    "compliance_policies",
    "conditional_access",
    "config_profiles",
    "defender_endpoint",
    "intune_full",
    "sspr",
    "windows_enterprise",
]


def test_office365_e3_hat_kein_ems():
    """Office 365 E3 deckt keines der EMS-Features ab, Microsoft 365 E3 alle."""
    for feature_id in NUR_MIT_EMS:
        assert m365_lizenzmatrix.deckt_feature(["oe3"], feature_id) is False, (
            f"Office 365 E3 darf '{feature_id}' nicht als lizenziert melden"
        )
        assert m365_lizenzmatrix.deckt_feature(["me3"], feature_id) is True, (
            f"Microsoft 365 E3 muss '{feature_id}' abdecken"
        )


def test_office365_e3_bekommt_lizenz_advisory_statt_fehlkonfiguration():
    """
    Ein Office-365-E3-Kunde ohne Conditional Access ist unterlizenziert, nicht
    fehlkonfiguriert. Der Fehlkonfigurations-Befund würde behaupten, das Feature
    sei vorhanden und nur nicht eingerichtet — im Kundengespräch nicht haltbar.
    """
    engine = RuleEngine()
    obj = TechnikObjekt(
        id="obj-oe3",
        typ="m365_security",
        bezeichnung="Tenant mit Office 365 E3",
        auftrag_id="auf-407-oe3",
        daten={
            "m365_lizenzen": ["oe3"],
            "conditional_access_regelwerke": "nein",
        },
    )
    findings, _ = engine.evaluate_all("auf-407-oe3", [], [obj], [])
    aktiv = {f.quelle for f in findings if f.status == "offen" and f.objekt_id == "obj-oe3"}

    assert "m365-lizenz-conditional-access-fehlt" in aktiv
    assert "m365-conditional-access-fehlt" not in aktiv


def test_addon_gilt_nicht_als_lizenziert():
    """
    'Add-on' heisst zubuchbar, nicht vorhanden. Würde es als lizenziert zählen,
    entstünde ein Fehlkonfigurations-Befund für etwas, das der Kunde nie gekauft hat.
    """
    zeile = m365_lizenzmatrix.get_feature_status("bp", "pim")
    assert zeile["enthalten"] == "Add-on"
    assert m365_lizenzmatrix.deckt_feature(["bp"], "pim") is False


def test_mehrere_skus_eine_deckende_genuegt():
    """Business Basic plus Entra ID P1 als Standalone deckt Conditional Access ab."""
    assert m365_lizenzmatrix.deckt_feature(["bb"], "conditional_access") is False
    assert m365_lizenzmatrix.deckt_feature(["bb", "entp1"], "conditional_access") is True


def test_unbekannte_feature_id_faellt_beim_laden_auf():
    """
    Ein Tippfehler in der feature_id muss beim Laden knallen. Ohne diese Prüfung
    würde die Regel schlicht nie zutreffen und das Finding still verschlucken.
    """
    engine = RuleEngine()
    regel = {
        "id": "m365-tippfehler",
        "gilt_fuer": "m365_security",
        "bedingung": {
            "alle": [
                {"feld": "m365_lizenzen", "operator": "lizenz_deckt", "wert": "conditional_acces"}
            ]
        },
    }
    with pytest.raises(RuleValidationError, match="conditional_acces"):
        engine.validate_rule(regel, "test.yaml")


def test_matrix_codes_decken_schema_ab():
    """Jeder Lizenzcode der Matrix muss im Schema wählbar sein und umgekehrt."""
    schema = schema_loader.get_schema("m365_security")
    feld = next(
        f
        for a in schema["abschnitte"]
        for f in a["felder"]
        if f["name"] == "m365_lizenzen"
    )
    schema_codes = {w["wert"] for w in feld["werte"]}

    with open(MATRIX_DATEI, "r", encoding="utf-8") as f:
        matrix = json.load(f)["matrix"]
    matrix_codes = {z["lizenzcode"] for z in matrix}

    assert matrix_codes == schema_codes, (
        f"Nur in der Matrix: {matrix_codes - schema_codes}; "
        f"nur im Schema: {schema_codes - matrix_codes}"
    )


def test_jede_zeile_traegt_eine_evidenzstufe():
    """
    Die Matrix ist ein ungeprüftes Rechercheergebnis. Der Evidenzstatus hält
    fest, was davon gegen eine Primärquelle steht — ohne das Feld verschwindet
    die Wissenslücke unsichtbar in einem Kundenbericht.
    """
    with open(MATRIX_DATEI, "r", encoding="utf-8") as f:
        daten = json.load(f)

    erlaubt = {"bestaetigt", "wahrscheinlich", "umstritten", "unbestaetigt"}
    for zeile in daten["matrix"]:
        assert zeile["evidenzstatus"] in erlaubt
        assert "quelle" in zeile

    # Die im Matrixvergleich benannten Zweifelsfälle müssen markiert bleiben.
    umstritten = {z["feature_id"] for z in daten["matrix"] if z["evidenzstatus"] == "umstritten"}
    assert "sharepoint_quota" in umstritten
    assert "audio_conferencing" in umstritten

    assert daten["meta"]["evidenz_offen"]["anzahl_features"] > 0
