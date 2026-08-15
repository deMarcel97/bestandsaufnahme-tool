"""
One-off cleanup for stray QA-Check test objects left behind in real data
by earlier runs of scratch/qa_check.py (before it cleaned up after itself).

Removes any TechnikObjekt whose 'betreut_durch' field starts with
"QA Inspector Team" from the given Auftrag (default: auf-test).

Usage: python scratch/cleanup_qa_testdata.py [auftrag_id]
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.storage import storage

auftrag_id = sys.argv[1] if len(sys.argv) > 1 else "auf-test"

objekte = storage.list_objekte(auftrag_id)
removed = [o for o in objekte if o.betreut_durch.startswith("QA Inspector Team")]

for o in removed:
    storage.delete_objekt(auftrag_id, o.typ, o.id)
    print(f"Removed {o.typ}/{o.id} ({o.bezeichnung!r}, betreut_durch={o.betreut_durch!r})")

print(f"\nCleaned up {len(removed)} stray QA test object(s) from '{auftrag_id}'.")
