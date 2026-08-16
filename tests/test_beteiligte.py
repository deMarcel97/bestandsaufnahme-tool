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


# ── Feature #321: Support-Matrix mit Technik-Verknüpfung, Notfall & SLAs ────

def test_speichert_und_laedt_erweiterte_felder(bestand):
    from app.models.technik import TechnikObjekt

    bestand.save_objekt(TechnikObjekt(
        id="fw-test-1",
        typ="firewall",
        bezeichnung="Haupt-Firewall",
        auftrag_id=AUFTRAG_ID
    ))

    stand = _version_im_formular(client.get(f"/auftrag/{AUFTRAG_ID}/beteiligte").text)

    antwort = client.post(
        f"/auftrag/{AUFTRAG_ID}/beteiligte",
        data={
            "version": stand,
            "beteiligter_name_0": "Max Notfall",
            "beteiligter_organisation_0": "IT-Service GmbH",
            "beteiligter_rolle_0": "Dienstleister",
            "beteiligter_objekt_id_0": "fw-test-1",
            "beteiligter_zustaendig_fuer_thema_0": "VPN & Routing",
            "beteiligter_email_0": "support@itservice.de",
            "beteiligter_telefon_0": "089-11111",
            "beteiligter_notfall_telefon_0": "0800-99999",
            "beteiligter_erreichbarkeit_0": "24/7 Rufbereitschaft",
            "beteiligter_sla_reaktionszeit_0": "2h Reaktionszeit",
        },
        follow_redirects=False,
    )
    assert antwort.status_code == 303

    auftrag = bestand.load_auftrag(AUFTRAG_ID)
    assert len(auftrag.beteiligte) == 1
    b = auftrag.beteiligte[0]
    assert b.name == "Max Notfall"
    assert b.objekt_id == "fw-test-1"
    assert b.notfall_telefon == "0800-99999"
    assert b.erreichbarkeit == "24/7 Rufbereitschaft"
    assert b.sla_reaktionszeit == "2h Reaktionszeit"

    # Formular zeigt gespeicherte Daten und selektiertes Dropdown
    seite = client.get(f"/auftrag/{AUFTRAG_ID}/beteiligte")
    assert "0800-99999" in seite.text
    assert "24/7 Rufbereitschaft" in seite.text
    assert "2h Reaktionszeit" in seite.text
    assert 'selected>Firewall: Haupt-Firewall</option>' in seite.text


def test_formular_objekte_dropdown_und_neues_objekt_link(bestand):
    from app.models.technik import TechnikObjekt

    bestand.save_objekt(TechnikObjekt(
        id="sw-test-1",
        typ="switch",
        bezeichnung="Core Switch",
        auftrag_id=AUFTRAG_ID
    ))

    seite = client.get(f"/auftrag/{AUFTRAG_ID}/beteiligte")
    assert "+ Neues Technik-Objekt anlegen ↗" in seite.text
    assert f'/auftrag/{AUFTRAG_ID}/erfassung' in seite.text
    assert 'target="_blank"' in seite.text
    assert "Switch: Core Switch" in seite.text
    assert "-- Allgemein / Gesamt-IT --" in seite.text


def test_formular_hinweis_wenn_keine_objekte(bestand):
    seite = client.get(f"/auftrag/{AUFTRAG_ID}/beteiligte")
    assert "Noch keine Technik-Objekte erfasst" in seite.text
    assert f'/auftrag/{AUFTRAG_ID}/erfassung' in seite.text


def test_report_builder_support_matrix_tabelle(bestand):
    from app.models.technik import TechnikObjekt
    from app.models.auftrag import Beteiligter
    from app.services.report_builder import report_builder
    from app.services.evaluator import evaluator_service

    fw = TechnikObjekt(
        id="fw-test-1",
        typ="firewall",
        bezeichnung="Zentrale Firewall",
        auftrag_id=AUFTRAG_ID
    )
    bestand.save_objekt(fw)

    auftrag = bestand.load_auftrag(AUFTRAG_ID)
    auftrag.beteiligte = [
        Beteiligter(
            name="Max Mustermann",
            organisation="IT Partner",
            rolle="Techniker",
            objekt_id="fw-test-1",
            zustaendig_fuer_thema="Firewall & Security",
            email="max@partner.de",
            telefon="089-12345",
            notfall_telefon="0800-99999",
            erreichbarkeit="Mo-Fr 8-18 Uhr",
            sla_reaktionszeit="4h Vor-Ort"
        ),
        Beteiligter(
            name="Erika Musterfrau",
            organisation="Kunde",
            rolle="Ansprechpartner_Kunde",
            objekt_id=None,
            zustaendig_fuer_thema="Gesamt-IT",
            email="erika@kunde.de",
            telefon="089-54321",
            notfall_telefon="",
            erreichbarkeit="Mo-Fr 9-17 Uhr",
            sla_reaktionszeit=""
        )
    ]

    bewertung = evaluator_service.evaluate_auftrag(auftrag.aktive_bausteine, [fw])
    md = report_builder.build_analysebericht(auftrag, [], [fw], [], bewertung, [], ziel_vertraulichkeit="kundentauglich")

    assert "## 2. Ansprechpartner & Support-Matrix" in md
    assert "| System/Bereich | Ansprechpartner & Rolle | Service- & Notfallkontakt | Service-Zeiten & SLA |" in md
    assert "Zentrale Firewall (Firewall) - Firewall & Security" in md
    assert "Max Mustermann (Techniker, IT Partner)" in md
    assert "Tel: 089-12345 / Notfall: 0800-99999 / Mail: max@partner.de" in md
    assert "Zeiten: Mo-Fr 8-18 Uhr / SLA: 4h Vor-Ort" in md
    assert "Gesamt-IT" in md
    assert "Erika Musterfrau (Ansprechpartner_Kunde, Kunde)" in md

    # Anonymisierter Bericht maskiert persönliche Daten
    md_anon = report_builder.build_analysebericht(auftrag, [], [fw], [], bewertung, [], ziel_vertraulichkeit="anonymisiert")
    assert "## 2. Ansprechpartner & Support-Matrix" in md_anon
    assert "[ANONYMISIERT]" in md_anon
    assert "Max Mustermann" not in md_anon
    assert "max@partner.de" not in md_anon
    assert "0800-99999" not in md_anon


def test_docx_export_support_matrix(bestand):
    from app.models.technik import TechnikObjekt
    from app.models.auftrag import Beteiligter
    from app.services.exporter import exporter_service
    from docx import Document

    fw = TechnikObjekt(
        id="fw-test-1",
        typ="firewall",
        bezeichnung="Zentrale Firewall",
        auftrag_id=AUFTRAG_ID,
        vertraulichkeit="kundentauglich"
    )
    bestand.save_objekt(fw)

    auftrag = bestand.load_auftrag(AUFTRAG_ID)
    auftrag.beteiligte = [
        Beteiligter(
            name="Max Mustermann",
            organisation="IT Partner",
            rolle="Techniker",
            objekt_id="fw-test-1",
            zustaendig_fuer_thema="Firewall & Security",
            email="max@partner.de",
            telefon="089-12345",
            notfall_telefon="0800-99999",
            erreichbarkeit="Mo-Fr 8-18 Uhr",
            sla_reaktionszeit="4h Vor-Ort"
        )
    ]

    docx_stream = exporter_service.export_analysebericht_docx(auftrag, [], [fw], [], "kundentauglich")
    doc = Document(docx_stream)

    # Suche Support-Matrix Tabelle im DOCX
    found_table = False
    for t in doc.tables:
        header = [c.text.strip() for c in t.rows[0].cells]
        if "System/Bereich" in header and "Service- & Notfallkontakt" in header:
            found_table = True
            row_text = " | ".join(c.text.strip() for c in t.rows[1].cells)
            assert "Zentrale Firewall" in row_text
            assert "Max Mustermann" in row_text
            assert "0800-99999" in row_text
            assert "4h Vor-Ort" in row_text
            break
    assert found_table, "Support-Matrix Tabelle wurde nicht in das DOCX Dokument gerendert"

