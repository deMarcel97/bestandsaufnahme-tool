# Deployment

Server-Deployment für Debian/Ubuntu mit systemd, nginx-Reverse-Proxy und Docker-Alternative.

## Karten

- #301: Server-Deployment für Debian/Ubuntu

## Beteiligte Dateien

| Datei | Rolle |
|---|---|
| `deploy/install.sh` | Idempotentes Install-Skript |
| `deploy/update.sh` | Update-Skript (git pull + Neustart) |
| `deploy/bestandsaufnahme-tool.service` | systemd-Unit |
| `deploy/nginx-site.conf` | nginx-Reverse-Proxy-Konfiguration |
| `Dockerfile` | Docker-Container-Definition |
| `requirements.txt` | Laufzeit-Abhängigkeiten (Quelle für pyproject, Docker, install.sh) |
| `app/config.py` | `BESTANDSAUFNAHME_DATA_DIR`, `HOST`, `PORT`, `RELOAD` |
| `run.py` | Server-Starter (liest Environment-Variablen) |

## Funktionsweise

### install.sh

- Idempotent: beliebig oft ausführbar, überschreibt weder Kundendaten noch Secrets.
- Richtet ein: Systempakete, Systemuser (`bestandsaufnahme`), Git-Checkout, Virtualenv, Env-File, systemd-Service, nginx-Site.
- IP-Beschränkung: `ALLOW_CIDRS` (Default RFC1918), bricht ab wenn leer.

| Variable | Default | Bedeutung |
|---|---|---|
| `SERVER_NAME` | `_` | Hostname der nginx-Site |
| `ALLOW_CIDRS` | RFC1918 | Quell-Netze |
| `APP_DIR` | `/opt/bestandsaufnahme-tool` | Code-Checkout |
| `DATA_DIR` | `/var/lib/bestandsaufnahme-tool/data` | Auftragsdaten |
| `ENV_FILE` | `/etc/bestandsaufnahme-tool/app.env` | Konfiguration/Secrets |
| `PORT` | `8000` | uvicorn-Port |
| `BRANCH` | `main` | Git-Branch |
| `SKIP_NGINX` | `0` | `1` = kein Reverse Proxy |

### update.sh

- `sudo /opt/bestandsaufnahme-tool/deploy/update.sh` -- Holt GitHub-Stand, installiert bei Bedarf Abhängigkeiten, startet Dienst neu.
- Bricht bei uncommitteten Änderungen ab (Schutz vor Überschreib-Unfällen).
- `--restart` Flag: nur Neustart, lässt lokale Änderungen unberührt.
- Gesamter Ablauf in einer Funktion (Bash liest vollständig ein, bevor sie startet -- #301 Fix für Selbst-Überschreibung).

### systemd-Unit

- Gehärtet: `ProtectSystem=strict`, `NoNewPrivileges`, `ReadWritePaths` nur auf Datenverzeichnis.
- uvicorn bindet ausschliesslich an `127.0.0.1` -- nach aussen nur über nginx.

### Server-Struktur

| Was | Wo |
|---|---|
| Code | `/opt/bestandsaufnahme-tool` |
| Nutzdaten | `/var/lib/bestandsaufnahme-tool/data` |
| Konfiguration/Secrets | `/etc/bestandsaufnahme-tool/app.env` |
| Dienst | `systemctl status bestandsaufnahme-tool` |
| Logs | `journalctl -u bestandsaufnahme-tool -f` |

### Docker

- `docker build -t bestandsaufnahme-tool .`
- `docker run -d -p 8000:8000 -v <data>:/srv/app/data bestandsaufnahme-tool`
- `/srv/app/data` muss auf persistentes Volume gemountet werden.
- `ENTRA_*`- und `SESSION_SECRET_KEY` per `-e` übergeben.

### Datenverzeichnis

- `BESTANDSAUFNAHME_DATA_DIR` legt fest, wo Auftragsdaten liegen.
- Serverbetrieb: `/var/lib/bestandsaufnahme-tool/data` (Code-Updates berühren Kundendaten nicht).
- Ohne Variable: `data/` im Projektverzeichnis (lokaler Dev-Betrieb).
