"""Tests für Stufe 1 des Speicherkonzepts: atomares Schreiben und
Konflikterkennung (Karte #305)."""

import os
import pytest
import yaml

from app.models.auftrag import Auftrag
from app.models.standort import Standort
from app.models.technik import TechnikObjekt
from app.services.storage import KonfliktFehler, StorageService, write_yaml_atomic


@pytest.fixture
def storage(tmp_path):
    return StorageService(data_dir=tmp_path)


# ── Atomares Schreiben ──────────────────────────────────────────────────

def test_schreiben_hinterlaesst_keine_temporaerdatei(tmp_path):
    ziel = tmp_path / "auftrag.yaml"
    write_yaml_atomic(ziel, {"a": 1})
    assert ziel.exists()
    assert list(tmp_path.iterdir()) == [ziel]


def test_alter_stand_bleibt_erhalten_wenn_das_schreiben_scheitert(tmp_path, monkeypatch):
    """Der Kern der Sache: bricht der Schreibvorgang ab, muss die bestehende
    Datei unangetastet sein. Mit `open(..., "w")` wäre sie zu diesem Zeitpunkt
    bereits geleert gewesen — genau der Datenverlust, um den es geht."""
    ziel = tmp_path / "auftrag.yaml"
    write_yaml_atomic(ziel, {"kunde": "Wichtig", "version": 1})

    def bricht_ab(*args, **kwargs):
        raise RuntimeError("Simulierter Abbruch mitten im Schreiben")

    monkeypatch.setattr("app.services.storage.yaml.dump", bricht_ab)

    with pytest.raises(RuntimeError):
        write_yaml_atomic(ziel, {"kunde": "Neu", "version": 2})

    # Alter Inhalt unverändert lesbar, kein Temporär-Torso zurückgeblieben
    assert yaml.safe_load(ziel.read_text(encoding="utf-8")) == {"kunde": "Wichtig", "version": 1}
    assert list(tmp_path.iterdir()) == [ziel]


def test_ersetzen_ist_ein_rename_kein_truncate(tmp_path, monkeypatch):
    """Belegt, dass os.replace genutzt wird — das ist die Eigenschaft, die
    Atomarität überhaupt erst herstellt."""
    ziel = tmp_path / "auftrag.yaml"
    aufrufe = []
    echtes_replace = os.replace

    def gemerkt(src, dst):
        aufrufe.append((str(src), str(dst)))
        return echtes_replace(src, dst)

    monkeypatch.setattr(os, "replace", gemerkt)
    write_yaml_atomic(ziel, {"a": 1})

    assert len(aufrufe) == 1
    assert aufrufe[0][1] == str(ziel)


# ── Konflikterkennung ───────────────────────────────────────────────────

def test_version_steigt_bei_jedem_speichern(storage):
    auftrag = Auftrag(id="auf-1", kunde="Kunde", bezeichnung="Test")
    assert auftrag.version == 1

    storage.save_auftrag(auftrag)
    assert auftrag.version == 2
    assert storage.load_auftrag("auf-1").version == 2

    storage.save_auftrag(auftrag)
    assert storage.load_auftrag("auf-1").version == 3


def test_zweiter_benutzer_ueberschreibt_nicht_stillschweigend(storage):
    """Das eigentliche Multiuser-Szenario: zwei Personen laden denselben
    Auftrag, beide speichern. Der zweite Speichervorgang muss scheitern statt
    die Arbeit des ersten zu verschlucken."""
    storage.save_auftrag(Auftrag(id="auf-1", kunde="Kunde", bezeichnung="Original"))

    benutzer_a = storage.load_auftrag("auf-1")
    benutzer_b = storage.load_auftrag("auf-1")

    benutzer_a.kunde = "Von A geändert"
    storage.save_auftrag(benutzer_a)

    benutzer_b.kunde = "Von B geändert"
    with pytest.raises(KonfliktFehler):
        storage.save_auftrag(benutzer_b)

    # Die Änderung von A ist erhalten geblieben
    assert storage.load_auftrag("auf-1").kunde == "Von A geändert"


def test_konflikt_nennt_den_betroffenen_datensatz(storage):
    storage.save_auftrag(Auftrag(id="auf-1", kunde="K", bezeichnung="Netzanalyse 2026"))
    veraltet = storage.load_auftrag("auf-1")
    storage.save_auftrag(storage.load_auftrag("auf-1"))

    with pytest.raises(KonfliktFehler) as exc:
        storage.save_auftrag(veraltet)
    assert "Netzanalyse 2026" in str(exc.value)


def test_konflikterkennung_greift_auch_fuer_standort_und_objekt(storage):
    storage.save_auftrag(Auftrag(id="auf-1", kunde="K", bezeichnung="T"))

    storage.save_standort(Standort(id="sto-1", auftrag_id="auf-1", bezeichnung="Zentrale"))
    veralteter_standort = storage.load_standort("auf-1", "sto-1")
    storage.save_standort(storage.load_standort("auf-1", "sto-1"))
    with pytest.raises(KonfliktFehler):
        storage.save_standort(veralteter_standort)

    storage.save_objekt(TechnikObjekt(id="fw-1", typ="firewall", auftrag_id="auf-1",
                                      standort_id="sto-1", bezeichnung="Firewall"))
    veraltetes_objekt = storage.load_objekt("auf-1", "firewall", "fw-1")
    storage.save_objekt(storage.load_objekt("auf-1", "firewall", "fw-1"))
    with pytest.raises(KonfliktFehler):
        storage.save_objekt(veraltetes_objekt)


def test_bestandsdaten_ohne_version_bleiben_ladbar(storage, tmp_path):
    """Vorhandene YAML-Dateien kennen das Feld nicht — sie müssen weiter
    funktionieren und dürfen beim ersten Speichern keinen Konflikt auslösen."""
    d = tmp_path / "auf-alt"
    d.mkdir()
    (d / "auftrag.yaml").write_text(
        yaml.dump({"id": "auf-alt", "kunde": "Altbestand", "bezeichnung": "Ohne Version"}),
        encoding="utf-8",
    )

    geladen = storage.load_auftrag("auf-alt")
    assert geladen is not None
    assert geladen.version == 1

    geladen.kunde = "Bearbeitet"
    storage.save_auftrag(geladen)
    assert storage.load_auftrag("auf-alt").kunde == "Bearbeitet"


def test_neuanlegen_loest_keinen_konflikt_aus(storage):
    """Ohne bestehende Datei gibt es nichts zu vergleichen."""
    storage.save_auftrag(Auftrag(id="auf-neu", kunde="K", bezeichnung="Neu"))
    assert storage.load_auftrag("auf-neu") is not None


# ── Rückmeldung an den Benutzer ─────────────────────────────────────────

def test_konflikt_wird_als_409_beantwortet_nicht_als_serverfehler():
    """Der zentrale Exception-Handler soll aus dem KonfliktFehler eine
    verständliche Seite machen, statt den Benutzer mit einem 500er
    stehenzulassen."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app, raise_server_exceptions=False)

    @app.get("/__konflikt_test")
    def _ausloeser():
        raise KonfliktFehler("Netzanalyse 2026")

    try:
        response = client.get("/__konflikt_test")
        assert response.status_code == 409
        assert "Netzanalyse 2026" in response.text
        assert "nicht gespeichert" in response.text.lower()
    finally:
        app.router.routes = [
            r for r in app.router.routes
            if getattr(r, "path", None) != "/__konflikt_test"
        ]
