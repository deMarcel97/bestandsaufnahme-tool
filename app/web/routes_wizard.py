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
from app.models.standort import Standort, Internetanbindung
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


@router.post("/auftrag/{auftrag_id}/wizard/step/{step}")
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

    summary_data = {}
    for step_num, step_data in progress.steps.items():
        summary_data[step_data.step_type] = step_data.data

    # 1. Schritt: Auftragsgrunddaten
    d1 = summary_data.get("auftragsgrunddaten") or {}
    if d1:
        if d1.get("kunde"):
            auftrag.kunde = d1["kunde"].strip()
        if "projekt_nummer" in d1:
            auftrag.projekt_nummer = d1["projekt_nummer"].strip()
        if d1.get("bezeichnung"):
            auftrag.bezeichnung = d1["bezeichnung"].strip()
        if "abgrenzung" in d1:
            auftrag.abgrenzung = d1["abgrenzung"].strip()

    # 2. Schritt: Standort-Grunddaten
    d2 = summary_data.get("standort_grunddaten") or {}
    standorte = storage.list_standorte(auftrag_id)
    standort = None
    if d2:
        sto_id = d2.get("standort_id")
        if sto_id:
            standort = storage.load_standort(auftrag_id, sto_id)
        if not standort:
            if standorte:
                standort = standorte[0]
            else:
                new_id = generate_slug_id("standort", d2.get("bezeichnung") or "Hauptsitz", [s.id for s in standorte])
                standort = Standort(
                    schema_version=1,
                    id=new_id,
                    auftrag_id=auftrag_id,
                    bezeichnung=d2.get("bezeichnung") or "Hauptsitz",
                    anzahl_user=10
                )
        if d2.get("bezeichnung"):
            standort.bezeichnung = d2["bezeichnung"].strip()
        if d2.get("anzahl_user"):
            try:
                standort.anzahl_user = int(d2["anzahl_user"])
            except (ValueError, TypeError):
                pass
        if "strasse" in d2:
            standort.strasse = d2["strasse"].strip()
        if "plz" in d2:
            standort.plz = d2["plz"].strip()
        if "ort" in d2:
            standort.ort = d2["ort"].strip()
        if "ansprechpartner_vor_ort" in d2:
            standort.ansprechpartner_vor_ort = d2["ansprechpartner_vor_ort"].strip()
        if "funktion" in d2:
            standort.funktion = d2["funktion"].strip()
    else:
        if standorte:
            standort = standorte[0]
        else:
            sto_id = generate_slug_id("standort", "Hauptsitz", [])
            standort = Standort(
                schema_version=1,
                id=sto_id,
                auftrag_id=auftrag_id,
                bezeichnung="Hauptsitz",
                anzahl_user=10
            )

    # 3. Schritt: Internetanbindungen am Standort
    d3 = summary_data.get("internetanbindungen") or {}
    if d3 and d3.get("hat_internetanbindung") == "ja":
        down = 0.0
        up = 0.0
        try:
            if d3.get("bandbreite_down"):
                down = float(str(d3["bandbreite_down"]).replace(",", "."))
        except ValueError:
            pass
        try:
            if d3.get("bandbreite_up"):
                up = float(str(d3["bandbreite_up"]).replace(",", "."))
        except ValueError:
            pass

        anbindung = Internetanbindung(
            anbieter=d3.get("anbieter", "").strip(),
            art=d3.get("art") or "DSL",
            bandbreite_down_mbit=down,
            bandbreite_up_mbit=up
        )
        if not standort.anbindungen:
            standort.anbindungen.append(anbindung)
        else:
            standort.anbindungen[0] = anbindung

    # Standort speichern
    storage.save_standort(standort)

    # 4. Schritt: Firewall
    existing_objekte = storage.list_objekte(auftrag_id)
    d4 = summary_data.get("firewall") or {}
    if d4 and d4.get("hat_firewall") == "ja":
        if "firewall" not in auftrag.aktive_bausteine:
            auftrag.aktive_bausteine.append("firewall")

        alter_val = ""
        if d4.get("alter"):
            alter_val = str(d4["alter"]).strip()

        wartung_val = "ja" if d4.get("wartungsvertrag") == "ja" else ("nein" if d4.get("wartungsvertrag") == "nein" else "")

        fw_id = generate_slug_id("firewall", d4.get("modell") or d4.get("hersteller") or "Firewall", [o.id for o in existing_objekte])
        fw_bez = f"Firewall {d4.get('modell', '')}".strip() or f"Firewall {d4.get('hersteller', '')}".strip() or "Firewall"
        fw_objekt = TechnikObjekt(
            schema_version=1,
            id=fw_id,
            typ="firewall",
            bezeichnung=fw_bez,
            auftrag_id=auftrag_id,
            standort_id=standort.id if standort else None,
            erfassungsstatus="teilweise",
            daten={
                "hersteller": d4.get("hersteller", ""),
                "modell": d4.get("modell", ""),
                "hardware_alter": alter_val,
                "wartungsvertrag_vorhanden": wartung_val
            }
        )
        storage.save_objekt(fw_objekt)
        existing_objekte.append(fw_objekt)

    # 5. Schritt: Switch
    d5 = summary_data.get("switch") or {}
    if d5 and d5.get("hat_switch") == "ja":
        if "switch" not in auftrag.aktive_bausteine:
            auftrag.aktive_bausteine.append("switch")

        ports_val = 0
        if d5.get("anzahl_ports"):
            try:
                ports_val = int(d5["anzahl_ports"])
            except (ValueError, TypeError):
                pass

        genutzt_val = 0
        if d5.get("anzahl_genutzt"):
            try:
                genutzt_val = int(d5["anzahl_genutzt"])
            except (ValueError, TypeError):
                pass

        switch_typ = "fully_managed" if d5.get("managed") == "managed" else ("unmanaged" if d5.get("managed") == "unmanaged" else "")

        sw_id = generate_slug_id("switch", d5.get("modell") or d5.get("hersteller") or "Switch", [o.id for o in existing_objekte])
        sw_bez = f"Switch {d5.get('modell', '')}".strip() or f"Switch {d5.get('hersteller', '')}".strip() or "Switch"
        sw_objekt = TechnikObjekt(
            schema_version=1,
            id=sw_id,
            typ="switch",
            bezeichnung=sw_bez,
            auftrag_id=auftrag_id,
            standort_id=standort.id if standort else None,
            erfassungsstatus="teilweise",
            daten={
                "hersteller": d5.get("hersteller", ""),
                "modell": d5.get("modell", ""),
                "port_anzahl": ports_val,
                "ports_belegt": genutzt_val,
                "switch_typ": switch_typ
            }
        )
        storage.save_objekt(sw_objekt)
        existing_objekte.append(sw_objekt)

    # 6. Schritt: Backup
    d6 = summary_data.get("backup") or {}
    if d6 and d6.get("hat_backup") == "ja":
        if "backup" not in auftrag.aktive_bausteine:
            auftrag.aktive_bausteine.append("backup")

        sw_raw = (d6.get("software") or "").lower()
        sw_map = {
            "veeam": "veeam",
            "synology": "synology_active_backup",
            "datto": "datto_bcdr",
            "acronis": "acronis_cyber_protect",
            "proxmox": "proxmox_backup_server",
            "commvault": "commvault"
        }
        sw_val = "sonstige"
        for k, v in sw_map.items():
            if k in sw_raw:
                sw_val = v
                break
        if not sw_raw:
            sw_val = "unbekannt"

        bk_id = generate_slug_id("backup", d6.get("software") or "Backup", [o.id for o in existing_objekte])
        bk_bez = f"Backup {d6.get('software', '')}".strip() or "Backup & Recovery"
        bk_objekt = TechnikObjekt(
            schema_version=1,
            id=bk_id,
            typ="backup",
            bezeichnung=bk_bez,
            auftrag_id=auftrag_id,
            standort_id=standort.id if standort else None,
            erfassungsstatus="teilweise",
            daten={
                "backup_software": sw_val,
                "backup_ziel": d6.get("ziel", ""),
                "strategie": d6.get("strategie", ""),
                "testwiederherstellung": d6.get("testwiederherstellung", "")
            }
        )
        storage.save_objekt(bk_objekt)

    # Auftrag mit aktualisierten aktiven Bausteinen und Grunddaten speichern
    storage.save_auftrag(auftrag)

    # Wizard-Fortschritt löschen
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
