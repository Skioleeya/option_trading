"""Version-aware native extension loader for bounded cutover slices."""

from __future__ import annotations

import importlib.util
import sys
from importlib.machinery import ExtensionFileLoader
from pathlib import Path


def load_l0_rust(*, candidates: list[Path], module_suffix: str) -> object:
    del module_suffix
    module_name = "l0_rust"
    for path in candidates:
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
    raise ImportError(f"Unable to load native l0_rust extension from candidates: {candidates}")
