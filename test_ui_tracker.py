
import sys
import asyncio
from datetime import datetime
import json

sys.path.append('e:\\US.market\\Option_v3')

from l3_assembly.assembly.ui_state_tracker import UIStateTracker
from l1_compute.output.enriched_snapshot import EnrichedSnapshot, AggregateGreeks, MicroSignals, ComputeQualityReport

# create fake history directly in the track
tracker = UIStateTracker()

for i in range(25):
    snap = EnrichedSnapshot(
        spot=100.0 + i,
        chain=[],
        aggregates=AggregateGreeks(atm_iv=0.2 + (i*0.01), net_gex=1000, call_wall=105, put_wall=95, net_charm=50),
        microstructure=MicroSignals(),
        quality=ComputeQualityReport(),
        ttm_seconds=3600,
        version=1,
        computed_at=datetime.now()
    )
    ui_metrics = tracker.tick(snap, None)
    
print('ui_metrics[svol_corr] on tick 25:', ui_metrics['svol_corr'])
print('VannaAnalyzer points:', len(tracker._vanna_analyzer._history))


