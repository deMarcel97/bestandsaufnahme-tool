# IT-Bestandsaufnahme-Tool (v2.7.30)

Ein spezialisiertes Web-Tool für IT-Systemhäuser zur strukturierten Erfassung, automatischen Risikobewertung und professionellen Berichtserstellung von IT-Kundeninfrastrukturen.

> Aktuelle Version: **2.7.30** — Änderungshistorie siehe [CHANGELOG.md](CHANGELOG.md).

---

## 🚀 Übersicht & Hauptfunktionen

- **Strukturierte Erfassung**: Formularbasierte Bestandsaufnahme für **IT-Infrastruktur- und Organisations-Kategorien** (Firewall, USV, Serverraum, Netzwerkschrank, Switch, Access Points, Storage, Backup & Recovery, Organisation & Prozesse, M365 Security, Clients, Server & Virtualisierung, Software).
- **Automatische Risiko-Analyse (Rule Engine)**: Überprüft Erfassungsdaten gegen konfigurierbare Regelwerke in `rules/*.yaml` und deckt Schwachstellen, Risiken und Abweichungen automatisch auf.
- **Bewertungssystem**: Berechnet Ampel-Scores und Gesamteinschätzungen zur IT-Sicherheit und Operational Readiness pro Standort und Kunde.
- **Berichtsexport (.docx)**: Erzeugt mit `python-docx` strukturierte Kundenberichte inklusive Handlungsempfehlungen.
- **Erfassungs-Fortschritt**: Übersichtlicher Fortschrittsbalken pro Auftrag und Standort.
- **Getrennte Navigation**: „Übersicht" (`/auftrag/{id}`) zeigt nur die Kennzahlen des Auftrags, „Erfassung" (`/auftrag/{id}/erfassung`) ist die Arbeitsfläche für Standorte und Objekte.

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

## 🌐 Produktiv-Deployment auf einem Server

### Variante A: Debian/Ubuntu-Server (empfohlen)

Für den Betrieb auf einem Ubuntu-/Debian-VPS liegt ein Install-Skript bei. Es
richtet ein Dienstkonto, ein Virtualenv, einen systemd-Service und einen
nginx-Reverse-Proxy ein:

```bash
git clone https://github.com/deMarcel97/bestandsaufnahme-tool.git
```

```bash
sudo SERVER_NAME=bestandsaufnahme.firma.de ALLOW_CIDRS="10.0.0.0/8 192.168.0.0/16" ./bestandsaufnahme-tool/deploy/install.sh
```

Das Skript ist **idempotent** — es kann beliebig oft laufen und überschreibt
dabei weder Kundendaten noch eingetragene Secrets.

| Variable       | Default                                | Bedeutung                                        |
|----------------|----------------------------------------|--------------------------------------------------|
| `SERVER_NAME`  | `_`                                    | Hostname der nginx-Site (`_` = beliebiger Host)  |
| `ALLOW_CIDRS`  | RFC1918-Netze                          | Quell-Netze, die zugreifen dürfen                |
| `APP_DIR`      | `/opt/bestandsaufnahme-tool`           | Code-Checkout                                    |
| `DATA_DIR`     | `/var/lib/bestandsaufnahme-tool/data`  | Auftragsdaten (bleiben bei Updates unangetastet) |
| `ENV_FILE`     | `/etc/bestandsaufnahme-tool/app.env`   | Konfiguration & Secrets                          |
| `PORT`         | `8000`                                 | Port, auf dem uvicorn lokal lauscht              |
| `BRANCH`       | `main`                                 | Auszurollender Git-Branch                        |
| `SKIP_NGINX`   | `0`                                    | `1` = keinen Reverse Proxy einrichten            |

Nach der Installation:

```bash
systemctl status bestandsaufnahme-tool
journalctl -u bestandsaufnahme-tool -f
```

> ⚠️ **Zugriffsschutz:** Solange kein Entra-ID-Login konfiguriert ist (siehe
> unten), ist die IP-Beschränkung in der nginx-Site die **einzige**
> Zugriffskontrolle vor den Kundendaten. `install.sh` bricht deshalb bewusst
> ab, wenn `ALLOW_CIDRS` leer ist. Bevor das Tool aus dem offenen Internet
> erreichbar sein soll, muss Entra ID aktiviert **und** TLS eingerichtet sein
> (z.B. `sudo certbot --nginx -d bestandsaufnahme.firma.de`).

### Auf dem Server arbeiten & aktualisieren

Der Code liegt als normaler Git-Checkout in `/opt/bestandsaufnahme-tool`,
damit direkt auf dem Server entwickelt und getestet werden kann:

```bash
sudo /opt/bestandsaufnahme-tool/deploy/update.sh
```

Holt den aktuellen Stand von GitHub, installiert bei Bedarf geänderte
Abhängigkeiten nach und startet den Dienst neu. Wurden Dateien direkt auf dem
Server bearbeitet, verhindert das Skript den Überschreib-Unfall und bricht ab —
für diesen Fall gibt es:

```bash
sudo /opt/bestandsaufnahme-tool/deploy/update.sh --restart
```

Das startet nur den Dienst neu und lässt lokale Änderungen unberührt.

### Variante B: Docker

Alternativ liegt ein `Dockerfile` bei:

```bash
docker build -t bestandsaufnahme-tool .
```

```bash
docker run -d -p 8000:8000 -v /pfad/zu/persistenten/daten:/srv/app/data bestandsaufnahme-tool
```

Der Container lauscht auf Port 8000 und sollte hinter einem Reverse Proxy
(TLS-Terminierung, z.B. nginx/Caddy/Traefik) betrieben werden. Das
`/srv/app/data`-Verzeichnis enthält alle Auftragsdaten und muss auf ein
persistentes Volume gemountet werden, sonst gehen die Daten beim
Container-Neustart verloren. Die `ENTRA_*`- und `SESSION_SECRET_KEY`-Variablen
werden wie unten beschrieben per `-e` übergeben.

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

Bei der Server-Installation stehen diese Werte in
`/etc/bestandsaufnahme-tool/app.env` (bereits als Kommentar vorbereitet). Nach
dem Eintragen: `sudo systemctl restart bestandsaufnahme-tool`.

Unabhängig vom Login steuert eine weitere Variable, wo die Nutzdaten liegen:

| Variable                      | Beschreibung                                                                                 |
|-------------------------------|----------------------------------------------------------------------------------------------|
| `BESTANDSAUFNAHME_DATA_DIR`   | Verzeichnis für Auftragsdaten. Ohne die Variable wird `data/` im Projektverzeichnis genutzt (lokaler Dev-Betrieb). Im Serverbetrieb zeigt sie auf `/var/lib/bestandsaufnahme-tool/data`, damit Code-Updates die Kundendaten nicht berühren. |

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
├── data/                    # YAML-Datenhaltung (Aufträge, Standorte, Befunde)
├── deploy/                  # Server-Deployment: install.sh, update.sh, systemd-Unit, nginx-Site
├── tests/                   # Automatisierte Unit- & Integrationstests
├── requirements.txt         # Laufzeit-Abhängigkeiten (Quelle für pyproject, Docker & install.sh)
├── pyproject.toml           # Paket- & Abhängigkeitskonfiguration
└── run.py                   # Server-StarterSkript
```

---
