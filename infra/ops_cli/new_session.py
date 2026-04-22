from __future__ import annotations

import argparse
import datetime as dt
import shutil
import subprocess
from pathlib import Path

from .common import now_in_timezone, read_text_utf8, repo_root

WINDOWS_TZ_MAP = {
    "Eastern Standard Time": "America/New_York",
    "UTC": "UTC",
}


def _resolve_timezone(name: str) -> str:
    if name in WINDOWS_TZ_MAP:
        return WINDOWS_TZ_MAP[name]
    # validate
    now_in_timezone(name)
    return name


def _run_git_value(args: list[str], default: str) -> str:
    try:
        out = subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL).strip()
        return out or default
    except Exception:
        return default


def _get_recent_session_lines(context_project_path: Path) -> list[str]:
    text = read_text_utf8(context_project_path)
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("- notes/sessions/") or line.startswith("- `notes/sessions/"):
            lines.append(line.replace("`", ""))
    return lines


def _get_global_backlog_lines(context_tasks_path: Path) -> list[str]:
    text = read_text_utf8(context_tasks_path)
    marker = "## Global Backlog (Cross-Session)"
    if marker not in text:
        return ["- [ ] P0:", "- [ ] P1:", "- [ ] P2:"]
    body = text.split(marker, 1)[1]
    body = body.split("## Process", 1)[0].strip()
    if not body:
        return ["- [ ] P0:", "- [ ] P1:", "- [ ] P2:"]
    return body.splitlines()


def _apply_meta_template(meta_path: Path, replacements: dict[str, str]) -> None:
    text = meta_path.read_text(encoding="utf-8")
    for old, new in replacements.items():
        text = text.replace(old, new)
    meta_path.write_text(text, encoding="utf-8")


def _update_context_indexes(repo: Path, session_rel: str, session_id: str) -> None:
    context_project = repo / "notes/context/project_state.md"
    context_tasks = repo / "notes/context/open_tasks.md"
    context_handoff = repo / "notes/context/handoff.md"

    current_recent = f"- {session_rel}/"
    recent = [current_recent]
    for line in _get_recent_session_lines(context_project):
        if line != current_recent:
            recent.append(line)
    recent = list(dict.fromkeys(recent))[:5]
    recent_text = "\n".join(recent)

    backlog_text = "\n".join(_get_global_backlog_lines(context_tasks))

    project_index = (
        "# Project State (Index)\n\n"
        "## Active Session\n"
        f"- Path: {session_rel}/project_state.md\n"
        f"- Meta: {session_rel}/meta.yaml\n"
        "- Status: ACTIVE\n\n"
        "## Recent Sessions\n"
        f"{recent_text}\n\n"
        "## Global Rules\n"
        "- Session folders are immutable records; do not overwrite prior sessions.\n"
        "- New substantive work must create a new session folder under notes/sessions/YYYY-MM-DD/<task-id>/ (or notes/sessions/YYYY-MM-DD/HHMM/<task-id>/ with time-bucket mode).\n"
        "- Keep this index file updated with the latest active session pointer.\n"
    )

    tasks_index = (
        "# Open Tasks (Index)\n\n"
        "## Active Session Tasks\n"
        f"- Path: {session_rel}/open_tasks.md\n\n"
        "## Global Backlog (Cross-Session)\n"
        f"{backlog_text}\n\n"
        "## Process\n"
        "- Task details and completion evidence belong in the session-local open_tasks.md.\n"
        "- Keep this file as the long-horizon queue and session pointer only.\n"
    )

    handoff_index = (
        "# Handoff (Index)\n\n"
        "## Active Handoff\n"
        f"- Path: {session_rel}/handoff.md\n"
        f"- Meta: {session_rel}/meta.yaml\n\n"
        "## Latest Outcome\n"
        f"- Session: {session_id}\n"
        "- Summary: Session created. Fill handoff.md when work is completed.\n\n"
        "## Next Session Bootstrap\n"
        "1. Read this file.\n"
        "2. Read notes/context/project_state.md and notes/context/open_tasks.md.\n"
        "3. Open the active session folder and continue from its handoff.md.\n"
    )

    context_project.write_text(project_index, encoding="utf-8")
    context_tasks.write_text(tasks_index, encoding="utf-8")
    context_handoff.write_text(handoff_index, encoding="utf-8")


def run_new_session(args: argparse.Namespace) -> int:
    repo = repo_root()
    tz_name = _resolve_timezone(args.timezone)
    now = now_in_timezone(tz_name)
    date_str = now.strftime("%Y-%m-%d")
    hhmm = now.strftime("%H%M")
    offset = now.utcoffset() or dt.timedelta(0)
    total_mins = int(offset.total_seconds() // 60)
    sign = "+" if total_mins >= 0 else "-"
    mins_abs = abs(total_mins)
    stamp = f"{now.strftime('%Y-%m-%d %H:%M:%S')} {sign}{mins_abs // 60:02d}:{mins_abs % 60:02d}"

    session_rel = (
        f"notes/sessions/{date_str}/{hhmm}/{args.task_id}" if args.use_time_bucket else f"notes/sessions/{date_str}/{args.task_id}"
    )
    session_dir = repo / session_rel
    if session_dir.exists():
        raise FileExistsError(f"Session already exists: {session_rel}")

    templates = repo / "notes/sessions/_templates"
    required = {
        "project_state.template.md": "project_state.md",
        "open_tasks.template.md": "open_tasks.md",
        "handoff.template.md": "handoff.md",
        "meta.template.yaml": "meta.yaml",
    }

    session_dir.mkdir(parents=True, exist_ok=False)
    for src, dst in required.items():
        source_file = templates / src
        if not source_file.exists():
            raise FileNotFoundError(f"Template not found: {source_file}")
        shutil.copy2(source_file, session_dir / dst)

    branch = _run_git_value(["git", "rev-parse", "--abbrev-ref", "HEAD"], "unknown")
    commit = _run_git_value(["git", "rev-parse", "--short", "HEAD"], "unknown")
    title = args.title or args.task_id.replace("_", " ")

    session_id = f"{date_str}/{hhmm}/{args.task_id}" if args.use_time_bucket else f"{date_str}/{args.task_id}"
    meta_path = session_dir / "meta.yaml"
    _apply_meta_template(
        meta_path,
        {
            'session_id: "YYYY-MM-DD/HHMM_scope_hotfix_or_mod"': f'session_id: "{session_id}"',
            'title: ""': f'title: "{title}"',
            'scope: "hotfix only | hotfix + modularization | feature"': f'scope: "{args.scope}"',
            'owner: ""': f'owner: "{args.owner}"',
            'timezone: "America/New_York"': f'timezone: "{tz_name}"',
            'started_at_et: ""': f'started_at_et: "{stamp}"',
            'updated_at_et: ""': f'updated_at_et: "{stamp}"',
            'branch: ""': f'branch: "{branch}"',
            'base_commit: ""': f'base_commit: "{commit}"',
            'head_commit: ""': f'head_commit: "{commit}"',
            'parent_session: null': (
                f'parent_session: "{args.parent_session}"' if args.parent_session else "parent_session: null"
            ),
        },
    )

    if args.update_pointer:
        _update_context_indexes(repo, session_rel, session_id)

    print(f"Session created: {session_rel}")
    print(f"Timezone: {tz_name}")
    if args.update_pointer:
        print("Updated context pointers: notes/context/project_state.md, notes/context/open_tasks.md, notes/context/handoff.md")
    else:
        print("Context pointer update: skipped (default; use --update-pointer to sync)")
    return 0


def build_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("new-session", help="Create a new session folder")
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--title", default="")
    parser.add_argument("--scope", default="hotfix + modularization")
    parser.add_argument("--owner", default="Codex")
    parser.add_argument("--parent-session", default="")
    parser.add_argument("--timezone", default="America/New_York")
    parser.add_argument("--use-time-bucket", action="store_true")
    parser.add_argument("--update-pointer", action="store_true")
    parser.set_defaults(func=run_new_session)
