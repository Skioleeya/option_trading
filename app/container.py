"""Dependency Injection container."""

import asyncio
from dataclasses import dataclass

from l0_ingest.feeds.option_chain_builder import OptionChainBuilder
from l2_decision.agents.agent_g import AgentG
from shared.system.redis_service import RedisService
from shared.system.historical_store import HistoricalStore
from shared.services.active_options.runtime_service import ActiveOptionsRuntimeService
from l1_compute.analysis.atm_decay_tracker import AtmDecayTracker
from l3_assembly.reactor import L3AssemblyReactor

from l1_compute.reactor import L1ComputeReactor
from l2_decision.reactor import L2DecisionReactor

@dataclass
class AppContainer:
    """Central service container for the application.

    Manages dependency injection for all services:
    - OptionChainBuilder (data feed)
    - AgentG (decision framework)
    - Redis & Historical store
    - Reactors (L1, L2, L3)
    """
    option_chain_builder: OptionChainBuilder
    agent_g: AgentG
    redis_service: RedisService
    historical_store: HistoricalStore
    atm_decay_tracker: AtmDecayTracker
    active_options_service: ActiveOptionsRuntimeService
    
    quote_hub_ready: asyncio.Event
    
    # Reactors
    l1_reactor: L1ComputeReactor
    l2_reactor: L2DecisionReactor
    l3_reactor: L3AssemblyReactor


def build_container() -> AppContainer:
    """Factory function to build the AppContainer without running I/O bindings."""
    # Data layer
    option_chain_builder = OptionChainBuilder()
    redis_service = RedisService()
    historical_store = HistoricalStore(redis_service)
    
    # Decision + services
    agent_g = AgentG()
    active_options_service = ActiveOptionsRuntimeService()
    
    # ATM Tracker (ctx is injected during lifespan)
    atm_decay_tracker = AtmDecayTracker(redis_service.client, None)
    
    # L1, L2 Reactors (legacy fallback path removed)
    l1_reactor = L1ComputeReactor(r=0.05, q=0.0, sabr_enabled=True)
    l2_reactor = L2DecisionReactor(shadow_mode=False)

    # L3 Reactor
    l3_reactor = L3AssemblyReactor(redis=redis_service.client)
    
    return AppContainer(
        option_chain_builder=option_chain_builder,
        agent_g=agent_g,
        redis_service=redis_service,
        historical_store=historical_store,
        atm_decay_tracker=atm_decay_tracker,
        active_options_service=active_options_service,
        quote_hub_ready=asyncio.Event(),
        l1_reactor=l1_reactor,
        l2_reactor=l2_reactor,
        l3_reactor=l3_reactor
    )
