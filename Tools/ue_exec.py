"""Run Python inside the running Voyager Unreal Editor (Python remote execution).

Usage:
    python Tools/ue_exec.py script.py        # run a file
    python Tools/ue_exec.py -c "print(1)"    # run inline code

Needs Project Settings > Plugins > Python > Enable Remote Execution (local only:
bind 127.0.0.1, TTL 0). Uses the engine's own client, remote_execution.py.
"""
import os
import sys
import time

ENGINE = os.environ.get("UE_ROOT", r"C:\Program Files\Epic Games\UE_5.8")
sys.path.insert(0, os.path.join(ENGINE, r"Engine\Plugins\Experimental\PythonScriptPlugin\Content\Python"))
import remote_execution as rx  # noqa: E402

PROJECT_ROOT = os.path.normcase(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def find_node(session, timeout=5.0):
    end = time.time() + timeout
    while time.time() < end:
        for node in session.remote_nodes:
            root = os.path.normcase(os.path.abspath(node.get("project_root", "")))
            if root == PROJECT_ROOT:
                return node
        time.sleep(0.1)
    found = [n.get("project_root") for n in session.remote_nodes]
    raise SystemExit(f"No editor found for {PROJECT_ROOT}. Seen: {found}")


def run(code):
    session = rx.RemoteExecution()
    session.start()
    try:
        node = find_node(session)
        session.open_command_connection(node["node_id"])
        result = session.run_command(code, unattended=True, exec_mode=rx.MODE_EXEC_FILE)
        for entry in result.get("output", []):
            print(entry.get("output", "").rstrip())
        if not result.get("success"):
            print(result.get("result"), file=sys.stderr)
            return 1
        return 0
    finally:
        session.stop()


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "-c":
        src = sys.argv[2]
    elif len(sys.argv) == 2:
        with open(sys.argv[1], encoding="utf-8") as f:
            src = f.read()
    else:
        raise SystemExit(__doc__)
    sys.exit(run(src))
