from pathlib import Path
from typing import Dict, Any, List, Optional
import yaml
from app.config import SCHEMAS_DIR, BEWERTUNG_DIR

ALLOWED_FIELD_TYPES = {
    "text", "mehrzeiliger_text", "zahl", "datum",
    "ja_nein", "ja_nein_unbekannt", "ja_nein_nicht_relevant", "auswahl", "mehrfachauswahl",
    "liste", "objekt_referenz"
}

# Felder innerhalb einer 'liste' dürfen nicht selbst 'liste' oder 'objekt_referenz' sein
# (keine Verschachtelung/Objekt-Referenzen in wiederholbaren Zeilen in dieser Iteration).
LISTE_ITEM_ALLOWED_TYPES = ALLOWED_FIELD_TYPES - {"liste", "objekt_referenz"}

class SchemaValidationError(Exception):
    pass

class SchemaLoader:
    def __init__(self, schemas_dir: Path = SCHEMAS_DIR, bewertung_dir: Path = BEWERTUNG_DIR):
        self.schemas_dir = schemas_dir
        self.bewertung_dir = bewertung_dir
        self.schemas: Dict[str, Dict[str, Any]] = {}
        self.kategorien: List[Dict[str, Any]] = []
        self.skala: List[Dict[str, Any]] = []
        self.load_all()

    def load_all(self):
        self.schemas.clear()
        if self.schemas_dir.exists():
            for p in self.schemas_dir.glob("*.yaml"):
                schema = self.load_schema_file(p)
                if schema and "typ" in schema:
                    self.schemas[schema["typ"]] = schema

        self._validate_cross_references()
        self.kategorien = self.load_kategorien()
        self.skala = self.load_skala()

    def _validate_feldef(self, feldef: Dict[str, Any], file_path: Path, allow_container: bool = True):
        fname = feldef.get("name")
        ftype = feldef.get("typ")
        allowed = ALLOWED_FIELD_TYPES if allow_container else LISTE_ITEM_ALLOWED_TYPES
        if ftype not in allowed:
            raise SchemaValidationError(
                f"Unbekannter oder an dieser Stelle unzulässiger Felddatentyp '{ftype}' in Feld '{fname}' ({file_path.name})"
            )

        # Check select values
        if ftype in ("auswahl", "mehrfachauswahl") and "werte" in feldef:
            for w in feldef["werte"]:
                if not isinstance(w, dict) or "wert" not in w:
                    raise SchemaValidationError(
                        f"Auswahlwert in Feld '{fname}' muss ein Objekt mit 'wert' sein"
                    )

        # Check bewertung block
        if "bewertung" in feldef:
            bew = feldef["bewertung"]
            if not isinstance(bew, dict) or "max_punkte" not in bew or "kategorie" not in bew:
                raise SchemaValidationError(
                    f"Bewertungsblock in Feld '{fname}' muss 'max_punkte' und 'kategorie' enthalten"
                )

        if ftype == "liste":
            sub_felder = feldef.get("felder")
            if not isinstance(sub_felder, list) or not sub_felder:
                raise SchemaValidationError(
                    f"Feld '{fname}' vom Typ 'liste' benötigt eine nicht-leere 'felder'-Liste ({file_path.name})"
                )
            for sub in sub_felder:
                self._validate_feldef(sub, file_path, allow_container=False)

        if ftype == "objekt_referenz":
            ziel_typen = feldef.get("ziel_typen")
            if not isinstance(ziel_typen, list) or not ziel_typen or not all(isinstance(t, str) for t in ziel_typen):
                raise SchemaValidationError(
                    f"Feld '{fname}' vom Typ 'objekt_referenz' benötigt eine nicht-leere Liste 'ziel_typen' ({file_path.name})"
                )

    def load_schema_file(self, file_path: Path) -> Dict[str, Any]:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise SchemaValidationError(f"Ungültiges Schema in {file_path.name}")

        if "typ" not in data or "abschnitte" not in data:
            raise SchemaValidationError(f"Schema {file_path.name} muss 'typ' und 'abschnitte' enthalten")

        # Validate sections and fields
        for abschnitt in data.get("abschnitte", []):
            for feldef in abschnitt.get("felder", []):
                self._validate_feldef(feldef, file_path)
        return data

    def _validate_cross_references(self):
        """Muss erst laufen, wenn alle Schemas geladen sind (objekt_referenz.ziel_typen
        kann auf ein Schema verweisen, das erst später alphabetisch geladen wird)."""
        for typ, schema in self.schemas.items():
            for abschnitt in schema.get("abschnitte", []):
                for feldef in abschnitt.get("felder", []):
                    if feldef.get("typ") == "objekt_referenz":
                        for zt in feldef.get("ziel_typen", []):
                            if zt not in self.schemas:
                                raise SchemaValidationError(
                                    f"Feld '{feldef.get('name')}' in Schema '{typ}' referenziert unbekannten Zieltyp '{zt}'"
                                )

    def load_kategorien(self) -> List[Dict[str, Any]]:
        kat_file = self.bewertung_dir / "kategorien.yaml"
        if not kat_file.exists():
            return []
        with open(kat_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        kats = data.get("kategorien", [])
        return sorted(kats, key=lambda x: x.get("reihenfolge", 99))

    def load_skala(self) -> List[Dict[str, Any]]:
        skala_file = self.bewertung_dir / "skala.yaml"
        if not skala_file.exists():
            skala_file = BEWERTUNG_DIR / "skala.yaml"
        if not skala_file.exists():
            raise FileNotFoundError(f"Kritischer Fehler: Bewertungsskala '{skala_file}' nicht gefunden. App-Start abgebrochen.")
        with open(skala_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        stufen = data.get("stufen", [])
        if not stufen:
            raise SchemaValidationError(f"Kritischer Fehler: Keine Stufen in Bewertungsskala '{skala_file}' definiert.")
        return sorted(stufen, key=lambda x: x.get("bis_prozent", 100))

    def get_schema(self, typ: str) -> Optional[Dict[str, Any]]:
        return self.schemas.get(typ)

    def get_all_types(self) -> List[str]:
        return list(self.schemas.keys())

schema_loader = SchemaLoader()
