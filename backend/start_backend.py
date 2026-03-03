import sys
import os
from datetime import datetime

# Add the backend directory to sys.path
sys.path.insert(0, os.path.abspath('.'))

try:
    from app.main import main
    print(f"[{datetime.now()}] Starting backend...")
    main()
except Exception as e:
    print(f"[{datetime.now()}] CRASH: {e}")
    import traceback
    traceback.print_exc()
