import numpy as np
from entropy_engine import StatisticalTests

def test_entropy():
    # Test passed
    data = [0, 1, 0, 1]
    h = StatisticalTests.shannon_entropy(data)
    print(f"Entropy needed 1.0, got {h}")
    assert abs(h - 1.0) < 1e-9

    data = [0, 0, 0, 0]
    h = StatisticalTests.shannon_entropy(data)
    print(f"Entropy needed 0.0, got {h}")
    assert abs(h - 0.0) < 1e-9

def test_autocorrelation():
    data = [0, 1, 0, 1]
    # mean = 0.5
    # (0-0.5)(0-0.5) + (1-0.5)(1-0.5) ...
    # Lag 1: (0-0.5)(1-0.5) + (1-0.5)(0-0.5) ...
    # This should be negative or zero depending on length
    ac = StatisticalTests.autocorrelation(data, lag=1)
    print(f"Autocorrelation: {ac}")

def test_min_entropy():
    data = [0, 0, 0, 1]
    # P(max) = 0.75
    # -log2(0.75) = - (log2(3) - 2) = 2 - 1.585 = 0.415
    min_h = StatisticalTests.min_entropy(data)
    print(f"Min Entropy: {min_h}")
    expected = -np.log2(0.75)
    assert abs(min_h - expected) < 1e-9

if __name__ == "__main__":
    try:
        test_entropy()
        test_autocorrelation()
        test_min_entropy()
        print("All StatisticalTests passed!")
    except Exception as e:
        print(f"Tests failed: {e}")
        exit(1)
