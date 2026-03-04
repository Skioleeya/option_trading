import asyncio
from main import AppContainer
from datetime import datetime

async def test_assembler():
    container = AppContainer()
    await container.initialize_all()
    # Read last payload
    print("WAITING 3 SECS FOR COMPUTE...")
    await asyncio.sleep(3)
    
    if container._l3_reactor:
        snap = container._l1_reactor._empty_snapshot(0)
        ui_metrics = container._l3_reactor.ui_tracker.tick(snap, None)
        
        # Test per strike gex array length and sample content
        if container._last_frozen and container._last_frozen.agent_g and container._last_frozen.agent_g.get("data", {}).get("chain_elements"):
            print(f"CHAIN ELEMENTS LEN: {len(container._last_frozen.agent_g.get('data', {}).get('chain_elements'))}")
            print(f"FIRST CHAIN ELEMENT: {container._last_frozen.agent_g.get('data', {}).get('chain_elements')[0] if container._last_frozen.agent_g.get('data', {}).get('chain_elements') else None}")
        from l3_assembly.presenters.ui.wall_migration.presenter import WallMigrationPresenter
        raw = WallMigrationPresenter.build(ui_metrics.get('wall_migration_data', {}))
        print(f"RAW ROWS: {raw}")
        from l3_assembly.presenters.wall_migration import WallMigrationPresenterV2
        final = WallMigrationPresenterV2.build(ui_metrics.get('wall_migration_data', {}))
        print(f"FINAL ROWS: {final}")
        
    payload = container._last_frozen
    if payload:
        print("\n=== L4 Payload Dump ===")
        # Output chain items
        print("PER STRIKE GEX L1: ", len(payload.agent_g.get("data", {}).get("chain_elements", [])) if payload.agent_g else "None")
        print(f"SPY SPOT: {payload.spot}")
        
        walls = payload.ui_state.wall_migration
        print(f"WALL MIGRATION JSON: {[w.to_dict() for w in walls]}")
        
        depth = payload.ui_state.depth_profile
        print(f"DEPTH PROFILE: {[d.to_dict() for d in depth]}")
        
        micro = payload.ui_state.micro_stats
        print(f"MICRO STATS: {micro.to_dict()}")
        
        sign = payload.signal
        print(f"SPY_ATM_IV: {sign.signal_summary.get('atm_iv', 0.0)}")
    else:
        print("NO PAYLOAD!")
        
    await container.shutdown_all()

if __name__ == '__main__':
    asyncio.run(test_assembler())
