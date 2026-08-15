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

# --- Reihenfolge der list_*-Methoden (#304) ---
# Ohne explizite Sortierung liefern glob()/iterdir() die Reihenfolge des
# Dateisystems: auf APFS die Hash-Reihenfolge der Verzeichniseinträge, also
# weder alphabetisch noch nach Anlagezeitpunkt — und sie ändert sich, sobald
# Einträge dazukommen oder wegfallen. Für den Benutzer sah das aus, als
# springe die Standortliste nach jedem Speichern.

def _auftrag_mit_standorten(tmp_path, bezeichnungen):
    storage = StorageService(data_dir=tmp_path)
    storage.save_auftrag(Auftrag(id="auf-test", bezeichnung="Test"))
    for i, bez in enumerate(bezeichnungen):
        storage.save_standort(
            Standort(id=f"sto-{i:02d}", auftrag_id="auf-test", bezeichnung=bez)
        )
    return storage


def test_standorte_alphabetisch_unabhaengig_von_anlagereihenfolge(tmp_path):
    storage = _auftrag_mit_standorten(
        tmp_path, ["Zentrale", "aachen", "Werk Süd", "Berlin", "Änderungsbüro"]
    )
    assert [s.bezeichnung for s in storage.list_standorte("auf-test")] == [
        "aachen", "Änderungsbüro", "Berlin", "Werk Süd", "Zentrale"
    ]


def test_standorte_reihenfolge_haengt_nicht_an_der_anlagereihenfolge(tmp_path):
    """Kernnachweis: dieselben Standorte in umgekehrter Reihenfolge angelegt
    müssen exakt dieselbe Liste ergeben."""
    bezeichnungen = ["Zentrale", "Aussenstelle", "München", "Berlin", "Hamburg"]
    vorwaerts = _auftrag_mit_standorten(tmp_path / "a", bezeichnungen)
    rueckwaerts = _auftrag_mit_standorten(tmp_path / "b", list(reversed(bezeichnungen)))

    assert [s.bezeichnung for s in vorwaerts.list_standorte("auf-test")] == \
           [s.bezeichnung for s in rueckwaerts.list_standorte("auf-test")]


def test_standorte_reihenfolge_bleibt_nach_speichern_und_loeschen_stabil(tmp_path):
    storage = _auftrag_mit_standorten(tmp_path, ["Zentrale", "Berlin", "Hamburg", "Aachen"])
    vorher = [s.id for s in storage.list_standorte("auf-test")]

    # Erneutes Speichern eines bestehenden Standorts darf nichts verschieben.
    storage.save_standort(storage.load_standort("auf-test", vorher[0]))
    assert [s.id for s in storage.list_standorte("auf-test")] == vorher

    # Löschen und in identischer Form neu anlegen ebenfalls nicht — genau hier
    # wechselte die Dateisystem-Reihenfolge frueher.
    mitte = storage.load_standort("auf-test", vorher[1])
    storage.delete_standort("auf-test", mitte.id)
    storage.save_standort(mitte)
    assert [s.id for s in storage.list_standorte("auf-test")] == vorher


def test_standorte_gleiche_bezeichnung_werden_ueber_id_stabilisiert(tmp_path):
    storage = StorageService(data_dir=tmp_path)
    storage.save_auftrag(Auftrag(id="auf-test", bezeichnung="Test"))
    for sid in ["sto-werk-02", "sto-werk", "sto-werk-01"]:
        storage.save_standort(Standort(id=sid, auftrag_id="auf-test", bezeichnung="Werk"))

    assert [s.id for s in storage.list_standorte("auf-test")] == \
        ["sto-werk", "sto-werk-01", "sto-werk-02"]


def test_objekte_nach_typ_dann_bezeichnung(tmp_path):
    storage = StorageService(data_dir=tmp_path)
    storage.save_auftrag(Auftrag(id="auf-test", bezeichnung="Test"))
    angelegt = [
        ("switch", "Switch Keller"),
        ("firewall", "Firewall Zentrale"),
        ("switch", "Switch Dach"),
        ("firewall", "firewall aussenstelle"),
    ]
    for i, (typ, bez) in enumerate(angelegt):
        storage.save_objekt(TechnikObjekt(
            id=f"obj-{i:02d}", typ=typ, bezeichnung=bez,
            auftrag_id="auf-test", standort_id="sto-zentrale"
        ))

    assert [(o.typ, o.bezeichnung) for o in storage.list_objekte("auf-test")] == [
        ("firewall", "firewall aussenstelle"),
        ("firewall", "Firewall Zentrale"),
        ("switch", "Switch Dach"),
        ("switch", "Switch Keller"),
    ]


def test_auftraege_nach_kunde_dann_bezeichnung(tmp_path):
    storage = StorageService(data_dir=tmp_path)
    angelegt = [
        ("auf-c", "Zeta GmbH", "Analyse"),
        ("auf-a", "alpha AG", "Migration"),
        ("auf-b", "alpha AG", "Bestandsaufnahme"),
    ]
    for aid, kunde, bez in angelegt:
        storage.save_auftrag(Auftrag(id=aid, kunde=kunde, bezeichnung=bez))

    assert [a.id for a in storage.list_auftraege()] == ["auf-b", "auf-a", "auf-c"]


def test_sortier_schluessel_behandelt_umlaute_und_grossschreibung(tmp_path):
    schluessel = StorageService.sortier_schluessel
    assert schluessel("Zentrale") == "zentrale"
    assert schluessel("München") == "muenchen"
    assert schluessel("ÄRZTEHAUS") == "aerztehaus"
    assert schluessel("Straße") == "strasse"
    assert schluessel("") == ""


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
