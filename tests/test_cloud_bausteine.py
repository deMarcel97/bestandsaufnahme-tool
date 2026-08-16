"""Tests für Karte #315: Cloud-Bausteine ohne Standortzuweisung (M365 & Co.)."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.auftrag import Auftrag
from app.models.standort import Standort
from app.models.technik import TechnikObjekt
from app.services.storage import storage
from app.services.schema_loader import schema_loader
from app.services.report_builder import report_builder
from app.services.evaluator import evaluator_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def temp_storage(tmp_path):
    old_dir = storage.data_dir
    storage.data_dir = tmp_path
    yield
    storage.data_dir = old_dir


def test_schema_m365_security_standortbezug_false():
    """1. Schema m365_security.yaml enthält standortbezug: false."""
    schema = schema_loader.get_schema("m365_security")
    assert schema is not None
    assert schema.get("standortbezug") is False


def test_technik_objekt_standort_id_optional():
    """2. TechnikObjekt.standort_id ist Optional[str] = None."""
    obj = TechnikObjekt(
        id="obj-test-cloud",
        typ="m365_security",
        bezeichnung="Microsoft 365 Tenant",
        auftrag_id="auf-1",
        standort_id=None
    )
    assert obj.standort_id is None
    storage.save_objekt(obj)

    loaded = storage.load_objekt("auf-1", "m365_security", "obj-test-cloud")
    assert loaded is not None
    assert loaded.standort_id is None


def test_cloud_form_and_routes_handling():
    """3 & 4. Formular zeigt 'Standortübergreifend (Cloud)' und Routen setzen standort_id=None."""
    auftrag = Auftrag(
        id="auf-cloud-1",
        projekt_nummer="P-2026-CLOUD",
        kunde="Cloud Kunde AG",
        bezeichnung="Cloud Bestandsaufnahme",
        aktive_bausteine=["m365_security", "firewall"]
    )
    storage.save_auftrag(auftrag)

    sto = Standort(
        id="sto-1",
        auftrag_id=auftrag.id,
        bezeichnung="Hauptsitz",
        ort="Hamburg"
    )
    storage.save_standort(sto)

    # GET Neuanlage M365 Formular
    resp = client.get(f"/auftrag/{auftrag.id}/objekt/neu?typ=m365_security")
    assert resp.status_code == 200
    assert "Standortübergreifend (Cloud)" in resp.text
    assert '<input type="hidden" name="standort_id" value="">' in resp.text

    # POST Neuanlage M365 Objekt
    resp_post = client.post(
        f"/auftrag/{auftrag.id}/objekt/neu?typ=m365_security",
        data={
            "bezeichnung": "Zentraler M365 Tenant",
            "standort_id": "",  # leer vom Formular
            "betreut_durch": "wir",
            "tenant_typ": "commercial_cloud",
            "mfa_fuer_alle_benutzer": "ja",
            "mfa_fuer_administratoren": "ja"
        },
        follow_redirects=False
    )
    assert resp_post.status_code == 303

    objekte = storage.list_objekte(auftrag.id)
    m365_obj = next((o for o in objekte if o.typ == "m365_security"), None)
    assert m365_obj is not None
    assert m365_obj.standort_id is None
    assert m365_obj.bezeichnung == "Zentraler M365 Tenant"

    # GET Bearbeiten M365 Formular
    resp_edit_get = client.get(f"/auftrag/{auftrag.id}/objekt/m365_security/{m365_obj.id}")
    assert resp_edit_get.status_code == 200
    assert "Standortübergreifend (Cloud)" in resp_edit_get.text

    # POST Bearbeiten M365 Objekt
    resp_edit_post = client.post(
        f"/auftrag/{auftrag.id}/objekt/m365_security/{m365_obj.id}",
        data={
            "bezeichnung": "Zentraler M365 Tenant Aktualisiert",
            "standort_id": "",
            "betreut_durch": "wir",
            "version": str(m365_obj.version),
            "tenant_typ": "commercial_cloud",
            "mfa_fuer_alle_benutzer": "ja"
        },
        follow_redirects=False
    )
    assert resp_edit_post.status_code == 303

    updated_obj = storage.load_objekt(auftrag.id, "m365_security", m365_obj.id)
    assert updated_obj.standort_id is None
    assert updated_obj.bezeichnung == "Zentraler M365 Tenant Aktualisiert"


def test_erfassung_uebersicht_cloud_abschnitt():
    """5. Erfassungsübersicht enthält eigenen Abschnitt für 'Standortübergreifend / Cloud-Dienste'."""
    auftrag = Auftrag(
        id="auf-cloud-2",
        projekt_nummer="P-2026-CLOUD2",
        kunde="Musterfirma",
        bezeichnung="Audit",
        aktive_bausteine=["m365_security", "firewall"]
    )
    storage.save_auftrag(auftrag)

    sto = Standort(
        id="sto-1",
        auftrag_id=auftrag.id,
        bezeichnung="Zentrale",
        ort="Köln"
    )
    storage.save_standort(sto)

    cloud_obj = TechnikObjekt(
        id="obj-m365-tenant",
        typ="m365_security",
        bezeichnung="M365 Cloud Tenant",
        auftrag_id=auftrag.id,
        standort_id=None,
        betreut_durch="wir",
        erfassungsstatus="vollstaendig",
        daten={"tenant_typ": "commercial_cloud"}
    )
    storage.save_objekt(cloud_obj)

    resp = client.get(f"/auftrag/{auftrag.id}/erfassung")
    assert resp.status_code == 200
    assert "Standortübergreifend / Cloud-Dienste" in resp.text
    assert "M365 Cloud Tenant" in resp.text
    assert "menu-cloud" in resp.text


def test_report_builder_cloud_abschnitt():
    """6. Analysebericht enthält Abschnitt 'Standortübergreifende Infrastruktur & Cloud-Dienste'."""
    auftrag = Auftrag(
        id="auf-cloud-3",
        projekt_nummer="P-2026-REP",
        kunde="Cloud Enterprise",
        bezeichnung="IT-Audit 2026",
        aktive_bausteine=["m365_security", "firewall"]
    )
    storage.save_auftrag(auftrag)

    sto = Standort(
        id="sto-1",
        auftrag_id=auftrag.id,
        bezeichnung="Hauptstandort",
        ort="Frankfurt"
    )
    storage.save_standort(sto)

    cloud_obj = TechnikObjekt(
        id="obj-m365-rep",
        typ="m365_security",
        bezeichnung="Unternehmensweiter M365 Tenant",
        auftrag_id=auftrag.id,
        standort_id=None,
        betreut_durch="wir",
        daten={
            "tenant_typ": "commercial_cloud",
            "mfa_fuer_alle_benutzer": "ja"
        }
    )
    storage.save_objekt(cloud_obj)

    standorte = [sto]
    objekte = [cloud_obj]
    bewertung = evaluator_service.evaluate_auftrag(auftrag.aktive_bausteine, objekte, standorte)

    markdown = report_builder.build_analysebericht(
        auftrag=auftrag,
        standorte=standorte,
        objekte=objekte,
        massnahmen=[],
        bewertung=bewertung,
        findings=[],
        ziel_vertraulichkeit="kundentauglich"
    )

    assert "### Standortübergreifende Infrastruktur & Cloud-Dienste" in markdown
    assert "Unternehmensweiter M365 Tenant (Microsoft 365 & Security)" in markdown
    assert "Als Cloud-Plattform wird ein kommerzieller Microsoft 365 Tenant genutzt." in markdown
    # Chapter 4 Übersichtstabelle
    assert "| Unternehmensweiter M365 Tenant | Microsoft 365 & Security | Standortübergreifend |" in markdown
