from flask import Flask, render_template, jsonify, Response
from entropy_engine import BrownianEngine
import time

app = Flask(__name__)
# Initialize the engine (global singleton)
engine = BrownianEngine()

@app.route('/')
def index():
    return render_template('index.html')

def gen_frames():
    while True:
        frame = engine.get_frame()
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.01) # Limit to ~100 FPS to save CPU
        else:
            time.sleep(0.1)

def gen_heatmap():
    while True:
        frame = engine.get_heatmap()
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.01) # Limit to ~100 FPS
        else:
            time.sleep(0.1)

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/heatmap_feed')
def heatmap_feed():
    return Response(gen_heatmap(), mimetype='multipart/x-mixed-replace; boundary=frame')

def gen_particle():
    while True:
        frame = engine.get_particle_feed()
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.03) # ~30 FPS
        else:
            time.sleep(0.1)

@app.route('/particle_feed')
def particle_feed():
    return Response(gen_particle(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/set-attack/<mode>')
def set_attack(mode):
    # Sanitize input
    if mode.upper() not in ['NONE', 'FREEZE', 'BRIGHTNESS', 'PATTERN']:
        return jsonify({"status": "error", "message": "Invalid mode"}), 400
        
    engine.set_attack_mode(mode)
    return jsonify({"status": "success", "mode": mode.upper()})

@app.route('/toggle-drbg/<state>')
def toggle_drbg(state):
    enabled = (state.upper() == 'ON')
    engine.set_drbg_mode(enabled)
    return jsonify({"status": "success", "drbg_mode": enabled})

@app.route('/live-stats')
def live_stats():
    """Lightweight endpoint for live chart updates (no blocking)."""
    return jsonify(engine.get_live_stats())

@app.route('/rotate-key')
def rotate_key():
    # Start collecting entropy
    engine.start_collection()
    
    # Capture for 5 seconds
    time.sleep(5)
    
    # Stop and compute stats
    data = engine.stop_collection()
    
    return jsonify(data)

@app.route('/compare-rng')
def compare_rng():
    from rng_comparison import RNGTester
    tester = RNGTester(engine)
    results = tester.run_suite(n_bits=100000)
    return jsonify(results)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003, debug=True, threaded=True, use_reloader=False)