from pathlib import Path
from typing import Dict, Any, List, Optional
import yaml
from app.config import SCHEMAS_DIR, BEWERTUNG_DIR

ALLOWED_FIELD_TYPES = {
    "text", "mehrzeiliger_text", "zahl", "datum",
    "ja_nein", "ja_nein_unbekannt", "ja_nein_nicht_relevant", "auswahl", "mehrfachauswahl"
}

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
        
        self.kategorien = self.load_kategorien()
        self.skala = self.load_skala()

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
                fname = feldef.get("name")
                ftype = feldef.get("typ")
                if ftype not in ALLOWED_FIELD_TYPES:
                    raise SchemaValidationError(
                        f"Unbekannter Felddatentyp '{ftype}' in Feld '{fname}' ({file_path.name})"
                    )
                
                # Check select values
                if ftype == "auswahl" and "werte" in feldef:
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
        return data

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
