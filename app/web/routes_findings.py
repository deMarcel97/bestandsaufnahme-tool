import logging
from datetime import datetime
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from app.services.storage import storage
from app.services.slug import generate_slug_id
from app.services.rule_engine import rule_engine
from app.web.templates import templates
from app.web.shared_context import build_sidebar_context
from app.models.finding import Finding
from app.models.massnahme import Massnahme

router = APIRouter()

STUFE_MAP = {"hoch": 1, "mittel": 2, "niedrig": 3, "empfehlung": 3}

def _build_massnahme_from_finding(f: Finding, existing_m_ids: list[str]) -> Massnahme:
    mid = generate_slug_id("massnahme", f.befund, existing_m_ids)
    default_stufe = STUFE_MAP.get(f.schweregrad, 2)

    title = None
    kosten_richtwert = 0.0
    aufwand_richtwert = 0.0
    kosten_quelle = "offen"

    rule_id = getattr(f, "quelle", None)
    if rule_id and rule_id != "manuell":
        rule = next((r for r in rule_engine.rules if r.get("id") == rule_id), None)
        if rule:
            mv = rule.get("massnahme_vorschlag")
            if mv:
                if mv.get("bezeichnung"):
                    title = mv.get("bezeichnung")
                else:
                    title = f"Bezeichnung fehlt im Regelwerk (Regel-ID: {rule_id})"
                    logging.warning(f"Regelwerks-Lücke: bezeichnung fehlt in massnahme_vorschlag bei Regel {rule_id}")

                k_val = mv.get("kosten_richtwert")
                a_val = mv.get("aufwand_richtwert")
                if k_val is not None or a_val is not None:
                    kosten_richtwert = float(k_val or 0.0)
                    aufwand_richtwert = float(a_val or 0.0)
                    kosten_quelle = "regelwerk"

    if not title:
        title = f.befund

    return Massnahme(
        schema_version=1,
        id=mid,
        bezeichnung=title,
        beschreibung=f"{f.empfehlung} (Risiko: {f.risiko})",
        findings=[f.id],
        stufe=default_stufe,
        prioritaet=f.schweregrad if f.schweregrad in ("hoch", "mittel", "niedrig") else "niedrig",
        dringlichkeit="mittel",
        investitionskosten=kosten_richtwert,
        zeitaufwand=aufwand_richtwert,
        kosten_quelle=kosten_quelle,
        foerderprogramm="",
        status="vorgeschlagen"
    )

@router.get("/auftrag/{auftrag_id}/findings")
def list_findings_page(request: Request, auftrag_id: str):
    auftrag = storage.load_auftrag(auftrag_id)
    if not auftrag:
        return RedirectResponse(url="/auftrag", status_code=303)

    standorte = storage.list_standorte(auftrag_id)
    findings = storage.list_findings(auftrag_id)

    sidebar_context = build_sidebar_context(auftrag)
    return templates.TemplateResponse(
        request=request,
        name="findings/index.html",
        context={
            "auftrag": auftrag,
            "findings": findings,
            "standorte": standorte,
            "active_tab": "findings",
            "active_nav": "auftrag",
            **sidebar_context
        }
    )

@router.post("/auftrag/{auftrag_id}/finding/neu")
def new_finding_submit(
    auftrag_id: str,
    standort_id: str = Form(...),
    schweregrad: str = Form("mittel"),
    befund: str = Form(...),
    risiko: str = Form(...),
    empfehlung: str = Form(...)
):
    existing_findings = storage.list_findings(auftrag_id)
    fid = generate_slug_id("finding", befund, [f.id for f in existing_findings])

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    finding = Finding(
        schema_version=1,
        id=fid,
        auftrag_id=auftrag_id,
        standort_id=standort_id,
        quelle="manuell",
        schweregrad=schweregrad,
        befund=befund,
        risiko=risiko,
        empfehlung=empfehlung,
        status="offen",
        erzeugt_am=now_str
    )
    existing_findings.append(finding)
    storage.save_findings(auftrag_id, existing_findings)
    return RedirectResponse(url=f"/auftrag/{auftrag_id}/findings", status_code=303)

@router.post("/auftrag/{auftrag_id}/finding/{finding_id}/status")
def update_finding_status(
    auftrag_id: str,
    finding_id: str,
    status: str = Form(...),
    begruendung: str = Form("")
):
    begruendung_clean = begruendung.strip()
    if status in ("verworfen", "kunde_akzeptiert") and not begruendung_clean:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Bei Status '{status}' ist eine Begründung zwingend erforderlich."
        )

    findings = storage.list_findings(auftrag_id)
    for f in findings:
        if f.id == finding_id:
            if f.status == "uebernommen" and status in ("offen", "bestaetigt", "verworfen", "kunde_akzeptiert", "behoben"):
                if f.massnahme_id:
                    massnahmen = storage.list_massnahmen(auftrag_id)
                    m = next((m for m in massnahmen if m.id == f.massnahme_id), None)
                    if m and f.id in m.findings:
                        m.findings.remove(f.id)
                    storage.save_massnahmen(auftrag_id, massnahmen)
                f.massnahme_id = None

            f.status = status
            f.begruendung = begruendung_clean
            if status == "behoben" and not f.behoben_am:
                f.behoben_am = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            break
    storage.save_findings(auftrag_id, findings)
    return RedirectResponse(url=f"/auftrag/{auftrag_id}/findings", status_code=303)

@router.post("/auftrag/{auftrag_id}/finding/{finding_id}/massnahme_erzeugen")
def create_massnahme_from_finding(auftrag_id: str, finding_id: str):
    findings = storage.list_findings(auftrag_id)
    target_finding = next((f for f in findings if f.id == finding_id), None)
    if not target_finding or target_finding.status != "bestaetigt":
        return RedirectResponse(url=f"/auftrag/{auftrag_id}/findings", status_code=303)

    massnahmen = storage.list_massnahmen(auftrag_id)
    existing_m_ids = [m.id for m in massnahmen]

    new_m = _build_massnahme_from_finding(target_finding, existing_m_ids)
    massnahmen.append(new_m)
    storage.save_massnahmen(auftrag_id, massnahmen)

    # Link finding and mark status as uebernommen
    target_finding.massnahme_id = new_m.id
    target_finding.status = "uebernommen"
    storage.save_findings(auftrag_id, findings)

    return RedirectResponse(url=f"/auftrag/{auftrag_id}/massnahmen", status_code=303)

@router.post("/auftrag/{auftrag_id}/findings/alle_uebernehmen")
def transfer_all_findings_to_massnahmen(auftrag_id: str):
    findings = storage.list_findings(auftrag_id)
    # B2: Strictly filter ONLY findings with status "bestaetigt"!
    bestaetigte = [f for f in findings if f.status == "bestaetigt"]
    offen_cnt = len([f for f in findings if f.status == "offen"])
    verworfen_cnt = len([f for f in findings if f.status in ("verworfen", "kunde_akzeptiert")])
    uebernommen_cnt = len([f for f in findings if f.status == "uebernommen"])
    skipped_count = len(findings) - len(bestaetigte)

    if not bestaetigte:
        return RedirectResponse(
            url=f"/auftrag/{auftrag_id}/findings?transferred=0&skipped={skipped_count}&offen={offen_cnt}&verworfen={verworfen_cnt}&uebernommen={uebernommen_cnt}",
            status_code=303
        )

    massnahmen = storage.list_massnahmen(auftrag_id)
    existing_m_ids = [m.id for m in massnahmen]

    for f in bestaetigte:
        new_m = _build_massnahme_from_finding(f, existing_m_ids)
        existing_m_ids.append(new_m.id)
        massnahmen.append(new_m)
        f.massnahme_id = new_m.id
        f.status = "uebernommen"

    storage.save_massnahmen(auftrag_id, massnahmen)
    storage.save_findings(auftrag_id, findings)

    return RedirectResponse(
        url=f"/auftrag/{auftrag_id}/massnahmen?transferred={len(bestaetigte)}&skipped={skipped_count}&offen={offen_cnt}&verworfen={verworfen_cnt}&uebernommen={uebernommen_cnt}",
        status_code=303
    )
