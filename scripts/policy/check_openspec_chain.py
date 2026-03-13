#!/usr/bin/env python3
"""OpenSpec parent/child governance gate.

Validates refactor governance proposal structure and runtime-change proposal linkage.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

RUNTIME_PREFIXES = (
    "l0_ingest/",
    "l1_compute/",
    "l2_decision/",
    "l3_assembly/",
    "l4_ui/",
    "app/",
    "shared/",
)

SKIP_RUNTIME_PATTERNS = (
    "/tests/",
    "/test/",
    "/__tests__/",
    "/__pycache__/",
    "/node_modules/",
    "/dist/",
    "/build/",
)

PARENT_PATTERN = re.compile(r"^refactor-governance-\d{8}-[a-z0-9-]+$")
CHILD_PATTERN = re.compile(r"^refactor-(nesting|dependency|bloat|magic-number)-\d{8}-[a-z0-9-]+$")

PARENT_TASK_LINES = [
    "## Governance",
    "- [ ] 定义统一度量口径（复杂度/嵌套/重复率/魔法数）",
    "- [ ] 定义子提案依赖图与执行顺序",
    "- [ ] 定义回滚策略与风险分级",
    "## Child Proposal Gate",
    "- [ ] nesting 子提案创建并通过审查",
    "- [ ] dependency 子提案创建并通过审查",
    "- [ ] bloat 子提案创建并通过审查",
    "- [ ] magic-number 子提案创建并通过审查",
    "## Merge Gate",
    "- [ ] 所有子提案 DoD 达成",
    "- [ ] 量化 before/after 汇总完成",
    "- [ ] Strict 校验通过并留痕",
]

CHILD_TASK_LINES = [
    "## Scope",
    "- [ ] 锁定目标文件清单（Top N）",
    "- [ ] 标记非目标范围（避免扩散）",
    "## Implementation",
    "- [ ] 重构实现（仅本主题）",
    "- [ ] 边界扫描（无跨层违规 import）",
    "- [ ] 魔法数治理（若本主题涉及）",
    "## Verification",
    "- [ ] 相关测试通过（scripts/test/run_pytest.ps1）",
    "- [ ] 指标达标（见量化门槛）",
    "- [ ] SOP 同步或写明 SOP-EXEMPT",
    "## DoD",
    "- [ ] 复杂度/嵌套/长度/重复率达到阈值",
    "- [ ] 无行为回归",
    "- [ ] 变更可回滚、可审计",
]


def normalize_path(path: str) -> str:
    return path.replace("\\", "/").strip().lstrip("./")


def parse_meta_list(meta_text: str, key: str) -> list[str]:
    lines = meta_text.splitlines()
    out: list[str] = []
    in_block = False
    base_indent = 0

    for raw in lines:
        line = raw.rstrip("\n")
        if not in_block:
            if re.match(rf"^{re.escape(key)}\s*:\s*$", line):
                in_block = True
                base_indent = len(line) - len(line.lstrip(" "))
            continue

        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if not stripped:
            continue
        if indent <= base_indent and not stripped.startswith("-"):
            break
        if stripped.startswith("-"):
            value = stripped[1:].strip().strip("\"").strip("'")
            if value:
                out.append(value)
            continue
        if indent <= base_indent:
            break

    return out


def is_runtime_file(path: str) -> bool:
    norm = normalize_path(path)
    if not norm.startswith(RUNTIME_PREFIXES):
        return False
    if any(p in norm for p in SKIP_RUNTIME_PATTERNS):
        return False
    return norm.endswith((".py", ".rs", ".ts", ".tsx"))


def has_openspec_exempt(handoff_text: str) -> bool:
    return bool(re.search(r"(?im)^\s*(?:-\s*)?OPENSPEC-EXEMPT\s*:\s*.+$", handoff_text))


def require_file(root: Path, rel: str, violations: list[dict[str, Any]], reason: str) -> None:
    if not (root / rel).exists():
        violations.append({"type": "missing_file", "path": rel, "message": reason})


def require_task_template(text: str, required_lines: list[str], path: str, violations: list[dict[str, Any]]) -> None:
    normalized_text = re.sub(r"-\s*\[[xX ]\]\s*", "- [ ] ", text)
    for line in required_lines:
        normalized_line = re.sub(r"-\s*\[[xX ]\]\s*", "- [ ] ", line)
        if normalized_line not in normalized_text:
            violations.append(
                {
                    "type": "task_template_missing_line",
                    "path": path,
                    "message": f"Required task template line missing: {line}",
                }
            )


def parse_child_headers(proposal_text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for key in ("PARENT_CHANGE_ID", "DEPENDENCY_ORDER", "BLOCKED_BY"):
        m = re.search(rf"(?m)^\s*{re.escape(key)}\s*:\s*(.+?)\s*$", proposal_text)
        if m:
            out[key] = m.group(1).strip()
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenSpec chain gate")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--meta-file", required=True)
    parser.add_argument("--handoff-file", required=True)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    meta_file = (repo_root / args.meta_file).resolve() if not Path(args.meta_file).is_absolute() else Path(args.meta_file)
    handoff_file = (repo_root / args.handoff_file).resolve() if not Path(args.handoff_file).is_absolute() else Path(args.handoff_file)

    if not meta_file.exists():
        print(f"[FAIL] meta file not found: {meta_file}")
        return 1
    if not handoff_file.exists():
        print(f"[FAIL] handoff file not found: {handoff_file}")
        return 1

    meta_text = meta_file.read_text(encoding="utf-8")
    handoff_text = handoff_file.read_text(encoding="utf-8")
    changed_files = [normalize_path(x) for x in parse_meta_list(meta_text, "files_changed")]

    runtime_changed = [x for x in changed_files if is_runtime_file(x)]
    openspec_changed = [x for x in changed_files if normalize_path(x).startswith("openspec/changes/")]

    violations: list[dict[str, Any]] = []

    if runtime_changed and not openspec_changed and not has_openspec_exempt(handoff_text):
        violations.append(
            {
                "type": "runtime_without_openspec",
                "message": "Runtime code changed but no openspec/changes update and no OPENSPEC-EXEMPT in handoff.",
                "runtime_changed_count": len(runtime_changed),
            }
        )

    changes_root = repo_root / "openspec" / "changes"
    if changes_root.exists():
        child_headers: dict[str, dict[str, str]] = {}
        parent_ids: set[str] = set()

        for directory in sorted(changes_root.iterdir()):
            if not directory.is_dir():
                continue
            if directory.name == "archive":
                continue

            change_id = directory.name
            is_parent = bool(PARENT_PATTERN.match(change_id))
            child_match = CHILD_PATTERN.match(change_id)
            is_child = bool(child_match)

            if change_id.startswith("refactor-") and not (is_parent or is_child):
                violations.append(
                    {
                        "type": "invalid_refactor_change_id",
                        "path": normalize_path(str(directory.relative_to(repo_root))),
                        "message": "Refactor change ID does not match parent/child naming conventions.",
                    }
                )
                continue

            if is_parent:
                parent_ids.add(change_id)
                base = f"openspec/changes/{change_id}"
                require_file(repo_root, f"{base}/proposal.md", violations, "parent proposal.md missing")
                require_file(repo_root, f"{base}/design.md", violations, "parent design.md missing")
                require_file(repo_root, f"{base}/tasks.md", violations, "parent tasks.md missing")
                require_file(repo_root, f"{base}/specs/refactor-governance/spec.md", violations, "parent spec missing")

                tasks_file = repo_root / base / "tasks.md"
                if tasks_file.exists():
                    require_task_template(tasks_file.read_text(encoding="utf-8"), PARENT_TASK_LINES, f"{base}/tasks.md", violations)

            if is_child:
                theme = child_match.group(1)
                base = f"openspec/changes/{change_id}"
                require_file(repo_root, f"{base}/proposal.md", violations, "child proposal.md missing")
                require_file(repo_root, f"{base}/design.md", violations, "child design.md missing")
                require_file(repo_root, f"{base}/tasks.md", violations, "child tasks.md missing")
                require_file(repo_root, f"{base}/specs/{theme}/spec.md", violations, "child theme spec missing")

                tasks_file = repo_root / base / "tasks.md"
                if tasks_file.exists():
                    require_task_template(tasks_file.read_text(encoding="utf-8"), CHILD_TASK_LINES, f"{base}/tasks.md", violations)

                proposal_file = repo_root / base / "proposal.md"
                if proposal_file.exists():
                    headers = parse_child_headers(proposal_file.read_text(encoding="utf-8"))
                    for key in ("PARENT_CHANGE_ID", "DEPENDENCY_ORDER", "BLOCKED_BY"):
                        if key not in headers:
                            violations.append(
                                {
                                    "type": "child_header_missing",
                                    "path": f"{base}/proposal.md",
                                    "message": f"Missing required header: {key}",
                                }
                            )
                    if "DEPENDENCY_ORDER" in headers and not re.match(r"^\d+$", headers["DEPENDENCY_ORDER"]):
                        violations.append(
                            {
                                "type": "dependency_order_invalid",
                                "path": f"{base}/proposal.md",
                                "message": "DEPENDENCY_ORDER must be an integer.",
                            }
                        )
                    child_headers[change_id] = headers

        parent_to_orders: dict[str, list[int]] = {}
        for child_id, headers in child_headers.items():
            parent = headers.get("PARENT_CHANGE_ID", "")
            if not parent:
                continue
            if parent not in parent_ids:
                violations.append(
                    {
                        "type": "parent_missing",
                        "path": f"openspec/changes/{child_id}/proposal.md",
                        "message": f"Referenced parent change does not exist: {parent}",
                    }
                )
                continue
            dep_order = headers.get("DEPENDENCY_ORDER", "")
            if dep_order.isdigit():
                parent_to_orders.setdefault(parent, []).append(int(dep_order))
            blocked_by = headers.get("BLOCKED_BY", "")
            if not blocked_by:
                violations.append(
                    {
                        "type": "blocked_by_missing",
                        "path": f"openspec/changes/{child_id}/proposal.md",
                        "message": "BLOCKED_BY must be set (use none when no dependency).",
                    }
                )

        for parent_id, orders in parent_to_orders.items():
            if len(orders) != len(set(orders)):
                violations.append(
                    {
                        "type": "duplicate_dependency_order",
                        "path": f"openspec/changes/{parent_id}",
                        "message": "Child proposals under the same parent must have unique DEPENDENCY_ORDER values.",
                    }
                )

    result = {
        "status": "PASS" if not violations else "FAIL",
        "runtime_changed": len(runtime_changed),
        "openspec_changed": len(openspec_changed),
        "violations": violations,
    }
    payload = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    print(payload)

    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())

