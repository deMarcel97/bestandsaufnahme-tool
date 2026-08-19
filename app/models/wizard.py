from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


# Schritt-Typen für den Wizard
WIZARD_STEP_TYPES = [
    "auftragsgrunddaten",
    "standort_grunddaten",
    "internetanbindungen",
    "firewall",
    "switch",
    "access_point",
    "server_virtualisierung",
    "storage",
    "backup",
    "usv",
    "clients",
    "m365_security",
    "organisation_prozesse",
    "zusammenfassung",
]

# Label für die Schritte
WIZARD_STEP_LABELS = {
    "auftragsgrunddaten": "Auftragsdaten",
    "standort_grunddaten": "Standort",
    "internetanbindungen": "Internet",
    "firewall": "Firewall",
    "switch": "Switch",
    "access_point": "WLAN / AP",
    "server_virtualisierung": "Server / Virtualisierung",
    "storage": "Storage / NAS",
    "backup": "Backup",
    "usv": "USV",
    "clients": "Clients / PCs",
    "m365_security": "M365 / Cloud",
    "organisation_prozesse": "Organisation & Notfall",
    "zusammenfassung": "Zusammenfassung",
}


class WizardStepData(BaseModel):
    """Daten für einen einzelnen Schritt im Wizard."""
    step_type: str
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = ""
    completed: bool = False
    skipped: bool = False


class WizardProgress(BaseModel):
    """Fortschritt des Erfassungs-Wizards für einen Auftrag."""
    schema_version: int = 1
    auftrag_id: str
    current_step: int = 1
    completed_steps: List[int] = Field(default_factory=list)
    skipped_steps: List[int] = Field(default_factory=list)
    steps: Dict[int, WizardStepData] = Field(default_factory=dict)
    started_at: str = ""
    last_updated: str = ""
    version: int = 1

    def get_current_step_data(self) -> Optional[WizardStepData]:
        return self.steps.get(self.current_step)

    def is_step_completed(self, step: int) -> bool:
        return step in self.completed_steps and step not in self.skipped_steps

    def is_step_skipped(self, step: int) -> bool:
        return step in self.skipped_steps

    def is_complete(self) -> bool:
        """Prüft, ob alle Datenerfassungs-Schritte abgeschlossen sind."""
        return self.current_step >= len(WIZARD_STEP_TYPES)

    def get_next_step(self) -> Optional[int]:
        """Gibt die nächste Schritt-Nummer zurück oder None, wenn fertig."""
        if self.is_complete():
            return None
        return self.current_step + 1

    def get_step_label(self, step: int) -> str:
        """Gibt das Label für einen Schritt zurück."""
        if 1 <= step <= len(WIZARD_STEP_TYPES):
            return WIZARD_STEP_LABELS.get(WIZARD_STEP_TYPES[step - 1], f"Schritt {step}")
        return f"Schritt {step}"


def create_empty_wizard_progress(auftrag_id: str) -> WizardProgress:
    """Erstellt einen neuen, leeren Wizard-Fortschritt."""
    now = datetime.now().isoformat()
    return WizardProgress(
        auftrag_id=auftrag_id,
        started_at=now,
        last_updated=now,
    )
