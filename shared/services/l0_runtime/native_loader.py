"""Native extension loader for L0 runtime and related shared helpers."""

from __future__ import annotations

import importlib.util
import sys
from functools import lru_cache
from importlib.machinery import ExtensionFileLoader
from pathlib import Path

_PACKAGE_DIR = Path(__file__).resolve().parent / "_native_generated"
_ELF_MAGIC = b"\x7fELF"
_PE_MAGIC = b"MZ"


def _default_candidates() -> tuple[Path, ...]:
    return (
        _PACKAGE_DIR / "wave10" / "l0_rust.pyd",
        _PACKAGE_DIR / "wave9" / "l0_rust.pyd",
        _PACKAGE_DIR / "wave8" / "l0_rust.pyd",
        _PACKAGE_DIR / "wave7" / "l0_rust.pyd",
        _PACKAGE_DIR / "wave6" / "l0_rust.pyd",
        _PACKAGE_DIR / "wave5" / "l0_rust.pyd",
        _PACKAGE_DIR / "wave4" / "l0_rust.pyd",
        _PACKAGE_DIR / "l0_rust.pyd",
    )


def _is_linux() -> bool:
    return sys.platform.startswith("linux")


def _is_windows() -> bool:
    return sys.platform.startswith("win")


def _read_magic(path: Path) -> bytes:
    try:
        with path.open("rb") as fp:
            return fp.read(4)
    except OSError:
        return b""


def _expand_candidates(candidate_paths: tuple[Path, ...]) -> tuple[Path, ...]:
    expanded: list[Path] = []
    for raw_path in candidate_paths:
        path = Path(raw_path)
        suffix = path.suffix.lower()
        if _is_linux():
            if suffix == ".pyd":
                so_path = path.with_suffix(".so")
                expanded.append(so_path)
                expanded.extend(sorted(so_path.parent.glob(f"{so_path.stem}*.so")))
                continue
            expanded.append(path)
            if suffix == ".so":
                expanded.extend(sorted(path.parent.glob(f"{path.stem}*.so")))
            continue
        if _is_windows() and suffix == ".so":
            expanded.append(path.with_suffix(".pyd"))
            continue
        expanded.append(path)

    deduped: list[Path] = []
    seen: set[Path] = set()
    for path in expanded:
        if path in seen:
            continue
        seen.add(path)
        deduped.append(path)
    return tuple(deduped)


def _format_error(
    *,
    module_slot: str,
    requested_candidates: tuple[Path, ...],
    expanded_candidates: tuple[Path, ...],
    incompatible_windows: list[Path],
    load_errors: list[str],
) -> str:
    lines = [
        f"Unable to load native l0_rust extension (slot={module_slot!r}, platform={sys.platform}).",
        f"Requested candidates: {requested_candidates}",
        f"Expanded candidates: {expanded_candidates}",
    ]
    if incompatible_windows:
        lines.append(f"Incompatible Windows binaries on Linux: {incompatible_windows}")
        lines.append(
            "Linux requires ELF .so artifact. Build and place l0_rust.so under "
            "shared/services/l0_runtime/_native_generated/(wave10|root)."
        )
    if load_errors:
        lines.append("Load errors:")
        lines.extend(f"  - {item}" for item in load_errors)
    return "\n".join(lines)


@lru_cache(maxsize=None)
def _load_from_candidates(candidate_paths: tuple[Path, ...], module_slot: str, platform_tag: str) -> object:
    del platform_tag
    module_name = "l0_rust"
    loaded = sys.modules.get(module_name)
    if loaded is not None:
        return loaded

    expanded_candidates = _expand_candidates(candidate_paths)
    incompatible_windows: list[Path] = []
    load_errors: list[str] = []

    for path in expanded_candidates:
        if not path.exists():
            continue
        if _is_linux() and path.suffix.lower() == ".pyd":
            incompatible_windows.append(path)
            continue
        magic = _read_magic(path)
        if _is_linux() and magic.startswith(_PE_MAGIC):
            incompatible_windows.append(path)
            continue
        if _is_linux() and path.suffix.lower() == ".so" and magic != _ELF_MAGIC:
            load_errors.append(f"{path}: unexpected binary magic {magic!r}")
            continue
        loader = ExtensionFileLoader(module_name, str(path))
        spec = importlib.util.spec_from_file_location(module_name, path, loader=loader)
        if spec is None or spec.loader is None:
            continue
        try:
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            return module
        except Exception as exc:  # noqa: BLE001
            sys.modules.pop(module_name, None)
            load_errors.append(f"{path}: {type(exc).__name__}: {exc}")

    raise ImportError(
        _format_error(
            module_slot=module_slot,
            requested_candidates=candidate_paths,
            expanded_candidates=expanded_candidates,
            incompatible_windows=incompatible_windows,
            load_errors=load_errors,
        )
    )


def load_l0_rust(*, candidates: list[Path] | None = None, module_suffix: str | None = None) -> object:
    requested = tuple(candidates or _default_candidates())
    slot = (module_suffix or "default").strip() or "default"
    return _load_from_candidates(requested, slot, sys.platform)


l0_rust = load_l0_rust()

__all__ = ["l0_rust", "load_l0_rust"]
