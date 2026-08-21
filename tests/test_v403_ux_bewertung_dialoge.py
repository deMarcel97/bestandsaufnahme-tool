"""Tests für Paket 2 aus Card #403:
- ISSUE-006: Vorläufig-Hinweis und Erfassungsstand-Badge in der Bewertungskachel
- ISSUE-002: Sticky Dialog-Footer, scrollbarer Dialog-Body in CSS
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from app.main import app
from app.models.technik import TechnikObjekt
from app.models.standort import Standort
from app.services.storage import storage
from app.services.evaluator import evaluator_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def temp_storage(tmp_path):
    old_dir = storage.data_dir
    storage.data_dir = tmp_path
    yield
    storage.data_dir = old_dir


def test_bewertung_kachel_vorlaeufig_bei_unvollstaendiger_erfassung(tmp_path):
    """Wenn die Erfassung unvollständig ist (unter_50_prozent_warnung = True),
    zeigt die KPI-Kachel 'Vorläufig: <Stufe>' und das Badge 'Erfassungsstand: XX %'."""
    client.post("/auftrag/neu", data={
        "projekt_nummer": "PROJ-403-A",
        "kunde": "Kunde Unvollstaendig",
        "bezeichnung": "Auftrag mit unvollstaendiger Erfassung",
        "aktive_bausteine": ["firewall", "switches"],
    }, follow_redirects=False)
    aid = "auf-auftrag-mit-unvollstaendiger-erfassung"

    client.post(f"/auftrag/{aid}/standort/neu", data={
        "bezeichnung": "Hauptstandort",
        "anzahl_user": 10,
    }, follow_redirects=False)

    # Nur eine leere Firewall angelegt -> Baustein switches fehlt komplett, Feldabdeckung niedrig
    client.post(f"/auftrag/{aid}/objekt/neu?typ=firewall", data={
        "bezeichnung": "FW-1",
        "standort_id": "sto-hauptstandort",
    }, follow_redirects=False)

    res = client.get(f"/auftrag/{aid}/bewertung")
    assert res.status_code == 200
    assert "Vorläufig:" in res.text
    assert "Erfassungsstand:" in res.text
    assert "badge badge-warning" in res.text
    # Detail-Box bleibt weiterhin vorhanden
    assert "alert alert-warning" in res.text


def test_bewertung_kachel_ohne_vorlaeufig_bei_vollstaendiger_erfassung(tmp_path):
    """Wenn die Erfassung vollständig ist (unter_50_prozent_warnung = False),
    zeigt die KPI-Kachel kein 'Vorläufig:' und kein 'Erfassungsstand:'-Badge."""
    client.post("/auftrag/neu", data={
        "projekt_nummer": "PROJ-403-B",
        "kunde": "Kunde Vollstaendig",
        "bezeichnung": "Auftrag mit vollstaendiger Erfassung",
        "aktive_bausteine": ["firewall"],
    }, follow_redirects=False)
    aid = "auf-auftrag-mit-vollstaendiger-erfassung"

    client.post(f"/auftrag/{aid}/standort/neu", data={
        "bezeichnung": "Hauptstandort",
        "anzahl_user": 10,
    }, follow_redirects=False)

    # Firewall vollstaendig ausfüllen
    full_daten = {
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
    fw_obj = TechnikObjekt(
        id="obj-fw-voll",
        typ="firewall",
        bezeichnung="Vollstaendige Firewall",
        auftrag_id=aid,
        standort_id="sto-hauptstandort",
        daten=full_daten
    )
    storage.save_objekt(fw_obj)

    # Prüfen, dass Evaluator tatsächlich unter_50_prozent_warnung = False liefert
    sto = storage.list_standorte(aid)
    objs = storage.list_objekte(aid)
    bew = evaluator_service.evaluate_auftrag(["firewall"], objs, sto)
    assert bew.unter_50_prozent_warnung is False

    res = client.get(f"/auftrag/{aid}/bewertung")
    assert res.status_code == 200
    assert "Vorläufig:" not in res.text
    assert "Erfassungsstand:" not in res.text
    assert "alert alert-warning" not in res.text


def test_bewertung_kachel_erfassungsstand_zeigt_niedrigsten_wert(tmp_path):
    """Regression: Wenn ein ganzer Baustein fehlt (Bausteinabdeckung < 100%),
    aber der erfasste Baustein vollständig ausgefüllt ist (Feldabdeckung = 100%),
    darf das Badge nicht irreführend 100% zeigen - es muss den niedrigeren der
    beiden Werte anzeigen."""
    client.post("/auftrag/neu", data={
        "projekt_nummer": "PROJ-403-C",
        "kunde": "Kunde Fehlender Baustein",
        "bezeichnung": "Auftrag mit fehlendem Baustein",
        "aktive_bausteine": ["firewall", "switches"],
    }, follow_redirects=False)
    aid = "auf-auftrag-mit-fehlendem-baustein"

    client.post(f"/auftrag/{aid}/standort/neu", data={
        "bezeichnung": "Hauptstandort",
        "anzahl_user": 10,
    }, follow_redirects=False)

    # Firewall vollständig ausfüllen, switches komplett auslassen
    full_daten = {
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
    fw_obj = TechnikObjekt(
        id="obj-fw-voll",
        typ="firewall",
        bezeichnung="Vollstaendige Firewall",
        auftrag_id=aid,
        standort_id="sto-hauptstandort",
        daten=full_daten
    )
    storage.save_objekt(fw_obj)

    sto = storage.list_standorte(aid)
    objs = storage.list_objekte(aid)
    bew = evaluator_service.evaluate_auftrag(["firewall", "switches"], objs, sto)
    assert bew.unter_50_prozent_warnung is True
    assert bew.bausteinabdeckung_prozent < bew.feldabdeckung_prozent

    res = client.get(f"/auftrag/{aid}/bewertung")
    assert res.status_code == 200
    niedrigster_wert = min(bew.feldabdeckung_prozent, bew.bausteinabdeckung_prozent)
    assert f"Erfassungsstand: {niedrigster_wert} %" in res.text
    assert f"Erfassungsstand: {bew.feldabdeckung_prozent} %" not in res.text


def test_dialog_css_regeln_vorhanden():
    """Prüft, dass die CSS-Regeln für sticky Dialog-Footer und scrollbaren Body in style.css definiert sind."""
    css_path = Path("app/static/css/style.css")
    assert css_path.exists()
    content = css_path.read_text(encoding="utf-8")

    # Dialog Container
    assert "max-height: calc(100vh - 120px)" in content
    assert "overflow: hidden" in content
    # Dialog Body
    assert "overflow-y: auto" in content
    assert "flex: 1 1 auto" in content
    assert "min-height: 0" in content
    # Mobile Breakpoint
    assert "max-height: calc(100vh - 40px)" in content
