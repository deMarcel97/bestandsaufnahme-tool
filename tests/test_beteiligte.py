"""Tests für Karte #316a: die Erfassungsseite für Auftrag.beteiligte.

Das Modellfeld existierte schon, liess sich aber durch kein Formular füllen.
Die Tests hier decken das Formular selbst ab (Anzeige, Speichern, leere
Zeilen) und die Konflikterkennung nach dem Muster aus #308
(test_konflikt_formulare.py).
"""

import re
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.auftrag import Auftrag

client = TestClient(app)

AUFTRAG_ID = "auf-beteiligte-test"


@pytest.fixture(autouse=True)
def temp_storage(tmp_path):
    from app.services.storage import storage
    old_dir = storage.data_dir
    storage.data_dir = tmp_path
    yield
    storage.data_dir = old_dir


@pytest.fixture
def bestand():
    from app.services.storage import storage

    storage.save_auftrag(Auftrag(
        id=AUFTRAG_ID,
        projekt_nummer="auf-2026-316",
        kunde="Beteiligte GmbH",
        bezeichnung="Beteiligte-Bestandsaufnahme",
        aktive_bausteine=["firewall"],
    ))
    return storage


def _version_im_formular(seite: str) -> str:
    treffer = re.search(r'name="version"\s+value="(\d+)"', seite)
    assert treffer, "Das Formular führt keine Version mit"
    return treffer.group(1)


# ── Grundfunktion ─────────────────────────────────────────────────────────

def test_formular_ist_erreichbar(bestand):
    antwort = client.get(f"/auftrag/{AUFTRAG_ID}/beteiligte")
    assert antwort.status_code == 200
    assert "Beteiligte" in antwort.text


def test_formular_fuer_unbekannten_auftrag_leitet_um():
    antwort = client.get("/auftrag/unbekannt/beteiligte", follow_redirects=False)
    assert antwort.status_code == 303
    assert antwort.headers["location"] == "/auftrag"


def test_speichert_mehrere_zeilen(bestand):
    stand = _version_im_formular(client.get(f"/auftrag/{AUFTRAG_ID}/beteiligte").text)

    antwort = client.post(
        f"/auftrag/{AUFTRAG_ID}/beteiligte",
        data={
            "version": stand,
            "beteiligter_name_0": "Anna Admin",
            "beteiligter_organisation_0": "Kunde",
            "beteiligter_rolle_0": "Ansprechpartner_Kunde",
            "beteiligter_zustaendig_fuer_thema_0": "Firewall",
            "beteiligter_email_0": "anna@kunde.de",
            "beteiligter_telefon_0": "0123456",
            "beteiligter_name_1": "Bert Bau",
            "beteiligter_organisation_1": "Dienstleister GmbH",
            "beteiligter_rolle_1": "Techniker",
            "beteiligter_zustaendig_fuer_thema_1": "Verkabelung",
            "beteiligter_email_1": "bert@dienstleister.de",
            "beteiligter_telefon_1": "0654321",
        },
        follow_redirects=False,
    )
    assert antwort.status_code == 303

    auftrag = bestand.load_auftrag(AUFTRAG_ID)
    assert len(auftrag.beteiligte) == 2
    assert auftrag.beteiligte[0].name == "Anna Admin"
    assert auftrag.beteiligte[0].rolle == "Ansprechpartner_Kunde"
    assert auftrag.beteiligte[1].name == "Bert Bau"
    assert auftrag.beteiligte[1].organisation == "Dienstleister GmbH"


def test_leere_zeile_wird_verworfen(bestand):
    """Eine per JavaScript hinzugefügte, aber nicht ausgefüllte Zeile schickt
    ihre Felder als leere Strings mit — die darf keinen Datensatz erzeugen."""
    stand = _version_im_formular(client.get(f"/auftrag/{AUFTRAG_ID}/beteiligte").text)

    client.post(
        f"/auftrag/{AUFTRAG_ID}/beteiligte",
        data={
            "version": stand,
            "beteiligter_name_0": "Anna Admin",
            "beteiligter_rolle_0": "Ansprechpartner_Kunde",
            # Zeile 1: alle Felder leer, wie von einer ungenutzten Zeile im
            # Formular verschickt.
            "beteiligter_name_1": "",
            "beteiligter_organisation_1": "",
            "beteiligter_rolle_1": "",
            "beteiligter_zustaendig_fuer_thema_1": "",
            "beteiligter_email_1": "",
            "beteiligter_telefon_1": "",
        },
        follow_redirects=False,
    )

    auftrag = bestand.load_auftrag(AUFTRAG_ID)
    assert len(auftrag.beteiligte) == 1
    assert auftrag.beteiligte[0].name == "Anna Admin"


def test_gespeicherte_beteiligte_erscheinen_im_formular(bestand):
    stand = _version_im_formular(client.get(f"/auftrag/{AUFTRAG_ID}/beteiligte").text)
    client.post(
        f"/auftrag/{AUFTRAG_ID}/beteiligte",
        data={
            "version": stand,
            "beteiligter_name_0": "Anna Admin",
            "beteiligter_email_0": "anna@kunde.de",
        },
        follow_redirects=False,
    )

    seite = client.get(f"/auftrag/{AUFTRAG_ID}/beteiligte")
    assert "Anna Admin" in seite.text
    assert "anna@kunde.de" in seite.text


def test_leerer_bestand_zeigt_eine_leere_zeile(bestand):
    """Ohne Beteiligte gibt es trotzdem eine erste editierbare Zeile, statt
    einer leeren Tabelle ohne Einstiegspunkt."""
    seite = client.get(f"/auftrag/{AUFTRAG_ID}/beteiligte")
    assert 'name="beteiligter_name_0"' in seite.text


# ── Konflikterkennung (#308) ───────────────────────────────────────────────

def test_zweiter_benutzer_ueberschreibt_den_ersten_nicht(bestand):
    a = client.get(f"/auftrag/{AUFTRAG_ID}/beteiligte")
    b = client.get(f"/auftrag/{AUFTRAG_ID}/beteiligte")
    stand = _version_im_formular(a.text)
    assert _version_im_formular(b.text) == stand

    antwort_a = client.post(
        f"/auftrag/{AUFTRAG_ID}/beteiligte",
        data={"version": stand, "beteiligter_name_0": "Von A"},
        follow_redirects=False,
    )
    assert antwort_a.status_code == 303
    assert bestand.load_auftrag(AUFTRAG_ID).beteiligte[0].name == "Von A"

    antwort_b = client.post(
        f"/auftrag/{AUFTRAG_ID}/beteiligte",
        data={"version": stand, "beteiligter_name_0": "Von B"},
        follow_redirects=False,
    )
    assert antwort_b.status_code == 409
    assert bestand.load_auftrag(AUFTRAG_ID).beteiligte[0].name == "Von A"


def test_konflikt_liefert_das_formular_mit_den_eingegebenen_werten_zurueck(bestand):
    stand = _version_im_formular(client.get(f"/auftrag/{AUFTRAG_ID}/beteiligte").text)
    client.post(
        f"/auftrag/{AUFTRAG_ID}/beteiligte",
        data={"version": stand, "beteiligter_name_0": "Von A"},
        follow_redirects=False,
    )
    antwort = client.post(
        f"/auftrag/{AUFTRAG_ID}/beteiligte",
        data={"version": stand, "beteiligter_name_0": "Muehsam getippter Name von B"},
        follow_redirects=False,
    )

    assert antwort.status_code == 409
    assert "Muehsam getippter Name von B" in antwort.text
    assert "Nicht gespeichert" in antwort.text


def test_erneutes_speichern_nach_dem_hinweis_setzt_sich_durch(bestand):
    stand = _version_im_formular(client.get(f"/auftrag/{AUFTRAG_ID}/beteiligte").text)
    client.post(
        f"/auftrag/{AUFTRAG_ID}/beteiligte",
        data={"version": stand, "beteiligter_name_0": "Von A"},
        follow_redirects=False,
    )
    abgelehnt = client.post(
        f"/auftrag/{AUFTRAG_ID}/beteiligte",
        data={"version": stand, "beteiligter_name_0": "Von B"},
        follow_redirects=False,
    )
    assert abgelehnt.status_code == 409

    zweiter_anlauf = client.post(
        f"/auftrag/{AUFTRAG_ID}/beteiligte",
        data={"version": _version_im_formular(abgelehnt.text), "beteiligter_name_0": "Von B"},
        follow_redirects=False,
    )
    assert zweiter_anlauf.status_code == 303
    assert bestand.load_auftrag(AUFTRAG_ID).beteiligte[0].name == "Von B"


def test_ohne_mitgefuehrte_version_bleibt_es_beim_bisherigen_verhalten(bestand):
    client.post(
        f"/auftrag/{AUFTRAG_ID}/beteiligte",
        data={"version": "1", "beteiligter_name_0": "Von A"},
        follow_redirects=False,
    )

    ohne_feld = client.post(
        f"/auftrag/{AUFTRAG_ID}/beteiligte",
        data={"beteiligter_name_0": "Ohne Version"},
        follow_redirects=False,
    )
    assert ohne_feld.status_code == 303
    assert bestand.load_auftrag(AUFTRAG_ID).beteiligte[0].name == "Ohne Version"


def test_speichern_erhoeht_den_stand_im_formular(bestand):
    vorher = _version_im_formular(client.get(f"/auftrag/{AUFTRAG_ID}/beteiligte").text)

    client.post(
        f"/auftrag/{AUFTRAG_ID}/beteiligte",
        data={"version": vorher, "beteiligter_name_0": "Anna Admin"},
        follow_redirects=False,
    )
    nachher = _version_im_formular(client.get(f"/auftrag/{AUFTRAG_ID}/beteiligte").text)

    assert int(nachher) == int(vorher) + 1


# ── Seitenleiste ────────────────────────────────────────────────────────

def test_sidebar_hebt_beteiligte_als_aktiven_tab_hervor(bestand):
    seite = client.get(f"/auftrag/{AUFTRAG_ID}/beteiligte")
    assert re.search(
        r'<a href="/auftrag/[^"]+/beteiligte" class="active">', seite.text
    )


def test_sidebar_zeigt_anzahl_beteiligter(bestand):
    stand = _version_im_formular(client.get(f"/auftrag/{AUFTRAG_ID}/beteiligte").text)
    client.post(
        f"/auftrag/{AUFTRAG_ID}/beteiligte",
        data={
            "version": stand,
            "beteiligter_name_0": "Anna Admin",
            "beteiligter_name_1": "Bert Bau",
        },
        follow_redirects=False,
    )

    seite = client.get(f"/auftrag/{AUFTRAG_ID}/beteiligte")
    assert '<span class="count">2</span>' in seite.text
