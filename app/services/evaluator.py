from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple
from app.models.standort import Standort
from app.models.technik import TechnikObjekt
from app.models.bewertung import (
    KriteriumBewertung, KategorieBewertung, GesamtBewertung
)
from app.services.schema_loader import schema_loader
from app.utils.number_parser import parse_float_german

class EvaluatorService:
    def evaluate_auftrag(
        self,
        aktive_bausteine: List[str],
        objekte: List[TechnikObjekt],
        standorte: Optional[List[Standort]] = None
    ) -> GesamtBewertung:
        """
        Calculates category scores, overall score, coverage rate, worst location, and scale rating.
        Enforces worst-value principle across multiple objects of the same type per location.
        """
        categories_def = schema_loader.kategorien
        skala_def = schema_loader.skala

        # Map to store compiled criteria per (kategorie_id, kriterium_id)
        criterion_instances: Dict[Tuple[str, str], List[KriteriumBewertung]] = {}
        total_available_criteria = 0

        for typ in aktive_bausteine:
            schema = schema_loader.get_schema(typ)
            if not schema:
                continue

            typ_criteria_fields = []
            for abschnitt in schema.get("abschnitte", []):
                for feldef in abschnitt.get("felder", []):
                    if "bewertung" in feldef:
                        typ_criteria_fields.append(feldef)

            total_available_criteria += len(typ_criteria_fields)
            typ_objekte = [o for o in objekte if o.typ == typ]

            for feldef in typ_criteria_fields:
                bew_block = feldef["bewertung"]
                kat_id = bew_block.get("kategorie")
                krit_id = bew_block.get("kriterium")
                max_pts = float(bew_block.get("max_punkte", 0))
                fname = feldef.get("name")

                if not typ_objekte:
                    # Baustein aktiviert, aber kein Objekt dieses Typs erfasst.
                    # Bewusst als 0 Punkte gewertet (nicht ausgeschlossen): das ist eine
                    # echte Erfassungslücke bei einem aktivierten Baustein, kein einzelnes
                    # unbeantwortetes Feld. Getrennt vom Unrated-Feld-Fix zu betrachten.
                    kb = KriteriumBewertung(
                        field_name=fname,
                        kriterium_id=krit_id,
                        kategorie_id=kat_id,
                        max_punkte=max_pts,
                        erreichte_punkte=0.0,
                        wert=None,
                        objekt_id="",
                        objekt_bezeichnung=f"Kein {typ}-Objekt vorhanden",
                        objekt_typ=typ
                    )
                    key = (kat_id, krit_id)
                    criterion_instances.setdefault(key, []).append(kb)
                else:
                    for obj in typ_objekte:
                        val = obj.daten.get(fname)
                        pts = self._extract_points(val, feldef)
                        kb = KriteriumBewertung(
                            field_name=fname,
                            kriterium_id=krit_id,
                            kategorie_id=kat_id,
                            max_punkte=max_pts,
                            erreichte_punkte=pts,
                            wert=val,
                            objekt_id=obj.id,
                            objekt_bezeichnung=obj.bezeichnung,
                            objekt_typ=obj.typ
                        )
                        key = (kat_id, krit_id)
                        criterion_instances.setdefault(key, []).append(kb)

        # Calculate Baustein coverage
        erfasste_bausteine = set()
        for o in objekte:
            if o.typ in aktive_bausteine:
                erfasste_bausteine.add(o.typ)

        nicht_erfasste_bausteine = [b for b in aktive_bausteine if b not in erfasste_bausteine]
        bausteinabdeckung = (len(erfasste_bausteine) / len(aktive_bausteine) * 100.0) if aktive_bausteine else 100.0

        # Calculate location scores & locate worst location
        standort_scores: Dict[str, Tuple[float, float, float]] = {}
        standort_objekte: Dict[str, List[TechnikObjekt]] = {}
        for o in objekte:
            sto_key = o.standort_id or "default"
            standort_objekte.setdefault(sto_key, []).append(o)

        for sto_id, sto_objs in standort_objekte.items():
            sto_achieved = 0.0
            sto_max = 0.0
            for typ in aktive_bausteine:
                schema = schema_loader.get_schema(typ)
                if not schema:
                    continue
                sto_typ_objs = [o for o in sto_objs if o.typ == typ]
                if not sto_typ_objs:
                    continue
                for abschnitt in schema.get("abschnitte", []):
                    for feldef in abschnitt.get("felder", []):
                        if "bewertung" in feldef:
                            max_pts = float(feldef["bewertung"].get("max_punkte", 0))
                            rated_pts = [
                                p for p in (
                                    self._extract_points(o.daten.get(feldef["name"]), feldef)
                                    for o in sto_typ_objs
                                ) if p is not None
                            ]
                            if not rated_pts:
                                # Kein Objekt an diesem Standort hat dieses Feld beantwortet
                                # -> Kriterium fällt aus Zähler UND Nenner raus.
                                continue
                            sto_achieved += min(rated_pts)
                            sto_max += max_pts
            if sto_max > 0:
                pct = (sto_achieved / sto_max) * 100.0
                standort_scores[sto_id] = (sto_achieved, sto_max, pct)

        schlechtester_id = None
        schlechtester_bez = None
        schlechtester_pct = None
        if standort_scores:
            worst_sto_id = min(standort_scores.keys(), key=lambda k: standort_scores[k][2])
            schlechtester_id = worst_sto_id
            standort_map = {s.id: s.bezeichnung for s in standorte} if standorte else {}
            schlechtester_bez = standort_map.get(worst_sto_id, worst_sto_id)
            schlechtester_pct = round(standort_scores[worst_sto_id][2], 1)

        # Process categories
        kategorien_result: List[KategorieBewertung] = []
        tot_achieved = 0.0
        tot_max_rated = 0.0
        rated_criteria_count = 0

        for cat in categories_def:
            cat_id = cat["id"]
            cat_bezeichnung = cat["bezeichnung"]
            cat_reihenfolge = cat.get("reihenfolge", 1)

            cat_kriterien: List[KriteriumBewertung] = []
            cat_achieved = 0.0
            cat_max_rated = 0.0

            for (c_id, kr_id), inst_list in criterion_instances.items():
                if c_id != cat_id:
                    continue

                worst_kb = self._pick_worst_instance(inst_list)
                if worst_kb.ist_bewertet:
                    cat_kriterien.append(worst_kb)
                    rated_criteria_count += 1
                    cat_achieved += worst_kb.erreichte_punkte
                    cat_max_rated += worst_kb.max_punkte

            if not cat_kriterien or cat_max_rated == 0:
                continue

            cat_prozent = (cat_achieved / cat_max_rated * 100.0) if cat_max_rated > 0 else 0.0
            st_id, st_bez = self._lookup_skala(cat_prozent, skala_def)

            kategorien_result.append(KategorieBewertung(
                id=cat_id,
                bezeichnung=cat_bezeichnung,
                reihenfolge=cat_reihenfolge,
                erreichte_punkte=cat_achieved,
                max_punkte=cat_max_rated,
                prozent=round(cat_prozent, 1),
                stufe_id=st_id,
                stufe_bezeichnung=st_bez,
                kriterien=cat_kriterien
            ))

            tot_achieved += cat_achieved
            tot_max_rated += cat_max_rated

        gesamt_prozent = (tot_achieved / tot_max_rated * 100.0) if tot_max_rated > 0 else 0.0
        g_st_id, g_st_bez = self._lookup_skala(gesamt_prozent, skala_def)

        feldabdeckung = (rated_criteria_count / total_available_criteria * 100.0) if total_available_criteria > 0 else 0.0

        return GesamtBewertung(
            gesamt_prozent=round(gesamt_prozent, 1),
            gesamt_stufe_id=g_st_id,
            gesamt_stufe_bezeichnung=g_st_bez,
            erfassungsgrad_prozent=round(feldabdeckung, 1),
            erfassungsgrad_bewertet_anzahl=rated_criteria_count,
            erfassungsgrad_gesamt_anzahl=total_available_criteria,
            feldabdeckung_prozent=round(feldabdeckung, 1),
            bausteinabdeckung_prozent=round(bausteinabdeckung, 1),
            nicht_erfasste_bausteine=nicht_erfasste_bausteine,
            unter_50_prozent_warnung=(bausteinabdeckung < 100.0 or feldabdeckung < 50.0),
            schlechtester_standort_id=schlechtester_id,
            schlechtester_standort_bezeichnung=schlechtester_bez,
            schlechtester_standort_prozent=schlechtester_pct,
            kategorien=kategorien_result
        )

    def _extract_points(self, val: Any, feldef: Dict[str, Any]) -> Optional[float]:
        """
        Extracts points for a field value according to schema.

        Unerfasste Kriterien (val is None, empty, unbekannt, rueckfrage, nicht_relevant)
        geben None zurück -> fallen bei der Aggregation aus Zähler UND Nenner raus, damit
        Teil-Erfassungen fair bleiben (siehe Bugfix 2026-08: vorher zählten sie fälschlich
        als 0 Punkte und blieben im Nenner).
        Schema-abweichende Werte (ein Wert wurde erfasst, passt aber zu keiner Schema-Option)
        zählen weiterhin als 0.0 Punkte, da hier tatsächlich eine Antwort vorliegt.
        Supports threshold calculations for zahl and datum fields.
        """
        bew_block = feldef.get("bewertung", {})
        max_pts = float(bew_block.get("max_punkte", 0))

        if val is None or val == "" or val == "unbekannt" or val == "rueckfrage" or val == "nicht_relevant" or val == []:
            return None

        ftype = feldef.get("typ")

        # Choice and boolean fields
        if ftype in ("auswahl", "ja_nein", "ja_nein_unbekannt", "ja_nein_nicht_relevant") and "werte" in feldef:
            for w in feldef["werte"]:
                if str(w.get("wert")).lower() == str(val).lower():
                    pts = w.get("punkte")
                    return float(pts) if pts is not None else 0.0
            # Value not found in schema options -> schema-abweichender Wert
            return 0.0

        # Numeric fields (zahl)
        elif ftype == "zahl":
            val_num = parse_float_german(val, None)
            if val_num is None:
                return 0.0
            if "werte" in feldef:
                for w in feldef["werte"]:
                    op = w.get("operator", "gleich")
                    target = w.get("wert")
                    matched = False
                    if op == "groesser_gleich" and target is not None:
                        matched = val_num >= float(target)
                    elif op == "groesser" and target is not None:
                        matched = val_num > float(target)
                    elif op == "kleiner_gleich" and target is not None:
                        matched = val_num <= float(target)
                    elif op == "kleiner" and target is not None:
                        matched = val_num < float(target)
                    elif op == "gleich" and target is not None:
                        matched = val_num == float(target)
                    elif op == "bereich" and "min" in w and "max" in w:
                        matched = float(w["min"]) <= val_num <= float(w["max"])
                    if matched:
                        pts = w.get("punkte")
                        return float(pts) if pts is not None else 0.0
            return max_pts if val_num > 0 else 0.0

        # Date fields (datum)
        elif ftype == "datum":
            val_str = str(val).strip()
            try:
                dt = datetime.strptime(val_str, "%Y-%m-%d").date()
                today = date.today()
                days_diff = (dt - today).days
                age_years = (today - dt).days / 365.25
            except (ValueError, TypeError):
                return 0.0

            if "werte" in feldef:
                for w in feldef["werte"]:
                    op = w.get("operator", "datum_nach_heute")
                    target = w.get("wert")
                    matched = False
                    if op == "datum_vor_heute":
                        matched = dt < today
                    elif op == "datum_nach_heute":
                        matched = dt >= today
                    elif op == "alter_in_jahren_kleiner" and target is not None:
                        matched = age_years < float(target)
                    elif op == "alter_in_jahren_groesser" and target is not None:
                        matched = age_years > float(target)
                    elif op == "tage_kleiner" and target is not None:
                        matched = days_diff < float(target)
                    if matched:
                        pts = w.get("punkte")
                        return float(pts) if pts is not None else 0.0
            return max_pts if dt >= today else 0.0

        return 0.0

    def _pick_worst_instance(self, inst_list: List[KriteriumBewertung]) -> KriteriumBewertung:
        """
        Picks the instance with lowest achieved points for worst-value rule.

        Nur unter den tatsächlich bewerteten Instanzen wird das Minimum gesucht - eine
        unbeantwortete Instanz (erreichte_punkte is None) darf ein echt bewertetes,
        schlechtes Ergebnis nicht verdecken. Sind alle Instanzen unbeantwortet, bleibt das
        Kriterium unbeantwortet (wird bei der Aggregation ausgeschlossen).
        """
        if not inst_list:
            raise ValueError("inst_list cannot be empty")
        rated = [x for x in inst_list if x.erreichte_punkte is not None]
        if rated:
            return min(rated, key=lambda x: x.erreichte_punkte)
        return inst_list[0]

    def calculate_objekt_status(self, obj: TechnikObjekt) -> str:
        schema = schema_loader.get_schema(obj.typ)
        if not schema:
            return obj.erfassungsstatus

        required_and_rule_fields = []
        all_fields = []

        def _sichtbar(sichtbar_cond: Optional[Dict[str, Any]]) -> bool:
            if not sichtbar_cond:
                return True
            cond_field = sichtbar_cond.get("feld")
            cond_op = sichtbar_cond.get("operator", "gleich")
            cond_val = sichtbar_cond.get("wert")
            parent_val = obj.daten.get(cond_field)

            p_str = "ja" if parent_val is True or str(parent_val).lower() == "ja" else ("nein" if parent_val is False or str(parent_val).lower() in ("nein", "false") else str(parent_val).lower())
            c_str = "ja" if cond_val is True or str(cond_val).lower() == "ja" else ("nein" if cond_val is False or str(cond_val).lower() in ("nein", "false") else str(cond_val).lower())

            if cond_op == "gleich" and p_str != c_str:
                return False
            return True

        for abschnitt in schema.get("abschnitte", []):
            if not _sichtbar(abschnitt.get("sichtbar_wenn")):
                continue
            for field in abschnitt.get("felder", []):
                fname = field.get("name")
                all_fields.append(fname)

                if not _sichtbar(field.get("sichtbar_wenn")):
                    continue

                if field.get("pflicht") or field.get("regelrelevant"):
                    required_and_rule_fields.append(fname)

        def _is_filled(val: Any) -> bool:
            if val is None:
                return False
            if isinstance(val, (list, dict, tuple, set)) and len(val) == 0:
                return False
            if isinstance(val, str) and (val.strip() == "" or val in ("unbekannt", "rueckfrage")):
                return False
            return True

        filled_any = any(_is_filled(obj.daten.get(fn)) for fn in all_fields)
        if not filled_any:
            return "unbekannt"

        all_required_filled = all(
            _is_filled(obj.daten.get(fn)) for fn in required_and_rule_fields
        ) if required_and_rule_fields else filled_any

        if all_required_filled:
            return "vollständig"
        return "teilweise"

    def _lookup_skala(self, prozent: float, skala_def: List[Dict[str, Any]]) -> Tuple[str, str]:
        for st in skala_def:
            if prozent <= float(st.get("bis_prozent", 100)):
                return (st.get("id", "ausreichend"), st.get("bezeichnung", "Ausreichend"))
        return ("sehr_gut", "Sehr gut")

evaluator_service = EvaluatorService()
