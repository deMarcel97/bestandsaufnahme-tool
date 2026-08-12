import sys
import html
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

client = httpx.Client(base_url="http://127.0.0.1:8000")
resp = client.get("/auftrag/auf-test")
raw_html = resp.text
unescaped_html = html.unescape(raw_html)

print("--- TESTING LABELS IN UNESCAPED HTML ---")
labels = [
    "Server & Virtualisierung",
    "Switch / Aktive Netzwerktechnik",
    "Backup & Storage",
    "USV (Unterbrechungsfreie Stromversorgung)",
    "Clients & Arbeitsplätze",
    "Microsoft 365 & Security"
]

for l in labels:
    in_raw = l in raw_html
    in_unescaped = l in unescaped_html
    print(f"Label '{l:<45}': in_raw={in_raw}, in_unescaped={in_unescaped}")

print("\n--- SEARCHING FOR SHORT/ALTERNATIVE LABELS ---")
short_terms = ["Server", "Switch", "Backup", "USV", "Client", "M365", "Firewall"]
for s in short_terms:
    print(f"Term '{s}': in_raw={s in raw_html}")
