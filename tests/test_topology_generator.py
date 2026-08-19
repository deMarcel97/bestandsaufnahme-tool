import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.auftrag import Auftrag
from app.models.standort import Standort, Internetanbindung
from app.models.technik import TechnikObjekt
from app.services.topology_generator import (
    generate_network_topology_mermaid,
    generate_network_topology_summary_text,
    sanitize_mermaid_id,
    sanitize_mermaid_label,
    sanitize_edge_label,
)
from app.services.report_builder import report_builder
from app.services.exporter import exporter_service
from app.services.evaluator import evaluator_service
from app.services.storage import storage

client = TestClient(app)


@pytest.fixture(autouse=True)
def temp_storage(tmp_path):
    old_dir = storage.data_dir
    storage.data_dir = tmp_path
    yield
    storage.data_dir = old_dir


def test_sanitize_helpers():
    assert sanitize_mermaid_id("123-abc.def/ghi") == "n_123_abc_def_ghi"
    assert sanitize_mermaid_id("sw_core_1") == "sw_core_1"
    assert sanitize_mermaid_label('Switch "Core" [Rack 1]') == "Switch 'Core' (Rack 1)"
    assert sanitize_edge_label("Trunk | VLAN 10,20") == "Trunk / VLAN 10,20"


def test_empty_topology():
    mermaid = generate_network_topology_mermaid(None, [])
    assert "flowchart TD" in mermaid
    assert "Keine Netzwerkkomponenten erfasst" in mermaid


def test_full_hierarchy_topology():
    standort = Standort(
        id="sto-1",
        auftrag_id="auf-1",
        bezeichnung="Hauptsitz München",
        ort="München",
        anzahl_user=50,
        anbindungen=[
            Internetanbindung(
                anbieter="Telekom",
                art="Glasfaser_FTTH",
                bandbreite_down_mbit=1000.0,
                bandbreite_up_mbit=1000.0,
                ist_backup_leitung="nein",
                redundante_anbindung="ja",
            ),
            Internetanbindung(
                anbieter="Vodafone",
                art="DSL",
                bandbreite_down_mbit=100.0,
                bandbreite_up_mbit=40.0,
                ist_backup_leitung="ja",
                redundante_anbindung="ja",
            ),
        ],
    )

    fw = TechnikObjekt(
        id="fw-1",
        typ="firewall",
        bezeichnung="FortiGate 100F",
        auftrag_id="auf-1",
        standort_id="sto-1",
        daten={"hersteller": "Fortinet", "modell": "100F", "aufbau": "Cluster_aktiv_passiv"},
    )

    sw_core = TechnikObjekt(
        id="sw-core-1",
        typ="switch",
        bezeichnung="Core Switch Cisco 9300",
        auftrag_id="auf-1",
        standort_id="sto-1",
        daten={"hersteller": "Cisco", "modell": "Catalyst 9300", "geschwindigkeit": "10G", "cluster_verbund": "ja", "anbindung_firewall_typ": "lag"},
    )

    sw_access = TechnikObjekt(
        id="sw-acc-1",
        typ="switch",
        bezeichnung="Etagenverteiler OG1",
        auftrag_id="auf-1",
        standort_id="sto-1",
        daten={"hersteller": "Aruba_HPE", "modell": "2930F", "geschwindigkeit": "1G", "poe_vorhanden": "ja", "port_anzahl": 48},
    )

    server = TechnikObjekt(
        id="srv-1",
        typ="server_virtualisierung",
        bezeichnung="VMware Host Cluster",
        auftrag_id="auf-1",
        standort_id="sto-1",
        daten={
            "wird_virtualisiert": "ja",
            "hypervisor_typ": "vmware_vsphere",
            "hypervisor_version": "8.0 U2",
            "hersteller": "dell",
            "modell": "PowerEdge R750",
            "anzahl_host_server": 2,
            "ha_cluster_eingerichtet": "ja",
        },
    )

    storage_obj = TechnikObjekt(
        id="sto-dev-1",
        typ="storage",
        bezeichnung="Synology SAN",
        auftrag_id="auf-1",
        standort_id="sto-1",
        daten={
            "bereitstellung": "shared_storage",
            "hersteller_shared": "synology",
            "protokoll_anbindung": "iscsi",
            "kapazitaet_netto_tb": 24,
        },
    )

    vm1 = TechnikObjekt(
        id="vm-1",
        typ="vm",
        bezeichnung="DC01",
        auftrag_id="auf-1",
        standort_id="sto-1",
        daten={
            "name": "DC01",
            "betriebssystem": "Windows Server 2022",
            "cpu_kerne": 4,
            "ram_gb": 16,
            "funktion_dienst": "Domain Controller & DNS",
            "host_referenz": "srv-1",
            "ha_faehig": "ja",
        },
    )

    ap = TechnikObjekt(
        id="ap-1",
        typ="access_point",
        bezeichnung="UniFi AP Pro OG1",
        auftrag_id="auf-1",
        standort_id="sto-1",
        daten={
            "hersteller": "Ubiquiti",
            "modell": "U6 Pro",
            "wlan_standard": "wifi6",
            "management": "cloud_controller",
            "gast_wlan_vorhanden": "ja",
        },
    )

    clients = TechnikObjekt(
        id="cli-1",
        typ="clients",
        bezeichnung="Arbeitsplätze Zentrale",
        auftrag_id="auf-1",
        standort_id="sto-1",
        daten={
            "anzahl_windows_clients": 40,
            "anzahl_mac_clients": 5,
            "anzahl_linux_clients": 2,
            "einsatzart": "festarbeitsplaetze_und_notebooks",
        },
    )

    usv = TechnikObjekt(
        id="usv-1",
        typ="usv",
        bezeichnung="APC Smart-UPS 3000",
        auftrag_id="auf-1",
        standort_id="sto-1",
        daten={"hersteller": "APC", "leistung_va": 3000, "autonomiezeit_min": 25},
    )

    objekte = [fw, sw_core, sw_access, server, storage_obj, vm1, ap, clients, usv]

    mermaid = generate_network_topology_mermaid(standort, objekte)

    # Subgraphs check
    assert 'subgraph WAN ["🌐 Internet & WAN-Anbindung"]' in mermaid
    assert 'subgraph Perimeter ["🛡️ Perimeter & Security"]' in mermaid
    assert 'subgraph CoreSwitching ["🔀 Core- & Distribution-Switching"]' in mermaid
    assert 'subgraph AccessSwitching ["🔌 Access-Switching"]' in mermaid
    assert 'subgraph ServerStorageInfra ["🖥️ Server, Storage & Virtualisierung"]' in mermaid
    assert 'subgraph VMs ["📦 Virtuelle Maschinen"]' in mermaid
    assert 'subgraph WLANInfra ["📶 WLAN-Infrastruktur"]' in mermaid
    assert 'subgraph Endpoints ["💻 Clients & Endgeräte"]' in mermaid
    assert 'subgraph PowerInfra ["⚡ Stromabsicherung & USV"]' in mermaid

    # Nodes content check
    assert "Telekom" in mermaid
    assert "Vodafone" in mermaid
    assert "FortiGate 100F" in mermaid
    assert "Core Switch Cisco 9300" in mermaid
    assert "Etagenverteiler OG1" in mermaid
    assert "PowerEdge R750" in mermaid
    assert "Synology SAN" in mermaid
    assert "DC01" in mermaid
    assert "UniFi AP Pro OG1" in mermaid
    assert "Arbeitsplätze Zentrale" in mermaid
    assert "APC Smart-UPS 3000" in mermaid

    # Connections check
    assert "Backup WAN" in mermaid
    assert "Uplink" in mermaid
    assert "SAN / iSCSI / NFS" in mermaid
    assert "Hypervisor Host" in mermaid
    assert "LAN 1G" in mermaid
    assert "USV-Schutz" in mermaid


def test_topology_summary_text():
    standort = Standort(
        id="sto-1",
        auftrag_id="auf-1",
        bezeichnung="Zweigstelle Hamburg",
        anbindungen=[
            Internetanbindung(anbieter="Telekom", art="Glasfaser_FTTH", bandbreite_down_mbit=500, bandbreite_up_mbit=500)
        ],
    )
    fw = TechnikObjekt(id="fw-1", typ="firewall", bezeichnung="Branch-FW", auftrag_id="auf-1", standort_id="sto-1")
    sw = TechnikObjekt(id="sw-1", typ="switch", bezeichnung="Branch-Switch", auftrag_id="auf-1", standort_id="sto-1")

    text = generate_network_topology_summary_text(standort, [fw, sw])
    assert "Topologie-Übersicht für Zweigstelle Hamburg:" in text
    assert "Telekom via Glasfaser_FTTH" in text
    assert "Branch-FW" in text
    assert "Branch-Switch" in text


def test_report_builder_and_docx_export_with_mermaid():
    auftrag = Auftrag(id="auf-topo-1", projekt_nummer="PROJ-TOPO", kunde="Topologie Kunde", bezeichnung="Topologie Test Projekt")
    standort = Standort(
        id="sto-topo-1",
        auftrag_id="auf-topo-1",
        bezeichnung="Zentrale",
        ort="Frankfurt",
        anbindungen=[Internetanbindung(anbieter="Telekom", art="Glasfaser_FTTH", bandbreite_down_mbit=1000, bandbreite_up_mbit=1000)],
    )
    fw = TechnikObjekt(
        id="fw-topo-1",
        typ="firewall",
        bezeichnung="Edge-Firewall",
        auftrag_id="auf-topo-1",
        standort_id="sto-topo-1",
        daten={"hersteller": "Sophos", "modell": "XGS 2100"},
    )
    sw = TechnikObjekt(
        id="sw-topo-1",
        typ="switch",
        bezeichnung="Hauptverteiler",
        auftrag_id="auf-topo-1",
        standort_id="sto-topo-1",
        daten={"hersteller": "Aruba_HPE", "modell": "CX 6200F", "port_anzahl": 48},
    )

    bew = evaluator_service.evaluate_auftrag(["firewall", "switch"], [fw, sw], [standort])

    # Report builder markdown check
    md_report = report_builder.build_analysebericht(auftrag, [standort], [fw, sw], [], bew, [], ziel_vertraulichkeit="kundentauglich")
    assert "#### Netzwerktopologie" in md_report
    assert "```mermaid" in md_report
    assert "flowchart TD" in md_report
    assert "Edge-Firewall" in md_report

    # DOCX export check
    docx_stream = exporter_service.export_analysebericht_docx(auftrag, [standort], [fw, sw], [], "kundentauglich")
    assert docx_stream is not None
    assert docx_stream.getbuffer().nbytes > 0


def test_web_routes_erfassung_and_preview():
    client.post("/auftrag/neu", data={
        "projekt_nummer": "PROJ-WEB-TOPO",
        "kunde": "Web Topo Kunde",
        "bezeichnung": "Web Topo Auftrag",
        "aktive_bausteine": ["firewall", "switch"],
    }, follow_redirects=False)
    aid = "auf-web-topo-auftrag"

    client.post(f"/auftrag/{aid}/standort/neu", data={
        "bezeichnung": "Berlin Office",
        "anzahl_user": 20,
    }, follow_redirects=False)

    client.post(f"/auftrag/{aid}/objekt/neu?typ=firewall", data={
        "bezeichnung": "Berlin-Firewall",
        "standort_id": "sto-berlin-office",
    }, follow_redirects=False)

    # 1. Erfassung shows topology container & mermaid block
    res_erf = client.get(f"/auftrag/{aid}/erfassung")
    assert res_erf.status_code == 200
    assert "Netzwerktopologie: Berlin Office" in res_erf.text
    assert "zoomTopology" in res_erf.text

    # 2. Topologie preview route
    res_prev = client.get(f"/auftrag/{aid}/topologie-preview")
    assert res_prev.status_code == 200
    assert "Netzwerktopologie: Berlin Office" in res_prev.text
    assert "Berlin-Firewall" in res_prev.text

    # 3. Overview page has visualize trigger button
    res_ueber = client.get(f"/auftrag/{aid}")
    assert res_ueber.status_code == 200
    assert "Netzplan visualisieren" in res_ueber.text
