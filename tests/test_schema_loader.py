import pytest
from pathlib import Path
from app.services.schema_loader import SchemaLoader, SchemaValidationError

def test_load_firewall_schema():
    loader = SchemaLoader()
    fw_schema = loader.get_schema("firewall")
    assert fw_schema is not None
    assert fw_schema["typ"] == "firewall"
    assert fw_schema["berichtskapitel"] == "netzwerk_und_internet"

def test_extensiveness_dummy_schema(tmp_path):
    # Test that a new schema file adds a new object type without code changes
    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir()
    bew_dir = tmp_path / "bewertung"
    bew_dir.mkdir()

    dummy_yaml = schemas_dir / "usv.yaml"
    dummy_yaml.write_text("""
schema_version: 1
typ: usv
bezeichnung_anzeige: USV Notstrom
berichtskapitel: infrastruktur
abschnitte:
  - id: was_ist_es
    titel: Was ist es
    felder:
      - name: hersteller
        typ: auswahl
        pflicht: true
        werte:
          - wert: APC
            textbaustein: "Eine USV des Herstellers APC sichert die Stromversorgung."
""", encoding="utf-8")

    loader = SchemaLoader(schemas_dir=schemas_dir, bewertung_dir=bew_dir)
    assert "usv" in loader.get_all_types()
    usv_schema = loader.get_schema("usv")
    assert usv_schema["bezeichnung_anzeige"] == "USV Notstrom"

def test_sichtbar_wenn_loads_on_real_schemas():
    loader = SchemaLoader()

    ap_schema = loader.get_schema("access_point")
    felder = {f["name"]: f for a in ap_schema["abschnitte"] for f in a["felder"]}
    assert felder["gast_wlan_isoliert"]["sichtbar_wenn"] == {
        "feld": "gast_wlan_vorhanden", "operator": "gleich", "wert": "ja"
    }

    nws_schema = loader.get_schema("netzwerkschrank")
    felder = {f["name"]: f for a in nws_schema["abschnitte"] for f in a["felder"]}
    assert felder["patchpanel_beschriftung"]["sichtbar_wenn"] == {
        "feld": "patchpanel_vorhanden", "operator": "gleich", "wert": "ja"
    }

def test_invalid_field_type_raises(tmp_path):
    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir()
    bew_dir = tmp_path / "bewertung"
    bew_dir.mkdir()

    bad_yaml = schemas_dir / "bad.yaml"
    bad_yaml.write_text("""
schema_version: 1
typ: bad
abschnitte:
  - id: a1
    felder:
      - name: f1
        typ: unkown_custom_type
""", encoding="utf-8")

    with pytest.raises(SchemaValidationError):
        SchemaLoader(schemas_dir=schemas_dir, bewertung_dir=bew_dir)
