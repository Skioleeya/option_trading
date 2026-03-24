"""L0 V2 single-direction worktree."""

from __future__ import annotations

from typing import Any

__all__ = ["OptionChainBuilder"]


def __getattr__(name: str) -> Any:
    if name == "OptionChainBuilder":
        from .facade import OptionChainBuilder

        return OptionChainBuilder
    raise AttributeError(name)
