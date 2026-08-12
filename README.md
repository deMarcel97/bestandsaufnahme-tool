# IT-Bestandsaufnahme-Tool (v2.0.0)

Ein spezialisiertes Web-Tool für IT-Systemhäuser zur strukturierten Erfassung, automatischen Risikobewertung und professionellen Berichtserstellung von IT-Kundeninfrastrukturen.

---

## 🚀 Übersicht & Hauptfunktionen

- **Strukturierte Erfassung**: Formularbasierte Bestandsaufnahme für **10 IT-Infrastruktur-Kategorien** (Firewall, USV, Serverraum, Netzwerkschrank, Switch, Access Points, M365 Security, Clients, Backup/Storage, Server & Virtualisierung).
- **Automatische Risiko-Analyse (Rule Engine)**: Überprüft Erfassungsdaten gegen konfigurierbare Regelwerke in `rules/*.yaml` und deckt Schwachstellen, Risiken und Abweichungen automatisch auf.
- **Bewertungssystem**: Berechnet Ampel-Scores und Gesamteinschätzungen zur IT-Sicherheit und Operational Readiness pro Standort und Kunde.
- **Berichtsexport (.docx)**: Erzeugt mit `python-docx` strukturierte Kundenberichte inklusive Handlungsempfehlungen.
- **Erfassungs-Fortschritt**: Übersichtlicher Fortschrittsbalken pro Auftrag und Standort.

---

## 🛠️ Technologiestack

- **Backend**: Python 3.14+ mit [FastAPI](https://fastapi.tiangolo.com/) & [Uvicorn](https://www.uvicorn.org/)
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

## 📝 Lizenz & Autoren

Entwickelt für IT-Systemhäuser zur professionellen Kundenauditierung.