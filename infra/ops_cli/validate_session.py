from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .common import normalize_repo_path, print_fail, print_ok, read_text_utf8, repo_root
from .validation_helpers import (
    Hit,
    get_handoff_field,
    get_meta_list_items,
    get_runtime_source_targets,
    get_unchecked_open_task_items,
    load_policy,
    read_active_session_path,
    scan_anti_pattern_hits,
    scan_layer_boundary_hits,
)


@dataclass
class Reporter:
    has_error: bool = False

    def pass_(self, message: str) -> None:
        print_ok(message)

    def fail(self, message: str) -> None:
        print_fail(message)
        self.has_error = True


def _require_key(text: str, pattern: str, label: str, reporter: Reporter) -> None:
    if re.search(pattern, text, flags=re.MULTILINE):
        reporter.pass_(f"meta.yaml has {label}")
    else:
        reporter.fail(f"meta.yaml missing or empty: {label}")


def _report_hits(hits: list[Hit], header: str, reporter: Reporter, max_report: int = 20) -> None:
    if not hits:
        return
    reporter.fail(f"{header} ({len(hits)} hit(s))")
    for hit in hits[:max_report]:
        rule_id = hit.rule_id or "RULE"
        message = hit.message or "Violation"
        reporter.fail(f"  {rule_id} @ {hit.path}:{hit.line} -> {message} | {hit.excerpt}")
    if len(hits) > max_report:
        reporter.fail(f"  ... {len(hits) - max_report} more violation(s) not shown")


def _parse_int(raw: str | None, field: str, reporter: Reporter) -> int | None:
    if raw is None or raw.strip() == "":
        reporter.fail(f"Debt gate: {field} missing")
        return None
    try:
        return int(raw.strip())
    except ValueError:
        reporter.fail(f"Debt gate: {field} must be integer")
        return None


def _run_python_script(cmd: list[str], success_message: str, fail_message: str, reporter: Reporter) -> None:
    proc = subprocess.run(cmd, check=False)
    if proc.returncode == 0:
        reporter.pass_(success_message)
    else:
        reporter.fail(fail_message)


def run_validate_session(args: argparse.Namespace) -> int:
    reporter = Reporter()
    repo = repo_root()

    context_project = repo / "notes/context/project_state.md"
    context_tasks = repo / "notes/context/open_tasks.md"
    context_handoff = repo / "notes/context/handoff.md"

    try:
        active_session_path = read_active_session_path(context_project)
    except Exception as exc:
        print_fail(str(exc))
        return 1

    session_path = args.session_path or active_session_path
    is_active_session = session_path == active_session_path
    enforce_debt_gate = is_active_session or args.strict

    session_dir = repo / session_path
    if not session_dir.exists():
        print_fail(f"Session directory not found: {session_path}")
        return 1

    print(f"Validating session: {session_path}")
    if args.strict:
        print("Mode: STRICT")

    for filename in ("project_state.md", "open_tasks.md", "handoff.md", "meta.yaml"):
        path = session_dir / filename
        if path.exists():
            reporter.pass_(f"{filename} exists")
        else:
            reporter.fail(f"{filename} missing")

    meta_path = session_dir / "meta.yaml"
    handoff_path = session_dir / "handoff.md"
    open_tasks_path = session_dir / "open_tasks.md"

    meta_text = read_text_utf8(meta_path)
    handoff_text = read_text_utf8(handoff_path)

    if meta_path.exists():
        _require_key(meta_text, r'^session_id:\s*".+?"\s*$', "session_id", reporter)
        _require_key(meta_text, r'^branch:\s*".+?"\s*$', "branch", reporter)
        _require_key(meta_text, r'^base_commit:\s*".+?"\s*$', "base_commit", reporter)
        _require_key(meta_text, r'^head_commit:\s*".+?"\s*$', "head_commit", reporter)
        _require_key(meta_text, r"^tests_passed:\s*.*$", "tests_passed", reporter)

    changed_files = get_meta_list_items(meta_text, "files_changed")
    commands = get_meta_list_items(meta_text, "commands")
    tests_passed = get_meta_list_items(meta_text, "tests_passed")

    if args.strict:
        reporter.pass_("Strict gate: files_changed is non-empty") if changed_files else reporter.fail(
            "Strict gate: files_changed must be non-empty"
        )
        reporter.pass_("Strict gate: commands is non-empty") if commands else reporter.fail(
            "Strict gate: commands must be non-empty"
        )
        reporter.pass_("Strict gate: tests_passed is non-empty") if tests_passed else reporter.fail(
            "Strict gate: tests_passed must be non-empty"
        )

        strict_cmd = any(re.search(r"(?i)manage\.py\s+validate-session\s+--strict", cmd) for cmd in commands)
        if strict_cmd:
            reporter.pass_("Strict gate: commands include strict validation evidence")
        else:
            reporter.fail("Strict gate: commands must include strict validation evidence")

        strict_in_handoff = bool(re.search(r"(?im)manage\.py\s+validate-session\s+--strict", handoff_text))
        if strict_in_handoff:
            reporter.pass_("Strict gate: handoff includes strict validation record")
        else:
            reporter.fail("Strict gate: handoff must include strict validation record")

    if is_active_session:
        project_text = read_text_utf8(context_project)
        tasks_text = read_text_utf8(context_tasks)
        handoff_index_text = read_text_utf8(context_handoff)

        ptrs = {
            "project_state index pointer": [f"- Path: {session_path}/project_state.md", f"- Path: `{session_path}/project_state.md`"],
            "project_state meta pointer": [f"- Meta: {session_path}/meta.yaml", f"- Meta: `{session_path}/meta.yaml`"],
            "open_tasks index pointer": [f"- Path: {session_path}/open_tasks.md", f"- Path: `{session_path}/open_tasks.md`"],
            "handoff index pointer": [f"- Path: {session_path}/handoff.md", f"- Path: `{session_path}/handoff.md`"],
            "handoff meta pointer": [f"- Meta: {session_path}/meta.yaml", f"- Meta: `{session_path}/meta.yaml`"],
        }

        checks = {
            "project_state index pointer": project_text,
            "project_state meta pointer": project_text,
            "open_tasks index pointer": tasks_text,
            "handoff index pointer": handoff_index_text,
            "handoff meta pointer": handoff_index_text,
        }
        for label, options in ptrs.items():
            text = checks[label]
            if any(option in text for option in options):
                reporter.pass_(f"{label} OK")
            else:
                reporter.fail(f"{label} mismatch")
    else:
        reporter.pass_("Pointer checks skipped (validating non-active session)")

    runtime_regex = re.compile(r"^(l0_ingest|l1_compute|l2_decision|l3_assembly|l4_ui|app)/")
    runtime_changed = [
        item
        for item in changed_files
        if runtime_regex.search(normalize_repo_path(item))
        and not re.search(r"^docs/|^notes/", normalize_repo_path(item))
        and not re.search(r"/tests?/|/__tests__/", normalize_repo_path(item))
    ]
    sop_changed = [item for item in changed_files if normalize_repo_path(item).startswith("docs/SOP/")]
    has_sop_exempt = bool(re.search(r"(?im)^\s*SOP-EXEMPT\s*:\s*.+$", handoff_text))

    if runtime_changed:
        if sop_changed:
            reporter.pass_("SOP sync gate OK (docs/SOP updated)")
        elif has_sop_exempt:
            reporter.pass_("SOP sync gate OK (SOP-EXEMPT present in handoff.md)")
        else:
            reporter.fail("SOP sync gate failed: runtime files changed but no docs/SOP update and no SOP-EXEMPT in handoff.md")
    else:
        reporter.pass_("SOP sync gate skipped (no runtime-layer files changed)")

    if args.strict:
        policy_path = repo / "scripts/policy/layer_boundary_rules.json"
        if not policy_path.exists():
            reporter.fail(f"Architecture policy file missing: {policy_path}")
        else:
            policy = load_policy(policy_path)
            changed_arch_targets = [x for x in runtime_changed if re.search(r"\.(py|ts|tsx|rs)$", normalize_repo_path(x))]
            if changed_arch_targets:
                _report_hits(
                    scan_layer_boundary_hits(repo, changed_arch_targets, policy),
                    "Strict gate: architecture anti-coupling violations detected in changed files",
                    reporter,
                )
                if not reporter.has_error:
                    reporter.pass_("Strict gate: architecture anti-coupling scan passed (changed files)")
            else:
                reporter.pass_("Strict gate: architecture anti-coupling scan skipped for changed files (none)")

            if args.full_repo_architecture_scan:
                full_hits = scan_layer_boundary_hits(repo, get_runtime_source_targets(repo), policy)
                _report_hits(full_hits, "Strict gate: full-repo architecture anti-coupling violations detected", reporter, max_report=40)
                if not full_hits:
                    reporter.pass_("Strict gate: full-repo architecture anti-coupling scan passed")
            else:
                reporter.pass_("Strict gate: full-repo architecture scan skipped by default (use --full-repo-architecture-scan)")

        anti_targets = [x for x in runtime_changed if re.search(r"\.(py|rs)$", normalize_repo_path(x))]
        if anti_targets:
            anti_hits = scan_anti_pattern_hits(repo, anti_targets)
            _report_hits(anti_hits, "Strict gate: anti-pattern violations detected in changed runtime files", reporter)
            if not anti_hits:
                reporter.pass_("Strict gate: anti-pattern scan passed (changed runtime files)")
        else:
            reporter.pass_("Strict gate: anti-pattern scan skipped (no changed .py/.rs runtime files)")

        diag_dir = repo / "tmp/session_validation_diag"
        diag_dir.mkdir(parents=True, exist_ok=True)

        quality_script = repo / "scripts/policy/check_quality_gates.py"
        if not quality_script.exists():
            reporter.fail(f"Strict gate: quality gate script missing ({quality_script})")
        else:
            quality_out = diag_dir / "quality_gate.json"
            quality_targets = [
                x
                for x in changed_files
                if runtime_regex.search(normalize_repo_path(x))
                and re.search(r"\.(py|rs)$", normalize_repo_path(x))
                and not re.search(r"/tests?/|/__tests__/", normalize_repo_path(x))
            ]
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as tmp:
                tmp.write("files_changed:\n")
                for entry in sorted(set(quality_targets)):
                    tmp.write(f'  - "{entry.replace(chr(34), r"\\\"")}"\n')
                tmp_meta = Path(tmp.name)

            _run_python_script(
                [
                    sys.executable,
                    str(quality_script),
                    "--repo-root",
                    str(repo),
                    "--config",
                    str(repo / "scripts/policy/quality_thresholds.json"),
                    "--meta-file",
                    str(tmp_meta),
                    "--output",
                    str(quality_out),
                ],
                "Strict gate: quality thresholds passed (changed Python/Rust runtime files)",
                f"Strict gate: quality thresholds failed (see {quality_out})",
                reporter,
            )
            tmp_meta.unlink(missing_ok=True)

        openspec_script = repo / "scripts/policy/check_openspec_chain.py"
        if not openspec_script.exists():
            reporter.fail(f"Strict gate: openspec chain script missing ({openspec_script})")
        else:
            openspec_out = diag_dir / "openspec_gate.json"
            _run_python_script(
                [
                    sys.executable,
                    str(openspec_script),
                    "--repo-root",
                    str(repo),
                    "--meta-file",
                    str(meta_path),
                    "--handoff-file",
                    str(handoff_path),
                    "--output",
                    str(openspec_out),
                ],
                "Strict gate: openspec parent/child gate passed",
                f"Strict gate: openspec parent/child gate failed (see {openspec_out})",
                reporter,
            )
    else:
        reporter.pass_("Architecture anti-coupling gate skipped (run with --strict)")

    if args.strict:
        artifact_hits = [
            p
            for p in changed_files
            if re.search(r"^logs/", normalize_repo_path(p))
            or re.search(r"^data/atm_decay/atm[^/]*\.json$", normalize_repo_path(p))
        ]
        if artifact_hits:
            artifact_exempt = get_handoff_field(handoff_text, "RUNTIME-ARTIFACT-EXEMPT")
            if artifact_exempt:
                reporter.pass_("Strict gate: runtime artifact exemption present")
            else:
                reporter.fail(
                    "Strict gate: runtime artifacts detected in files_changed but RUNTIME-ARTIFACT-EXEMPT missing. "
                    + f"Files: {', '.join(artifact_hits)}"
                )
        else:
            reporter.pass_("Strict gate: no runtime artifacts in files_changed")

    if enforce_debt_gate:
        unchecked_items = get_unchecked_open_task_items(open_tasks_path)
        debt_fields = {name: get_handoff_field(handoff_text, name) for name in [
            "DEBT-EXEMPT", "DEBT-OWNER", "DEBT-DUE", "DEBT-RISK", "DEBT-NEW", "DEBT-CLOSED", "DEBT-DELTA", "DEBT-JUSTIFICATION"
        ]}

        if unchecked_items:
            for field in ("DEBT-EXEMPT", "DEBT-OWNER", "DEBT-DUE", "DEBT-RISK"):
                reporter.pass_(f"Debt gate: {field} present") if debt_fields[field] else reporter.fail(f"Debt gate: {field} missing")
        else:
            reporter.pass_("Debt gate: no unchecked tasks")

        debt_new = _parse_int(debt_fields["DEBT-NEW"], "DEBT-NEW", reporter)
        debt_closed = _parse_int(debt_fields["DEBT-CLOSED"], "DEBT-CLOSED", reporter)
        debt_delta = _parse_int(debt_fields["DEBT-DELTA"], "DEBT-DELTA", reporter)
        if debt_new is not None and debt_closed is not None and debt_delta is not None:
            if debt_delta != (debt_new - debt_closed):
                reporter.fail("Debt gate: DEBT-DELTA must equal DEBT-NEW - DEBT-CLOSED")
            else:
                reporter.pass_("Debt gate: DEBT metrics arithmetic OK")
            if debt_delta > 0 and not debt_fields["DEBT-JUSTIFICATION"]:
                reporter.fail("Debt gate: DEBT-DELTA > 0 requires DEBT-JUSTIFICATION")

        if unchecked_items and debt_fields["DEBT-DUE"]:
            try:
                due_date = dt.datetime.strptime(debt_fields["DEBT-DUE"], "%Y-%m-%d").date()
            except ValueError:
                reporter.fail("Debt gate: DEBT-DUE must be YYYY-MM-DD")
                due_date = None

            if due_date is not None:
                today = dt.date.today()
                if due_date < today:
                    reporter.fail("Debt gate: DEBT-DUE is overdue")

                has_p0 = any(re.match(r"^\s*P0\s*:", str(item["item"])) for item in unchecked_items)
                has_p1 = any(re.match(r"^\s*P1\s*:", str(item["item"])) for item in unchecked_items)
                max_days = 0 if has_p0 else (2 if has_p1 else 5)
                if due_date > today + dt.timedelta(days=max_days):
                    reporter.fail("Debt gate: DEBT-DUE exceeds SLA window for target priority")
                else:
                    reporter.pass_("Debt gate: DEBT-DUE within SLA window")

        if unchecked_items:
            all_debt_items: list[str] = []
            for task_file in (repo / "notes/sessions").rglob("open_tasks.md"):
                for row in get_unchecked_open_task_items(task_file):
                    all_debt_items.append(str(row["item"]).strip().lower())
            duplicate_debt = {item for item in all_debt_items if all_debt_items.count(item) > 1}
            if duplicate_debt:
                reporter.fail("Debt gate: duplicate unresolved debt entries found across sessions without supersede marker")
            else:
                reporter.pass_("Debt gate: no duplicate unresolved debt entries")
        else:
            reporter.pass_("Debt gate: duplicate unresolved debt scan skipped (no unchecked tasks in active session)")
    else:
        reporter.pass_("Debt gate skipped (validating non-active session in non-strict mode)")

    if reporter.has_error:
        print_fail("Session validation failed.")
        return 1

    print_ok("Session validation passed.")
    return 0


def build_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("validate-session", help="Validate session records and strict gates")
    parser.add_argument("--session-path", default="")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--full-repo-architecture-scan", action="store_true")
    parser.set_defaults(func=run_validate_session)
