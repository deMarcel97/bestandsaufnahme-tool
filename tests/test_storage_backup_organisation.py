import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.schema_loader import schema_loader, SchemaLoader
from app.services.rule_engine import rule_engine, RuleEngine
from app.services.evaluator import evaluator_service
from app.services.report_builder import report_builder
from app.services.exporter import exporter_service
from app.services.storage import storage
from app.models.auftrag import Auftrag
from app.models.standort import Standort
from app.models.technik import TechnikObjekt

client = TestClient(app)

def test_schemas_loaded_successfully():
    """Verify that storage, backup, and organisation_prozesse schemas load correctly."""
    loader = SchemaLoader()
    all_types = loader.get_all_types()
    
    assert "storage" in all_types
    assert "backup" in all_types
    assert "organisation_prozesse" in all_types
    assert "backup_storage" in all_types  # Backward compatibility

    # Check storage schema properties
    schema_storage = loader.get_schema("storage")
    assert schema_storage["typ"] == "storage"
    assert schema_storage["bezeichnung_anzeige"] == "Storage & Speicher-Systeme"
    assert schema_storage["berichtskapitel"] == "infrastruktur"
    assert schema_storage.get("standortbezug") is True or schema_storage.get("standortbezug") is None

    # Check backup schema properties
    schema_backup = loader.get_schema("backup")
    assert schema_backup["typ"] == "backup"
    assert schema_backup["bezeichnung_anzeige"] == "Backup & Recovery"
    assert schema_backup["berichtskapitel"] == "infrastruktur"
    assert schema_backup.get("standortbezug") is True or schema_backup.get("standortbezug") is None
    
    # Check mehrfachauswahl in backup schema
    sec_backup = schema_backup["abschnitte"][0]
    sicherungsumfang_field = next((f for f in sec_backup["felder"] if f["name"] == "sicherungsumfang"), None)
    assert sicherungsumfang_field is not None
    assert sicherungsumfang_field["typ"] == "mehrfachauswahl"
    assert len(sicherungsumfang_field["werte"]) >= 5

    # Check organisation_prozesse schema properties
    schema_org = loader.get_schema("organisation_prozesse")
    assert schema_org["typ"] == "organisation_prozesse"
    assert schema_org["bezeichnung_anzeige"] == "Organisation & Prozesse"
    assert schema_org["berichtskapitel"] == "organisation"
    assert schema_org.get("standortbezug") is False

def test_storage_rules_evaluation():
    """Test that storage rules trigger appropriate findings."""
    re = RuleEngine()
    sto = Standort(id="sto-1", auftrag_id="auf-test-sto", bezeichnung="Zentrale", anbindungen=[])
    
    bad_storage = TechnikObjekt(
        id="sto-obj-1",
        typ="storage",
        bezeichnung="Haupt-Storage",
        auftrag_id="auf-test-sto",
        standort_id="sto-1",
        daten={
            "bereitstellung": "shared_storage",
            "hersteller_shared": "synology",
            "protokoll_anbindung": "iscsi",
            "controller_redundanz": "single_controller",
            "technologie_local": "software_raid",
            "medientyp": "hdd_only",
            "kapazitaet_brutto_tb": 24.0,
            "kapazitaet_netto_tb": 16.0,
            "fuellgrad_prozent": "ueber_85",
            "wartungsvertrag_status": "abgelaufen_eol"
        }
    )

    findings, open_pts = re.evaluate_all("auf-test-sto", [sto], [bad_storage], [])
    active_findings = [f for f in findings if f.status == "offen" and f.objekt_id == "sto-obj-1"]
    active_ids = {f.quelle for f in active_findings}

    assert "sto-fuellgrad-kritisch" in active_ids
    assert "sto-single-controller" in active_ids
    assert "sto-wartungsvertrag-eol" in active_ids
    assert "sto-hdd-only" in active_ids

def test_backup_rules_evaluation():
    """Test that backup rules trigger appropriate findings."""
    re = RuleEngine()
    sto = Standort(id="sto-1", auftrag_id="auf-test-bak", bezeichnung="Zentrale", anbindungen=[])
    
    bad_backup = TechnikObjekt(
        id="bak-obj-1",
        typ="backup",
        bezeichnung="Veeam Backup",
        auftrag_id="auf-test-bak",
        standort_id="sto-1",
        daten={
            "backup_software": "veeam",
            "sicherungsumfang": ["vollstaendige_vms", "fileserver"],
            "primaeres_ziel": "lokales_nas",
            "sekundaeres_ziel_offsite": "kein_offsite",
            "unveraenderbarkeit_immutability": "nicht_vorhanden",
            "rpo_haeufigkeit": "woechentlich_oder_seltener",
            "rto_wiederanlaufzeit": "mehrere_tage",
            "wiederherstellungstest_status": "noch_nie_getestet",
            "monitoring_alerting": "keine_ueberwachung"
        }
    )

    findings, open_pts = re.evaluate_all("auf-test-bak", [sto], [bad_backup], [])
    active_findings = [f for f in findings if f.status == "offen" and f.objekt_id == "bak-obj-1"]
    active_ids = {f.quelle for f in active_findings}

    assert "bak-kein-offsite" in active_ids
    assert "bak-kein-immutability" in active_ids
    assert "bak-restore-nie-getestet" in active_ids
    assert "bak-keine-ueberwachung" in active_ids
    assert "bak-rpo-unzureichend" in active_ids
    assert "bak-rto-kritisch" in active_ids

def test_organisation_prozesse_rules_evaluation():
    """Test that organisation_prozesse rules trigger appropriate findings."""
    re = RuleEngine()
    
    bad_org = TechnikObjekt(
        id="org-obj-1",
        typ="organisation_prozesse",
        bezeichnung="Organisation & Prozesse",
        auftrag_id="auf-test-org",
        standort_id=None,
        daten={
            "notfallhandbuch_status": "nicht_vorhanden",
            "wiederanlaufplan_dokumentiert": "nein",
            "it_dokumentation_status": "nicht_vorhanden",
            "it_sicherheitsrichtlinie_unterschrieben": "nein",
            "passwort_policy_mfa": "keine_vorgaben",
            "passwort_manager_einsatz": "kein_manager_im_browser",
            "byod_policy": "geduldet_ohne_regeln",
            "gaeste_wlan_trennung": "geteiltes_netz_mit_passwort",
            "mitarbeiter_awareness_schulungen": "keine_schulungen",
            "zutrittskontrolle_serverraum": "offen_zugaenglich",
            "offboarding_prozess": "kein_prozess",
            "av_vertraege_dsgvo": "nicht_geprueft"
        }
    )

    findings, open_pts = re.evaluate_all("auf-test-org", [], [bad_org], [])
    active_findings = [f for f in findings if f.status == "offen" and f.objekt_id == "org-obj-1"]
    active_ids = {f.quelle for f in active_findings}

    assert "org-kein-notfallhandbuch" in active_ids
    assert "org-kein-wiederanlaufplan" in active_ids
    assert "org-it-doku-fehlt" in active_ids
    assert "org-keine-sicherheitsrichtlinie" in active_ids
    assert "org-passwort-policy-keine" in active_ids
    assert "org-kein-passwort-manager" in active_ids
    assert "org-byod-ungeregelt" in active_ids
    assert "org-gaeste-wlan-ungesichert" in active_ids
    assert "org-keine-awareness" in active_ids
    assert "org-serverraum-zutritt-offen" in active_ids
    assert "org-kein-offboarding" in active_ids
    assert "org-av-vertraege-fehlen" in active_ids

def test_evaluator_with_new_modules():
    """Verify evaluator calculates scores correctly for storage, backup, and organisation_prozesse."""
    aktive = ["storage", "backup", "organisation_prozesse"]
    
    sto_obj = TechnikObjekt(
        id="sto-1",
        typ="storage",
        bezeichnung="SAN",
        auftrag_id="auf-eval",
        standort_id="loc-1",
        daten={
            "controller_redundanz": "dual_active_active",
            "medientyp": "all_flash_nvme",
            "fuellgrad_prozent": "unter_70",
            "wartungsvertrag_status": "aktiv_24_7"
        }
    )
    
    bak_obj = TechnikObjekt(
        id="bak-1",
        typ="backup",
        bezeichnung="Backup Server",
        auftrag_id="auf-eval",
        standort_id="loc-1",
        daten={
            "sekundaeres_ziel_offsite": "s3_object_storage",
            "unveraenderbarkeit_immutability": "vollstaendig_aktiv",
            "rpo_haeufigkeit": "stundengenau_oder_oefter",
            "rto_wiederanlaufzeit": "unter_4_stunden",
            "wiederherstellungstest_status": "regelmaessig_quartal_monat",
            "monitoring_alerting": "automatisiertes_ticket_monitoring"
        }
    )

    org_obj = TechnikObjekt(
        id="org-1",
        typ="organisation_prozesse",
        bezeichnung="Unternehmensorganisation",
        auftrag_id="auf-eval",
        standort_id=None,
        daten={
            "notfallhandbuch_status": "vorhanden_aktuell_getestet",
            "wiederanlaufplan_dokumentiert": "ja_vollstaendig",
            "it_dokumentation_status": "vollstaendig_aktuell",
            "it_sicherheitsrichtlinie_unterschrieben": "ja_alle_mitarbeiter",
            "passwort_policy_mfa": "mfa_pflicht_und_strenge_policy",
            "passwort_manager_einsatz": "unternehmensweit_zentral",
            "byod_policy": "klare_regelung_mit_mdm",
            "gaeste_wlan_trennung": "vollstaendig_isoliertes_vlan_portal",
            "mitarbeiter_awareness_schulungen": "regelmaessig_mit_phishing_tests",
            "zutrittskontrolle_serverraum": "protokolliert_elektronisch_transponder",
            "offboarding_prozess": "standardisierter_prozess_mit_checkliste",
            "av_vertraege_dsgvo": "vollstaendig_vorhanden"
        }
    )

    standorte = [Standort(id="loc-1", auftrag_id="auf-eval", bezeichnung="HQ", anbindungen=[])]
    bewertung = evaluator_service.evaluate_auftrag(aktive, [sto_obj, bak_obj, org_obj], standorte)

    assert bewertung.gesamt_prozent >= 95.0
    assert bewertung.bausteinabdeckung_prozent == 100.0
    assert len(bewertung.kategorien) > 0

def test_report_builder_and_exports():
    """Verify report building and docx export work with storage, backup, and organisation_prozesse."""
    auftrag = Auftrag(
        id="auf-rep-test",
        projekt_nummer="PROJ-323",
        kunde="Musterkunde GmbH",
        bezeichnung="Testprojekt Storage Backup Org",
        aktive_bausteine=["storage", "backup", "organisation_prozesse"]
    )
    storage.save_auftrag(auftrag)
    
    standort = Standort(id="sto-rep", auftrag_id=auftrag.id, bezeichnung="Hauptsitz", ort="Berlin", anbindungen=[])
    storage.save_standort(standort)

    sto_obj = TechnikObjekt(
        id="sto-rep-1",
        typ="storage",
        bezeichnung="All-Flash NVMe SAN",
        auftrag_id=auftrag.id,
        standort_id=standort.id,
        daten={
            "bereitstellung": "shared_storage",
            "hersteller_shared": "netapp",
            "controller_redundanz": "dual_active_active",
            "medientyp": "all_flash_nvme",
            "kapazitaet_brutto_tb": 50.0,
            "kapazitaet_netto_tb": 35.0,
            "fuellgrad_prozent": "unter_70",
            "wartungsvertrag_status": "aktiv_24_7"
        }
    )
    storage.save_objekt(sto_obj)

    bak_obj = TechnikObjekt(
        id="bak-rep-1",
        typ="backup",
        bezeichnung="Veeam Cloud Backup",
        auftrag_id=auftrag.id,
        standort_id=standort.id,
        daten={
            "backup_software": "veeam",
            "sicherungsumfang": ["vollstaendige_vms", "fileserver", "datenbanken_sql_exchange"],
            "primaeres_ziel": "lokales_nas",
            "sekundaeres_ziel_offsite": "s3_object_storage",
            "unveraenderbarkeit_immutability": "vollstaendig_aktiv",
            "rpo_haeufigkeit": "stundengenau_oder_oefter",
            "rto_wiederanlaufzeit": "unter_4_stunden",
            "wiederherstellungstest_status": "regelmaessig_quartal_monat",
            "monitoring_alerting": "automatisiertes_ticket_monitoring"
        }
    )
    storage.save_objekt(bak_obj)

    org_obj = TechnikObjekt(
        id="org-rep-1",
        typ="organisation_prozesse",
        bezeichnung="IT-Organisation & Prozesse",
        auftrag_id=auftrag.id,
        standort_id=None,
        daten={
            "notfallhandbuch_status": "vorhanden_aktuell_getestet",
            "wiederanlaufplan_dokumentiert": "ja_vollstaendig",
            "it_dokumentation_status": "vollstaendig_aktuell",
            "it_sicherheitsrichtlinie_unterschrieben": "ja_alle_mitarbeiter",
            "passwort_policy_mfa": "mfa_pflicht_und_strenge_policy",
            "passwort_manager_einsatz": "unternehmensweit_zentral",
            "byod_policy": "klare_regelung_mit_mdm",
            "gaeste_wlan_trennung": "vollstaendig_isoliertes_vlan_portal",
            "mitarbeiter_awareness_schulungen": "regelmaessig_mit_phishing_tests",
            "zutrittskontrolle_serverraum": "protokolliert_elektronisch_transponder",
            "offboarding_prozess": "standardisierter_prozess_mit_checkliste",
            "av_vertraege_dsgvo": "vollstaendig_vorhanden"
        }
    )
    storage.save_objekt(org_obj)

    try:
        objekte = [sto_obj, bak_obj, org_obj]
        bewertung = evaluator_service.evaluate_auftrag(auftrag.aktive_bausteine, objekte, [standort])
        
        md_text = report_builder.build_analysebericht(
            auftrag, [standort], objekte, [], bewertung, [], ziel_vertraulichkeit="intern"
        )
        
        assert "All-Flash NVMe SAN" in md_text
        assert "Storage & Speicher-Systeme" in md_text
        assert "Veeam Cloud Backup" in md_text
        assert "Backup & Recovery" in md_text
        assert "IT-Organisation & Prozesse" in md_text
        assert "Organisation & Prozesse" in md_text
        assert "Standortübergreifende Infrastruktur & Cloud-Dienste" in md_text

        # Test docx export
        docx_stream = exporter_service.export_analysebericht_docx(
            auftrag, [standort], objekte, [], "intern", []
        )
        assert docx_stream.getbuffer().nbytes > 1000
    finally:
        storage.delete_auftrag(auftrag.id)

def test_web_routes_and_forms():
    """Verify web form rendering and CRUD for storage, backup, and organisation_prozesse."""
    auftrag = Auftrag(
        id="auf-web-test",
        projekt_nummer="PROJ-WEB-323",
        kunde="Web Testkunde",
        bezeichnung="Web Formulare Test",
        aktive_bausteine=["storage", "backup", "organisation_prozesse"]
    )
    storage.save_auftrag(auftrag)
    standort = Standort(id="sto-web", auftrag_id=auftrag.id, bezeichnung="Web HQ", ort="Hamburg", anbindungen=[])
    storage.save_standort(standort)

    try:
        # 1. GET new form for storage
        resp = client.get(f"/auftrag/{auftrag.id}/objekt/neu?typ=storage&standort_id={standort.id}")
        assert resp.status_code == 200
        assert "Storage &amp; Speicher-Systeme" in resp.text or "Storage & Speicher-Systeme" in resp.text
        assert "Bereitstellungsart" in resp.text

        # 2. POST new storage object
        resp_post = client.post(
            f"/auftrag/{auftrag.id}/objekt/neu?typ=storage",
            data={
                "bezeichnung": "Produktiv SAN",
                "standort_id": standort.id,
                "betreut_durch": "wir",
                "vertraulichkeit": "intern",
                "bereitstellung": "shared_storage",
                "hersteller_shared": "dell_powervault_powerstore_unity",
                "protokoll_anbindung": "iscsi",
                "controller_redundanz": "dual_active_active",
                "medientyp": "all_flash_ssd",
                "kapazitaet_brutto_tb": "32",
                "kapazitaet_netto_tb": "24",
                "fuellgrad_prozent": "unter_70",
                "wartungsvertrag_status": "aktiv_24_7"
            },
            follow_redirects=False
        )
        assert resp_post.status_code == 303

        # 3. GET new form for backup (with mehrfachauswahl)
        resp = client.get(f"/auftrag/{auftrag.id}/objekt/neu?typ=backup&standort_id={standort.id}")
        assert resp.status_code == 200
        assert "Backup &amp; Recovery" in resp.text or "Backup & Recovery" in resp.text
        assert "Sicherungsumfang" in resp.text

        # 4. POST new backup object with multi-select checkboxes
        resp_post_bak = client.post(
            f"/auftrag/{auftrag.id}/objekt/neu?typ=backup",
            data={
                "bezeichnung": "Zentrales Veeam Backup",
                "standort_id": standort.id,
                "betreut_durch": "wir",
                "vertraulichkeit": "intern",
                "backup_software": "veeam",
                "sicherungsumfang": ["vollstaendige_vms", "fileserver", "datenbanken_sql_exchange"],
                "primaeres_ziel": "lokales_nas",
                "sekundaeres_ziel_offsite": "s3_object_storage",
                "unveraenderbarkeit_immutability": "vollstaendig_aktiv",
                "rpo_haeufigkeit": "stundengenau_oder_oefter",
                "rto_wiederanlaufzeit": "unter_4_stunden",
                "wiederherstellungstest_status": "regelmaessig_quartal_monat",
                "monitoring_alerting": "automatisiertes_ticket_monitoring"
            },
            follow_redirects=False
        )
        assert resp_post_bak.status_code == 303

        # 5. GET new form for organisation_prozesse (cloud / standortbezug: false)
        resp = client.get(f"/auftrag/{auftrag.id}/objekt/neu?typ=organisation_prozesse")
        assert resp.status_code == 200
        assert "Organisation &amp; Prozesse" in resp.text or "Organisation & Prozesse" in resp.text
        assert "Standortübergreifend (Cloud)" in resp.text

        # 6. POST new organisation_prozesse object
        resp_post_org = client.post(
            f"/auftrag/{auftrag.id}/objekt/neu?typ=organisation_prozesse",
            data={
                "bezeichnung": "IT-Prozesse 2026",
                "betreut_durch": "wir",
                "vertraulichkeit": "intern",
                "notfallhandbuch_status": "vorhanden_aktuell_getestet",
                "wiederanlaufplan_dokumentiert": "ja_vollstaendig",
                "it_dokumentation_status": "vollstaendig_aktuell",
                "it_sicherheitsrichtlinie_unterschrieben": "ja_alle_mitarbeiter",
                "passwort_policy_mfa": "mfa_pflicht_und_strenge_policy",
                "passwort_manager_einsatz": "unternehmensweit_zentral",
                "byod_policy": "klare_regelung_mit_mdm",
                "gaeste_wlan_trennung": "vollstaendig_isoliertes_vlan_portal",
                "mitarbeiter_awareness_schulungen": "regelmaessig_mit_phishing_tests",
                "zutrittskontrolle_serverraum": "protokolliert_elektronisch_transponder",
                "offboarding_prozess": "standardisierter_prozess_mit_checkliste",
                "av_vertraege_dsgvo": "vollstaendig_vorhanden"
            },
            follow_redirects=False
        )
        assert resp_post_org.status_code == 303

        # Check saved objects in storage
        loaded_objekte = storage.list_objekte(auftrag.id)
        assert len(loaded_objekte) == 3

        bak_saved = next((o for o in loaded_objekte if o.typ == "backup"), None)
        assert bak_saved is not None
        assert isinstance(bak_saved.daten.get("sicherungsumfang"), list)
        assert "vollstaendige_vms" in bak_saved.daten.get("sicherungsumfang")
        assert "fileserver" in bak_saved.daten.get("sicherungsumfang")

        org_saved = next((o for o in loaded_objekte if o.typ == "organisation_prozesse"), None)
        assert org_saved is not None
        assert org_saved.standort_id is None
    finally:
        storage.delete_auftrag(auftrag.id)
