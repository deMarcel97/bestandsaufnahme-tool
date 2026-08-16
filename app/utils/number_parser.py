import re
from typing import Any, Optional


def parse_float_german(val: Any, default: Optional[float] = 0.0) -> Optional[float]:
    """Parst eine Zahl im deutschen oder internationalen Format zu float.

    Unterstützt:
    - Deutsche Formate: "1.249,90", "1249,90", "1.000.000,50", "1.249", "1.000", "100,5", "-5,25"
    - Internationale Formate: "1,249.90", "1249.90", "1.5", "0.75"
    - Ganze Zahlen und Strings mit Leerzeichen: " 1 249,90 ", "42"
    - Ungültige Werte / leere Strings fallen auf `default` zurück.
    """
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)

    s = str(val).strip().replace("'", "").replace(" ", "").replace("\xa0", "").replace("\u202f", "")
    if not s:
        return default

    # Vorzeichen abspalten
    sign = ""
    if s.startswith(("-", "+")):
        sign = s[0]
        s = s[1:]

    if not s:
        return default

    has_dot = "." in s
    has_comma = "," in s

    if has_dot and has_comma:
        # Sowohl Punkt als auch Komma vorhanden
        last_dot = s.rfind(".")
        last_comma = s.rfind(",")
        if last_comma > last_dot:
            # Deutsches Format: 1.249,90 -> Punkte entfernen, Komma zu Punkt
            s = s.replace(".", "").replace(",", ".")
        else:
            # Englisches Format: 1,249.90 -> Kommas entfernen
            s = s.replace(",", "")
    elif has_comma:
        # Nur Komma vorhanden
        if re.match(r"^[1-9]\d{0,2}(,\d{3})+$", s):
            s = s.replace(",", "")
        else:
            s = s.replace(",", ".")
    elif has_dot:
        # Nur Punkt vorhanden
        # Tausenderpunkte: "1.000.000", "1.000", "10.000", "1.249"
        # Dezimalpunkt: "1.5", "1.25", "1249.90", "0.123", "1249.500"
        if re.match(r"^[1-9]\d{0,2}(\.\d{3})+$", s):
            s = s.replace(".", "")

    try:
        return float(sign + s)
    except (ValueError, TypeError):
        return default


def parse_int_german(val: Any, default: Optional[int] = 0) -> Optional[int]:
    """Parst eine Ganzzahl im deutschen oder internationalen Format zu int."""
    f = parse_float_german(val, default=None)
    if f is None:
        return default
    return int(f)
