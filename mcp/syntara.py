#!/usr/bin/env python3
"""Syntara installer entrypoint."""

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

WORKBUDDY_CONFIG = Path.home() / ".workbuddy" / "mcp.json"
WORKBUDDY_SKILLS_DIR = Path.home() / ".workbuddy" / "skills"
TRAE_SOLO_USER_DIR = Path.home() / "Library" / "Application Support" / "TRAE SOLO" / "User"
TRAE_SOLO_MCP_CONFIG = TRAE_SOLO_USER_DIR / "mcp.json"
TRAE_GLOBAL_SKILLS_DIR = Path.home() / ".trae" / "skills"
LEGACY_PROJECT_TRAE_SKILLS_DIR = ROOT / ".trae" / "skills"

TARGETS = ("workbuddy", "trae")
WORKBUDDY_SKILLS = {
    "syntara-style-profiler": "Syntara 风格档案",
    "syntara-writing": "Syntara 写作",
}
TRAE_SKILLS = list(WORKBUDDY_SKILLS)
RETIRED_SKILLS = {
    "syntara-knowledge-writing": "Syntara 资料写作",
    "syntara-academic-writing": "Syntara 学术书籍写作",
    "syntara-literature-review": "Syntara 文献综述",
}


def read_config(path: Path, label: str) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{label} MCP config is not valid JSON: {path}\n{exc}") from exc


def write_config(path: Path, config: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ensure_runtime() -> None:
    if not PYTHON.exists():
        print(f"Missing virtualenv Python: {PYTHON}", file=sys.stderr)
        print("Run this first: ./start.sh", file=sys.stderr)
        raise SystemExit(1)
    if not MCP.exists():
        print(f"Missing MCP server: {MCP}", file=sys.stderr)
        raise SystemExit(1)


def syntara_server_config() -> dict:
    return {
        "command": str(PYTHON),
        "args": [str(MCP)],
        "env": {
            "SYNTARA_BASE_URL": "http://127.0.0.1:8888",
            "SYNTARA_MCP_AUTO_START": "1",
        },
        "disabled": False,
    }


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


def install_workbuddy_skills() -> list[str]:
    WORKBUDDY_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    installed: list[str] = []
    installed_at = int(time.time() * 1000)
    for skill_name in RETIRED_SKILLS:
        dst = WORKBUDDY_SKILLS_DIR / skill_name
        if dst.exists():
            shutil.rmtree(dst)
    for skill_name, display_name in WORKBUDDY_SKILLS.items():
        src = ROOT / "skills" / skill_name
        if not src.exists():
            raise SystemExit(f"Missing skill directory: {src}")
        dst = WORKBUDDY_SKILLS_DIR / skill_name
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


def uninstall_workbuddy_skills() -> list[str]:
    removed: list[str] = []
    all_skills = {**WORKBUDDY_SKILLS, **RETIRED_SKILLS}
    for skill_name, display_name in all_skills.items():
        dst = WORKBUDDY_SKILLS_DIR / skill_name
        if dst.exists():
            shutil.rmtree(dst)
            removed.append(f"{display_name} ({skill_name})")
    return removed


def install_trae_skills() -> list[str]:
    TRAE_GLOBAL_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    installed: list[str] = []
    for skill_name in RETIRED_SKILLS:
        dst = TRAE_GLOBAL_SKILLS_DIR / skill_name
        if dst.exists():
            shutil.rmtree(dst)
    for skill_name in TRAE_SKILLS:
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
    for skills_dir in [TRAE_GLOBAL_SKILLS_DIR, LEGACY_PROJECT_TRAE_SKILLS_DIR]:
        for skill_name in [*TRAE_SKILLS, *RETIRED_SKILLS]:
            dst = skills_dir / skill_name
            if dst.exists():
                shutil.rmtree(dst)
                removed.append(str(dst))
    return removed


def install_mcp_config(path: Path, label: str) -> Path:
    config = read_config(path, label)
    servers = config.setdefault("mcpServers", {})
    servers["syntara"] = syntara_server_config()
    write_config(path, config)
    return path


def uninstall_mcp_config(path: Path, label: str) -> bool:
    config = read_config(path, label)
    servers = config.get("mcpServers")
    if not isinstance(servers, dict) or "syntara" not in servers:
        return False
    del servers["syntara"]
    write_config(path, config)
    return True


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


def install_workbuddy(args: argparse.Namespace) -> None:
    ensure_runtime()
    config_path = install_mcp_config(WORKBUDDY_CONFIG, "WorkBuddy")
    installed_skills = [] if args.skip_skills else install_workbuddy_skills()
    style_profile = import_style_file(args)
    killed = restart_existing_syntara_mcp()

    print(f"Installed Syntara MCP for WorkBuddy: {config_path}")
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


def uninstall_workbuddy(args: argparse.Namespace) -> None:
    removed_config = uninstall_mcp_config(WORKBUDDY_CONFIG, "WorkBuddy")
    removed_skills = [] if args.skip_skills else uninstall_workbuddy_skills()
    killed = restart_existing_syntara_mcp()

    if removed_config:
        print(f"Removed Syntara MCP from WorkBuddy: {WORKBUDDY_CONFIG}")
    else:
        print("Syntara MCP was not present in WorkBuddy config.")
    if removed_skills:
        print("Removed WorkBuddy Syntara skills:")
        for skill in removed_skills:
            print(f"- {skill}")
    elif not args.skip_skills:
        print("No WorkBuddy Syntara skills were found.")
    if killed:
        print(f"Stopped {killed} existing Syntara MCP process(es).")
    print("Restart WorkBuddy to refresh the MCP and skill lists.")


def install_trae(args: argparse.Namespace, *, skip_missing: bool = False) -> None:
    ensure_runtime()
    if not TRAE_SOLO_USER_DIR.exists():
        message = f"TRAE SOLO user directory not found: {TRAE_SOLO_USER_DIR}"
        if skip_missing:
            print(f"{message}; skipped TRAE SOLO.")
            return
        print(message, file=sys.stderr)
        print("Open TRAE SOLO once, then run this installer again.", file=sys.stderr)
        raise SystemExit(1)

    config_path = install_mcp_config(TRAE_SOLO_MCP_CONFIG, "TRAE SOLO")
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


def uninstall_trae(args: argparse.Namespace) -> None:
    removed_config = uninstall_mcp_config(TRAE_SOLO_MCP_CONFIG, "TRAE SOLO")
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


def run_for_target(target: str, action, args: argparse.Namespace) -> None:
    if target == "workbuddy":
        action["workbuddy"](args)
        return
    if target == "trae":
        action["trae"](args)
        return
    for name in TARGETS:
        if name == "trae" and action is INSTALL_ACTIONS:
            install_trae(args, skip_missing=True)
        else:
            action[name](args)


def find_python3() -> str:
    for name in ["python3.12", "python3"]:
        path = shutil.which(name)
        if path:
            return path
    raise SystemExit("Python 3 is required but was not found on PATH.")


def update_repo_and_dependencies() -> None:
    if (ROOT / ".git").exists():
        subprocess.run(["git", "pull", "--ff-only"], cwd=str(ROOT), check=True)
    if not PYTHON.exists():
        subprocess.run([find_python3(), "-m", "venv", str(ROOT / ".venv")], cwd=str(ROOT), check=True)
    subprocess.run([str(PYTHON), "-m", "pip", "install", "-q", "-r", "requirements.txt"], cwd=str(ROOT), check=True)

    frontend = ROOT / "frontend"
    if (frontend / "package.json").exists():
        npm = shutil.which("npm")
        if not npm:
            raise SystemExit("npm is required to update frontend dependencies.")
        subprocess.run([npm, "install", "--silent"], cwd=str(frontend), check=True)


def install(args: argparse.Namespace) -> int:
    run_for_target(args.target, INSTALL_ACTIONS, args)
    return 0


def uninstall(args: argparse.Namespace) -> int:
    run_for_target(args.target, UNINSTALL_ACTIONS, args)
    print("Syntara local databases, PDFs, corpora, and style profiles were not deleted.")
    return 0


def update(args: argparse.Namespace) -> int:
    update_repo_and_dependencies()
    run_for_target(args.target, INSTALL_ACTIONS, args)
    print("Updated Syntara code, dependencies, MCP config, and skills.")
    print("Syntara local databases, PDFs, corpora, and style profiles were not deleted.")
    return 0


def add_common_install_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("target", choices=[*TARGETS, "all"], help="Client integration to manage.")
    parser.add_argument("--style-file", help="Optional Markdown/TXT style profile or style corpus to save during setup.")
    parser.add_argument("--style-name", default="Default Writing Style", help="Name for the imported style profile.")
    parser.add_argument("--style-project", default="default", help="Syntara project slug for the style profile.")
    parser.add_argument(
        "--style-type",
        default="general",
        help="Writing type, such as blog-article, literature-review, manual, instructional-guide, presentation, or general.",
    )
    parser.add_argument("--no-default-style", action="store_true", help="Do not set the imported style as project default.")
    parser.add_argument("--setup-style", action="store_true", help="Prompt for a style file path after installing MCP.")
    parser.add_argument("--skip-skills", action="store_true", help="Do not install or remove Syntara client skills.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Install, update, or uninstall Syntara client integrations.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    install_parser = subparsers.add_parser("install", help="Install Syntara MCP and skills into a client.")
    add_common_install_options(install_parser)
    install_parser.set_defaults(func=install)

    update_parser = subparsers.add_parser("update", help="Update Syntara, then refresh client MCP and skills.")
    add_common_install_options(update_parser)
    update_parser.set_defaults(func=update)

    uninstall_parser = subparsers.add_parser("uninstall", help="Remove Syntara MCP and copied skills from a client.")
    uninstall_parser.add_argument("target", choices=[*TARGETS, "all"], help="Client integration to remove.")
    uninstall_parser.add_argument("--skip-skills", action="store_true", help="Only remove MCP config; do not remove copied skills.")
    uninstall_parser.set_defaults(func=uninstall)

    return parser


INSTALL_ACTIONS = {
    "workbuddy": install_workbuddy,
    "trae": install_trae,
}
UNINSTALL_ACTIONS = {
    "workbuddy": uninstall_workbuddy,
    "trae": uninstall_trae,
}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
