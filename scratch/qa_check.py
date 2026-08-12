import sys
import html
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import time
import httpx
import uvicorn
import threading
from app.main import app
from app.services.schema_loader import schema_loader
from app.services.storage import storage

# Check if port 8000 is open. If not, start uvicorn server in background thread.
BASE_URL = "http://127.0.0.1:8000"

def try_server():
    try:
        r = httpx.get(f"{BASE_URL}/auftrag", timeout=1.0)
        return True
    except Exception:
        return False

if not try_server():
    def start_server():
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    time.sleep(1.5)

client = httpx.Client(base_url=BASE_URL, follow_redirects=False)

print("=========================================================")
print(" BROWSER & UI INSPECTOR QUALITY ASSURANCE (QA) CHECK")
print("=========================================================")

# 1. VERIFY ALL REQUIRED ROUTES RETURN EXPECTED STATUS CODES
routes_to_test = [
    ("/auftrag", 200),
    ("/auftrag/auf-test", 200),
    ("/auftrag/auf-test/findings", 200),
    ("/auftrag/auf-test/massnahmen", 200),
    ("/auftrag/auf-test/bewertung", 200),
    ("/auftrag/auf-test/export", 200),
    ("/auftrag/auf-test/offene_punkte", 200),
    ("/auftrag/auf-test/einstellungen", 200),
    ("/static/css/style.css", 200),
    ("/static/js/dialog.js", 200)
]

print("\n--- 1. Testing Route HTTP Status Codes ---")
route_results = {}
for route, expected_status in routes_to_test:
    resp = client.get(route)
    status_match = resp.status_code == expected_status
    print(f"[{'PASS' if status_match else 'FAIL'}] GET {route:<30} -> HTTP {resp.status_code} (Expected {expected_status}, Length: {len(resp.text)} bytes)")
    assert status_match, f"Route {route} failed: expected {expected_status}, got {resp.status_code}"
    route_results[route] = (resp.status_code, len(resp.text))

# 2. VERIFY HTML ASSETS & COMPONENTS RENDERING
print("\n--- 2. Testing HTML & UI Components Rendering ---")
resp_detail = client.get("/auftrag/auf-test")
raw_html_detail = resp_detail.text
html_detail = html.unescape(raw_html_detail)

# Check CSS
css_in_html = "/static/css/style.css" in raw_html_detail
print(f"[{'PASS' if css_in_html else 'FAIL'}] CSS Link (/static/css/style.css) present in HTML")
assert css_in_html, "CSS Link missing in HTML"

# Check Sidebar partial rendering
sidebar_in_html = 'class="sidebar"' in raw_html_detail and "Aktive Bausteine" in html_detail
print(f"[{'PASS' if sidebar_in_html else 'FAIL'}] Sidebar partial (_sidebar.html) rendered correctly")
assert sidebar_in_html, "Sidebar partial missing or invalid"

# Check JS Dialogs
resp_js = client.get("/static/js/dialog.js")
dialog_js_ok = resp_js.status_code == 200 and len(resp_js.text) > 0
print(f"[{'PASS' if dialog_js_ok else 'FAIL'}] Dialog JS (/static/js/dialog.js) loads successfully ({len(resp_js.text)} bytes)")
assert dialog_js_ok, "Dialog JS missing or empty"

# 3. VERIFY BUILDING BLOCKS LABELS IN UI
print("\n--- 3. Testing 7 Building Blocks UI Display ---")

labels_to_check = [
    ("server_virtualisierung", "Server & Virtualisierung"),
    ("switch", "Switch / Aktive Netzwerktechnik"),
    ("backup_storage", "Backup & Storage"),
    ("usv", "USV (Unterbrechungsfreie Stromversorgung)"),
    ("clients", "Clients & Arbeitsplätze"),
    ("m365_security", "Microsoft 365 & Security"),
    ("firewall", "Firewall")
]

for typ, label in labels_to_check:
    present = label in html_detail
    print(f"[{'PASS' if present else 'FAIL'}] Building block '{typ}' label '{label}' rendered in UI")
    assert present, f"Building block label '{label}' not found in detail HTML"

# 4. TEST CREATING AND EDITING TECH OBJECTS FOR ALL BUILDING BLOCKS
print("\n--- 4. Testing Tech Object Creation & Editing (HTTP 200 / 303) ---")

standorte = storage.list_standorte("auf-test")
assert standorte, "No standort found for auf-test"
standort_id = standorte[0].id

building_blocks_to_test = [
    ("server_virtualisierung", "Server & Virtualisierung"),
    ("switch", "Switches & Netzwerk"),
    ("backup_storage", "Backup & Storage"),
    ("usv", "USV Stromversorgung"),
    ("clients", "Clients"),
    ("m365_security", "M365 Security")
]

for typ, label in building_blocks_to_test:
    # A. GET Creation Form
    form_url = f"/auftrag/auf-test/objekt/neu?typ={typ}&standort_id={standort_id}"
    resp_form = client.get(form_url)
    form_ok = resp_form.status_code == 200
    print(f"[{'PASS' if form_ok else 'FAIL'}] GET Form for {label} ({typ}) -> HTTP {resp_form.status_code}")
    assert form_ok, f"GET creation form failed for {typ}"

    # B. POST Create Tech Object (Include ?typ= in URL)
    bezeichnung = f"QA TestObjekt {typ}"
    post_data = {
        "typ": typ,
        "standort_id": standort_id,
        "bezeichnung": bezeichnung,
        "betreut_durch": "QA Inspector Team",
        "vertraulichkeit": "intern",
        "erfassungsstatus": "vollstaendig"
    }
    post_url = f"/auftrag/auf-test/objekt/neu?typ={typ}"
    resp_post = client.post(post_url, data=post_data)
    post_ok = resp_post.status_code == 303
    print(f"[{'PASS' if post_ok else 'FAIL'}] POST Create Object '{bezeichnung}' -> HTTP {resp_post.status_code}")
    assert post_ok, f"POST creation failed for {typ}: expected 303, got {resp_post.status_code}"

    # C. Follow Redirect & Verify Object in List/Detail
    redirect_loc = resp_post.headers.get("location")
    resp_redirect = client.get(redirect_loc)
    redirect_ok = resp_redirect.status_code == 200
    print(f"[{'PASS' if redirect_ok else 'FAIL'}] Follow redirect ({redirect_loc}) -> HTTP {resp_redirect.status_code}")
    assert redirect_ok, f"Redirect failed for {typ}"

    # D. GET Edit Form for newly created object
    objekte = storage.list_objekte("auf-test", typ=typ)
    created_obj = next((o for o in objekte if o.bezeichnung == bezeichnung), None)
    assert created_obj, f"Created object {bezeichnung} of typ {typ} not found in storage"
    
    edit_url = f"/auftrag/auf-test/objekt/{typ}/{created_obj.id}"
    resp_edit_get = client.get(edit_url)
    edit_get_ok = resp_edit_get.status_code == 200
    print(f"[{'PASS' if edit_get_ok else 'FAIL'}] GET Edit Form for object {created_obj.id} -> HTTP {resp_edit_get.status_code}")
    assert edit_get_ok, f"GET edit form failed for object {created_obj.id}"

    # E. POST Edit Tech Object
    post_edit_data = {
        "typ": typ,
        "standort_id": standort_id,
        "bezeichnung": f"{bezeichnung} Updated",
        "betreut_durch": "QA Inspector Team (Updated)",
        "vertraulichkeit": "intern",
        "erfassungsstatus": "vollstaendig"
    }
    resp_edit_post = client.post(edit_url, data=post_edit_data)
    edit_post_ok = resp_edit_post.status_code == 303
    print(f"[{'PASS' if edit_post_ok else 'FAIL'}] POST Edit Object '{created_obj.id}' -> HTTP {resp_edit_post.status_code}")
    assert edit_post_ok, f"POST edit failed for object {created_obj.id}"

print("\n=========================================================")
print(" ALL QA TESTS PASSED SUCCESSFULLY!")
print("=========================================================")
