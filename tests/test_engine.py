from entropy_engine import BrownianEngine
import time
import sys

print("Initializing Engine...")
try:
    engine = BrownianEngine()
    print("Engine Initialized.")
    time.sleep(2)
    print("Stopping Engine...")
    del engine
    print("Engine Stopped.")
except Exception as e:
    print(f"CRASH: {e}")
    import traceback
    traceback.print_exc()
