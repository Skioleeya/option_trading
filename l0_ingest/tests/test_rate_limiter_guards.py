import pytest

from l0_ingest.feeds.rate_limiter import (
    APIRateLimiter,
    LONGPORT_MAX_CALLS_PER_SEC,
    LONGPORT_MAX_CONCURRENT,
    LONGPORT_MAX_REQUEST_BURST,
)


def test_limiter_clamps_to_official_quote_api_caps() -> None:
    limiter = APIRateLimiter(
        rate=99.0,
        burst=99,
        max_concurrent=99,
        symbol_rate=240.0,
        symbol_burst=50,
    )

    assert limiter.max_calls_per_sec == LONGPORT_MAX_CALLS_PER_SEC
    assert limiter.max_concurrent == LONGPORT_MAX_CONCURRENT
    assert limiter.tokens == float(LONGPORT_MAX_REQUEST_BURST)


@pytest.mark.asyncio
async def test_acquire_rejects_weight_above_symbol_burst() -> None:
    limiter = APIRateLimiter(symbol_burst=5)

    with pytest.raises(ValueError, match="exceeds symbol_burst=5"):
        async with limiter.acquire(weight=6):
            pass

