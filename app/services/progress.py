from typing import List, Dict, Any
from app.models.auftrag import Auftrag
from app.models.standort import Standort
from app.models.technik import TechnikObjekt, OffenerPunktItem
from app.services.schema_loader import schema_loader

class ProgressService:
    def calculate_progress(self, aktive_bausteine: List[str], objekte: List[TechnikObjekt]) -> Dict[str, Dict[str, Any]]:
        """
        Calculates completion progress (% of filled mandatory fields) per active block type.
        """
        result = {}
        for typ in aktive_bausteine:
            schema = schema_loader.get_schema(typ)
            if not schema:
                result[typ] = {"titel": typ.capitalize(), "prozent": 0.0, "ausgefuellt": 0, "gesamt": 0}
                continue

            # Identify mandatory fields
            mandatory_fields = []
            for abschnitt in schema.get("abschnitte", []):
                for feldef in abschnitt.get("felder", []):
                    if feldef.get("pflicht", False):
                        mandatory_fields.append(feldef.get("name"))

            typ_objekte = [o for o in objekte if o.typ == typ]
            if not typ_objekte or not mandatory_fields:
                result[typ] = {
                    "titel": schema.get("bezeichnung_anzeige", typ.capitalize()),
                    "prozent": 100.0 if typ_objekte else 0.0,
                    "ausgefuellt": 0,
                    "gesamt": len(mandatory_fields) * max(1, len(typ_objekte))
                }
                continue

            total_mand = len(mandatory_fields) * len(typ_objekte)
            filled_count = 0

            for obj in typ_objekte:
                for fname in mandatory_fields:
                    val = obj.daten.get(fname)
                    if val is not None and val != "" and val != "unbekannt" and val != "rueckfrage":
                        filled_count += 1

            pct = (filled_count / total_mand * 100.0) if total_mand > 0 else 0.0
            result[typ] = {
                "titel": schema.get("bezeichnung_anzeige", typ.capitalize()),
                "prozent": round(pct, 1),
                "ausgefuellt": filled_count,
                "gesamt": total_mand
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
        - empty rule-relevant fields
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
                text=f"{label} fehlt — noch kein Gerät erfasst",
                status="offen",
                quelle="struktur_fehlt",
                ziel_url=f"/auftrag/{auftrag.id}/objekt/neu?typ={typ}"
            ))

        # 1. Rueckfrage & Rule-relevant empty fields from objects
        for obj in objekte:
            schema = schema_loader.get_schema(obj.typ)
            if not schema:
                continue

            for abschnitt in schema.get("abschnitte", []):
                for feldef in abschnitt.get("felder", []):
                    fname = feldef.get("name")
                    flabel = feldef.get("label", fname)
                    val = obj.daten.get(fname)

                    if val == "rueckfrage":
                        consolidated.append(OffenerPunktItem(
                            id=f"op-rf-{obj.id}-{fname}",
                            text=f"Rückfrage erforderlich bei '{flabel}' für Gerät '{obj.bezeichnung}'",
                            status="offen",
                            quelle="rueckfrage",
                            ziel_url=f"/auftrag/{auftrag.id}/objekt/{obj.typ}/{obj.id}#field_{fname}"
                        ))
                    elif feldef.get("regelrelevant", False) and (val is None or val == "" or val == "unbekannt"):
                        consolidated.append(OffenerPunktItem(
                            id=f"op-rr-{obj.id}-{fname}",
                            text=f"Regelrelevantes Feld '{flabel}' ist unvollständig/unbekannt bei Gerät '{obj.bezeichnung}'",
                            status="offen",
                            quelle="regelrelevant_leer",
                            ziel_url=f"/auftrag/{auftrag.id}/objekt/{obj.typ}/{obj.id}#field_{fname}"
                        ))

            # Manual open points from object
            for item in obj.offene_punkte:
                if not item.ziel_url:
                    item.ziel_url = f"/auftrag/{auftrag.id}/objekt/{obj.id}/bearbeiten"
                consolidated.append(item)

        # 2. Open points from Rule Engine
        consolidated.extend(rule_open_points)

        # 3. Document requests
        for doc in auftrag.dokumentenanforderung:
            if doc.status in ("angefordert", "offen"):
                consolidated.append(OffenerPunktItem(
                    id=f"op-doc-{doc.bezeichnung}",
                    text=f"Ausstehendes Dokument: '{doc.bezeichnung}' (Status: {doc.status})",
                    status="offen",
                    quelle="dokument",
                    ziel_url=f"/auftrag/{auftrag.id}/einstellungen"
                ))

        return consolidated

progress_service = ProgressService()
