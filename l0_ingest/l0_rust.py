"""Compatibility shim for the compiled ``l0_rust`` extension in L0."""

from __future__ import annotations

from typing import Any

try:
    from ._native import l0_rust as _ext
except Exception as exc:  # pragma: no cover - env specific
    raise ImportError(
        "Failed to import compiled l0_rust extension from l0_ingest/_native"
    ) from exc

if hasattr(_ext, "__all__"):
    __all__ = list(_ext.__all__)  # type: ignore[attr-defined]
else:
    __all__ = [name for name in dir(_ext) if not name.startswith("_")]

globals().update({name: getattr(_ext, name) for name in __all__})
__doc__ = getattr(_ext, "__doc__", None) or __doc__


def __getattr__(name: str) -> Any:
    return getattr(_ext, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_ext)))

