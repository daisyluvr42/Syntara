#!/usr/bin/env python3
"""Install Syntara MCP into WorkBuddy."""

from __future__ import annotations

import argparse
import json
import os
import signal
import shutil
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "bin" / "python"
MCP = ROOT / "mcp" / "syntara_mcp.py"
CONFIG = Path.home() / ".workbuddy" / "mcp.json"
SKILLS_DIR = Path.home() / ".workbuddy" / "skills"
SKILLS = {
    "syntara-style-profiler": "Syntara 风格档案",
    "syntara-knowledge-writing": "Syntara 资料写作",
    "syntara-academic-writing": "Syntara 学术书籍写作",
    "syntara-literature-review": "Syntara 文献综述",
}


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install Syntara MCP into WorkBuddy.")
    parser.add_argument("--style-file", help="Optional Markdown/TXT style profile or style corpus to save during setup.")
    parser.add_argument("--style-name", default="Default Writing Style", help="Name for the imported style profile.")
    parser.add_argument("--style-project", default="default", help="Syntara project slug for the style profile.")
    parser.add_argument(
        "--style-type",
        default="general",
        help="Writing type, such as wechat-longform, professional-book, literature-review, tutorial, ppt.",
    )
    parser.add_argument("--no-default-style", action="store_true", help="Do not set the imported style as project default.")
    parser.add_argument("--setup-style", action="store_true", help="Prompt for a style file path after installing MCP.")
    parser.add_argument("--skip-skills", action="store_true", help="Do not install Syntara WorkBuddy skills.")
    return parser.parse_args()


def import_style_file(args: argparse.Namespace) -> dict | None:
    style_file = args.style_file
    if args.setup_style and not style_file:
        style_file = input("Style file path (leave empty to skip): ").strip()
        if style_file:
            if args.style_name == "Default Writing Style":
                entered_name = input(f"Style name [{args.style_name}]: ").strip()
                if entered_name:
                    args.style_name = entered_name
            entered_project = input(f"Project [{args.style_project}]: ").strip()
            if entered_project:
                args.style_project = entered_project
            entered_type = input(f"Style type [{args.style_type}]: ").strip()
            if entered_type:
                args.style_type = entered_type

    if not style_file:
        return None

    path = Path(style_file).expanduser()
    if not path.exists() or not path.is_file():
        raise SystemExit(f"Style file not found: {path}")

    code = f"""
from pathlib import Path
from backend.db.sqlite import init_db
from backend.services.style_profile import save_style_profile

init_db()
path = Path({str(path)!r})
profile = save_style_profile(
    name={args.style_name!r},
    project={args.style_project!r},
    style_type={args.style_type!r},
    profile_json={{
        "name": {args.style_name!r},
        "project": {args.style_project!r},
        "style_type": {args.style_type!r},
        "source": str(path),
        "kind": "imported_style_profile",
    }},
    profile_markdown=path.read_text(encoding="utf-8", errors="ignore"),
    tags=["imported-style", {args.style_type!r}],
    set_default={not args.no_default_style!r},
)
print(profile["id"])
"""
    result = subprocess.run(
        [str(PYTHON), "-c", code],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"Failed to import style file:\n{result.stderr}")
    return {
        "id": result.stdout.strip().splitlines()[-1],
        "name": args.style_name,
        "project": args.style_project,
        "style_type": args.style_type,
    }


def install_workbuddy_skills() -> list[str]:
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    installed: list[str] = []
    installed_at = int(time.time() * 1000)
    for skill_name, display_name in SKILLS.items():
        src = ROOT / "skills" / skill_name
        if not src.exists():
            raise SystemExit(f"Missing skill directory: {src}")
        dst = SKILLS_DIR / skill_name
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        meta = {
            "name": display_name,
            "installedAt": installed_at,
            "source": "userImport",
        }
        (dst / "_user_meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        installed.append(f"{display_name} ({skill_name})")
    return installed


def main() -> int:
    args = parse_args()
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
    installed_skills = [] if args.skip_skills else install_workbuddy_skills()
    style_profile = import_style_file(args)
    killed = restart_existing_syntara_mcp()

    print(f"Installed Syntara MCP for WorkBuddy: {CONFIG}")
    if installed_skills:
        print("Installed WorkBuddy skills:")
        for skill in installed_skills:
            print(f"- {skill}")
    if style_profile:
        print(
            "Imported style profile: "
            f"{style_profile['name']} "
            f"(project={style_profile['project']}, style_type={style_profile['style_type']}, id={style_profile['id']})"
        )
    if killed:
        print(f"Restarted {killed} existing Syntara MCP process(es).")
    print("Open WorkBuddy -> Connectors -> Custom Connector -> MCP management, then trust/enable syntara if prompted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
