"""Service-layer wiring for the L0 V2 facade."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from shared.services.l0_runtime.services.orchestration.orchestrator import FeedOrchestrator
from shared.services.l0_runtime.services.orchestration.support import apply_rest_update
from shared.services.l0_runtime.services.pollers.tier2_poller import Tier2Poller
from shared.services.l0_runtime.services.pollers.tier3_poller import Tier3Poller
from shared.services.l0_runtime.services.subscription.manager import OptionSubscriptionManager
from shared.services.l0_runtime.services.sync.iv_baseline_sync import IVBaselineSync


@dataclass
class RuntimeServices:
    sub_mgr: OptionSubscriptionManager
    iv_sync: IVBaselineSync
    tier2: Tier2Poller
    tier3: Tier3Poller
    orchestrator: FeedOrchestrator

    @classmethod
    def build(cls, *, runtime_bundle: Any, state: Any) -> "RuntimeServices":
        sub_mgr = OptionSubscriptionManager(
            config=runtime_bundle.config,
            quote_runtime=runtime_bundle.quote_runtime,
            rate_limiter=runtime_bundle.rate_limiter,
        )
        iv_sync = IVBaselineSync(runtime_bundle.rate_limiter)
        tier2 = Tier2Poller(runtime_bundle.rate_limiter)
        tier3 = Tier3Poller(runtime_bundle.rate_limiter)
        orchestrator = FeedOrchestrator(
            runtime_bundle.quote_runtime,
            state.store,
            sub_mgr,
            iv_sync,
            runtime_bundle.rate_limiter,
            on_price_repair_update=lambda symbol, item: apply_rest_update(
                symbol=symbol,
                item=item,
                resolve_strike=sub_mgr.resolve_strike,
                sanitizer=state.sanitizer,
                store=state.store,
            ),
            needs_price_repair_fn=state.store.needs_price_repair,
        )
        return cls(
            sub_mgr=sub_mgr,
            iv_sync=iv_sync,
            tier2=tier2,
            tier3=tier3,
            orchestrator=orchestrator,
        )

