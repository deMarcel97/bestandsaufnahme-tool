"""Tests für Karte #308: die Konflikterkennung über die Dauer eines geöffneten
Formulars hinweg.

Der Zähler und die Prüfung im StorageService stammen aus #305 — sie konnten aber
nie anschlagen, weil die POST-Handler den Datensatz unmittelbar vor dem Speichern
frisch von der Platte laden und die Version damit zwangsläufig übereinstimmt.
Die Tests hier stellen deshalb den eigentlichen Fall über HTTP nach: zwei
Benutzer öffnen dasselbe Formular, der zweite darf den ersten nicht überschreiben.
"""

import re
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.auftrag import Auftrag
from app.models.standort import Standort
from app.models.technik import TechnikObjekt

client = TestClient(app)

AUFTRAG_ID = "auf-konflikt-test"
STANDORT_ID = "sto-zentrale"
OBJEKT_ID = "fw-hauptstandort"


@pytest.fixture(autouse=True)
def temp_storage(tmp_path):
    from app.services.storage import storage
    old_dir = storage.data_dir
    storage.data_dir = tmp_path
    yield
    storage.data_dir = old_dir


@pytest.fixture
def bestand():
    """Ein Auftrag mit Standort und einem Technik-Objekt, alle auf Version 1."""
    from app.services.storage import storage

    storage.save_auftrag(Auftrag(
        id=AUFTRAG_ID,
        projekt_nummer="auf-2026-308",
        kunde="Konflikt GmbH",
        bezeichnung="Konflikt-Bestandsaufnahme",
        aktive_bausteine=["firewall"],
    ))
    storage.save_standort(Standort(
        id=STANDORT_ID,
        auftrag_id=AUFTRAG_ID,
        bezeichnung="Zentrale",
        ort="Berlin",
        anzahl_user=25,
    ))
    storage.save_objekt(TechnikObjekt(
        id=OBJEKT_ID,
        typ="firewall",
        auftrag_id=AUFTRAG_ID,
        standort_id=STANDORT_ID,
        bezeichnung="Firewall Zentrale",
    ))
    return storage


def _version_im_formular(seite: str) -> str:
    """Liest den Stand, den ein ausgeliefertes Formular mitführt."""
    treffer = re.search(r'name="version"\s+value="(\d+)"', seite)
    assert treffer, "Das Formular führt keine Version mit"
    return treffer.group(1)


STAMMDATEN = {"kunde": "Konflikt GmbH", "bezeichnung": "Konflikt-Bestandsaufnahme"}


# ── Der Vierschritt aus der Karte, einmal je Formular ────────────────────

def test_stammdaten_zweiter_benutzer_ueberschreibt_den_ersten_nicht(bestand):
    """A und B öffnen dasselbe Formular, A speichert zuerst — B muss abprallen."""
    a = client.get(f"/auftrag/{AUFTRAG_ID}/stammdaten")
    b = client.get(f"/auftrag/{AUFTRAG_ID}/stammdaten")
    stand = _version_im_formular(a.text)
    assert _version_im_formular(b.text) == stand

    antwort_a = client.post(
        f"/auftrag/{AUFTRAG_ID}/stammdaten",
        data={**STAMMDATEN, "version": stand, "auftraggeber": "Von A"},
        follow_redirects=False,
    )
    assert antwort_a.status_code == 303
    assert bestand.load_auftrag(AUFTRAG_ID).auftraggeber == "Von A"

    antwort_b = client.post(
        f"/auftrag/{AUFTRAG_ID}/stammdaten",
        data={**STAMMDATEN, "version": stand, "auftraggeber": "Von B"},
        follow_redirects=False,
    )
    assert antwort_b.status_code == 409
    assert bestand.load_auftrag(AUFTRAG_ID).auftraggeber == "Von A"


def test_standort_zweiter_benutzer_ueberschreibt_den_ersten_nicht(bestand):
    a = client.get(f"/auftrag/{AUFTRAG_ID}/standort/{STANDORT_ID}/bearbeiten")
    stand = _version_im_formular(a.text)

    ziel = f"/auftrag/{AUFTRAG_ID}/standort/{STANDORT_ID}/bearbeiten"
    antwort_a = client.post(
        ziel,
        data={"bezeichnung": "Zentrale", "version": stand, "funktion": "Von A"},
        follow_redirects=False,
    )
    assert antwort_a.status_code == 303

    antwort_b = client.post(
        ziel,
        data={"bezeichnung": "Zentrale", "version": stand, "funktion": "Von B"},
        follow_redirects=False,
    )
    assert antwort_b.status_code == 409
    assert bestand.load_standort(AUFTRAG_ID, STANDORT_ID).funktion == "Von A"


def test_technik_objekt_zweiter_benutzer_ueberschreibt_den_ersten_nicht(bestand):
    a = client.get(f"/auftrag/{AUFTRAG_ID}/objekt/firewall/{OBJEKT_ID}")
    stand = _version_im_formular(a.text)

    ziel = f"/auftrag/{AUFTRAG_ID}/objekt/firewall/{OBJEKT_ID}"
    basis = {"bezeichnung": "Firewall Zentrale", "standort_id": STANDORT_ID}

    antwort_a = client.post(
        ziel, data={**basis, "version": stand, "notiz": "Von A"}, follow_redirects=False
    )
    assert antwort_a.status_code == 303

    antwort_b = client.post(
        ziel, data={**basis, "version": stand, "notiz": "Von B"}, follow_redirects=False
    )
    assert antwort_b.status_code == 409
    assert bestand.load_objekt(AUFTRAG_ID, "firewall", OBJEKT_ID).notiz == "Von A"


def test_unternehmenskontext_zweiter_benutzer_ueberschreibt_den_ersten_nicht(bestand):
    a = client.get(f"/auftrag/{AUFTRAG_ID}/unternehmenskontext")
    stand = _version_im_formular(a.text)

    ziel = f"/auftrag/{AUFTRAG_ID}/unternehmenskontext"
    antwort_a = client.post(
        ziel, data={"version": stand, "kerngeschaeft": "Von A"}, follow_redirects=False
    )
    assert antwort_a.status_code == 303

    antwort_b = client.post(
        ziel, data={"version": stand, "kerngeschaeft": "Von B"}, follow_redirects=False
    )
    assert antwort_b.status_code == 409
    assert bestand.load_auftrag(AUFTRAG_ID).unternehmenskontext.kerngeschaeft == "Von A"


# ── Was der zurückgewiesene Benutzer zu sehen bekommt ────────────────────

def test_konflikt_liefert_das_formular_mit_den_eingegebenen_werten_zurueck(bestand):
    """Die Eingaben eines langen Formulars dürfen bei einem Konflikt nicht
    verlorengehen — sonst müsste der Benutzer alles neu tippen."""
    stand = _version_im_formular(client.get(f"/auftrag/{AUFTRAG_ID}/objekt/firewall/{OBJEKT_ID}").text)
    ziel = f"/auftrag/{AUFTRAG_ID}/objekt/firewall/{OBJEKT_ID}"
    basis = {"bezeichnung": "Firewall Zentrale", "standort_id": STANDORT_ID}

    client.post(ziel, data={**basis, "version": stand, "notiz": "Von A"}, follow_redirects=False)
    antwort = client.post(
        ziel,
        data={**basis, "version": stand, "notiz": "Muehsam getippter Text von B"},
        follow_redirects=False,
    )

    assert antwort.status_code == 409
    assert "Muehsam getippter Text von B" in antwort.text
    assert "Nicht gespeichert" in antwort.text


def test_erneutes_speichern_nach_dem_hinweis_setzt_sich_durch(bestand):
    """Das zurückgelieferte Formular führt den Stand der Platte mit. Wer nach
    dem Hinweis noch einmal speichert, überschreibt damit bewusst — sonst
    bliebe er in derselben Meldung hängen."""
    stand = _version_im_formular(client.get(f"/auftrag/{AUFTRAG_ID}/standort/{STANDORT_ID}/bearbeiten").text)
    ziel = f"/auftrag/{AUFTRAG_ID}/standort/{STANDORT_ID}/bearbeiten"

    client.post(ziel, data={"bezeichnung": "Zentrale", "version": stand, "funktion": "Von A"}, follow_redirects=False)
    abgelehnt = client.post(
        ziel, data={"bezeichnung": "Zentrale", "version": stand, "funktion": "Von B"}, follow_redirects=False
    )
    assert abgelehnt.status_code == 409

    zweiter_anlauf = client.post(
        ziel,
        data={"bezeichnung": "Zentrale", "version": _version_im_formular(abgelehnt.text), "funktion": "Von B"},
        follow_redirects=False,
    )
    assert zweiter_anlauf.status_code == 303
    assert bestand.load_standort(AUFTRAG_ID, STANDORT_ID).funktion == "Von B"


# ── Randfälle ───────────────────────────────────────────────────────────

def test_ohne_mitgefuehrte_version_bleibt_es_beim_bisherigen_verhalten(bestand):
    """Ein Formular aus einer älteren Programmversion (oder ein Aufruf per curl)
    schickt kein version-Feld. Das darf nicht dazu führen, dass gar nichts mehr
    gespeichert werden kann."""
    ziel = f"/auftrag/{AUFTRAG_ID}/standort/{STANDORT_ID}/bearbeiten"
    client.post(ziel, data={"bezeichnung": "Zentrale", "version": "1", "funktion": "Von A"}, follow_redirects=False)

    ohne_feld = client.post(ziel, data={"bezeichnung": "Zentrale", "funktion": "Ohne Version"}, follow_redirects=False)
    assert ohne_feld.status_code == 303
    assert bestand.load_standort(AUFTRAG_ID, STANDORT_ID).funktion == "Ohne Version"


def test_neuanlegen_fuehrt_keine_version_mit(bestand):
    """Beim Anlegen gibt es noch nichts, womit sich vergleichen liesse — das
    Feld gehört dort nicht ins Formular."""
    neu = client.get(f"/auftrag/{AUFTRAG_ID}/standort/neu")
    assert 'name="version"' not in neu.text


def test_speichern_erhoeht_den_stand_im_formular(bestand):
    """Nach jedem Speichern muss das Formular den neuen Stand ausliefern,
    sonst würde der nächste Speichervorgang fälschlich als Konflikt gelten."""
    ziel = f"/auftrag/{AUFTRAG_ID}/standort/{STANDORT_ID}/bearbeiten"
    vorher = _version_im_formular(client.get(ziel).text)

    client.post(ziel, data={"bezeichnung": "Zentrale", "version": vorher}, follow_redirects=False)
    nachher = _version_im_formular(client.get(ziel).text)

    assert int(nachher) == int(vorher) + 1
