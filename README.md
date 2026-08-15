# IT-Bestandsaufnahme-Tool (v2.5.0)

Ein spezialisiertes Web-Tool für IT-Systemhäuser zur strukturierten Erfassung, automatischen Risikobewertung und professionellen Berichtserstellung von IT-Kundeninfrastrukturen.

> Aktuelle Version: **2.5.0** — Änderungshistorie siehe [CHANGELOG.md](CHANGELOG.md).

---

## 🚀 Übersicht & Hauptfunktionen

- **Strukturierte Erfassung**: Formularbasierte Bestandsaufnahme für **11 IT-Infrastruktur-Kategorien** (Firewall, USV, Serverraum, Netzwerkschrank, Switch, Access Points, M365 Security, Clients, Backup/Storage, Server & Virtualisierung, Software (Kategorie CRM, DMS oder ERP wählbar)).
- **Automatische Risiko-Analyse (Rule Engine)**: Überprüft Erfassungsdaten gegen konfigurierbare Regelwerke in `rules/*.yaml` und deckt Schwachstellen, Risiken und Abweichungen automatisch auf.
- **Bewertungssystem**: Berechnet Ampel-Scores und Gesamteinschätzungen zur IT-Sicherheit und Operational Readiness pro Standort und Kunde.
- **Berichtsexport (.docx)**: Erzeugt mit `python-docx` strukturierte Kundenberichte inklusive Handlungsempfehlungen.
- **Erfassungs-Fortschritt**: Übersichtlicher Fortschrittsbalken pro Auftrag und Standort.

---

## 🛠️ Technologiestack

- **Backend**: Python 3.10+ mit [FastAPI](https://fastapi.tiangolo.com/) & [Uvicorn](https://www.uvicorn.org/)
- **Frontend**: Responsive HTML5 mit Jinja2-Templates & Vanilla CSS
- **Validierung & Schemas**: [Pydantic v2](https://docs.pydantic.dev/) & [PyYAML](https://pyyaml.org/)
- **Dokumentengenerierung**: `python-docx`
- **Testing**: `pytest` & `httpx`

---

## 📦 Installation & Setup

### 1. Repository klonen & virtuelles Environment erstellen

```bash
git clone https://github.com/deMarcel97/bestandsaufnahme-tool.git
cd bestandsaufnahme-tool

python3 -m venv venv
source venv/bin/activate
```

### 2. Abhängigkeiten installieren

```bash
pip install -e .[dev]
```

---

## 💻 Anwendung starten

Starte den Entwicklungs-Server mit:

```bash
python run.py
```

Die Anwendung ist anschließend im Browser erreichbar unter:
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 🌐 Produktiv-Deployment auf einem Webserver

Für den Betrieb auf einem echten Webserver (statt des lokalen Single-User-
Dev-Servers) liegt ein `Dockerfile` bei:

```bash
docker build -t bestandsaufnahme-tool .
docker run -d \
  -p 8000:8000 \
  -v /pfad/zu/persistenten/daten:/srv/app/data \
  -e ENTRA_TENANT_ID=... \
  -e ENTRA_CLIENT_ID=... \
  -e ENTRA_CLIENT_SECRET=... \
  -e SESSION_SECRET_KEY=... \
  bestandsaufnahme-tool
```

Der Container lauscht auf Port 8000 und sollte hinter einem Reverse Proxy
(TLS-Terminierung, z.B. nginx/Caddy/Traefik) betrieben werden. Das
`/srv/app/data`-Verzeichnis enthält alle Auftragsdaten und muss auf ein
persistentes Volume gemountet werden, sonst gehen die Daten beim
Container-Neustart verloren.

### Entra ID (Azure AD) Single Sign-On

Der Login-Flow gegen Microsoft Entra ID ist als Code-Grundgerüst vorhanden
(`app/web/routes_auth.py`), aber standardmäßig **deaktiviert** — ohne die
folgenden drei Umgebungsvariablen läuft die Anwendung unverändert als
lokales Tool ohne Login weiter:

| Variable              | Beschreibung                                                        |
|------------------------|----------------------------------------------------------------------|
| `ENTRA_TENANT_ID`      | Tenant-ID aus der Azure-Portal-App-Registrierung                    |
| `ENTRA_CLIENT_ID`      | Client-/Application-ID der App-Registrierung                        |
| `ENTRA_CLIENT_SECRET`  | Client Secret der App-Registrierung                                  |
| `SESSION_SECRET_KEY`   | Fester geheimer Schlüssel zur Cookie-Signierung (sonst zufällig pro Prozessstart — Sessions überleben dann keinen Neustart/Mehrprozessbetrieb) |

Voraussetzung ist eine App-Registrierung im Entra-ID-Tenant (Azure Portal →
App registrations) mit Redirect-URI `https://<host>/auth/callback`. Sobald
alle drei `ENTRA_*`-Variablen gesetzt sind, verlangt die Anwendung für jede
Seite einen gültigen Entra-ID-Login (`app/main.py`, `require_entra_login`).

**Hinweis:** Der Login gewährt aktuell jedem erfolgreich angemeldeten
Nutzer:innen aus dem Tenant vollen Zugriff auf alle Aufträge — eine
Trennung nach Benutzer/Rolle (wer sieht/bearbeitet was) ist bewusst noch
nicht umgesetzt und für einen späteren Ausbauschritt vorgesehen, wenn das
Tool dafür ausgereift genug ist.

---

## 🧪 Tests ausführen

Die Anwendung verfügt über eine umfassende Testsuite (54 Tests). Führe die Tests wie folgt aus:

```bash
PYTHONPATH=. pytest
```

---

## 📂 Projektstruktur

```
.
├── app/
│   ├── main.py              # FastAPI Anwendungs-Einstiegspunkt
│   ├── web/                 # Web-Routes & Controller (Aufträge, Standorte, Objekte, Export)
│   ├── services/            # Core-Services (SchemaLoader, RuleEngine, Evaluator, Exporter, Storage)
│   ├── models/              # Pydantic Datenmodelle
│   ├── templates/           # Jinja2 HTML-Templates
│   └── static/              # CSS Stylesheets & JS Utilities
├── schemas/                 # YAML-Definitionen der 10 Erfassungsobjekte
├── rules/                   # Regelwerke für automatisierte Risikoanalysen
├── data/                    # JSON-Datenhaltung (Aufträge, Standorte, Befunde)
├── tests/                   # Automatisierte Unit- & Integrationstests
├── pyproject.toml           # Paket- & Abhängigkeitskonfiguration
└── run.py                   # Server-StarterSkript
```

---
