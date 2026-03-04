import subprocess
import sys
import os
import time

# Ensure we are in the backend directory
os.chdir(r"e:\US.market\Option_v3\backend")

print("Starting Uvicorn...")
process = subprocess.Popen(
    ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--log-level", "debug"],
    stdout=open("logs/fresh_uvicorn.log", "w"),
    stderr=subprocess.STDOUT,
    env={**os.environ, "PYTHONPATH": "."}
)

time.sleep(2) # Brief wait to spawn process
print(f"Uvicorn started with PID {process.pid} logging to fresh_uvicorn.log")
# Process remains running in background
