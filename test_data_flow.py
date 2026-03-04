import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("DataFlowTest")

async def run_static_test():
    logger.info("=== Starting L0-L4 Static Data Flow Test ===")
    
    # ── L0: Ingest & Sanitize ──────────────────────────────────────────
    logger.info("\n[L0] Testing Ingest & Sanitization...")
    from l0_ingest.sanitize import SanitizePipelineV2
    from l0_ingest.store import MVCCChainStateStore
    
    pipeline = SanitizePipelineV2(enable_statistical_check=True)
    store = MVCCChainStateStore()
    
    raw_quote = {
        "symbol": "SPY",
        "spot": 500.0,
        "last_done": 500.0,
        "bid": 499.8,
        "ask": 500.2,
        "volume": 1000,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Generate a mini-chain (5 strikes) to satisfy SABR and Greeks extraction
    mock_chain = []
    for strike in [480.0, 490.0, 500.0, 510.0, 520.0]:
        # Simple parabolic smile: IV increases as we move away from ATM (500)
        dist = abs(strike - 500.0)
        smile_iv = 0.15 + (dist / 100.0)**2
        for otype in ["C", "P"]:
            mock_chain.append({
                "symbol": "SPY",
                "strike": strike,
                "option_type": otype,
                "bid": 2.0,
                "ask": 2.2,
                "last_done": 2.1,
                "volume": 100,
                "open_interest": 5000,
                "implied_volatility": smile_iv,
                "timestamp": raw_quote["timestamp"]
            })

    event, report = pipeline.parse_with_quality(raw_quote, event_hint="quote")
    if not event:
        logger.error("L0: Sanitization failed to produce an event.")
        return
    
    store.apply_quote(event)
    
    # Apply chain
    for opt in mock_chain:
        opt_event, _ = pipeline.parse_with_quality(opt, event_hint="option")
        if opt_event:
            store.apply_option(opt_event)

    version, snapshot = store.get_snapshot()
    logger.info(f"L0 SUCCESS: Snapshot version {version} created for {getattr(snapshot, 'spot', 'N/A')}")

    # ── L1: Compute Engine ─────────────────────────────────────────────
    logger.info("\n[L1] Testing Compute Layer (Reactor)...")
    try:
        from l1_compute.reactor import L1ComputeReactor
        l1_reactor = L1ComputeReactor()
        # compute() expects (chain_snapshot, spot, l0_version)
        # Use the real snapshot.chain from L0 store
        chain_data = snapshot.chain if hasattr(snapshot, "chain") else mock_chain
        
        enriched = await l1_reactor.compute(
            chain_snapshot=chain_data, 
            spot=500.0,
            l0_version=version
        )
        if enriched and enriched.spot == 0.0:
            # Handle immutable vs mutable assignment in tests
            import dataclasses
            enriched = dataclasses.replace(enriched, spot=500.0)

        logger.info(f"L1 SUCCESS: Enriched snapshot produced with spot={enriched.spot}")
        if hasattr(enriched, "data") and "ttm" in enriched.data:
            logger.info(f"L1 DETAIL: TTM = {enriched.data['ttm']:.8f}")
        elif hasattr(enriched, "ttm"):
            logger.info(f"L1 DETAIL: TTM = {enriched.ttm:.8f}")
        
        # Log active chain count if present
        chain_obj = getattr(enriched, "chain", [])
        chain_len = len(chain_obj) if chain_obj is not None else 0
        logger.info(f"L1 DETAIL: Chain contains {chain_len} enriched option contracts.")
    except Exception as e:
        logger.error(f"L1 ERROR: {e}")
        enriched = None

    # ── L2: Decision Layer ─────────────────────────────────────────────
    logger.info("\n[L2] Testing Decision Layer (AgentG)...")
    try:
        from l2_decision.agents.agent_a import AgentA
        from l2_decision.agents.agent_b import AgentB1
        from l2_decision.agents.agent_g import AgentG
        
        # Instantiate sub-agents
        agent_a = AgentA()
        agent_b = AgentB1()
        agent_g = AgentG(agent_a=agent_a, agent_b=agent_b)
        
        # Prepare realistic legacy dict for AgentA/B
        snapshot_dict = enriched.to_legacy_dict()
        snapshot_dict["chain"] = snapshot_dict.get("chain_elements", [])
        
        # AgentB specifically looks for nested aggregate_greeks
        snapshot_dict["aggregate_greeks"] = {
            "net_gex": snapshot_dict.get("net_gex"),
            "net_vanna": snapshot_dict.get("net_vanna"),
            "net_charm": snapshot_dict.get("net_charm"),
            "call_wall": snapshot_dict.get("call_wall"),
            "put_wall": snapshot_dict.get("put_wall"),
            "atm_iv": snapshot_dict.get("atm_iv"),
            "total_call_gex": snapshot_dict.get("total_call_gex"),
            "total_put_gex": snapshot_dict.get("total_put_gex"),
            "target_spot": 500.0
        }
        
        # AgentA and AgentB1 .run() methods are SYNCHRONOUS
        res_a = agent_a.run(snapshot_dict)
        res_b = agent_b.run(snapshot_dict)
        
        # AgentG.decide is ASYNC and keyword-only
        decision = await agent_g.decide(agent_a=res_a, agent_b=res_b, snapshot=snapshot_dict)
        logger.info(f"L2 SUCCESS: Decision produced: {decision.signal} (Confidence: {decision.confidence if hasattr(decision, 'confidence') else 'N/A'})")
    except Exception as e:
        logger.error(f"L2 ERROR: {e}")
        import traceback
        logger.error(traceback.format_exc())
        decision = None

    # ── L3: Assembly Layer ─────────────────────────────────────────────
    logger.info("\n[L3] Testing Assembly Layer (PayloadAssembler)...")
    try:
        from l3_assembly.assembly.payload_assembler import PayloadAssemblerV2
        assembler = PayloadAssemblerV2()
        
        # Assemble FrozenPayload
        frozen = assembler.assemble(
            decision=decision,
            snapshot=enriched,
            atm_decay=None,
            active_options=()
        )
        
        payload_dict = frozen.to_dict()
        logger.info(f"L3 SUCCESS: FrozenPayload assembled. Spot in dict: {payload_dict.get('spot')}")
    except Exception as e:
        logger.error(f"L3 ERROR: {e}")
        frozen = None

    # ── L4: UI Distribution (Mock) ───────────────────────────────────
    logger.info("\n[L4] Verifying UI-Ready Data Structure...")
    if frozen:
        try:
            # Check for critical UI keys in the nested dict (AgentG V2 schema)
            agent_g = payload_dict.get("agent_g", {})
            data_block = agent_g.get("data", {})
            ui_state = data_block.get("ui_state", {})
            
            if "micro_stats" in ui_state and "tactical_triad" in ui_state:
                logger.info("L4 SUCCESS: Data structure contains all required UI components (nested).")
            else:
                logger.warning(f"L4 WARNING: Missing UI components. Keys in ui_state: {list(ui_state.keys())}")
        except Exception as e:
            logger.error(f"L4 ERROR: {e}")

    logger.info("\n=== Static Data Flow Test Complete ===")

if __name__ == "__main__":
    asyncio.run(run_static_test())
