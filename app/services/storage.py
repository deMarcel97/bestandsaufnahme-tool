from pathlib import Path
import copy
import shutil
import logging
from typing import List, Optional, Dict, Any
import yaml
from pydantic import ValidationError
from app.config import DATA_DIR
from app.models.auftrag import Auftrag
from app.models.standort import Standort
from app.models.technik import TechnikObjekt
from app.models.finding import Finding
from app.models.massnahme import Massnahme
from app.services.slug import generate_slug_id, is_valid_id

class StorageService:
    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

    # --- AUFTRAG ---
    def get_auftrag_dir(self, auftrag_id: str, create: bool = False) -> Optional[Path]:
        if not is_valid_id(auftrag_id):
            return None
        p = self.data_dir / auftrag_id
        if create:
            p.mkdir(parents=True, exist_ok=True)
        return p

    def save_auftrag(self, auftrag: Auftrag) -> Optional[str]:
        d = self.get_auftrag_dir(auftrag.id, create=True)
        if d is None:
            return None
        fpath = d / "auftrag.yaml"
        with open(fpath, "w", encoding="utf-8") as f:
            yaml.dump(auftrag.model_dump(), f, allow_unicode=True, sort_keys=False)
        return auftrag.id

    def load_auftrag(self, auftrag_id: str) -> Optional[Auftrag]:
        d = self.get_auftrag_dir(auftrag_id)
        if d is None:
            return None
        fpath = d / "auftrag.yaml"
        if not fpath.exists():
            return None
        with open(fpath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data:
            return None
        try:
            return Auftrag.model_validate(data)
        except ValidationError as e:
            logging.error(f"Skipping invalid Auftrag in {fpath}: {e}")
            return None

    @staticmethod
    def sortier_schluessel(text: str) -> str:
        """Sortierschlüssel für deutschsprachige Bezeichnungen.

        Ohne Aufbereitung sortiert Python nach Zeichencode: Großbuchstaben vor
        Kleinbuchstaben ('Zentrale' vor 'aachen') und Umlaute hinter 'z'
        ('Ärztehaus' hinter 'Zentrale'). Beides widerspricht dem, was jemand
        beim Blick auf eine Standortliste erwartet. casefold() vereinheitlicht
        die Groß-/Kleinschreibung (und bildet dabei 'ß' auf 'ss' ab), die
        Umlaut-Ersetzung sortiert 'ä/ö/ü' wie 'ae/oe/ue' ein — dieselbe
        Transliteration, die auch die IDs erzeugt (app/services/slug.py)."""
        text = (text or "").casefold()
        for umlaut, ersatz in (("ä", "ae"), ("ö", "oe"), ("ü", "ue")):
            text = text.replace(umlaut, ersatz)
        return text

    def list_auftraege(self) -> List[Auftrag]:
        auftraege = []
        for d in self.data_dir.iterdir():
            if d.is_dir() and (d / "auftrag.yaml").exists():
                a = self.load_auftrag(d.name)
                if a:
                    auftraege.append(a)
        # Nach Kunde, dann Bezeichnung: die Übersicht ist eine Kundenliste, und
        # die automatisch vergebenen Projektnummern ('PROJEKT-2', 'PROJEKT-10')
        # würden sich alphabetisch in der falschen Reihenfolge einsortieren.
        # Die id als letztes Kriterium hält die Reihenfolge auch dann stabil,
        # wenn zwei Aufträge Kunde und Bezeichnung teilen.
        auftraege.sort(key=lambda a: (self.sortier_schluessel(a.kunde),
                                      self.sortier_schluessel(a.bezeichnung),
                                      a.id))
        return auftraege

    def delete_auftrag(self, auftrag_id: str):
        d = self.get_auftrag_dir(auftrag_id)
        if d is not None and d.exists():
            shutil.rmtree(d)

    def projekt_nummer_existiert(self, projekt_nummer: str, exclude_id: Optional[str] = None) -> bool:
        pn = projekt_nummer.strip().lower()
        if not pn:
            return False
        return any(
            a.projekt_nummer.strip().lower() == pn
            for a in self.list_auftraege()
            if a.id != exclude_id
        )

    # --- STANDORT ---
    def save_standort(self, standort: Standort) -> Optional[str]:
        if not is_valid_id(standort.id):
            return None
        base = self.get_auftrag_dir(standort.auftrag_id, create=True)
        if base is None:
            return None
        d = base / "standorte"
        d.mkdir(parents=True, exist_ok=True)
        fpath = d / f"{standort.id}.yaml"
        with open(fpath, "w", encoding="utf-8") as f:
            yaml.dump(standort.model_dump(), f, allow_unicode=True, sort_keys=False)
        return standort.id

    def load_standort(self, auftrag_id: str, standort_id: str) -> Optional[Standort]:
        if not is_valid_id(standort_id):
            return None
        base = self.get_auftrag_dir(auftrag_id)
        if base is None:
            return None
        fpath = base / "standorte" / f"{standort_id}.yaml"
        if not fpath.exists():
            return None
        with open(fpath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data:
            return None
        try:
            return Standort.model_validate(data)
        except ValidationError as e:
            logging.error(f"Skipping invalid Standort in {fpath}: {e}")
            return None

    def list_standorte(self, auftrag_id: str) -> List[Standort]:
        base = self.get_auftrag_dir(auftrag_id)
        if base is None:
            return []
        d = base / "standorte"
        if not d.exists():
            return []
        standorte = []
        for fpath in sorted(d.glob("*.yaml")):
            with open(fpath, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if data:
                try:
                    standorte.append(Standort.model_validate(data))
                except ValidationError as e:
                    logging.error(f"Skipping invalid Standort in {fpath}: {e}")
        # Alphabetisch nach Bezeichnung — das ist die Spalte, die der Benutzer
        # in der Oberfläche sieht und nach der er sucht. Die id wäre technisch
        # naheliegender, ist aber nur der Slug der Bezeichnung zum Zeitpunkt
        # der Anlage: nach einer Umbenennung würde ein Standort dann an seiner
        # alten Stelle stehen bleiben. Sie dient hier nur als Tiebreak, damit
        # zwei gleich benannte Standorte nicht wieder zufällig springen.
        standorte.sort(key=lambda s: (self.sortier_schluessel(s.bezeichnung), s.id))
        return standorte

    def delete_standort(self, auftrag_id: str, standort_id: str):
        if not is_valid_id(standort_id):
            return
        base = self.get_auftrag_dir(auftrag_id)
        if base is None:
            return
        fpath = base / "standorte" / f"{standort_id}.yaml"
        if fpath.exists():
            fpath.unlink()

    # --- TECHNIK OBJEKT ---
    def save_objekt(self, obj: TechnikObjekt) -> Optional[str]:
        if not is_valid_id(obj.typ) or not is_valid_id(obj.id):
            return None
        base = self.get_auftrag_dir(obj.auftrag_id, create=True)
        if base is None:
            return None
        d = base / "objekte" / obj.typ
        d.mkdir(parents=True, exist_ok=True)
        fpath = d / f"{obj.id}.yaml"
        with open(fpath, "w", encoding="utf-8") as f:
            yaml.dump(obj.model_dump(), f, allow_unicode=True, sort_keys=False)
        return obj.id

    def load_objekt(self, auftrag_id: str, typ: str, objekt_id: str) -> Optional[TechnikObjekt]:
        if not is_valid_id(typ) or not is_valid_id(objekt_id):
            return None
        base = self.get_auftrag_dir(auftrag_id)
        if base is None:
            return None
        fpath = base / "objekte" / typ / f"{objekt_id}.yaml"
        if not fpath.exists():
            return None
        with open(fpath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data:
            return None
        try:
            return TechnikObjekt.model_validate(data)
        except ValidationError as e:
            logging.error(f"Skipping invalid TechnikObjekt in {fpath}: {e}")
            return None

    def list_objekte(self, auftrag_id: str, typ: Optional[str] = None) -> List[TechnikObjekt]:
        base = self.get_auftrag_dir(auftrag_id)
        if base is None:
            return []
        obj_dir = base / "objekte"
        if not obj_dir.exists():
            return []

        result = []
        if typ:
            if not is_valid_id(typ):
                return []
            target_dirs = [obj_dir / typ]
        else:
            target_dirs = [d for d in obj_dir.iterdir() if d.is_dir()]

        for d in sorted(target_dirs):
            if d.exists():
                for fpath in sorted(d.glob("*.yaml")):
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                    if data:
                        try:
                            result.append(TechnikObjekt.model_validate(data))
                        except ValidationError as e:
                            logging.error(f"Skipping invalid TechnikObjekt in {fpath}: {e}")
        # Erst nach Typ, dann nach Bezeichnung — genau die Reihenfolge der
        # beiden ersten Spalten der Objekttabelle je Standort. Dadurch stehen
        # gleichartige Objekte (alle Switches, alle Access Points) beieinander,
        # statt sich über die Tabelle zu verteilen.
        result.sort(key=lambda o: (o.typ,
                                   self.sortier_schluessel(o.bezeichnung),
                                   o.id))
        return result

    def delete_objekt(self, auftrag_id: str, typ: str, objekt_id: str):
        if not is_valid_id(typ) or not is_valid_id(objekt_id):
            return
        base = self.get_auftrag_dir(auftrag_id)
        if base is None:
            return
        fpath = base / "objekte" / typ / f"{objekt_id}.yaml"
        if fpath.exists():
            fpath.unlink()

    def duplicate_objekt(self, auftrag_id: str, typ: str, objekt_id: str) -> Optional[TechnikObjekt]:
        source = self.load_objekt(auftrag_id, typ, objekt_id)
        if not source:
            return None

        existing_ids = [o.id for o in self.list_objekte(auftrag_id)]
        new_bezeichnung = f"{source.bezeichnung} (Kopie)"
        new_id = generate_slug_id(typ, new_bezeichnung, existing_ids)

        copy_obj = TechnikObjekt(
            schema_version=source.schema_version,
            id=new_id,
            typ=source.typ,
            bezeichnung=new_bezeichnung,
            auftrag_id=source.auftrag_id,
            standort_id=source.standort_id,
            betreut_durch=source.betreut_durch,
            dienstleister_name=source.dienstleister_name,
            notiz=source.notiz,
            vertraulichkeit=source.vertraulichkeit,
            erfassungsstatus=source.erfassungsstatus,
            offene_punkte=[],  # Cleared on duplication
            daten=copy.deepcopy(source.daten)
        )
        self.save_objekt(copy_obj)
        return copy_obj

    def resolve_objekt_referenz(self, auftrag_id: str, objekt_id: str, ziel_typen: List[str]) -> Optional[TechnikObjekt]:
        """Löst einen 'objekt_referenz'-Wert auf. Der gespeicherte Wert ist nur eine id,
        ohne Typ-Information - daher werden alle erlaubten Zieltypen durchprobiert.
        Gibt None zurück statt zu crashen, falls das Zielobjekt inzwischen gelöscht wurde."""
        if not objekt_id:
            return None
        for zt in ziel_typen:
            obj = self.load_objekt(auftrag_id, zt, objekt_id)
            if obj:
                return obj
        return None

    # --- FINDINGS ---
    def save_findings(self, auftrag_id: str, findings: List[Finding]):
        d = self.get_auftrag_dir(auftrag_id, create=True)
        if d is None:
            return
        fpath = d / "findings.yaml"
        data = [f.model_dump() for f in findings]
        with open(fpath, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)

    def list_findings(self, auftrag_id: str) -> List[Finding]:
        d = self.get_auftrag_dir(auftrag_id)
        if d is None:
            return []
        fpath = d / "findings.yaml"
        if not fpath.exists():
            return []
        with open(fpath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data or not isinstance(data, list):
            return []
        valid_findings = []
        for item in data:
            try:
                valid_findings.append(Finding.model_validate(item))
            except Exception as e:
                logging.error(f"Skipping invalid Finding item in {fpath}: {e}")
        return valid_findings

    # --- MASSNAHMEN ---
    def save_massnahmen(self, auftrag_id: str, massnahmen: List[Massnahme]):
        d = self.get_auftrag_dir(auftrag_id, create=True)
        if d is None:
            return
        fpath = d / "massnahmen.yaml"
        data = [m.model_dump() for m in massnahmen]
        with open(fpath, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)

    def list_massnahmen(self, auftrag_id: str) -> List[Massnahme]:
        d = self.get_auftrag_dir(auftrag_id)
        if d is None:
            return []
        fpath = d / "massnahmen.yaml"
        if not fpath.exists():
            return []
        with open(fpath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data or not isinstance(data, list):
            return []
        return [Massnahme.model_validate(item) for item in data]

storage = StorageService()
