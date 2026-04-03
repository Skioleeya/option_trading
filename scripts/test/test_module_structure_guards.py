from __future__ import annotations

import ast
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROOTS = (
    "l0_ingest",
    "l1_compute",
    "l2_decision",
    "l3_assembly",
    "l4_ui",
    "app",
    "shared",
    "shared_rust",
    "shared_rust_models",
    "shared_rust_services",
)
SKIP_DIR_PATTERNS = (
    "/tests/",
    "/test/",
    "/__tests__/",
    "/__pycache__/",
    "/target/",
    "/node_modules/",
    "/dist/",
    "/build/",
    "/.venv/",
)

# Baseline debt set for incremental retirement.
FORBIDDEN_L1_IMPORT_ALLOWLIST = {
    "l1_compute/compute/gpu_greeks_kernel.py",
    "l1_compute/reactor.py",
}

PURE_SHIM_ALLOWLIST = {
    "l1_compute/arrow/schema.py",
    "l2_decision/feature_store/extractors.py",
}

FORBIDDEN_FLOW_COMPAT_PATHS = {
    "l2_decision/signals/flow/__init__.py",
    "l2_decision/signals/flow/deg_composer.py",
    "l2_decision/signals/flow/flow_engine_d.py",
    "l2_decision/signals/flow/flow_engine_e.py",
    "l2_decision/signals/flow/flow_engine_g.py",
}


def _is_runtime_file(path: Path) -> bool:
    rel = path.relative_to(REPO_ROOT).as_posix()
    if path.suffix not in (".py", ".rs"):
        return False
    if not rel.startswith(RUNTIME_ROOTS):
        return False
    return not any(pat in rel for pat in SKIP_DIR_PATTERNS)


def _iter_runtime_files() -> list[Path]:
    files: list[Path] = []
    for root in RUNTIME_ROOTS:
        root_path = REPO_ROOT / root
        if not root_path.exists():
            continue
        for file_path in root_path.rglob("*"):
            if file_path.is_file() and _is_runtime_file(file_path):
                files.append(file_path)
    return sorted(files, key=lambda p: p.as_posix())


def _count_lines(path: Path) -> int:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return len(text.splitlines())


def test_runtime_source_file_length_max_400() -> None:
    violations: list[str] = []
    for path in _iter_runtime_files():
        lines = _count_lines(path)
        if lines > 400:
            rel = path.relative_to(REPO_ROOT).as_posix()
            violations.append(f"{rel}: {lines}")
    assert not violations, "Runtime source files exceed 400 lines:\n" + "\n".join(violations)


def test_l1_forbidden_numeric_imports_are_not_expanding() -> None:
    forbidden = re.compile(r"^\s*(import\s+numpy\b|from\s+scipy\b|import\s+numba\b|import\s+cupy\b)", re.M)
    hits: set[str] = set()
    l1_root = REPO_ROOT / "l1_compute"
    for path in l1_root.rglob("*.py"):
        rel = path.relative_to(REPO_ROOT).as_posix()
        if any(pat in rel for pat in SKIP_DIR_PATTERNS):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if forbidden.search(text):
            hits.add(rel)

    unexpected = sorted(hits - FORBIDDEN_L1_IMPORT_ALLOWLIST)
    assert not unexpected, "New forbidden L1 numeric imports detected:\n" + "\n".join(unexpected)


def _is_pure_shim(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="ignore")
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return False

    has_import = False
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            has_import = True
            continue
        if isinstance(node, ast.Assign):
            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if "__all__" in targets:
                continue
            return False
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            continue
        return False
    return has_import


def test_no_new_pure_shims_in_runtime_python() -> None:
    pure_shims: set[str] = set()
    for path in _iter_runtime_files():
        if path.suffix != ".py":
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel.endswith("__init__.py"):
            continue
        if _is_pure_shim(path):
            pure_shims.add(rel)

    unexpected = sorted(pure_shims - PURE_SHIM_ALLOWLIST)
    assert not unexpected, "New pure shim files detected:\n" + "\n".join(unexpected)


def test_flow_compat_modules_removed() -> None:
    present = [
        rel_path
        for rel_path in sorted(FORBIDDEN_FLOW_COMPAT_PATHS)
        if (REPO_ROOT / rel_path).exists()
    ]
    assert not present, "Flow compatibility modules must be removed:\n" + "\n".join(present)
