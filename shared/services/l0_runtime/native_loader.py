"""Native extension loader for L0 runtime and related shared helpers."""

from __future__ import annotations

import importlib.util
import sys
from functools import lru_cache
from importlib.machinery import ExtensionFileLoader
from pathlib import Path

_PACKAGE_DIR = Path(__file__).resolve().parent / "_native_generated"


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


@lru_cache(maxsize=None)
def _load_from_candidates(candidate_paths: tuple[Path, ...]) -> object:
    module_name = "l0_rust"
    loaded = sys.modules.get(module_name)
    if loaded is not None:
        return loaded
    for path in candidate_paths:
        if not path.exists():
            continue
        loader = ExtensionFileLoader(module_name, str(path))
        spec = importlib.util.spec_from_file_location(module_name, path, loader=loader)
        if spec is None:
            continue
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        loader.exec_module(module)
        return module
    raise ImportError(f"Unable to load native l0_rust extension from candidates: {candidate_paths}")


def load_l0_rust(*, candidates: list[Path] | None = None, module_suffix: str | None = None) -> object:
    del module_suffix
    return _load_from_candidates(tuple(candidates or _default_candidates()))


l0_rust = load_l0_rust()

__all__ = ["l0_rust", "load_l0_rust"]
