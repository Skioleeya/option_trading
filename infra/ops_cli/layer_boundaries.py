from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from .common import normalize_repo_path, print_fail, print_ok, repo_root
from .validation_helpers import load_policy, scan_layer_boundary_hits

_FALLBACK_ALLOWED_TOP_LEVEL = {
    "app",
    "l0_ingest",
    "l1_compute",
    "l2_decision",
    "l3_assembly",
    "l4_ui",
    "shared",
    "infra",
    "scripts",
}

_FALLBACK_EXCLUDED_PREFIXES = (
    ".git/",
    ".venv/",
    "node_modules/",
    "dist/",
    "target/",
    "tmp/",
    "logs/",
    "data/",
)


def _is_fallback_target(rel: str) -> bool:
    if not rel.endswith((".py", ".ts", ".tsx")):
        return False
    if any(rel.startswith(prefix) for prefix in _FALLBACK_EXCLUDED_PREFIXES):
        return False
    top_level = rel.split("/", 1)[0]
    return top_level in _FALLBACK_ALLOWED_TOP_LEVEL


def _tracked_targets(repo: Path) -> list[str]:
    used_git_ls_files = True
    try:
        out = subprocess.check_output(["git", "ls-files"], cwd=repo, text=True, stderr=subprocess.DEVNULL)
        files = [normalize_repo_path(line) for line in out.splitlines() if line.strip()]
    except Exception:
        used_git_ls_files = False
        files = [
            normalize_repo_path(str(path.relative_to(repo)))
            for path in repo.rglob("*")
            if path.is_file()
        ]

    targets: list[str] = []
    for rel in files:
        if not used_git_ls_files:
            if not _is_fallback_target(rel):
                continue
        elif not rel.endswith((".py", ".ts", ".tsx")):
            continue
        if not (repo / rel).exists():
            continue
        targets.append(rel)
    return targets


def run_check_layer_boundaries(args: argparse.Namespace) -> int:
    repo = repo_root()
    policy_path = Path(args.policy_path)
    if not policy_path.is_absolute():
        policy_path = repo / policy_path
    if not policy_path.exists():
        print_fail(f"Missing policy file: {policy_path}")
        return 1

    try:
        policy = load_policy(policy_path)
    except Exception:
        print_fail(f"Cannot parse policy file: {policy_path}")
        return 1

    hits = scan_layer_boundary_hits(repo, _tracked_targets(repo), policy)
    if hits:
        print_fail(f"Layer boundary violations: {len(hits)}")
        for hit in hits:
            message = hit.message or "Layer boundary violation"
            print_fail(f"{hit.path}:{hit.line} [{hit.rule_id}] {message} | {hit.excerpt}")
        return 1

    print_ok("Layer boundary scan passed (full repository)")
    return 0


def build_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("check-layer-boundaries", help="Run layer boundary scan")
    parser.add_argument("--policy-path", default="scripts/policy/layer_boundary_rules.json")
    parser.set_defaults(func=run_check_layer_boundaries)
