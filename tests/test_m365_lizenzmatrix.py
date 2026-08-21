"""Tests für Karte #408: M365-Lizenzmatrix Fundament (Lizenzfeld, Regeln, Tier-Blindheit-Fix)."""

import pytest
import yaml
from pathlib import Path
from fastapi.testclient import TestClient

from app.config import RULES_DIR
from app.main import app
from app.models.auftrag import Auftrag
from app.models.technik import TechnikObjekt
from app.models.standort import Standort
from app.services.schema_loader import schema_loader
from app.services.rule_engine import RuleEngine
from app.services.storage import storage

client = TestClient(app)

EXPECTED_SKUS = [
    "bb", "bs", "bp", "me1", "oe3", "me3", "oe5", "me5",
    "exop1", "exop2", "entp1", "entp2", "dfb", "dfep1", "dfep2"
]


def test_schema_m365_lizenzen_field():
    """Prüft, dass das Feld m365_lizenzen im Schema m365_security korrekt definiert ist."""
    schema = schema_loader.get_schema("m365_security")
    assert schema is not None

    was_ist_es = next((a for a in schema["abschnitte"] if a["id"] == "was_ist_es"), None)
    assert was_ist_es is not None

    feld_lizenzen = next((f for f in was_ist_es["felder"] if f["name"] == "m365_lizenzen"), None)
    assert feld_lizenzen is not None
    assert feld_lizenzen["typ"] == "mehrfachauswahl"
    assert feld_lizenzen["regelrelevant"] is True
    assert feld_lizenzen["vertraulichkeit"] == "kundentauglich"

    skus = [w["wert"] for w in feld_lizenzen["werte"]]
    assert skus == EXPECTED_SKUS

    # Freitextfeld lizenztypen muss weiterhin existieren
    feld_freitext = next((f for f in was_ist_es["felder"] if f["name"] == "lizenztypen"), None)
    assert feld_freitext is not None
    assert feld_freitext["typ"] == "text"


def test_rules_loading_and_no_duplicates():
    """Prüft, dass die M365-Regeln valide geladen werden und keine doppelten IDs zwischen den Dateien existieren."""
    engine = RuleEngine()
    rule_ids = [r["id"] for r in engine.rules]

    # Prüfen, dass die neuen 6 Regeln existieren
    expected_rule_ids = [
        "m365-lizenz-conditional-access-fehlt",
        "m365-conditional-access-fehlt",
        "m365-lizenz-defender-o365-fehlt",
        "m365-defender-o365-fehlt",
        "m365-lizenz-audit-fehlt",
        "m365-audit-log-deaktiviert",
    ]
    for rid in expected_rule_ids:
        assert rid in rule_ids, f"Regel {rid} fehlt im RuleEngine"

    # Prüfen, dass keine Schnittmenge zwischen m365_security und m365_lizenzmatrix besteht
    with open(RULES_DIR / "m365_lizenzmatrix.yaml", "r", encoding="utf-8") as f:
        lm_rules = [r["id"] for r in yaml.safe_load(f).get("regeln", [])]
    with open(RULES_DIR / "m365_security.yaml", "r", encoding="utf-8") as f:
        sec_rules = [r["id"] for r in yaml.safe_load(f).get("regeln", [])]

    overlap = set(lm_rules) & set(sec_rules)
    assert len(overlap) == 0, f"Überlappende Regel-IDs gefunden: {overlap}"


def test_conditional_access_tier_blindness_fix():
    """
    Business-Basic-Kunde ohne CA darf NICHT 'm365-conditional-access-fehlt' (Fehlkonfiguration) bekommen,
    sondern 'm365-lizenz-conditional-access-fehlt' (Lizenz-Upgrade-Advisory).
    """
    engine = RuleEngine()

    # 1. Business Basic mit unbekanntem CA-Status -> nur Lizenz-Finding
    obj_bb_unbekannt = TechnikObjekt(
        id="obj-m365-bb-1",
        typ="m365_security",
        bezeichnung="M365 Tenant BB",
        auftrag_id="auf-test-ca",
        daten={
            "m365_lizenzen": ["bb"],
            "conditional_access_regelwerke": "unbekannt"
        }
    )
    findings, _ = engine.evaluate_all("auf-test-ca", [], [obj_bb_unbekannt], [])
    active = {f.quelle: f for f in findings if f.status == "offen" and f.objekt_id == "obj-m365-bb-1"}

    assert "m365-lizenz-conditional-access-fehlt" in active
    assert active["m365-lizenz-conditional-access-fehlt"].schweregrad == "hoch"
    assert "m365-conditional-access-fehlt" not in active

    # 2. Business Basic mit 'nein' CA-Status -> weiterhin nur Lizenz-Finding, NICHT Fehlkonfiguration
    obj_bb_nein = TechnikObjekt(
        id="obj-m365-bb-2",
        typ="m365_security",
        bezeichnung="M365 Tenant BB 2",
        auftrag_id="auf-test-ca",
        daten={
            "m365_lizenzen": ["bb"],
            "conditional_access_regelwerke": "nein"
        }
    )
    findings, _ = engine.evaluate_all("auf-test-ca", [], [obj_bb_nein], [])
    active = {f.quelle: f for f in findings if f.status == "offen" and f.objekt_id == "obj-m365-bb-2"}

    assert "m365-lizenz-conditional-access-fehlt" in active
    assert "m365-conditional-access-fehlt" not in active

    # 3. Business Premium (hat CA) mit 'nein' CA-Status -> Fehlkonfiguration greift!
    obj_bp_nein = TechnikObjekt(
        id="obj-m365-bp",
        typ="m365_security",
        bezeichnung="M365 Tenant BP",
        auftrag_id="auf-test-ca",
        daten={
            "m365_lizenzen": ["bp"],
            "conditional_access_regelwerke": "nein"
        }
    )
    findings, _ = engine.evaluate_all("auf-test-ca", [], [obj_bp_nein], [])
    active = {f.quelle: f for f in findings if f.status == "offen" and f.objekt_id == "obj-m365-bp"}

    assert "m365-conditional-access-fehlt" in active
    assert active["m365-conditional-access-fehlt"].schweregrad == "hoch"
    assert "m365-lizenz-conditional-access-fehlt" not in active

    # 4. Business Premium mit 'ja' CA-Status -> kein Finding
    obj_bp_ja = TechnikObjekt(
        id="obj-m365-bp-ja",
        typ="m365_security",
        bezeichnung="M365 Tenant BP OK",
        auftrag_id="auf-test-ca",
        daten={
            "m365_lizenzen": ["bp"],
            "conditional_access_regelwerke": "ja"
        }
    )
    findings, _ = engine.evaluate_all("auf-test-ca", [], [obj_bp_ja], [])
    active = {f.quelle: f for f in findings if f.status == "offen" and f.objekt_id == "obj-m365-bp-ja"}

    assert "m365-conditional-access-fehlt" not in active
    assert "m365-lizenz-conditional-access-fehlt" not in active


def test_unanswered_m365_lizenzen_is_offener_punkt_not_finding():
    """
    Ein Objekt, bei dem m365_lizenzen nie beantwortet wurde (leere Liste, wie sie
    routes_objekt.py für ein unangetastetes mehrfachauswahl-Feld speichert), darf
    KEIN 'Lizenz fehlt'-Finding auslösen — das würde eine bestätigte Unterlizenzierung
    vortäuschen, obwohl schlicht die Angabe fehlt. Stattdessen muss ein Offener Punkt
    (regelrelevant_leer) entstehen, der zum Nachtragen auffordert.
    """
    engine = RuleEngine()

    obj_unanswered = TechnikObjekt(
        id="obj-m365-lizenzen-leer",
        typ="m365_security",
        bezeichnung="M365 Tenant ohne Lizenzangabe",
        auftrag_id="auf-test-leer",
        daten={
            "m365_lizenzen": [],
            "conditional_access_regelwerke": "nein",
        }
    )
    findings, open_points = engine.evaluate_all("auf-test-leer", [], [obj_unanswered], [])
    active = {f.quelle: f for f in findings if f.status == "offen" and f.objekt_id == "obj-m365-lizenzen-leer"}

    assert "m365-lizenz-conditional-access-fehlt" not in active
    assert "m365-conditional-access-fehlt" not in active

    op_ids = [op.id for op in open_points]
    assert any("m365-lizenz-conditional-access-fehlt-obj-m365-lizenzen-leer" in oid for oid in op_ids)
    matching_op = next(op for op in open_points if "m365-lizenz-conditional-access-fehlt" in op.id)
    assert matching_op.quelle == "regelrelevant_leer"


def test_defender_o365_rules():
    """Prüft Lizenz vs. Konfigurations-Finding für Defender for Office 365 (Plan 1)."""
    engine = RuleEngine()

    # Plan ohne Defender (z.B. Business Standard 'bs')
    obj_bs = TechnikObjekt(
        id="obj-m365-bs",
        typ="m365_security",
        bezeichnung="M365 BS",
        auftrag_id="auf-test-def",
        daten={
            "m365_lizenzen": ["bs"],
            "defender_for_office365_aktiv": "nein"
        }
    )
    findings, _ = engine.evaluate_all("auf-test-def", [], [obj_bs], [])
    active = {f.quelle: f for f in findings if f.status == "offen" and f.objekt_id == "obj-m365-bs"}

    assert "m365-lizenz-defender-o365-fehlt" in active
    assert active["m365-lizenz-defender-o365-fehlt"].schweregrad == "hoch"
    assert "m365-defender-o365-fehlt" not in active

    # Plan mit Defender (z.B. Business Premium 'bp'), aber nicht aktiv -> Fehlkonfiguration hoch
    obj_bp = TechnikObjekt(
        id="obj-m365-bp-def",
        typ="m365_security",
        bezeichnung="M365 BP",
        auftrag_id="auf-test-def",
        daten={
            "m365_lizenzen": ["bp"],
            "defender_for_office365_aktiv": "nein"
        }
    )
    findings, _ = engine.evaluate_all("auf-test-def", [], [obj_bp], [])
    active = {f.quelle: f for f in findings if f.status == "offen" and f.objekt_id == "obj-m365-bp-def"}

    assert "m365-defender-o365-fehlt" in active
    assert active["m365-defender-o365-fehlt"].schweregrad == "hoch"
    assert "m365-lizenz-defender-o365-fehlt" not in active


def test_purview_audit_rules():
    """Prüft Lizenz vs. Konfigurations-Finding für Purview Audit Standard."""
    engine = RuleEngine()

    # Plan ohne Audit (z.B. Business Standard 'bs' oder Exchange Online Plan 1 'exop1')
    obj_bs = TechnikObjekt(
        id="obj-m365-bs-audit",
        typ="m365_security",
        bezeichnung="M365 BS",
        auftrag_id="auf-test-audit",
        daten={
            "m365_lizenzen": ["bs"],
            "audit_logging_aktiv": "nein"
        }
    )
    findings, _ = engine.evaluate_all("auf-test-audit", [], [obj_bs], [])
    active = {f.quelle: f for f in findings if f.status == "offen" and f.objekt_id == "obj-m365-bs-audit"}

    assert "m365-lizenz-audit-fehlt" in active
    assert active["m365-lizenz-audit-fehlt"].schweregrad == "mittel"
    assert "m365-audit-log-deaktiviert" not in active

    # Plan mit Audit (z.B. Microsoft 365 E1 'me1'), aber nicht aktiv -> Fehlkonfiguration mittel
    obj_me1 = TechnikObjekt(
        id="obj-m365-me1",
        typ="m365_security",
        bezeichnung="M365 E1",
        auftrag_id="auf-test-audit",
        daten={
            "m365_lizenzen": ["me1"],
            "audit_logging_aktiv": "nein"
        }
    )
    findings, _ = engine.evaluate_all("auf-test-audit", [], [obj_me1], [])
    active = {f.quelle: f for f in findings if f.status == "offen" and f.objekt_id == "obj-m365-me1"}

    assert "m365-audit-log-deaktiviert" in active
    assert active["m365-audit-log-deaktiviert"].schweregrad == "mittel"
    assert "m365-lizenz-audit-fehlt" not in active


def test_mixed_licenses_and_standalone_addons():
    """Prüft gemischte SKUs (z.B. Business Basic + Entra ID P1 Standalone)."""
    engine = RuleEngine()

    obj_mixed = TechnikObjekt(
        id="obj-m365-mixed",
        typ="m365_security",
        bezeichnung="M365 Mixed",
        auftrag_id="auf-test-mixed",
        daten={
            "m365_lizenzen": ["bb", "entp1"],
            "conditional_access_regelwerke": "nein",
            "defender_for_office365_aktiv": "nein",
            "audit_logging_aktiv": "nein"
        }
    )
    findings, _ = engine.evaluate_all("auf-test-mixed", [], [obj_mixed], [])
    active = {f.quelle: f for f in findings if f.status == "offen" and f.objekt_id == "obj-m365-mixed"}

    # CA ist durch entp1 lizenziert -> Fehlkonfiguration statt Lizenz-Fehlt
    assert "m365-conditional-access-fehlt" in active
    assert "m365-lizenz-conditional-access-fehlt" not in active

    # Defender und Audit fehlen in [bb, entp1] -> Lizenz-Fehlt
    assert "m365-lizenz-defender-o365-fehlt" in active
    assert "m365-lizenz-audit-fehlt" in active


def test_form_create_and_edit_with_m365_lizenzen():
    """Testet Erstellung und Bearbeitung eines m365_security Objekts über HTTP-Routen."""
    auftrag = Auftrag(
        id="auf-test-m365-form",
        projekt_nummer="PR-M365-01",
        kunde="Test M365 Kunde",
        bezeichnung="M365 Form Test",
        aktive_bausteine=["m365_security"]
    )
    storage.save_auftrag(auftrag)

    try:
        # 1. Neuanlage mit mehreren Lizenzen
        post_data = {
            "bezeichnung": "Haupt-Tenant",
            "erfassungsstatus": "vollstaendig",
            "vertraulichkeit": "kundentauglich",
            "tenant_typ": "commercial_cloud",
            "anzahl_lizenzen": "25",
            "lizenztypen": "Business Basic + Entra ID P1",
            "m365_lizenzen": ["bb", "entp1"],
            "conditional_access_regelwerke": "nein",
            "defender_for_office365_aktiv": "nein",
            "audit_logging_aktiv": "ja",
        }

        resp = client.post(
            f"/auftrag/{auftrag.id}/objekt/neu?typ=m365_security",
            data=post_data,
            follow_redirects=False
        )
        assert resp.status_code == 303

        objekte = storage.list_objekte(auftrag.id)
        m365_obj = next((o for o in objekte if o.typ == "m365_security"), None)
        assert m365_obj is not None
        assert m365_obj.daten["m365_lizenzen"] == ["bb", "entp1"]

        # 2. GET Bearbeitungsformular: Checkboxen müssen checked sein
        resp_get = client.get(f"/auftrag/{auftrag.id}/objekt/m365_security/{m365_obj.id}")
        assert resp_get.status_code == 200
        # Prüfe, dass bb und entp1 als checked gerendert sind
        assert 'name="m365_lizenzen" value="bb" checked' in resp_get.text or 'value="bb" checked' in resp_get.text
        assert 'name="m365_lizenzen" value="entp1" checked' in resp_get.text or 'value="entp1" checked' in resp_get.text

        # 3. POST Bearbeiten: Lizenzen aktualisieren auf [bp]
        edit_data = {
            "bezeichnung": "Haupt-Tenant Aktualisiert",
            "version": str(m365_obj.version),
            "erfassungsstatus": "vollstaendig",
            "vertraulichkeit": "kundentauglich",
            "tenant_typ": "commercial_cloud",
            "anzahl_lizenzen": "25",
            "lizenztypen": "Business Premium",
            "m365_lizenzen": ["bp"],
            "conditional_access_regelwerke": "ja",
            "defender_for_office365_aktiv": "ja",
            "audit_logging_aktiv": "ja",
        }
        resp_edit = client.post(
            f"/auftrag/{auftrag.id}/objekt/m365_security/{m365_obj.id}",
            data=edit_data,
            follow_redirects=False
        )
        assert resp_edit.status_code == 303

        updated_obj = storage.load_objekt(auftrag.id, "m365_security", m365_obj.id)
        assert updated_obj.daten["m365_lizenzen"] == ["bp"]

    finally:
        storage.delete_auftrag(auftrag.id)
