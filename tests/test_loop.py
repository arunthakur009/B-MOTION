from entropy_engine import BrownianEngine
import time
import sys
import threading

print("Initializing Engine for Loop Test...")
try:
    engine = BrownianEngine()
    print("Engine Initialized.")
    
    # The engine starts its thread in __init__
    # Let's let it run for 10 seconds
    print("Running for 10 seconds...")
    for i in range(10):
        time.sleep(1)
        # Try to access frames to simulate app usage
        f = engine.get_frame()
        h = engine.get_heatmap()
        p = engine.get_particle_feed()
        print(f"Tick {i+1}: Frame bytes: {len(f)}, Heatmap bytes: {len(h)}, Particle bytes: {len(p)}")
        if not engine.running:
             print("Engine stopped unexpectedly!")
             break
             
    engine.running = False
    print("Test Complete. Engine survived.")
    
except Exception as e:
    print(f"CRASH: {e}")
    import traceback
    traceback.print_exc()
