#!/usr/bin/env bash
#
# Installiert das IT-Bestandsaufnahme-Tool auf einem Debian/Ubuntu-Server.
#
#   sudo ./deploy/install.sh
#
# Das Skript ist idempotent: es kann beliebig oft laufen, ohne bestehende
# Daten, Konfiguration oder Secrets zu überschreiben.
#
# Konfiguration über Umgebungsvariablen, z.B.:
#   sudo SERVER_NAME=bestandsaufnahme.firma.de \
#        ALLOW_CIDRS="10.8.0.0/24 192.168.1.0/24" \
#        ./deploy/install.sh
#
set -euo pipefail

# ── Konfiguration ────────────────────────────────────────────────────────
APP_NAME="${APP_NAME:-bestandsaufnahme-tool}"
APP_USER="${APP_USER:-bestandsaufnahme}"
APP_DIR="${APP_DIR:-/opt/${APP_NAME}}"
DATA_DIR="${DATA_DIR:-/var/lib/${APP_NAME}/data}"
ENV_FILE="${ENV_FILE:-/etc/${APP_NAME}/app.env}"
PORT="${PORT:-8000}"

REPO_URL="${REPO_URL:-https://github.com/deMarcel97/bestandsaufnahme-tool.git}"
BRANCH="${BRANCH:-main}"

# Hostname, unter dem das Tool erreichbar ist. "_" = beliebiger Host.
SERVER_NAME="${SERVER_NAME:-_}"

# Quell-Netze, die zugreifen dürfen. Default: private RFC1918-Netze.
# ACHTUNG: Solange kein Entra-ID-Login aktiv ist, ist das die einzige
# Zugriffskontrolle vor den Kundendaten.
ALLOW_CIDRS="${ALLOW_CIDRS:-10.0.0.0/8 172.16.0.0/12 192.168.0.0/16}"

SKIP_NGINX="${SKIP_NGINX:-0}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Hilfsfunktionen ──────────────────────────────────────────────────────
log()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!!\033[0m  %s\n' "$*" >&2; }
die()  { printf '\033[1;31mFEHLER:\033[0m %s\n' "$*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "Bitte mit sudo/root ausführen."
command -v apt-get >/dev/null || die "Kein apt-get gefunden — dieses Skript ist für Debian/Ubuntu."

# ── 1. Systempakete ──────────────────────────────────────────────────────
log "Systempakete installieren"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
PACKAGES=(python3 python3-venv python3-pip git curl)
[[ "$SKIP_NGINX" == "1" ]] || PACKAGES+=(nginx)
apt-get install -y -qq "${PACKAGES[@]}"

# ── 2. Dienstkonto ───────────────────────────────────────────────────────
# Systemkonto ohne Login-Shell und ohne Home — der Dienst braucht beides nicht.
if id "$APP_USER" &>/dev/null; then
    log "Benutzer '$APP_USER' existiert bereits"
else
    log "Benutzer '$APP_USER' anlegen"
    useradd --system --no-create-home --shell /usr/sbin/nologin "$APP_USER"
fi

# ── 3. Code ausrollen ────────────────────────────────────────────────────
if [[ -d "$APP_DIR/.git" ]]; then
    log "Vorhandenes Checkout in $APP_DIR aktualisieren"
    if [[ -n "$(git -C "$APP_DIR" status --porcelain)" ]]; then
        # Wichtig beim gemeinsamen Live-Arbeiten auf dem Server: ungesicherte
        # Änderungen werden nicht stillschweigend weggeworfen.
        warn "$APP_DIR hat uncommittete Änderungen — Code-Update wird übersprungen."
        warn "Erst committen/stashen, dann install.sh erneut ausführen."
    else
        git -C "$APP_DIR" fetch --quiet origin "$BRANCH"
        git -C "$APP_DIR" checkout --quiet "$BRANCH"
        git -C "$APP_DIR" merge --quiet --ff-only "origin/$BRANCH"
    fi
elif [[ -d "$APP_DIR" && -n "$(ls -A "$APP_DIR" 2>/dev/null)" ]]; then
    die "$APP_DIR existiert, ist aber kein Git-Checkout und nicht leer. Bitte manuell prüfen."
else
    log "Repository nach $APP_DIR klonen ($BRANCH)"
    git clone --quiet --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi

# ── 4. Datenverzeichnis ──────────────────────────────────────────────────
# Liegt bewusst ausserhalb von $APP_DIR, damit Code-Updates die Kundendaten
# nicht berühren und der Dienst nur hier Schreibrechte braucht.
log "Datenverzeichnis $DATA_DIR"
mkdir -p "$DATA_DIR"
chown -R "$APP_USER:$APP_USER" "$DATA_DIR"
chmod 750 "$DATA_DIR"

# ── 5. Virtualenv & Abhängigkeiten ───────────────────────────────────────
log "Virtualenv & Abhängigkeiten"
[[ -x "$APP_DIR/venv/bin/python" ]] || python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --quiet --upgrade pip
"$APP_DIR/venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"

# Der Code selbst wird nur gelesen — Eigentümer bleibt root, damit der
# Dienst sich nicht selbst überschreiben kann.
chown -R root:root "$APP_DIR"
chmod -R go-w "$APP_DIR"

# ── 6. Environment-Datei ─────────────────────────────────────────────────
# Nur anlegen, wenn sie fehlt — sonst würden bei jedem Lauf evtl. eingetragene
# Entra-Secrets überschrieben.
if [[ -f "$ENV_FILE" ]]; then
    log "Environment-Datei $ENV_FILE existiert bereits — bleibt unverändert"
else
    log "Environment-Datei $ENV_FILE anlegen"
    mkdir -p "$(dirname "$ENV_FILE")"
    cat > "$ENV_FILE" <<EOF
# Konfiguration des IT-Bestandsaufnahme-Tools.
# Nach Änderungen: systemctl restart ${APP_NAME}

BESTANDSAUFNAHME_DATA_DIR=${DATA_DIR}

# ── Entra ID (Azure AD) SSO — aktuell deaktiviert ───────────────────────
# Solange diese drei Werte leer sind, läuft das Tool OHNE Login. Der Zugriff
# ist dann ausschliesslich durch die IP-Beschränkung in der nginx-Site
# geschützt. Zum Aktivieren: Werte eintragen, SESSION_SECRET_KEY setzen,
# Dienst neu starten — und erst danach die IP-Beschränkung lockern.
#ENTRA_TENANT_ID=
#ENTRA_CLIENT_ID=
#ENTRA_CLIENT_SECRET=
#SESSION_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
EOF
fi
chown root:"$APP_USER" "$ENV_FILE"
chmod 640 "$ENV_FILE"

# ── 7. systemd-Service ───────────────────────────────────────────────────
log "systemd-Service einrichten"
sed \
    -e "s|__APP_USER__|${APP_USER}|g" \
    -e "s|__APP_DIR__|${APP_DIR}|g" \
    -e "s|__DATA_DIR__|${DATA_DIR}|g" \
    -e "s|__ENV_FILE__|${ENV_FILE}|g" \
    -e "s|__PORT__|${PORT}|g" \
    "$SCRIPT_DIR/bestandsaufnahme-tool.service" > "/etc/systemd/system/${APP_NAME}.service"

systemctl daemon-reload
systemctl enable --quiet "$APP_NAME"
systemctl restart "$APP_NAME"

# ── 8. nginx-Reverse-Proxy ───────────────────────────────────────────────
if [[ "$SKIP_NGINX" == "1" ]]; then
    log "nginx übersprungen (SKIP_NGINX=1)"
else
    log "nginx-Site einrichten"

    if [[ -z "${ALLOW_CIDRS// /}" ]]; then
        die "ALLOW_CIDRS ist leer. Ohne aktiven Login wäre das Tool damit offen im Netz.
       Entweder erlaubte Netze setzen (ALLOW_CIDRS=\"10.0.0.0/8\") oder
       bewusst SKIP_NGINX=1 verwenden und den Zugriff anderweitig absichern."
    fi

    ALLOW_RULES=""
    for cidr in $ALLOW_CIDRS; do
        ALLOW_RULES+="    allow ${cidr};"$'\n'
    done
    # 127.0.0.1 immer erlauben, sonst schlägt der Health-Check unten fehl.
    ALLOW_RULES+="    allow 127.0.0.1;"

    SITE="/etc/nginx/sites-available/${APP_NAME}"
    python3 - "$SCRIPT_DIR/nginx-site.conf" "$SITE" "$SERVER_NAME" "$PORT" "$ALLOW_RULES" <<'PY'
import sys
src, dst, server_name, port, allow_rules = sys.argv[1:6]
# Bewusst Python statt sed: die allow-Regeln sind mehrzeilig, was sed-
# Ersetzungen unnötig fummelig machen würde.
conf = open(src, encoding="utf-8").read()
conf = conf.replace("__SERVER_NAME__", server_name)
conf = conf.replace("__PORT__", port)
conf = conf.replace("__ALLOW_RULES__", allow_rules)
open(dst, "w", encoding="utf-8").write(conf)
PY

    ln -sfn "$SITE" "/etc/nginx/sites-enabled/${APP_NAME}"

    # Die Default-Site würde sonst als erster server-Block ohne server_name
    # alle Anfragen abfangen, die nicht auf SERVER_NAME passen.
    if [[ -e /etc/nginx/sites-enabled/default ]]; then
        log "nginx-Default-Site deaktivieren"
        rm -f /etc/nginx/sites-enabled/default
    fi

    nginx -t
    systemctl reload nginx
fi

# ── 9. Health-Check ──────────────────────────────────────────────────────
log "Health-Check"
for _ in $(seq 1 15); do
    if curl -fsS -o /dev/null "http://127.0.0.1:${PORT}/auftrag"; then
        HEALTHY=1
        break
    fi
    sleep 1
done

if [[ "${HEALTHY:-0}" != "1" ]]; then
    warn "Anwendung antwortet auf 127.0.0.1:${PORT} nicht. Logs:"
    journalctl -u "$APP_NAME" -n 30 --no-pager >&2 || true
    exit 1
fi

cat <<EOF

$(log "Installation abgeschlossen")

  Code:          $APP_DIR
  Daten:         $DATA_DIR
  Konfiguration: $ENV_FILE
  Dienst:        systemctl status $APP_NAME
  Logs:          journalctl -u $APP_NAME -f
  Update:        sudo $APP_DIR/deploy/update.sh

  Erreichbar über nginx auf Port 80 — freigegebene Netze:
$(for c in $ALLOW_CIDRS; do echo "    - $c"; done)

  ACHTUNG: Es ist kein Login aktiv. Die IP-Beschränkung ist derzeit die
  einzige Zugriffskontrolle vor den Kundendaten. Vor der Nutzung mit
  echten Kundendaten aus dem offenen Internet sollte Entra-ID-SSO
  aktiviert und TLS eingerichtet werden (siehe README).

EOF
