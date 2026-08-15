import subprocess
import json
import time

def move_all_to_done():
    cmd = [
        "npx", "-y", "mcp-remote@latest",
        "https://api.superthread.com/mcp/app",
        "--header",
        "Authorization: Bearer stp-cda685a27a55057acc6f916117317a80.FXOR5T34yHvtD37MmdY5yTO95_q_1CASdFwZIN98gShMDE8lK8HaI7C8_8e6mfQm"
    ]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def send(req):
        p.stdin.write(json.dumps(req) + "\n")
        p.stdin.flush()

    def read_res():
        while True:
            line = p.stdout.readline()
            if not line:
                return None
            line = line.strip()
            if not line:
                continue
            try:
                return json.loads(line)
            except Exception:
                continue

    req_id = 1
    send({"jsonrpc": "2.0", "id": req_id, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "client", "version": "1.0"}}})
    read_res()
    send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def call_tool(tool_name, args):
        nonlocal req_id
        req_id += 1
        print(f"Calling tool: {tool_name} with args {args}")
        send({"jsonrpc": "2.0", "id": req_id, "method": "tools/call", "params": {"name": tool_name, "arguments": args}})
        res = read_res()
        print(f"Result: {json.dumps(res)[:160]}...")
        return res

    cards_to_update = [
        {
            "id": "281",
            "title": "QA-Testdaten bereinigen",
            "loesungsweg": "Lösungsweg:\nIn Test-Auftragsdaten (z. B. auf-test) tauchten historische 'QA Inspector Team'-Einträge in der Betreut-durch-Spalte auf, die nicht regulär erzeugt wurden.",
            "loesung": "Lösung:\nTestdaten-Bereinigung durchgeführt. Unberechtigte QA-Inspector-Team-Objekte entfernt. Verifiziert mit automatisierter Testsuite."
        },
        {
            "id": "283",
            "title": "Auftragsstatus & Vertraulichkeit editierbar machen",
            "loesungsweg": "Lösungsweg:\nIn Auftragsübersicht (list.html) und Detailansicht (detail.html) fehlte die Möglichkeit, die Vertraulichkeitsstufe (intern, kundentauglich, anonymisiert) direkt per Schnellzugriff-Dropdown zu ändern und zu persistieren.",
            "loesung": "Lösung:\nNeue POST-Route /auftrag/{auftrag_id}/vertraulichkeit in app/web/routes_auftrag.py ergänzt. Dropdowns in list.html und detail.html eingebunden. Persistierung und Weiterleitung erfolgreich getestet."
        },
        {
            "id": "284",
            "title": "Empfehlung bei Stammdaten-Änderung",
            "loesungsweg": "Lösungsweg:\nBestimmte organisatorische Stammdaten (wie 24/7-Geschäftszeiten oder fehlende IT-Abteilung) erfordern im Assessment-Prozess automatische Empfehlungen für den Kundenbericht.",
            "loesung": "Lösung:\nClientseitige Hinweisfunktion (toggleEmpfehlungen) im Stammdatenformular edit.html integriert. Properties empfehlung_rufbereitschaft (bei 24/7) und empfehlung_it_dienstleister (bei IT=nein) im Unternehmenskontext-Modell (app/models/auftrag.py) implementiert."
        },
        {
            "id": "286",
            "title": "Trennung Stammdaten & Kontext",
            "loesungsweg": "Lösungsweg:\nIm Formular edit.html waren allgemeine Stammdaten, Auftragssteuerung und Unternehmenskontext visuell vermischt.",
            "loesung": "Lösung:\nSaubere Aufteilung im Template edit.html in separate Fieldsets: 1. Stammdaten, 2. Auftragssteuerung, 3. Unternehmenskontext. Datenmodell bleibt kompatibel."
        },
        {
            "id": "287",
            "title": "Offene Punkte nach Hardware/Baustein strukturieren",
            "loesungsweg": "Lösungsweg:\nOffene Punkte wurden bisher rein nach Standort aufgelistet, was bei vielen Bausteinen unübersichtlich war.",
            "loesung": "Lösung:\nIn app/web/routes_offene_punkte.py Gruppierung erweitert: Offene Punkte werden nun standortbezogen und zusätzlich nach Baustein-Typ (Firewall, Switch, Server etc.) strukturiert aufgelistet."
        },
        {
            "id": "295",
            "title": "Ampelfarben Standortübersicht",
            "loesungsweg": "Lösungsweg:\nIn app/static/css/style.css und den Standort-Templates waren Status-Farben teilweise inkonsistent.",
            "loesung": "Lösung:\nAmpelfarben in style.css angepasst: Vollständig = grün (--ok), Teilweise = gelb/orange (--warn), Noch nicht erfasst/Unbekannt = grau (--muted)."
        },
        {
            "id": "296",
            "title": "Server-Detailfragen ergänzen",
            "loesungsweg": "Lösungsweg:\nIm Schema server_virtualisierung.yaml fehlten standardisierte Felder für die Höheneinheit/Rack-Position und das exakte Anschaffungs-/Baujahr.",
            "loesung": "Lösung:\nFelder standort_rack (Standort/Rack inkl. Höheneinheit) und baujahr (Baujahr / Anschaffungsjahr) in schemas/server_virtualisierung.yaml ergänzt."
        },
        {
            "id": "297",
            "title": "Server & Virtualisierung: Wird virtualisiert als Pflichtfeld",
            "loesungsweg": "Lösungsweg:\nBei der Server-Erfassung musste zunächst geklärt werden, ob es sich um Bare Metal oder Virtualisierung handelt. Hypervisor-spezifische Fragen sollten nur bei Virtualisierung erscheinen.",
            "loesung": "Lösung:\nwird_virtualisiert als Pflichtfeld (typ: ja_nein) ganz oben im Schema platziert. Alle Hypervisor-, VM- und Cluster-Felder mit bedingter Sichtbarkeit (sichtbar_wenn: wird_virtualisiert == ja) versehen. Rules angepasst."
        },
        {
            "id": "298",
            "title": "Feld Festplatten-Slots",
            "loesungsweg": "Lösungsweg:\nBei Backup-Storage und Servern fehlte eine strukturierte Mehrfacherfassung von Festplatten inklusive moderner Anbindungstypen wie M.2 NVMe.",
            "loesung": "Lösung:\nfestplatten_slots als liste-Typ in schemas/backup_storage.yaml ergänzt und in beiden Schemas um den Anbindungstyp m2 erweitert."
        },
        {
            "id": "299",
            "title": "Feld Kommentar ans Formularende",
            "loesungsweg": "Lösungsweg:\nDas Kommentarfeld war in verschiedenen Schemas unterschiedlich platziert (teils mittendrin oder abschnittsbezogen als hardware_kommentar).",
            "loesung": "Lösung:\nÜber alle 13 Schemas (schemas/*.yaml) hinweg das Kommentarfeld einheitlich als letztes Feld in den jeweils letzten Abschnitt verschoben."
        }
    ]

    for card in cards_to_update:
        cid = card["id"]
        print(f"\n--- Processing Card #{cid}: {card['title']} ---")
        # 1. Add Kommentar 1: Lösungsweg
        call_tool("comment_create", {"task_id": cid, "content": card["loesungsweg"]})
        time.sleep(0.3)
        # 2. Add Kommentar 2: Lösung
        call_tool("comment_create", {"task_id": cid, "content": card["loesung"]})
        time.sleep(0.3)
        # 3. Move to Done (list_id 84)
        call_tool("task_update", {"task_id": cid, "list_id": "84"})
        time.sleep(0.3)

    # Refresh board data
    print("\n=== Refreshing Superthread Board Data ===")
    board_info = call_tool("board_get", {"board_id": "15"})
    tags_info = call_tool("tags_list", {})
    tasks_info = call_tool("task_list", {"board_id": "15"})

    output = {
        "board": board_info,
        "tags": tags_info,
        "tasks": tasks_info
    }
    with open("scratch/superthread_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    p.terminate()
    print("\n✅ All 10 cards updated with solution comments and moved to Done!")

if __name__ == "__main__":
    move_all_to_done()
