"""Tests für Karte #314: Hierarchische Gliederung der Offenen Punkte
nach Standort -> Thema/Baustein mit Ausklapp-Toggles (<details>/<summary>).
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.auftrag import Auftrag, Dokumentenanforderung
from app.models.standort import Standort
from app.models.technik import TechnikObjekt, OffenerPunktItem
from app.services.storage import storage

client = TestClient(app)


@pytest.fixture(autouse=True)
def temp_storage(tmp_path):
    old_dir = storage.data_dir
    storage.data_dir = tmp_path
    yield
    storage.data_dir = old_dir


def test_offene_punkte_hierarchisch_nach_standort_und_thema():
    """Prüft, dass offene Punkte nach Standort -> Thema gegliedert werden
    und Toggle-Elemente (<details>/<summary>) im HTML gerendert werden."""
    auftrag = Auftrag(
        id="auf-op-1",
        projekt_nummer="P-2026-OP",
        kunde="Test GmbH",
        bezeichnung="Test Bestandsaufnahme",
        aktive_bausteine=["m365_security", "firewall"],
        dokumentenanforderung=[
            Dokumentenanforderung(bezeichnung="Netzwerkplan", status="angefordert")
        ]
    )
    storage.save_auftrag(auftrag)

    sto1 = Standort(
        id="sto-1",
        auftrag_id=auftrag.id,
        bezeichnung="Hauptstandort München",
        ort="München"
    )
    sto2 = Standort(
        id="sto-2",
        auftrag_id=auftrag.id,
        bezeichnung="Zweigstelle Berlin",
        ort="Berlin"
    )
    storage.save_standort(sto1)
    storage.save_standort(sto2)

    # Objekt mit Rückfrage an Standort 1
    obj1 = TechnikObjekt(
        id="obj-m365",
        auftrag_id=auftrag.id,
        standort_id="sto-1",
        typ="m365_security",
        bezeichnung="M365 Cloud",
        daten={"mfa_status": "rueckfrage"}
    )
    storage.save_objekt(obj1)

    # Objekt an Standort 2
    obj2 = TechnikObjekt(
        id="obj-fw",
        auftrag_id=auftrag.id,
        standort_id="sto-2",
        typ="firewall",
        bezeichnung="FortiGate 60F",
        offene_punkte=[
            OffenerPunktItem(id="op-custom-1", text="Admin-Zugang klären", status="offen", standort_id="sto-2", objekt_typ="firewall")
        ]
    )
    storage.save_objekt(obj2)

    response = client.get(f"/auftrag/{auftrag.id}/offene_punkte")
    assert response.status_code == 200
    html = response.text

    # Standorte als Details/Summary vorhanden
    assert "Hauptstandort München" in html
    assert "Zweigstelle Berlin" in html
    assert "Standortübergreifend / Allgemein" in html

    # Themenbereiche vorhanden
    assert "Microsoft 365" in html or "M365" in html
    assert "Firewall" in html
    assert "Dokumente" in html and "Unterlagen" in html

    # Details- und Summary-Tags für Toggles vorhanden
    assert "<details class=\"group-details\" open>" in html
    assert "<details class=\"subgroup-details\" open>" in html
    assert "toggleAllOpenPoints" in html
    assert "Alle aufklappen" in html
    assert "Alle zuklappen" in html


def test_offene_punkte_leerer_zustand():
    """Prüft die Anzeige bei fehlerfreiem, vollständig erfasstem Bestand."""
    auftrag = Auftrag(
        id="auf-op-empty",
        projekt_nummer="P-2026-EMPTY",
        kunde="Clean AG",
        bezeichnung="Vollständig",
        aktive_bausteine=[]
    )
    storage.save_auftrag(auftrag)
    sto = Standort(id="sto-clean", auftrag_id=auftrag.id, bezeichnung="Zentrale")
    storage.save_standort(sto)

    response = client.get(f"/auftrag/{auftrag.id}/offene_punkte")
    assert response.status_code == 200
    assert "Keine offenen Punkte" in response.text


def test_offene_punkte_respects_sichtbar_wenn():
    """Prüft, dass Felder mit nicht erfüllter sichtbar_wenn Bedingung keine offenen Punkte erzeugen."""
    auftrag = Auftrag(
        id="auf-op-vis",
        projekt_nummer="P-2026-VIS",
        kunde="Visible GmbH",
        bezeichnung="Sichtbarkeitstest",
        aktive_bausteine=["firewall"]
    )
    storage.save_auftrag(auftrag)
    sto = Standort(id="sto-vis", auftrag_id=auftrag.id, bezeichnung="Zentrale")
    storage.save_standort(sto)

    # Firewall ohne HA (ha_cluster_eingerichtet = nein)
    # Felder unter sichtbar_wenn: {feld: ha_cluster_eingerichtet, wert: ja} dürfen NICHT als offene Punkte gemeldet werden
    fw = TechnikObjekt(
        id="fw-vis",
        auftrag_id=auftrag.id,
        standort_id="sto-vis",
        typ="firewall",
        bezeichnung="FortiGate 60F",
        daten={
            "hersteller": "Fortinet",
            "modell": "FortiGate 60F",
            "ha_cluster_eingerichtet": "nein",
        }
    )
    storage.save_objekt(fw)

    from app.services.progress import progress_service
    items = progress_service.collect_offene_punkte(auftrag, [sto], [fw], [])
    field_names = [it.id for it in items]

    # HA-spezifische Felder dürfen nicht in items sein
    for fid in field_names:
        assert "ha_sync" not in fid.lower()
        assert "ha_heartbeat" not in fid.lower()


def test_fehlender_baustein_differenziert_kritisch_wichtig():
    """Karte #423: ein komplett fehlender Baustein ist nicht mehr pauschal
    'kritisch' — Kernkomponenten (Firewall, ...) bleiben kritisch, periphere
    Bausteine (Access Point, ...) werden auf 'wichtig' runtergestuft."""
    auftrag = Auftrag(
        id="auf-op-krit",
        projekt_nummer="P-2026-KRIT",
        kunde="Kritikalitaet GmbH",
        bezeichnung="Kritikalitaetstest",
        aktive_bausteine=["firewall", "access_point"]
    )
    storage.save_auftrag(auftrag)
    sto = Standort(id="sto-krit", auftrag_id=auftrag.id, bezeichnung="Zentrale")
    storage.save_standort(sto)

    from app.services.progress import progress_service
    items = progress_service.collect_offene_punkte(auftrag, [sto], [], [])

    fehlt_firewall = next(it for it in items if it.id == "op-struktur-fehlt-firewall")
    fehlt_access_point = next(it for it in items if it.id == "op-struktur-fehlt-access_point")

    assert fehlt_firewall.prioritaet == "kritisch"
    assert fehlt_access_point.prioritaet == "wichtig"


def test_calculate_progress_counts_all_visible_fields():
    """Prüft, dass calculate_progress alle sichtbaren Felder zählt und nicht nur Pflichtfelder (ISSUE-004)."""
    from app.services.progress import progress_service

    # 1. Wizard-Teilerfassung: Firewall mit nur wenigen Feldern
    fw_wizard = TechnikObjekt(
        id="fw-wiz-1",
        auftrag_id="auf-1",
        typ="firewall",
        bezeichnung="FortiGate 60F",
        erfassungsstatus="teilweise",
        daten={
            "hersteller": "Fortinet",
            "modell_fortinet": "FortiGate 60F",
            "hardware_alter": "unter_3_jahre",
            "wartungsvertrag_vorhanden": "ja",
            "ips_aktiv": "ja",
        },
    )

    prog = progress_service.calculate_progress(["firewall"], [fw_wizard])
    assert "firewall" in prog
    fw_prog = prog["firewall"]

    # Gesamt darf nicht nur 1 sein (Pflichtfeld), sondern muss alle sichtbaren Felder umfassen
    assert fw_prog["gesamt"] >= 20
    assert fw_prog["ausgefuellt"] == 5
    # Prozentsatz muss realistisch unter 100% liegen (z. B. 16.1%)
    assert 0.0 < fw_prog["prozent"] < 100.0

    # 2. Leerzustand
    fw_empty = TechnikObjekt(id="fw-empty", auftrag_id="auf-1", typ="firewall", bezeichnung="FW", daten={})
    prog_empty = progress_service.calculate_progress(["firewall"], [fw_empty])
    assert prog_empty["firewall"]["prozent"] == 0.0
    assert prog_empty["firewall"]["ausgefuellt"] == 0


