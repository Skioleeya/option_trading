"""Tests for L1 Arrow zero-copy schemas and data processing."""
import pyarrow as pa
import pytest

from l1_compute.arrow.schema import dicts_to_record_batch, OPTION_CHAIN_SCHEMA
from l1_compute.reactor import L1ComputeReactor


def _make_dict_chain(n: int) -> list[dict]:
    return [
        {
            "symbol": f"SPY{i}",
            "strike": 500.0 + i,
            "type": "CALL" if i % 2 == 0 else "PUT",
            "bid": 1.0 + i * 0.1,
            "ask": 1.2 + i * 0.1,
            "iv": 0.15,
            "volume": 100.0,
            "open_interest": 500.0,
            "contract_multiplier": 100.0,
        }
        for i in range(n)
    ]


class TestArrowSchema:
    def test_dicts_to_record_batch_matches_schema(self):
        """Converting a list of dictionaries should produce a RecordBatch matching the explicit schema."""
        dicts = _make_dict_chain(10)
        rb = dicts_to_record_batch(dicts)
        
        assert isinstance(rb, pa.RecordBatch)
        assert rb.schema == OPTION_CHAIN_SCHEMA
        assert rb.num_rows == 10
        assert rb.num_columns == 9

        # Spot check data
        assert rb.column("symbol")[0].as_py() == "SPY0"
        assert rb.column("strike")[1].as_py() == 501.0
        assert rb.column("is_call")[0].as_py() is True
        assert rb.column("is_call")[1].as_py() is False


class TestReactorArrowIntegration:
    @pytest.mark.asyncio
    async def test_reactor_accepts_record_batch(self):
        """L1ComputeReactor should be able to process a PyArrow RecordBatch directly without converting back to dicts."""
        dicts = _make_dict_chain(20)
        rb = dicts_to_record_batch(dicts)

        reactor = L1ComputeReactor(sabr_enabled=False)
        snap = await reactor.compute(rb, spot=505.0)
        
        # Ensure it computed
        assert snap.quality.contracts_computed == 20
        # Ensure the resulting chain retains its Arrow RecordBatch type
        assert isinstance(snap.chain, pa.RecordBatch)
        # Ensure extra column 'computed_iv' was added by the reactor
        assert "computed_iv" in snap.chain.schema.names
        assert snap.chain.num_columns == 13  # 9 base columns + computed_iv, gex, call_gex, put_gex
        
    @pytest.mark.asyncio
    async def test_to_legacy_dict_from_record_batch(self):
        """to_legacy_dict should correctly parse out the RecordBatch back to a list of dicts for Agent compatibility."""
        dicts = _make_dict_chain(10)
        rb = dicts_to_record_batch(dicts)

        reactor = L1ComputeReactor(sabr_enabled=False)
        snap = await reactor.compute(rb, spot=505.0)
        
        legacy = snap.to_legacy_dict()
        assert "chain_elements" in legacy
        
        elements = legacy["chain_elements"]
        assert len(elements) == 10
        assert elements[0]["symbol"] == "SPY0"
        assert "computed_iv" in elements[0]
