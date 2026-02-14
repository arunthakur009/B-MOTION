import requests
import time
import sys

BASE_URL = "http://localhost:5002"

def set_attack(mode):
    resp = requests.get(f"{BASE_URL}/set-attack/{mode}")
    print(f"Set Attack {mode}: {resp.status_code}")
    time.sleep(1)

def toggle_drbg(state):
    resp = requests.get(f"{BASE_URL}/toggle-drbg/{state}")
    print(f"Toggle DRBG {state}: {resp.json()}")
    time.sleep(1)

def rotate_key():
    resp = requests.get(f"{BASE_URL}/rotate-key")
    data = resp.json()
    print(f"Rotate Key: Health={data.get('health_score')}, Mode={data.get('entropy_stats', {}).get('mode', 'TRNG')}")
    return data

def run_test():
    print("--- Starting DRBG Verification ---")
    
    # 1. Reset
    print("\n[Step 1] Normal Operation")
    toggle_drbg("OFF")
    set_attack("NONE")
    time.sleep(2) # Accumulate entropy
    data = rotate_key()
    if data['health_score'] < 50:
        print("FAIL: Baseline health too low")
        return False
        
    # 2. Attack without DRBG
    print("\n[Step 2] Attack with DRBG OFF")
    set_attack("BRIGHTNESS") # Blinds the camera
    time.sleep(2)
    data = rotate_key()
    # Expect failure or low score
    if data['health_score'] > 20: 
        print(f"WARNING: Health score {data['health_score']} unexpectedly high for blinded camera.")
        # proceed anyway
    else:
        print("PASS: Health score dropped as expected.")

    # 3. Enable DRBG Fallback
    print("\n[Step 3] Attack with DRBG ON")
    toggle_drbg("ON")
    time.sleep(1)
    data = rotate_key()
    
    # Expect high score and DRBG mode
    mode = data.get('entropy_stats', {}).get('mode', 'TRNG')
    score = data.get('health_score')
    
    if score >= 90 and mode == 'DRBG_FALLBACK':
        print("PASS: DRBG Fallback active with high health score.")
    else:
        print(f"FAIL: Expected DRBG_FALLBACK and Score >= 90. Got Mode={mode}, Score={score}")
        return False

    # 4. Cleanup
    print("\n[Step 4] Cleanup")
    set_attack("NONE")
    toggle_drbg("OFF")
    return True

if __name__ == "__main__":
    try:
        if run_test():
            print("\n--- TEST PASSED ---")
            sys.exit(0)
        else:
            print("\n--- TEST FAILED ---")
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
