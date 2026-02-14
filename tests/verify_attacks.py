import requests
import time
import json

BASE_URL = "http://localhost:5002"

def test_attack(mode, expected_health_max=100):
    print(f"\n--- Testing Attack: {mode} ---")
    
    # 1. Set Attack Mode
    resp = requests.get(f"{BASE_URL}/set-attack/{mode}")
    print(f"Set Attack Response: {resp.json()}")
    
    if resp.status_code != 200 or resp.json().get("mode") != mode:
        print("FAIL: Could not set attack mode")
        return False
        
    # 2. Trigger Key Rotation (this runs the collection cycle)
    print("Triggering entropy collection (5s)...")
    start = time.time()
    resp = requests.get(f"{BASE_URL}/rotate-key")
    print(f"Collection took {time.time() - start:.2f}s")
    
    data = resp.json()
    health = data.get("health_score")
    stats = data.get("entropy_stats", {})
    
    print(f"Health Score: {health}")
    print(f"Stats: Entropy={stats.get('shannon_entropy'):.4f}, AutoCorr={stats.get('autocorrelation'):.4f}")
    
    if health is None:
        print("FAIL: No health score returned")
        return False
        
    # Check expectations
    if mode == 'NONE':
        if health < 80:
             print("WARNING: Baseline health is low. Is camera covered?")
    else:
        if health > expected_health_max:
            print(f"FAIL: Health score too high for attack {mode}. Expected < {expected_health_max}, got {health}")
            return False
        else:
            print("PASS: Health score dropped as expected.")
            
    return True

def main():
    try:
        # Check if server is up
        requests.get(BASE_URL)
    except requests.exceptions.ConnectionError:
        print("Server not running. Please start app.py first.")
        return

    # Baseline
    test_attack("NONE", 100)
    
    # Freeze (Low Entropy)
    test_attack("FREEZE", 60)
    
    # Brightness (Low Entropy)
    test_attack("BRIGHTNESS", 60)
    
    # Pattern (High Autocorrelation)
    test_attack("PATTERN", 70)
    
    # Reset
    print("\n--- Resetting ---")
    requests.get(f"{BASE_URL}/set-attack/NONE")

if __name__ == "__main__":
    main()
