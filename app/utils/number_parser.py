from typing import Optional

def parse_float_german(val: Optional[str], default: float = 0.0) -> float:
    if val is None:
        return default
    s = str(val).strip().replace(",", ".")
    if not s:
        return default
    try:
        return float(s)
    except (ValueError, TypeError):
        return default

def parse_int_german(val: Optional[str], default: int = 0) -> int:
    if val is None:
        return default
    s = str(val).strip().replace(",", ".")
    if not s:
        return default
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return default
