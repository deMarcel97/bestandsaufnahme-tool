from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from app.services.storage import storage
from app.services.slug import generate_slug_id
from app.web.templates import templates
from app.web.shared_context import build_sidebar_context
from app.models.massnahme import Massnahme
from app.utils.number_parser import parse_float_german, parse_int_german

router = APIRouter()

@router.get("/auftrag/{auftrag_id}/massnahmen")
def list_massnahmen_page(request: Request, auftrag_id: str):
    auftrag = storage.load_auftrag(auftrag_id)
    if not auftrag:
        return RedirectResponse(url="/auftrag", status_code=303)

    massnahmen = storage.list_massnahmen(auftrag_id)

    transferred = request.query_params.get("transferred")
    skipped = request.query_params.get("skipped")
    offen = request.query_params.get("offen")
    verworfen = request.query_params.get("verworfen")
    uebernommen = request.query_params.get("uebernommen")

    sidebar_context = build_sidebar_context(auftrag)
    return templates.TemplateResponse(
        request=request,
        name="massnahmen/index.html",
        context={
            "auftrag": auftrag,
            "massnahmen": massnahmen,
            "transferred": transferred,
            "skipped": skipped,
            "offen": offen,
            "verworfen": verworfen,
            "uebernommen": uebernommen,
            "active_tab": "massnahmen",
            "active_nav": "auftrag",
            **sidebar_context
        }
    )

@router.post("/auftrag/{auftrag_id}/massnahme/neu")
def new_massnahme_submit(
    auftrag_id: str,
    bezeichnung: str = Form(...),
    beschreibung: str = Form(""),
    stufe: str = Form("2"),
    prioritaet: str = Form("mittel"),
    dringlichkeit: str = Form("mittel"),
    status: str = Form("vorgeschlagen"),
    investitionskosten: str = Form("0.0"),
    monatliche_kosten: str = Form("0.0"),
    zeitaufwand: str = Form("0.0"),
    zeitaufwand_einheit: str = Form("Stunden"),
    foerderprogramm: str = Form("")
):
    massnahmen = storage.list_massnahmen(auftrag_id)
    mid = generate_slug_id("massnahme", bezeichnung, [m.id for m in massnahmen])

    inv_val = parse_float_german(investitionskosten)
    mon_val = parse_float_german(monatliche_kosten)
    zeit_val = parse_float_german(zeitaufwand)
    stufe_val = parse_int_german(stufe, 2)

    new_m = Massnahme(
        schema_version=1,
        id=mid,
        bezeichnung=bezeichnung,
        beschreibung=beschreibung,
        stufe=stufe_val,
        prioritaet=prioritaet,
        dringlichkeit=dringlichkeit,
        status=status,
        investitionskosten=inv_val,
        monatliche_kosten=mon_val,
        zeitaufwand=zeit_val,
        zeitaufwand_einheit=zeitaufwand_einheit,
        foerderprogramm=foerderprogramm,
        kosten_quelle="manuell" if (inv_val > 0 or mon_val > 0 or zeit_val > 0) else "offen"
    )
    massnahmen.append(new_m)
    storage.save_massnahmen(auftrag_id, massnahmen)
    return RedirectResponse(url=f"/auftrag/{auftrag_id}/massnahmen", status_code=303)

@router.post("/auftrag/{auftrag_id}/massnahme/{massnahme_id}/kosten")
def update_massnahme_kosten(
    auftrag_id: str,
    massnahme_id: str,
    investitionskosten: str = Form("0.0"),
    monatliche_kosten: str = Form("0.0")
):
    massnahmen = storage.list_massnahmen(auftrag_id)
    m = next((m for m in massnahmen if m.id == massnahme_id), None)
    if m:
        m.investitionskosten = parse_float_german(investitionskosten)
        m.monatliche_kosten = parse_float_german(monatliche_kosten)
        m.kosten_quelle = "manuell"
        storage.save_massnahmen(auftrag_id, massnahmen)
    return RedirectResponse(url=f"/auftrag/{auftrag_id}/massnahmen#massnahme-{massnahme_id}", status_code=303)

@router.post("/auftrag/{auftrag_id}/massnahme/{massnahme_id}/loeschen")
def delete_massnahme_submit(auftrag_id: str, massnahme_id: str):
    massnahmen = storage.list_massnahmen(auftrag_id)
    massnahme_to_delete = next((m for m in massnahmen if m.id == massnahme_id), None)
    massnahmen = [m for m in massnahmen if m.id != massnahme_id]
    storage.save_massnahmen(auftrag_id, massnahmen)

    # Item 1.7: Reset all linked findings back to 'bestaetigt' and clear massnahme_id
    findings = storage.list_findings(auftrag_id)
    findings_changed = False
    linked_f_ids = set(massnahme_to_delete.findings) if massnahme_to_delete else set()
    for f in findings:
        if f.massnahme_id == massnahme_id or f.id in linked_f_ids:
            f.status = "bestaetigt"
            f.massnahme_id = None
            findings_changed = True
    if findings_changed:
        storage.save_findings(auftrag_id, findings)

    return RedirectResponse(url=f"/auftrag/{auftrag_id}/massnahmen", status_code=303)
