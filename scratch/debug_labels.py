import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.schema_loader import schema_loader
from app.web.routes_auftrag import get_bausteine_labels

for typ in schema_loader.get_all_types():
    s = schema_loader.get_schema(typ)
    print(f"Type: {typ:<25} | Label: {s.get('bezeichnung_anzeige', 'N/A')}")
