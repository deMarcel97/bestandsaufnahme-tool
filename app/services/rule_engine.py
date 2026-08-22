from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import yaml
from app.config import RULES_DIR
from app.models.technik import TechnikObjekt, OffenerPunktItem
from app.models.standort import Standort
from app.models.finding import Finding
from app.services.schema_loader import schema_loader
from app.services.m365_lizenzmatrix import m365_lizenzmatrix

class RuleValidationError(Exception):
    pass

class ConditionEvaluator:
    @staticmethod
    def evaluate_condition(cond: Dict[str, Any], data_dict: Dict[str, Any]) -> Tuple[bool, bool]:
        """
        Evaluates a condition tree.
        Returns (is_satisfied, contains_missing_info).
        If a field is missing, empty, "unbekannt", or "rueckfrage", condition is NOT satisfied (is_satisfied=False),
        and contains_missing_info=True.
        """
        if "alle" in cond:
            is_all_true = True
            missing_info = False
            for sub in cond["alle"]:
                sat, miss = ConditionEvaluator.evaluate_condition(sub, data_dict)
                if miss:
                    missing_info = True
                if not sat:
                    is_all_true = False
            return (is_all_true and not missing_info, missing_info)

        elif "eines" in cond:
            any_satisfied = False
            has_missing = False
            for sub in cond["eines"]:
                sat, miss = ConditionEvaluator.evaluate_condition(sub, data_dict)
                if sat:
                    any_satisfied = True
                if miss:
                    has_missing = True
            
            if any_satisfied:
                return (True, False)
            elif has_missing:
                return (False, True)
            else:
                return (False, False)

        else:
            # Single condition node
            field_name = cond.get("feld")
            operator = cond.get("operator")
            expected = cond.get("wert")

            val = data_dict.get(field_name)

            # Rule Section 8.2: missing, empty, "unbekannt", "rueckfrage"
            # val == [] covers untouched mehrfachauswahl fields (routes_objekt.py
            # stores form_data.getlist() unconditionally, never None for these).
            if val is None or val == "" or val == [] or val == "unbekannt" or val == "rueckfrage":
                return (False, True)

            # Compare operators
            sat = ConditionEvaluator._evaluate_op(val, operator, expected)
            return (sat, False)

    @staticmethod
    def _evaluate_op(val: Any, operator: str, expected: Any) -> bool:
        if isinstance(val, (list, tuple)):
            val_strs = [str(x).lower() for x in val]
            # Lizenzabdeckung steht nicht in der Regel, sondern in der
            # M365-Lizenzmatrix: `wert` ist eine feature_id, keine Planliste.
            if operator == "lizenz_deckt":
                return m365_lizenzmatrix.deckt_feature(val_strs, str(expected))
            elif operator == "lizenz_deckt_nicht":
                return not m365_lizenzmatrix.deckt_feature(val_strs, str(expected))
            elif operator == "in_liste" or operator == "enthaelt":
                if isinstance(expected, (list, tuple)):
                    return any(str(e).lower() in val_strs for e in expected)
                return str(expected).lower() in val_strs
            elif operator == "nicht_in_liste" or operator == "enthaelt_nicht":
                if isinstance(expected, (list, tuple)):
                    return not any(str(e).lower() in val_strs for e in expected)
                return str(expected).lower() not in val_strs
            elif operator == "gleich":
                return str(expected).lower() in val_strs
            elif operator == "ungleich":
                return str(expected).lower() not in val_strs
            elif operator == "ist_leer":
                return len(val) == 0
            elif operator == "ist_nicht_leer":
                return len(val) > 0
            return False

        if operator == "gleich":
            return str(val).lower() == str(expected).lower()
        elif operator == "ungleich":
            return str(val).lower() != str(expected).lower()
        elif operator == "groesser":
            try:
                return float(val) > float(expected)
            except (ValueError, TypeError):
                return False
        elif operator == "kleiner":
            try:
                return float(val) < float(expected)
            except (ValueError, TypeError):
                return False
        elif operator == "ist_leer":
            return val is None or val == ""
        elif operator == "ist_nicht_leer":
            return val is not None and val != ""
        elif operator == "datum_vor_heute":
            try:
                dt = datetime.strptime(str(val), "%Y-%m-%d").date()
                return dt < date.today()
            except (ValueError, TypeError):
                return False
        elif operator == "datum_in_tagen_kleiner":
            try:
                dt = datetime.strptime(str(val), "%Y-%m-%d").date()
                diff_days = (dt - date.today()).days
                return diff_days < float(expected)
            except (ValueError, TypeError):
                return False
        elif operator == "in_liste":
            if isinstance(expected, list):
                return val in expected
            return str(val) in str(expected).split(",")
        elif operator == "nicht_in_liste":
            if isinstance(expected, list):
                return val not in expected
            return str(val) not in str(expected).split(",")
        return False

class RuleEngine:
    def __init__(self, rules_dir: Path = RULES_DIR):
        self.rules_dir = rules_dir
        self.rules: List[Dict[str, Any]] = []
        self.load_rules()

    def load_rules(self):
        self.rules.clear()
        if self.rules_dir.exists():
            for fpath in self.rules_dir.glob("*.yaml"):
                with open(fpath, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                rule_list = data.get("regeln", [])
                for r in rule_list:
                    self.validate_rule(r, fpath.name)
                    self.rules.append(r)

    def validate_rule(self, rule: Dict[str, Any], filename: str):
        gilt_fuer = rule.get("gilt_fuer")
        rule_id = rule.get("id")

        # Die Lizenz-Operatoren zeigen auf die Matrix statt auf das Schema.
        # Ein Tippfehler in der feature_id bliebe sonst unsichtbar: die Regel
        # wuerde nie zutreffen und damit still ein Finding verschlucken.
        for feature_id in self._extract_lizenz_features(rule.get("bedingung", {})):
            if feature_id not in m365_lizenzmatrix.feature_ids():
                raise RuleValidationError(
                    f"Regel '{rule_id}' in {filename} verweist auf unbekannte "
                    f"feature_id '{feature_id}' in der M365-Lizenzmatrix"
                )

        # If rule applies to a tech object, verify field exists in schema
        if gilt_fuer and gilt_fuer != "standort":
            schema = schema_loader.get_schema(gilt_fuer)
            if schema:
                all_fields = set()
                for abschnitt in schema.get("abschnitte", []):
                    for feldef in abschnitt.get("felder", []):
                        all_fields.add(feldef.get("name"))
                
                # Extract fields from condition tree
                cond_fields = self._extract_fields(rule.get("bedingung", {}))
                for f in cond_fields:
                    if f not in all_fields and f != "anzahl_anbindungen":
                        raise RuleValidationError(
                            f"Regel '{rule_id}' in {filename} verweist auf unbekanntes Feld '{f}' in Schema '{gilt_fuer}'"
                        )

    def _extract_fields(self, cond: Dict[str, Any]) -> List[str]:
        fields = []
        if "alle" in cond:
            for sub in cond["alle"]:
                fields.extend(self._extract_fields(sub))
        elif "eines" in cond:
            for sub in cond["eines"]:
                fields.extend(self._extract_fields(sub))
        elif "feld" in cond:
            fields.append(cond["feld"])
        return fields

    def _extract_lizenz_features(self, cond: Dict[str, Any]) -> List[str]:
        """feature_ids, die eine Regel ueber die Lizenz-Operatoren anspricht."""
        features = []
        if "alle" in cond:
            for sub in cond["alle"]:
                features.extend(self._extract_lizenz_features(sub))
        elif "eines" in cond:
            for sub in cond["eines"]:
                features.extend(self._extract_lizenz_features(sub))
        elif cond.get("operator") in ("lizenz_deckt", "lizenz_deckt_nicht"):
            features.append(str(cond.get("wert")))
        return features

    def evaluate_all(
        self,
        auftrag_id: str,
        standorte: List[Standort],
        objekte: List[TechnikObjekt],
        existing_findings: List[Finding]
    ) -> Tuple[List[Finding], List[OffenerPunktItem]]:
        """
        Evaluates all rules against standorte and objekte.
        Returns (updated_findings, generated_open_points).
        """
        findings_map: Dict[str, Finding] = {f.id: f for f in existing_findings}
        new_open_points: List[OffenerPunktItem] = []
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 1. Evaluate Standort rules
        for sto in standorte:
            has_backup = any(getattr(a, "ist_backup_leitung", "nein") == "ja" for a in sto.anbindungen)
            arten_list = [getattr(a, "art", "") for a in sto.anbindungen if getattr(a, "art", "")]
            has_identical_art = len(arten_list) > 1 and len(set(arten_list)) < len(arten_list)

            sto_data = {
                "anzahl_anbindungen": len(sto.anbindungen),
                "hat_backup_leitung": "ja" if has_backup else "nein",
                "hat_gleiche_anbindungsart": "ja" if has_identical_art else "nein",
                "bezeichnung": sto.bezeichnung,
                "redaktionskonzept_backup_leitung": getattr(sto, "redaktionskonzept_backup_leitung", "automatische_umschaltung"),
                "trassenfuehrung_getrennt": getattr(sto, "trassenfuehrung_getrennt", "ja"),
                "usv_fuer_netzwerktechnik": getattr(sto, "usv_fuer_netzwerktechnik", ""),
            }
            sto_rules = [r for r in self.rules if r.get("gilt_fuer") == "standort"]
            for r in sto_rules:
                fid = f"{r['id']}-{sto.id}"
                satisfied, miss = ConditionEvaluator.evaluate_condition(r.get("bedingung", {}), sto_data)
                
                if miss:
                    new_open_points.append(OffenerPunktItem(
                        id=f"op-{fid}",
                        text=f"Offener Punkt für Regel '{r['befund']}' an Standort '{sto.bezeichnung}': Unvollständige Angaben.",
                        status="offen",
                        quelle="regelrelevant_leer",
                        ziel_url=f"/auftrag/{auftrag_id}/standort/{sto.id}/bearbeiten",
                        standort_id=sto.id
                    ))

                self._apply_rule_result(fid, r, satisfied, miss, auftrag_id, sto.id, None, findings_map, now_str)

        # 2. Evaluate Technik-Objekt rules
        for obj in objekte:
            obj_rules = [r for r in self.rules if r.get("gilt_fuer") == obj.typ]
            for r in obj_rules:
                fid = f"{r['id']}-{obj.id}"
                satisfied, miss = ConditionEvaluator.evaluate_condition(r.get("bedingung", {}), obj.daten)

                if miss:
                    c_fields = self._extract_fields(r.get("bedingung", {}))
                    f_anchor = f"#field_{c_fields[0]}" if c_fields else ""
                    new_open_points.append(OffenerPunktItem(
                        id=f"op-{fid}",
                        text=f"Offener Punkt für Regel '{r['befund']}' bei Objekt '{obj.bezeichnung}': Unvollständige Angaben.",
                        status="offen",
                        quelle="regelrelevant_leer",
                        ziel_url=f"/auftrag/{auftrag_id}/objekt/{obj.typ}/{obj.id}{f_anchor}",
                        standort_id=obj.standort_id,
                        objekt_typ=obj.typ
                    ))

                self._apply_rule_result(fid, r, satisfied, miss, auftrag_id, obj.standort_id, obj.id, findings_map, now_str)

        return list(findings_map.values()), new_open_points

    def _apply_rule_result(
        self,
        fid: str,
        rule: Dict[str, Any],
        satisfied: bool,
        missing: bool,
        auftrag_id: str,
        standort_id: str,
        objekt_id: Optional[str],
        findings_map: Dict[str, Finding],
        now_str: str
    ):
        existing = findings_map.get(fid)

        if satisfied:
            if existing:
                # Re-activate finding if previously behoben or keep user status
                if existing.status == "behoben":
                    existing.status = "offen"
                    existing.behoben_am = None
            else:
                # Create new finding
                new_f = Finding(
                    schema_version=1,
                    id=fid,
                    auftrag_id=auftrag_id,
                    standort_id=standort_id,
                    objekt_id=objekt_id,
                    quelle=rule.get("id", "manuell"),
                    schweregrad=rule.get("schweregrad", "mittel"),
                    befund=rule.get("befund", ""),
                    risiko=rule.get("risiko", ""),
                    empfehlung=rule.get("empfehlung", ""),
                    referenz=rule.get("referenz", ""),
                    status="offen",
                    erzeugt_am=now_str
                )
                findings_map[fid] = new_f
        else:
            # Rule does NOT trigger
            if existing:
                if missing:
                    # Item 1.10: Field is missing/unbekannt/rueckfrage. Do NOT resolve finding if existing!
                    pass
                else:
                    # Item 1.9: Only 'offen' findings are marked as 'behoben'
                    if existing.status == "offen":
                        existing.status = "behoben"
                        existing.behoben_am = now_str
                    elif existing.status in ("bestaetigt", "verworfen", "kunde_akzeptiert", "uebernommen"):
                        # User status stays unchanged; append hint note if not already present
                        hint = " [Hinweis: Regel greift laut aktuellen Daten nicht mehr]"
                        current_beg = existing.begruendung or ""
                        if hint not in current_beg:
                            existing.begruendung = (current_beg + hint).strip()

rule_engine = RuleEngine()
