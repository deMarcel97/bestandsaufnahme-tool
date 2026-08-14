from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from app.config import BASE_DIR
from app.services.storage import storage
from app.services.schema_loader import schema_loader
from app.services.slug import generate_slug_id
from app.models.technik import TechnikObjekt
from app.utils.number_parser import parse_float_german, parse_int_german

router = APIRouter()
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))

def _collect_objekt_referenz_candidates(auftrag_id: str, schema: dict) -> dict:
    """Baut für jedes 'objekt_referenz'-Feld im Schema die Liste wählbarer Zielobjekte
    (über alle 'ziel_typen' hinweg, mit Typ + Standort im Label zur Unterscheidung)."""
    candidates = {}
    standorte_map = None
    for abschnitt in schema.get("abschnitte", []):
        for feldef in abschnitt.get("felder", []):
            if feldef.get("typ") != "objekt_referenz":
                continue
            if standorte_map is None:
                standorte_map = {s.id: s.bezeichnung for s in storage.list_standorte(auftrag_id)}
            opts = []
            for zt in feldef.get("ziel_typen", []):
                zt_schema = schema_loader.get_schema(zt)
                zt_label = zt_schema.get("bezeichnung_anzeige", zt.capitalize()).split("/")[0].strip() if zt_schema else zt.capitalize()
                for o in storage.list_objekte(auftrag_id, typ=zt):
                    sto_name = standorte_map.get(o.standort_id, "")
                    label = f"{zt_label}: {o.bezeichnung}" + (f" ({sto_name})" if sto_name else "")
                    opts.append({"id": o.id, "label": label})
            candidates[feldef.get("name")] = opts
    return candidates

def _parse_liste_field(form_data, feldef: dict) -> list:
    """Parst wiederholbare Zeilen eines 'liste'-Feldes aus Formulardaten mit Keys der
    Form '{feldname}_{idx}_{unterfeldname}', analog zu _parse_anbindungen_from_form."""
    fname = feldef.get("name")
    sub_felder = feldef.get("felder", [])
    prefix = f"{fname}_"
    indices = set()
    for key in form_data.keys():
        if not key.startswith(prefix):
            continue
        rest = key[len(prefix):]
        if "_" not in rest:
            continue
        idx_str, sub_name = rest.split("_", 1)
        if idx_str.isdigit() and any(sf.get("name") == sub_name for sf in sub_felder):
            indices.add(int(idx_str))

    rows = []
    for idx in sorted(indices):
        row = {}
        has_value = False
        for sf in sub_felder:
            sf_name = sf.get("name")
            val = form_data.get(f"{fname}_{idx}_{sf_name}")
            if val is None:
                continue
            if sf.get("typ") == "zahl":
                if str(val).strip() != "":
                    row[sf_name] = parse_float_german(val)
                    has_value = True
            else:
                val = val.strip() if isinstance(val, str) else val
                row[sf_name] = val
                if val:
                    has_value = True
        if has_value:
            rows.append(row)
    return rows

@router.get("/auftrag/{auftrag_id}/objekt/neu")
def new_objekt_form(request: Request, auftrag_id: str, typ: str = "firewall", standort_id: str = ""):
    auftrag = storage.load_auftrag(auftrag_id)
    if not auftrag:
        return RedirectResponse(url="/auftrag", status_code=303)

    schema = schema_loader.get_schema(typ)
    if not schema:
        return RedirectResponse(url=f"/auftrag/{auftrag_id}", status_code=303)

    standorte = storage.list_standorte(auftrag_id)
    selected_sto = next((s for s in standorte if s.id == standort_id), None)
    if not selected_sto and standorte:
        selected_sto = standorte[0]
        standort_id = selected_sto.id

    sto_label = selected_sto.bezeichnung if selected_sto else "Hauptstandort"
    schema_label = schema.get("bezeichnung_anzeige", typ.capitalize()).split("/")[0].strip()
    default_bezeichnung = f"{schema_label} {sto_label}"

    return templates.TemplateResponse(
        request=request,
        name="technik/form.html",
        context={
            "auftrag": auftrag,
            "schema": schema,
            "standorte": standorte,
            "selected_standort_id": standort_id,
            "default_bezeichnung": default_bezeichnung,
            "objekt_referenz_candidates": _collect_objekt_referenz_candidates(auftrag_id, schema),
            "obj": None,
            "active_nav": "auftrag"
        }
    )

@router.post("/auftrag/{auftrag_id}/objekt/neu")
async def new_objekt_submit(request: Request, auftrag_id: str, typ: str = "firewall"):
    auftrag = storage.load_auftrag(auftrag_id)
    if not auftrag:
        return RedirectResponse(url="/auftrag", status_code=303)

    schema = schema_loader.get_schema(typ)
    if not schema:
        return RedirectResponse(url=f"/auftrag/{auftrag_id}", status_code=303)

    form_data = await request.form()
    bezeichnung = form_data.get("bezeichnung", f"{typ.capitalize()} Gerät")
    standort_id = form_data.get("standort_id", "")
    betreut_durch = form_data.get("betreut_durch", "Kunde")
    dienstleister_name = form_data.get("dienstleister_name", "")
    notiz = form_data.get("notiz", "")
    vertraulichkeit = form_data.get("vertraulichkeit", auftrag.vertraulichkeit_default)
    erfassungsstatus = form_data.get("erfassungsstatus", "unbekannt")

    existing_ids = [o.id for o in storage.list_objekte(auftrag_id)]
    obj_id = generate_slug_id(typ, bezeichnung, existing_ids)

    # Collect custom schema field values
    daten = {}
    if schema:
        for abschnitt in schema.get("abschnitte", []):
            for feldef in abschnitt.get("felder", []):
                fname = feldef.get("name")
                if feldef.get("typ") == "liste":
                    daten[fname] = _parse_liste_field(form_data, feldef)
                elif fname in form_data:
                    val = form_data.get(fname)
                    if feldef.get("typ") == "zahl" and val is not None and str(val).strip() != "":
                        daten[fname] = parse_float_german(val)
                    else:
                        daten[fname] = val

    obj = TechnikObjekt(
        schema_version=1,
        id=obj_id,
        typ=typ,
        bezeichnung=bezeichnung,
        auftrag_id=auftrag_id,
        standort_id=standort_id,
        betreut_durch=betreut_durch,
        dienstleister_name=dienstleister_name,
        notiz=notiz,
        vertraulichkeit=vertraulichkeit,
        erfassungsstatus=erfassungsstatus,
        daten=daten
    )
    storage.save_objekt(obj)
    return RedirectResponse(url=f"/auftrag/{auftrag_id}", status_code=303)

@router.get("/auftrag/{auftrag_id}/objekt/{typ}/{objekt_id}")
def edit_objekt_form(request: Request, auftrag_id: str, typ: str, objekt_id: str):
    auftrag = storage.load_auftrag(auftrag_id)
    obj = storage.load_objekt(auftrag_id, typ, objekt_id)
    schema = schema_loader.get_schema(typ)
    if not auftrag or not obj or not schema:
        return RedirectResponse(url=f"/auftrag/{auftrag_id}", status_code=303)

    standorte = storage.list_standorte(auftrag_id)
    return templates.TemplateResponse(
        request=request,
        name="technik/form.html",
        context={
            "auftrag": auftrag,
            "schema": schema,
            "standorte": standorte,
            "selected_standort_id": obj.standort_id,
            "objekt_referenz_candidates": _collect_objekt_referenz_candidates(auftrag_id, schema),
            "obj": obj,
            "active_nav": "auftrag"
        }
    )

@router.post("/auftrag/{auftrag_id}/objekt/{typ}/{objekt_id}")
async def edit_objekt_submit(request: Request, auftrag_id: str, typ: str, objekt_id: str):
    obj = storage.load_objekt(auftrag_id, typ, objekt_id)
    if not obj:
        return RedirectResponse(url=f"/auftrag/{auftrag_id}", status_code=303)

    form_data = await request.form()
    obj.bezeichnung = form_data.get("bezeichnung", obj.bezeichnung)
    obj.standort_id = form_data.get("standort_id", obj.standort_id)
    obj.betreut_durch = form_data.get("betreut_durch", obj.betreut_durch)
    obj.dienstleister_name = form_data.get("dienstleister_name", obj.dienstleister_name)
    obj.notiz = form_data.get("notiz", obj.notiz)
    obj.vertraulichkeit = form_data.get("vertraulichkeit", obj.vertraulichkeit)
    obj.erfassungsstatus = form_data.get("erfassungsstatus", obj.erfassungsstatus)

    schema = schema_loader.get_schema(typ)
    if schema:
        for abschnitt in schema.get("abschnitte", []):
            for feldef in abschnitt.get("felder", []):
                fname = feldef.get("name")
                if feldef.get("typ") == "liste":
                    obj.daten[fname] = _parse_liste_field(form_data, feldef)
                elif fname in form_data:
                    val = form_data.get(fname)
                    if feldef.get("typ") == "zahl" and val is not None and str(val).strip() != "":
                        obj.daten[fname] = parse_float_german(val)
                    else:
                        obj.daten[fname] = val

    storage.save_objekt(obj)
    return RedirectResponse(url=f"/auftrag/{auftrag_id}", status_code=303)

@router.post("/auftrag/{auftrag_id}/objekt/{typ}/{objekt_id}/duplizieren")
def duplicate_objekt_action(auftrag_id: str, typ: str, objekt_id: str):
    storage.duplicate_objekt(auftrag_id, typ, objekt_id)
    return RedirectResponse(url=f"/auftrag/{auftrag_id}", status_code=303)

@router.post("/auftrag/{auftrag_id}/objekt/{typ}/{objekt_id}/loeschen")
def delete_objekt_action(auftrag_id: str, typ: str, objekt_id: str):
    storage.delete_objekt(auftrag_id, typ, objekt_id)
    return RedirectResponse(url=f"/auftrag/{auftrag_id}", status_code=303)

@router.post("/auftrag/{auftrag_id}/objekt/mehrere_anlegen")
def batch_create_objekte_submit(
    auftrag_id: str,
    standort_id: str = Form(...),
    typ: str = Form(...),
    anzahl: int = Form(1)
):
    auftrag = storage.load_auftrag(auftrag_id)
    if not auftrag:
        return RedirectResponse(url="/auftrag", status_code=303)

    schema = schema_loader.get_schema(typ)
    if not schema:
        return RedirectResponse(url=f"/auftrag/{auftrag_id}", status_code=303)

    standorte = storage.list_standorte(auftrag_id)
    sto = next((s for s in standorte if s.id == standort_id), None)
    sto_name = sto.bezeichnung if sto else "Standort"

    schema_label = schema.get("bezeichnung_anzeige", typ.capitalize()).split("/")[0].strip()

    existing_objekte = storage.list_objekte(auftrag_id)
    existing_ids = [o.id for o in existing_objekte]
    sto_existing_count = len([o for o in existing_objekte if o.standort_id == standort_id and o.typ == typ])

    target_count = parse_int_german(anzahl, 1)
    target_count = max(1, min(target_count, 20))

    for i in range(1, target_count + 1):
        num = sto_existing_count + i
        bezeichnung = f"{schema_label} {num} ({sto_name})"
        obj_id = generate_slug_id(typ, bezeichnung, existing_ids)
        existing_ids.append(obj_id)

        obj = TechnikObjekt(
            schema_version=1,
            id=obj_id,
            typ=typ,
            bezeichnung=bezeichnung,
            auftrag_id=auftrag_id,
            standort_id=standort_id,
            betreut_durch="Kunde",
            vertraulichkeit=auftrag.vertraulichkeit_default,
            erfassungsstatus="unbekannt",
            daten={}
        )
        storage.save_objekt(obj)

    return RedirectResponse(url=f"/auftrag/{auftrag_id}", status_code=303)
