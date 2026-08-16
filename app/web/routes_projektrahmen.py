"""Seite „Projektrahmen" (Karte #316).

Bündelt vier bislang tote Modellfelder aus `Auftrag`, die keine eigene
Eingabemaske hatten: die Rahmenbedingungen des Einsatzes (ein einzelnes
Objekt), die geplanten Ergebnisartefakte sowie die manuell vor Ort notierten
positiven und negativen Beobachtungen. Die beiden Beobachtungslisten sind
bewusst etwas anderes als die automatisch aus den Erfassungsregeln erzeugten
Findings (siehe `routes_findings.py`) — sie halten den persönlichen Eindruck
vor Ort fest, den keine Regel liefern kann.
"""

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.services.storage import storage, KonfliktFehler
from app.web.templates import templates
from app.web.shared_context import build_sidebar_context
from app.web.formular_listen import parse_unterobjekte
from app.models.auftrag import Ergebnisartefakt, Aspekt
from app.utils.number_parser import parse_int_german

router = APIRouter()

ERGEBNISARTEFAKT_TYP_OPTIONS = [
    "Analysebericht",
    "Managementsummary",
    "Massnahmenkatalog",
    "Netzdokumentation",
    "Notfalldokumentation",
]
ERGEBNISARTEFAKT_STATUS_OPTIONS = ["offen", "in Arbeit", "geliefert"]


def _kontext(auftrag, *, konflikt: bool = False) -> dict:
    sidebar_context = build_sidebar_context(auftrag)
    return {
        "auftrag": auftrag,
        "ergebnisartefakt_typ_options": ERGEBNISARTEFAKT_TYP_OPTIONS,
        "ergebnisartefakt_status_options": ERGEBNISARTEFAKT_STATUS_OPTIONS,
        "konflikt": konflikt,
        "active_tab": "projektrahmen",
        "active_nav": "auftrag",
        **sidebar_context,
    }


@router.get("/auftrag/{auftrag_id}/projektrahmen")
def projektrahmen_form(request: Request, auftrag_id: str):
    auftrag = storage.load_auftrag(auftrag_id)
    if not auftrag:
        return RedirectResponse(url="/auftrag", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="auftrag/projektrahmen.html",
        context=_kontext(auftrag),
    )


@router.post("/auftrag/{auftrag_id}/projektrahmen")
async def projektrahmen_submit(request: Request, auftrag_id: str):
    auftrag = storage.load_auftrag(auftrag_id)
    if not auftrag:
        return RedirectResponse(url="/auftrag", status_code=303)

    form_data = await request.form()

    auftrag.rahmenbedingungen.benoetigte_zugaenge = form_data.get("benoetigte_zugaenge", "").strip()
    auftrag.rahmenbedingungen.zutrittsregelung = form_data.get("zutrittsregelung", "").strip()
    auftrag.rahmenbedingungen.nda_vorhanden = form_data.get("nda_vorhanden", "nein")
    auftrag.rahmenbedingungen.wartungsfenster_einschraenkungen = form_data.get(
        "wartungsfenster_einschraenkungen", ""
    ).strip()
    auftrag.rahmenbedingungen.analysewerkzeuge = form_data.get("analysewerkzeuge", "").strip()

    auftrag.ergebnisartefakte = parse_unterobjekte(form_data, "artefakt", Ergebnisartefakt)
    auftrag.positive_aspekte = parse_unterobjekte(form_data, "positiv", Aspekt)
    auftrag.negative_aspekte = parse_unterobjekte(form_data, "negativ", Aspekt)

    # Massgeblich ist der Stand, den das Formular beim Laden gesehen hat — nicht
    # der frisch geladene. Sonst stimmt die Version beim Speichern immer überein
    # und die Konflikterkennung könnte nie anschlagen (Karte #308).
    auftrag.version = parse_int_german(form_data.get("version"), auftrag.version)

    try:
        storage.save_auftrag(auftrag)
    except KonfliktFehler:
        auftrag.version = _aktuelle_version(auftrag_id, auftrag.version)
        return templates.TemplateResponse(
            request=request,
            name="auftrag/projektrahmen.html",
            status_code=409,
            context=_kontext(auftrag, konflikt=True),
        )

    return RedirectResponse(url=f"/auftrag/{auftrag_id}", status_code=303)


def _aktuelle_version(auftrag_id: str, fallback: int) -> int:
    """Der Stand, der nach einem Konflikt auf der Platte liegt.

    Das Formular geht damit zurück an den Benutzer, damit ein zweites Speichern
    die fremde Änderung bewusst überschreiben kann, statt in derselben Meldung
    hängenzubleiben."""
    aktuell = storage.load_auftrag(auftrag_id)
    return aktuell.version if aktuell else fallback
