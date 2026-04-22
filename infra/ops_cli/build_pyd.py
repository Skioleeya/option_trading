from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

from .common import ensure_dir, repo_root


CRATE_MANIFESTS: dict[str, str] = {
    "shared_rust_services": "shared_rust_services/Cargo.toml",
    "shared_rust_contracts": "shared_rust/Cargo.toml",
    "shared_rust_models": "shared_rust_models/Cargo.toml",
    "shared_rust_l0_support": "shared_rust_l0_support/Cargo.toml",
    "l0_rust": "l0_ingest/l0_rust/Cargo.toml",
    "l1_rust": "l1_compute/l1_rust/Cargo.toml",
    "rust_kernel": "rust_kernel/Cargo.toml",
}


def _workspace_cargo_env(repo: Path) -> dict[str, str]:
    env = os.environ.copy()
    cargo_home = repo / "tmp" / "cargo_home"
    cargo_target = repo / "tmp" / "cargo_target"
    ensure_dir(cargo_home)
    ensure_dir(cargo_target)
    env["CARGO_HOME"] = str(cargo_home)
    env["CARGO_TARGET_DIR"] = str(cargo_target)
    return env


def _selected_crates(args: argparse.Namespace) -> list[str]:
    if args.all:
        return list(CRATE_MANIFESTS.keys())
    if args.crate:
        unknown = [name for name in args.crate if name not in CRATE_MANIFESTS]
        if unknown:
            raise ValueError(f"Unknown crate(s): {', '.join(unknown)}")
        return args.crate
    return list(CRATE_MANIFESTS.keys())


def _run_cargo_for_crate(repo: Path, env: dict[str, str], crate: str, command: str, profile: str) -> int:
    manifest = repo / CRATE_MANIFESTS[crate]
    if not manifest.exists():
        print(f"[build-pyd] skip: manifest missing for {crate} -> {manifest}")
        return 0

    cmd = ["cargo", command, "--manifest-path", str(manifest)]
    if command == "build" and profile == "release":
        cmd.append("--release")

    print(f"[build-pyd] crate={crate} cmd={' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=repo, env=env, check=False)
    if proc.returncode != 0:
        print(f"[build-pyd] failed: crate={crate} exit={proc.returncode}")
    else:
        print(f"[build-pyd] passed: crate={crate}")
    return proc.returncode


def _extension_suffix() -> str:
    suffix = sysconfig.get_config_var("EXT_SUFFIX")
    if isinstance(suffix, str) and suffix:
        return suffix
    return ".pyd"


def _package_init(module_name: str) -> str:
    return (
        f"from .{module_name} import *\n\n"
        f"__doc__ = {module_name}.__doc__\n"
        f"if hasattr({module_name}, \"__all__\"):\n"
        f"    __all__ = {module_name}.__all__\n"
    )


def _venv_site_packages(repo: Path) -> Path:
    venv_purelib = repo / ".venv" / "Lib" / "site-packages"
    if venv_purelib.exists():
        return venv_purelib
    return Path(sysconfig.get_paths()["purelib"])


def _install_paths(repo: Path, crate: str) -> list[Path]:
    ext_suffix = _extension_suffix()
    site_packages = _venv_site_packages(repo)
    mapping: dict[str, list[Path]] = {
        "shared_rust_contracts": [repo / "shared_rust" / "contracts.pyd"],
        "shared_rust_models": [repo / "shared_rust" / "models.pyd"],
        "shared_rust_services": [repo / "shared_rust" / "services.pyd"],
        "shared_rust_l0_support": [repo / "shared_rust" / "services_l0_support.pyd"],
        "l0_rust": [
            repo / "shared" / "services" / "l0_runtime" / "_native_generated" / "l0_rust.pyd",
            repo / "shared" / "services" / "l0_runtime" / "_native_generated" / "wave10" / "l0_rust.pyd",
        ],
        "l1_rust": [site_packages / "l1_rust" / f"l1_rust{ext_suffix}"],
        "rust_kernel": [site_packages / "rust_kernel" / f"rust_kernel{ext_suffix}"],
    }
    return mapping.get(crate, [])


def _source_artifact(repo: Path, crate: str, profile: str) -> Path:
    suffix = ".dll" if os.name == "nt" else ".so"
    if crate == "shared_rust_contracts":
        name = "contracts"
    elif crate == "shared_rust_models":
        name = "models"
    elif crate == "shared_rust_services":
        name = "services"
    elif crate == "shared_rust_l0_support":
        name = "services_l0_support"
    else:
        name = crate
    return repo / "tmp" / "cargo_target" / profile / f"{name}{suffix}"


def _write_package_init_if_needed(dest: Path) -> None:
    package_dir = dest.parent
    init_path = package_dir / "__init__.py"
    module_name = package_dir.name
    if module_name not in {"l1_rust", "rust_kernel"}:
        return
    if not init_path.exists():
        init_path.write_text(_package_init(module_name), encoding="utf-8")


def _install_artifact(repo: Path, crate: str, profile: str) -> int:
    source = _source_artifact(repo, crate, profile)
    if not source.exists():
        print(f"[build-pyd] install skip: built artifact missing for {crate} -> {source}")
        return 1

    targets = _install_paths(repo, crate)
    if not targets:
        print(f"[build-pyd] install skip: no runtime install path configured for {crate}")
        return 0

    failures = 0
    for dest in targets:
        dest.parent.mkdir(parents=True, exist_ok=True)
        _write_package_init_if_needed(dest)
        try:
            shutil.copy2(source, dest)
            print(f"[build-pyd] installed: {crate} -> {dest}")
        except OSError as exc:
            failures += 1
            print(f"[build-pyd] install failed: {crate} -> {dest} ({exc})")
    return 0 if failures == 0 else 1


def run_build_pyd(args: argparse.Namespace) -> int:
    if os.name != "nt":
        print("[build-pyd] Windows-only runtime contract violation: run this command on Windows host.")
        return 1

    repo = repo_root()
    os.chdir(repo)
    env = _workspace_cargo_env(repo)

    print(f"[build-pyd] repo={repo}")
    print(f"[build-pyd] CARGO_HOME={env['CARGO_HOME']}")
    print(f"[build-pyd] CARGO_TARGET_DIR={env['CARGO_TARGET_DIR']}")

    command = "check" if args.check else "build"
    profile = args.profile

    try:
        crates = _selected_crates(args)
    except ValueError as exc:
        print(f"[build-pyd] {exc}")
        return 1

    failures = 0
    for crate in crates:
        code = _run_cargo_for_crate(repo, env, crate, command, profile)
        if code != 0:
            failures += 1
            if args.stop_on_error:
                return code
            continue
        if command == "build":
            install_code = _install_artifact(repo, crate, profile)
            if install_code != 0:
                failures += 1
                if args.stop_on_error:
                    return install_code

    if failures:
        return 1
    print("[build-pyd] all selected crates passed")
    return 0


def build_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("build-pyd", help="Build Rust .pyd owners with workspace-local cargo dirs")
    parser.add_argument("--all", action="store_true", help="Build all configured crates (default when --crate absent)")
    parser.add_argument("--crate", action="append", default=[], help=f"Target crate: {', '.join(CRATE_MANIFESTS.keys())}")
    parser.add_argument("--check", action="store_true", help="Run cargo check instead of cargo build")
    parser.add_argument("--profile", choices=["debug", "release"], default="release")
    parser.add_argument("--stop-on-error", action="store_true", help="Stop at first failed crate")
    parser.set_defaults(func=run_build_pyd)
