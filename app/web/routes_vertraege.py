"""Erfassung der Verträge eines Auftrags (Karte #316).

Eine beliebig lange Liste, kein Einzeldatensatz — deshalb kein
"Anlegen"-Formular wie bei Standort/Objekt, sondern eine Seite, die die
gesamte Liste auf einmal einliest und ersetzt (siehe `formular_listen.py`).
"""

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.services.storage import storage, KonfliktFehler
from app.web.templates import templates
from app.web.shared_context import build_sidebar_context
from app.web.formular_listen import parse_unterobjekte
from app.models.auftrag import Vertrag
from app.utils.number_parser import parse_int_german

router = APIRouter()


@router.get("/auftrag/{auftrag_id}/vertraege")
def vertraege_form(request: Request, auftrag_id: str):
    auftrag = storage.load_auftrag(auftrag_id)
    if not auftrag:
        return RedirectResponse(url="/auftrag", status_code=303)

    sidebar_context = build_sidebar_context(auftrag)
    return templates.TemplateResponse(
        request=request,
        name="auftrag/vertraege.html",
        context={
            "auftrag": auftrag,
            "active_tab": "vertraege",
            "active_nav": "auftrag",
            **sidebar_context
        }
    )


@router.post("/auftrag/{auftrag_id}/vertraege")
async def vertraege_submit(request: Request, auftrag_id: str):
    auftrag = storage.load_auftrag(auftrag_id)
    if not auftrag:
        return RedirectResponse(url="/auftrag", status_code=303)

    form_data = await request.form()
    auftrag.vertraege = parse_unterobjekte(form_data, "vertrag", Vertrag)

    # Massgeblich ist der Stand, den das Formular beim Laden gesehen hat — nicht
    # der frisch geladene. Sonst stimmt die Version beim Speichern immer überein
    # und die Konflikterkennung könnte nie anschlagen (Karte #308).
    auftrag.version = parse_int_german(form_data.get("version"), auftrag.version)

    try:
        storage.save_auftrag(auftrag)
    except KonfliktFehler:
        auftrag.version = _aktuelle_version(auftrag_id, auftrag.version)
        sidebar_context = build_sidebar_context(auftrag)
        return templates.TemplateResponse(
            request=request,
            name="auftrag/vertraege.html",
            status_code=409,
            context={
                "auftrag": auftrag,
                "konflikt": True,
                "active_tab": "vertraege",
                "active_nav": "auftrag",
                **sidebar_context
            }
        )

    return RedirectResponse(url=f"/auftrag/{auftrag_id}/vertraege", status_code=303)


def _aktuelle_version(auftrag_id: str, fallback: int) -> int:
    """Der Stand, der nach einem Konflikt auf der Platte liegt (siehe
    `routes_auftrag.py::_aktuelle_version`)."""
    aktuell = storage.load_auftrag(auftrag_id)
    return aktuell.version if aktuell else fallback
