import asyncio

import pytest
from fastapi import FastAPI

import app.lifespan as lifespan_module


class _DummyRedisService:
    client = None

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None


class _DummyAgentG:
    async def set_redis_client(self, client) -> None:
        return None


class _DummyUiTracker:
    async def set_redis_client(self, client) -> None:
        return None


class _DummyL3Store:
    def __init__(self) -> None:
        self.bound_redis = None

    def bind_redis(self, client) -> None:
        self.bound_redis = client


class _DummyL3Reactor:
    def __init__(self) -> None:
        self.store = _DummyL3Store()
        self.ui_tracker = _DummyUiTracker()

    def bind_redis(self, client) -> None:
        self.store.bind_redis(client)


class _DummyL1Reactor:
    def update_microstructure_depth(self, *args, **kwargs) -> None:
        return None

    def update_microstructure_trades(self, *args, **kwargs) -> None:
        return None


class _DummyL2Reactor:
    def flush_audit(self) -> None:
        return None


class _DummyAtmDecayTracker:
    def __init__(self) -> None:
        self.redis = None
        self.anchor = object()
        self.initialized_spot = None

    async def initialize(self, *, spot: float) -> None:
        self.initialized_spot = spot

    async def bootstrap_intraday_anchor(self, chain, spot: float) -> None:
        return None

    def get_anchor_symbols(self) -> set[str]:
        return set()

    def compute_current_decay(self, chain) -> None:
        return None


class _DummyOptionChainBuilder:
    def __init__(self) -> None:
        self.on_depth = None
        self.on_trade = None
        self.repair_symbols_calls: list[set[str]] = []

    async def initialize(self) -> None:
        return None

    async def fetch_snapshot(self) -> dict[str, object]:
        return {"spot": None}

    def get_startup_chain_snapshot(self) -> list[dict[str, object]]:
        return [{"symbol": "SPY260326C647000.US", "strike": 647.0}]

    async def repair_symbols_once(self, symbols, log_prefix: str | None = None) -> int:
        self.repair_symbols_calls.append(set(symbols))
        return 0

    def get_startup_bootstrap_context(self) -> tuple[float, list[dict[str, object]]]:
        return 0.0, []

    def set_mandatory_symbols(self, symbols) -> None:
        return None

    async def refresh_subscriptions_once(self, spot: float) -> None:
        return None

    async def shutdown(self) -> None:
        return None


class _DummyContainer:
    def __init__(self) -> None:
        self.redis_service = _DummyRedisService()
        self.agent_g = _DummyAgentG()
        self.atm_decay_tracker = _DummyAtmDecayTracker()
        self.l3_reactor = _DummyL3Reactor()
        self.option_chain_builder = _DummyOptionChainBuilder()
        self.quote_hub_ready = asyncio.Event()
        self.l1_reactor = _DummyL1Reactor()
        self.l2_reactor = _DummyL2Reactor()


async def _noop_sleep(seconds: float) -> None:
    return None


async def _noop_loop(*args, **kwargs) -> None:
    return None


@pytest.mark.asyncio
async def test_lifespan_normalizes_none_initial_spot(monkeypatch: pytest.MonkeyPatch) -> None:
    container = _DummyContainer()
    app = FastAPI()

    monkeypatch.setattr(lifespan_module, "build_container", lambda: container)
    monkeypatch.setattr(lifespan_module.asyncio, "sleep", _noop_sleep)
    monkeypatch.setattr(lifespan_module, "run_compute_loop", _noop_loop)
    monkeypatch.setattr(lifespan_module, "run_broadcast_loop", _noop_loop)
    monkeypatch.setattr(lifespan_module, "run_housekeeping_loop", _noop_loop)

    async with lifespan_module.lifespan(app):
        assert app.state.container is container

    assert container.atm_decay_tracker.initialized_spot == 0.0
    assert container.option_chain_builder.repair_symbols_calls == []
    assert container.quote_hub_ready.is_set()


class _BootingRedisService(_DummyRedisService):
    async def start(self) -> None:
        self.client = object()


class _BootingContainer(_DummyContainer):
    def __init__(self) -> None:
        super().__init__()
        self.redis_service = _BootingRedisService()


@pytest.mark.asyncio
async def test_lifespan_binds_redis_client_into_l3_store(monkeypatch: pytest.MonkeyPatch) -> None:
    container = _BootingContainer()
    app = FastAPI()

    monkeypatch.setattr(lifespan_module, "build_container", lambda: container)
    monkeypatch.setattr(lifespan_module.asyncio, "sleep", _noop_sleep)
    monkeypatch.setattr(lifespan_module, "run_compute_loop", _noop_loop)
    monkeypatch.setattr(lifespan_module, "run_broadcast_loop", _noop_loop)
    monkeypatch.setattr(lifespan_module, "run_housekeeping_loop", _noop_loop)

    async with lifespan_module.lifespan(app):
        assert app.state.container is container

    assert container.l3_reactor.store.bound_redis is container.redis_service.client
