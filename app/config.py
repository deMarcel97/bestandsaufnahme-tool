import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Nutzdaten (Aufträge, Standorte, Objekte, Findings) liegen lokal im
# Projektverzeichnis. Im Serverbetrieb muss das Datenverzeichnis dagegen
# ausserhalb des Code-Checkouts liegen (z.B. /var/lib/bestandsaufnahme-tool/data),
# damit ein Code-Update die Kundendaten nicht anfasst und der systemd-Service
# mit ProtectSystem=strict nur genau dieses eine Verzeichnis schreiben darf.
# Bewusst mit Prefix statt schlicht DATA_DIR: ein generischer Name könnte in
# einer Shell bereits für etwas anderes gesetzt sein, und die Anwendung würde
# Kundendaten dann unbemerkt woanders hinschreiben.
DATA_DIR = Path(os.environ.get("BESTANDSAUFNAHME_DATA_DIR") or (BASE_DIR / "data")).resolve()

# Schemas, Regelwerke und Bewertungslogik sind Teil des Codes und werden
# zusammen mit ihm ausgeliefert — daher bewusst nicht konfigurierbar.
SCHEMAS_DIR = BASE_DIR / "schemas"
RULES_DIR = BASE_DIR / "rules"
BEWERTUNG_DIR = BASE_DIR / "bewertung"

# Ensure data dir exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── Entra ID (Azure AD) SSO ─────────────────────────────────────────────
# Alle Werte kommen aus einer echten App-Registrierung im Entra-ID-Tenant
# (Azure Portal -> App registrations). Ohne diese drei Werte bleibt Auth
# deaktiviert und das Tool verhält sich wie bisher (lokales Single-User-Tool
# ohne Login) — so bleiben lokale Entwicklung und Tests unverändert lauffähig.
ENTRA_TENANT_ID = os.environ.get("ENTRA_TENANT_ID", "")
ENTRA_CLIENT_ID = os.environ.get("ENTRA_CLIENT_ID", "")
ENTRA_CLIENT_SECRET = os.environ.get("ENTRA_CLIENT_SECRET", "")
ENTRA_REDIRECT_PATH = "/auth/callback"

AUTH_ENABLED = bool(ENTRA_TENANT_ID and ENTRA_CLIENT_ID and ENTRA_CLIENT_SECRET)

# Nur für Sessions/Cookie-Signierung relevant, wenn AUTH_ENABLED. Ohne
# gesetzte SESSION_SECRET_KEY wird bei jedem Prozessstart ein neuer
# zufälliger Schlüssel erzeugt (bestehende Sessions werden dann ungültig) —
# für einen Mehrprozess-/Produktionsbetrieb hinter Entra ID sollte
# SESSION_SECRET_KEY daher fest gesetzt werden.
SESSION_SECRET_KEY = os.environ.get("SESSION_SECRET_KEY") or secrets.token_hex(32)
