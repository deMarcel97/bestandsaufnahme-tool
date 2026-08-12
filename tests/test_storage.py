import pytest
from pathlib import Path
from app.services.storage import StorageService
from app.services.slug import generate_slug_id, slugify, is_valid_id
from app.models.auftrag import Auftrag
from app.models.standort import Standort
from app.models.technik import TechnikObjekt

def test_slugify():
    assert slugify("Landkreis München 2026!") == "landkreis-muenchen-2026"
    assert slugify("Zentrale - Hauptgebäude") == "zentrale-hauptgebaeude"

def test_generate_slug_id_collision():
    existing = ["sto-zentrale", "sto-zentrale-01"]
    sid = generate_slug_id("standort", "Zentrale", existing)
    assert sid == "sto-zentrale-02"

def test_storage_crud_and_duplication(tmp_path):
    storage = StorageService(data_dir=tmp_path)
    
    # Save Auftrag
    a = Auftrag(id="auf-test", projekt_nummer="123", kunde="Kunde A", bezeichnung="Test Project")
    storage.save_auftrag(a)
    loaded_a = storage.load_auftrag("auf-test")
    assert loaded_a is not None
    assert loaded_a.kunde == "Kunde A"

    # Save Standort
    sto = Standort(id="sto-zentrale", auftrag_id="auf-test", bezeichnung="Zentrale")
    storage.save_standort(sto)

    # Save TechnikObjekt
    obj = TechnikObjekt(
        id="fw-zentrale-01",
        typ="firewall",
        bezeichnung="Firewall 01",
        auftrag_id="auf-test",
        standort_id="sto-zentrale",
        daten={"hersteller": "Sophos", "hardware_alter": "unter_3_jahre"}
    )
    storage.save_objekt(obj)

    # Duplicate Objekt
    copy_obj = storage.duplicate_objekt("auf-test", "firewall", "fw-zentrale-01")
    assert copy_obj is not None
    assert copy_obj.id != "fw-zentrale-01"
    assert "Kopie" in copy_obj.bezeichnung
    assert copy_obj.daten["hersteller"] == "Sophos"

def test_is_valid_id():
    assert is_valid_id("auf-test")
    assert is_valid_id("sto-zentrale-01")
    assert is_valid_id("server_virtualisierung")  # typ-Werte nutzen snake_case
    assert not is_valid_id("..")
    assert not is_valid_id("../../etc")
    assert not is_valid_id("")
    assert not is_valid_id("a/b")
    assert not is_valid_id(".")

def test_path_traversal_delete_auftrag_is_blocked(tmp_path):
    # Sentinel außerhalb von data_dir, um Traversal über ".." nachzuweisen
    root = tmp_path / "root"
    data_dir = root / "data"
    data_dir.mkdir(parents=True)
    sentinel = root / "SENTINEL.txt"
    sentinel.write_text("sentinel")

    storage = StorageService(data_dir=data_dir)
    storage.delete_auftrag("..")  # frueher: shutil.rmtree(data_dir / "..") == rmtree(root)

    assert sentinel.exists()
    assert data_dir.exists()

def test_path_traversal_rejected_in_all_id_params(tmp_path):
    storage = StorageService(data_dir=tmp_path)
    a = Auftrag(id="auf-test", projekt_nummer="123", kunde="Kunde A", bezeichnung="Test Project")
    storage.save_auftrag(a)

    assert storage.load_auftrag("..") is None
    assert storage.load_standort("auf-test", "..") is None
    assert storage.load_objekt("auf-test", "..", "irrelevant") is None
    assert storage.load_objekt("auf-test", "firewall", "..") is None
    storage.delete_objekt("auf-test", "..", "auftrag")  # darf nicht auftrag.yaml treffen
    assert storage.load_auftrag("auf-test") is not None
