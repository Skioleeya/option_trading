import pytest

from l3_assembly.presenters.micro_stats import MicroStatsPresenterV2


@pytest.mark.parametrize(
    ("gex_regime", "label", "badge"),
    (
        ("SUPER_PIN", "SUPER PIN", "badge-amber"),
        ("DAMPING", "DAMPING", "badge-hollow-green"),
        ("ACCELERATION", "VOLATILE", "badge-hollow-purple"),
        ("NEUTRAL", "NEUTRAL", "badge-neutral"),
    ),
)
def test_micro_stats_net_gex_contract(gex_regime: str, label: str, badge: str) -> None:
    state = MicroStatsPresenterV2.build(
        gex_regime=gex_regime,
        wall_dyn={},
        vanna="NORMAL",
        momentum="NEUTRAL",
    )
    assert state.net_gex.label == label
    assert state.net_gex.badge == badge


def test_micro_stats_rejects_unknown_gex_regime() -> None:
    with pytest.raises(ValueError, match="Unknown gex_regime"):
        MicroStatsPresenterV2.build(
            gex_regime="UNKNOWN_STATE",
            wall_dyn={},
            vanna="NORMAL",
            momentum="NEUTRAL",
        )
