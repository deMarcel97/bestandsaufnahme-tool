# Security & Auth

Security-Headers, CSRF-Schutz, Entra-ID-SSO und IP-Beschränkung.

## Karten

- #301: Server-Deployment (Zugriffsbeschränkung)
- #373: Globale Security-Headers

## Beteiligte Dateien

| Datei | Rolle |
|---|---|
| `app/main.py` | Middleware: `require_entra_login`, `block_cross_site_writes`, `add_security_headers` |
| `app/web/routes_auth.py` | Entra-ID-OAuth: Login, Callback, Logout |
| `app/config.py` | `AUTH_ENABLED`, `ENTRA_TENANT_ID`, `ENTRA_CLIENT_ID`, `ENTRA_CLIENT_SECRET` |
| `deploy/nginx-site.conf` | IP-Beschränkung (`ALLOW_CIDRS`) |

## Funktionsweise

### Security-Headers (#373)

Middleware `add_security_headers` setzt:

| Header | Wert |
|---|---|
| `X-Frame-Options` | `SAMEORIGIN` |
| `X-Content-Type-Options` | `nosniff` |
| `X-XSS-Protection` | `1; mode=block` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | (restriktiv) |
| `Content-Security-Policy` | (restriktiv) |

### CSRF-Schutz

Middleware `block_cross_site_writes`:
- Prüft `Sec-Fetch-Site` und `Origin` bei POST-Requests.
- Blockiert Cross-Site-POSTs.

### Entra-ID-SSO (#301)

- Login-Flow gegen Microsoft Entra ID (Azure AD).
- Standardmäßig **deaktiviert** -- ohne `ENTRA_*`-Variablen läuft die Anwendung als lokales Tool ohne Login.
- Aktivierung: `ENTRA_TENANT_ID`, `ENTRA_CLIENT_ID`, `ENTRA_CLIENT_SECRET` setzen.
- `SESSION_SECRET_KEY` für Cookie-Signierung (sonst zufällig pro Prozessstart).
- Bei aktiviertem Login: jede Seite verlangt gültigen Entra-ID-Login (`require_entra_login`).
- Redirect-URI: `https://<host>/auth/callback`.

### IP-Beschränkung (#301)

- nginx-Site beschränkt Zugriff auf konfigurierbare Quell-Netze (`ALLOW_CIDRS`, Default RFC1918).
- `install.sh` bricht ab, wenn `ALLOW_CIDRS` leer ist.
- Solange kein Entra-ID-Login aktiv: IP-Beschränkung ist die **einzige** Zugriffskontrolle.

### SessionMiddleware

- `same_site="lax"` Cookies.
- Als äußerste Middleware im Starlette-Stack hinzugefügt.
