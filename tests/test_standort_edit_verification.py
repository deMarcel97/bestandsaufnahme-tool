"""
Verification Script for Standort Edit Form and YAML Persistence.
"""
import os
import yaml
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.services.storage import storage

client = TestClient(app)

def run_standort_edit_test():
    print("--- Starting Standort Edit Verification Test ---")
    
    # 1. Create a test order
    auftrag_data = {
        "projekt_nummer": "PRJ-STANDORT-TEST",
        "kunde": "Testfirma GmbH",
        "bezeichnung": "Standort Test Projekt",
        "grundlage": "Angebot",
        "vertraulichkeit_default": "kundentauglich",
        "aktive_bausteine": ["firewall", "usv"]
    }
    resp = client.post("/auftrag/neu", data=auftrag_data, follow_redirects=True)
    assert resp.status_code == 200, f"Failed to create order: {resp.status_code}"
    auftrag_id = "auf-standort-test-projekt"
    print(f"1. Test order created: {auftrag_id} (HTTP {resp.status_code})")

    # 2. Create initial Standort
    initial_standort_data = {
        "bezeichnung": "Initialer Standort",
        "strasse": "Altstraße 1",
        "plz": "10115",
        "ort": "Berlin",
        "anzahl_user": 15,
        "funktion": "Zweigstelle",
        "ansprechpartner_vor_ort": "Initial Person",
        "redaktionskonzept_backup_leitung": "automatische_umschaltung",
        "trassenfuehrung_getrennt": "ja",
        "usv_fuer_netzwerktechnik": "ja",
        "anbieter_0": "Telekom",
        "art_0": "DSL",
        "bandbreite_down_mbit_0": 50,
        "bandbreite_up_mbit_0": 10,
        "ist_backup_leitung_0": "nein"
    }
    resp = client.post(f"/auftrag/{auftrag_id}/standort/neu", data=initial_standort_data, follow_redirects=True)
    assert resp.status_code == 200, f"Failed to create standort: {resp.status_code}"
    standort_id = "sto-initialer-standort"
    print(f"2. Initial standort created: {standort_id} (HTTP {resp.status_code})")

    # 3. Test GET request for Standort Edit Form
    resp_get = client.get(f"/auftrag/{auftrag_id}/standort/{standort_id}/bearbeiten")
    assert resp_get.status_code == 200, f"GET edit form failed: {resp_get.status_code}"
    assert "Standort bearbeiten" in resp_get.text
    print("3. GET edit form successful (HTTP 200)")

    # 4. Perform POST edit request with all fields requested by user requirement:
    # - Bezeichnung
    # - Straße
    # - PLZ
    # - Ort
    # - Ansprechpartner vor Ort
    # - Redundanzkonzept (redaktionskonzept_backup_leitung)
    # - Trassenführung (trassenfuehrung_getrennt)
    # - USV-Absicherung (usv_fuer_netzwerktechnik)
    # - Internetanbindungen (anbindungen: primary + secondary backup)
    edit_standort_data = {
        "bezeichnung": "Hauptstandort Bayern Nord",
        "strasse": "Industriestraße 42",
        "plz": "80331",
        "ort": "München",
        "anzahl_user": 120,
        "funktion": "Hauptverwaltung & Rechenzentrum",
        "ansprechpartner_vor_ort": "Hans Huber (IT-Leiter)",
        "begehung_am": "2026-08-15",
        "redaktionskonzept_backup_leitung": "manuelle_umschaltung",
        "trassenfuehrung_getrennt": "nein",
        "usv_fuer_netzwerktechnik": "nein",
        
        # Primary Line (Index 0)
        "anbieter_0": "Deutsche Telekom",
        "art_0": "Glasfaser_FTTH",
        "bandbreite_down_mbit_0": 1000,
        "bandbreite_up_mbit_0": 500,
        "symmetrisch_0": "nein",
        "feste_ip_0": "ja",
        "ist_backup_leitung_0": "nein",
        "failover_verfahren_0": "Primary BGP",
        "ip_adressen_0": "198.51.100.10",
        "subnetzmaske_0": "/30",
        
        # Secondary Backup Line (Index 1)
        "anbieter_1": "Vodafone Business",
        "art_1": "Kabel",
        "bandbreite_down_mbit_1": 500,
        "bandbreite_up_mbit_1": 50,
        "symmetrisch_1": "nein",
        "feste_ip_1": "nein",
        "ist_backup_leitung_1": "ja",
        "failover_verfahren_1": "Statische Umschaltung",
        "ip_adressen_1": "",
        "subnetzmaske_1": ""
    }

    resp_post = client.post(
        f"/auftrag/{auftrag_id}/standort/{standort_id}/bearbeiten",
        data=edit_standort_data,
        follow_redirects=False
    )
    assert resp_post.status_code == 303, f"Expected 303 redirect on edit submit, got: {resp_post.status_code}"
    print(f"4. POST edit request returned HTTP 303 Redirect to: {resp_post.headers.get('location')}")

    # Follow redirect to order detail page
    resp_redirect = client.get(resp_post.headers.get('location'))
    assert resp_redirect.status_code == 200, f"Failed following redirect: {resp_redirect.status_code}"
    assert "Hauptstandort Bayern Nord" in resp_redirect.text
    print("5. Followed redirect to order detail page successfully (HTTP 200)")

    # 5. Direct verification of storage loaded object
    sto = storage.load_standort(auftrag_id, standort_id)
    assert sto is not None, "Failed to load standort from storage!"
    
    assert sto.bezeichnung == "Hauptstandort Bayern Nord"
    assert sto.strasse == "Industriestraße 42"
    assert sto.plz == "80331"
    assert sto.ort == "München"
    assert sto.ansprechpartner_vor_ort == "Hans Huber (IT-Leiter)"
    assert sto.redaktionskonzept_backup_leitung == "manuelle_umschaltung"
    assert sto.trassenfuehrung_getrennt == "nein"
    assert sto.usv_fuer_netzwerktechnik == "nein"
    assert len(sto.anbindungen) == 2

    # Verify connection 0
    anb0 = sto.anbindungen[0]
    assert anb0.anbieter == "Deutsche Telekom"
    assert anb0.art == "Glasfaser_FTTH"
    assert anb0.bandbreite_down_mbit == 1000.0
    assert anb0.bandbreite_up_mbit == 500.0
    assert anb0.feste_ip == "ja"
    assert anb0.ip_adressen == "198.51.100.10"
    assert anb0.subnetzmaske == "/30"
    assert anb0.ist_backup_leitung == "nein"

    # Verify connection 1
    anb1 = sto.anbindungen[1]
    assert anb1.anbieter == "Vodafone Business"
    assert anb1.art == "Kabel"
    assert anb1.bandbreite_down_mbit == 500.0
    assert anb1.bandbreite_up_mbit == 50.0
    assert anb1.ist_backup_leitung == "ja"
    assert anb1.failover_verfahren == "Statische Umschaltung"

    print("6. In-memory loaded Standort model validated successfully.")

    # 6. Direct YAML File Inspection on disk
    yaml_file_path = storage.get_auftrag_dir(auftrag_id) / "standorte" / f"{standort_id}.yaml"
    assert yaml_file_path.exists(), f"YAML file does not exist at {yaml_file_path}"
    
    with open(yaml_file_path, "r", encoding="utf-8") as f:
        yaml_content = yaml.safe_load(f)

    print("\n--- Raw YAML Content Saved on Disk ---")
    print(yaml.dump(yaml_content, allow_unicode=True))

    assert yaml_content["bezeichnung"] == "Hauptstandort Bayern Nord"
    assert yaml_content["strasse"] == "Industriestraße 42"
    assert yaml_content["plz"] == "80331"
    assert yaml_content["ort"] == "München"
    assert yaml_content["ansprechpartner_vor_ort"] == "Hans Huber (IT-Leiter)"
    assert yaml_content["redaktionskonzept_backup_leitung"] == "manuelle_umschaltung"
    assert yaml_content["trassenfuehrung_getrennt"] == "nein"
    assert yaml_content["usv_fuer_netzwerktechnik"] == "nein"
    assert isinstance(yaml_content["anbindungen"], list)
    assert len(yaml_content["anbindungen"]) == 2

    # Clean up test data
    storage.delete_auftrag(auftrag_id)
    print("7. Cleaned up test order and standort YAML.")
    print("--- ALL VERIFICATION CHECKS PASSED SUCCESSFULLY ---")

if __name__ == "__main__":
    run_standort_edit_test()
