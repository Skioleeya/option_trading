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


def test_symbol_profile_promotes_to_steady_and_falls_back_on_cooldown() -> None:
    limiter = APIRateLimiter(
        startup_symbol_rate=180.0,
        startup_symbol_burst=20,
        steady_symbol_rate=240.0,
        steady_symbol_burst=50,
    )

    assert limiter.symbol_profile == "startup"
    assert limiter.max_symbol_weight == 20

    limiter._profile_entered_at -= 121.0
    limiter._last_cooldown_ts -= 121.0
    promoted = limiter.maybe_promote_to_steady(
        warmup_done=True,
        warming_up=False,
        stable_for_sec=120.0,
    )

    assert promoted is True
    assert limiter.symbol_profile == "steady"
    assert limiter.max_symbol_weight == 50

    limiter.trigger_cooldown(seconds=60)
    assert limiter.cooldown_active is True
    assert limiter.symbol_profile == "startup"
    assert limiter.max_symbol_weight == 20
    assert limiter.cooldown_hits_5m >= 1
