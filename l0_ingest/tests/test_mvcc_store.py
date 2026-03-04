"""
test_mvcc_store.py — MVCC 快照隔离存储测试

覆盖:
  - 单线程写入+读取一致性
  - 版本号单调递增
  - GC 旧版本不超限
  - 并发读不阻塞写入
"""
import threading
import time
import pytest
from l0_ingest.store.mvcc_store import MVCCChainStateStore
from l0_ingest.events.market_events import CleanQuoteEvent


class TestMVCCChainStateStore:

    def setup_method(self) -> None:
        self.store = MVCCChainStateStore(keep_versions=3)

    # ── 单线程写入读取 ────────────────────────────────────────────────
    def test_initial_snapshot_is_none(self) -> None:
        version, snap = self.store.get_snapshot()
        assert version == 0
        assert snap is None

    def test_update_spot_creates_snapshot(self) -> None:
        self.store.update_spot(590.5)
        version, snap = self.store.get_snapshot()
        assert version == 1
        assert snap is not None
        assert snap.spot_price == pytest.approx(590.5)

    def test_version_monotonically_increases(self) -> None:
        for i in range(5):
            self.store.update_spot(590.0 + i)
        version, _ = self.store.get_snapshot()
        assert version == 5

    def test_apply_quote_updates_chain(self) -> None:
        event = CleanQuoteEvent(
            seq_no=1, symbol="SPY_C_590",
            bid=1.10, ask=1.15, last=1.12,
            volume=100, open_interest=500,
            strike=590.0, expiry="2024-12-20",
            option_type="call",
        )
        self.store.apply_quote(event)
        _, snap = self.store.get_snapshot()
        assert snap is not None
        # 链中应含有 SPY_C_590
        symbols_in_snap = [row[0] for row in snap.chain_snapshot]
        assert "SPY_C_590" in symbols_in_snap

    def test_history_bounded_by_keep_versions(self) -> None:
        """历史版本数不超过 keep_versions"""
        for i in range(10):
            self.store.update_spot(float(i))
        history = self.store.get_history()
        assert len(history) <= 3, f"Expected ≤ 3, got {len(history)}"

    def test_snapshot_is_immutable(self) -> None:
        """快照对象不可变（frozen dataclass）"""
        self.store.update_spot(590.0)
        _, snap = self.store.get_snapshot()
        with pytest.raises((AttributeError, TypeError)):
            snap.spot_price = 999.0  # type: ignore[misc]

    # ── 并发读写 ──────────────────────────────────────────────────────
    def test_concurrent_reads_dont_block_writes(self) -> None:
        """多线程读取不应阻塞写入线程"""
        errors = []
        read_results = []

        def reader() -> None:
            for _ in range(50):
                try:
                    v, snap = self.store.get_snapshot()
                    read_results.append(v)
                    time.sleep(0.001)
                except Exception as e:
                    errors.append(str(e))

        def writer() -> None:
            for i in range(20):
                try:
                    self.store.update_spot(float(i))
                    time.sleep(0.002)
                except Exception as e:
                    errors.append(str(e))

        threads = [threading.Thread(target=reader) for _ in range(5)]
        threads.append(threading.Thread(target=writer))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert not errors, f"并发错误: {errors}"
        assert len(read_results) > 0

    def test_snapshot_age_ms(self) -> None:
        """快照 age_ms 随时间增加"""
        self.store.update_spot(590.0)
        _, snap = self.store.get_snapshot()
        time.sleep(0.05)   # 50ms — 比 Windows 计时精度高一个数量级
        assert snap.age_ms >= 5, "age_ms 应反映时间流逝"

    def test_snapshot_freshness(self) -> None:
        self.store.update_spot(590.0)
        _, snap = self.store.get_snapshot()
        assert snap.is_fresh(max_age_ms=500)
        time.sleep(0.6)
        assert not snap.is_fresh(max_age_ms=500)
