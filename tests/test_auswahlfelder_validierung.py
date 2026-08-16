"""Tests zu Karte #309: Auswahlfelder werden serverseitig geprüft.

Das Dropdown im Browser lässt nichts Ungültiges zu — ein POST an die Route
schon. Vorher schrieben `create_auftrag()` und `stammdaten_submit()` die Werte
von `grundlage`, `status` und `vertraulichkeit_default` ungeprüft ins Modell,
und dieselbe Lücke gab es bei `vertraulichkeit` an Standort und Technik-Objekt.

Die Regel, die hier festgehalten wird: **ein unbekannter Wert wird verworfen.**
Beim Bearbeiten bleibt der gespeicherte Wert stehen (ein fehlerhafter POST
überschreibt nichts), beim Neuanlegen greift der Vorgabewert — bei der
Vertraulichkeit also "intern", die schützende Stufe (#310).
"""

import pytest
from fastapi.testclient import TestClient

from app.config import BASE_DIR
from app.main import app
from app.web.optionen import (
    GRUNDLAGE_OPTIONS,
    STATUS_OPTIONS,
    VERTRAULICHKEIT_OPTIONS,
    gueltiger_wert,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def temp_storage(tmp_path):
    from app.services.storage import storage
    old_dir = storage.data_dir
    storage.data_dir = tmp_path
    yield
    storage.data_dir = old_dir


def _auftrag_anlegen(**felder) -> str:
    daten = {"kunde": "Test GmbH", "bezeichnung": "Karte 309"}
    daten.update(felder)
    res = client.post("/auftrag/neu", data=daten, follow_redirects=True)
    assert res.status_code == 200
    return "auf-karte-309"


# ── Der Prüfhelfer selbst ───────────────────────────────────────────────

def test_gueltiger_wert_laesst_bekannte_werte_durch():
    assert gueltiger_wert("Analyse", GRUNDLAGE_OPTIONS, "Sonstiges") == "Analyse"


def test_gueltiger_wert_ersetzt_unbekannte_durch_rueckfall():
    assert gueltiger_wert("Erfundenes", GRUNDLAGE_OPTIONS, "Sonstiges") == "Sonstiges"


def test_gueltiger_wert_prueft_exakt():
    """Kein Trimmen, keine Gross-/Kleinschreibungs-Toleranz: die Werte kommen
    aus einem `<select>`, das genau diese Zeichenketten liefert. Wer hier
    grosszuegig wird, laesst am Ende doch wieder Varianten in die Ablage."""
    assert gueltiger_wert("analyse", GRUNDLAGE_OPTIONS, "Sonstiges") == "Sonstiges"
    assert gueltiger_wert(" Analyse ", GRUNDLAGE_OPTIONS, "Sonstiges") == "Sonstiges"
    assert gueltiger_wert("", GRUNDLAGE_OPTIONS, "Sonstiges") == "Sonstiges"


# ── Auftrag anlegen ─────────────────────────────────────────────────────

def test_neuanlage_verwirft_unbekannte_grundlage():
    from app.services.storage import storage

    auftrag_id = _auftrag_anlegen(grundlage="Schnapsidee")
    assert storage.load_auftrag(auftrag_id).grundlage == "Sonstiges"


def test_neuanlage_verwirft_unbekannte_vertraulichkeit():
    """Der entscheidende Fall: ein Tippfehler darf den Datensatz nicht in eine
    freizuegigere Stufe befoerdern. Der Rueckfall ist "intern"."""
    from app.services.storage import storage

    auftrag_id = _auftrag_anlegen(vertraulichkeit_default="kundentauglcih")
    assert storage.load_auftrag(auftrag_id).vertraulichkeit_default == "intern"


# ── Stammdaten bearbeiten ───────────────────────────────────────────────

def test_stammdaten_behalten_bisherigen_wert_bei_unbekannter_eingabe():
    from app.services.storage import storage

    auftrag_id = _auftrag_anlegen(grundlage="Analyse",
                                  vertraulichkeit_default="anonymisiert")
    res = client.post(f"/auftrag/{auftrag_id}/stammdaten", data={
        "kunde": "Test GmbH",
        "bezeichnung": "Karte 309",
        "grundlage": "Schnapsidee",
        "status": "Erfunden",
        "vertraulichkeit_default": "oeffentlich",
    }, follow_redirects=True)
    assert res.status_code == 200

    auftrag = storage.load_auftrag(auftrag_id)
    assert auftrag.grundlage == "Analyse"
    assert auftrag.status == "Vorbereitung"
    assert auftrag.vertraulichkeit_default == "anonymisiert"


def test_stammdaten_speichern_trotz_eines_ungueltigen_feldes_den_rest():
    """Ein ungueltiger Wert in einem Feld darf nicht das ganze Formular
    verwerfen — sonst gehen die uebrigen Eingaben still verloren."""
    from app.services.storage import storage

    auftrag_id = _auftrag_anlegen()
    client.post(f"/auftrag/{auftrag_id}/stammdaten", data={
        "kunde": "Neuer Kunde GmbH",
        "bezeichnung": "Karte 309",
        "grundlage": "Schnapsidee",
    }, follow_redirects=True)

    assert storage.load_auftrag(auftrag_id).kunde == "Neuer Kunde GmbH"


def test_status_route_ignoriert_unbekannten_status():
    from app.services.storage import storage

    auftrag_id = _auftrag_anlegen()
    client.post(f"/auftrag/{auftrag_id}/status", data={"status": "Erfunden"},
                follow_redirects=True)
    assert storage.load_auftrag(auftrag_id).status == "Vorbereitung"


def test_vertraulichkeits_route_ignoriert_unbekannte_stufe():
    from app.services.storage import storage

    auftrag_id = _auftrag_anlegen(vertraulichkeit_default="anonymisiert")
    client.post(f"/auftrag/{auftrag_id}/vertraulichkeit",
                data={"vertraulichkeit_default": "oeffentlich"},
                follow_redirects=True)
    assert storage.load_auftrag(auftrag_id).vertraulichkeit_default == "anonymisiert"


# ── Standort und Technik-Objekt ─────────────────────────────────────────

def test_neuer_standort_verwirft_unbekannte_vertraulichkeit():
    from app.services.storage import storage

    auftrag_id = _auftrag_anlegen(vertraulichkeit_default="anonymisiert")
    client.post(f"/auftrag/{auftrag_id}/standort/neu", data={
        "bezeichnung": "Zentrale",
        "vertraulichkeit": "oeffentlich",
    }, follow_redirects=True)

    standort = storage.load_standort(auftrag_id, "sto-zentrale")
    assert standort.vertraulichkeit == "anonymisiert"


def test_neues_objekt_verwirft_unbekannte_vertraulichkeit():
    from app.services.storage import storage

    auftrag_id = _auftrag_anlegen(vertraulichkeit_default="anonymisiert")
    client.post(f"/auftrag/{auftrag_id}/standort/neu", data={"bezeichnung": "Zentrale"},
                follow_redirects=True)
    client.post(f"/auftrag/{auftrag_id}/objekt/neu", data={
        "typ": "firewall",
        "bezeichnung": "Perimeter FW",
        "standort_id": "sto-zentrale",
        "vertraulichkeit": "oeffentlich",
    }, follow_redirects=True)

    objekte = storage.list_objekte(auftrag_id, typ="firewall")
    assert len(objekte) == 1
    assert objekte[0].vertraulichkeit == "anonymisiert"


# ── Zentralisierung ─────────────────────────────────────────────────────

def test_vertraulichkeitsstufen_stehen_nicht_mehr_literal_in_templates():
    """Gegenstueck zum gleichnamigen Test fuer GRUNDLAGE_OPTIONS (#302): sobald
    ein Template die Liste wieder selbst aufzaehlt, koennen Auswahl und
    serverseitige Pruefung auseinanderlaufen."""
    template_dir = BASE_DIR / "app" / "templates"
    for pfad in sorted(template_dir.rglob("*.html")):
        inhalt = pfad.read_text(encoding="utf-8")
        assert '"intern", "kundentauglich"' not in inhalt, \
            f"{pfad.name} zaehlt die Stufen wieder selbst auf"


def test_optionslisten_decken_sich_mit_der_exporter_logik():
    """Die Stufen hier und die von `VertraulichkeitsStufe.parse()` erkannten
    muessen dieselben sein — sonst bietet das Formular etwas an, das der Export
    nicht kennt und auf seinen Rueckfallwert abbildet."""
    from app.services.exporter import VertraulichkeitsStufe

    assert set(VERTRAULICHKEIT_OPTIONS) == {
        stufe.name.lower() for stufe in VertraulichkeitsStufe
    }


def test_status_und_grundlage_haben_genau_eine_quelle():
    """Die Listen wurden aus `routes_auftrag.py` nach `optionen.py` gezogen.
    Der Re-Import dort bleibt bestehen, damit aeltere Tests weiter laufen."""
    from app.web import routes_auftrag

    assert routes_auftrag.STATUS_OPTIONS is STATUS_OPTIONS
    assert routes_auftrag.GRUNDLAGE_OPTIONS is GRUNDLAGE_OPTIONS
