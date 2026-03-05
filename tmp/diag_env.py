import sys
import os

print("--- sys.path ---")
for p in sys.path:
    print(f"  {p}")

print("\n--- Imports ---")
try:
    import l1_compute.analysis.atm_decay_tracker as tracker
    print(f"l1_compute.analysis.atm_decay_tracker: {tracker.__file__}")
except ImportError as e:
    print(f"l1_compute.analysis.atm_decay_tracker: IMPORT ERROR - {e}")

try:
    import app.services.analysis.atm_decay_tracker as tracker_alt
    print(f"app.services.analysis.atm_decay_tracker: {tracker_alt.__file__}")
except ImportError as e:
    print(f"app.services.analysis.atm_decay_tracker: IMPORT ERROR - {e}")

try:
    from shared.system.redis_service import RedisService
    import shared.system.redis_service as redis_mod
    print(f"shared.system.redis_service: {redis_mod.__file__}")
except ImportError as e:
    print(f"shared.system.redis_service: IMPORT ERROR - {e}")
