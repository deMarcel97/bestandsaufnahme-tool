from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from app.config import BASE_DIR
from app.services.storage import storage
from app.services.progress import progress_service

router = APIRouter()
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))

@router.get("/auftrag/{auftrag_id}/offene_punkte")
def offene_punkte_page(request: Request, auftrag_id: str):
    auftrag = storage.load_auftrag(auftrag_id)
    if not auftrag:
        return RedirectResponse(url="/auftrag", status_code=303)

    standorte = storage.list_standorte(auftrag_id)
    objekte = storage.list_objekte(auftrag_id)
    offene_punkte = progress_service.collect_offene_punkte(auftrag, standorte, objekte, [])

    # Group open points hierarchically: standort -> geraet/komponente -> items
    grouped: dict = {}
    for s in standorte:
        grouped[s.bezeichnung] = {}
    grouped["Allgemein / Unternehmenskontext"] = {}

    for op in offene_punkte:
        matched_sto = None
        for s in standorte:
            if s.bezeichnung in op.text or s.id in op.ziel_url:
                matched_sto = s.bezeichnung
                break
        if not matched_sto:
            matched_sto = "Allgemein / Unternehmenskontext"

        # Determine device / component label
        comp_label = "Standort-Stammdaten & Anbindung"
        if op.quelle == "struktur_fehlt":
            comp_label = "Fehlende Erfassung"
        elif "Gerät '" in op.text:
            try:
                comp_label = op.text.split("Gerät '")[1].split("'")[0]
            except IndexError:
                pass
        elif "Firewall" in op.text or "firewall" in op.ziel_url:
            comp_label = "Firewall-System"

        if comp_label not in grouped[matched_sto]:
            grouped[matched_sto][comp_label] = []

        grouped[matched_sto][comp_label].append(op)

    return templates.TemplateResponse(
        request=request,
        name="offene_punkte/index.html",
        context={
            "auftrag": auftrag,
            "offene_punkte": offene_punkte,
            "grouped_punkte": grouped,
            "active_tab": "offene_punkte",
            "active_nav": "auftrag"
        }
    )
