import html
from fastapi import APIRouter, Request, Form, Response
from fastapi.responses import RedirectResponse, HTMLResponse
from pathlib import Path
from app.services.storage import storage, KonfliktFehler
from app.services.schema_loader import schema_loader
from app.services.slug import generate_slug_id
from app.services.rule_engine import rule_engine
from app.services.evaluator import evaluator_service
from app.services.topology_generator import generate_network_topology_mermaid
from app.web.templates import templates
from app.web.shared_context import build_sidebar_context, aktuelle_version
from app.models.auftrag import Auftrag, Aspekt, GeplanteAenderung
from app.utils.number_parser import parse_float_german, parse_int_german
from app.web.formular_listen import parse_unterobjekte
from app.web.optionen import (
    STATUS_OPTIONS,
    GRUNDLAGE_OPTIONS,
    VERTRAULICHKEIT_OPTIONS,
    ZWECK_OPTIONS,
    gueltiger_wert,
)

router = APIRouter()

BAUSTEIN_GRUPPEN = [
    {
        "titel": "Netzwerk & Perimeter",
        "typen": ["firewall", "switch", "access_point", "netzwerkschrank"]
    },
    {
        "titel": "Server & Rechenzentrum",
        "typen": ["server_virtualisierung", "vm", "server_cluster", "serverraum", "usv"]
    },
    {
        "titel": "Speicher & Sicherung",
        "typen": ["storage", "backup"]
    },
    {
        "titel": "Clients & Workplace",
        "typen": ["clients", "software"]
    },
    {
        "titel": "Cloud & Governance",
        "typen": ["m365_security", "organisation_prozesse"]
    },
]

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
            "baustein_gruppen": BAUSTEIN_GRUPPEN,
            "grundlage_options": GRUNDLAGE_OPTIONS,
            "vertraulichkeit_options": VERTRAULICHKEIT_OPTIONS,
            "active_nav": "auftrag"
        }
    )

@router.post("/auftrag/neu")
def create_auftrag(
    projekt_nummer: str = Form(""),
    jira_url: str = Form(""),
    kunde: str = Form(""),
    bezeichnung: str = Form(""),
    grundlage: str = Form("Sonstiges"),
    vertraulichkeit_default: str = Form("intern"),
    aktive_bausteine: list[str] = Form(default=["firewall"]),
    start_wizard: str = Form("")
):
    kunde_clean = (kunde or "").strip()
    bezeichnung_clean = (bezeichnung or "").strip()
    if not kunde_clean or not bezeichnung_clean:
        return HTMLResponse(content="<script>alert('Bitte Kunde und Auftragsbezeichnung angeben.'); window.history.back();</script>", status_code=400)

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
    auftrag_id = generate_slug_id("auftrag", bezeichnung_clean, existing_ids)

    auftrag = Auftrag(
        schema_version=1,
        id=auftrag_id,
        projekt_nummer=projekt_nummer,
        jira_url=jira_url.strip() if jira_url else None,
        kunde=kunde_clean,
        bezeichnung=bezeichnung_clean,
        # Beim Neuanlegen gibt es noch keinen Wert zu bewahren — hier ist der
        # Vorgabewert des Formulars der richtige Rückfall. Bei der
        # Vertraulichkeit ist das "intern", also die schützende Stufe (#310).
        grundlage=gueltiger_wert(grundlage, GRUNDLAGE_OPTIONS, "Sonstiges"),
        vertraulichkeit_default=gueltiger_wert(
            vertraulichkeit_default, VERTRAULICHKEIT_OPTIONS, "intern"
        ),
        aktive_bausteine=aktive_bausteine
    )
    storage.save_auftrag(auftrag)

    if start_wizard in ("1", "true", "on", "yes"):
        return RedirectResponse(url=f"/auftrag/{auftrag_id}/wizard", status_code=303)
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
    if auftrag and vertraulichkeit_default in VERTRAULICHKEIT_OPTIONS:
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

    cloud_bausteine = [
        typ for typ in auftrag.aktive_bausteine
        if schema_loader.get_schema(typ) and schema_loader.get_schema(typ).get("standortbezug") is False
    ]
    standort_bausteine = [
        typ for typ in auftrag.aktive_bausteine
        if not (schema_loader.get_schema(typ) and schema_loader.get_schema(typ).get("standortbezug") is False)
    ]
    cloud_objekte = [o for o in objekte if not o.standort_id]

    topologien = {}
    for sto in standorte:
        sto_objs = [o for o in objekte if o.standort_id == sto.id]
        topologien[sto.id] = generate_network_topology_mermaid(sto, sto_objs)

    return templates.TemplateResponse(
        request=request,
        name="auftrag/erfassung.html",
        context={
            "auftrag": auftrag,
            "standorte": standorte,
            "objekte": objekte,
            "topologien": topologien,
            "cloud_objekte": cloud_objekte,
            "cloud_bausteine": cloud_bausteine,
            "standort_bausteine": standort_bausteine,
            "bausteine_labels": get_bausteine_labels(),
            "active_tab": "erfassung",
            "active_nav": "auftrag",
            **sidebar_context
        }
    )

@router.get("/auftrag/{auftrag_id}/topologie-preview")
def topologie_preview(request: Request, auftrag_id: str):
    auftrag = storage.load_auftrag(auftrag_id)
    if not auftrag:
        return HTMLResponse("<p class='text-muted'>Auftrag nicht gefunden.</p>")
    standorte = storage.list_standorte(auftrag_id)
    objekte = storage.list_objekte(auftrag_id)
    topologien = {}
    for sto in standorte:
        sto_objs = [o for o in objekte if o.standort_id == sto.id]
        topologien[sto.id] = generate_network_topology_mermaid(sto, sto_objs)

    return templates.TemplateResponse(
        request=request,
        name="auftrag/_topologie_preview.html",
        context={
            "auftrag": auftrag,
            "standorte": standorte,
            "topologien": topologien,
        }
    )


@router.get("/auftrag/{auftrag_id}/einstellungen")
def edit_auftrag_redirect(auftrag_id: str):
    """Der frühere Sammel-Menüpunkt „Stammdaten & Kontext" ist in die zwei
    Menüpunkte „Stammdaten" und „Unternehmenskontext" aufgeteilt. Die alte
    Adresse bleibt als Weiterleitung bestehen, damit Lesezeichen und in
    Auftragsdaten gespeicherte Ziel-Links weiter funktionieren."""
    return RedirectResponse(url=f"/auftrag/{auftrag_id}/stammdaten", status_code=303)

@router.get("/auftrag/{auftrag_id}/stammdaten")
def stammdaten_form(request: Request, auftrag_id: str):
    auftrag = storage.load_auftrag(auftrag_id)
    if not auftrag:
        return RedirectResponse(url="/auftrag", status_code=303)

    verfuegbare_typen = schema_loader.get_all_types()
    bausteine_labels = get_bausteine_labels()
    sidebar_context = build_sidebar_context(auftrag)
    return templates.TemplateResponse(
        request=request,
        name="auftrag/stammdaten.html",
        context={
            "auftrag": auftrag,
            "verfuegbare_typen": verfuegbare_typen,
            "bausteine_labels": bausteine_labels,
            "baustein_gruppen": BAUSTEIN_GRUPPEN,
            "grundlage_options": GRUNDLAGE_OPTIONS,
            "zweck_options": ZWECK_OPTIONS,
            "vertraulichkeit_options": VERTRAULICHKEIT_OPTIONS,
            "active_tab": "stammdaten",
            "active_nav": "auftrag",
            **sidebar_context
        }
    )

@router.post("/auftrag/{auftrag_id}/stammdaten")
def stammdaten_submit(
    request: Request,
    auftrag_id: str,
    version: str = Form(""),
    projekt_nummer: str = Form(""),
    jira_url: str = Form(""),
    kunde: str = Form(...),
    auftraggeber: str = Form(""),
    bezeichnung: str = Form(...),
    grundlage: str = Form("Sonstiges"),
    status: str = Form("Vorbereitung"),
    vertraulichkeit_default: str = Form("intern"),
    aktive_bausteine: list[str] = Form(default=[]),
    zweck: list[str] = Form(default=[]),
    abgrenzung: str = Form(""),
    aufwand_geplant: str = Form(""),
    aufwand_ist: str = Form(""),
    beauftragung: str = Form(""),
    kickoff: str = Form(""),
    entwurf_vorlage: str = Form(""),
    abgabe: str = Form("")
):
    """Speichert ausschliesslich die Felder der Stammdaten-Seite. Der
    Unternehmenskontext wird bewusst nicht angefasst — er hat eine eigene
    Seite mit eigenem Formular, und ein Speichern hier darf ihn nicht leeren."""
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
    # Beim Bearbeiten ist der bereits gespeicherte Wert der Rückfall: ein
    # fehlerhafter POST überschreibt damit nichts, statt den Datensatz auf einen
    # Vorgabewert zurückzusetzen. Die übrigen Felder des Formulars werden
    # trotzdem gespeichert (Karte #309).
    auftrag.grundlage = gueltiger_wert(grundlage, GRUNDLAGE_OPTIONS, auftrag.grundlage)
    auftrag.status = gueltiger_wert(status, STATUS_OPTIONS, auftrag.status)
    auftrag.vertraulichkeit_default = gueltiger_wert(
        vertraulichkeit_default, VERTRAULICHKEIT_OPTIONS, auftrag.vertraulichkeit_default
    )
    auftrag.aktive_bausteine = aktive_bausteine
    # Wie bei den anderen Auswahlfeldern (#309): unbekannte Werte aus einem
    # manipulierten POST fallen heraus statt gespeichert zu werden.
    auftrag.zweck = [wert for wert in zweck if wert in ZWECK_OPTIONS]
    auftrag.abgrenzung = abgrenzung
    auftrag.aufwand_geplant = parse_float_german(aufwand_geplant, auftrag.aufwand_geplant)
    auftrag.aufwand_ist = parse_float_german(aufwand_ist, auftrag.aufwand_ist)

    # Dates
    auftrag.termine.beauftragung = beauftragung if beauftragung else None
    auftrag.termine.kickoff = kickoff if kickoff else None
    auftrag.termine.entwurf_vorlage = entwurf_vorlage if entwurf_vorlage else None
    auftrag.termine.abgabe = abgabe if abgabe else None

    # Massgeblich ist der Stand, den das Formular beim Laden gesehen hat — nicht
    # der frisch geladene. Sonst stimmt die Version beim Speichern immer überein
    # und die Konflikterkennung könnte nie anschlagen (Karte #308). Fehlt das
    # Feld (Formular aus einer älteren Version), bleibt es beim bisherigen
    # Verhalten.
    auftrag.version = parse_int_german(version, auftrag.version)

    try:
        storage.save_auftrag(auftrag)
    except KonfliktFehler:
        auftrag.version = aktuelle_version(auftrag_id, auftrag.version)
        sidebar_context = build_sidebar_context(auftrag)
        return templates.TemplateResponse(
            request=request,
            name="auftrag/stammdaten.html",
            status_code=409,
            context={
                "auftrag": auftrag,
                "verfuegbare_typen": schema_loader.get_all_types(),
                "bausteine_labels": get_bausteine_labels(),
                "grundlage_options": GRUNDLAGE_OPTIONS,
                "zweck_options": ZWECK_OPTIONS,
                "konflikt": True,
                "active_tab": "stammdaten",
                "active_nav": "auftrag",
                **sidebar_context
            }
        )

    return RedirectResponse(url=f"/auftrag/{auftrag_id}", status_code=303)


@router.get("/auftrag/{auftrag_id}/unternehmenskontext")
def unternehmenskontext_form(request: Request, auftrag_id: str):
    auftrag = storage.load_auftrag(auftrag_id)
    if not auftrag:
        return RedirectResponse(url="/auftrag", status_code=303)

    sidebar_context = build_sidebar_context(auftrag)
    return templates.TemplateResponse(
        request=request,
        name="auftrag/unternehmenskontext.html",
        context={
            "auftrag": auftrag,
            "active_tab": "unternehmenskontext",
            "active_nav": "auftrag",
            **sidebar_context
        }
    )

@router.post("/auftrag/{auftrag_id}/unternehmenskontext")
async def unternehmenskontext_submit(
    request: Request,
    auftrag_id: str,
    version: str = Form(""),
    kerngeschaeft: str = Form(""),
    anzahl_standorte_kunde: str = Form("1"),
    it_abteilung_vorhanden: str = Form("nein"),
    anzahl_mitarbeiter_gesamt: str = Form(""),
    anzahl_it_mitarbeiter: str = Form(""),
    anzahl_it_nutzer: str = Form(""),
    geschaeftszeiten_tage: str = Form("Montag bis Freitag"),
    geschaeftszeiten_von: str = Form("08:00"),
    geschaeftszeiten_bis: str = Form("17:00"),
    allgemeine_hinweise: str = Form("")
):
    """Speichert ausschliesslich den Unternehmenskontext. Stammdaten,
    Auftragssteuerung und Termine bleiben unangetastet — sie gehören zur
    Stammdaten-Seite."""
    auftrag = storage.load_auftrag(auftrag_id)
    if not auftrag:
        return RedirectResponse(url="/auftrag", status_code=303)

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

    # Beliebig lange Listen — kommen nicht als benannte Form()-Parameter,
    # sondern zeilenweise als system_<feld>_<index> / aenderung_<feld>_<index>
    # (Karte #316, Parser aus formular_listen.py).
    form_data = await request.form()
    auftrag.unternehmenskontext.geschaeftskritische_systeme = parse_unterobjekte(
        form_data, "system", Aspekt
    )
    auftrag.unternehmenskontext.geplante_aenderungen = parse_unterobjekte(
        form_data, "aenderung", GeplanteAenderung
    )

    # Siehe stammdaten_submit: massgeblich ist der beim Laden gesehene Stand.
    auftrag.version = parse_int_german(version, auftrag.version)

    try:
        storage.save_auftrag(auftrag)
    except KonfliktFehler:
        auftrag.version = aktuelle_version(auftrag_id, auftrag.version)
        sidebar_context = build_sidebar_context(auftrag)
        return templates.TemplateResponse(
            request=request,
            name="auftrag/unternehmenskontext.html",
            status_code=409,
            context={
                "auftrag": auftrag,
                "konflikt": True,
                "active_tab": "unternehmenskontext",
                "active_nav": "auftrag",
                **sidebar_context
            }
        )

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
