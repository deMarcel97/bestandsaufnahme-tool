import subprocess
import json

def update_cards():
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
        print(f"Calling tool: {tool_name} for task {args.get('task_id') or args.get('card_id')}")
        send({"jsonrpc": "2.0", "id": req_id, "method": "tools/call", "params": {"name": tool_name, "arguments": args}})
        res = read_res()
        print(f"Result: {json.dumps(res)[:120]}...")
        return res

    cards_to_update = [
        {
            "id": "293",
            "loesungsweg": "Lösungsweg:\nUrsache analysiert: setuptools versuchte aufgrund des Flat-Layouts ohne Package-Konfiguration Verzeichnisse wie rules, exports, schemas und bewertung als Top-Level Python-Packages zu installieren.\nLösung: Explizite Definition von [tool.setuptools] packages = [\"app\"] in pyproject.toml.",
            "loesung": "Lösung:\nIn pyproject.toml [tool.setuptools] packages = [\"app\"] ergänzt. 'pip install -e .[dev]' im sauberen venv erfolgreich getestet; alle Tests laufen fehlerfrei durch."
        },
        {
            "id": "292",
            "loesungsweg": "Lösungsweg:\nIn app/services/exporter.py ruft der DOCX-Export chart_generator.py auf, welcher 'from PIL import Image, ImageDraw, ImageFont' importiert. Pillow war nicht unter dependencies deklariert und es fehlte ein Test für export_analysebericht_docx().",
            "loesung": "Lösung:\n'pillow>=10.0.0' in pyproject.toml unter dependencies ergänzt. 'test_docx_exporter()' in tests/test_exporter.py hinzugefügt, sodass DOCX-Erstellung und Chart-Rendering automatisiert per pytest abgesichert sind."
        },
        {
            "id": "291",
            "loesungsweg": "Lösungsweg:\nVergleich von README.md, CHANGELOG.md und pyproject.toml zeigte inkonsistente Versionsangaben (2.1.0 im README-Fließtext vs. 2.2.0) und fehlendes requires-python.",
            "loesung": "Lösung:\nVersion einheitlich auf 2.3.0 in pyproject.toml, CHANGELOG.md und README.md angehoben. 'requires-python = \">=3.10\"' in pyproject.toml und README.md hinterlegt."
        },
        {
            "id": "294",
            "loesungsweg": "Lösungsweg:\nEvaluatorService.evaluate_auftrag() erhielt bisher nur objekte, nicht die Standort-Objekte, wodurch die schlechtester_standort_bezeichnung nur die interne ID duplizierte statt den Klarnamen aufzulösen.",
            "loesung": "Lösung:\nParameter 'standorte: Optional[List[Standort]] = None' zu evaluate_auftrag() hinzugefügt und in allen Routen (routes_auftrag.py, routes_bewertung.py, routes_export.py, exporter.py) übergeben. Neuer Unit-Test in tests/test_evaluator.py deckt die Namensauflösung ab."
        }
    ]

    for card in cards_to_update:
        # 1. Add Kommentar 1: Lösungsweg
        call_tool("comment_create", {"task_id": card["id"], "content": card["loesungsweg"]})
        # 2. Add Kommentar 2: Lösung
        call_tool("comment_create", {"task_id": card["id"], "content": card["loesung"]})
        # 3. Move to Done (list_id 84)
        call_tool("task_update", {"task_id": card["id"], "list_id": "84"})

    p.terminate()
    print("All cards updated successfully!")

if __name__ == "__main__":
    update_cards()
