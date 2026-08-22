"""Lizenzwissen für Microsoft 365 (Karte #407).

Beantwortet die Frage „deckt die Lizenzierung dieses Kunden Feature X ab?"
aus `rules/m365_lizenzmatrix.json`. Vorher stand die Antwort als
handgepflegte Planliste in jeder einzelnen Regel (`wert: [bp, me3, me5, …]`)
— bei 41 Features über 15 Pläne wäre das über achtzig Listen, die nach jedem
Microsoft-Repackaging alle einzeln nachgezogen werden müssten.

Der Unterschied, an dem es hängt: nur das „Microsoft 365"-Bundle bringt EMS
(Intune, Entra ID P1/P2) mit, das gleichnamige „Office 365"-Bundle nicht.
Wer beide gleich behandelt, meldet einem Office-365-E3-Kunden Conditional
Access als vorhanden — ein Befund, der im Kundengespräch nicht standhält.
"""
import json
from typing import Any, Dict, List, Optional

from app.config import RULES_DIR

MATRIX_DATEI = RULES_DIR / "m365_lizenzmatrix.json"


class M365Lizenzmatrix:
    def __init__(self, pfad=MATRIX_DATEI):
        self.pfad = pfad
        self.meta: Dict[str, Any] = {}
        # (lizenzcode, feature_id) -> Matrixzeile
        self._zeilen: Dict[tuple, Dict[str, Any]] = {}
        self._feature_ids: set = set()
        self.laden()

    def laden(self):
        self._zeilen.clear()
        self._feature_ids.clear()
        if not self.pfad.exists():
            return
        with open(self.pfad, "r", encoding="utf-8") as f:
            daten = json.load(f)
        self.meta = daten.get("meta", {})
        for zeile in daten.get("matrix", []):
            code = zeile.get("lizenzcode")
            fid = zeile.get("feature_id")
            if not code or not fid:
                continue
            self._zeilen[(code, fid)] = zeile
            self._feature_ids.add(fid)

    def feature_ids(self) -> set:
        """Alle bekannten Feature-IDs — Grundlage der Regelprüfung beim Laden."""
        return set(self._feature_ids)

    def get_feature_status(self, lizenzplan: str, feature_id: str) -> Optional[Dict[str, Any]]:
        """Matrixzeile für genau einen Plan (SKU-Kürzel wie `bp`, `oe3`).

        `None`, wenn die Kombination nicht in der Matrix steht — etwa weil ein
        Standalone-Plan das Feature gar nicht führt.
        """
        if feature_id not in self._feature_ids:
            raise KeyError(
                f"Unbekannte feature_id '{feature_id}' — bekannt sind "
                f"{len(self._feature_ids)} Features aus {self.pfad.name}"
            )
        return self._zeilen.get((str(lizenzplan).lower(), feature_id))

    def deckt_feature(self, lizenzen: List[str], feature_id: str) -> bool:
        """Deckt mindestens eine der erfassten SKUs das Feature ab?

        Ein Tenant trägt oft mehrere SKUs (Business Basic plus Entra ID P1 als
        Standalone). Es genügt, wenn eine davon das Feature mitbringt.

        `Add-on` zählt bewusst **nicht** als abgedeckt: es ist innerhalb des
        Plans zubuchbar, aber erst nach Kauf vorhanden. Als „vorhanden" gewertet
        würde daraus ein Fehlkonfigurations-Befund für etwas, das der Kunde
        schlicht nicht besitzt.
        """
        for code in lizenzen or []:
            zeile = self.get_feature_status(code, feature_id)
            if zeile and zeile.get("enthalten") == "Ja":
                return True
        return False


m365_lizenzmatrix = M365Lizenzmatrix()
