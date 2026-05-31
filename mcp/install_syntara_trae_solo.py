#!/usr/bin/env python3
"""Install Syntara MCP and skills for TRAE SOLO."""

from __future__ import annotations

import argparse
import json
import os
import signal
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "bin" / "python"
MCP = ROOT / "mcp" / "syntara_mcp.py"
TRAE_SOLO_USER_DIR = Path.home() / "Library" / "Application Support" / "TRAE SOLO" / "User"
TRAE_SOLO_MCP_CONFIG = TRAE_SOLO_USER_DIR / "mcp.json"
TRAE_GLOBAL_SKILLS_DIR = Path.home() / ".trae" / "skills"
LEGACY_PROJECT_SKILLS_DIR = ROOT / ".trae" / "skills"
SKILLS = [
    "syntara-style-profiler",
    "syntara-knowledge-writing",
    "syntara-academic-writing",
    "syntara-literature-review",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install Syntara MCP into TRAE SOLO.")
    parser.add_argument("--uninstall", action="store_true", help="Remove Syntara MCP config and global Trae skills.")
    parser.add_argument("--skip-skills", action="store_true", help="Only install MCP config; do not copy Trae skills.")
    return parser.parse_args()


def read_config(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"TRAE SOLO MCP config is not valid JSON: {path}\n{exc}") from exc


def write_config(path: Path, config: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def install_mcp_config() -> Path:
    config = read_config(TRAE_SOLO_MCP_CONFIG)
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
    write_config(TRAE_SOLO_MCP_CONFIG, config)
    return TRAE_SOLO_MCP_CONFIG


def uninstall_mcp_config() -> bool:
    config = read_config(TRAE_SOLO_MCP_CONFIG)
    servers = config.get("mcpServers")
    if not isinstance(servers, dict) or "syntara" not in servers:
        return False
    del servers["syntara"]
    write_config(TRAE_SOLO_MCP_CONFIG, config)
    return True


def install_trae_skills() -> list[str]:
    TRAE_GLOBAL_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    installed: list[str] = []
    for skill_name in SKILLS:
        src = ROOT / "skills" / skill_name
        if not src.exists():
            raise SystemExit(f"Missing skill directory: {src}")
        dst = TRAE_GLOBAL_SKILLS_DIR / skill_name
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        installed.append(str(dst))
    return installed


def uninstall_trae_skills() -> list[str]:
    removed: list[str] = []
    for skills_dir in [TRAE_GLOBAL_SKILLS_DIR, LEGACY_PROJECT_SKILLS_DIR]:
        for skill_name in SKILLS:
            dst = skills_dir / skill_name
            if dst.exists():
                shutil.rmtree(dst)
                removed.append(str(dst))
    return removed


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
    args = parse_args()

    if not PYTHON.exists():
        print(f"Missing virtualenv Python: {PYTHON}", file=sys.stderr)
        print("Run this first: ./start.sh", file=sys.stderr)
        return 1
    if not MCP.exists():
        print(f"Missing MCP server: {MCP}", file=sys.stderr)
        return 1
    if not TRAE_SOLO_USER_DIR.exists():
        print(f"TRAE SOLO user directory not found: {TRAE_SOLO_USER_DIR}", file=sys.stderr)
        print("Open TRAE SOLO once, then run this installer again.", file=sys.stderr)
        return 1

    if args.uninstall:
        removed_config = uninstall_mcp_config()
        removed_skills = [] if args.skip_skills else uninstall_trae_skills()
        killed = restart_existing_syntara_mcp()

        if removed_config:
            print(f"Removed Syntara MCP from TRAE SOLO: {TRAE_SOLO_MCP_CONFIG}")
        else:
            print("Syntara MCP was not present in TRAE SOLO config.")
        if removed_skills:
            print("Removed TRAE SOLO Syntara skills:")
            for skill in removed_skills:
                print(f"- {skill}")
        elif not args.skip_skills:
            print("No TRAE SOLO Syntara skills were found.")
        if killed:
            print(f"Stopped {killed} existing Syntara MCP process(es).")
        print("Restart TRAE SOLO to refresh the MCP and skill lists.")
        return 0

    config_path = install_mcp_config()
    installed_skills = [] if args.skip_skills else install_trae_skills()
    killed = restart_existing_syntara_mcp()

    print(f"Installed Syntara MCP for TRAE SOLO: {config_path}")
    if installed_skills:
        print("Installed TRAE SOLO global skills:")
        for skill in installed_skills:
            print(f"- {skill}")
    if killed:
        print(f"Restarted {killed} existing Syntara MCP process(es).")
    print("Restart TRAE SOLO, then enable/use the syntara MCP server from the MCP panel if prompted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
