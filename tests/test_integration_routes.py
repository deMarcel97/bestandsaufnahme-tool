import html
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

def test_full_workflow():
    from app.services.storage import storage
    # Cleanup previous test runs
    existing = storage.list_auftraege()
    for a in existing:
        if a.projekt_nummer == "auf-2026-999":
            storage.delete_auftrag(a.id)

    # 1. List orders
    res = client.get("/auftrag")
    assert res.status_code == 200
    assert "Auftragsübersicht" in res.text

    # 2. Create Order
    res = client.post("/auftrag/neu", data={
        "projekt_nummer": "auf-2026-999",
        "kunde": "Landkreis Teststadt",
        "bezeichnung": "Integrations-Bestandsaufnahme",
        "grundlage": "Angebot",
        "vertraulichkeit_default": "kundentauglich",
        "aktive_bausteine": ["firewall"]
    }, follow_redirects=True)
    assert res.status_code == 200
    assert "Integrations-Bestandsaufnahme" in res.text

    auftrag_id = "auf-integrations-bestandsaufnahme"

    # 3. Add Standort
    res = client.post(f"/auftrag/{auftrag_id}/standort/neu", data={
        "bezeichnung": "Hauptgebäude",
        "ort": "Teststadt",
        "anzahl_user": 25,
        "anbieter_0": "Telekom",
        "art_0": "Glasfaser_FTTH",
        "bandbreite_down_mbit_0": 100,
        "bandbreite_up_mbit_0": 100,
        "ist_backup_leitung_0": "nein"
    }, follow_redirects=True)
    assert res.status_code == 200
    assert "Hauptgebäude" in res.text

    standort_id = "sto-hauptgebaeude"

    # 4. Add Firewall Object with expired security sub & rueckfrage field
    res = client.post(f"/auftrag/{auftrag_id}/objekt/neu?typ=firewall", data={
        "bezeichnung": "Zentrale Firewall",
        "standort_id": standort_id,
        "betreut_durch": "wir",
        "hersteller": "Fortinet",
        "security_abo_vorhanden": "nein", # triggers fw-security-abo-abgelaufen
        "exchange_onprem_dahinter": "ja",
        "dokumentation_vorhanden": "rueckfrage" # creates open point
    }, follow_redirects=True)
    assert res.status_code == 200
    assert "Zentrale Firewall" in res.text

    # 5. Evaluate Rules
    res = client.post(f"/auftrag/{auftrag_id}/bewerten", follow_redirects=True)
    assert res.status_code == 200
    assert "Gesamtbewertung" in res.text

    # 6. Check Findings
    res = client.get(f"/auftrag/{auftrag_id}/findings")
    assert res.status_code == 200
    assert "Firewall ohne aktives Security-Abonnement" in res.text

    # 7. Check Open Points
    res = client.get(f"/auftrag/{auftrag_id}/offene_punkte")
    assert res.status_code == 200
    assert "Rückfrage erforderlich" in res.text

    # 8. Check Measures Catalog
    res = client.get(f"/auftrag/{auftrag_id}/massnahmen")
    assert res.status_code == 200

    # 9. Download Export Analysebericht
    res = client.get(f"/auftrag/{auftrag_id}/export/download/analysebericht.md?ziel_vertraulichkeit=kundentauglich")
    assert res.status_code == 200
    assert "# Analysebericht: IT-Bestandsaufnahme" in res.text
    assert "Als zentrale Firewall kommt ein System des Herstellers Fortinet zum Einsatz." in res.text

def test_path_traversal_delete_is_rejected():
    from app.services.storage import storage
    client.post("/auftrag/neu", data={
        "projekt_nummer": "PROJ-TRAV-1",
        "kunde": "PoC",
        "bezeichnung": "Traversal Delete Test",
    }, follow_redirects=False)
    auftrag_id = "auf-traversal-delete-test"
    assert storage.load_auftrag(auftrag_id) is not None

    # ".." als auftrag_id, %2e-kodiert damit der Client es nicht vorher normalisiert
    res = client.post("/auftrag/%2e%2e/delete", follow_redirects=False)
    assert res.status_code in (303, 404)

    # Der zuvor angelegte Auftrag muss unversehrt sein
    assert storage.load_auftrag(auftrag_id) is not None

def test_projekt_nummer_duplicate_error_is_escaped():
    payload = "PROJ-XSSTEST'); alert(1); //"
    client.post("/auftrag/neu", data={
        "projekt_nummer": payload,
        "kunde": "PoC",
        "bezeichnung": "PoC Order A",
    }, follow_redirects=False)

    res = client.post("/auftrag/neu", data={
        "projekt_nummer": payload,
        "kunde": "PoC2",
        "bezeichnung": "PoC Order B",
    }, follow_redirects=False)
    assert res.status_code == 400
    assert payload not in res.text
    assert html.escape(payload) in res.text

def test_export_defaults_to_auftrag_vertraulichkeit_default():
    client.post("/auftrag/neu", data={
        "projekt_nummer": "PROJ-EXPORT-DEFAULT",
        "kunde": "PoC",
        "bezeichnung": "Export Default Test",
        "vertraulichkeit_default": "intern",
    }, follow_redirects=False)
    auftrag_id = "auf-export-default-test"

    res = client.get(f"/auftrag/{auftrag_id}/export")
    assert res.status_code == 200
    assert "Stufe intern" in res.text

def test_objekt_typ_traversal_rejected():
    from app.services.storage import storage
    client.post("/auftrag/neu", data={
        "projekt_nummer": "PROJ-TT-1",
        "kunde": "PoC",
        "bezeichnung": "Typ Traversal Test",
    }, follow_redirects=False)
    auftrag_id = "auf-typ-traversal-test"

    res = client.post(f"/auftrag/{auftrag_id}/objekt/neu?typ=../../../../tmp/pwn", data={
        "bezeichnung": "Boese Datei",
    }, follow_redirects=False)
    assert res.status_code == 303
    assert storage.list_objekte(auftrag_id) == []

def _stammdaten_formular(bezeichnung: str, projekt_nummer: str) -> dict:
    return {
        "projekt_nummer": projekt_nummer,
        "jira_url": "https://jira.example.org/BAT-1",
        "kunde": "Trenn-Kunde",
        "auftraggeber": "Frau Muster",
        "bezeichnung": bezeichnung,
        "grundlage": "Rahmenvertrag",
        "status": "Erfassung",
        "vertraulichkeit_default": "intern",
        "aktive_bausteine": ["firewall", "switch"],
        "beauftragung": "2026-01-05",
        "kickoff": "2026-01-12",
        "entwurf_vorlage": "2026-02-01",
        "abgabe": "2026-03-01",
    }

KONTEXT_FORMULAR = {
    "kerngeschaeft": "Maschinenbau",
    "anzahl_standorte_kunde": "1",
    "it_abteilung_vorhanden": "ja",
    "anzahl_mitarbeiter_gesamt": "250",
    "anzahl_it_mitarbeiter": "4",
    "anzahl_it_nutzer": "230",
    "geschaeftszeiten_tage": "Montag bis Samstag",
    "geschaeftszeiten_von": "06:00",
    "geschaeftszeiten_bis": "20:00",
    "allgemeine_hinweise": "Zutritt nur mit Voranmeldung",
}

def _pruefe_stammdaten(auftrag, formular: dict):
    """Vergleicht gegen die tatsächlich abgeschickten Werte statt gegen einen
    vorher genommenen Schnappschuss: ein Handler, der Felder immer auf ihren
    Default zurücksetzt, fällt sonst nicht auf."""
    assert auftrag.projekt_nummer == formular["projekt_nummer"]
    assert auftrag.jira_url == formular["jira_url"]
    assert auftrag.kunde == formular["kunde"]
    assert auftrag.auftraggeber == formular["auftraggeber"]
    assert auftrag.bezeichnung == formular["bezeichnung"]
    assert auftrag.grundlage == formular["grundlage"]
    assert auftrag.status == formular["status"]
    assert auftrag.vertraulichkeit_default == formular["vertraulichkeit_default"]
    assert auftrag.aktive_bausteine == formular["aktive_bausteine"]
    assert auftrag.termine.beauftragung == formular["beauftragung"]
    assert auftrag.termine.kickoff == formular["kickoff"]
    assert auftrag.termine.entwurf_vorlage == formular["entwurf_vorlage"]
    assert auftrag.termine.abgabe == formular["abgabe"]

def _pruefe_kontext(auftrag, formular: dict):
    kontext = auftrag.unternehmenskontext
    assert kontext.kerngeschaeft == formular["kerngeschaeft"]
    assert kontext.anzahl_standorte_kunde == int(formular["anzahl_standorte_kunde"])
    assert kontext.it_abteilung_vorhanden == formular["it_abteilung_vorhanden"]
    assert kontext.anzahl_mitarbeiter_gesamt == int(formular["anzahl_mitarbeiter_gesamt"])
    assert kontext.anzahl_it_mitarbeiter == int(formular["anzahl_it_mitarbeiter"])
    assert kontext.anzahl_it_nutzer == int(formular["anzahl_it_nutzer"])
    assert kontext.geschaeftszeiten_tage == formular["geschaeftszeiten_tage"]
    assert kontext.geschaeftszeiten_von == formular["geschaeftszeiten_von"]
    assert kontext.geschaeftszeiten_bis == formular["geschaeftszeiten_bis"]
    assert kontext.allgemeine_hinweise == formular["allgemeine_hinweise"]

def _auftrag_mit_stammdaten_und_kontext(bezeichnung: str, projekt_nummer: str) -> str:
    """Legt einen Auftrag an und füllt beide Seiten (Stammdaten und
    Unternehmenskontext) einmal vollständig aus."""
    from app.services.storage import storage

    client.post("/auftrag/neu", data={
        "projekt_nummer": projekt_nummer,
        "kunde": "Trenn-Kunde",
        "bezeichnung": bezeichnung,
    }, follow_redirects=False)
    auftrag_id = next(a.id for a in storage.list_auftraege() if a.projekt_nummer == projekt_nummer)

    client.post(f"/auftrag/{auftrag_id}/stammdaten",
                data=_stammdaten_formular(bezeichnung, projekt_nummer), follow_redirects=False)
    client.post(f"/auftrag/{auftrag_id}/unternehmenskontext",
                data=KONTEXT_FORMULAR, follow_redirects=False)

    return auftrag_id

def test_stammdaten_speichern_laesst_unternehmenskontext_unveraendert():
    """Beide Seiten sind eigene Formulare. Wer nur die Stammdaten speichert,
    schickt keine Kontextfelder mit — der Kontext darf davon nicht geleert oder
    auf Defaults zurückgesetzt werden."""
    from app.services.storage import storage

    auftrag_id = _auftrag_mit_stammdaten_und_kontext("Trennung Stammdaten", "PROJ-TRENN-1")

    res = client.post(f"/auftrag/{auftrag_id}/stammdaten", data={
        "projekt_nummer": "PROJ-TRENN-1",
        "kunde": "Trenn-Kunde neu",
        "bezeichnung": "Trennung Stammdaten",
        "grundlage": "Angebot",
        "status": "Bewertung",
        "vertraulichkeit_default": "kundentauglich",
        "aktive_bausteine": ["firewall"],
    }, follow_redirects=False)
    assert res.status_code == 303

    auftrag = storage.load_auftrag(auftrag_id)
    assert auftrag.kunde == "Trenn-Kunde neu"
    assert auftrag.status == "Bewertung"
    _pruefe_kontext(auftrag, KONTEXT_FORMULAR)

def test_unternehmenskontext_speichern_laesst_stammdaten_unveraendert():
    """Gegenprobe: Der Kontext darf Stammdaten, Auftragssteuerung und Termine
    nicht überschreiben."""
    from app.services.storage import storage

    bezeichnung, projekt_nummer = "Trennung Kontext", "PROJ-TRENN-2"
    auftrag_id = _auftrag_mit_stammdaten_und_kontext(bezeichnung, projekt_nummer)

    res = client.post(f"/auftrag/{auftrag_id}/unternehmenskontext", data={
        "kerngeschaeft": "Maschinenbau und Service",
        "anzahl_standorte_kunde": "1",
        "it_abteilung_vorhanden": "nein",
        "geschaeftszeiten_tage": "24/7",
        "allgemeine_hinweise": "Neue Hinweise",
    }, follow_redirects=False)
    assert res.status_code == 303

    auftrag = storage.load_auftrag(auftrag_id)
    assert auftrag.unternehmenskontext.kerngeschaeft == "Maschinenbau und Service"
    assert auftrag.unternehmenskontext.geschaeftszeiten_tage == "24/7"
    assert auftrag.unternehmenskontext.allgemeine_hinweise == "Neue Hinweise"
    _pruefe_stammdaten(auftrag, _stammdaten_formular(bezeichnung, projekt_nummer))

def test_alte_einstellungen_url_leitet_auf_stammdaten_weiter():
    auftrag_id = _auftrag_mit_stammdaten_und_kontext("Trennung Redirect", "PROJ-TRENN-3")

    res = client.get(f"/auftrag/{auftrag_id}/einstellungen", follow_redirects=False)
    assert res.status_code == 303
    assert res.headers["location"] == f"/auftrag/{auftrag_id}/stammdaten"

def test_beide_seiten_zeigen_sidebar_mit_fortschritt():
    """build_sidebar_context() muss auf beiden Seiten eingebunden sein, sonst
    fehlt die Baustein-Fortschrittsanzeige."""
    auftrag_id = _auftrag_mit_stammdaten_und_kontext("Trennung Sidebar", "PROJ-TRENN-4")

    for pfad, ueberschrift in (("stammdaten", "Stammdaten"), ("unternehmenskontext", "Unternehmenskontext")):
        res = client.get(f"/auftrag/{auftrag_id}/{pfad}")
        assert res.status_code == 200
        assert f"<h1>{ueberschrift}</h1>" in res.text
        assert "baustein-list" in res.text
        assert f'href="/auftrag/{auftrag_id}/stammdaten"' in res.text
        assert f'href="/auftrag/{auftrag_id}/unternehmenskontext"' in res.text

def test_batch_create_objekte():
    from app.services.storage import storage
    client.post("/auftrag/neu", data={
        "projekt_nummer": "PROJ-BATCH-1",
        "kunde": "Batch Kunde",
        "bezeichnung": "Batch Test Order",
        "aktive_bausteine": ["netzwerkschrank"]
    }, follow_redirects=True)
    auftrag_id = "auf-batch-test-order"

    client.post(f"/auftrag/{auftrag_id}/standort/neu", data={
        "bezeichnung": "Hauptstandort"
    }, follow_redirects=True)

    res = client.post(f"/auftrag/{auftrag_id}/objekt/mehrere_anlegen", data={
        "standort_id": "sto-hauptstandort",
        "typ": "netzwerkschrank",
        "anzahl": 3
    }, follow_redirects=True)

    assert res.status_code == 200
    objs = storage.list_objekte(auftrag_id)
    assert len(objs) == 3
    assert any("Netzwerkschrank 1" in o.bezeichnung for o in objs)
    assert any("Netzwerkschrank 2" in o.bezeichnung for o in objs)
    assert any("Netzwerkschrank 3" in o.bezeichnung for o in objs)
