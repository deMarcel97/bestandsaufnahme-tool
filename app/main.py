from urllib.parse import urlparse
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from app.config import BASE_DIR, AUTH_ENABLED, SESSION_SECRET_KEY, APP_VERSION
from app.services.storage import KonfliktFehler
from app.web import (
    routes_auftrag,
    routes_standort,
    routes_objekt,
    routes_findings,
    routes_massnahmen,
    routes_bewertung,
    routes_offene_punkte,
    routes_export,
    routes_auth,
    routes_beteiligte,
    routes_vertraege,
    routes_unterlagen,
    routes_projektrahmen,
    routes_wizard,
    routes_versionierung,
)

app = FastAPI(title="IT-Bestandsaufnahme Tool", version=APP_VERSION)

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(BASE_DIR / "app" / "static" / "favicon.svg", media_type="image/svg+xml")

from starlette.exceptions import HTTPException as StarletteHTTPException
from app.web.templates import templates

UNSAFE_METHODS = {"POST", "PUT", "DELETE", "PATCH"}
PUBLIC_PATH_PREFIXES = ("/auth/", "/static/", "/favicon.ico")

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
    von Sec-Fetch-Site bzw. Origin/Referer gegen den Host geprüft."""
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

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Setzt restriktive HTTP Security-Headers für alle Requests (#373)."""
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' data: https://fonts.gstatic.com; "
        "img-src 'self' data: https: blob:; "
        "connect-src 'self';"
    )
    return response

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Liefert für 404-Fehler im Browser eine ansprechende HTML-Fehlerseite (#375)."""
    if exc.status_code == 404:
        accept = request.headers.get("accept", "")
        if "text/html" in accept or "*/*" in accept:
            return templates.TemplateResponse(
                request=request,
                name="errors/404.html",
                context={"request": request, "status_code": 404, "detail": exc.detail},
                status_code=404
            )
    return PlainTextResponse(str(exc.detail), status_code=exc.status_code)

@app.exception_handler(500)
async def custom_500_handler(request: Request, exc: Exception):
    """Liefert für 500-Fehler im Browser eine HTML-Fehlerseite (#375)."""
    accept = request.headers.get("accept", "")
    if "text/html" in accept or "*/*" in accept:
        return templates.TemplateResponse(
            request=request,
            name="errors/500.html",
            context={"request": request, "status_code": 500, "detail": "Interner Serverfehler"},
            status_code=500
        )
    return PlainTextResponse("Interner Serverfehler", status_code=500)

@app.exception_handler(KonfliktFehler)
async def konflikt_handler(request: Request, exc: KonfliktFehler):
    """Zeigt einen verständlichen Hinweis, statt den Nutzer mit einem
    Serverfehler stehenzulassen.

    Bewusst als zentraler Handler und nicht in jeder Route: der Konflikt kann
    an jeder Speicherstelle auftreten, und die Antwort ist überall dieselbe.
    Bewusst auch ohne Template — die Seite muss selbst dann noch darstellbar
    sein, wenn das Problem beim Laden von Daten liegt."""
    name = exc.bezeichnung or "Der Datensatz"
    return HTMLResponse(
        status_code=409,
        content=f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8">
<title>Änderung nicht gespeichert</title>
<link rel="stylesheet" href="/static/css/style.css"></head>
<body><div class="container" style="max-width:640px;margin-top:64px;">
<h1 style="font-size:22px;">Änderung nicht gespeichert</h1>
<p><strong>{name}</strong> wurde zwischenzeitlich von jemand anderem geändert.</p>
<p>Damit die fremden Änderungen nicht verlorengehen, wurde nichts überschrieben.
Lade die Seite neu, um den aktuellen Stand zu sehen, und trage deine Änderung
danach erneut ein.</p>
<p style="margin-top:28px;"><a href="javascript:history.back()">Zurück zum Formular</a>
&nbsp;·&nbsp; <a href="/auftrag">Zur Auftragsübersicht</a></p>
</div></body></html>""",
    )

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
app.include_router(routes_beteiligte.router)
app.include_router(routes_vertraege.router)
app.include_router(routes_unterlagen.router)
app.include_router(routes_projektrahmen.router)
app.include_router(routes_wizard.router)
app.include_router(routes_versionierung.router)
