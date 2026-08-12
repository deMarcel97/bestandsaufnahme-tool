import re

ID_RE = re.compile(r'^[a-z0-9]+([_-][a-z0-9]+)*$')

def is_valid_id(value: str) -> bool:
    """Prüft, ob value ein sicheres Pfad-Segment ist: nur Kleinbuchstaben, Ziffern,
    Bindestrich oder Unterstrich als Trenner. Deckt sowohl von generate_slug_id
    erzeugte IDs (kebab-case) als auch feste Objekttypen (snake_case, z.B.
    'server_virtualisierung') ab. Lehnt '.', '..', '/' und alle
    Pfad-Traversal-Versuche ab, da diese nicht diesem Format entsprechen."""
    return bool(value) and bool(ID_RE.fullmatch(value))

def slugify(text: str) -> str:
    """Converts a given text into a clean URL/filename-friendly slug."""
    if not text:
        return "unbenannt"
    
    text = text.lower()
    # Transliterate German umlauts
    text = text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    # Replace non-alphanumeric characters with hyphen
    text = re.sub(r'[^a-z0-9]+', '-', text)
    # Strip leading/trailing hyphens
    text = text.strip('-')
    return text if text else "unbenannt"

PREFIX_MAP = {
    "auftrag": "auf",
    "standort": "sto",
    "firewall": "fw",
    "finding": "fin",
    "massnahme": "mas"
}

def generate_slug_id(typ: str, bezeichnung: str, existing_ids: list[str]) -> str:
    """Generates a stable slug ID with prefix and collision handling."""
    prefix = PREFIX_MAP.get(typ.lower(), typ[:3].lower())
    base_slug = slugify(bezeichnung)
    candidate = f"{prefix}-{base_slug}"
    
    if candidate not in existing_ids:
        return candidate
    
    counter = 1
    while f"{candidate}-{counter:02d}" in existing_ids:
        counter += 1
    return f"{candidate}-{counter:02d}"
