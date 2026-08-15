import html
from fastapi import APIRouter, Request, Form, Response
from fastapi.responses import RedirectResponse, HTMLResponse
from pathlib import Path
from app.services.storage import storage
from app.services.schema_loader import schema_loader
from app.services.slug import generate_slug_id
from app.services.rule_engine import rule_engine
from app.services.evaluator import evaluator_service
from app.web.templates import templates
from app.web.shared_context import build_sidebar_context
from app.models.auftrag import Auftrag, Termine, Unternehmenskontext
from app.utils.number_parser import parse_int_german, parse_float_german

router = APIRouter()

STATUS_OPTIONS = ["Vorbereitung", "Erfassung", "Konsolidierung", "Bewertung", "Abgabe"]

def get_bausteine_labels() -> dict:
    labels = {}
    for typ in schema_loader.get_all_types():
        s = schema_loader.get_schema(typ)
        labels[typ] = s.get("bezeichnung_anzeige", typ.capitalize()) if s else typ.capitalize()
    return labels

@router.get("/")
def index_redirect():
    return RedirectResponse(url="/auftrag", status_code=303)

@router.get("/auftrag")
def list_auftraege(request: Request):
    auftraege = storage.list_auftraege()
    verfuegbare_typen = schema_loader.get_all_types()
    bausteine_labels = get_bausteine_labels()
    return templates.TemplateResponse(
        request=request,
        name="auftrag/list.html",
        context={
            "auftraege": auftraege,
            "verfuegbare_typen": verfuegbare_typen,
            "bausteine_labels": bausteine_labels,
            "active_nav": "auftrag"
        }
    )

@router.post("/auftrag/neu")
def create_auftrag(
    projekt_nummer: str = Form(""),
    jira_url: str = Form(""),
    kunde: str = Form(...),
    bezeichnung: str = Form(...),
    grundlage: str = Form("Sonstiges"),
    vertraulichkeit_default: str = Form("kundentauglich"),
    aktive_bausteine: list[str] = Form(default=["firewall"])
):
    all_auftraege = storage.list_auftraege()
    
    # Auto-generate projekt_nummer if empty
    if not projekt_nummer.strip():
        max_proj = 0
        for a in all_auftraege:
            if a.projekt_nummer.startswith("PROJEKT-"):
                try:
                    num = int(a.projekt_nummer.replace("PROJEKT-", ""))
                    if num > max_proj:
                        max_proj = num
                except ValueError:
                    pass
        projekt_nummer = f"PROJEKT-{max_proj + 1}"
    elif storage.projekt_nummer_existiert(projekt_nummer):
        safe_projekt_nummer = html.escape(projekt_nummer)
        return HTMLResponse(content=f"<script>alert('Fehler: Projektnummer {safe_projekt_nummer} existiert bereits. Ist dies ein weiterer Standort? Bitte erstelle im bestehenden Projekt einen neuen Standort.'); window.history.back();</script>", status_code=400)

    existing_ids = [a.id for a in all_auftraege]
    auftrag_id = generate_slug_id("auftrag", bezeichnung, existing_ids)

    auftrag = Auftrag(
        schema_version=1,
        id=auftrag_id,
        projekt_nummer=projekt_nummer,
        jira_url=jira_url if jira_url else None,
        kunde=kunde,
        bezeichnung=bezeichnung,
        grundlage=grundlage,
        vertraulichkeit_default=vertraulichkeit_default,
        aktive_bausteine=aktive_bausteine
    )
    storage.save_auftrag(auftrag)
    return RedirectResponse(url=f"/auftrag/{auftrag_id}", status_code=303)

@router.post("/auftrag/{auftrag_id}/status")
def update_auftrag_status(auftrag_id: str, status: str = Form(...), next: str = Form(default="")):
    auftrag = storage.load_auftrag(auftrag_id)
    if auftrag and status in STATUS_OPTIONS:
        auftrag.status = status
        storage.save_auftrag(auftrag)
    redirect_url = next if next in ("/auftrag", f"/auftrag/{auftrag_id}") else f"/auftrag/{auftrag_id}"
    return RedirectResponse(url=redirect_url, status_code=303)

@router.post("/auftrag/{auftrag_id}/vertraulichkeit")
def update_auftrag_vertraulichkeit(auftrag_id: str, vertraulichkeit_default: str = Form(...), next: str = Form(default="")):
    auftrag = storage.load_auftrag(auftrag_id)
    if auftrag and vertraulichkeit_default in ["intern", "kundentauglich", "anonymisiert"]:
        auftrag.vertraulichkeit_default = vertraulichkeit_default
        storage.save_auftrag(auftrag)
    redirect_url = next if next in ("/auftrag", f"/auftrag/{auftrag_id}") else f"/auftrag/{auftrag_id}"
    return RedirectResponse(url=redirect_url, status_code=303)

@router.get("/auftrag/{auftrag_id}")
def detail_auftrag(request: Request, auftrag_id: str):
    """Übersicht: Status auf einen Blick (Kennzahlen), nichts zum Bearbeiten.
    Nur hier läuft die teure Gesamtbewertung — die Erfassungsseite braucht sie nicht."""
    auftrag = storage.load_auftrag(auftrag_id)
    if not auftrag:
        return RedirectResponse(url="/auftrag", status_code=303)

    standorte = storage.list_standorte(auftrag_id)
    objekte = storage.list_objekte(auftrag_id)
    sidebar_context = build_sidebar_context(auftrag, standorte, objekte)
    bewertung = evaluator_service.evaluate_auftrag(auftrag.aktive_bausteine, objekte, standorte)

    return templates.TemplateResponse(
        request=request,
        name="auftrag/detail.html",
        context={
            "auftrag": auftrag,
            "bewertung": bewertung,
            "active_tab": "uebersicht",
            "active_nav": "auftrag",
            **sidebar_context
        }
    )

@router.get("/auftrag/{auftrag_id}/erfassung")
def erfassung_auftrag(request: Request, auftrag_id: str):
    """Erfassung: die Arbeitsfläche mit Standorten, Bausteinauswahl und erfassten
    Objekten. Ohne Gesamtbewertung, die gehört auf die Übersicht."""
    auftrag = storage.load_auftrag(auftrag_id)
    if not auftrag:
        return RedirectResponse(url="/auftrag", status_code=303)

    standorte = storage.list_standorte(auftrag_id)
    objekte = storage.list_objekte(auftrag_id)
    sidebar_context = build_sidebar_context(auftrag, standorte, objekte)

    return templates.TemplateResponse(
        request=request,
        name="auftrag/erfassung.html",
        context={
            "auftrag": auftrag,
            "standorte": standorte,
            "objekte": objekte,
            "bausteine_labels": get_bausteine_labels(),
            "active_tab": "erfassung",
            "active_nav": "auftrag",
            **sidebar_context
        }
    )

@router.get("/auftrag/{auftrag_id}/einstellungen")
def edit_auftrag_form(request: Request, auftrag_id: str):
    auftrag = storage.load_auftrag(auftrag_id)
    if not auftrag:
        return RedirectResponse(url="/auftrag", status_code=303)

    verfuegbare_typen = schema_loader.get_all_types()
    bausteine_labels = get_bausteine_labels()
    sidebar_context = build_sidebar_context(auftrag)
    return templates.TemplateResponse(
        request=request,
        name="auftrag/edit.html",
        context={
            "auftrag": auftrag,
            "verfuegbare_typen": verfuegbare_typen,
            "bausteine_labels": bausteine_labels,
            "active_tab": "einstellungen",
            "active_nav": "auftrag",
            **sidebar_context
        }
    )

@router.post("/auftrag/{auftrag_id}/einstellungen")
def edit_auftrag_submit(
    auftrag_id: str,
    projekt_nummer: str = Form(""),
    jira_url: str = Form(""),
    kunde: str = Form(...),
    auftraggeber: str = Form(""),
    bezeichnung: str = Form(...),
    grundlage: str = Form("Sonstiges"),
    status: str = Form("Vorbereitung"),
    vertraulichkeit_default: str = Form("kundentauglich"),
    aktive_bausteine: list[str] = Form(default=[]),
    kerngeschaeft: str = Form(""),
    anzahl_standorte_kunde: str = Form("1"),
    it_abteilung_vorhanden: str = Form("nein"),
    anzahl_mitarbeiter_gesamt: str = Form(""),
    anzahl_it_mitarbeiter: str = Form(""),
    anzahl_it_nutzer: str = Form(""),
    geschaeftszeiten_tage: str = Form("Montag bis Freitag"),
    geschaeftszeiten_von: str = Form("08:00"),
    geschaeftszeiten_bis: str = Form("17:00"),
    allgemeine_hinweise: str = Form(""),
    beauftragung: str = Form(""),
    kickoff: str = Form(""),
    entwurf_vorlage: str = Form(""),
    abgabe: str = Form("")
):
    auftrag = storage.load_auftrag(auftrag_id)
    if not auftrag:
        return RedirectResponse(url="/auftrag", status_code=303)

    # Collision check for projekt_nummer
    if projekt_nummer.strip() and projekt_nummer.strip() != auftrag.projekt_nummer:
        if storage.projekt_nummer_existiert(projekt_nummer, exclude_id=auftrag.id):
            safe_projekt_nummer = html.escape(projekt_nummer)
            return HTMLResponse(content=f"<script>alert('Fehler: Projektnummer {safe_projekt_nummer} existiert bereits. Ist dies ein weiterer Standort? Bitte im bestehenden Projekt einen neuen Standort anlegen.'); window.history.back();</script>", status_code=400)

    auftrag.projekt_nummer = projekt_nummer if projekt_nummer.strip() else auftrag.projekt_nummer
    auftrag.jira_url = jira_url if jira_url else None
    auftrag.kunde = kunde
    auftrag.auftraggeber = auftraggeber
    auftrag.bezeichnung = bezeichnung
    auftrag.grundlage = grundlage
    auftrag.status = status
    auftrag.vertraulichkeit_default = vertraulichkeit_default
    auftrag.aktive_bausteine = aktive_bausteine

    # Context
    auftrag.unternehmenskontext.kerngeschaeft = kerngeschaeft
    target_count = parse_int_german(anzahl_standorte_kunde, 1)
    auftrag.unternehmenskontext.anzahl_standorte_kunde = target_count
    auftrag.unternehmenskontext.it_abteilung_vorhanden = it_abteilung_vorhanden
    auftrag.unternehmenskontext.anzahl_mitarbeiter_gesamt = parse_int_german(anzahl_mitarbeiter_gesamt) if anzahl_mitarbeiter_gesamt else None
    auftrag.unternehmenskontext.anzahl_it_mitarbeiter = parse_int_german(anzahl_it_mitarbeiter) if anzahl_it_mitarbeiter else None
    auftrag.unternehmenskontext.anzahl_it_nutzer = parse_int_german(anzahl_it_nutzer) if anzahl_it_nutzer else None
    auftrag.unternehmenskontext.geschaeftszeiten_tage = geschaeftszeiten_tage
    auftrag.unternehmenskontext.geschaeftszeiten_von = geschaeftszeiten_von
    auftrag.unternehmenskontext.geschaeftszeiten_bis = geschaeftszeiten_bis
    auftrag.unternehmenskontext.allgemeine_hinweise = allgemeine_hinweise

    # Dates
    auftrag.termine.beauftragung = beauftragung if beauftragung else None
    auftrag.termine.kickoff = kickoff if kickoff else None
    auftrag.termine.entwurf_vorlage = entwurf_vorlage if entwurf_vorlage else None
    auftrag.termine.abgabe = abgabe if abgabe else None

    storage.save_auftrag(auftrag)

    # Auto-generate Standorte if target_count > current existing standorte count
    existing_standorte = storage.list_standorte(auftrag_id)
    if len(existing_standorte) < target_count:
        existing_ids = [s.id for s in existing_standorte]
        from app.models.standort import Standort
        for i in range(len(existing_standorte) + 1, target_count + 1):
            sto_name = f"Standort {i}"
            sto_id = generate_slug_id("standort", sto_name, existing_ids)
            existing_ids.append(sto_id)
            new_sto = Standort(
                schema_version=1,
                id=sto_id,
                auftrag_id=auftrag_id,
                bezeichnung=sto_name,
                anzahl_user=10
            )
            storage.save_standort(new_sto)

    return RedirectResponse(url=f"/auftrag/{auftrag_id}", status_code=303)

@router.post("/auftrag/{auftrag_id}/bewerten")
def evaluate_auftrag(auftrag_id: str):
    auftrag = storage.load_auftrag(auftrag_id)
    if not auftrag:
        return RedirectResponse(url="/auftrag", status_code=303)

    standorte = storage.list_standorte(auftrag_id)
    objekte = storage.list_objekte(auftrag_id)
    existing_findings = storage.list_findings(auftrag_id)

    # Evaluate rules
    updated_findings, rule_open_points = rule_engine.evaluate_all(
        auftrag_id, standorte, objekte, existing_findings
    )
    storage.save_findings(auftrag_id, updated_findings)

    return RedirectResponse(url=f"/auftrag/{auftrag_id}/bewertung", status_code=303)

@router.post("/auftrag/{auftrag_id}/delete")
def delete_auftrag(auftrag_id: str):
    storage.delete_auftrag(auftrag_id)
    return RedirectResponse(url="/auftrag", status_code=303)
