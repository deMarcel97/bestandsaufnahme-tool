"""Erfassungsseite für Auftrag.versionshistorie (Karte #350).

Verwaltet die Dokumenten- und Berichtsversionen eines Auftrags (z.B. v0.1 Analyse Hauptstandort,
v0.2 Nebenstandort, v0.3 Nacharbeiten, v1.0 Finalisierung).
"""

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.models.auftrag import VersionsEintrag
from app.services.storage import storage, KonfliktFehler
from app.utils.number_parser import parse_int_german
from app.web.formular_listen import parse_unterobjekte
from app.web.shared_context import build_sidebar_context, aktuelle_version
from app.web.templates import templates

router = APIRouter()

VERSION_STATUS_OPTIONS = ["Entwurf", "In Prüfung", "Freigegeben"]


@router.get("/auftrag/{auftrag_id}/versionierung")
def versionierung_form(request: Request, auftrag_id: str):
    auftrag = storage.load_auftrag(auftrag_id)
    if not auftrag:
        return RedirectResponse(url="/auftrag", status_code=303)

    sidebar_context = build_sidebar_context(auftrag)
    return templates.TemplateResponse(
        request=request,
        name="auftrag/versionierung.html",
        context={
            "auftrag": auftrag,
            "version_status_options": VERSION_STATUS_OPTIONS,
            "active_tab": "versionierung",
            "active_nav": "auftrag",
            **sidebar_context
        }
    )


@router.post("/auftrag/{auftrag_id}/versionierung")
async def versionierung_submit(request: Request, auftrag_id: str):
    auftrag = storage.load_auftrag(auftrag_id)
    if not auftrag:
        return RedirectResponse(url="/auftrag", status_code=303)

    form_data = await request.form()
    auftrag.versionshistorie = parse_unterobjekte(form_data, "ver", VersionsEintrag)

    auftrag.version = parse_int_german(form_data.get("version"), auftrag.version)

    try:
        storage.save_auftrag(auftrag)
    except KonfliktFehler:
        auftrag.version = aktuelle_version(auftrag_id, auftrag.version)
        sidebar_context = build_sidebar_context(auftrag)
        return templates.TemplateResponse(
            request=request,
            name="auftrag/versionierung.html",
            status_code=409,
            context={
                "auftrag": auftrag,
                "version_status_options": VERSION_STATUS_OPTIONS,
                "konflikt": True,
                "active_tab": "versionierung",
                "active_nav": "auftrag",
                **sidebar_context
            }
        )

    return RedirectResponse(url=f"/auftrag/{auftrag_id}/versionierung", status_code=303)
