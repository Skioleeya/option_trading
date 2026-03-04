"""
test_statistical_breaker.py — 统计异常检测断路器测试

覆盖:
  - 正常数据通过
  - 5σ 跳变触发熔断
  - gap 计时告警
  - bid > ask 倒挂检测
  - OI 突变告警
"""
import pytest
import time
from l0_refactor.sanitize.statistical_breaker import StatisticalBreaker
from l0_refactor.events.quality_events import BreakerReason, AlertSeverity


class TestStatisticalBreaker:

    def setup_method(self) -> None:
        self.breaker = StatisticalBreaker(
            tick_jump_sigma=5.0,
            gap_threshold_s=0.1,   # 测试用短 gap
            oi_quantile=0.99,
            breaker_reset_s=0.05,  # 快速重置用于测试
        )
        self.sym = "SPY_C_590"

    # ── 正常数据通过 ──────────────────────────────────────────────────
    def test_normal_data_passes(self) -> None:
        """连续稳定报价应全部通过"""
        for i in range(20):
            bid = 1.00 + i * 0.001
            ask = bid + 0.05
            passed, breaker_ev, alert = self.breaker.check_quote(self.sym, bid, ask)
            assert passed, f"tick {i} should pass"
        assert True

    # ── Tick Jump ─────────────────────────────────────────────────────
    def test_tick_jump_triggers_breaker(self) -> None:
        """价格突然 5σ 跳变应触发熔断"""
        # 建立稳定基线（均值≈1.0, std≈0.001）
        for i in range(15):
            v = 1.0 + (i % 3) * 0.001
            self.breaker.check_quote(self.sym, v, v + 0.05)

        # 注入异常跳变：5.0 → 远超 5σ
        passed, breaker_ev, alert = self.breaker.check_quote(self.sym, 5.0, 5.05)
        assert not passed, "极端跳变应触发断路"
        assert breaker_ev is not None
        assert breaker_ev.reason == BreakerReason.TICK_JUMP
        assert breaker_ev.is_open is True

    def test_breaker_auto_resets(self) -> None:
        """熔断后等待 reset 时间自动恢复"""
        # 建立基线
        for i in range(15):
            v = 1.0 + (i % 3) * 0.001
            self.breaker.check_quote(self.sym, v, v + 0.05)

        # 触发熔断
        passed, breaker_ev, _ = self.breaker.check_quote(self.sym, 5.0, 5.05)
        assert not passed

        # 等待重置
        time.sleep(0.1)

        # 恢复后正常报价应通过
        passed, recovery_ev, _ = self.breaker.check_quote(self.sym, 1.0, 1.05)
        assert passed, "断路器应在等待后自动恢复"
        # recovery_ev 是恢复事件
        if recovery_ev is not None:
            assert not recovery_ev.is_open

    # ── Gap 检测 ──────────────────────────────────────────────────────
    def test_gap_generates_alert(self) -> None:
        """超过 gap_threshold_s 没有报价应生成告警"""
        self.breaker.check_quote(self.sym, 1.0, 1.05)
        time.sleep(0.15)  # 超过 0.1s 阈值
        passed, _, alert = self.breaker.check_quote(self.sym, 1.0, 1.05)
        assert passed, "gap 告警不应导致 drop"
        assert alert is not None
        assert "gap" in alert.reason.lower()

    # ── Bid > Ask ─────────────────────────────────────────────────────
    def test_bid_gt_ask_generates_alert(self) -> None:
        """倒挂应生成告警但不 drop"""
        passed, breaker_ev, alert = self.breaker.check_quote(self.sym, 1.10, 1.05)
        assert passed, "倒挂应生成告警但不 drop"
        assert alert is not None
        assert "bid_gt_ask" in alert.reason

    # ── OI 突变 ───────────────────────────────────────────────────────
    def test_oi_surge_generates_alert(self) -> None:
        """OI 大幅突变超过 Q99 应生成告警"""
        # 建立稳定 OI 基线（需至少 20 个 delta 样本，delta ≈ 10）
        oi = 100.0
        for i in range(60):   # 60 个样本确保 Q99 统计稳定
            oi += 10.0
            self.breaker.check_quote(self.sym, 1.0, 1.05, open_interest=oi, seq_no=i)

        # 注入 OI 突变（+200000 >> Q99≈10）
        passed, _, alert = self.breaker.check_quote(
            self.sym, 1.0, 1.05, open_interest=oi + 200_000, seq_no=100
        )
        assert passed, "OI 突变应告警但不 drop"
        assert alert is not None
        assert "oi_surge" in alert.reason

    # ── 多 Symbol 独立状态 ────────────────────────────────────────────
    def test_independent_per_symbol_state(self) -> None:
        """不同 symbol 的状态应相互隔离"""
        sym_a, sym_b = "SPY_C_590", "SPY_P_580"
        # 在 sym_a 建立基线并触发熔断
        for i in range(15):
            v = 1.0 + (i % 3) * 0.001
            self.breaker.check_quote(sym_a, v, v + 0.05)
        self.breaker.check_quote(sym_a, 50.0, 50.05)  # 触发 sym_a 熔断

        # sym_b 应不受影响
        passed, _, _ = self.breaker.check_quote(sym_b, 1.0, 1.05)
        assert passed, "sym_b 不应被 sym_a 的熔断影响"
