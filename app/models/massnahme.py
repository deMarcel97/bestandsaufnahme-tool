from typing import List
from pydantic import BaseModel, Field

class Massnahme(BaseModel):
    schema_version: int = 1
    id: str
    bezeichnung: str = ""
    beschreibung: str = ""
    findings: List[str] = Field(default_factory=list)
    stufe: int = 2  # 1, 2, 3
    investitionskosten: float = 0.0
    monatliche_kosten: float = 0.0
    zeitaufwand: float = 0.0
    zeitaufwand_einheit: str = "Stunden"  # Stunden, Tage
    prioritaet: str = "mittel"  # hoch, mittel, niedrig
    status: str = "vorgeschlagen"  # vorgeschlagen, im Angebot, beauftragt, verworfen
    kosten_quelle: str = "offen"  # regelwerk, manuell, offen
    bemerkung: str = ""
