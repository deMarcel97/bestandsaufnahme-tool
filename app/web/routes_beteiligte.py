"""Erfassungsseite für Auftrag.beteiligte (Karte #316).

Die Beteiligten-Liste ist ein Unterobjekt-Formular wie die Internetanbindungen
eines Standorts, nur ohne deren Sonderfälle — deshalb hier über
`parse_unterobjekte` statt über einen eigenen Parser (siehe
app/web/formular_listen.py).
"""

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.models.auftrag import Beteiligter
from app.services.storage import storage, KonfliktFehler
from app.utils.number_parser import parse_int_german
from app.web.formular_listen import parse_unterobjekte
from app.web.shared_context import build_sidebar_context, aktuelle_version
from app.web.templates import templates

router = APIRouter()


@router.get("/auftrag/{auftrag_id}/beteiligte")
def beteiligte_form(request: Request, auftrag_id: str):
    auftrag = storage.load_auftrag(auftrag_id)
    if not auftrag:
        return RedirectResponse(url="/auftrag", status_code=303)

    objekte = storage.list_objekte(auftrag_id)
    sidebar_context = build_sidebar_context(auftrag, objekte=objekte)
    return templates.TemplateResponse(
        request=request,
        name="auftrag/beteiligte.html",
        context={
            "auftrag": auftrag,
            "objekte": objekte,
            "active_tab": "beteiligte",
            "active_nav": "auftrag",
            **sidebar_context
        }
    )


@router.post("/auftrag/{auftrag_id}/beteiligte")
async def beteiligte_submit(request: Request, auftrag_id: str):
    auftrag = storage.load_auftrag(auftrag_id)
    if not auftrag:
        return RedirectResponse(url="/auftrag", status_code=303)

    form_data = await request.form()
    auftrag.beteiligte = parse_unterobjekte(form_data, "beteiligter", Beteiligter)

    # Massgeblich ist der Stand, den das Formular beim Laden gesehen hat — nicht
    # der frisch geladene. Sonst stimmt die Version beim Speichern immer überein
    # und die Konflikterkennung könnte nie anschlagen (Karte #308).
    auftrag.version = parse_int_german(form_data.get("version"), auftrag.version)

    try:
        storage.save_auftrag(auftrag)
    except KonfliktFehler:
        auftrag.version = aktuelle_version(auftrag_id, auftrag.version)
        objekte = storage.list_objekte(auftrag_id)
        sidebar_context = build_sidebar_context(auftrag, objekte=objekte)
        return templates.TemplateResponse(
            request=request,
            name="auftrag/beteiligte.html",
            status_code=409,
            context={
                "auftrag": auftrag,
                "objekte": objekte,
                "konflikt": True,
                "active_tab": "beteiligte",
                "active_nav": "auftrag",
                **sidebar_context
            }
        )

    return RedirectResponse(url=f"/auftrag/{auftrag_id}/beteiligte", status_code=303)


