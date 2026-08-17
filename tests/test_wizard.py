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


def test_wizard_init_and_flow(client, tmp_path):
    # 1. Auftrag anlegen
    auftrag = Auftrag(
        id="proj-wiz-test",
        kunde="Wizard Kunde",
        projekt_nummer="P-WIZ-01",
        bezeichnung="Test Wizard Auftrag",
        aktive_bausteine=[]
    )
    storage.save_auftrag(auftrag)

    # 2. Wizard initialisieren
    resp = client.post("/auftrag/proj-wiz-test/wizard/init", follow_redirects=True)
    assert resp.status_code == 200
    assert "Interaktive Erfassung" in resp.text
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
            "abgrenzung": "Scope nur Hauptstandort"
        },
        follow_redirects=True
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
            "funktion": "IT-Leiter"
        },
        follow_redirects=True
    )
    assert resp.status_code == 200
    assert "Internetanbindungen" in resp.text

    # 5. Schritt 3: Internetanbindungen speichern
    resp = client.post(
        "/auftrag/proj-wiz-test/wizard/step/3",
        data={
            "hat_internetanbindung": "ja",
            "anbieter": "Telekom",
            "art": "Glasfaser",
            "bandbreite_down": "1000",
            "bandbreite_up": "500"
        },
        follow_redirects=True
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
            "alter": "2",
            "wartungsvertrag": "ja"
        },
        follow_redirects=True
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
            "anzahl_ports": "48",
            "anzahl_genutzt": "32",
            "managed": "managed"
        },
        follow_redirects=True
    )
    assert resp.status_code == 200
    assert "Backup" in resp.text

    # 8. Schritt 6: Backup speichern
    resp = client.post(
        "/auftrag/proj-wiz-test/wizard/step/6",
        data={
            "hat_backup": "ja",
            "strategie": "3-2-1",
            "software": "Veeam",
            "ziel": "NAS",
            "testwiederherstellung": "ja"
        },
        follow_redirects=True
    )
    assert resp.status_code == 200
    assert "Zusammenfassung" in resp.text

    # 9. Zusammenfassung anzeigen
    resp = client.get("/auftrag/proj-wiz-test/wizard/zusammenfassung")
    assert resp.status_code == 200
    assert "Zusammenfassung - Interaktive Erfassung" in resp.text
    assert "Fortinet" in resp.text
    assert "Catalyst 9200" in resp.text

    # 10. Wizard abschließen und Bausteine anlegen
    resp = client.post("/auftrag/proj-wiz-test/wizard/abschliessen", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/auftrag/proj-wiz-test/erfassung"

    # Fortschritt muss gelöscht sein
    assert storage.load_wizard_progress("proj-wiz-test") is None

    # Auftrag prüfen
    saved_auftrag = storage.load_auftrag("proj-wiz-test")
    assert saved_auftrag.kunde == "Wizard Kunde Aktualisiert"
    assert saved_auftrag.projekt_nummer == "P-WIZ-99"
    assert "firewall" in saved_auftrag.aktive_bausteine
    assert "switch" in saved_auftrag.aktive_bausteine
    assert "backup" in saved_auftrag.aktive_bausteine

    # Standorte prüfen
    standorte = storage.list_standorte("proj-wiz-test")
    assert len(standorte) == 1
    assert standorte[0].bezeichnung == "Hauptstandort Berlin"
    assert standorte[0].anzahl_user == 25
    assert len(standorte[0].anbindungen) == 1
    assert standorte[0].anbindungen[0].anbieter == "Telekom"
    assert standorte[0].anbindungen[0].bandbreite_down_mbit == 1000.0

    # Technik-Objekte prüfen
    objekte = storage.list_objekte("proj-wiz-test")
    typen = [o.typ for o in objekte]
    assert "firewall" in typen
    assert "switch" in typen
    assert "backup" in typen

    fw = next(o for o in objekte if o.typ == "firewall")
    assert fw.daten["hersteller"] == "Fortinet"
    assert fw.daten["modell"] == "FortiGate 60F"
    assert fw.daten["hardware_alter"] == "2"

    sw = next(o for o in objekte if o.typ == "switch")
    assert sw.daten["hersteller"] == "Cisco"
    assert sw.daten["port_anzahl"] == 48
    assert sw.daten["switch_typ"] == "fully_managed"

    bk = next(o for o in objekte if o.typ == "backup")
    assert bk.daten["backup_software"] == "veeam"
    assert bk.daten["backup_ziel"] == "NAS"


def test_wizard_skip_and_abbruch(client, tmp_path):
    auftrag = Auftrag(
        id="proj-skip-test",
        kunde="Skip Kunde",
        bezeichnung="Test Skip",
        aktive_bausteine=[]
    )
    storage.save_auftrag(auftrag)

    # Init
    client.post("/auftrag/proj-skip-test/wizard/init", follow_redirects=True)

    # Step 1 überspringen
    client.post("/auftrag/proj-skip-test/wizard/skip", follow_redirects=True)
    prog = storage.load_wizard_progress("proj-skip-test")
    assert prog.current_step == 2

    # Abbruch aufrufen (Fortschritt bleibt erhalten)
    resp = client.post("/auftrag/proj-skip-test/wizard/abbruch", follow_redirects=False)
    assert resp.status_code == 303
    assert storage.load_wizard_progress("proj-skip-test") is not None
