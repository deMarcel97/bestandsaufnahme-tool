import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.web.routes_wizard import format_baustein_bezeichnung
from app.services.progress import progress_service
from app.models.auftrag import Auftrag
from app.models.standort import Standort
from app.models.technik import TechnikObjekt, OffenerPunktItem

client = TestClient(app)

def test_http_security_headers_present():
    """Prüft, ob alle geforderten HTTP Security-Headers gesetzt werden (#373)."""
    response = client.get("/auftrag")
    assert response.status_code == 200
    assert response.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "default-src 'self'" in response.headers.get("Content-Security-Policy", "")
    assert "geolocation=()" in response.headers.get("Permissions-Policy", "")

def test_offline_mermaid_asset_available():
    """Prüft, dass mermaid.min.js lokal unter /static/js/ liegt (#372)."""
    response = client.get("/static/js/mermaid.min.js")
    assert response.status_code == 200
    assert len(response.content) > 100000

def test_custom_404_html_error_page():
    """Prüft, dass 404-Fehler eine ansprechende HTML-Fehlerseite liefern (#375)."""
    response = client.get("/nicht-existierende-route-12345", headers={"Accept": "text/html"})
    assert response.status_code == 404
    assert "404 — Seite nicht gefunden" in response.text
    assert "Zur Auftragsübersicht" in response.text

def test_baustein_model_name_generation():
    """Prüft, dass Baustein-Namen das Modell priorisieren (#376)."""
    assert format_baustein_bezeichnung("Firewall", "Fortinet", "FortiGate 60F") == "Firewall FortiGate 60F"
    assert format_baustein_bezeichnung("Server", "Dell", "PowerEdge R740") == "Server PowerEdge R740"
    assert format_baustein_bezeichnung("Switch", "Cisco", "Catalyst 9200-24T") == "Switch Catalyst 9200-24T"
    assert format_baustein_bezeichnung("Access Point", "Ubiquiti", "UniFi U6 Pro") == "Access Point UniFi U6 Pro"
    assert format_baustein_bezeichnung("USV", "APC", "Smart-UPS 1500") == "USV Smart-UPS 1500"
    # Fallback bei leerem Modell
    assert format_baustein_bezeichnung("Storage", "Synology", "") == "Storage Synology"
    assert format_baustein_bezeichnung("Firewall", "Fortinet", "") == "Firewall Fortinet"
    assert format_baustein_bezeichnung("Firewall", "", "") == "Firewall Standard"

def test_offene_punkte_priorities():
    """Prüft die 3-stufige Priorisierung der offenen Punkte (#369)."""
    auftrag = Auftrag(
        schema_version=1,
        id="auf-test-prio",
        projekt_nummer="PROJ-PRIO",
        kunde="Test Kunde",
        bezeichnung="Test Prio",
        aktive_bausteine=["firewall"]
    )
    standort = Standort(schema_version=1, id="sto-prio", bezeichnung="Standort Prio", auftrag_id="auf-test-prio")
    
    fw_obj = TechnikObjekt(
        schema_version=1,
        id="fw-prio",
        typ="firewall",
        bezeichnung="Firewall Test",
        auftrag_id="auf-test-prio",
        standort_id="sto-prio",
        daten={"wartungsvertrag_vorhanden": "unbekannt", "seriennummer": "unbekannt"}
    )
    
    punkte = progress_service.collect_offene_punkte(auftrag, [standort], [fw_obj], [])
    assert len(punkte) > 0
    
    # wartungsvertrag_vorhanden ist kritisch
    kritische = [p for p in punkte if p.prioritaet == "kritisch"]
    assert len(kritische) > 0
    assert any("Wartungsvertrag" in p.text or "wartungsvertrag" in p.text for p in kritische)

def test_modal_create_auftrag_empty_validation():
    """Prüft, dass leeres Absenden von /auftrag/neu sauberes 400 liefert (#364)."""
    response = client.post("/auftrag/neu", data={"kunde": "", "bezeichnung": ""})
    assert response.status_code == 400
    assert "Bitte Kunde und Auftragsbezeichnung angeben" in response.text
