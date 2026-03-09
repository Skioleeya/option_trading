from l0_ingest.subscription_manager import OptionSubscriptionManager


def _build_manager(cap: int, strike_map: dict[str, float]) -> OptionSubscriptionManager:
    mgr = OptionSubscriptionManager.__new__(OptionSubscriptionManager)
    mgr._subscription_cap = cap
    mgr._symbol_to_strike = dict(strike_map)
    return mgr


def test_subscription_cap_keeps_mandatory_and_nearest_to_spot() -> None:
    mgr = _build_manager(
        cap=3,
        strike_map={"OPT_A": 99.0, "OPT_B": 100.0, "OPT_C": 130.0, "OPT_D": 90.0},
    )
    target_set = {"OPT_A", "OPT_B", "OPT_C", "OPT_D"}

    kept = mgr._enforce_subscription_cap(
        target_set,
        mandatory_symbols={"OPT_D"},
        spot=100.0,
    )

    assert kept == {"OPT_D", "OPT_A", "OPT_B"}
    assert set(mgr._symbol_to_strike.keys()) == kept


def test_subscription_cap_trims_mandatory_when_it_exceeds_cap() -> None:
    mgr = _build_manager(
        cap=2,
        strike_map={"OPT_A": 100.0, "OPT_B": 101.0, "OPT_C": 130.0},
    )
    target_set = {"OPT_A", "OPT_B", "OPT_C"}

    kept = mgr._enforce_subscription_cap(
        target_set,
        mandatory_symbols={"OPT_A", "OPT_B", "OPT_C"},
        spot=100.0,
    )

    assert kept == {"OPT_A", "OPT_B"}

