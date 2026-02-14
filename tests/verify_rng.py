import requests
import json
import time

BASE_URL = "http://localhost:5002"

def test_rng_comparison():
    print("\n--- Testing RNG Comparison ---")
    start = time.time()
    try:
        resp = requests.get(f"{BASE_URL}/compare-rng", timeout=60)
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return False
        
    print(f"Analysis took {time.time() - start:.2f}s")
    
    if resp.status_code != 200:
        print(f"FAIL: API returned {resp.status_code}")
        print(resp.text)
        return False
        
    results = resp.json()
    print(json.dumps(results, indent=2))
    
    # Validation Logic
    python_rng = next(r for r in results if "Python Random" in r["source"])
    numpy_rng = next(r for r in results if "NumPy" in r["source"])
    brownian_rng = next(r for r in results if "Brownian" in r["source"])
    
    # 1. Check Reboot Vulnerability
    if python_rng["reboot_vulnerability"] != "DETECTED":
        print("FAIL: Python Random should be vulnerable to reboot attack")
        return False
        
    if numpy_rng["reboot_vulnerability"] != "DETECTED":
        print("FAIL: NumPy Random should be vulnerable to reboot attack")
        return False
        
    if brownian_rng["reboot_vulnerability"] != "SECURE":
        print("FAIL: Brownian Engine should be SECURE")
        return False
        
    # 2. Check NIST Tests (Just ensure they ran, P-values are probabilistic)
    if python_rng["monobit_p"] < 0 or python_rng["runs_p"] < 0:
        print("FAIL: Invalid P-values for Python RNG")
        return False

    print("PASS: RNG Comparison Logic Verified")
    return True

if __name__ == "__main__":
    try:
        # Check if server is up
        requests.get(BASE_URL)
    except:
        print("Server not running. Start app.py first.")
        exit(1)
        
    test_rng_comparison()
