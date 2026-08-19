import pytest
from starlette.testclient import TestClient
from app.main import app
from app.models.auftrag import Auftrag
from app.models.standort import Standort
from app.services.storage import storage


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "data_dir", tmp_path)
    return TestClient(app)


def test_wizard_init_and_full_flow(client, tmp_path):
    # 1. Auftrag anlegen
    auftrag = Auftrag(
        id="proj-wiz-test",
        kunde="Wizard Kunde",
        projekt_nummer="P-WIZ-01",
        bezeichnung="Test Wizard Auftrag",
        aktive_bausteine=[],
    )
    storage.save_auftrag(auftrag)

    # 2. Wizard initialisieren
    resp = client.post("/auftrag/proj-wiz-test/wizard/init", follow_redirects=True)
    assert resp.status_code == 200
    assert "Interaktive Bestandsaufnahme" in resp.text
    assert "Auftragsgrunddaten" in resp.text

    # Fortschritt prüfen
    progress = storage.load_wizard_progress("proj-wiz-test")
    assert progress is not None
    assert progress.current_step == 1

    # 3. Schritt 1: Auftragsgrunddaten speichern
    resp = client.post(
        "/auftrag/proj-wiz-test/wizard/step/1",
        data={
            "kunde": "Wizard Kunde Aktualisiert",
            "projekt_nummer": "P-WIZ-99",
            "bezeichnung": "Aktualisierter Wizard Auftrag",
            "abgrenzung": "Scope nur Hauptstandort",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Standort-Grunddaten" in resp.text

    # 4. Schritt 2: Standort-Grunddaten speichern
    resp = client.post(
        "/auftrag/proj-wiz-test/wizard/step/2",
        data={
            "bezeichnung": "Hauptstandort Berlin",
            "anzahl_user": "25",
            "strasse": "Musterstr. 1",
            "plz": "10115",
            "ort": "Berlin",
            "ansprechpartner_vor_ort": "Max Mustermann",
            "funktion": "IT-Leiter",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Internetanbindung" in resp.text

    # 5. Schritt 3: Internetanbindungen speichern
    resp = client.post(
        "/auftrag/proj-wiz-test/wizard/step/3",
        data={
            "hat_internetanbindung": "ja",
            "anbieter": "Telekom",
            "art": "Glasfaser_FTTH",
            "bandbreite_down": "1000",
            "bandbreite_up": "500",
            "feste_ip_vorhanden": "ja",
            "redundante_anbindung": "nein",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Firewall" in resp.text

    # 6. Schritt 4: Firewall speichern
    resp = client.post(
        "/auftrag/proj-wiz-test/wizard/step/4",
        data={
            "hat_firewall": "ja",
            "hersteller": "Fortinet",
            "modell": "FortiGate 60F",
            "hardware_alter": "unter_3_jahre",
            "wartungsvertrag_vorhanden": "ja",
            "ha_cluster_eingerichtet": "nein",
            "ips_ids_aktiv": "ja",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Switch" in resp.text

    # 7. Schritt 5: Switch speichern
    resp = client.post(
        "/auftrag/proj-wiz-test/wizard/step/5",
        data={
            "hat_switch": "ja",
            "hersteller": "Cisco",
            "modell": "Catalyst 9200",
            "port_anzahl": "48",
            "ports_belegt": "32",
            "management_typ": "managed_l2",
            "netztrennung": "vlan_getrennt",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "WLAN" in resp.text

    # 8. Schritt 6: Access Point speichern
    resp = client.post(
        "/auftrag/proj-wiz-test/wizard/step/6",
        data={
            "hat_access_point": "ja",
            "hersteller": "Ubiquiti",
            "modell": "UniFi U6 Pro",
            "gast_wlan_vorhanden": "ja",
            "gast_wlan_isoliert": "ja",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Server" in resp.text

    # 9. Schritt 7: Server & Virtualisierung speichern
    resp = client.post(
        "/auftrag/proj-wiz-test/wizard/step/7",
        data={
            "hat_server": "ja",
            "wird_virtualisiert": "ja",
            "hypervisor_typ": "vmware_esxi",
            "hersteller": "Dell",
            "modell": "PowerEdge R740",
            "anzahl_vms": "6",
            "hardware_alter": "unter_3_jahre",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Storage" in resp.text

    # 10. Schritt 8: Storage speichern
    resp = client.post(
        "/auftrag/proj-wiz-test/wizard/step/8",
        data={
            "hat_storage": "ja",
            "bereitstellung": "shared_storage",
            "hersteller_shared": "Synology",
            "kapazitaet_netto_tb": "16",
            "fuellgrad_prozent": "60",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Backup" in resp.text

    # 11. Schritt 9: Backup speichern
    resp = client.post(
        "/auftrag/proj-wiz-test/wizard/step/9",
        data={
            "hat_backup": "ja",
            "backup_software": "veeam",
            "backup_ziel": "lokal_nas",
            "strategie": "3_2_1_regel",
            "testwiederherstellung": "ja_regelmaessig_protokolliert",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "USV" in resp.text

    # 12. Schritt 10: USV speichern
    resp = client.post(
        "/auftrag/proj-wiz-test/wizard/step/10",
        data={
            "hat_usv": "ja",
            "hersteller": "APC",
            "modell": "Smart-UPS 1500",
            "batterie_alter": "unter_3_jahre",
            "abschaltsignal_an_server": "ja",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Clients" in resp.text

    # 13. Schritt 11: Clients speichern
    resp = client.post(
        "/auftrag/proj-wiz-test/wizard/step/11",
        data={
            "hat_clients": "ja",
            "anzahl_windows_clients": "20",
            "anzahl_mac_clients": "5",
            "anzahl_linux_clients": "0",
            "haupt_betriebssystem_version": "windows_11",
            "edr_antivirus_zentral_gemanagt": "ja",
            "zentrales_patchmanagement_aktiv": "ja",
            "lokale_adminrechte_eingeschraenkt": "ja",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "M365" in resp.text

    # 14. Schritt 12: M365 speichern
    resp = client.post(
        "/auftrag/proj-wiz-test/wizard/step/12",
        data={
            "hat_m365": "ja",
            "tenant_typ": "microsoft_365_business",
            "mfa_fuer_alle_benutzer": "ja",
            "mfa_fuer_administratoren": "ja",
            "m365_drittanbieter_backup_aktiv": "ja",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Organisation" in resp.text

    # 15. Schritt 13: Organisation speichern
    resp = client.post(
        "/auftrag/proj-wiz-test/wizard/step/13",
        data={
            "hat_organisation": "ja",
            "notfallhandbuch_status": "vollstaendig_aktuell",
            "it_dokumentation_status": "vollstaendig_aktuell",
            "it_sicherheitsrichtlinie_unterschrieben": "ja_alle",
            "passwort_manager_einsatz": "unternehmensweit_verpflichtend",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Zusammenfassung der Bestandsaufnahme" in resp.text

    # 16. Zusammenfassung anzeigen & überprüfen
    resp = client.get("/auftrag/proj-wiz-test/wizard/zusammenfassung")
    assert resp.status_code == 200
    assert "Fortinet" in resp.text
    assert "Catalyst 9200" in resp.text
    assert "PowerEdge R740" in resp.text
    assert "Synology" in resp.text
    assert "Veeam" in resp.text or "veeam" in resp.text

    # 17. Wizard abschließen und alle Bausteine erzeugen
    resp = client.post("/auftrag/proj-wiz-test/wizard/abschliessen", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/auftrag/proj-wiz-test/erfassung"

    # Fortschritt muss gelöscht sein
    assert storage.load_wizard_progress("proj-wiz-test") is None

    # Auftrag prüfen
    saved_auftrag = storage.load_auftrag("proj-wiz-test")
    assert saved_auftrag.kunde == "Wizard Kunde Aktualisiert"
    assert saved_auftrag.projekt_nummer == "P-WIZ-99"

    expected_bausteine = [
        "firewall", "switch", "access_point", "server_virtualisierung",
        "storage", "backup", "usv", "clients", "m365_security", "organisation_prozesse"
    ]
    for b in expected_bausteine:
        assert b in saved_auftrag.aktive_bausteine

    # Standorte prüfen
    standorte = storage.list_standorte("proj-wiz-test")
    assert len(standorte) == 1
    assert standorte[0].bezeichnung == "Hauptstandort Berlin"
    assert standorte[0].anzahl_user == 25
    assert len(standorte[0].anbindungen) == 1
    assert standorte[0].anbindungen[0].anbieter == "Telekom"
    assert standorte[0].anbindungen[0].art == "Glasfaser_FTTH"
    assert standorte[0].anbindungen[0].bandbreite_down_mbit == 1000.0

    # Technik-Objekte prüfen
    objekte = storage.list_objekte("proj-wiz-test")
    typen = [o.typ for o in objekte]
    for b in expected_bausteine:
        assert b in typen

    fw = next(o for o in objekte if o.typ == "firewall")
    assert fw.daten["hersteller"] == "Fortinet"
    assert fw.daten["modell"] == "FortiGate 60F"
    assert fw.daten["hardware_alter"] == "unter_3_jahre"

    sw = next(o for o in objekte if o.typ == "switch")
    assert sw.daten["hersteller"] == "Cisco"
    assert sw.daten["port_anzahl"] == 48
    assert sw.daten["management_typ"] == "managed_l2"

    ap = next(o for o in objekte if o.typ == "access_point")
    assert ap.daten["hersteller"] == "Ubiquiti"
    assert ap.daten["gast_wlan_isoliert"] == "ja"

    srv = next(o for o in objekte if o.typ == "server_virtualisierung")
    assert srv.daten["hersteller"] == "Dell"
    assert srv.daten["anzahl_vms"] == 6

    sto = next(o for o in objekte if o.typ == "storage")
    assert sto.daten["hersteller_shared"] == "Synology"
    assert sto.daten["kapazitaet_netto_tb"] == 16.0

    bk = next(o for o in objekte if o.typ == "backup")
    assert bk.daten["backup_software"] == "veeam"
    assert bk.daten["strategie"] == "3_2_1_regel"

    usv = next(o for o in objekte if o.typ == "usv")
    assert usv.daten["hersteller"] == "APC"
    assert usv.daten["abschaltsignal_an_server"] == "ja"

    cl = next(o for o in objekte if o.typ == "clients")
    assert cl.daten["anzahl_windows_clients"] == 20
    assert cl.daten["edr_antivirus_zentral_gemanagt"] == "ja"

    m365 = next(o for o in objekte if o.typ == "m365_security")
    assert m365.daten["mfa_fuer_alle_benutzer"] == "ja"
    assert m365.standort_id is None

    org = next(o for o in objekte if o.typ == "organisation_prozesse")
    assert org.daten["notfallhandbuch_status"] == "vollstaendig_aktuell"
    assert org.standort_id is None


def test_wizard_navigation_helpers(client, tmp_path):
    auftrag = Auftrag(
        id="proj-nav-test",
        kunde="Nav Kunde",
        bezeichnung="Test Nav",
        aktive_bausteine=[],
    )
    storage.save_auftrag(auftrag)

    # Init
    client.post("/auftrag/proj-nav-test/wizard/init", follow_redirects=True)
    prog = storage.load_wizard_progress("proj-nav-test")
    assert prog.current_step == 1

    # Step 1 überspringen via GET Link
    resp = client.get("/auftrag/proj-nav-test/wizard/skip", follow_redirects=False)
    assert resp.status_code == 303
    prog = storage.load_wizard_progress("proj-nav-test")
    assert prog.current_step == 2

    # Direkt zu Schritt 5 springen
    resp = client.get("/auftrag/proj-nav-test/wizard/goto/5", follow_redirects=False)
    assert resp.status_code == 303
    prog = storage.load_wizard_progress("proj-nav-test")
    assert prog.current_step == 5

    # Zurück-Button testen
    resp = client.get("/auftrag/proj-nav-test/wizard/back", follow_redirects=False)
    assert resp.status_code == 303
    prog = storage.load_wizard_progress("proj-nav-test")
    assert prog.current_step == 4

    # Abbruch via GET (pausieren)
    resp = client.get("/auftrag/proj-nav-test/wizard/abbruch", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/auftrag/proj-nav-test"
    assert storage.load_wizard_progress("proj-nav-test") is not None


def test_auftrag_creation_with_start_wizard(client, tmp_path):
    """Prüft, dass start_wizard=1 direkt in den Wizard weiterleitet und start_wizard='' zur Übersicht."""
    # 1. Mit start_wizard="1"
    resp = client.post(
        "/auftrag/neu",
        data={
            "kunde": "Neukunde Direktstart",
            "bezeichnung": "Direktstart Projekt",
            "start_wizard": "1",
            "aktive_bausteine": ["firewall", "switch"],
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    loc = resp.headers["location"]
    assert loc.endswith("/wizard")
    auftrag_id = loc.split("/")[2]

    # 2. Ohne start_wizard
    resp2 = client.post(
        "/auftrag/neu",
        data={
            "kunde": "Neukunde Standard",
            "bezeichnung": "Standard Projekt",
            "start_wizard": "",
            "aktive_bausteine": ["firewall"],
        },
        follow_redirects=False,
    )
    assert resp2.status_code == 303
    assert not resp2.headers["location"].endswith("/wizard")


def test_wizard_resumption_dialog_and_reset(client, tmp_path):
    """Prüft den Wiederaufnahme-Dialog bei bestehendem Fortschritt und die Fortsetzen/Neu-Starten-Aktionen."""
    auftrag = Auftrag(
        id="proj-resume-test",
        kunde="Resume Kunde",
        bezeichnung="Test Wiederaufnahme",
        aktive_bausteine=["firewall"],
    )
    storage.save_auftrag(auftrag)

    # 1. Frischer Wizard (kein Fortschritt): Soll direkt Schritt 1 zeigen
    resp = client.get("/auftrag/proj-resume-test/wizard")
    assert resp.status_code == 200
    assert "Auftragsgrunddaten" in resp.text
    assert "Gespeicherter Erfassungsstand vorhanden" not in resp.text

    # 2. Schritt 1 speichern
    client.post(
        "/auftrag/proj-resume-test/wizard/step/1",
        data={
            "kunde": "Resume Kunde",
            "bezeichnung": "Test Wiederaufnahme",
        },
        follow_redirects=True,
    )

    # 3. Wizard erneut aufrufen ohne resume-Parameter -> Wiederaufnahme-Dialog anzeigen
    resp_dialog = client.get("/auftrag/proj-resume-test/wizard")
    assert resp_dialog.status_code == 200
    assert "Gespeicherter Erfassungsstand vorhanden" in resp_dialog.text
    assert "Erfassung fortsetzen & prüfen" in resp_dialog.text
    assert "Erfassung neu starten" in resp_dialog.text

    # 4. Fortsetzen mit resume=1 -> Schritt 2 Formular zeigen
    resp_resume = client.get("/auftrag/proj-resume-test/wizard?resume=1")
    assert resp_resume.status_code == 200
    assert "Standort-Grunddaten" in resp_resume.text
    assert "Gespeicherter Erfassungsstand vorhanden" not in resp_resume.text

    # 5. Neu starten via POST init -> Reset auf Schritt 1
    resp_init = client.post("/auftrag/proj-resume-test/wizard/init", follow_redirects=False)
    assert resp_init.status_code == 303
    prog = storage.load_wizard_progress("proj-resume-test")
    assert prog.current_step == 1
    assert len(prog.completed_steps) == 0

