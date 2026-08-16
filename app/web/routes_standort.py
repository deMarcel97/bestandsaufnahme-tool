import html
from datetime import date
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from app.services.storage import storage, KonfliktFehler
from app.services.slug import generate_slug_id
from app.services.rule_engine import rule_engine
from app.web.templates import templates
from app.web.shared_context import build_sidebar_context
from app.models.standort import Standort, Internetanbindung
from app.utils.number_parser import parse_float_german, parse_int_german
from app.web.optionen import VERTRAULICHKEIT_OPTIONS, gueltiger_wert

router = APIRouter()

def _parse_anbindungen_from_form(form_data) -> list[Internetanbindung]:
    anbindungen = []
    indices = set()
    for key in form_data.keys():
        if "_" in key:
            parts = key.rsplit("_", 1)
            if parse_int_german(parts[1], -1) >= 0:
                indices.add(parse_int_german(parts[1]))

    for idx in sorted(indices):
        vorhanden = f"anbindung_vorhanden_{idx}" in form_data
        anbieter = form_data.get(f"anbieter_{idx}", "").strip()
        art = form_data.get(f"art_{idx}", "DSL").strip()
        down_val = parse_float_german(form_data.get(f"bandbreite_down_mbit_{idx}"))
        up_val = parse_float_german(form_data.get(f"bandbreite_up_mbit_{idx}"))
        symmetrisch = form_data.get(f"symmetrisch_{idx}", "nein")
        feste_ip = form_data.get(f"feste_ip_{idx}", "nein")
        ist_backup = form_data.get(f"ist_backup_leitung_{idx}", "nein")
        failover = form_data.get(f"failover_verfahren_{idx}", "").strip()
        ip_adressen = form_data.get(f"ip_adressen_{idx}", "").strip()
        subnetzmaske = form_data.get(f"subnetzmaske_{idx}", "").strip()
        sla_entstoerzeit = parse_float_german(form_data.get(f"sla_entstoerzeit_{idx}"))

        has_user_input = bool(
            anbieter or
            down_val > 0 or
            up_val > 0 or
            ip_adressen or
            failover or
            sla_entstoerzeit > 0 or
            subnetzmaske or
            symmetrisch == "ja" or
            feste_ip == "ja" or
            ist_backup == "ja" or
            (art and art != "DSL")
        )

        if has_user_input or (vorhanden and (anbieter or down_val > 0 or up_val > 0 or art != "DSL" or ist_backup == "ja")):
            anbindungen.append(Internetanbindung(
                anbieter=anbieter if anbieter else "Unbekannt",
                art=art if art else "DSL",
                bandbreite_down_mbit=down_val,
                bandbreite_up_mbit=up_val,
                symmetrisch=symmetrisch,
                feste_ip=feste_ip,
                ip_adressen=ip_adressen,
                subnetzmaske=subnetzmaske,
                sla_entstoerzeit=sla_entstoerzeit,
                ist_backup_leitung=ist_backup,
                failover_verfahren=failover
            ))
    return anbindungen

@router.get("/auftrag/{auftrag_id}/standort/neu")
def new_standort_form(request: Request, auftrag_id: str):
    auftrag = storage.load_auftrag(auftrag_id)
    if not auftrag:
        return RedirectResponse(url="/auftrag", status_code=303)
    sidebar_context = build_sidebar_context(auftrag)
    return templates.TemplateResponse(
        request=request,
        name="standort/form.html",
        context={
            "auftrag": auftrag,
            "standort": None,
            "heutiges_datum": date.today().isoformat(),
            "active_tab": "erfassung",
            "active_nav": "auftrag",
            **sidebar_context
        }
    )

@router.post("/auftrag/{auftrag_id}/standort/neu")
async def new_standort_submit(
    request: Request,
    auftrag_id: str
):
    form_data = await request.form()
    bezeichnung = form_data.get("bezeichnung", "").strip()
    strasse = form_data.get("strasse", "").strip()
    plz = form_data.get("plz", "").strip()
    ort = form_data.get("ort", "").strip()
    anzahl_user = parse_int_german(form_data.get("anzahl_user"))
    funktion = form_data.get("funktion", "").strip()
    ansprechpartner_vor_ort = form_data.get("ansprechpartner_vor_ort", "").strip()
    begehung_am = form_data.get("begehung_am", "").strip()
    redaktionskonzept_backup_leitung = form_data.get("redaktionskonzept_backup_leitung", "automatische_umschaltung")
    trassenfuehrung_getrennt = form_data.get("trassenfuehrung_getrennt", "ja")
    usv_fuer_netzwerktechnik = form_data.get("usv_fuer_netzwerktechnik", "")
    notiz = form_data.get("notiz", "").strip()

    auftrag = storage.load_auftrag(auftrag_id)
    if not auftrag:
        return RedirectResponse(url="/auftrag", status_code=303)

    # Unbekannte Stufe fällt auf die Vorgabe des Auftrags zurück statt ungeprüft
    # gespeichert zu werden — an diesem Feld hängt die Filterung beim Export
    # (Karte #309, gleiche Richtung wie #310).
    vertraulichkeit = gueltiger_wert(
        form_data.get("vertraulichkeit", auftrag.vertraulichkeit_default),
        VERTRAULICHKEIT_OPTIONS,
        auftrag.vertraulichkeit_default,
    )

    existing_ids = [s.id for s in storage.list_standorte(auftrag_id)]
    sto_id = generate_slug_id("standort", bezeichnung, existing_ids)
    anbindungen = _parse_anbindungen_from_form(form_data)

    standort = Standort(
        schema_version=1,
        id=sto_id,
        auftrag_id=auftrag_id,
        bezeichnung=bezeichnung,
        strasse=strasse,
        plz=plz,
        ort=ort,
        anzahl_user=anzahl_user,
        funktion=funktion,
        ansprechpartner_vor_ort=ansprechpartner_vor_ort,
        vertraulichkeit=vertraulichkeit,
        begehung_am=begehung_am if begehung_am else None,
        redaktionskonzept_backup_leitung=redaktionskonzept_backup_leitung,
        trassenfuehrung_getrennt=trassenfuehrung_getrennt,
        usv_fuer_netzwerktechnik=usv_fuer_netzwerktechnik,
        anbindungen=anbindungen,
        notiz=notiz
    )
    storage.save_standort(standort)

    return RedirectResponse(url=f"/auftrag/{auftrag_id}/erfassung", status_code=303)

@router.get("/auftrag/{auftrag_id}/standort/{standort_id}/bearbeiten")
def edit_standort_form(request: Request, auftrag_id: str, standort_id: str):
    auftrag = storage.load_auftrag(auftrag_id)
    standort = storage.load_standort(auftrag_id, standort_id)
    if not auftrag or not standort:
        return RedirectResponse(url=f"/auftrag/{auftrag_id}/erfassung", status_code=303)
    sidebar_context = build_sidebar_context(auftrag)
    return templates.TemplateResponse(
        request=request,
        name="standort/form.html",
        context={
            "auftrag": auftrag,
            "standort": standort,
            "active_tab": "erfassung",
            "active_nav": "auftrag",
            **sidebar_context
        }
    )

@router.post("/auftrag/{auftrag_id}/standort/{standort_id}/bearbeiten")
async def edit_standort_submit(
    request: Request,
    auftrag_id: str,
    standort_id: str
):
    form_data = await request.form()
    standort = storage.load_standort(auftrag_id, standort_id)
    if not standort:
        return RedirectResponse(url=f"/auftrag/{auftrag_id}/erfassung", status_code=303)

    standort.bezeichnung = form_data.get("bezeichnung", standort.bezeichnung).strip()
    standort.strasse = form_data.get("strasse", "").strip()
    standort.plz = form_data.get("plz", "").strip()
    standort.ort = form_data.get("ort", "").strip()
    standort.anzahl_user = parse_int_german(form_data.get("anzahl_user"))
    standort.funktion = form_data.get("funktion", "").strip()
    standort.ansprechpartner_vor_ort = form_data.get("ansprechpartner_vor_ort", "").strip()
    standort.vertraulichkeit = gueltiger_wert(
        form_data.get("vertraulichkeit", standort.vertraulichkeit),
        VERTRAULICHKEIT_OPTIONS,
        standort.vertraulichkeit,
    )
    begehung_am = form_data.get("begehung_am", "").strip()
    standort.begehung_am = begehung_am if begehung_am else None

    if "redaktionskonzept_backup_leitung" in form_data:
        standort.redaktionskonzept_backup_leitung = form_data.get("redaktionskonzept_backup_leitung")
    if "trassenfuehrung_getrennt" in form_data:
        standort.trassenfuehrung_getrennt = form_data.get("trassenfuehrung_getrennt")
    if "usv_fuer_netzwerktechnik" in form_data:
        standort.usv_fuer_netzwerktechnik = form_data.get("usv_fuer_netzwerktechnik")
    standort.notiz = form_data.get("notiz", "").strip()

    standort.anbindungen = _parse_anbindungen_from_form(form_data)

    # Massgeblich ist der Stand, den das Formular beim Laden gesehen hat — nicht
    # der frisch geladene. Sonst stimmt die Version beim Speichern immer überein
    # und die Konflikterkennung könnte nie anschlagen (Karte #308). Fehlt das
    # Feld (Formular aus einer älteren Version), bleibt es beim bisherigen
    # Verhalten.
    standort.version = parse_int_german(form_data.get("version"), standort.version)

    try:
        storage.save_standort(standort)
    except KonfliktFehler:
        return _konflikt_formular(request, auftrag_id, standort_id, standort)

    return RedirectResponse(url=f"/auftrag/{auftrag_id}/erfassung", status_code=303)

def _konflikt_formular(request: Request, auftrag_id: str, standort_id: str, standort: Standort):
    """Liefert das Bearbeitungsformular mit den gerade eingegebenen Werten und
    einem Hinweis zurück, statt sie auf einer Fehlerseite zu verlieren.

    Die Version wird auf den Stand der Platte gehoben: ein zweites Speichern
    soll die fremde Änderung bewusst überschreiben können, statt in derselben
    Meldung hängenzubleiben."""
    auftrag = storage.load_auftrag(auftrag_id)
    if not auftrag:
        return RedirectResponse(url=f"/auftrag/{auftrag_id}/erfassung", status_code=303)

    aktuell = storage.load_standort(auftrag_id, standort_id)
    if aktuell:
        standort.version = aktuell.version

    sidebar_context = build_sidebar_context(auftrag)
    return templates.TemplateResponse(
        request=request,
        name="standort/form.html",
        status_code=409,
        context={
            "auftrag": auftrag,
            "standort": standort,
            "konflikt": True,
            "active_tab": "erfassung",
            "active_nav": "auftrag",
            **sidebar_context
        }
    )

@router.post("/auftrag/{auftrag_id}/standort/{standort_id}/loeschen")
def delete_standort_action(auftrag_id: str, standort_id: str):
    """Löscht einen Standort, sofern keine Technik-Objekte mehr daran hängen.

    Bewusst kein Kaskadenlöschen und kein automatisches Umhängen: was mit den
    erfassten Objekten geschehen soll, weiss nur der Bearbeiter. Sie lassen
    sich über das Objektformular auf einen anderen Standort umstellen oder
    einzeln löschen — beides gibt es bereits."""
    standort = storage.load_standort(auftrag_id, standort_id)
    if not standort:
        return RedirectResponse(url=f"/auftrag/{auftrag_id}/erfassung", status_code=303)

    haengende = [o for o in storage.list_objekte(auftrag_id) if o.standort_id == standort_id]
    if haengende:
        return _loeschen_abgelehnt(auftrag_id, standort, haengende)

    storage.delete_standort(auftrag_id, standort_id)
    return RedirectResponse(url=f"/auftrag/{auftrag_id}/erfassung", status_code=303)

def _loeschen_abgelehnt(auftrag_id: str, standort, haengende) -> HTMLResponse:
    """Benennt die Objekte, die dem Löschen im Weg stehen.

    Ohne diese Liste müsste der Bearbeiter selbst durchzählen, was noch am
    Standort hängt. Bewusst ohne Template, damit die Seite auch dann steht,
    wenn mit den Auftragsdaten etwas nicht stimmt — dieselbe Überlegung wie
    beim Konflikt-Handler in `app/main.py`."""
    name = html.escape(standort.bezeichnung or standort.id)
    anzahl = len(haengende)
    if anzahl == 1:
        satz = (f"An <strong>{name}</strong> hängt noch 1 Objekt. Es muss zuerst auf einen "
                "anderen Standort verschoben oder gelöscht werden — sonst bliebe es ohne "
                "Zuordnung zurück.")
    else:
        satz = (f"An <strong>{name}</strong> hängen noch {anzahl} Objekte. Sie müssen zuerst "
                "auf einen anderen Standort verschoben oder gelöscht werden — sonst blieben "
                "sie ohne Zuordnung zurück.")
    zeilen = "\n".join(
        f'<li><a href="/auftrag/{html.escape(auftrag_id)}/objekt/{html.escape(o.typ)}/{html.escape(o.id)}">'
        f"{html.escape(o.bezeichnung or o.id)}</a></li>"
        for o in haengende
    )
    return HTMLResponse(
        status_code=409,
        content=f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8">
<title>Standort nicht gelöscht</title>
<link rel="stylesheet" href="/static/css/style.css"></head>
<body><div class="container" style="max-width:640px;margin-top:64px;">
<h1 style="font-size:22px;">Standort nicht gelöscht</h1>
<p>{satz}</p>
<ul>{zeilen}</ul>
<p>Zum Verschieben das Objekt öffnen und oben einen anderen Standort wählen.</p>
<p style="margin-top:28px;"><a href="/auftrag/{html.escape(auftrag_id)}/erfassung">Zurück zur Erfassung</a></p>
</div></body></html>""",
    )
