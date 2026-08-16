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

    standort_by_id = {s.id: s for s in standorte}

    # Hierarchische Struktur: Standort -> Thema/Baustein -> Punkte
    standort_groups = {}
    for s in standorte:
        standort_groups[s.id] = {
            "id": s.id,
            "name": s.bezeichnung,
            "typ": "standort",
            "themen": {},
            "total_count": 0
        }

    allgemein_id = "_allgemein"
    standort_groups[allgemein_id] = {
        "id": allgemein_id,
        "name": "Standortübergreifend / Allgemein",
        "typ": "allgemein",
        "themen": {},
        "total_count": 0
    }

    for op in offene_punkte:
        target_sto_id = None
        if op.standort_id and op.standort_id in standort_groups:
            target_sto_id = op.standort_id
        else:
            for s in standorte:
                if s.bezeichnung in op.text or s.id in (op.ziel_url or ""):
                    target_sto_id = s.id
                    break
        if not target_sto_id:
            target_sto_id = allgemein_id

        # Themenbereich / Baustein-Label ermitteln
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
                comp_label = "Fehlende Bausteine"
            elif op.quelle == "dokument":
                comp_label = "Dokumente & Unterlagen"
            elif "Firewall" in op.text or "firewall" in (op.ziel_url or ""):
                comp_label = "Firewall-System"
            else:
                comp_label = "Standort-Stammdaten & Anbindung"

        sto_entry = standort_groups[target_sto_id]
        sto_entry["total_count"] += 1
        if comp_label not in sto_entry["themen"]:
            sto_entry["themen"][comp_label] = {
                "name": comp_label,
                "count": 0,
                "punkte": []
            }
        sto_entry["themen"][comp_label]["punkte"].append(op)
        sto_entry["themen"][comp_label]["count"] += 1

    # Nur befüllte Gruppen weitergeben
    grouped_standorte = []
    for s in standorte:
        g = standort_groups[s.id]
        if g["total_count"] > 0:
            g["themen_list"] = list(g["themen"].values())
            grouped_standorte.append(g)

    g_allg = standort_groups[allgemein_id]
    if g_allg["total_count"] > 0:
        g_allg["themen_list"] = list(g_allg["themen"].values())
        grouped_standorte.append(g_allg)

    # Abwärtskompatibles grouped_punkte dict
    grouped_punkte = {}
    for g in grouped_standorte:
        grouped_punkte[g["name"]] = {t["name"]: t["punkte"] for t in g["themen_list"]}

    sidebar_context = build_sidebar_context(auftrag)
    return templates.TemplateResponse(
        request=request,
        name="offene_punkte/index.html",
        context={
            "auftrag": auftrag,
            "offene_punkte": offene_punkte,
            "grouped_standorte": grouped_standorte,
            "grouped_punkte": grouped_punkte,
            "active_tab": "offene_punkte",
            "active_nav": "auftrag",
            **sidebar_context
        }
    )
