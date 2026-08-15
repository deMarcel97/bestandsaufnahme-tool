from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

class Internetanbindung(BaseModel):
    anbieter: str = ""
    art: str = "DSL"  # DSL, Kabel, Glasfaser_FTTH, Standleitung, Ethernet, Richtfunk, LTE_5G, Starlink, Sonstiges
    bandbreite_down_mbit: float = 0.0
    bandbreite_up_mbit: float = 0.0
    symmetrisch: str = "nein"  # ja / nein
    feste_ip: str = "nein"  # ja / nein
    ip_adressen: str = ""  # vertraulichkeit: intern
    subnetzmaske: str = ""  # vertraulichkeit: intern
    sla_entstoerzeit: float = 0.0  # Stunden
    ist_backup_leitung: str = "nein"  # ja / nein
    failover_verfahren: str = ""

    @field_validator("sla_entstoerzeit", mode="before")
    @classmethod
    def _coerce_legacy_sla_entstoerzeit(cls, v):
        """Ältere Daten speicherten hier Freitext (z.B. '' oder '4h rund um die Uhr').
        Nicht parsbare Werte werden statt eines harten Fehlers auf 0.0 gesetzt."""
        if v is None or v == "":
            return 0.0
        try:
            return float(str(v).replace(",", "."))
        except ValueError:
            return 0.0

class Standort(BaseModel):
    schema_version: int = 1
    version: int = 1  # Konflikterkennung, siehe Auftrag.version
    id: str
    auftrag_id: str
    bezeichnung: str = ""
    strasse: str = ""
    plz: str = ""
    ort: str = ""
    anzahl_user: int = 0
    funktion: str = ""
    ansprechpartner_vor_ort: str = ""
    vertraulichkeit: str = "kundentauglich"  # intern, kundentauglich, anonymisiert
    begehung_am: Optional[str] = None
    redaktionskonzept_backup_leitung: str = "automatische_umschaltung"
    trassenfuehrung_getrennt: str = "ja"
    usv_fuer_netzwerktechnik: str = ""
    anbindungen: List[Internetanbindung] = Field(default_factory=list)
    notiz: str = ""
