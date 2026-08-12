from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from app.config import BASE_DIR
from app.services.storage import storage
from app.services.evaluator import evaluator_service

router = APIRouter()
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))

@router.get("/auftrag/{auftrag_id}/bewertung")
def bewertung_dashboard(request: Request, auftrag_id: str):
    auftrag = storage.load_auftrag(auftrag_id)
    if not auftrag:
        return RedirectResponse(url="/auftrag", status_code=303)

    objekte = storage.list_objekte(auftrag_id)
    bewertung = evaluator_service.evaluate_auftrag(auftrag.aktive_bausteine, objekte)

    return templates.TemplateResponse(
        request=request,
        name="bewertung/index.html",
        context={
            "auftrag": auftrag,
            "bewertung": bewertung,
            "active_tab": "bewertung",
            "active_nav": "auftrag"
        }
    )
