"""State owner for the L0 V2 facade."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from l0_ingest.v2.normalize.pipeline import SanitizationPipeline
from l0_ingest.v2.state.runtime.chain_state_store import ChainStateStore


@dataclass
class LiveState:
    store: ChainStateStore = field(default_factory=ChainStateStore)
    sanitizer: SanitizationPipeline = field(default_factory=SanitizationPipeline)

    def snapshot_rows(self, target_symbols: set[str] | None = None) -> list[dict[str, Any]]:
        return self.store.get_snapshot(target_symbols)
