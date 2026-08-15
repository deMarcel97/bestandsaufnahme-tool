"""Die Versionsnummer steht an mehreren Stellen (Anwendung, Paketmetadaten,
Dokumentation). Diese Tests halten sie zusammen — sonst zeigt die Oberfläche
irgendwann eine Version an, die nicht der ausgelieferten entspricht."""

import re
import tomllib
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import APP_VERSION, BASE_DIR
from app.main import app

client = TestClient(app)


def test_version_ist_semver():
    assert re.fullmatch(r"\d+\.\d+\.\d+", APP_VERSION), APP_VERSION


def test_pyproject_hat_dieselbe_version():
    data = tomllib.loads((BASE_DIR / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["version"] == APP_VERSION


def test_readme_nennt_dieselbe_version():
    readme = (BASE_DIR / "README.md").read_text(encoding="utf-8")
    assert f"# IT-Bestandsaufnahme-Tool (v{APP_VERSION})" in readme
    assert f"Aktuelle Version: **{APP_VERSION}**" in readme


def test_changelog_hat_eintrag_fuer_version():
    changelog = (BASE_DIR / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{APP_VERSION}]" in changelog


def test_openapi_meldet_dieselbe_version():
    assert client.get("/openapi.json").json()["info"]["version"] == APP_VERSION


def test_version_steht_in_der_oberflaeche():
    """Wird als Jinja-Global gesetzt, muss also ohne Zutun der einzelnen
    Routen auf jeder Seite ankommen."""
    response = client.get("/auftrag")
    assert response.status_code == 200
    assert f"v{APP_VERSION}" in response.text


def test_version_auch_auf_unterseiten():
    """Gegenprobe auf einer Seite aus einem anderen Route-Modul — belegt, dass
    wirklich alle Module dieselbe Template-Instanz nutzen."""
    from app.services.storage import storage
    from app.models.auftrag import Auftrag

    auftrag = Auftrag(id="auf-version-test", projekt_nummer="PROJEKT-9999",
                      kunde="Testkunde", bezeichnung="Versionstest")
    storage.save_auftrag(auftrag)
    try:
        response = client.get(f"/auftrag/{auftrag.id}/offene_punkte")
        assert response.status_code == 200
        assert f"v{APP_VERSION}" in response.text
    finally:
        storage.delete_auftrag(auftrag.id)
