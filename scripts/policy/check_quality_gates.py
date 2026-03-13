#!/usr/bin/env python3
"""Institutional quality gate for changed Python runtime files.

Checks changed runtime files recorded in session meta.yaml against static thresholds:
- nesting depth
- cyclomatic complexity (approximation)
- function/class length
- magic number governance ratio
- duplicate code windows
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass
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

SKIP_PATTERNS = (
    "/tests/",
    "/test/",
    "/__tests__/",
    "/__pycache__/",
    "/node_modules/",
    "/dist/",
    "/build/",
)


@dataclass
class FunctionMetrics:
    name: str
    lineno: int
    end_lineno: int
    length: int
    max_nesting: int
    cyclomatic_complexity: int
    is_hot_path: bool


@dataclass
class ClassMetrics:
    name: str
    lineno: int
    end_lineno: int
    length: int


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


def is_runtime_python_file(path: str) -> bool:
    norm = normalize_path(path)
    if not norm.endswith(".py"):
        return False
    if not norm.startswith(RUNTIME_PREFIXES):
        return False
    return not any(pat in norm for pat in SKIP_PATTERNS)


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    parent_map: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parent_map[child] = parent
    return parent_map


def _extract_nested_bodies(node: ast.AST) -> list[list[ast.stmt]]:
    out: list[list[ast.stmt]] = []
    if isinstance(node, (ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith)):
        out.append(node.body)
        if node.orelse:
            out.append(node.orelse)
    elif isinstance(node, ast.If):
        out.append(node.body)
        if node.orelse:
            out.append(node.orelse)
    elif isinstance(node, ast.Try):
        out.append(node.body)
        if node.orelse:
            out.append(node.orelse)
        if node.finalbody:
            out.append(node.finalbody)
        for handler in node.handlers:
            out.append(handler.body)
    elif isinstance(node, ast.Match):
        for case in node.cases:
            out.append(case.body)
    return out


def max_nesting_depth(stmts: list[ast.stmt], depth: int = 0) -> int:
    max_depth = depth
    for stmt in stmts:
        max_depth = max(max_depth, depth)
        for body in _extract_nested_bodies(stmt):
            max_depth = max(max_depth, max_nesting_depth(body, depth + 1))
    return max_depth


def cyclomatic_complexity(node: ast.AST) -> int:
    score = 1
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.IfExp, ast.ExceptHandler, ast.With, ast.AsyncWith)):
            score += 1
        elif isinstance(child, ast.BoolOp):
            score += max(0, len(child.values) - 1)
        elif isinstance(child, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            for gen in child.generators:
                score += 1 + len(gen.ifs)
        elif isinstance(child, ast.Match):
            score += max(1, len(child.cases))
    return score


def is_hot_path(name: str, patterns: list[str]) -> bool:
    for pat in patterns:
        if re.search(pat, name):
            return True
    return False


def _numeric_from_constant(node: ast.AST) -> float | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        operand = node.operand
        if isinstance(operand, ast.Constant) and isinstance(operand.value, (int, float)) and not isinstance(operand.value, bool):
            return -float(operand.value)
    return None


def _is_exempt_magic(value: float, exempt: list[float]) -> bool:
    return any(abs(value - x) <= 1e-12 for x in exempt)


def _is_governed_literal(node: ast.AST, parent_map: dict[ast.AST, ast.AST]) -> bool:
    parent = parent_map.get(node)
    while parent is not None:
        if isinstance(parent, ast.Assign):
            if parent.value is node:
                for target in parent.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        return True
            break
        if isinstance(parent, ast.AnnAssign):
            if parent.value is node and isinstance(parent.target, ast.Name) and parent.target.id.isupper():
                return True
            break
        if isinstance(parent, (ast.Return, ast.Call, ast.BinOp, ast.Compare, ast.BoolOp, ast.If, ast.For, ast.While, ast.With, ast.Assert, ast.Expr)):
            break
        parent = parent_map.get(parent)
    return False


def analyze_python_file(path: Path, cfg: dict[str, Any]) -> tuple[list[FunctionMetrics], list[ClassMetrics], dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    parent_map = build_parent_map(tree)

    functions: list[FunctionMetrics] = []
    classes: list[ClassMetrics] = []

    hot_patterns = cfg.get("hot_path_name_patterns", [])

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end_lineno = getattr(node, "end_lineno", node.lineno)
            length = end_lineno - node.lineno + 1
            nesting = max_nesting_depth(node.body, 0)
            cc = cyclomatic_complexity(node)
            functions.append(
                FunctionMetrics(
                    name=node.name,
                    lineno=node.lineno,
                    end_lineno=end_lineno,
                    length=length,
                    max_nesting=nesting,
                    cyclomatic_complexity=cc,
                    is_hot_path=is_hot_path(node.name, hot_patterns),
                )
            )
        elif isinstance(node, ast.ClassDef):
            end_lineno = getattr(node, "end_lineno", node.lineno)
            classes.append(
                ClassMetrics(
                    name=node.name,
                    lineno=node.lineno,
                    end_lineno=end_lineno,
                    length=end_lineno - node.lineno + 1,
                )
            )

    exempt_values = [float(x) for x in cfg.get("magic_number_exempt_values", [0, 1, -1])]
    total_business_magic = 0
    governed_business_magic = 0

    for node in ast.walk(tree):
        numeric = _numeric_from_constant(node)
        if numeric is None:
            continue
        if _is_exempt_magic(numeric, exempt_values):
            continue
        total_business_magic += 1
        if _is_governed_literal(node, parent_map):
            governed_business_magic += 1

    magic_ratio = 1.0
    if total_business_magic > 0:
        magic_ratio = governed_business_magic / total_business_magic

    return functions, classes, {
        "magic_total": total_business_magic,
        "magic_governed": governed_business_magic,
        "magic_ratio": magic_ratio,
    }


def normalize_line(line: str) -> str:
    no_comment = line.split("#", 1)[0].strip()
    return re.sub(r"\s+", " ", no_comment)


def count_duplicate_windows(files: list[Path], window_size: int) -> tuple[int, list[dict[str, Any]]]:
    windows: dict[str, list[tuple[str, int]]] = {}
    for path in files:
        lines = path.read_text(encoding="utf-8").splitlines()
        normalized = [normalize_line(line) for line in lines]
        for i in range(0, max(0, len(normalized) - window_size + 1)):
            window = normalized[i : i + window_size]
            if any(not x for x in window):
                continue
            if all(x.startswith("import ") or x.startswith("from ") for x in window):
                continue
            key = "\n".join(window)
            windows.setdefault(key, []).append((normalize_path(str(path)), i + 1))

    dup_entries: list[dict[str, Any]] = []
    for key, locs in windows.items():
        if len(locs) < 2:
            continue
        dup_entries.append(
            {
                "occurrences": len(locs),
                "locations": [{"file": f, "line": ln} for f, ln in locs[:6]],
                "preview": key.split("\n")[:2],
            }
        )

    return len(dup_entries), dup_entries[:10]


def main() -> int:
    parser = argparse.ArgumentParser(description="Quality gate for changed Python runtime files")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--config", default="scripts/policy/quality_thresholds.json")
    parser.add_argument("--meta-file", required=True)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    meta_file = (repo_root / args.meta_file).resolve() if not Path(args.meta_file).is_absolute() else Path(args.meta_file)
    cfg_file = (repo_root / args.config).resolve() if not Path(args.config).is_absolute() else Path(args.config)

    if not meta_file.exists():
        print(f"[FAIL] meta file not found: {meta_file}")
        return 1
    if not cfg_file.exists():
        print(f"[FAIL] quality config not found: {cfg_file}")
        return 1

    cfg = load_config(cfg_file)
    meta_text = meta_file.read_text(encoding="utf-8")
    changed_files = [normalize_path(p) for p in parse_meta_list(meta_text, "files_changed")]

    target_files: list[Path] = []
    for rel in changed_files:
        if is_runtime_python_file(rel):
            full = (repo_root / rel).resolve()
            if full.exists():
                target_files.append(full)

    summary: dict[str, Any] = {
        "status": "PASS",
        "targets": [normalize_path(str(p.relative_to(repo_root))) for p in target_files],
        "violations": [],
        "metrics": {},
    }

    if not target_files:
        summary["metrics"] = {"analyzed_python_runtime_files": 0}
        payload = json.dumps(summary, indent=2, ensure_ascii=False)
        if args.output:
            Path(args.output).write_text(payload, encoding="utf-8")
        print(payload)
        return 0

    max_fn_len = int(cfg.get("max_function_length", 80))
    max_cls_len = int(cfg.get("max_class_length", 400))
    max_depth = int(cfg.get("max_nesting_depth", 3))
    hot_max_depth = int(cfg.get("hot_max_nesting_depth", 2))
    max_cc = int(cfg.get("max_cyclomatic_complexity", 10))
    hot_max_cc = int(cfg.get("hot_max_cyclomatic_complexity", 8))
    min_magic_ratio = float(cfg.get("magic_number_min_governance_ratio", 0.8))

    total_magic = 0
    total_magic_governed = 0
    function_count = 0
    class_count = 0

    for path in target_files:
        rel = normalize_path(str(path.relative_to(repo_root)))
        try:
            functions, classes, magic_info = analyze_python_file(path, cfg)
        except SyntaxError as exc:
            summary["violations"].append(
                {
                    "type": "syntax_error",
                    "file": rel,
                    "line": exc.lineno,
                    "message": str(exc),
                }
            )
            continue

        function_count += len(functions)
        class_count += len(classes)
        total_magic += int(magic_info["magic_total"])
        total_magic_governed += int(magic_info["magic_governed"])

        for fn in functions:
            depth_limit = hot_max_depth if fn.is_hot_path else max_depth
            cc_limit = hot_max_cc if fn.is_hot_path else max_cc

            if fn.length > max_fn_len:
                summary["violations"].append(
                    {
                        "type": "function_length",
                        "file": rel,
                        "line": fn.lineno,
                        "symbol": fn.name,
                        "actual": fn.length,
                        "limit": max_fn_len,
                    }
                )
            if fn.max_nesting > depth_limit:
                summary["violations"].append(
                    {
                        "type": "nesting_depth",
                        "file": rel,
                        "line": fn.lineno,
                        "symbol": fn.name,
                        "actual": fn.max_nesting,
                        "limit": depth_limit,
                        "hot_path": fn.is_hot_path,
                    }
                )
            if fn.cyclomatic_complexity > cc_limit:
                summary["violations"].append(
                    {
                        "type": "cyclomatic_complexity",
                        "file": rel,
                        "line": fn.lineno,
                        "symbol": fn.name,
                        "actual": fn.cyclomatic_complexity,
                        "limit": cc_limit,
                        "hot_path": fn.is_hot_path,
                    }
                )

        for cls in classes:
            if cls.length > max_cls_len:
                summary["violations"].append(
                    {
                        "type": "class_length",
                        "file": rel,
                        "line": cls.lineno,
                        "symbol": cls.name,
                        "actual": cls.length,
                        "limit": max_cls_len,
                    }
                )

    duplicate_window_size = int(cfg.get("duplicate_window_size", 12))
    max_duplicate_windows = int(cfg.get("max_duplicate_windows", 0))
    duplicate_windows, duplicate_examples = count_duplicate_windows(target_files, duplicate_window_size)
    if duplicate_windows > max_duplicate_windows:
        summary["violations"].append(
            {
                "type": "duplicate_windows",
                "actual": duplicate_windows,
                "limit": max_duplicate_windows,
                "window_size": duplicate_window_size,
                "examples": duplicate_examples,
            }
        )

    magic_ratio = 1.0 if total_magic == 0 else total_magic_governed / total_magic
    if magic_ratio < min_magic_ratio:
        summary["violations"].append(
            {
                "type": "magic_number_governance_ratio",
                "actual": round(magic_ratio, 4),
                "limit": min_magic_ratio,
                "magic_total": total_magic,
                "magic_governed": total_magic_governed,
            }
        )

    summary["metrics"] = {
        "analyzed_python_runtime_files": len(target_files),
        "function_count": function_count,
        "class_count": class_count,
        "magic_total": total_magic,
        "magic_governed": total_magic_governed,
        "magic_ratio": round(magic_ratio, 4),
        "duplicate_windows": duplicate_windows,
    }

    if summary["violations"]:
        summary["status"] = "FAIL"

    payload = json.dumps(summary, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    print(payload)

    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
