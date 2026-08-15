import subprocess
import json
import time

def tag_cards():
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

    # Tag Mapping:
    # 4 = Bug
    # 5 = Feature
    card_tags = [
        {"id": "281", "tag": "4", "name": "Bug", "title": "QA-Testdaten bereinigen"},
        {"id": "283", "tag": "5", "name": "Feature", "title": "Auftragsstatus & Vertraulichkeit editierbar"},
        {"id": "284", "tag": "5", "name": "Feature", "title": "Empfehlung bei Stammdaten-Änderung"},
        {"id": "286", "tag": "5", "name": "Feature", "title": "Trennung Stammdaten & Kontext"},
        {"id": "287", "tag": "5", "name": "Feature", "title": "Offene Punkte strukturieren"},
        {"id": "295", "tag": "4", "name": "Bug", "title": "Ampelfarben Standortübersicht"},
        {"id": "296", "tag": "5", "name": "Feature", "title": "Server-Detailfragen ergänzen"},
        {"id": "297", "tag": "5", "name": "Feature", "title": "Server & Virtualisierung: Pflichtfeld"},
        {"id": "298", "tag": "5", "name": "Feature", "title": "Feld Festplatten-Slots"},
        {"id": "299", "tag": "4", "name": "Bug", "title": "Feld Kommentar ans Formularende"}
    ]

    for ct in card_tags:
        cid = ct["id"]
        tag_id = ct["tag"]
        print(f"\n--- Tagging Card #{cid} ({ct['title']}) with [{ct['name']}] ---")
        call_tool("task_add_tags", {"task_id": cid, "space_id": "6", "tag_ids": [tag_id]})
        time.sleep(0.3)

    # Refresh board data
    print("\n=== Refreshing Superthread Board Data ===")
    board_info = call_tool("board_get", {"board_id": "15"})
    tags_info = call_tool("tags_list", {"space_id": "6"})
    tasks_info = call_tool("task_list", {"board_id": "15"})

    output = {
        "board": board_info,
        "tags": tags_info,
        "tasks": tasks_info
    }
    with open("scratch/superthread_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    p.terminate()
    print("\n✅ All 10 cards tagged successfully!")

if __name__ == "__main__":
    tag_cards()
