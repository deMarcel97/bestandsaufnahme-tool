"""
Tests for v2.6.0 Backlog Features (Cards #281, #283, #284, #286, #287, #295, #296, #297, #298, #299)
"""
from fastapi.testclient import TestClient
from app.main import app
from app.services.schema_loader import SchemaLoader
from app.models.auftrag import Unternehmenskontext

client = TestClient(app)


def test_schema_kommentar_fields_at_end_of_last_section():
    """Card #299: Verifies that kommentar is at the end of the last section in all schemas."""
    loader = SchemaLoader()
    for typ in loader.get_all_types():
        schema = loader.get_schema(typ)
        abschnitte = schema.get("abschnitte", [])
        assert len(abschnitte) > 0, f"Schema {typ} has no abschnitte"
        last_abschnitt = abschnitte[-1]
        felder = last_abschnitt.get("felder", [])
        assert len(felder) > 0, f"Schema {typ} has no felder in last abschnitt"
        last_field = felder[-1]
        assert last_field.get("name") == "kommentar", f"Schema {typ} does not have 'kommentar' as last field in last section"


def test_server_virtualisierung_fields_and_mandatory_wird_virtualisiert():
    """Card #296, #297, #298: Verifies server_virtualisierung fields."""
    loader = SchemaLoader()
    schema = loader.get_schema("server_virtualisierung")
    
    # #297: wird_virtualisiert is pflicht: true at the top
    first_field = schema["abschnitte"][0]["felder"][0]
    assert first_field["name"] == "wird_virtualisiert"
    assert first_field.get("pflicht") is True
    
    # #296: standort_rack and baujahr exist in hardware section
    hardware_fields = {f["name"]: f for f in schema["abschnitte"][1]["felder"]}
    assert "standort_rack" in hardware_fields
    assert "baujahr" in hardware_fields
    
    # #298: festplatten_slots has m2 option
    fp_field = hardware_fields["festplatten_slots"]
    anbindung_subfield = next(f for f in fp_field["felder"] if f["name"] == "anbindung")
    anbindung_werte = [w["wert"] for w in anbindung_subfield["werte"]]
    assert "m2" in anbindung_werte


def test_backup_storage_festplatten_slots():
    """Card #298: Verifies festplatten_slots in backup_storage."""
    loader = SchemaLoader()
    schema = loader.get_schema("backup_storage")
    first_section_fields = {f["name"]: f for f in schema["abschnitte"][0]["felder"]}
    assert "festplatten_slots" in first_section_fields
    fp_field = first_section_fields["festplatten_slots"]
    anbindung_subfield = next(f for f in fp_field["felder"] if f["name"] == "anbindung")
    anbindung_werte = [w["wert"] for w in anbindung_subfield["werte"]]
    assert "m2" in anbindung_werte


def test_unternehmenskontext_empfehlungen():
    """Card #284: Verifies empfehlung properties on Unternehmenskontext."""
    kontext_ohne_it = Unternehmenskontext(
        it_abteilung_vorhanden="nein",
        geschaeftszeiten_tage="24/7"
    )
    assert kontext_ohne_it.empfehlung_it_dienstleister is True
    assert kontext_ohne_it.empfehlung_rufbereitschaft is True
    
    kontext_mit_it = Unternehmenskontext(
        it_abteilung_vorhanden="ja",
        geschaeftszeiten_tage="Montag bis Freitag"
    )
    assert kontext_mit_it.empfehlung_it_dienstleister is False
    assert kontext_mit_it.empfehlung_rufbereitschaft is False
