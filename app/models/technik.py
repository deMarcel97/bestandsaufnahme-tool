from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class OffenerPunktItem(BaseModel):
    id: str = ""
    text: str = ""
    status: str = "offen"  # offen, erledigt
    quelle: str = "manuell"  # manuell, rueckfrage, regelrelevant_leer, dokument
    ziel_url: str = ""
    standort_id: str = ""
    objekt_typ: str = ""

class TechnikObjekt(BaseModel):
    schema_version: int = 1
    id: str
    typ: str
    bezeichnung: str = ""
    auftrag_id: str
    standort_id: str
    betreut_durch: str = "Kunde"  # wir, Kunde, Dritter
    dienstleister_name: str = ""
    notiz: str = ""
    vertraulichkeit: str = "intern"  # intern, kundentauglich, anonymisiert
    erfassungsstatus: str = "unbekannt"  # vollstaendig, teilweise, unbekannt
    offene_punkte: List[OffenerPunktItem] = Field(default_factory=list)
    daten: Dict[str, Any] = Field(default_factory=dict)
