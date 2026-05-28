#!/usr/bin/env python3
"""Install Syntara MCP into WorkBuddy."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "bin" / "python"
MCP = ROOT / "mcp" / "syntara_mcp.py"
CONFIG = Path.home() / ".workbuddy" / "mcp.json"


def read_config() -> dict:
    if not CONFIG.exists():
        return {}
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"WorkBuddy MCP config is not valid JSON: {CONFIG}\n{exc}") from exc


def write_config(config: dict) -> None:
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def restart_existing_syntara_mcp() -> int:
    try:
        result = subprocess.run(
            ["pgrep", "-f", str(MCP)],
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        return 0

    killed = 0
    for line in result.stdout.splitlines():
        try:
            pid = int(line.strip())
        except ValueError:
            continue
        if pid == os.getpid():
            continue
        try:
            os.kill(pid, signal.SIGTERM)
            killed += 1
        except ProcessLookupError:
            pass
    return killed


def main() -> int:
    if not PYTHON.exists():
        print(f"Missing virtualenv Python: {PYTHON}", file=sys.stderr)
        print("Run this first: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt", file=sys.stderr)
        return 1
    if not MCP.exists():
        print(f"Missing MCP server: {MCP}", file=sys.stderr)
        return 1

    config = read_config()
    servers = config.setdefault("mcpServers", {})
    servers["syntara"] = {
        "command": str(PYTHON),
        "args": [str(MCP)],
        "env": {
            "SYNTARA_BASE_URL": "http://127.0.0.1:8888",
            "SYNTARA_MCP_AUTO_START": "1",
        },
        "disabled": False,
    }
    write_config(config)
    killed = restart_existing_syntara_mcp()

    print(f"Installed Syntara MCP for WorkBuddy: {CONFIG}")
    if killed:
        print(f"Restarted {killed} existing Syntara MCP process(es).")
    print("Open WorkBuddy -> Connectors -> Custom Connector -> MCP management, then trust/enable syntara if prompted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
