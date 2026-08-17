import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.auftrag import Auftrag, VersionsEintrag
from app.services.report_builder import ReportBuilder
from app.services.storage import storage

client = TestClient(app)
AUFTRAG_ID = "auf-vers-test"


@pytest.fixture(autouse=True)
def temp_storage(tmp_path):
    old_dir = storage.data_dir
    storage.data_dir = tmp_path
    yield
    storage.data_dir = old_dir


@pytest.fixture
def test_auftrag():
    a = Auftrag(
        id=AUFTRAG_ID,
        projekt_nummer="PRJ-2026-VERS",
        kunde="Musterfirma GmbH",
        bezeichnung="Versionierungstest",
        aktive_bausteine=["firewall"],
    )
    storage.save_auftrag(a)
    return a


def test_aktuelle_berichts_version_property():
    a = Auftrag(id="a1", kunde="Test", bezeichnung="Test")
    assert a.aktuelle_berichts_version == "v0.1"

    a.versionshistorie = [
        VersionsEintrag(version="0.1", datum="2026-08-01", autor="Marcel", beschreibung="Erstanalyse"),
        VersionsEintrag(version="0.2", datum="2026-08-10", autor="Marcel", beschreibung="Nebenstandorte"),
        VersionsEintrag(version="v1.0", datum="2026-08-17", autor="Marcel", beschreibung="Final"),
    ]
    assert a.aktuelle_berichts_version == "v1.0"


def test_versionierung_form_get_and_post_flow(test_auftrag):
    # 1. GET auf leeres Formular
    resp = client.get(f"/auftrag/{AUFTRAG_ID}/versionierung")
    assert resp.status_code == 200
    assert "Versionierung &amp; Dokumentenhistorie" in resp.text
    assert "v0.1" in resp.text

    # 2. POST mit 3 Versionen
    post_data = {
        "ver_version_0": "0.1",
        "ver_datum_0": "2026-08-01",
        "ver_autor_0": "Marcel Russlies",
        "ver_status_0": "Entwurf",
        "ver_beschreibung_0": "Analyse Hauptstandort",
        "ver_version_1": "0.2",
        "ver_datum_1": "2026-08-10",
        "ver_autor_1": "Marcel Russlies",
        "ver_status_1": "In Prüfung",
        "ver_beschreibung_1": "Analyse Nebenstandort",
        "ver_version_2": "1.0",
        "ver_datum_2": "2026-08-17",
        "ver_autor_2": "Marcel Russlies",
        "ver_status_2": "Freigegeben",
        "ver_beschreibung_2": "Finalisierung",
    }
    post_resp = client.post(
        f"/auftrag/{AUFTRAG_ID}/versionierung",
        data=post_data,
        follow_redirects=False,
    )
    assert post_resp.status_code == 303

    # 3. Aus Storage laden und prüfen
    gespeichert = storage.load_auftrag(AUFTRAG_ID)
    assert len(gespeichert.versionshistorie) == 3
    assert gespeichert.versionshistorie[0].version == "0.1"
    assert gespeichert.versionshistorie[0].beschreibung == "Analyse Hauptstandort"
    assert gespeichert.versionshistorie[1].version == "0.2"
    assert gespeichert.versionshistorie[2].version == "1.0"
    assert gespeichert.versionshistorie[2].status == "Freigegeben"
    assert gespeichert.aktuelle_berichts_version == "v1.0"

    # 4. Formular erneut laden
    get_resp = client.get(f"/auftrag/{AUFTRAG_ID}/versionierung")
    assert get_resp.status_code == 200
    assert 'value="Analyse Hauptstandort"' in get_resp.text
    assert 'value="Finalisierung"' in get_resp.text
    assert 'value="Freigegeben" selected' in get_resp.text


def test_versionierung_skips_empty_rows(test_auftrag):
    # Leere Zeilen dürfen nicht gespeichert werden
    post_resp = client.post(
        f"/auftrag/{AUFTRAG_ID}/versionierung",
        data={
            "ver_version_0": "",
            "ver_autor_0": "",
            "ver_beschreibung_0": "",
        },
        follow_redirects=False,
    )
    assert post_resp.status_code == 303
    gespeichert = storage.load_auftrag(AUFTRAG_ID)
    assert gespeichert.versionshistorie == []


def test_versionierung_konflikt_erkennung(test_auftrag):
    stand = storage.load_auftrag(AUFTRAG_ID).version
    # Benutzer A speichert
    client.post(
        f"/auftrag/{AUFTRAG_ID}/versionierung",
        data={"version": str(stand)},
        follow_redirects=False,
    )

    # Benutzer B sendet veraltete Version
    antwort = client.post(
        f"/auftrag/{AUFTRAG_ID}/versionierung",
        data={
            "version": str(stand),
            "ver_version_0": "0.5",
            "ver_beschreibung_0": "Nicht verlorene Version",
        },
        follow_redirects=False,
    )
    assert antwort.status_code == 409
    assert "Nicht verlorene Version" in antwort.text


def test_report_builder_includes_dokumentenhistorie_table(test_auftrag):
    test_auftrag.versionshistorie = [
        VersionsEintrag(version="0.1", datum="01.08.2026", autor="Marcel", status="Entwurf", beschreibung="Erstanalyse"),
        VersionsEintrag(version="1.0", datum="17.08.2026", autor="Marcel", status="Freigegeben", beschreibung="Finalisierung"),
    ]
    rb = ReportBuilder()
    from app.services.evaluator import evaluator_service
    bew = evaluator_service.evaluate_auftrag([], [])
    rep = rb.build_analysebericht(test_auftrag, [], [], [], bew, [], ziel_vertraulichkeit="kundentauglich")

    assert "**Version:** v1.0" in rep
    assert "## Dokumentenhistorie" in rep
    assert "| 0.1 | 01.08.2026 | Marcel | Entwurf | Erstanalyse |" in rep
    assert "| 1.0 | 17.08.2026 | Marcel | Freigegeben | Finalisierung |" in rep


def test_report_builder_anonymizes_author_in_dokumentenhistorie(test_auftrag):
    test_auftrag.versionshistorie = [
        VersionsEintrag(version="1.0", datum="17.08.2026", autor="Marcel Russlies", status="Freigegeben", beschreibung="Finalisierung"),
    ]
    rb = ReportBuilder()
    from app.services.evaluator import evaluator_service
    bew = evaluator_service.evaluate_auftrag([], [])
    rep = rb.build_analysebericht(test_auftrag, [], [], [], bew, [], ziel_vertraulichkeit="anonymisiert")

    assert "[ANONYMISIERT]" in rep
    assert "Marcel Russlies" not in rep
    assert "| 1.0 | 17.08.2026 | [ANONYMISIERT] | Freigegeben | Finalisierung |" in rep
