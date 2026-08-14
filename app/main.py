from urllib.parse import urlparse
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from app.config import BASE_DIR
from app.web import (
    routes_auftrag,
    routes_standort,
    routes_objekt,
    routes_findings,
    routes_massnahmen,
    routes_bewertung,
    routes_offene_punkte,
    routes_export
)

app = FastAPI(title="IT-Bestandsaufnahme Tool", version="2.1.0")

UNSAFE_METHODS = {"POST", "PUT", "DELETE", "PATCH"}

@app.middleware("http")
async def block_cross_site_writes(request: Request, call_next):
    """Leichtgewichtiger CSRF-Schutz für ein lokales Single-User-Tool ohne
    Sessions/Auth: state-changing Requests werden anhand von Sec-Fetch-Site
    bzw. Origin/Referer gegen den Host geprüft, statt ein volles
    Token-basiertes CSRF-System einzuführen. Fehlen alle drei Header (z.B.
    curl, Testclients), wird durchgelassen."""
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

# Mount Static Files
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")

# Include Web Routers
app.include_router(routes_auftrag.router)
app.include_router(routes_standort.router)
app.include_router(routes_objekt.router)
app.include_router(routes_findings.router)
app.include_router(routes_massnahmen.router)
app.include_router(routes_bewertung.router)
app.include_router(routes_offene_punkte.router)
app.include_router(routes_export.router)
