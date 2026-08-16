"""Tests für Karte #316: die Seite „Projektrahmen" mit Rahmenbedingungen,
Ergebnisartefakten und den manuellen Beobachtungen vor Ort, sowie deren
Anbindung an den Bericht (`app/services/report_builder.py`).
"""

import re
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.auftrag import Auftrag

client = TestClient(app)

AUFTRAG_ID = "auf-projektrahmen-test"


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
        kunde="Projektrahmen GmbH",
        bezeichnung="Projektrahmen-Bestandsaufnahme",
        aktive_bausteine=["firewall"],
    ))
    return storage


def _version_im_formular(seite: str) -> str:
    treffer = re.search(r'name="version"\s+value="(\d+)"', seite)
    assert treffer, "Das Formular führt keine Version mit"
    return treffer.group(1)


def test_formular_zeigt_active_tab_und_bestehende_werte(bestand):
    antwort = client.get(f"/auftrag/{AUFTRAG_ID}/projektrahmen")
    assert antwort.status_code == 200
    assert 'class="active"' in antwort.text
    assert "Projektrahmen" in antwort.text


def test_rahmenbedingungen_werden_gespeichert(bestand):
    stand = _version_im_formular(client.get(f"/auftrag/{AUFTRAG_ID}/projektrahmen").text)

    antwort = client.post(
        f"/auftrag/{AUFTRAG_ID}/projektrahmen",
        data={
            "version": stand,
            "benoetigte_zugaenge": "VPN-Zugang, Domänen-Konto",
            "zutrittsregelung": "Anmeldung am Empfang",
            "nda_vorhanden": "ja",
            "wartungsfenster_einschraenkungen": "nur nachts",
            "analysewerkzeuge": "nur passive Erfassung",
        },
        follow_redirects=False,
    )
    assert antwort.status_code == 303

    auftrag = bestand.load_auftrag(AUFTRAG_ID)
    assert auftrag.rahmenbedingungen.benoetigte_zugaenge == "VPN-Zugang, Domänen-Konto"
    assert auftrag.rahmenbedingungen.zutrittsregelung == "Anmeldung am Empfang"
    assert auftrag.rahmenbedingungen.nda_vorhanden == "ja"
    assert auftrag.rahmenbedingungen.wartungsfenster_einschraenkungen == "nur nachts"
    assert auftrag.rahmenbedingungen.analysewerkzeuge == "nur passive Erfassung"


def test_ergebnisartefakte_und_aspekte_werden_ueber_listen_gespeichert(bestand):
    stand = _version_im_formular(client.get(f"/auftrag/{AUFTRAG_ID}/projektrahmen").text)

    antwort = client.post(
        f"/auftrag/{AUFTRAG_ID}/projektrahmen",
        data={
            "version": stand,
            "artefakt_bezeichnung_0": "Analysebericht 2026",
            "artefakt_typ_0": "Analysebericht",
            "artefakt_status_0": "in Arbeit",
            "positiv_titel_0": "Patchstand vorbildlich",
            "positiv_text_0": "Alle Systeme aktuell gepatcht angetroffen.",
            "negativ_titel_0": "Serverraum unaufgeräumt",
            "negativ_text_0": "Kabel liegen offen im Gang, wirkt vernachlässigt.",
        },
        follow_redirects=False,
    )
    assert antwort.status_code == 303

    auftrag = bestand.load_auftrag(AUFTRAG_ID)
    assert len(auftrag.ergebnisartefakte) == 1
    assert auftrag.ergebnisartefakte[0].bezeichnung == "Analysebericht 2026"
    assert auftrag.ergebnisartefakte[0].typ == "Analysebericht"
    assert auftrag.ergebnisartefakte[0].status == "in Arbeit"

    assert len(auftrag.positive_aspekte) == 1
    assert auftrag.positive_aspekte[0].titel == "Patchstand vorbildlich"

    assert len(auftrag.negative_aspekte) == 1
    assert auftrag.negative_aspekte[0].titel == "Serverraum unaufgeräumt"


def test_leere_zeilen_der_aspekt_listen_werden_nicht_gespeichert(bestand):
    """Wer eine Zeile hinzufügt und dann nichts einträgt, soll keinen leeren
    Datensatz hinterlassen (siehe `parse_unterobjekte`)."""
    stand = _version_im_formular(client.get(f"/auftrag/{AUFTRAG_ID}/projektrahmen").text)

    antwort = client.post(
        f"/auftrag/{AUFTRAG_ID}/projektrahmen",
        data={
            "version": stand,
            "positiv_titel_0": "",
            "positiv_text_0": "",
        },
        follow_redirects=False,
    )
    assert antwort.status_code == 303
    auftrag = bestand.load_auftrag(AUFTRAG_ID)
    assert auftrag.positive_aspekte == []


def test_zweiter_benutzer_ueberschreibt_den_ersten_nicht(bestand):
    a = client.get(f"/auftrag/{AUFTRAG_ID}/projektrahmen")
    b = client.get(f"/auftrag/{AUFTRAG_ID}/projektrahmen")
    stand = _version_im_formular(a.text)
    assert _version_im_formular(b.text) == stand

    antwort_a = client.post(
        f"/auftrag/{AUFTRAG_ID}/projektrahmen",
        data={"version": stand, "analysewerkzeuge": "Von A"},
        follow_redirects=False,
    )
    assert antwort_a.status_code == 303
    assert bestand.load_auftrag(AUFTRAG_ID).rahmenbedingungen.analysewerkzeuge == "Von A"

    antwort_b = client.post(
        f"/auftrag/{AUFTRAG_ID}/projektrahmen",
        data={"version": stand, "analysewerkzeuge": "Von B"},
        follow_redirects=False,
    )
    assert antwort_b.status_code == 409
    assert "Nicht gespeichert" in antwort_b.text
    assert bestand.load_auftrag(AUFTRAG_ID).rahmenbedingungen.analysewerkzeuge == "Von A"


def test_konflikt_liefert_eingegebene_werte_zurueck(bestand):
    stand = _version_im_formular(client.get(f"/auftrag/{AUFTRAG_ID}/projektrahmen").text)

    client.post(
        f"/auftrag/{AUFTRAG_ID}/projektrahmen",
        data={"version": stand, "analysewerkzeuge": "Von A"},
        follow_redirects=False,
    )
    antwort = client.post(
        f"/auftrag/{AUFTRAG_ID}/projektrahmen",
        data={
            "version": stand,
            "positiv_titel_0": "Muehsam getippter Titel von B",
            "positiv_text_0": "Text von B",
        },
        follow_redirects=False,
    )
    assert antwort.status_code == 409
    assert "Muehsam getippter Titel von B" in antwort.text


def test_ohne_mitgefuehrte_version_bleibt_es_beim_bisherigen_verhalten(bestand):
    ziel = f"/auftrag/{AUFTRAG_ID}/projektrahmen"
    client.post(ziel, data={"version": "1", "analysewerkzeuge": "Von A"}, follow_redirects=False)

    ohne_feld = client.post(ziel, data={"analysewerkzeuge": "Ohne Version"}, follow_redirects=False)
    assert ohne_feld.status_code == 303
    assert bestand.load_auftrag(AUFTRAG_ID).rahmenbedingungen.analysewerkzeuge == "Ohne Version"


# ── Anbindung an den Bericht ──────────────────────────────────────────────

def test_beobachtungen_landen_im_bericht():
    """`positive_aspekte`/`negative_aspekte` müssen in
    `report_builder.build_analysebericht` als eigener Abschnitt erscheinen,
    getrennt von den automatisch erzeugten Findings — sonst bleibt das
    Formular folgenlos (Karte #316)."""
    from app.services.report_builder import ReportBuilder
    from app.services.evaluator import evaluator_service
    from app.models.auftrag import Aspekt

    rb = ReportBuilder()
    auftrag = Auftrag(
        id="a-bericht",
        projekt_nummer="P-316",
        kunde="Bericht GmbH",
        bezeichnung="Bericht-Test",
        positive_aspekte=[Aspekt(titel="Patchstand vorbildlich", text="Alles aktuell.")],
        negative_aspekte=[Aspekt(titel="Serverraum unaufgeräumt", text="Wirkt vernachlässigt.")],
    )
    bew = evaluator_service.evaluate_auftrag([], [])

    report = rb.build_analysebericht(auftrag, [], [], [], bew, [], ziel_vertraulichkeit="kundentauglich")

    assert "## Anhang: Beobachtungen vor Ort" in report
    assert "### Positive Beobachtungen" in report
    assert "Patchstand vorbildlich" in report
    assert "### Negative Beobachtungen" in report
    assert "Serverraum unaufgeräumt" in report


def test_beobachtungen_fehlen_in_der_anonymisierten_fassung():
    """Freitext-Beobachtungen können leicht auf den Kunden schliessen lassen —
    dieselbe Zurückhaltung wie bei der Vertragsübersicht."""
    from app.services.report_builder import ReportBuilder
    from app.services.evaluator import evaluator_service
    from app.models.auftrag import Aspekt

    rb = ReportBuilder()
    auftrag = Auftrag(
        id="a-bericht-anon",
        projekt_nummer="P-316",
        kunde="Bericht GmbH",
        bezeichnung="Bericht-Test",
        positive_aspekte=[Aspekt(titel="Patchstand vorbildlich", text="Alles aktuell.")],
    )
    bew = evaluator_service.evaluate_auftrag([], [])

    report = rb.build_analysebericht(auftrag, [], [], [], bew, [], ziel_vertraulichkeit="anonymisiert")

    assert "Beobachtungen vor Ort" not in report


def test_kein_abschnitt_ohne_beobachtungen():
    from app.services.report_builder import ReportBuilder
    from app.services.evaluator import evaluator_service

    rb = ReportBuilder()
    auftrag = Auftrag(id="a-leer", projekt_nummer="P-316", kunde="Leer GmbH", bezeichnung="Leer-Test")
    bew = evaluator_service.evaluate_auftrag([], [])

    report = rb.build_analysebericht(auftrag, [], [], [], bew, [], ziel_vertraulichkeit="kundentauglich")

    assert "Beobachtungen vor Ort" not in report
