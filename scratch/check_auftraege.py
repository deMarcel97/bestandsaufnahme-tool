import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.storage import storage

auftraege = storage.list_auftraege()
print("Auftraege in storage:")
for a in auftraege:
    print(f"  ID: {a.id}, Kunde: {a.kunde}, Bez: {a.bezeichnung}")
