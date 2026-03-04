
import sys
import traceback
sys.path.append('e:\\US.market\\Option_v3')
from l3_assembly.presenters.tactical_triad import TacticalTriadPresenterV2

try:
    res = TacticalTriadPresenterV2.build(
        vrp=15.0,
        vrp_state='TRAP',
        net_charm=50.0,
        svol_corr=None,
        svol_state='NORMAL',
       fused_signal_direction=None,
    )
    print(res)
except Exception as e:
    traceback.print_exc()


