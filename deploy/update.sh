#!/usr/bin/env bash
#
# Aktualisiert eine bestehende Installation und startet den Dienst neu.
#
#   sudo /opt/bestandsaufnahme-tool/deploy/update.sh              # Code holen + neu starten
#   sudo /opt/bestandsaufnahme-tool/deploy/update.sh --restart    # nur neu starten
#
# "--restart" ist für das Arbeiten direkt auf dem Server gedacht: Code im
# Checkout ändern, neu starten, im Browser prüfen — ohne dass ein git pull
# die gerade gemachten Änderungen anfasst.
#
set -euo pipefail

APP_NAME="${APP_NAME:-bestandsaufnahme-tool}"
APP_DIR="${APP_DIR:-/opt/${APP_NAME}}"
PORT="${PORT:-8000}"
BRANCH="${BRANCH:-main}"

RESTART_ONLY=0
[[ "${1:-}" == "--restart" ]] && RESTART_ONLY=1

log()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!!\033[0m  %s\n' "$*" >&2; }
die()  { printf '\033[1;31mFEHLER:\033[0m %s\n' "$*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "Bitte mit sudo/root ausführen."
[[ -d "$APP_DIR/.git" ]] || die "$APP_DIR ist kein Git-Checkout — zuerst deploy/install.sh ausführen."

if [[ "$RESTART_ONLY" == "0" ]]; then
    if [[ -n "$(git -C "$APP_DIR" status --porcelain)" ]]; then
        die "$APP_DIR hat uncommittete Änderungen.
       Entweder committen/stashen, oder '--restart' verwenden, um die
       lokalen Änderungen zu behalten und nur den Dienst neu zu starten."
    fi

    log "Code aktualisieren ($BRANCH)"
    BEFORE="$(git -C "$APP_DIR" rev-parse HEAD)"
    git -C "$APP_DIR" fetch --quiet origin "$BRANCH"
    git -C "$APP_DIR" checkout --quiet "$BRANCH"
    git -C "$APP_DIR" merge --quiet --ff-only "origin/$BRANCH"
    AFTER="$(git -C "$APP_DIR" rev-parse HEAD)"

    if [[ "$BEFORE" == "$AFTER" ]]; then
        log "Bereits aktuell ($(git -C "$APP_DIR" log -1 --format=%h))"
    else
        log "$(git -C "$APP_DIR" log --oneline "$BEFORE..$AFTER" | wc -l) neue Commits"
        git -C "$APP_DIR" log --oneline "$BEFORE..$AFTER"
    fi

    # Abhängigkeiten nur neu installieren, wenn sich requirements.txt geändert
    # hat — spart bei reinen Code-Updates den Grossteil der Laufzeit.
    if [[ "$BEFORE" != "$AFTER" ]] && \
       ! git -C "$APP_DIR" diff --quiet "$BEFORE" "$AFTER" -- requirements.txt; then
        log "requirements.txt geändert — Abhängigkeiten aktualisieren"
        "$APP_DIR/venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"
    fi

    chown -R root:root "$APP_DIR"
    chmod -R go-w "$APP_DIR"
fi

log "Dienst neu starten"
systemctl restart "$APP_NAME"

log "Health-Check"
for _ in $(seq 1 15); do
    if curl -fsS -o /dev/null "http://127.0.0.1:${PORT}/auftrag"; then
        log "Läuft: $(git -C "$APP_DIR" log -1 --format='%h %s')"
        exit 0
    fi
    sleep 1
done

warn "Anwendung antwortet auf 127.0.0.1:${PORT} nicht. Logs:"
journalctl -u "$APP_NAME" -n 30 --no-pager >&2 || true
exit 1
