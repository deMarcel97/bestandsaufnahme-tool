"""
Erfassungs-Wizard Routes.

Geführter, vollständiger Durchlauf durch alle Kernbereiche der IT-Bestandsaufnahme beim Kunden.
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
    WizardStepData,
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


def _get_bausteine_labels() -> dict:
    """Gibt die Anzeigenamen aller Baustein-Typen zurück."""
    labels = dict(WIZARD_STEP_LABELS)
    for typ in schema_loader.get_all_types():
        s = schema_loader.get_schema(typ)
        if s and s.get("bezeichnung_anzeige"):
            labels[typ] = s.get("bezeichnung_anzeige")
    return labels


@router.get("/auftrag/{auftrag_id}/wizard")
def wizard_view(request: Request, auftrag_id: str, step: Optional[int] = None):
    """Startet oder setzt den Erfassungs-Wizard fort."""
    auftrag = get_auftrag_or_redirect(auftrag_id)
    if isinstance(auftrag, RedirectResponse):
        return auftrag

    progress = storage.load_wizard_progress(auftrag_id)
    if not progress:
        progress = storage.init_wizard_progress(auftrag_id)
        if not progress:
            return RedirectResponse(url=f"/auftrag/{auftrag_id}", status_code=303)

    # Optionalen Ziel-Schritt über Query-Parameter ansteuern
    if step is not None and 1 <= step <= len(WIZARD_STEP_TYPES):
        progress.current_step = step
        storage.save_wizard_progress(progress)

    # Wenn der letzte Schritt erreicht ist, zur Zusammenfassung
    if progress.current_step >= len(WIZARD_STEP_TYPES):
        return RedirectResponse(url=f"/auftrag/{auftrag_id}/wizard/zusammenfassung", status_code=303)

    current_step = progress.current_step
    step_type = WIZARD_STEP_TYPES[current_step - 1] if current_step <= len(WIZARD_STEP_TYPES) else "zusammenfassung"
    step_data = progress.steps.get(current_step)

    standorte = storage.list_standorte(auftrag_id)
    objekte = storage.list_objekte(auftrag_id)
    sidebar_context = build_sidebar_context(auftrag, standorte, objekte)

    # Standard-Standort sicherstellen
    if not standorte:
        sto_id = generate_slug_id("standort", "Hauptsitz", [])
        new_standort = Standort(
            schema_version=1,
            id=sto_id,
            auftrag_id=auftrag_id,
            bezeichnung="Hauptsitz",
            anzahl_user=10,
        )
        storage.save_standort(new_standort)
        standorte = [new_standort]

    context = {
        "auftrag": auftrag,
        "progress": progress,
        "current_step": current_step,
        "total_steps": len(WIZARD_STEP_TYPES),
        "data_steps_count": len(WIZARD_STEP_TYPES) - 1,
        "step_type": step_type,
        "step_label": WIZARD_STEP_LABELS.get(step_type, step_type),
        "step_data": step_data.data if step_data else {},
        "standorte": standorte,
        "standort": standorte[0] if standorte else None,
        "objekte": objekte,
        "bausteine": auftrag.aktive_bausteine,
        "baustein_labels": _get_bausteine_labels(),
        "active_nav": "auftrag",
        **sidebar_context,
    }

    return templates.TemplateResponse(
        request=request,
        name="auftrag/wizard.html",
        context=context,
    )


@router.post("/auftrag/{auftrag_id}/wizard/init")
def wizard_init(auftrag_id: str):
    """Initialisiert einen neuen Wizard-Fortschritt und startet bei Schritt 1."""
    auftrag = get_auftrag_or_redirect(auftrag_id)
    if isinstance(auftrag, RedirectResponse):
        return auftrag

    storage.delete_wizard_progress(auftrag_id)
    progress = create_empty_wizard_progress(auftrag_id)
    storage.save_wizard_progress(progress)

    return RedirectResponse(url=f"/auftrag/{auftrag_id}/wizard", status_code=303)


@router.get("/auftrag/{auftrag_id}/wizard/goto/{step}")
def wizard_goto(auftrag_id: str, step: int):
    """Springt direkt zu einem bestimmten Schritt."""
    progress = storage.load_wizard_progress(auftrag_id)
    if progress and 1 <= step <= len(WIZARD_STEP_TYPES):
        progress.current_step = step
        storage.save_wizard_progress(progress)
    return RedirectResponse(url=f"/auftrag/{auftrag_id}/wizard", status_code=303)


@router.get("/auftrag/{auftrag_id}/wizard/back")
def wizard_back(auftrag_id: str):
    """Geht zum vorherigen Schritt zurück."""
    progress = storage.load_wizard_progress(auftrag_id)
    if progress:
        progress.current_step = max(1, progress.current_step - 1)
        storage.save_wizard_progress(progress)
    return RedirectResponse(url=f"/auftrag/{auftrag_id}/wizard", status_code=303)


@router.post("/auftrag/{auftrag_id}/wizard/step/{step}")
async def wizard_save_step(
    request: Request,
    auftrag_id: str,
    step: int,
):
    """Speichert die Formulardaten eines Schritts und rückt zum nächsten vor."""
    auftrag = get_auftrag_or_redirect(auftrag_id)
    if isinstance(auftrag, RedirectResponse):
        return auftrag

    progress = storage.load_wizard_progress(auftrag_id)
    if not progress:
        progress = storage.init_wizard_progress(auftrag_id)

    form_data = await request.form()
    step_data = dict(form_data)

    step_type = WIZARD_STEP_TYPES[step - 1] if step <= len(WIZARD_STEP_TYPES) else "zusammenfassung"

    progress.steps[step] = WizardStepData(
        step_type=step_type,
        data=step_data,
        timestamp=datetime.now().isoformat(),
        completed=True,
    )
    if step not in progress.completed_steps:
        progress.completed_steps.append(step)
    progress.current_step = step + 1
    progress.last_updated = datetime.now().isoformat()

    try:
        storage.save_wizard_progress(progress)
    except KonfliktFehler:
        existing = storage.load_wizard_progress(auftrag_id)
        progress.version = (existing.version + 1) if existing else 1
        storage.save_wizard_progress(progress)

    if progress.current_step >= len(WIZARD_STEP_TYPES):
        return RedirectResponse(url=f"/auftrag/{auftrag_id}/wizard/zusammenfassung", status_code=303)

    return RedirectResponse(url=f"/auftrag/{auftrag_id}/wizard", status_code=303)


@router.get("/auftrag/{auftrag_id}/wizard/skip")
@router.post("/auftrag/{auftrag_id}/wizard/skip")
def wizard_skip_step(auftrag_id: str):
    """Überspringt den aktuellen Schritt."""
    progress = storage.load_wizard_progress(auftrag_id)
    if not progress:
        return RedirectResponse(url=f"/auftrag/{auftrag_id}/wizard", status_code=303)

    current_step = progress.current_step
    step_type = WIZARD_STEP_TYPES[current_step - 1] if current_step <= len(WIZARD_STEP_TYPES) else "zusammenfassung"

    progress.steps[current_step] = WizardStepData(
        step_type=step_type,
        data={},
        timestamp=datetime.now().isoformat(),
        completed=True,
    )
    if current_step not in progress.completed_steps:
        progress.completed_steps.append(current_step)
    progress.current_step = current_step + 1
    progress.last_updated = datetime.now().isoformat()

    storage.save_wizard_progress(progress)

    if progress.current_step >= len(WIZARD_STEP_TYPES):
        return RedirectResponse(url=f"/auftrag/{auftrag_id}/wizard/zusammenfassung", status_code=303)

    return RedirectResponse(url=f"/auftrag/{auftrag_id}/wizard", status_code=303)


@router.get("/auftrag/{auftrag_id}/wizard/abbruch")
@router.post("/auftrag/{auftrag_id}/wizard/abbruch")
def wizard_abbruch(auftrag_id: str):
    """Bricht den Wizard ab und kehrt zur Auftragsansicht zurück (Fortschritt bleibt erhalten)."""
    return RedirectResponse(url=f"/auftrag/{auftrag_id}", status_code=303)


@router.get("/auftrag/{auftrag_id}/wizard/zusammenfassung")
def wizard_zusammenfassung(request: Request, auftrag_id: str):
    """Zeigt die Zusammenfassung aller im Wizard erfassten Daten."""
    auftrag = get_auftrag_or_redirect(auftrag_id)
    if isinstance(auftrag, RedirectResponse):
        return auftrag

    progress = storage.load_wizard_progress(auftrag_id)
    if not progress:
        return RedirectResponse(url=f"/auftrag/{auftrag_id}/wizard", status_code=303)

    standorte = storage.list_standorte(auftrag_id)
    objekte = storage.list_objekte(auftrag_id)
    sidebar_context = build_sidebar_context(auftrag, standorte, objekte)

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
            **sidebar_context,
        },
    )


@router.post("/auftrag/{auftrag_id}/wizard/abschliessen")
def wizard_abschliessen(auftrag_id: str):
    """Schließt den Wizard ab und legt automatisch alle aktivierten Bausteine und Objekte an."""
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
                    anzahl_user=10,
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
                anzahl_user=10,
            )

    # 3. Schritt: Internetanbindungen
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
            bandbreite_up_mbit=up,
            feste_ip_vorhanden=d3.get("feste_ip_vorhanden") or "unbekannt",
            redundante_anbindung=d3.get("redundante_anbindung") or "unbekannt",
        )
        if not standort.anbindungen:
            standort.anbindungen.append(anbindung)
        else:
            standort.anbindungen[0] = anbindung

    # Standort speichern
    storage.save_standort(standort)

    existing_objekte = storage.list_objekte(auftrag_id)

    # 4. Schritt: Firewall
    d4 = summary_data.get("firewall") or {}
    if d4 and d4.get("hat_firewall") == "ja":
        if "firewall" not in auftrag.aktive_bausteine:
            auftrag.aktive_bausteine.append("firewall")

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
                "hardware_alter": d4.get("hardware_alter", "unter_3_jahre"),
                "wartungsvertrag_vorhanden": d4.get("wartungsvertrag_vorhanden", "unbekannt"),
                "ha_cluster_eingerichtet": d4.get("ha_cluster_eingerichtet", "unbekannt"),
                "ips_ids_aktiv": d4.get("ips_ids_aktiv", "unbekannt"),
            },
        )
        storage.save_objekt(fw_objekt)
        existing_objekte.append(fw_objekt)

    # 5. Schritt: Switch
    d5 = summary_data.get("switch") or {}
    if d5 and d5.get("hat_switch") == "ja":
        if "switch" not in auftrag.aktive_bausteine:
            auftrag.aktive_bausteine.append("switch")

        ports_val = 24
        if d5.get("port_anzahl"):
            try:
                ports_val = int(d5["port_anzahl"])
            except (ValueError, TypeError):
                pass

        genutzt_val = 0
        if d5.get("ports_belegt"):
            try:
                genutzt_val = int(d5["ports_belegt"])
            except (ValueError, TypeError):
                pass

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
                "management_typ": d5.get("management_typ", "managed_l2"),
                "netztrennung": d5.get("netztrennung", "vlan_getrennt"),
                "poe_vorhanden": d5.get("poe_vorhanden", "unbekannt"),
            },
        )
        storage.save_objekt(sw_objekt)
        existing_objekte.append(sw_objekt)

    # 6. Schritt: Access Point / WLAN
    d6 = summary_data.get("access_point") or {}
    if d6 and d6.get("hat_access_point") == "ja":
        if "access_point" not in auftrag.aktive_bausteine:
            auftrag.aktive_bausteine.append("access_point")

        ap_id = generate_slug_id("access_point", d6.get("modell") or d6.get("hersteller") or "WLAN AP", [o.id for o in existing_objekte])
        ap_bez = f"Access Point {d6.get('modell', '')}".strip() or f"Access Point {d6.get('hersteller', '')}".strip() or "Access Point"
        ap_objekt = TechnikObjekt(
            schema_version=1,
            id=ap_id,
            typ="access_point",
            bezeichnung=ap_bez,
            auftrag_id=auftrag_id,
            standort_id=standort.id if standort else None,
            erfassungsstatus="teilweise",
            daten={
                "hersteller": d6.get("hersteller", ""),
                "modell": d6.get("modell", ""),
                "gast_wlan_vorhanden": d6.get("gast_wlan_vorhanden", "ja"),
                "gast_wlan_isoliert": d6.get("gast_wlan_isoliert", "ja"),
                "verschluesselung_wpa3": d6.get("verschluesselung_wpa3", "unbekannt"),
                "management": d6.get("management", "cloud_controller"),
            },
        )
        storage.save_objekt(ap_objekt)
        existing_objekte.append(ap_objekt)

    # 7. Schritt: Server & Virtualisierung
    d7 = summary_data.get("server_virtualisierung") or {}
    if d7 and d7.get("hat_server") == "ja":
        if "server_virtualisierung" not in auftrag.aktive_bausteine:
            auftrag.aktive_bausteine.append("server_virtualisierung")

        vms_count = 0
        if d7.get("anzahl_vms"):
            try:
                vms_count = int(d7["anzahl_vms"])
            except (ValueError, TypeError):
                pass

        srv_id = generate_slug_id("server_virtualisierung", d7.get("modell") or d7.get("hersteller") or "Server", [o.id for o in existing_objekte])
        srv_bez = f"Server {d7.get('modell', '')}".strip() or f"Server {d7.get('hersteller', '')}".strip() or "Server-Infrastruktur"
        srv_objekt = TechnikObjekt(
            schema_version=1,
            id=srv_id,
            typ="server_virtualisierung",
            bezeichnung=srv_bez,
            auftrag_id=auftrag_id,
            standort_id=standort.id if standort else None,
            erfassungsstatus="teilweise",
            daten={
                "wird_virtualisiert": d7.get("wird_virtualisiert", "ja"),
                "hypervisor_typ": d7.get("hypervisor_typ", "vmware_esxi"),
                "hersteller": d7.get("hersteller", ""),
                "modell": d7.get("modell", ""),
                "anzahl_vms": vms_count,
                "hardware_alter": d7.get("hardware_alter", "unter_3_jahre"),
                "wartungsvertrag_vorhanden": d7.get("wartungsvertrag_vorhanden", "ja"),
                "ha_cluster_eingerichtet": d7.get("ha_cluster_eingerichtet", "unbekannt"),
            },
        )
        storage.save_objekt(srv_objekt)
        existing_objekte.append(srv_objekt)

    # 8. Schritt: Storage / NAS
    d8 = summary_data.get("storage") or {}
    if d8 and d8.get("hat_storage") == "ja":
        if "storage" not in auftrag.aktive_bausteine:
            auftrag.aktive_bausteine.append("storage")

        brutto_val = 0.0
        netto_val = 0.0
        fuell_val = 0
        try:
            if d8.get("kapazitaet_brutto_tb"):
                brutto_val = float(str(d8["kapazitaet_brutto_tb"]).replace(",", "."))
            if d8.get("kapazitaet_netto_tb"):
                netto_val = float(str(d8["kapazitaet_netto_tb"]).replace(",", "."))
            if d8.get("fuellgrad_prozent"):
                fuell_val = int(d8["fuellgrad_prozent"])
        except (ValueError, TypeError):
            pass

        sto_obj_id = generate_slug_id("storage", d8.get("hersteller_shared") or "Storage", [o.id for o in existing_objekte])
        sto_bez = f"Storage {d8.get('hersteller_shared', '')}".strip() or "Zentraler Datenspeicher"
        sto_objekt = TechnikObjekt(
            schema_version=1,
            id=sto_obj_id,
            typ="storage",
            bezeichnung=sto_bez,
            auftrag_id=auftrag_id,
            standort_id=standort.id if standort else None,
            erfassungsstatus="teilweise",
            daten={
                "bereitstellung": d8.get("bereitstellung", "shared_storage"),
                "hersteller_shared": d8.get("hersteller_shared", "Synology"),
                "kapazitaet_brutto_tb": brutto_val,
                "kapazitaet_netto_tb": netto_val,
                "fuellgrad_prozent": fuell_val,
                "wartungsvertrag_status": d8.get("wartungsvertrag_status", "aktiv_hersteller"),
            },
        )
        storage.save_objekt(sto_objekt)
        existing_objekte.append(sto_objekt)

    # 9. Schritt: Backup & Recovery
    d9 = summary_data.get("backup") or {}
    if d9 and d9.get("hat_backup") == "ja":
        if "backup" not in auftrag.aktive_bausteine:
            auftrag.aktive_bausteine.append("backup")

        bk_id = generate_slug_id("backup", d9.get("backup_software") or "Backup", [o.id for o in existing_objekte])
        bk_bez = f"Backup {d9.get('backup_software', '')}".strip() or "Backup & Recovery"
        bk_objekt = TechnikObjekt(
            schema_version=1,
            id=bk_id,
            typ="backup",
            bezeichnung=bk_bez,
            auftrag_id=auftrag_id,
            standort_id=standort.id if standort else None,
            erfassungsstatus="teilweise",
            daten={
                "backup_software": d9.get("backup_software", "veeam"),
                "backup_ziel": d9.get("backup_ziel", "lokal_nas"),
                "strategie": d9.get("strategie", "3_2_1_regel"),
                "testwiederherstellung": d9.get("testwiederherstellung", "ja_regelmaessig_protokolliert"),
                "unveraenderliches_backup": d9.get("unveraenderliches_backup", "unbekannt"),
            },
        )
        storage.save_objekt(bk_objekt)
        existing_objekte.append(bk_objekt)

    # 10. Schritt: USV
    d10 = summary_data.get("usv") or {}
    if d10 and d10.get("hat_usv") == "ja":
        if "usv" not in auftrag.aktive_bausteine:
            auftrag.aktive_bausteine.append("usv")

        ueb_min = 15
        if d10.get("ueberbrueckungszeit_minuten"):
            try:
                ueb_min = int(d10["ueberbrueckungszeit_minuten"])
            except (ValueError, TypeError):
                pass

        usv_id = generate_slug_id("usv", d10.get("modell") or d10.get("hersteller") or "USV", [o.id for o in existing_objekte])
        usv_bez = f"USV {d10.get('modell', '')}".strip() or f"USV {d10.get('hersteller', '')}".strip() or "USV Stromversorgung"
        usv_objekt = TechnikObjekt(
            schema_version=1,
            id=usv_id,
            typ="usv",
            bezeichnung=usv_bez,
            auftrag_id=auftrag_id,
            standort_id=standort.id if standort else None,
            erfassungsstatus="teilweise",
            daten={
                "hersteller": d10.get("hersteller", "APC"),
                "modell": d10.get("modell", ""),
                "batterie_alter": d10.get("batterie_alter", "unter_3_jahre"),
                "abschaltsignal_an_server": d10.get("abschaltsignal_an_server", "ja"),
                "ueberbrueckungszeit_minuten": ueb_min,
            },
        )
        storage.save_objekt(usv_objekt)
        existing_objekte.append(usv_objekt)

    # 11. Schritt: Clients
    d11 = summary_data.get("clients") or {}
    if d11 and d11.get("hat_clients") == "ja":
        if "clients" not in auftrag.aktive_bausteine:
            auftrag.aktive_bausteine.append("clients")

        win_c = 0
        mac_c = 0
        lin_c = 0
        try:
            if d11.get("anzahl_windows_clients"):
                win_c = int(d11["anzahl_windows_clients"])
            if d11.get("anzahl_mac_clients"):
                mac_c = int(d11["anzahl_mac_clients"])
            if d11.get("anzahl_linux_clients"):
                lin_c = int(d11["anzahl_linux_clients"])
        except (ValueError, TypeError):
            pass

        cl_id = generate_slug_id("clients", "Clients", [o.id for o in existing_objekte])
        cl_objekt = TechnikObjekt(
            schema_version=1,
            id=cl_id,
            typ="clients",
            bezeichnung="Clients / Endgeräte",
            auftrag_id=auftrag_id,
            standort_id=standort.id if standort else None,
            erfassungsstatus="teilweise",
            daten={
                "anzahl_windows_clients": win_c,
                "anzahl_mac_clients": mac_c,
                "anzahl_linux_clients": lin_c,
                "haupt_betriebssystem_version": d11.get("haupt_betriebssystem_version", "windows_11"),
                "edr_antivirus_zentral_gemanagt": d11.get("edr_antivirus_zentral_gemanagt", "ja"),
                "zentrales_patchmanagement_aktiv": d11.get("zentrales_patchmanagement_aktiv", "ja"),
                "lokale_adminrechte_eingeschraenkt": d11.get("lokale_adminrechte_eingeschraenkt", "ja"),
                "festplattenverschluesselung_aktiv": d11.get("festplattenverschluesselung_aktiv", "unbekannt"),
            },
        )
        storage.save_objekt(cl_objekt)
        existing_objekte.append(cl_objekt)

    # 12. Schritt: M365 / Cloud Security
    d12 = summary_data.get("m365_security") or {}
    if d12 and d12.get("hat_m365") == "ja":
        if "m365_security" not in auftrag.aktive_bausteine:
            auftrag.aktive_bausteine.append("m365_security")

        m365_id = generate_slug_id("m365_security", "M365 Cloud", [o.id for o in existing_objekte])
        m365_objekt = TechnikObjekt(
            schema_version=1,
            id=m365_id,
            typ="m365_security",
            bezeichnung="Microsoft 365 / Cloud-Security",
            auftrag_id=auftrag_id,
            standort_id=None,
            erfassungsstatus="teilweise",
            daten={
                "tenant_typ": d12.get("tenant_typ", "microsoft_365_business"),
                "mfa_fuer_alle_benutzer": d12.get("mfa_fuer_alle_benutzer", "ja"),
                "mfa_fuer_administratoren": d12.get("mfa_fuer_administratoren", "ja"),
                "m365_drittanbieter_backup_aktiv": d12.get("m365_drittanbieter_backup_aktiv", "ja"),
                "conditional_access_regelwerke": d12.get("conditional_access_regelwerke", "unbekannt"),
            },
        )
        storage.save_objekt(m365_objekt)
        existing_objekte.append(m365_objekt)

    # 13. Schritt: Organisation & Prozesse
    d13 = summary_data.get("organisation_prozesse") or {}
    if d13 and d13.get("hat_organisation") == "ja":
        if "organisation_prozesse" not in auftrag.aktive_bausteine:
            auftrag.aktive_bausteine.append("organisation_prozesse")

        org_id = generate_slug_id("organisation_prozesse", "Organisation", [o.id for o in existing_objekte])
        org_objekt = TechnikObjekt(
            schema_version=1,
            id=org_id,
            typ="organisation_prozesse",
            bezeichnung="Organisation & IT-Sicherheitsmanagement",
            auftrag_id=auftrag_id,
            standort_id=None,
            erfassungsstatus="teilweise",
            daten={
                "notfallhandbuch_status": d13.get("notfallhandbuch_status", "nicht_vorhanden"),
                "it_dokumentation_status": d13.get("it_dokumentation_status", "lueckenhaft"),
                "it_sicherheitsrichtlinie_unterschrieben": d13.get("it_sicherheitsrichtlinie_unterschrieben", "nein"),
                "passwort_manager_einsatz": d13.get("passwort_manager_einsatz", "optional_vorhanden"),
                "mitarbeiter_awareness_schulungen": d13.get("mitarbeiter_awareness_schulungen", "nein"),
            },
        )
        storage.save_objekt(org_objekt)
        existing_objekte.append(org_objekt)

    # Auftrag mit aktualisierten Stammdaten & aktiven Bausteinen speichern
    storage.save_auftrag(auftrag)

    # Wizard-Fortschritt löschen
    storage.delete_wizard_progress(auftrag_id)

    return RedirectResponse(url=f"/auftrag/{auftrag_id}/erfassung", status_code=303)
