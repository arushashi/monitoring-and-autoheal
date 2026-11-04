#!/usr/bin/env python3
"""Alert-driven auto-healing webhook (Alertmanager-style payloads).

Safety features:
  * allow-list: only alerts listed in ACTIONS can trigger anything
  * input validation: names must match a strict pattern (no shell injection)
  * cooldown: the same alert+target is not remediated twice within COOLDOWN_SEC
  * dry-run by default: pass --execute to actually run commands
  * audit log of every decision
"""
import argparse
import json
import re
import subprocess
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

NAME_RE = re.compile(r"^[a-z0-9]([-a-z0-9.]{0,251}[a-z0-9])?$")
COOLDOWN_SEC = 900

# alertname -> command template; {namespace} and {deployment} come from alert labels
ACTIONS = {
    "PodCrashLooping": ["kubectl", "rollout", "restart", "deployment/{deployment}", "-n", "{namespace}"],
    "HighMemoryLeak": ["kubectl", "rollout", "restart", "deployment/{deployment}", "-n", "{namespace}"],
}

_last_run = {}


def decide(alert: dict, now: float, last_run: dict, cooldown: int = COOLDOWN_SEC):
    """Return (command_or_None, reason). Pure function, easy to test."""
    if alert.get("status") != "firing":
        return None, "not firing"
    labels = alert.get("labels", {})
    name = labels.get("alertname")
    template = ACTIONS.get(name)
    if template is None:
        return None, f"no action for alert '{name}'"
    ns, dep = labels.get("namespace", ""), labels.get("deployment", "")
    if not NAME_RE.match(ns) or not NAME_RE.match(dep):
        return None, "invalid namespace/deployment label"
    key = (name, ns, dep)
    if now - last_run.get(key, 0) < cooldown:
        return None, "cooldown active"
    last_run[key] = now
    return [part.format(namespace=ns, deployment=dep) for part in template], "allowed"


def audit(msg: dict) -> None:
    print(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), **msg}), flush=True)


def make_handler(execute: bool):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            length = int(self.headers.get("Content-Length", 0))
            try:
                payload = json.loads(self.rfile.read(length) or b"{}")
            except ValueError:
                self.send_response(400); self.end_headers(); return
            for alert in payload.get("alerts", []):
                cmd, reason = decide(alert, time.time(), _last_run)
                if cmd is None:
                    audit({"decision": "skip", "reason": reason})
                elif execute:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    audit({"decision": "run", "cmd": cmd, "rc": result.returncode})
                else:
                    audit({"decision": "dry-run", "cmd": cmd})
            self.send_response(200); self.end_headers()

        def log_message(self, *args):
            pass
    return Handler


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=9000)
    ap.add_argument("--execute", action="store_true", help="really run commands (default: dry-run)")
    args = ap.parse_args()
    audit({"event": "start", "port": args.port, "execute": args.execute})
    HTTPServer(("0.0.0.0", args.port), make_handler(args.execute)).serve_forever()
