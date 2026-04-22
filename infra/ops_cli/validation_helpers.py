from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .common import normalize_repo_path, path_glob_match


@dataclass
class Hit:
    rule_id: str
    path: str
    line: int
    excerpt: str
    message: str


def read_active_session_path(context_project_file: Path) -> str:
    text = context_project_file.read_text(encoding="utf-8")
    match = re.search(r"(?m)^- Path:\s+`?(.+?)/project_state\.md`?$", text)
    if not match:
        raise ValueError(f"Cannot parse active session path from {context_project_file}")
    return match.group(1)


def get_meta_list_items(meta_text: str, key: str) -> list[str]:
    inline = re.search(rf"(?m)^{re.escape(key)}:\s*\[(.*?)\]\s*$", meta_text)
    if inline:
        body = inline.group(1).strip()
        if not body:
            return []
        tokens: list[str] = []
        for raw in body.split(","):
            token = raw.strip()
            if (token.startswith('"') and token.endswith('"')) or (
                token.startswith("'") and token.endswith("'")
            ):
                token = token[1:-1]
            if token:
                tokens.append(token)
        return tokens

    lines = meta_text.splitlines()
    items: list[str] = []
    in_block = False
    base_indent = 0

    for raw in lines:
        line = raw.rstrip("\n")
        if not in_block:
            header = re.match(rf"^([ \t]*){re.escape(key)}\s*:\s*$", line)
            if header:
                in_block = True
                base_indent = len(header.group(1))
            continue

        if not line.strip():
            continue

        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if indent <= base_indent and not stripped.startswith("-"):
            break
        if not stripped.startswith("-"):
            break

        value = stripped[1:].strip()
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        if value:
            items.append(value)

    return items


def get_unchecked_open_task_items(open_tasks_path: Path) -> list[dict[str, str | int]]:
    if not open_tasks_path.exists():
        return []

    section = ""
    rows: list[dict[str, str | int]] = []
    for line_no, line in enumerate(open_tasks_path.read_text(encoding="utf-8").splitlines(), start=1):
        header = re.match(r"^\s*##\s+(.+?)\s*$", line)
        if header:
            section = header.group(1).strip()
            continue

        unchecked = re.match(r"^\s*-\s*\[\s\]\s*(.+?)\s*$", line)
        if not unchecked:
            continue

        item = unchecked.group(1).strip()
        if re.search(r"(?i)SUP(?:ER|SER)SEDED-BY\s*:", item):
            continue
        rows.append({"section": section, "item": item, "line": line_no})
    return rows


def get_handoff_field(handoff_text: str, field_name: str) -> str | None:
    match = re.search(rf"(?im)^\s*(?:-\s*)?{re.escape(field_name)}\s*:\s*(.+?)\s*$", handoff_text)
    return match.group(1).strip() if match else None


def load_policy(policy_path: Path) -> dict:
    return json.loads(policy_path.read_text(encoding="utf-8"))


def get_runtime_source_targets(repo_root: Path) -> list[str]:
    roots = ("l0_ingest", "l1_compute", "l2_decision", "l3_assembly", "l4_ui", "app", "shared")
    ext_allow = {".py", ".ts", ".tsx", ".rs"}
    skip_fragments = ("/tests/", "/test/", "/__tests__/", "/__pycache__/", "/node_modules/", "/dist/", "/build/")

    targets: list[str] = []
    for root in roots:
        root_dir = repo_root / root
        if not root_dir.exists():
            continue
        for file_path in root_dir.rglob("*"):
            if not file_path.is_file() or file_path.suffix.lower() not in ext_allow:
                continue
            rel = normalize_repo_path(str(file_path.relative_to(repo_root)))
            if any(fragment in rel for fragment in skip_fragments):
                continue
            targets.append(rel)

    deduped = sorted(set(targets))
    return deduped


def scan_layer_boundary_hits(repo_root: Path, target_paths: list[str], policy: dict) -> list[Hit]:
    rules = [rule for rule in policy.get("rules", []) if rule.get("enabled", True)]
    allow_rules = policy.get("allow", [])
    hits: list[Hit] = []

    for target in sorted(set(target_paths)):
        norm_target = normalize_repo_path(target)
        if not norm_target:
            continue
        full_path = repo_root / norm_target
        if not full_path.exists() or not full_path.is_file():
            continue

        lines = full_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for line_no, line in enumerate(lines, start=1):
            for rule in rules:
                rule_glob = str(rule.get("glob", "")).strip()
                rule_regex = str(rule.get("regex", "")).strip()
                if not rule_glob or not rule_regex:
                    continue
                if not path_glob_match(norm_target, rule_glob):
                    continue
                if not re.search(rule_regex, line, flags=re.IGNORECASE):
                    continue

                allowed = False
                for allow_rule in allow_rules:
                    allow_glob = str(allow_rule.get("glob", "")).strip()
                    allow_regex = str(allow_rule.get("regex", "")).strip()
                    if not allow_glob or not allow_regex:
                        continue
                    if path_glob_match(norm_target, allow_glob) and re.search(
                        allow_regex,
                        line,
                        flags=re.IGNORECASE,
                    ):
                        allowed = True
                        break

                if not allowed:
                    hits.append(
                        Hit(
                            rule_id=str(rule.get("id", "RULE")),
                            path=norm_target,
                            line=line_no,
                            excerpt=line.strip(),
                            message=str(rule.get("message", "Violation")),
                        )
                    )
    return hits


def scan_anti_pattern_hits(repo_root: Path, target_paths: list[str]) -> list[Hit]:
    hits: list[Hit] = []
    for target in sorted(set(target_paths)):
        norm_target = normalize_repo_path(target)
        if not norm_target:
            continue
        full_path = repo_root / norm_target
        if not full_path.exists() or not full_path.is_file():
            continue

        ext = full_path.suffix.lower()
        lines = full_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for line_no, line in enumerate(lines, start=1):
            trimmed = line.strip()
            if ext == ".rs" and re.search(r"\bunwrap\s*\(", trimmed):
                hits.append(
                    Hit(
                        rule_id="RUST_RUNTIME_UNWRAP",
                        path=norm_target,
                        line=line_no,
                        excerpt=trimmed,
                        message="Rust runtime path must not introduce unwrap().",
                    )
                )
            if ext == ".py" and (
                re.match(r"^except\s*:\s*$", trimmed)
                or re.match(r"^except\s+Exception\s*:\s*$", trimmed)
            ):
                hits.append(
                    Hit(
                        rule_id="PY_SILENT_EXCEPT",
                        path=norm_target,
                        line=line_no,
                        excerpt=trimmed,
                        message="Silent/bare Python except in runtime source is forbidden.",
                    )
                )
    return hits
