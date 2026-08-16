"""Tests für Karte #316: Erfassungsseite für Unterlagen
(Auftrag.dokumentenanforderung).

Das Feld existierte im Modell und wurde bereits von `progress.py` gelesen
(offene Punkte für angeforderte/offene Dokumente) — die Schleife lief aber
immer über eine leere Liste, weil es kein Formular gab, das sie füllen
konnte. Die Tests hier decken die neue Seite ab (inklusive Konflikterkennung,
#308) und dass die Fortschrittsseite jetzt tatsächlich reagiert.
"""

import re
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.auftrag import Auftrag
from app.models.standort import Standort
from app.models.technik import TechnikObjekt
from app.services.progress import progress_service

client = TestClient(app)

AUFTRAG_ID = "auf-unterlagen-test"
STANDORT_ID = "sto-zentrale"
OBJEKT_ID = "fw-zentrale"


@pytest.fixture(autouse=True)
def temp_storage(tmp_path):
    from app.services.storage import storage
    old_dir = storage.data_dir
    storage.data_dir = tmp_path
    yield
    storage.data_dir = old_dir


@pytest.fixture
def bestand():
    """Auftrag mit Standort und Objekt, damit strukturelle offene Punkte
    (fehlender Standort / fehlendes Objekt je Baustein) die Dokument-Punkte
    im Progress-Test nicht überlagern."""
    from app.services.storage import storage
    storage.save_auftrag(Auftrag(
        id=AUFTRAG_ID,
        projekt_nummer="PROJEKT-316-B",
        kunde="Unterlagen GmbH",
        bezeichnung="Unterlagen-Bestandsaufnahme",
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
    treffer = re.search(r'name="version"\s+value="(\d+)"', seite)
    assert treffer, "Das Formular führt keine Version mit"
    return treffer.group(1)


def test_unterlagen_form_laedt(bestand):
    antwort = client.get(f"/auftrag/{AUFTRAG_ID}/unterlagen")
    assert antwort.status_code == 200
    assert "Unterlagen" in antwort.text


def test_dokument_anlegen_und_speichern(bestand):
    stand = _version_im_formular(client.get(f"/auftrag/{AUFTRAG_ID}/unterlagen").text)
    antwort = client.post(
        f"/auftrag/{AUFTRAG_ID}/unterlagen",
        data={
            "version": stand,
            "dokument_bezeichnung_0": "Netzplan",
            "dokument_angefordert_am_0": "2026-01-15",
            "dokument_status_0": "angefordert",
            "dokument_bemerkung_0": "Beim IT-Leiter angefragt",
        },
        follow_redirects=False,
    )
    assert antwort.status_code == 303

    auftrag = bestand.load_auftrag(AUFTRAG_ID)
    assert len(auftrag.dokumentenanforderung) == 1
    d = auftrag.dokumentenanforderung[0]
    assert d.bezeichnung == "Netzplan"
    assert d.angefordert_am == "2026-01-15"
    assert d.status == "angefordert"
    assert d.bemerkung == "Beim IT-Leiter angefragt"


def test_leere_zeile_erzeugt_keinen_datensatz(bestand):
    """Eine hinzugefügte, aber nicht ausgefüllte Zeile — auch mit dem
    unberührten Status-Platzhalter — darf keinen Datensatz hinterlassen."""
    stand = _version_im_formular(client.get(f"/auftrag/{AUFTRAG_ID}/unterlagen").text)
    client.post(
        f"/auftrag/{AUFTRAG_ID}/unterlagen",
        data={"version": stand, "dokument_status_0": ""},
        follow_redirects=False,
    )
    auftrag = bestand.load_auftrag(AUFTRAG_ID)
    assert auftrag.dokumentenanforderung == []


def test_zweiter_benutzer_ueberschreibt_den_ersten_nicht(bestand):
    """Konflikterkennung (#308): A speichert zuerst, B mit demselben
    Ausgangsstand prallt ab und bekommt seine Eingaben zurück."""
    stand = _version_im_formular(client.get(f"/auftrag/{AUFTRAG_ID}/unterlagen").text)

    antwort_a = client.post(
        f"/auftrag/{AUFTRAG_ID}/unterlagen",
        data={"version": stand, "dokument_bezeichnung_0": "Von A", "dokument_status_0": "offen"},
        follow_redirects=False,
    )
    assert antwort_a.status_code == 303

    antwort_b = client.post(
        f"/auftrag/{AUFTRAG_ID}/unterlagen",
        data={"version": stand, "dokument_bezeichnung_0": "Von B", "dokument_status_0": "offen"},
        follow_redirects=False,
    )
    assert antwort_b.status_code == 409
    assert "Nicht gespeichert" in antwort_b.text
    assert "Von B" in antwort_b.text
    assert bestand.load_auftrag(AUFTRAG_ID).dokumentenanforderung[0].bezeichnung == "Von A"


# ── progress.py: die Schleife lief bisher über eine leere Liste (Karte #316) ──

def test_offene_dokumentenanforderung_erzeugt_einen_offenen_punkt(bestand):
    auftrag = bestand.load_auftrag(AUFTRAG_ID)
    auftrag.dokumentenanforderung = [
        {"bezeichnung": "Netzplan", "status": "offen"},
        {"bezeichnung": "Lizenzuebersicht", "status": "angefordert"},
        {"bezeichnung": "Passwortliste", "status": "erhalten"},
        {"bezeichnung": "NDA", "status": "abgelehnt"},
    ]
    # Über das Modell laufen lassen statt Dicts direkt zu übernehmen, damit
    # der Test dieselbe Validierung durchläuft wie das echte Formular.
    from app.models.auftrag import Dokumentenanforderung
    auftrag.dokumentenanforderung = [Dokumentenanforderung(**d) for d in auftrag.dokumentenanforderung]
    bestand.save_auftrag(auftrag)

    standorte = bestand.list_standorte(AUFTRAG_ID)
    objekte = bestand.list_objekte(AUFTRAG_ID)
    offene_punkte = progress_service.collect_offene_punkte(auftrag, standorte, objekte, [])

    dokument_punkte = [p for p in offene_punkte if p.quelle == "dokument"]
    texte = {p.text for p in dokument_punkte}

    # Nur "offen" und "angefordert" sind ausstehend — "erhalten" und
    # "abgelehnt" sind abgeschlossene Zustände, kein offener Punkt mehr.
    assert len(dokument_punkte) == 2
    assert any("Netzplan" in t for t in texte)
    assert any("Lizenzuebersicht" in t for t in texte)
    assert not any("Passwortliste" in t for t in texte)
    assert not any("NDA" in t for t in texte)

    # Das Ziel muss auf die neue Unterlagen-Seite zeigen, nicht auf die
    # Stammdaten — dort gibt es das Feld gar nicht mehr zu bearbeiten.
    for p in dokument_punkte:
        assert p.ziel_url == f"/auftrag/{AUFTRAG_ID}/unterlagen"


def test_vollstaendig_erledigte_dokumente_erzeugen_keinen_offenen_punkt(bestand):
    from app.models.auftrag import Dokumentenanforderung
    auftrag = bestand.load_auftrag(AUFTRAG_ID)
    auftrag.dokumentenanforderung = [
        Dokumentenanforderung(bezeichnung="Netzplan", status="erhalten"),
        Dokumentenanforderung(bezeichnung="NDA", status="abgelehnt"),
    ]
    bestand.save_auftrag(auftrag)

    standorte = bestand.list_standorte(AUFTRAG_ID)
    objekte = bestand.list_objekte(AUFTRAG_ID)
    offene_punkte = progress_service.collect_offene_punkte(auftrag, standorte, objekte, [])

    assert not [p for p in offene_punkte if p.quelle == "dokument"]


def test_unterlagen_seite_zeigt_ausstehendes_dokument_in_offenen_punkten(bestand):
    """End-to-End: über das Formular gespeicherte offene Unterlage taucht auf
    der Offene-Punkte-Seite mit Link zur Unterlagen-Seite auf."""
    stand = _version_im_formular(client.get(f"/auftrag/{AUFTRAG_ID}/unterlagen").text)
    client.post(
        f"/auftrag/{AUFTRAG_ID}/unterlagen",
        data={
            "version": stand,
            "dokument_bezeichnung_0": "Netzplan",
            "dokument_status_0": "offen",
        },
        follow_redirects=False,
    )

    seite = client.get(f"/auftrag/{AUFTRAG_ID}/offene_punkte")
    assert seite.status_code == 200
    assert "Netzplan" in seite.text
    assert f"/auftrag/{AUFTRAG_ID}/unterlagen" in seite.text
