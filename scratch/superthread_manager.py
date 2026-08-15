import subprocess
import json
import sys

def execute_mcp_actions(actions):
    """
    actions: list of dicts with {"tool": "tool_name", "args": {...}}
    """
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

    results = []
    for action in actions:
        req_id += 1
        tool = action["tool"]
        args = action["args"]
        print(f"Calling tool: {tool} with args: {args.keys()}")
        send({"jsonrpc": "2.0", "id": req_id, "method": "tools/call", "params": {"name": tool, "arguments": args}})
        res = read_res()
        results.append(res)
        print(f"Result for {tool}: {json.dumps(res)[:100]}...")

    p.terminate()
    return results

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "move_doing":
        task_ids = sys.argv[2:]
        actions = [{"tool": "task_update", "args": {"task_id": tid, "list_id": "83"}} for tid in task_ids]
        execute_mcp_actions(actions)
