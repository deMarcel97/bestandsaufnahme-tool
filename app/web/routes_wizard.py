"""
Erfassungs-Wizard Routes.

Einmaliger, geführter Durchlauf durch die wichtigsten Bausteine beim Anlegen eines Auftrags.
"""

from datetime import datetime
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from typing import Optional

from app.services.storage import storage, KonfliktFehler
from app.services.schema_loader import schema_loader
from app.services.slug import generate_slug_id
from app.web.templates import templates
from app.web.shared_context import build_sidebar_context
from app.models.auftrag import Auftrag
from app.models.standort import Standort
from app.models.technik import TechnikObjekt
from app.models.wizard import (
    WizardProgress,
    WIZARD_STEP_TYPES,
    WIZARD_STEP_LABELS,
    create_empty_wizard_progress,
)

router = APIRouter()


def get_auftrag_or_redirect(auftrag_id: str):
    """Lädt einen Auftrag oder leitet zur Übersicht weiter."""
    auftrag = storage.load_auftrag(auftrag_id)
    if not auftrag:
        return RedirectResponse(url="/auftrag", status_code=303)
    return auftrag


@router.get("/auftrag/{auftrag_id}/wizard")
def wizard_start(request: Request, auftrag_id: str):
    """Startet oder setzt den Erfassungs-Wizard fort."""
    auftrag = get_auftrag_or_redirect(auftrag_id)
    if isinstance(auftrag, RedirectResponse):
        return auftrag

    # Wizard-Fortschritt initialisieren oder laden
    progress = storage.load_wizard_progress(auftrag_id)
    if not progress:
        progress = storage.init_wizard_progress(auftrag_id)
        if not progress:
            return RedirectResponse(url=f"/auftrag/{auftrag_id}", status_code=303)

    # Wenn bereits abgeschlossen, zur Zusammenfassung
    if progress.is_complete():
        return RedirectResponse(url=f"/auftrag/{auftrag_id}/wizard/zusammenfassung", status_code=303)

    # Aktuellen Schritt und Daten laden
    current_step = progress.current_step
    step_type = WIZARD_STEP_TYPES[current_step - 1] if current_step <= len(WIZARD_STEP_TYPES) else "zusammenfassung"
    step_data = progress.get_current_step_data()

    standorte = storage.list_standorte(auftrag_id)
    objekte = storage.list_objekte(auftrag_id)
    sidebar_context = build_sidebar_context(auftrag, standorte, objekte)

    # Standardwerte für Standort-Auswahl
    # Wenn kein Standort existiert, einen anlegen
    if not standorte:
        sto_id = generate_slug_id("standort", "Hauptsitz", [])
        new_standort = Standort(
            schema_version=1,
            id=sto_id,
            auftrag_id=auftrag_id,
            bezeichnung="Hauptsitz",
            anzahl_user=10
        )
        storage.save_standort(new_standort)
        standorte = [new_standort]

    # Kontext für das Template aufbauen
    context = {
        "auftrag": auftrag,
        "progress": progress,
        "current_step": current_step,
        "total_steps": len(WIZARD_STEP_TYPES),
        "step_type": step_type,
        "step_label": WIZARD_STEP_LABELS.get(step_type, step_type),
        "step_data": step_data.data if step_data else {},
        "standorte": standorte,
        "standort": standorte[0] if standorte else None,
        "objekte": objekte,
        "bausteine": auftrag.aktive_bausteine,
        "baustein_labels": _get_bausteine_labels(),
        "active_nav": "auftrag",
        **sidebar_context
    }

    return templates.TemplateResponse(
        request=request,
        name="auftrag/wizard.html",
        context=context
    )


def _get_bausteine_labels() -> dict:
    """Gibt die Anzeigenamen aller Baustein-Typen zurück."""
    labels = {}
    for typ in schema_loader.get_all_types():
        s = schema_loader.get_schema(typ)
        labels[typ] = s.get("bezeichnung_anzeige", typ.capitalize()) if s else typ.capitalize()
    return labels


@router.post("/auftrag/{auftrag_id}/wizard/init")
def wizard_init(auftrag_id: str):
    """Initialisiert einen neuen Wizard-Fortschritt und leitet zum ersten Schritt weiter."""
    auftrag = get_auftrag_or_redirect(auftrag_id)
    if isinstance(auftrag, RedirectResponse):
        return auftrag

    # Eventuell bestehenden Fortschritt löschen
    storage.delete_wizard_progress(auftrag_id)
    
    # Neuen Fortschritt anlegen
    progress = create_empty_wizard_progress(auftrag_id)
    storage.save_wizard_progress(progress)
    
    return RedirectResponse(url=f"/auftrag/{auftrag_id}/wizard", status_code=303)


@router.post("/auftrag/{auftrag_id}/wizard/step/{step: int}")
async def wizard_save_step(
    request: Request,
    auftrag_id: str,
    step: int,
):
    """Speichert die Daten eines Schrittes und geht zum nächsten."""
    auftrag = get_auftrag_or_redirect(auftrag_id)
    if isinstance(auftrag, RedirectResponse):
        return auftrag

    # Fortschritt laden
    progress = storage.load_wizard_progress(auftrag_id)
    if not progress:
        return RedirectResponse(url=f"/auftrag/{auftrag_id}/wizard", status_code=303)

    # Formulardaten parsen
    form_data = await request.form()
    step_data = dict(form_data)

    # Aktuellen Schritt speichern
    step_type = WIZARD_STEP_TYPES[step - 1] if step <= len(WIZARD_STEP_TYPES) else "zusammenfassung"
    
    from app.models.wizard import WizardStepData
    progress.steps[step] = WizardStepData(
        step_type=step_type,
        data=step_data,
        timestamp=datetime.now().isoformat(),
        completed=True
    )
    if step not in progress.completed_steps:
        progress.completed_steps.append(step)
    progress.current_step = step + 1

    # Speichern
    try:
        storage.save_wizard_progress(progress)
    except KonfliktFehler:
        # Bei Konflikt: Version aktualisieren und neu speichern
        existing = storage.load_wizard_progress(auftrag_id)
        progress.version = existing.version + 1 if existing else 1
        storage.save_wizard_progress(progress)

    # Wenn alle Schritte abgeschlossen, zur Zusammenfassung
    if progress.is_complete():
        return RedirectResponse(url=f"/auftrag/{auftrag_id}/wizard/zusammenfassung", status_code=303)

    # Zum nächsten Schritt
    return RedirectResponse(url=f"/auftrag/{auftrag_id}/wizard", status_code=303)


@router.get("/auftrag/{auftrag_id}/wizard/zusammenfassung")
def wizard_zusammenfassung(request: Request, auftrag_id: str):
    """Zeigt die Zusammenfassung aller erfassten Daten."""
    auftrag = get_auftrag_or_redirect(auftrag_id)
    if isinstance(auftrag, RedirectResponse):
        return auftrag

    progress = storage.load_wizard_progress(auftrag_id)
    if not progress:
        return RedirectResponse(url=f"/auftrag/{auftrag_id}/wizard", status_code=303)

    standorte = storage.list_standorte(auftrag_id)
    objekte = storage.list_objekte(auftrag_id)
    sidebar_context = build_sidebar_context(auftrag, standorte, objekte)

    # Zusammenfassung der erfassten Daten
    summary_data = {}
    for step_num, step_data in progress.steps.items():
        summary_data[step_data.step_type] = step_data.data

    return templates.TemplateResponse(
        request=request,
        name="auftrag/wizard_zusammenfassung.html",
        context={
            "auftrag": auftrag,
            "progress": progress,
            "summary_data": summary_data,
            "baustein_labels": _get_bausteine_labels(),
            "active_nav": "auftrag",
            **sidebar_context
        }
    )


@router.post("/auftrag/{auftrag_id}/wizard/abschliessen")
def wizard_abschliessen(auftrag_id: str):
    """Schließt den Wizard ab und erstellt die erfassten Objekte."""
    auftrag = get_auftrag_or_redirect(auftrag_id)
    if isinstance(auftrag, RedirectResponse):
        return auftrag

    progress = storage.load_wizard_progress(auftrag_id)
    if not progress:
        return RedirectResponse(url=f"/auftrag/{auftrag_id}", status_code=303)

    # Hier würden die erfassten Daten in echte Objekte umgewandelt
    # Für jetzt: einfach den Fortschritt löschen und zur Erfassung weiterleiten
    # TODO: Automatisches Anlegen der Bausteine implementieren
    storage.delete_wizard_progress(auftrag_id)

    return RedirectResponse(url=f"/auftrag/{auftrag_id}/erfassung", status_code=303)


@router.post("/auftrag/{auftrag_id}/wizard/abbruch")
def wizard_abbruch(auftrag_id: str):
    """Bricht den Wizard ab und kehrt zum Auftrag zurück."""
    # Fortschritt nicht löschen, damit man später wieder einsteigen kann
    return RedirectResponse(url=f"/auftrag/{auftrag_id}", status_code=303)


@router.post("/auftrag/{auftrag_id}/wizard/skip")
def wizard_skip_step(auftrag_id: str):
    """Überspringt den aktuellen Schritt."""
    progress = storage.load_wizard_progress(auftrag_id)
    if not progress:
        return RedirectResponse(url=f"/auftrag/{auftrag_id}/wizard", status_code=303)

    # Aktuellen Schritt als übersprungen markieren
    current_step = progress.current_step
    step_type = WIZARD_STEP_TYPES[current_step - 1] if current_step <= len(WIZARD_STEP_TYPES) else "zusammenfassung"
    
    from app.models.wizard import WizardStepData
    progress.steps[current_step] = WizardStepData(
        step_type=step_type,
        data={},
        timestamp=datetime.now().isoformat(),
        completed=True
    )
    if current_step not in progress.completed_steps:
        progress.completed_steps.append(current_step)
    progress.current_step = current_step + 1

    storage.save_wizard_progress(progress)

    if progress.is_complete():
        return RedirectResponse(url=f"/auftrag/{auftrag_id}/wizard/zusammenfassung", status_code=303)

    return RedirectResponse(url=f"/auftrag/{auftrag_id}/wizard", status_code=303)
