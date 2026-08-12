from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SCHEMAS_DIR = BASE_DIR / "schemas"
RULES_DIR = BASE_DIR / "rules"
BEWERTUNG_DIR = BASE_DIR / "bewertung"

# Ensure data dir exists
DATA_DIR.mkdir(parents=True, exist_ok=True)
