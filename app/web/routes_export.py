from typing import Optional
from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse
from app.services.storage import storage
from app.services.evaluator import evaluator_service
from app.services.exporter import exporter_service
from app.web.templates import templates
from app.web.shared_context import build_sidebar_context

router = APIRouter()

@router.get("/auftrag/{auftrag_id}/export")
def export_page(request: Request, auftrag_id: str, ziel_vertraulichkeit: Optional[str] = None):
    auftrag = storage.load_auftrag(auftrag_id)
    if not auftrag:
        return RedirectResponse(url="/auftrag", status_code=303)

    if ziel_vertraulichkeit is None:
        ziel_vertraulichkeit = auftrag.vertraulichkeit_default

    standorte = storage.list_standorte(auftrag_id)
    objekte = storage.list_objekte(auftrag_id)
    massnahmen = storage.list_massnahmen(auftrag_id)

    bericht_preview = exporter_service.export_analysebericht(
        auftrag, standorte, objekte, massnahmen, ziel_vertraulichkeit
    )

    sidebar_context = build_sidebar_context(auftrag)
    return templates.TemplateResponse(
        request=request,
        name="export/index.html",
        context={
            "auftrag": auftrag,
            "ziel_vertraulichkeit": ziel_vertraulichkeit,
            "bericht_preview": bericht_preview,
            "active_tab": "export",
            "active_nav": "auftrag",
            **sidebar_context
        }
    )

@router.get("/auftrag/{auftrag_id}/export/download/{filename}")
def download_export(auftrag_id: str, filename: str, ziel_vertraulichkeit: Optional[str] = None):
    auftrag = storage.load_auftrag(auftrag_id)
    if not auftrag:
        return RedirectResponse(url="/auftrag", status_code=303)

    if ziel_vertraulichkeit is None:
        ziel_vertraulichkeit = auftrag.vertraulichkeit_default

    standorte = storage.list_standorte(auftrag_id)
    objekte = storage.list_objekte(auftrag_id)
    findings = storage.list_findings(auftrag_id)
    massnahmen = storage.list_massnahmen(auftrag_id)

    if filename == "analysebericht.md":
        content = exporter_service.export_analysebericht(
            auftrag, standorte, objekte, massnahmen, ziel_vertraulichkeit
        )
        return Response(content=content, media_type="text/markdown", headers={"Content-Disposition": f"attachment; filename=analysebericht_{auftrag_id}.md"})

    elif filename == "analysebericht.docx":
        docx_bytes = exporter_service.export_analysebericht_docx(
            auftrag, standorte, objekte, massnahmen, ziel_vertraulichkeit
        )
        return Response(content=docx_bytes.getvalue(), media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers={"Content-Disposition": f"attachment; filename=analysebericht_{auftrag_id}.docx"})

    elif filename == "massnahmen.md":
        content = exporter_service.export_massnahmenkatalog_md(massnahmen, ziel_vertraulichkeit)
        return Response(content=content, media_type="text/markdown", headers={"Content-Disposition": f"attachment; filename=massnahmen_{auftrag_id}.md"})

    elif filename == "massnahmen.csv":
        content = exporter_service.export_massnahmenkatalog_csv(massnahmen, ziel_vertraulichkeit)
        return Response(content=content, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=massnahmen_{auftrag_id}.csv"})

    elif filename == "summary.md":
        bewertung = evaluator_service.evaluate_auftrag(auftrag.aktive_bausteine, objekte, standorte)
        content = exporter_service.export_managementsummary(auftrag, standorte, objekte, findings, massnahmen, bewertung, ziel_vertraulichkeit=ziel_vertraulichkeit)
        return Response(content=content, media_type="text/markdown", headers={"Content-Disposition": f"attachment; filename=summary_{auftrag_id}.md"})

    elif filename == "raw.json":
        content = exporter_service.export_raw_json(auftrag, standorte, objekte, findings, massnahmen, ziel_vertraulichkeit)
        return Response(content=content, media_type="application/json", headers={"Content-Disposition": f"attachment; filename=raw_{auftrag_id}.json"})

    return RedirectResponse(url=f"/auftrag/{auftrag_id}/export", status_code=303)
