"""
test_data_quality.py — 数据质量报告测试

覆盖:
  - DataQualityReport 生成和字段
  - QualityMetrics 聚合计算
  - QualityCollector 滚动窗口
  - 空数据处理
"""
import pytest
from l0_ingest.quality.data_quality import DataQualityReport, QualityMetrics, QualityCollector


class TestDataQualityReport:

    def test_initial_state(self) -> None:
        report = DataQualityReport(symbol="SPY_C_590")
        assert report.symbol == "SPY_C_590"
        assert report.passed is False
        assert report.warnings == []
        assert report.errors == []

    def test_add_warning(self) -> None:
        report = DataQualityReport(symbol="SPY_C_590", passed=True)
        report.add_warning("bid NaN")
        assert len(report.warnings) == 1
        assert report.passed is True   # warning 不影响 passed

    def test_add_error_sets_failed(self) -> None:
        report = DataQualityReport(symbol="SPY_C_590", passed=True)
        report.add_error("circuit breaker open")
        assert report.passed is False
        assert len(report.errors) == 1

    def test_has_issues_property(self) -> None:
        report = DataQualityReport(symbol="SPY_C_590", passed=True)
        assert not report.has_issues
        report.add_warning("x")
        assert report.has_issues

    def test_is_clean_property(self) -> None:
        report = DataQualityReport(symbol="SPY_C_590", passed=True)
        assert report.is_clean
        report.add_error("bad")
        assert not report.is_clean

    def test_summary_format(self) -> None:
        report = DataQualityReport(symbol="SPY_C_590", passed=True)
        report.add_warning("w1")
        s = report.summary()
        assert "SPY_C_590" in s
        assert "PASS" in s


class TestQualityMetrics:

    def test_pass_rate_empty(self) -> None:
        m = QualityMetrics()
        assert m.pass_rate == 0.0   # denominator protected

    def test_pass_rate_calculation(self) -> None:
        m = QualityMetrics(total_ticks=10, passed_ticks=8)
        assert m.pass_rate == pytest.approx(0.8)

    def test_nan_rate_calculation(self) -> None:
        m = QualityMetrics(total_ticks=100, nan_count=5)
        assert m.nan_rate == pytest.approx(0.05)

    def test_to_dict_keys(self) -> None:
        m = QualityMetrics(total_ticks=5, passed_ticks=4)
        d = m.to_dict()
        assert "total_ticks" in d
        assert "pass_rate" in d
        assert "nan_rate" in d
        assert "breaker_trips" in d


class TestQualityCollector:

    def setup_method(self) -> None:
        self.collector = QualityCollector(window_size=10)

    def test_empty_snapshot(self) -> None:
        m = self.collector.snapshot()
        assert m.total_ticks == 0

    def test_records_pass(self) -> None:
        r = DataQualityReport(symbol="A", passed=True)
        self.collector.record(r)
        m = self.collector.snapshot()
        assert m.total_ticks == 1
        assert m.passed_ticks == 1

    def test_records_fail(self) -> None:
        r = DataQualityReport(symbol="A", passed=False)
        r.add_error("circuit breaker open")
        self.collector.record(r)
        m = self.collector.snapshot()
        assert m.total_ticks == 1
        assert m.passed_ticks == 0
        assert m.breaker_trips == 1

    def test_gap_warning_counted(self) -> None:
        r = DataQualityReport(symbol="A", passed=True)
        r.add_warning("gap_timeout detected")
        self.collector.record(r)
        m = self.collector.snapshot()
        assert m.gap_events == 1

    def test_window_bounded(self) -> None:
        for i in range(15):
            r = DataQualityReport(symbol="A", passed=True)
            self.collector.record(r)
        m = self.collector.snapshot()
        assert m.total_ticks <= 10  # window_size=10

    def test_filter_by_symbol(self) -> None:
        for sym in ["A", "B", "A", "B", "A"]:
            r = DataQualityReport(symbol=sym, passed=True)
            self.collector.record(r)
        m_a = self.collector.snapshot(symbol="A")
        m_b = self.collector.snapshot(symbol="B")
        assert m_a.total_ticks == 3
        assert m_b.total_ticks == 2

    def test_clear(self) -> None:
        for _ in range(5):
            self.collector.record(DataQualityReport(symbol="A", passed=True))
        self.collector.clear()
        m = self.collector.snapshot()
        assert m.total_ticks == 0
