from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from app.services.storage import storage
from app.services.progress import progress_service
from app.services.schema_loader import schema_loader
from app.web.templates import templates
from app.web.shared_context import build_sidebar_context

router = APIRouter()

def _hardware_label(typ: str) -> str:
    schema = schema_loader.get_schema(typ)
    return schema.get("bezeichnung_anzeige", typ.capitalize()) if schema else typ.capitalize()

@router.get("/auftrag/{auftrag_id}/offene_punkte")
def offene_punkte_page(request: Request, auftrag_id: str):
    auftrag = storage.load_auftrag(auftrag_id)
    if not auftrag:
        return RedirectResponse(url="/auftrag", status_code=303)

    standorte = storage.list_standorte(auftrag_id)
    objekte = storage.list_objekte(auftrag_id)
    offene_punkte = progress_service.collect_offene_punkte(auftrag, standorte, objekte, [])

    standort_by_id = {s.id: s.bezeichnung for s in standorte}

    # Group open points hierarchically: standort -> hardware/komponente -> items
    grouped: dict = {}
    for s in standorte:
        grouped[s.bezeichnung] = {}
    grouped["Allgemein / Unternehmenskontext"] = {}

    for op in offene_punkte:
        matched_sto = standort_by_id.get(op.standort_id)
        if not matched_sto:
            for s in standorte:
                if s.bezeichnung in op.text or s.id in op.ziel_url:
                    matched_sto = s.bezeichnung
                    break
        if not matched_sto:
            matched_sto = "Allgemein / Unternehmenskontext"

        # Determine hardware/component label
        comp_label = None
        if op.objekt_typ:
            comp_label = _hardware_label(op.objekt_typ)
        else:
            obj_match = None
            if "Objekt '" in op.text:
                try:
                    obj_name = op.text.split("Objekt '")[1].split("'")[0]
                    obj_match = next((o for o in objekte if o.bezeichnung == obj_name), None)
                except IndexError:
                    pass
            if not obj_match and op.ziel_url:
                for o in objekte:
                    if o.id in op.ziel_url:
                        obj_match = o
                        break
            if obj_match:
                comp_label = _hardware_label(obj_match.typ)

        if not comp_label:
            if op.quelle == "struktur_fehlt":
                comp_label = "Fehlende Erfassung"
            elif op.quelle == "dokument":
                comp_label = "Dokumentenanforderungen"
            elif "Firewall" in op.text or "firewall" in (op.ziel_url or ""):
                comp_label = "Firewall-System"
            else:
                comp_label = "Standort-Stammdaten & Anbindung"

        if comp_label not in grouped[matched_sto]:
            grouped[matched_sto][comp_label] = []

        grouped[matched_sto][comp_label].append(op)

    sidebar_context = build_sidebar_context(auftrag)
    return templates.TemplateResponse(
        request=request,
        name="offene_punkte/index.html",
        context={
            "auftrag": auftrag,
            "offene_punkte": offene_punkte,
            "grouped_punkte": grouped,
            "active_tab": "offene_punkte",
            "active_nav": "auftrag",
            **sidebar_context
        }
    )
