from typing import Optional
from pydantic import BaseModel, model_validator

class Finding(BaseModel):
    schema_version: int = 1
    id: str
    auftrag_id: str
    standort_id: Optional[str] = None
    objekt_id: Optional[str] = None
    quelle: str = "manuell"  # regel_id oder "manuell"
    schweregrad: str = "mittel"  # hoch, mittel, niedrig, empfehlung
    befund: str = ""
    risiko: str = ""
    empfehlung: str = ""
    referenz: str = ""
    status: str = "offen"  # offen, bestaetigt, verworfen, kunde_akzeptiert, behoben
    begruendung: str = ""
    aufwand_schaetzung: str = ""
    massnahme_id: Optional[str] = None
    erzeugt_am: str = ""
    behoben_am: Optional[str] = None

    @model_validator(mode="after")
    def validate_begruendung(self):
        if self.status in ("verworfen", "kunde_akzeptiert") and not self.begruendung.strip():
            raise ValueError(f"Bei Status '{self.status}' ist eine Begründung zwingend erforderlich.")
        return self
