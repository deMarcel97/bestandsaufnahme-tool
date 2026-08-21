from typing import List, Dict, Any
from app.models.auftrag import Auftrag
from app.models.standort import Standort
from app.models.technik import TechnikObjekt, OffenerPunktItem
from app.services.schema_loader import schema_loader

def _is_field_visible(sichtbar_cond: Any, data_dict: Dict[str, Any]) -> bool:
    if not sichtbar_cond or not isinstance(sichtbar_cond, dict):
        return True
    cond_field = sichtbar_cond.get("feld")
    cond_op = sichtbar_cond.get("operator", "gleich")
    cond_val = sichtbar_cond.get("wert")
    parent_val = data_dict.get(cond_field)

    p_str = "ja" if parent_val is True or str(parent_val).lower() == "ja" else ("nein" if parent_val is False or str(parent_val).lower() in ("nein", "false") else str(parent_val).lower())
    c_str = "ja" if cond_val is True or str(cond_val).lower() == "ja" else ("nein" if cond_val is False or str(cond_val).lower() in ("nein", "false") else str(cond_val).lower())

    if cond_op == "gleich" and p_str != c_str:
        return False
    if cond_op == "ungleich" and p_str == c_str:
        return False
    return True


class ProgressService:
    def calculate_progress(self, aktive_bausteine: List[str], objekte: List[TechnikObjekt]) -> Dict[str, Dict[str, Any]]:
        """
        Calculates completion progress (% of filled visible fields) per active block type,
        taking section and field visibility into account.
        """
        result = {}
        for typ in aktive_bausteine:
            schema = schema_loader.get_schema(typ)
            if not schema:
                result[typ] = {"titel": typ.capitalize(), "prozent": 0.0, "ausgefuellt": 0, "gesamt": 0}
                continue

            typ_objekte = [o for o in objekte if o.typ == typ]
            if not typ_objekte:
                result[typ] = {
                    "titel": schema.get("bezeichnung_anzeige", typ.capitalize()),
                    "prozent": 0.0,
                    "ausgefuellt": 0,
                    "gesamt": 0
                }
                continue

            total_fields = 0
            filled_count = 0

            for obj in typ_objekte:
                for abschnitt in schema.get("abschnitte", []):
                    if not _is_field_visible(abschnitt.get("sichtbar_wenn"), obj.daten):
                        continue
                    for feldef in abschnitt.get("felder", []):
                        if not _is_field_visible(feldef.get("sichtbar_wenn"), obj.daten):
                            continue
                        total_fields += 1
                        val = obj.daten.get(feldef.get("name"))
                        if val is not None and val != "" and val != "unbekannt" and val != "rueckfrage":
                            filled_count += 1

            pct = (filled_count / total_fields * 100.0) if total_fields > 0 else 100.0
            result[typ] = {
                "titel": schema.get("bezeichnung_anzeige", typ.capitalize()),
                "prozent": round(pct, 1),
                "ausgefuellt": filled_count,
                "gesamt": total_fields
            }

        return result

    def collect_offene_punkte(
        self,
        auftrag: Auftrag,
        standorte: List[Standort],
        objekte: List[TechnikObjekt],
        rule_open_points: List[OffenerPunktItem]
    ) -> List[OffenerPunktItem]:
        """
        Consolidates open points across order:
        - fehlende Standorte / komplett fehlende aktive Bausteine
        - "rueckfrage" fields
        - empty rule-relevant fields (only when field and section are visible)
        - manual object offene_punkte
        - undelivered document requests
        """
        consolidated: List[OffenerPunktItem] = []

        # 0. Strukturelle Lücken: kein Standort erfasst, oder aktive Bausteine ganz ohne Objekt
        if not standorte:
            consolidated.append(OffenerPunktItem(
                id="op-struktur-kein-standort",
                text="Standort fehlt — noch kein Standort erfasst",
                status="offen",
                quelle="struktur_fehlt",
                prioritaet="kritisch",
                ziel_url=f"/auftrag/{auftrag.id}/standort/neu"
            ))

        erfasste_typen = {o.typ for o in objekte}
        for typ in auftrag.aktive_bausteine:
            if typ in erfasste_typen:
                continue
            schema = schema_loader.get_schema(typ)
            label = schema.get("bezeichnung_anzeige", typ.capitalize()) if schema else typ.capitalize()
            consolidated.append(OffenerPunktItem(
                id=f"op-struktur-fehlt-{typ}",
                text=f"{label} fehlt — noch kein Objekt erfasst",
                status="offen",
                quelle="struktur_fehlt",
                prioritaet="kritisch",
                ziel_url=f"/auftrag/{auftrag.id}/objekt/neu?typ={typ}",
                objekt_typ=typ
            ))

        # Kernfelder mit kritischer Auswirkung bei Fehlen
        KRITISCHE_FELDER = {
            "wartungsvertrag_vorhanden", "wartungsvertrag_status", "strategie",
            "mfa_fuer_alle_benutzer", "mfa_fuer_administratoren",
            "notfallhandbuch_status", "it_dokumentation_status",
            "edr_antivirus_zentral_gemanagt", "ips_ids_aktiv",
            "unveraenderliches_backup", "testwiederherstellung",
            "zentrales_patchmanagement_aktiv", "lokale_adminrechte_eingeschraenkt",
            "gast_wlan_isoliert", "netztrennung"
        }

        # 1. Rueckfrage & Rule-relevant empty fields from objects
        for obj in objekte:
            schema = schema_loader.get_schema(obj.typ)
            if not schema:
                continue

            for abschnitt in schema.get("abschnitte", []):
                if not _is_field_visible(abschnitt.get("sichtbar_wenn"), obj.daten):
                    continue
                for feldef in abschnitt.get("felder", []):
                    if not _is_field_visible(feldef.get("sichtbar_wenn"), obj.daten):
                        continue
                    fname = feldef.get("name")
                    flabel = feldef.get("label", fname)
                    val = obj.daten.get(fname)

                    if val == "rueckfrage":
                        consolidated.append(OffenerPunktItem(
                            id=f"op-rf-{obj.id}-{fname}",
                            text=f"Rückfrage erforderlich bei '{flabel}' für Objekt '{obj.bezeichnung}'",
                            status="offen",
                            quelle="rueckfrage",
                            prioritaet="kritisch",
                            ziel_url=f"/auftrag/{auftrag.id}/objekt/{obj.typ}/{obj.id}#field_{fname}",
                            standort_id=obj.standort_id,
                            objekt_typ=obj.typ
                        ))
                    elif feldef.get("regelrelevant", False) and (val is None or val == "" or val == [] or val == "unbekannt"):
                        prio = "kritisch" if fname in KRITISCHE_FELDER else "wichtig"
                        consolidated.append(OffenerPunktItem(
                            id=f"op-rr-{obj.id}-{fname}",
                            text=f"Regelrelevantes Feld '{flabel}' ist unvollständig/unbekannt bei Objekt '{obj.bezeichnung}'",
                            status="offen",
                            quelle="regelrelevant_leer",
                            prioritaet=prio,
                            ziel_url=f"/auftrag/{auftrag.id}/objekt/{obj.typ}/{obj.id}#field_{fname}",
                            standort_id=obj.standort_id,
                            objekt_typ=obj.typ
                        ))

            # Manual open points from object
            for item in obj.offene_punkte:
                if not item.ziel_url:
                    item.ziel_url = f"/auftrag/{auftrag.id}/objekt/{obj.id}/bearbeiten"
                if not item.standort_id:
                    item.standort_id = obj.standort_id
                if not item.objekt_typ:
                    item.objekt_typ = obj.typ
                if not item.prioritaet:
                    item.prioritaet = "wichtig"
                consolidated.append(item)

        # 2. Open points from Rule Engine
        for r_item in rule_open_points:
            if not getattr(r_item, "prioritaet", None):
                r_item.prioritaet = "kritisch"
            consolidated.append(r_item)

        # 3. Document requests
        for doc in auftrag.dokumentenanforderung:
            if doc.status in ("angefordert", "offen"):
                consolidated.append(OffenerPunktItem(
                    id=f"op-doc-{doc.bezeichnung}",
                    text=f"Ausstehendes Dokument: '{doc.bezeichnung}' (Status: {doc.status})",
                    status="offen",
                    quelle="dokument",
                    prioritaet="wichtig",
                    ziel_url=f"/auftrag/{auftrag.id}/unterlagen"
                ))

        return consolidated

progress_service = ProgressService()
