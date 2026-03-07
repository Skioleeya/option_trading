import pytest

from l0_ingest.feeds import market_data_gateway as gateway_module


class _DummyConfig:
    pass


class _BrokenQuoteContext:
    def __init__(self, _config):
        raise RuntimeError("simulated connect failure")


class _FakeQuoteContext:
    def __init__(self):
        self.on_quote = None
        self.on_depth = None
        self.on_trades = None

    def set_on_quote(self, cb):
        self.on_quote = cb

    def set_on_depth(self, cb):
        self.on_depth = cb

    def set_on_trades(self, cb):
        self.on_trades = cb


@pytest.mark.asyncio
async def test_connect_degrades_when_quote_context_init_fails(monkeypatch):
    monkeypatch.setattr(gateway_module, "QuoteContext", _BrokenQuoteContext)
    gateway = gateway_module.MarketDataGateway(config=_DummyConfig(), primary_ctx=None)

    await gateway.connect()

    diag = gateway.diagnostics()
    assert gateway.quote_ctx is None
    assert diag["connected"] is False
    assert diag["queue_size"] == 0


@pytest.mark.asyncio
async def test_connect_registers_callbacks_when_primary_ctx_injected():
    fake_ctx = _FakeQuoteContext()
    gateway = gateway_module.MarketDataGateway(config=_DummyConfig(), primary_ctx=fake_ctx)

    await gateway.connect()

    assert gateway.quote_ctx is fake_ctx
    assert fake_ctx.on_quote is not None
    assert fake_ctx.on_depth is not None
    assert fake_ctx.on_trades is not None
