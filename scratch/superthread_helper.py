import subprocess
import json
import sys

def run_mcp_session():
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
        send({"jsonrpc": "2.0", "id": req_id, "method": "tools/call", "params": {"name": tool_name, "arguments": args}})
        res = read_res()
        if not res:
            return None
        result = res.get("result", {})
        content = result.get("content", [])
        if content and isinstance(content, list) and "text" in content[0]:
            try:
                return json.loads(content[0]["text"])
            except Exception:
                return content[0]["text"]
        return result

    # 1. Get Board 15 info
    print("=== Fetching Board Info ===")
    board_info = call_tool("board_get", {"board_id": "15"})
    
    # 2. Get tags
    tags_info = call_tool("tags_list", {})

    # 3. Get all tasks for Board 15
    print("=== Fetching Tasks for Board 15 ===")
    tasks_info = call_tool("task_list", {"board_id": "15"})

    output = {
        "board": board_info,
        "tags": tags_info,
        "tasks": tasks_info
    }
    
    with open("scratch/superthread_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    p.terminate()
    print("Successfully saved data to scratch/superthread_data.json")

if __name__ == "__main__":
    run_mcp_session()
