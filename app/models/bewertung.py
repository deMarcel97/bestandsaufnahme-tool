from typing import List, Optional, Any
from pydantic import BaseModel, Field

class KriteriumBewertung(BaseModel):
    field_name: str
    kriterium_id: str
    kategorie_id: str
    max_punkte: float
    erreichte_punkte: Optional[float] = None  # None if unrated/unbekannt/rueckfrage
    wert: Any = None
    objekt_id: str = ""
    objekt_bezeichnung: str = ""
    objekt_typ: str = ""

    @property
    def ist_bewertet(self) -> bool:
        return self.erreichte_punkte is not None

class KategorieBewertung(BaseModel):
    id: str
    bezeichnung: str
    reihenfolge: int = 1
    erreichte_punkte: float = 0.0
    max_punkte: float = 0.0
    prozent: float = 0.0
    stufe_id: str = "ausreichend"
    stufe_bezeichnung: str = "Ausreichend"
    kriterien: List[KriteriumBewertung] = Field(default_factory=list)

class GesamtBewertung(BaseModel):
    gesamt_prozent: float = 0.0
    gesamt_stufe_id: str = "ausreichend"
    gesamt_stufe_bezeichnung: str = "Ausreichend"
    erfassungsgrad_prozent: float = 0.0
    erfassungsgrad_bewertet_anzahl: int = 0
    erfassungsgrad_gesamt_anzahl: int = 0
    feldabdeckung_prozent: float = 0.0
    bausteinabdeckung_prozent: float = 0.0
    nicht_erfasste_bausteine: List[str] = Field(default_factory=list)
    unter_50_prozent_warnung: bool = False
    schlechtester_standort_id: Optional[str] = None
    schlechtester_standort_bezeichnung: Optional[str] = None
    schlechtester_standort_prozent: Optional[float] = None
    kategorien: List[KategorieBewertung] = Field(default_factory=list)
