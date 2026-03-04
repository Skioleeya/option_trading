"""
test_sanitize_pipeline.py — SanitizePipelineV2 集成测试

覆盖:
  - 向后兼容旧 CleanQuoteEvent 字段
  - NaN/Inf 过滤替换
  - 统计检测集成（breaker drop）
  - bid>ask 修正
  - parse_with_quality 返回报告
"""
import math
import pytest
from l0_refactor.sanitize.pipeline import SanitizePipelineV2
from l0_refactor.events.market_events import CleanQuoteEvent, CleanDepthEvent, CleanTradeEvent, QualityFlag


class TestSanitizePipelineV2:

    def setup_method(self) -> None:
        # 禁用统计检测以隔离管道测试
        self.pipeline = SanitizePipelineV2(enable_statistical_check=False)

    # ── 正常报价 ──────────────────────────────────────────────────────
    def test_parse_quote_normal(self) -> None:
        raw = {
            "symbol": "SPY_C_590", "seq_no": 1,
            "bid": 1.10, "ask": 1.15, "last": 1.12,
            "volume": 200, "open_interest": 1000,
            "strike": 590.0, "expiry": "2024-12-20",
            "option_type": "call",
            "delta": 0.5, "iv": 0.25,
        }
        event = self.pipeline.parse_quote(raw)
        assert event is not None
        assert isinstance(event, CleanQuoteEvent)
        assert event.bid == pytest.approx(1.10)
        assert event.ask == pytest.approx(1.15)
        assert event.delta == pytest.approx(0.5)
        assert event.iv == pytest.approx(0.25)
        assert event.quality_flags == QualityFlag.OK

    # ── NaN 过滤 ──────────────────────────────────────────────────────
    def test_nan_bid_replaced_with_zero(self) -> None:
        raw = {
            "symbol": "SPY_C_590", "seq_no": 2,
            "bid": float("nan"), "ask": 1.15,
        }
        event = self.pipeline.parse_quote(raw)
        assert event is not None
        assert math.isfinite(event.bid)
        assert event.bid == pytest.approx(0.0)
        assert event.has_flag(QualityFlag.NAN_CLEANED)

    def test_inf_ask_replaced_with_zero(self) -> None:
        raw = {
            "symbol": "SPY_C_590", "seq_no": 3,
            "bid": 1.10, "ask": float("inf"),
        }
        event = self.pipeline.parse_quote(raw)
        assert event is not None
        assert math.isfinite(event.ask)

    # ── Bid > Ask 修正 ────────────────────────────────────────────────
    def test_bid_gt_ask_swapped(self) -> None:
        raw = {
            "symbol": "SPY_C_590", "seq_no": 4,
            "bid": 1.20, "ask": 1.10,  # 倒挂
        }
        event = self.pipeline.parse_quote(raw)
        assert event is not None
        assert event.bid < event.ask, "倒挂应被修正"
        assert event.has_flag(QualityFlag.BID_GT_ASK)

    # ── NaN 希腊值 ────────────────────────────────────────────────────
    def test_nan_delta_becomes_none(self) -> None:
        raw = {
            "symbol": "SPY_C_590", "seq_no": 5,
            "bid": 1.10, "ask": 1.15,
            "delta": float("nan"),
        }
        event = self.pipeline.parse_quote(raw)
        assert event is not None
        assert event.delta is None

    # ── parse_with_quality 返回报告 ───────────────────────────────────
    def test_parse_with_quality_returns_report(self) -> None:
        raw = {
            "symbol": "SPY_C_590", "seq_no": 6,
            "bid": 1.10, "ask": 1.15,
        }
        event, report = self.pipeline.parse_with_quality(raw, "quote")
        assert event is not None
        assert report.symbol == "SPY_C_590"
        assert report.passed

    def test_parse_with_quality_captures_warnings(self) -> None:
        raw = {
            "symbol": "SPY_C_590", "seq_no": 7,
            "bid": float("nan"), "ask": 1.15,
        }
        event, report = self.pipeline.parse_with_quality(raw, "quote")
        assert event is not None
        assert len(report.warnings) > 0

    # ── Depth 解析 ────────────────────────────────────────────────────
    def test_parse_depth_multi_level(self) -> None:
        raw = {
            "symbol": "SPY_C_590", "seq_no": 8,
            "bids": [[1.10, 50], [1.09, 100]],
            "asks": [[1.15, 30], [1.16, 80]],
        }
        event = self.pipeline.parse_depth(raw)
        assert event is not None
        assert isinstance(event, CleanDepthEvent)
        assert len(event.bids) == 2
        assert len(event.asks) == 2

    # ── Trade 解析 ────────────────────────────────────────────────────
    def test_parse_trade_normal(self) -> None:
        raw = {
            "symbol": "SPY_C_590", "seq_no": 9,
            "price": 1.12, "size": 5, "direction": "buy",
        }
        event = self.pipeline.parse_trade(raw)
        assert event is not None
        assert isinstance(event, CleanTradeEvent)
        assert event.price == pytest.approx(1.12)
        assert event.direction == "buy"

    def test_parse_trade_nan_price_drops(self) -> None:
        raw = {
            "symbol": "SPY_C_590", "seq_no": 10,
            "price": float("nan"), "size": 5,
        }
        event = self.pipeline.parse_trade(raw)
        assert event is None, "无效 price 的 trade 应被丢弃"

    # ── 统计检测集成 ──────────────────────────────────────────────────
    def test_statistical_breaker_integrated(self) -> None:
        """启用统计检测时，极端跳变应返回 None"""
        pipeline = SanitizePipelineV2(
            enable_statistical_check=True,
            tick_jump_sigma=5.0,
        )
        sym = "SPY_C_590"
        # 建立基线
        for i in range(15):
            v = 1.0 + (i % 3) * 0.001
            pipeline.parse_quote({
                "symbol": sym, "seq_no": i,
                "bid": v, "ask": v + 0.05,
            })
        # 注入跳变
        result = pipeline.parse_quote({
            "symbol": sym, "seq_no": 100,
            "bid": 50.0, "ask": 50.05,
        })
        assert result is None, "5σ 跳变应触发 breaker 并返回 None"
