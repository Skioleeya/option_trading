"""Generated native extension package for L0 runtime."""

from __future__ import annotations

import importlib.util
import sys
from importlib.machinery import ExtensionFileLoader
from pathlib import Path


def _load_extension() -> object:
    package_dir = Path(__file__).resolve().parent
    module_name = f"{__name__}.l0_rust"
    candidates = [
        package_dir / "wave10" / "l0_rust.pyd",
        package_dir / "wave9" / "l0_rust.pyd",
        package_dir / "wave8" / "l0_rust.pyd",
        package_dir / "wave7" / "l0_rust.pyd",
        package_dir / "wave6" / "l0_rust.pyd",
        package_dir / "wave5" / "l0_rust.pyd",
        package_dir / "wave4" / "l0_rust.pyd",
        package_dir / "l0_rust.pyd",
    ]
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
    raise ImportError(f"Unable to load native l0_rust extension from {package_dir}")


l0_rust = _load_extension()

__all__ = ["l0_rust"]
