# Arbeitsanweisungen für KI-Agenten

Gilt für alle Agenten/Tools, die in diesem Repo arbeiten (Claude Code,
Antigravity/agy, Mistral Vibe, …).

## Projekt

FastAPI-Webtool zur strukturierten IT-Bestandsaufnahme beim Kunden. Daten
liegen als YAML-Dateien, nicht in einer Datenbank. Details: [README.md](README.md).

Ein Grundsatz zieht sich durch alle Entscheidungen: **Es gibt genau ein
Erfassungswerkzeug für alle Kundengrößen** — vom 5-PC-Betrieb bis zum
1000-PC-Konzern. Neue Felder und Fragen müssen für beide Enden sinnvoll sein;
Fragen, die für kleine Kunden offensichtlich irrelevant sind, gehören hinter
eine `sichtbar_wenn`-Bedingung statt ins Standardformular.

## Live-Server

Das Tool läuft auf einem internen Server (Proxmox-LXC, Debian 13). Die
konkreten Adressen und Pfade stehen in `deploy/server.local.env` — die Datei
ist **absichtlich nicht im Git** (das Repo ist öffentlich):

```bash
source deploy/server.local.env
ssh "$BAT_SERVER_SSH"
```

Fehlt die Datei, bei Marcel danach fragen — nicht raten und nicht im Repo
suchen.

Aufbau auf dem Server:

| Was | Wo |
|---|---|
| Code (Git-Checkout) | `/opt/bestandsaufnahme-tool` |
| Nutzdaten | `/var/lib/bestandsaufnahme-tool/data` |
| Konfiguration/Secrets | `/etc/bestandsaufnahme-tool/app.env` |
| Dienst | `systemctl status bestandsaufnahme-tool` |
| Logs | `journalctl -u bestandsaufnahme-tool -f` |

Der Dienst läuft gehärtet: `/opt` ist für ihn **read-only**, beschreibbar ist
nur das Datenverzeichnis. uvicorn lauscht ausschliesslich auf `127.0.0.1`;
nach aussen geht es nur über nginx, das den Zugriff auf interne Netze
beschränkt. **Es ist kein Login aktiv** — diese IP-Beschränkung ist damit die
einzige Zugriffskontrolle vor den Kundendaten und darf nur zusammen mit der
Aktivierung von Entra-ID-SSO gelockert werden.

### Auf dem Server arbeiten

```bash
sudo /opt/bestandsaufnahme-tool/deploy/update.sh            # Stand von GitHub holen + Neustart
sudo /opt/bestandsaufnahme-tool/deploy/update.sh --restart  # nur Neustart, lokale Änderungen bleiben
```

Wer direkt auf dem Server Dateien ändert, nutzt `--restart` — die Variante
ohne Flag bricht bei uncommitteten Änderungen bewusst ab, statt sie zu
überschreiben.

## Regeln für Änderungen

1. **Erst Superthread-Karte, dann Code.** Board „Bestandsaufnahme-Tool"
   (space_id 6, board_id 15). Die Karte liefert die ID für alles Weitere und
   wird mit `Feature` oder `Bug` getaggt.
2. **Benennung nach Karten-ID**: Branch `feature/<id>-<slug>` bzw.
   `fix/<id>-<slug>`, PR-Titel `#<id> — <Kurzbeschreibung>`, CHANGELOG-Eintrag
   mit `(#<id>)`. Beispiele: `feature/301-server-deployment`,
   `fix/295-ampelfarben-standort`.
3. **Version bumpen + Dokumentation** bei jeder nennenswerten Änderung:
   `pyproject.toml`, `app/main.py`, README-Kopf und `CHANGELOG.md` (SemVer).
4. **Lokal *und* GitHub.** Jede Änderung landet sowohl im lokalen
   Dev-Checkout als auch als gepushter PR — nie nur in einem von beidem.
5. **Bei Fragen zu Feldabhängigkeiten und UX erst besprechen**, nicht direkt
   implementieren. Klare Bugs dürfen direkt gefixt werden.

## Tests

```bash
PYTHONPATH=. pytest
```

Muss vor jedem PR grün sein.
