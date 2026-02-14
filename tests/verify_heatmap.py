import requests

def test_heatmap():
    url = "http://localhost:5002/heatmap_feed"
    print(f"Testing Heatmap Feed: {url}")
    try:
        with requests.get(url, stream=True, timeout=5) as r:
            if r.status_code == 200:
                print("PASS: Heatmap feed returned 200 OK")
                # Check for MJPEG boundary
                content_type = r.headers.get('content-type')
                print(f"Content-Type: {content_type}")
                if 'multipart/x-mixed-replace' in content_type:
                    print("PASS: Correct MJPEG Content-Type")
                    return True
                else:
                    print("FAIL: Incorrect Content-Type")
            else:
                print(f"FAIL: Status Code {r.status_code}")
    except Exception as e:
        print(f"FAIL: Exception {e}")
    return False

if __name__ == "__main__":
    test_heatmap()
