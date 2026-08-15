from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from app.services.storage import storage
from app.services.evaluator import evaluator_service
from app.web.templates import templates
from app.web.shared_context import build_sidebar_context

router = APIRouter()

@router.get("/auftrag/{auftrag_id}/bewertung")
def bewertung_dashboard(request: Request, auftrag_id: str):
    auftrag = storage.load_auftrag(auftrag_id)
    if not auftrag:
        return RedirectResponse(url="/auftrag", status_code=303)

    standorte = storage.list_standorte(auftrag_id)
    objekte = storage.list_objekte(auftrag_id)
    bewertung = evaluator_service.evaluate_auftrag(auftrag.aktive_bausteine, objekte, standorte)

    sidebar_context = build_sidebar_context(auftrag)
    return templates.TemplateResponse(
        request=request,
        name="bewertung/index.html",
        context={
            "auftrag": auftrag,
            "bewertung": bewertung,
            "active_tab": "bewertung",
            "active_nav": "auftrag",
            **sidebar_context
        }
    )
