"""Der Sidebar-Eintrag „Übersicht & Erfassung" ist in zwei Menüpunkte geteilt (#306):
„Übersicht" zeigt nur die Kennzahlen, „Erfassung" nur die Arbeitsfläche mit Standorten,
Bausteinauswahl und Objekten. Diese Tests halten die Trennung fest — inklusive der
Zusage, dass `/auftrag/{id}` weiterhin funktioniert."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def temp_storage(tmp_path):
    from app.services.storage import storage
    old_dir = storage.data_dir
    storage.data_dir = tmp_path
    yield
    storage.data_dir = old_dir


@pytest.fixture
def auftrag_id():
    """Auftrag mit einem Standort und einem Objekt, damit auf beiden Seiten
    tatsächlich etwas anzuzeigen wäre."""
    client.post("/auftrag/neu", data={
        "projekt_nummer": "PROJ-306",
        "kunde": "Trennungskunde",
        "bezeichnung": "Trennung Uebersicht Erfassung",
        "aktive_bausteine": ["firewall"],
    }, follow_redirects=False)
    aid = "auf-trennung-uebersicht-erfassung"

    client.post(f"/auftrag/{aid}/standort/neu", data={
        "bezeichnung": "Verwaltungsgebäude",
        "anzahl_user": 12,
    }, follow_redirects=False)
    client.post(f"/auftrag/{aid}/objekt/neu?typ=firewall", data={
        "bezeichnung": "Perimeter-Firewall",
        "standort_id": "sto-verwaltungsgebaeude",
    }, follow_redirects=False)
    return aid


def test_uebersicht_bleibt_unter_der_alten_adresse_erreichbar(auftrag_id):
    """Die Route wird aus der Auftragsliste, den Breadcrumbs und diversen
    Weiterleitungen verlinkt und darf deshalb nicht wegfallen."""
    res = client.get(f"/auftrag/{auftrag_id}")
    assert res.status_code == 200
    assert "Trennung Uebersicht Erfassung" in res.text


def test_uebersicht_zeigt_die_vier_kennzahlen(auftrag_id):
    res = client.get(f"/auftrag/{auftrag_id}")
    assert res.status_code == 200
    for kachel in ("Gesamtbewertung", "Feldabdeckung", "Offene Punkte", "Findings"):
        assert kachel in res.text


def test_uebersicht_zeigt_keine_erfassungsflaeche(auftrag_id):
    """Standort-Karten, Baustein-Menü und Objekttabelle gehören auf die Erfassung."""
    res = client.get(f"/auftrag/{auftrag_id}")
    assert "Baustein wählen" not in res.text
    assert "Mehrere Objekte" not in res.text
    assert "Perimeter-Firewall" not in res.text


def test_erfassung_zeigt_standorte_bausteine_und_objekte(auftrag_id):
    res = client.get(f"/auftrag/{auftrag_id}/erfassung")
    assert res.status_code == 200
    assert "Verwaltungsgebäude" in res.text
    assert "Baustein wählen" in res.text
    assert "Perimeter-Firewall" in res.text
    assert f"/auftrag/{auftrag_id}/standort/neu" in res.text


def test_erfassung_zeigt_keine_kennzahlen(auftrag_id):
    """Die Kennzahlen-Kacheln bleiben der Übersicht vorbehalten."""
    res = client.get(f"/auftrag/{auftrag_id}/erfassung")
    assert "Gesamtbewertung" not in res.text
    assert "Feldabdeckung" not in res.text


def test_erfassung_berechnet_keine_gesamtbewertung(auftrag_id, monkeypatch):
    """Der teuerste Aufruf der alten Route darf auf der Erfassungsseite nicht mehr
    stattfinden — sonst ist die Aufteilung nur kosmetisch."""
    from app.web import routes_auftrag

    def _explode(*args, **kwargs):
        raise AssertionError("evaluate_auftrag gehört nicht auf die Erfassungsseite")

    monkeypatch.setattr(routes_auftrag.evaluator_service, "evaluate_auftrag", _explode)
    res = client.get(f"/auftrag/{auftrag_id}/erfassung")
    assert res.status_code == 200


def test_beide_menuepunkte_stehen_in_der_sidebar(auftrag_id):
    for pfad, aktiv, inaktiv in (
        (f"/auftrag/{auftrag_id}", "erfassung", "uebersicht"),
        (f"/auftrag/{auftrag_id}/erfassung", "uebersicht", "erfassung"),
    ):
        res = client.get(pfad)
        assert f'href="/auftrag/{auftrag_id}"' in res.text
        assert f'href="/auftrag/{auftrag_id}/erfassung"' in res.text
        assert ">Übersicht<" in res.text
        assert ">Erfassung<" in res.text


def test_sidebar_fortschritt_erscheint_auf_beiden_seiten(auftrag_id):
    """build_sidebar_context() muss auf beiden Seiten eingebunden sein."""
    for pfad in (f"/auftrag/{auftrag_id}", f"/auftrag/{auftrag_id}/erfassung"):
        res = client.get(pfad)
        assert "Aktive Bausteine" in res.text


def test_erfassung_unbekannter_auftrag_leitet_auf_die_liste(auftrag_id):
    res = client.get("/auftrag/gibt-es-nicht/erfassung", follow_redirects=False)
    assert res.status_code == 303
    assert res.headers["location"] == "/auftrag"


def test_objekt_speichern_landet_auf_der_erfassung(auftrag_id):
    """Nach dem Speichern arbeitet man weiter — also zurück auf die Arbeitsfläche."""
    res = client.post(f"/auftrag/{auftrag_id}/objekt/neu?typ=firewall", data={
        "bezeichnung": "Zweite Firewall",
        "standort_id": "sto-verwaltungsgebaeude",
    }, follow_redirects=False)
    assert res.status_code == 303
    # Query-Param "gespeichert" triggert den Toast (#427) — Pfad zaehlt hier, nicht die Query.
    assert res.headers["location"].split("?")[0] == f"/auftrag/{auftrag_id}/erfassung"


def test_standort_speichern_landet_auf_der_erfassung(auftrag_id):
    res = client.post(f"/auftrag/{auftrag_id}/standort/neu", data={
        "bezeichnung": "Aussenstelle",
        "anzahl_user": 4,
    }, follow_redirects=False)
    assert res.status_code == 303
    assert res.headers["location"] == f"/auftrag/{auftrag_id}/erfassung"


def test_objekt_loeschen_landet_auf_der_erfassung(auftrag_id):
    from app.services.storage import storage
    obj = storage.list_objekte(auftrag_id)[0]
    res = client.post(
        f"/auftrag/{auftrag_id}/objekt/{obj.typ}/{obj.id}/loeschen",
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert res.headers["location"] == f"/auftrag/{auftrag_id}/erfassung"
