import pytest
from app.services.schema_loader import schema_loader, SchemaLoader
from app.services.rule_engine import rule_engine, RuleEngine
from app.models.technik import TechnikObjekt
from app.models.standort import Standort

NEW_TYPES = [
    "server_virtualisierung",
    "switch",
    "access_point",
    "backup_storage",
    "usv",
    "serverraum",
    "netzwerkschrank",
    "clients",
    "m365_security",
    "software"
]

def test_all_new_schemas_loaded():
    loader = SchemaLoader()
    all_types = loader.get_all_types()
    for t in NEW_TYPES:
        assert t in all_types, f"Schema {t} was not loaded by SchemaLoader"
        schema = loader.get_schema(t)
        assert schema["typ"] == t
        assert "abschnitte" in schema
        assert len(schema["abschnitte"]) > 0

def test_all_new_rules_validated_and_loaded():
    re = RuleEngine()
    loaded_gilt_fuer = set(r.get("gilt_fuer") for r in re.rules)
    for t in NEW_TYPES:
        assert t in loaded_gilt_fuer, f"No rules found for type {t}"

def test_rule_evaluation_new_types():
    re = RuleEngine()
    sto = Standort(id="sto-test", auftrag_id="auf-test", bezeichnung="Test-Standort", anbindungen=[])

    # Test evaluating an object of each type with bad configuration (should trigger findings)
    bad_data = {
        "server_virtualisierung": {
            "hardware_alter": "ueber_5_jahre",
            "wartungsvertrag_vorhanden": "nein",
            "hypervisor_eol": "ja",
            "os_eol_vms_vorhanden": "ja",
            "patchstand_aktuell": "nein",
            "ha_cluster_eingerichtet": "nein",
            "redundante_netzteil_stromversorgung": "nein",
            "raid_konfiguration": "raid_0_oder_kein_raid",
            "monitoring_aktiv": "nein",
            "dokumentation_vorhanden": "keine"
        },
        "switch": {
            "management_typ": "unmanaged",
            "netztrennung": "nein",
            "firmware_aktuell": "nein",
            "garantie_bis": "2020-01-01",
            "wartungsvertrag_vorhanden": "nein",
            "konfigurationssicherung_aktuell": "nein",
            "zugangsschutz_management": "http_telnet",
            "port_security_aktiv": "nein",
            "loop_protection_aktiv": "nein"
        },
        "access_point": {
            "wlan_standard": "wifi4_oder_aelter",
            "management": "standalone",
            "gast_wlan_vorhanden": "ja",
            "gast_wlan_isoliert": "nein",
            "verschluesselung_wpa3": "nein",
            "firmware_aktuell": "nein",
            "garantie_bis": "2020-01-01",
            "wartungsvertrag_vorhanden": "nein"
        },
        "backup_storage": {
            "3_2_1_regel_erfuellt": "nein",
            "immutability_ransomware_schutz": "nein",
            "offsite_backup_vorhanden": "nein",
            "backup_verschluesselung": "nein",
            "regelmaessige_restore_tests": "nein",
            "hardware_alter_storage": "ueber_5_jahre",
            "backup_monitoring_und_alarming": "nein",
            "backup_konzept_dokumentiert": "keine"
        },
        "usv": {
            "batterie_alter": "ueber_5_jahre",
            "garantie_geraet_bis": "2020-01-01",
            "garantie_batterie_bis": "2020-01-01",
            "wartungsvertrag_vorhanden": "nein",
            "letzter_batterietest": "2020-01-01",
            "abschaltsignal_an_server": "nein",
            "auslastung_prozent": 85,
            "ueberbrueckungszeit_minuten": 3
        },
        "serverraum": {
            "zugangskontrolle": "frei_zugaenglich",
            "zutrittsprotokollierung": "nein",
            "zugangsberechtigte_dokumentiert": "nein",
            "umweltsensorik": "keine",
            "brandmeldeanlage": "nein",
            "loeschanlage": "keine",
            "stromeinspeisung": "eine_einspeisung",
            "notstromaggregat": "nein"
        },
        "netzwerkschrank": {
            "art": "offen_im_raum",
            "abschliessbar": "nein",
            "belueftung": "keine",
            "patchpanel_beschriftung": "keine",
            "verkabelungsdokumentation": "keine",
            "ausfuehrung_durch": "gewachsen_ohne_dokumentation",
            "kabeltyp": "cat5",
            "verkabelung_alter": "ueber_10_jahre",
            "erweiterungsreserve": "keine"
        },
        "clients": {
            "windows_10_eol_migration_geplant": "nein",
            "zentrales_patchmanagement_aktiv": "nein",
            "edr_antivirus_zentral_gemanagt": "nein",
            "festplattenverschluesselung_aktiv": "nein",
            "lokale_adminrechte_eingeschraenkt": "nein",
            "mdm_rmm_software_im_einsatz": "nein",
            "hardware_alter_durchschnitt": "ueber_5_jahre",
            "dokumentation_vorhanden": "keine"
        },
        "m365_security": {
            "mfa_fuer_administratoren": "nein",
            "mfa_fuer_alle_benutzer": "nein",
            "legacy_authentication_blockiert": "nein",
            "m365_drittanbieter_backup_aktiv": "nein",
            "conditional_access_regelwerke": "nein",
            "defender_for_office365_aktiv": "nein",
            "global_admin_anzahl_angemessen": "nein",
            "audit_logging_aktiv": "nein",
            "dokumentation_vorhanden": "keine"
        },
        "software": {
            "kategorie": "CRM",
            "wartungsvertrag_support_vorhanden": "nein",
            "datensicherung_vorhanden": "nein",
            "dokumentation_vorhanden": "keine"
        }
    }

    for t in NEW_TYPES:
        obj = TechnikObjekt(
            id=f"{t}-obj-1",
            typ=t,
            bezeichnung=f"Test {t}",
            auftrag_id="auf-test",
            standort_id="sto-test",
            daten=bad_data[t]
        )
        findings, open_pts = re.evaluate_all("auf-test", [sto], [obj], [])
        active_findings = [f for f in findings if f.status == "offen" and f.objekt_id == f"{t}-obj-1"]
        assert len(active_findings) > 0, f"Expected findings for {t}, got none"
