"""Tests für Karte #316 (Teil D): vier bislang tote Felder auf der Stammdaten-Seite
(`zweck`, `abgrenzung`, `aufwand_geplant`, `aufwand_ist`) sowie zwei tote Felder
auf der Unternehmenskontext-Seite (`geschaeftskritische_systeme`,
`geplante_aenderungen`).

Die beiden Unternehmenskontext-Felder werden von `ReportBuilder` bereits
gelesen (Zeilen 82/87) — ohne ein Formular dafür blieben die zugehörigen
Berichtsabschnitte zwangsläufig leer. Ein Test hält deshalb ausdrücklich fest,
dass erfasste Einträge im Analysebericht landen.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.auftrag import Auftrag, Aspekt, GeplanteAenderung
from app.services.report_builder import ReportBuilder
from app.web.optionen import ZWECK_OPTIONS

client = TestClient(app)

AUFTRAG_ID = "auf-316d-test"


@pytest.fixture(autouse=True)
def temp_storage(tmp_path):
    from app.services.storage import storage
    old_dir = storage.data_dir
    storage.data_dir = tmp_path
    yield
    storage.data_dir = old_dir


@pytest.fixture
def auftrag():
    from app.services.storage import storage
    a = Auftrag(
        id=AUFTRAG_ID,
        projekt_nummer="auf-2026-316d",
        kunde="Testkunde GmbH",
        bezeichnung="316d-Testauftrag",
        aktive_bausteine=["firewall"],
    )
    storage.save_auftrag(a)
    return storage


# ── Stammdaten: zweck, abgrenzung, aufwand_geplant, aufwand_ist ──────────

def test_stammdaten_form_bietet_alle_zweck_optionen_an(auftrag):
    antwort = client.get(f"/auftrag/{AUFTRAG_ID}/stammdaten")
    for opt in ZWECK_OPTIONS:
        assert f'value="{opt}"' in antwort.text


def test_stammdaten_speichert_die_vier_neuen_felder(auftrag):
    antwort = client.post(
        f"/auftrag/{AUFTRAG_ID}/stammdaten",
        data={
            "kunde": "Testkunde GmbH",
            "bezeichnung": "316d-Testauftrag",
            "zweck": ["Migrationsvorbereitung", "Optimierung"],
            "abgrenzung": "Ohne Telefonanlage und Client-Software.",
            "aufwand_geplant": "12,5",
            "aufwand_ist": "3,25",
        },
        follow_redirects=False,
    )
    assert antwort.status_code == 303

    gespeichert = auftrag.load_auftrag(AUFTRAG_ID)
    assert set(gespeichert.zweck) == {"Migrationsvorbereitung", "Optimierung"}
    assert gespeichert.abgrenzung == "Ohne Telefonanlage und Client-Software."
    # Deutsches Zahlformat (Komma statt Punkt) muss funktionieren.
    assert gespeichert.aufwand_geplant == 12.5
    assert gespeichert.aufwand_ist == 3.25


def test_stammdaten_verwirft_unbekannte_zweck_werte(auftrag):
    """Wie bei den anderen Auswahlfeldern (#309): ein manipulierter POST darf
    keinen Wert speichern, den das Dropdown nie angeboten hat."""
    antwort = client.post(
        f"/auftrag/{AUFTRAG_ID}/stammdaten",
        data={
            "kunde": "Testkunde GmbH",
            "bezeichnung": "316d-Testauftrag",
            "zweck": ["Optimierung", "Erfundener-Zweck"],
        },
        follow_redirects=False,
    )
    assert antwort.status_code == 303
    gespeichert = auftrag.load_auftrag(AUFTRAG_ID)
    assert gespeichert.zweck == ["Optimierung"]


def test_stammdaten_speichern_laesst_unternehmenskontext_unangetastet(auftrag):
    """Die Seiten sind bewusst getrennt (Docstring von stammdaten_submit) —
    ein Speichern der Stammdaten darf den Unternehmenskontext nicht leeren."""
    a = auftrag.load_auftrag(AUFTRAG_ID)
    a.unternehmenskontext.geschaeftskritische_systeme = [Aspekt(titel="ERP", text="SAP")]
    a.unternehmenskontext.kerngeschaeft = "Maschinenbau"
    auftrag.save_auftrag(a)

    client.post(
        f"/auftrag/{AUFTRAG_ID}/stammdaten",
        data={"kunde": "Testkunde GmbH", "bezeichnung": "316d-Testauftrag"},
        follow_redirects=False,
    )

    gespeichert = auftrag.load_auftrag(AUFTRAG_ID)
    assert gespeichert.unternehmenskontext.kerngeschaeft == "Maschinenbau"
    assert len(gespeichert.unternehmenskontext.geschaeftskritische_systeme) == 1
    assert gespeichert.unternehmenskontext.geschaeftskritische_systeme[0].titel == "ERP"


def test_stammdaten_konflikt_gibt_die_neuen_felder_zurueck(auftrag):
    """Bei einem Konflikt (#308) dürfen die vier neuen Felder nicht
    verlorengehen — sonst müsste der Benutzer sie neu eintragen."""
    stand = auftrag.load_auftrag(AUFTRAG_ID).version
    client.post(
        f"/auftrag/{AUFTRAG_ID}/stammdaten",
        data={"kunde": "Testkunde GmbH", "bezeichnung": "316d-Testauftrag", "version": str(stand)},
        follow_redirects=False,
    )

    antwort = client.post(
        f"/auftrag/{AUFTRAG_ID}/stammdaten",
        data={
            "kunde": "Testkunde GmbH",
            "bezeichnung": "316d-Testauftrag",
            "version": str(stand),
            "zweck": ["Notfalldokumentation"],
            "abgrenzung": "Muehsam getippte Abgrenzung von B",
            "aufwand_geplant": "7,5",
        },
        follow_redirects=False,
    )
    assert antwort.status_code == 409
    assert "Muehsam getippte Abgrenzung von B" in antwort.text
    assert 'value="Notfalldokumentation" checked' in antwort.text
    assert 'value="7.5"' in antwort.text


# ── Unternehmenskontext: geschaeftskritische_systeme, geplante_aenderungen ──

def test_unternehmenskontext_speichert_beide_aspekt_listen(auftrag):
    antwort = client.post(
        f"/auftrag/{AUFTRAG_ID}/unternehmenskontext",
        data={
            "system_titel_0": "ERP-System",
            "system_text_0": "SAP S/4HANA, zentral gehostet.",
            "system_titel_1": "Warenwirtschaft",
            "system_text_1": "Individualsoftware, Betrieb beim Kunden.",
            "aenderung_titel_0": "Serverumzug",
            "aenderung_text_0": "Migration ins neue Rechenzentrum Q3.",
        },
        follow_redirects=False,
    )
    assert antwort.status_code == 303

    gespeichert = auftrag.load_auftrag(AUFTRAG_ID)
    systeme = gespeichert.unternehmenskontext.geschaeftskritische_systeme
    aenderungen = gespeichert.unternehmenskontext.geplante_aenderungen

    assert len(systeme) == 2
    assert systeme[0].titel == "ERP-System"
    assert systeme[0].text == "SAP S/4HANA, zentral gehostet."
    assert systeme[1].titel == "Warenwirtschaft"

    assert len(aenderungen) == 1
    assert aenderungen[0].titel == "Serverumzug"
    assert aenderungen[0].text == "Migration ins neue Rechenzentrum Q3."


def test_unternehmenskontext_leere_zeilen_werden_nicht_gespeichert(auftrag):
    """Wer eine Zeile hinzufügt und nichts einträgt, soll keinen leeren
    Datensatz hinterlassen (siehe Docstring von parse_unterobjekte)."""
    antwort = client.post(
        f"/auftrag/{AUFTRAG_ID}/unternehmenskontext",
        data={"system_titel_0": "", "system_text_0": ""},
        follow_redirects=False,
    )
    assert antwort.status_code == 303
    gespeichert = auftrag.load_auftrag(AUFTRAG_ID)
    assert gespeichert.unternehmenskontext.geschaeftskritische_systeme == []


def test_unternehmenskontext_form_zeigt_bestehende_eintraege(auftrag):
    a = auftrag.load_auftrag(AUFTRAG_ID)
    a.unternehmenskontext.geschaeftskritische_systeme = [Aspekt(titel="ERP", text="SAP")]
    a.unternehmenskontext.geplante_aenderungen = [Aspekt(titel="Umzug", text="Neues RZ")]
    auftrag.save_auftrag(a)

    antwort = client.get(f"/auftrag/{AUFTRAG_ID}/unternehmenskontext")
    assert 'name="system_titel_0"' in antwort.text
    assert 'value="ERP"' in antwort.text
    assert 'name="aenderung_titel_0"' in antwort.text
    assert 'value="Umzug"' in antwort.text


def test_unternehmenskontext_speichern_laesst_stammdaten_unangetastet(auftrag):
    a = auftrag.load_auftrag(AUFTRAG_ID)
    a.zweck = ["Optimierung"]
    a.abgrenzung = "Bestehende Abgrenzung"
    auftrag.save_auftrag(a)

    client.post(
        f"/auftrag/{AUFTRAG_ID}/unternehmenskontext",
        data={"kerngeschaeft": "Handel"},
        follow_redirects=False,
    )

    gespeichert = auftrag.load_auftrag(AUFTRAG_ID)
    assert gespeichert.zweck == ["Optimierung"]
    assert gespeichert.abgrenzung == "Bestehende Abgrenzung"


def test_unternehmenskontext_konflikt_gibt_die_aspekt_listen_zurueck(auftrag):
    stand = auftrag.load_auftrag(AUFTRAG_ID).version
    client.post(
        f"/auftrag/{AUFTRAG_ID}/unternehmenskontext",
        data={"version": str(stand)},
        follow_redirects=False,
    )

    antwort = client.post(
        f"/auftrag/{AUFTRAG_ID}/unternehmenskontext",
        data={
            "version": str(stand),
            "system_titel_0": "Vom B nicht verlorenes System",
            "system_text_0": "Text von B",
        },
        follow_redirects=False,
    )
    assert antwort.status_code == 409
    assert "Vom B nicht verlorenes System" in antwort.text


# ── Analysebericht: die zwei Abschnitte, die zuvor zwangsläufig leer waren ──

def test_analysebericht_enthaelt_geschaeftskritische_systeme_und_aenderungen():
    rb = ReportBuilder()
    a = Auftrag(id="a1", projekt_nummer="P1", kunde="Test Kunde", bezeichnung="Analyse 2026")
    a.unternehmenskontext.geschaeftskritische_systeme = [
        Aspekt(titel="ERP-System", text="SAP S/4HANA, zentral gehostet.")
    ]
    a.unternehmenskontext.geplante_aenderungen = [
        GeplanteAenderung(titel="Serverumzug", text="Migration ins neue Rechenzentrum Q3.", status="in_planung")
    ]

    from app.services.evaluator import evaluator_service
    bew = evaluator_service.evaluate_auftrag(["firewall"], [])

    report = rb.build_analysebericht(a, [], [], [], bew, [], ziel_vertraulichkeit="kundentauglich")

    assert "### Geschäftskritische Systeme" in report
    assert "- **ERP-System:** SAP S/4HANA, zentral gehostet." in report
    assert "### Geplante Änderungen" in report
    assert "- **Serverumzug** (Status: In Planung): Migration ins neue Rechenzentrum Q3." in report


def test_unternehmenskontext_kerngeschaeft_hinweistext(auftrag):
    response = client.get(f"/auftrag/{AUFTRAG_ID}/unternehmenskontext")
    assert response.status_code == 200
    assert "Beschreiben Sie kurz die Haupttätigkeit" in response.text
    assert "placeholder=\"z. B. Mittelständischer Großhandel" in response.text


def test_unternehmenskontext_geplante_aenderung_status_flow(auftrag):
    antwort = client.post(
        f"/auftrag/{AUFTRAG_ID}/unternehmenskontext",
        data={
            "aenderung_titel_0": "M365 Migration",
            "aenderung_status_0": "in_durchfuehrung",
            "aenderung_text_0": "Migration aller Postfächer zu Exchange Online.",
            "aenderung_titel_1": "Glasfaser-Ausbau",
            "aenderung_status_1": "budgetierung",
            "aenderung_text_1": "Anbindung 1 GBit/s synchron.",
        },
        follow_redirects=False,
    )
    assert antwort.status_code == 303

    gespeichert = auftrag.load_auftrag(AUFTRAG_ID)
    aend = gespeichert.unternehmenskontext.geplante_aenderungen
    assert len(aend) == 2
    assert aend[0].titel == "M365 Migration"
    assert aend[0].status == "in_durchfuehrung"
    assert aend[1].titel == "Glasfaser-Ausbau"
    assert aend[1].status == "budgetierung"

    # Formular anzeigen und prüfen
    form_resp = client.get(f"/auftrag/{AUFTRAG_ID}/unternehmenskontext")
    assert form_resp.status_code == 200
    assert 'value="in_durchfuehrung" selected' in form_resp.text
    assert 'value="budgetierung" selected' in form_resp.text

    # Bericht prüfen
    rb = ReportBuilder()
    from app.services.evaluator import evaluator_service
    bew = evaluator_service.evaluate_auftrag([], [])
    rep = rb.build_analysebericht(gespeichert, [], [], [], bew, [], ziel_vertraulichkeit="kundentauglich")
    assert "- **M365 Migration** (Status: In Durchführung / Projektstart bestätigt): Migration aller Postfächer zu Exchange Online." in rep
    assert "- **Glasfaser-Ausbau** (Status: Budgetierung): Anbindung 1 GBit/s synchron." in rep
