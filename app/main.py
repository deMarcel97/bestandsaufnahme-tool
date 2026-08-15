from urllib.parse import urlparse
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from app.config import BASE_DIR, AUTH_ENABLED, SESSION_SECRET_KEY, APP_VERSION
from app.web import (
    routes_auftrag,
    routes_standort,
    routes_objekt,
    routes_findings,
    routes_massnahmen,
    routes_bewertung,
    routes_offene_punkte,
    routes_export,
    routes_auth
)

app = FastAPI(title="IT-Bestandsaufnahme Tool", version=APP_VERSION)

UNSAFE_METHODS = {"POST", "PUT", "DELETE", "PATCH"}
PUBLIC_PATH_PREFIXES = ("/auth/", "/static/")

@app.middleware("http")
async def require_entra_login(request: Request, call_next):
    """Erzwingt einen gültigen Entra-ID-Login für alle Seiten, sobald
    AUTH_ENABLED ist (siehe app/config.py). Ist keine Entra-ID-App-
    Registrierung konfiguriert, bleibt das Tool wie bisher ohne Login
    nutzbar (lokales Single-User-Setup)."""
    if AUTH_ENABLED and not request.url.path.startswith(PUBLIC_PATH_PREFIXES):
        if not request.session.get("user"):
            return RedirectResponse(url="/auth/login", status_code=303)
    return await call_next(request)

@app.middleware("http")
async def block_cross_site_writes(request: Request, call_next):
    """Leichtgewichtiger CSRF-Schutz: state-changing Requests werden anhand
    von Sec-Fetch-Site bzw. Origin/Referer gegen den Host geprüft, statt ein
    volles Token-basiertes CSRF-System einzuführen. Fehlen alle drei Header
    (z.B. curl, Testclients), wird durchgelassen."""
    if request.method in UNSAFE_METHODS:
        sec_fetch_site = request.headers.get("sec-fetch-site")
        if sec_fetch_site is not None:
            if sec_fetch_site == "cross-site":
                return PlainTextResponse("Cross-site request blocked", status_code=403)
        else:
            host = request.headers.get("host", "")
            candidate = request.headers.get("origin") or request.headers.get("referer")
            if candidate:
                candidate_host = urlparse(candidate).netloc
                if candidate_host and candidate_host != host:
                    return PlainTextResponse("Cross-site request blocked", status_code=403)
    return await call_next(request)

# SessionMiddleware muss zuletzt hinzugefügt werden, damit sie in Starlettes
# Stack außen liegt und request.session bereits in den obigen
# @app.middleware("http")-Funktionen verfügbar ist.
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY, same_site="lax")

# Mount Static Files
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")

# Include Web Routers
app.include_router(routes_auth.router)
app.include_router(routes_auftrag.router)
app.include_router(routes_standort.router)
app.include_router(routes_objekt.router)
app.include_router(routes_findings.router)
app.include_router(routes_massnahmen.router)
app.include_router(routes_bewertung.router)
app.include_router(routes_offene_punkte.router)
app.include_router(routes_export.router)
