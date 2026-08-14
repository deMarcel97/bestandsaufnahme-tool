import copy
import pytest
from fastapi.testclient import TestClient
from app.services.schema_loader import SchemaLoader, SchemaValidationError, schema_loader
from app.services.storage import storage, StorageService
from app.models.technik import TechnikObjekt
from app.web.routes_objekt import _parse_liste_field, _collect_objekt_referenz_candidates
from app.services.evaluator import evaluator_service
from app.main import app


# --- schema_loader: 'liste' Feldtyp ---

def test_liste_feldtyp_laedt_korrekt(tmp_path):
    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir()
    bew_dir = tmp_path / "bewertung"
    bew_dir.mkdir()

    (schemas_dir / "server_virtualisierung.yaml").write_text("""
schema_version: 1
typ: server_virtualisierung
bezeichnung_anzeige: Server
berichtskapitel: infrastruktur
abschnitte:
  - id: hardware
    titel: Hardware
    felder:
      - name: festplatten_slots
        typ: liste
        label: Festplatten-Slots
        felder:
          - name: typ
            typ: auswahl
            werte:
              - wert: ssd
              - wert: hdd
          - name: kapazitaet_gb
            typ: zahl
""", encoding="utf-8")

    loader = SchemaLoader(schemas_dir=schemas_dir, bewertung_dir=bew_dir)
    schema = loader.get_schema("server_virtualisierung")
    liste_feld = schema["abschnitte"][0]["felder"][0]
    assert liste_feld["typ"] == "liste"
    assert len(liste_feld["felder"]) == 2


def test_liste_ohne_unterfelder_raises(tmp_path):
    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir()
    bew_dir = tmp_path / "bewertung"
    bew_dir.mkdir()

    (schemas_dir / "bad.yaml").write_text("""
schema_version: 1
typ: bad
abschnitte:
  - id: a1
    felder:
      - name: leere_liste
        typ: liste
""", encoding="utf-8")

    with pytest.raises(SchemaValidationError):
        SchemaLoader(schemas_dir=schemas_dir, bewertung_dir=bew_dir)


def test_liste_verschachtelung_verboten(tmp_path):
    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir()
    bew_dir = tmp_path / "bewertung"
    bew_dir.mkdir()

    (schemas_dir / "bad.yaml").write_text("""
schema_version: 1
typ: bad
abschnitte:
  - id: a1
    felder:
      - name: aussen
        typ: liste
        felder:
          - name: innen
            typ: liste
            felder:
              - name: x
                typ: text
""", encoding="utf-8")

    with pytest.raises(SchemaValidationError):
        SchemaLoader(schemas_dir=schemas_dir, bewertung_dir=bew_dir)


# --- schema_loader: 'objekt_referenz' Feldtyp ---

def test_objekt_referenz_laedt_korrekt(tmp_path):
    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir()
    bew_dir = tmp_path / "bewertung"
    bew_dir.mkdir()

    (schemas_dir / "server_cluster.yaml").write_text("""
schema_version: 1
typ: server_cluster
bezeichnung_anzeige: Cluster
berichtskapitel: infrastruktur
abschnitte:
  - id: a1
    titel: Cluster
    felder:
      - name: anzahl_knoten
        typ: zahl
""", encoding="utf-8")

    (schemas_dir / "vm.yaml").write_text("""
schema_version: 1
typ: vm
bezeichnung_anzeige: VM
berichtskapitel: infrastruktur
abschnitte:
  - id: a1
    titel: Host
    felder:
      - name: host_referenz
        typ: objekt_referenz
        ziel_typen: [server_cluster]
""", encoding="utf-8")

    loader = SchemaLoader(schemas_dir=schemas_dir, bewertung_dir=bew_dir)
    vm_schema = loader.get_schema("vm")
    ref_feld = vm_schema["abschnitte"][0]["felder"][0]
    assert ref_feld["ziel_typen"] == ["server_cluster"]


def test_objekt_referenz_ohne_ziel_typen_raises(tmp_path):
    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir()
    bew_dir = tmp_path / "bewertung"
    bew_dir.mkdir()

    (schemas_dir / "bad.yaml").write_text("""
schema_version: 1
typ: bad
abschnitte:
  - id: a1
    felder:
      - name: ref
        typ: objekt_referenz
""", encoding="utf-8")

    with pytest.raises(SchemaValidationError):
        SchemaLoader(schemas_dir=schemas_dir, bewertung_dir=bew_dir)


def test_objekt_referenz_unbekannter_zieltyp_raises(tmp_path):
    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir()
    bew_dir = tmp_path / "bewertung"
    bew_dir.mkdir()

    (schemas_dir / "bad.yaml").write_text("""
schema_version: 1
typ: bad
abschnitte:
  - id: a1
    felder:
      - name: ref
        typ: objekt_referenz
        ziel_typen: [nicht_existierender_typ]
""", encoding="utf-8")

    with pytest.raises(SchemaValidationError):
        SchemaLoader(schemas_dir=schemas_dir, bewertung_dir=bew_dir)


# --- routes_objekt: _parse_liste_field ---

def test_parse_liste_field_baut_zeilen_aus_form_data():
    feldef = {
        "name": "festplatten_slots",
        "typ": "liste",
        "felder": [
            {"name": "typ", "typ": "auswahl"},
            {"name": "kapazitaet_gb", "typ": "zahl"},
        ],
    }
    form_data = {
        "festplatten_slots_0_typ": "ssd",
        "festplatten_slots_0_kapazitaet_gb": "480",
        "festplatten_slots_1_typ": "hdd",
        "festplatten_slots_1_kapazitaet_gb": "4000",
        "andere_liste_0_typ": "sollte_ignoriert_werden",
    }
    rows = _parse_liste_field(form_data, feldef)
    assert rows == [
        {"typ": "ssd", "kapazitaet_gb": 480.0},
        {"typ": "hdd", "kapazitaet_gb": 4000.0},
    ]


def test_parse_liste_field_leere_zeile_wird_uebersprungen():
    feldef = {
        "name": "netzwerkkarten",
        "typ": "liste",
        "felder": [{"name": "geschwindigkeit", "typ": "text"}],
    }
    form_data = {"netzwerkkarten_0_geschwindigkeit": "   "}
    assert _parse_liste_field(form_data, feldef) == []


# --- storage: deepcopy bei duplicate_objekt ---

def test_duplicate_objekt_deepcopy_liste_feld(tmp_path):
    svc = StorageService(data_dir=tmp_path)
    obj = TechnikObjekt(
        id="srv-original",
        typ="server_virtualisierung",
        bezeichnung="Server Original",
        auftrag_id="auf-test",
        standort_id="sto-a",
        daten={"festplatten_slots": [{"typ": "ssd", "kapazitaet_gb": 480}]}
    )
    svc.save_objekt(obj)

    kopie = svc.duplicate_objekt("auf-test", "server_virtualisierung", "srv-original")
    kopie.daten["festplatten_slots"].append({"typ": "hdd", "kapazitaet_gb": 4000})

    original_reloaded = svc.load_objekt("auf-test", "server_virtualisierung", "srv-original")
    assert len(original_reloaded.daten["festplatten_slots"]) == 1


# --- storage: resolve_objekt_referenz ---

def test_resolve_objekt_referenz_findet_richtigen_typ(tmp_path):
    svc = StorageService(data_dir=tmp_path)
    cluster = TechnikObjekt(id="clu-nord", typ="server_cluster", bezeichnung="Cluster Nord", auftrag_id="auf-test", standort_id="sto-a")
    svc.save_objekt(cluster)

    resolved = svc.resolve_objekt_referenz("auf-test", "clu-nord", ["server_virtualisierung", "server_cluster"])
    assert resolved is not None
    assert resolved.typ == "server_cluster"


def test_resolve_objekt_referenz_geloescht_gibt_none(tmp_path):
    svc = StorageService(data_dir=tmp_path)
    assert svc.resolve_objekt_referenz("auf-test", "clu-geloescht", ["server_virtualisierung", "server_cluster"]) is None
    assert svc.resolve_objekt_referenz("auf-test", "", ["server_cluster"]) is None


# --- routes_objekt: _collect_objekt_referenz_candidates ---

def test_collect_objekt_referenz_candidates(tmp_path):
    old_dir = storage.data_dir
    storage.data_dir = tmp_path
    try:
        cluster = TechnikObjekt(id="clu-nord", typ="server_virtualisierung", bezeichnung="Server A", auftrag_id="auf-test", standort_id="sto-a")
        storage.save_objekt(cluster)

        schema = {
            "abschnitte": [{
                "felder": [{
                    "name": "host_referenz",
                    "typ": "objekt_referenz",
                    "ziel_typen": ["server_virtualisierung"],
                }]
            }]
        }
        candidates = _collect_objekt_referenz_candidates("auf-test", schema)
        assert "host_referenz" in candidates
        assert any(c["id"] == "clu-nord" for c in candidates["host_referenz"])
    finally:
        storage.data_dir = old_dir


# --- evaluator: Abschnitt-Level sichtbar_wenn ---

def test_calculate_objekt_status_versteckter_abschnitt_nicht_pflicht(monkeypatch):
    schema = {
        "abschnitte": [
            {
                "id": "immer",
                "felder": [{"name": "wird_virtualisiert", "typ": "ja_nein", "pflicht": True}],
            },
            {
                "id": "virtualisierung",
                "sichtbar_wenn": {"feld": "wird_virtualisiert", "operator": "gleich", "wert": "ja"},
                "felder": [{"name": "hypervisor_typ", "typ": "text", "pflicht": True}],
            },
        ]
    }
    monkeypatch.setattr("app.services.evaluator.schema_loader.get_schema", lambda typ: schema)

    obj = TechnikObjekt(
        id="srv-1", typ="server_virtualisierung", bezeichnung="Server 1",
        auftrag_id="auf-test", standort_id="sto-a",
        daten={"wird_virtualisiert": "nein"}
    )
    # hypervisor_typ ist Pflicht, aber der Abschnitt ist ausgeblendet -> darf Status nicht blockieren
    assert evaluator_service.calculate_objekt_status(obj) == "vollständig"

    obj.daten["wird_virtualisiert"] = "ja"
    # Jetzt ist der Abschnitt sichtbar, hypervisor_typ fehlt -> teilweise
    assert evaluator_service.calculate_objekt_status(obj) == "teilweise"


# --- form.html: Ende-zu-Ende-Rendering (Regression fuer den TemplateSyntaxError,
# den kein reiner Unit-Test der Python-Hilfsfunktionen erkannt hätte) ---

client = TestClient(app)

@pytest.fixture
def temp_storage(tmp_path):
    old_dir = storage.data_dir
    storage.data_dir = tmp_path
    yield
    storage.data_dir = old_dir

@pytest.fixture
def temp_test_schema():
    """Registriert vorübergehend ein Test-Schema mit 'liste' und 'objekt_referenz'
    Feldern im echten schema_loader-Singleton, damit form.html end-to-end (inkl.
    Jinja-Kompilierung) über diese neuen Feldtypen gerendert wird."""
    schema_loader.schemas["test_host"] = {
        "typ": "test_host", "bezeichnung_anzeige": "Test Host", "berichtskapitel": "infrastruktur",
        "abschnitte": [{"id": "a1", "titel": "Basis", "felder": [
            {"name": "hersteller", "typ": "text"},
        ]}]
    }
    schema_loader.schemas["test_vm"] = {
        "typ": "test_vm", "bezeichnung_anzeige": "Test VM", "berichtskapitel": "infrastruktur",
        "abschnitte": [{"id": "a1", "titel": "Konfiguration", "felder": [
            {"name": "host_referenz", "typ": "objekt_referenz", "ziel_typen": ["test_host"]},
            {"name": "festplatten_slots", "typ": "liste", "label": "Festplatten-Slots", "felder": [
                {"name": "typ", "typ": "auswahl", "werte": [{"wert": "ssd"}, {"wert": "hdd"}]},
                {"name": "kapazitaet_gb", "typ": "zahl"},
            ]},
        ]}]
    }
    yield
    del schema_loader.schemas["test_host"]
    del schema_loader.schemas["test_vm"]

@pytest.mark.parametrize("typ", list(schema_loader.get_all_types()))
def test_neu_formular_rendert_fuer_jeden_realen_objekttyp(temp_storage, typ):
    client.post("/auftrag/neu", data={
        "projekt_nummer": f"PROJ-FORM-{typ}", "kunde": "PoC", "bezeichnung": "Formular Test",
    }, follow_redirects=False)
    res = client.get(f"/auftrag/auf-formular-test/objekt/neu?typ={typ}")
    assert res.status_code == 200

def test_neu_und_bearbeiten_formular_mit_liste_und_objekt_referenz(temp_storage, temp_test_schema):
    client.post("/auftrag/neu", data={
        "projekt_nummer": "PROJ-VM-1", "kunde": "PoC", "bezeichnung": "VM Test",
    }, follow_redirects=False)
    auftrag_id = "auf-vm-test"
    client.post(f"/auftrag/{auftrag_id}/standort/neu", data={"bezeichnung": "Standort A"}, follow_redirects=False)
    standort_id = "sto-standort-a"

    res_neu = client.get(f"/auftrag/{auftrag_id}/objekt/neu?typ=test_vm")
    assert res_neu.status_code == 200
    assert "Festplatten-Slots" in res_neu.text

    res_host = client.post(f"/auftrag/{auftrag_id}/objekt/neu?typ=test_host", data={
        "bezeichnung": "Host 1", "standort_id": standort_id,
    }, follow_redirects=False)
    assert res_host.status_code == 303
    host_id = storage.list_objekte(auftrag_id, typ="test_host")[0].id

    res_vm = client.post(f"/auftrag/{auftrag_id}/objekt/neu?typ=test_vm", data={
        "bezeichnung": "VM 1", "standort_id": standort_id,
        "host_referenz": host_id,
        "festplatten_slots_0_typ": "ssd",
        "festplatten_slots_0_kapazitaet_gb": "480",
    }, follow_redirects=False)
    assert res_vm.status_code == 303

    vm = storage.list_objekte(auftrag_id, typ="test_vm")[0]
    assert vm.daten["host_referenz"] == host_id
    assert vm.daten["festplatten_slots"] == [{"typ": "ssd", "kapazitaet_gb": 480.0}]

    res_edit = client.get(f"/auftrag/{auftrag_id}/objekt/test_vm/{vm.id}")
    assert res_edit.status_code == 200
    assert "480" in res_edit.text
    assert "Host 1" in res_edit.text
