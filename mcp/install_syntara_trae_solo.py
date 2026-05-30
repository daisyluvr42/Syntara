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
SKILLS = [
    "syntara-style-profiler",
    "syntara-knowledge-writing",
    "syntara-academic-writing",
    "syntara-literature-review",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install Syntara MCP into TRAE SOLO.")
    parser.add_argument(
        "--project-dir",
        default=str(ROOT),
        help="Project directory that should receive .trae/skills. Defaults to this Syntara checkout.",
    )
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


def install_trae_skills(project_dir: Path) -> list[str]:
    skills_dir = project_dir / ".trae" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    installed: list[str] = []
    for skill_name in SKILLS:
        src = ROOT / "skills" / skill_name
        if not src.exists():
            raise SystemExit(f"Missing skill directory: {src}")
        dst = skills_dir / skill_name
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        installed.append(str(dst))
    return installed


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
    project_dir = Path(args.project_dir).expanduser().resolve()

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
    if not project_dir.exists():
        print(f"Project directory not found: {project_dir}", file=sys.stderr)
        return 1

    config_path = install_mcp_config()
    installed_skills = [] if args.skip_skills else install_trae_skills(project_dir)
    killed = restart_existing_syntara_mcp()

    print(f"Installed Syntara MCP for TRAE SOLO: {config_path}")
    if installed_skills:
        print("Installed TRAE SOLO project skills:")
        for skill in installed_skills:
            print(f"- {skill}")
    if killed:
        print(f"Restarted {killed} existing Syntara MCP process(es).")
    print("Restart TRAE SOLO, then enable/use the syntara MCP server from the MCP panel if prompted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
