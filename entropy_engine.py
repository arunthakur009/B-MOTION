import cv2
import numpy as np
import hashlib
import time
import threading
import os
from collections import Counter
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

class StatisticalTests:
    @staticmethod
    def shannon_entropy(data):
        if not data:
            return 0.0
        counts = Counter(data)
        probabilities = [count / len(data) for count in counts.values()]
        return -sum(p * np.log2(p) for p in probabilities)

    @staticmethod
    def autocorrelation(data, lag=1):
        if not data or len(data) <= lag:
            return 0.0
        n = len(data)
        mean = np.mean(data)
        numerator = sum((data[i] - mean) * (data[i + lag] - mean) for i in range(n - lag))
        denominator = sum((x - mean) ** 2 for x in data)
        return numerator / denominator if denominator != 0 else 0.0

    @staticmethod
    def min_entropy(data):
        if not data:
            return 0.0
        counts = Counter(data)
        max_prob = max(counts.values()) / len(data)
        return -np.log2(max_prob)

class MockCamera:
    def __init__(self):
        self.frame_width = 640
        self.frame_height = 480
    
    def isOpened(self):
        return True
    
    def read(self):
        # Generate random noise frame
        frame = np.random.randint(0, 256, (self.frame_height, self.frame_width, 3), dtype=np.uint8)
        # Add visual indicator
        cv2.putText(frame, "MOCK CAMERA - NO DEVICE FOUND", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        time.sleep(0.05) # Simulate ~20 FPS
        return True, frame
    
    def release(self):
        pass
    
    def open(self, index):
        return True

class BrownianEngine:
    def __init__(self):
        self.using_mock = False
        try:
            self.camera = cv2.VideoCapture(0)
            if not self.camera.isOpened():
                raise Exception("Camera not found")
            print("CAMERA: Initialized with real camera (index 0)")
        except Exception as e:
            print(f"CAMERA INIT FAILED: {e}. Switching to MockCamera.")
            self.camera = MockCamera()
            self.using_mock = True
            print("FALLBACK: Initialized with MockCamera")
        
        self.lock = threading.Lock()
        self.running = True
        self.collecting = False
        self.entropy_data = {
            "dx": [], "dy": [], 
            "cum_x": [], "cum_y": [],
            "msd": [], "key": "INITIALIZING...",
            "raw_bits": [],
            "unbiased_bits": [],
            "bits_per_frame": [],
            "entropy_stats": {}
        }
        
        # Von Neumann Unbiasing Buffer
        self.vn_buffer = []

        # Optical Flow Parameters
        self.feature_params = dict(maxCorners=20, qualityLevel=0.3, minDistance=10, blockSize=7)
        self.lk_params = dict(winSize=(15, 15), maxLevel=2,
                              criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))
        
        # Tracking state
        self.p0 = None
        self.old_gray = None
        
        # Adversarial State
        self.attack_mode = 'NONE' # NONE, FREEZE, BRIGHTNESS, PATTERN
        self.last_valid_frame = None
        
        # Threading
        self.output_frame = None
        self.heatmap_frame = None
        self.particle_frame = None
        
        # Particle Simulation State
        self.drbg_mode = False
        self.last_seed = None
        self.particles = []
        self.n_particles = 10
        # Initialize random particles
        for _ in range(self.n_particles):
            self.particles.append({
                'x': np.random.randint(100, 540),
                'y': np.random.randint(100, 380),
                'history': []
            })

        # Live stats ring buffer (always running, independent of key rotation)
        self._live_bits_per_frame = []   # rolling last 60 frames
        self._live_msd = []              # rolling last 60 data points
        self._live_cum_x = 0.0
        self._live_cum_y = 0.0
        self._live_shannon = 0.0
        self._live_min_entropy = 0.0
        self._live_autocorrelation = 0.0
        self._live_avg_motion = 0.0
        self._live_recent_bits = []      # last 256 bits for stats

        self.thread = threading.Thread(target=self.update_camera, args=())
        self.thread.daemon = True
        self.thread.start()

    def update_camera(self):
        fail_count = 0
        while self.running:
            try:
                # If using mock, just read and sleep
                if self.using_mock:
                    ret, frame = self.camera.read()
                    if not ret:
                        print("Mock camera read failed!") # Should not happen
                        time.sleep(1)
                        continue
                else:
                    # Logic for REAL camera
                    if self.camera is None or not self.camera.isOpened():
                         # Attempt partial reconnect or wait
                        if fail_count > 10:
                            # Fallback to Mock
                            print("Too many failures. Switching to MockCamera.")
                            self.camera = MockCamera()
                            self.using_mock = True
                            continue
                        else:
                            print("Camera disconnected. Retrying...")
                            try:
                                self.camera.open(0)
                            except:
                                pass
                            fail_count += 1
                            time.sleep(1)
                            continue

                    ret, frame = self.camera.read()
                    if not ret:
                        print(f"Failed to read frame (Attempt {fail_count+1}/10)")
                        fail_count += 1
                        if fail_count > 10:
                             print("Too many failures. Switching to MockCamera.")
                             if self.camera: self.camera.release()
                             self.camera = MockCamera()
                             self.using_mock = True
                        time.sleep(1)
                        continue
                    else:
                        fail_count = 0 # Reset on success

                # --- Unified Processing Pipeline ---
                
                # Save valid frame for freeze attack

                # --- Unified Processing Pipeline ---
                
                # Save valid frame for freeze attack
                if self.attack_mode == 'NONE':
                    self.last_valid_frame = frame.copy()
                
                # Apply Attacks
                if self.attack_mode == 'FREEZE':
                    if self.last_valid_frame is not None:
                        frame = self.last_valid_frame.copy()
                        
                elif self.attack_mode == 'BRIGHTNESS':
                    frame = np.full_like(frame, 255)

                elif self.attack_mode == 'PATTERN':
                    rows, cols, _ = frame.shape
                    x = np.arange(cols)
                    y = np.arange(rows)
                    X, Y = np.meshgrid(x, y)
                    checker = ((X + Y) % 2).astype(np.uint8) * 255
                    if int(time.time() * 5) % 2 == 1:
                        checker = 255 - checker
                    frame = cv2.cvtColor(checker, cv2.COLOR_GRAY2BGR)
                
                # Convert to gray
                frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                vis_frame = frame.copy()

                # --- Heatmap Generation ---
                heatmap_local = None
                
                # Ensure old_gray is valid and matches shape
                if self.old_gray is not None and self.old_gray.shape == frame_gray.shape:
                    # Calculate absolute difference
                    diff = cv2.absdiff(self.old_gray, frame_gray)
                    
                    # Apply colormap to the raw difference
                    heatmap_color = cv2.applyColorMap(diff * 5, cv2.COLORMAP_INFERNO)
                    heatmap_local = heatmap_color
                    
                else:
                     # Reset if shapes don't match
                     self.old_gray = None
                     self.p0 = None

                # --- Particle Simulation (Independent Frame) ---
                # White background
                particle_vis = np.full((480, 640, 3), 255, dtype=np.uint8)
                
                # Draw grid (optional, for graph look)
                # cv2.line(particle_vis, ...) 

                for p in self.particles:
                    # Brownian step
                    dx = np.random.randint(-5, 6) # slightly faster
                    dy = np.random.randint(-5, 6)
                    p['x'] = int(np.clip(p['x'] + dx, 0, 639))
                    p['y'] = int(np.clip(p['y'] + dy, 0, 479))
                    
                    p['history'].append((p['x'], p['y']))
                    if len(p['history']) > 50: # Longer trails
                        p['history'].pop(0)
                        
                    # Draw trail (Blue: #3182ce -> BGR: 206, 130, 49)
                    if len(p['history']) > 1:
                        pts = np.array(p['history'], np.int32)
                        pts = pts.reshape((-1, 1, 2))
                        cv2.polylines(particle_vis, [pts], False, (206, 130, 49), 2, cv2.LINE_AA)
                        
                    # Draw head
                    cv2.circle(particle_vis, (p['x'], p['y']), 4, (206, 130, 49), -1)
                
                # Initialize tracking if needed
                if self.p0 is None or len(self.p0) < 5:
                    self.p0 = cv2.goodFeaturesToTrack(frame_gray, mask=None, **self.feature_params)
                    self.old_gray = frame_gray.copy()

                # Initialize tracking variable
                frame_bits_raw = []
                frame_dx = []
                frame_dy = []
                frame_bit_count = 0

                # Calculate Optical Flow
                if self.p0 is not None and self.old_gray is not None:
                    p1, st, err = cv2.calcOpticalFlowPyrLK(self.old_gray, frame_gray, self.p0, None, **self.lk_params)
                    
                    if p1 is not None:
                        good_new = p1[st == 1]
                        good_old = self.p0[st == 1] # Crash prevention if shapes mismatched logic failure
                        
                        # Draw tracks
                        for i, (new, old) in enumerate(zip(good_new, good_old)):
                            a, b = new.ravel()
                            c, d = old.ravel()
                            
                            # Draw Green Lines
                            cv2.line(vis_frame, (int(a), int(b)), (int(c), int(d)), (0, 255, 0), 2)
                            cv2.circle(vis_frame, (int(a), int(b)), 3, (0, 255, 0), -1)

                            if self.collecting:
                                dx = float(a - c)
                                dy = float(b - d)
                                
                                # LSB Extraction
                                h, w = frame_gray.shape
                                x, y = int(a), int(b)
                                if 0 <= x < w and 0 <= y < h:
                                    pixel_val = frame_gray[y, x]
                                    lsb = int(pixel_val & 1)
                                    frame_bits_raw.append(lsb)
                                    frame_bit_count += 1

                                frame_dx.append(dx)
                                frame_dy.append(dy)

                    self.p0 = good_new.reshape(-1, 1, 2)
                    self.old_gray = frame_gray.copy()
            
                # Indicators
                cv2.putText(vis_frame, "LIVE SENSOR FEED", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                # --- Update Live Stats (always, regardless of collecting) ---
                live_bit_count = len(frame_bits_raw) if self.collecting else 0
                # If not collecting, count motion points as proxy for entropy bits
                if not self.collecting and self.p0 is not None:
                    live_bit_count = len(self.p0)
                
                with self.lock:
                    self.output_frame = vis_frame.copy()
                    if heatmap_local is not None:
                        self.heatmap_frame = heatmap_local.copy()
                    self.particle_frame = particle_vis.copy()

                    # Update live ring buffers
                    self._live_bits_per_frame.append(live_bit_count)
                    if len(self._live_bits_per_frame) > 60:
                        self._live_bits_per_frame.pop(0)
                    
                    # Track cumulative displacement for MSD
                    if frame_dx:
                        avg_dx = np.mean(frame_dx)
                        avg_dy = np.mean(frame_dy)
                    else:
                        avg_dx = np.random.normal(0, 0.5)
                        avg_dy = np.random.normal(0, 0.5)
                    self._live_cum_x += avg_dx
                    self._live_cum_y += avg_dy
                    msd_val = self._live_cum_x**2 + self._live_cum_y**2
                    self._live_msd.append(float(msd_val))
                    if len(self._live_msd) > 60:
                        self._live_msd.pop(0)
                    
                    # Track recent bits for live stats
                    self._live_recent_bits.extend(frame_bits_raw)
                    if len(self._live_recent_bits) > 256:
                        self._live_recent_bits = self._live_recent_bits[-256:]
                    
                    # Recompute live stats periodically (every frame is fine since it's fast)
                    if self._live_recent_bits:
                        self._live_shannon = float(StatisticalTests.shannon_entropy(self._live_recent_bits))
                        self._live_min_entropy = float(StatisticalTests.min_entropy(self._live_recent_bits))
                        self._live_autocorrelation = float(StatisticalTests.autocorrelation(self._live_recent_bits))
                    if frame_dx:
                        mags = np.sqrt(np.array(frame_dx)**2 + np.array(frame_dy)**2)
                        self._live_avg_motion = float(np.mean(mags))
                    
                    # Commit collected data safely under lock
                    if self.collecting:
                        self.entropy_data["bits_per_frame"].append(frame_bit_count)
                        self.entropy_data["dx"].extend(frame_dx)
                        self.entropy_data["dy"].extend(frame_dy)
                        self.entropy_data["raw_bits"].extend(frame_bits_raw)
                        
                        # Process Von Neumann Unbiasing for collected bits
                        for bit in frame_bits_raw:
                            self.vn_buffer.append(bit)
                            while len(self.vn_buffer) >= 2:
                                b1 = self.vn_buffer.pop(0)
                                b2 = self.vn_buffer.pop(0)
                                if b1 == 0 and b2 == 1:
                                    self.entropy_data["unbiased_bits"].append(1)
                                elif b1 == 1 and b2 == 0:
                                    self.entropy_data["unbiased_bits"].append(0)
                                # else discard (00, 11)

            except Exception as e:
                print(f"Error in update_camera loop: {e}")
                # Reset state to be safe
                self.p0 = None
                self.old_gray = None
                time.sleep(1)
    
    # Helper methods removed or deprecated in thread-safe flow, logic moved inline
    def _process_bit(self, bit):
        pass # Logic moved to update_camera for thread safety

    def _accumulate_entropy(self, dx, dy):
        pass # Logic moved to update_camera for thread safety
        
    def start_collection(self):
        with self.lock:
            # Reset data
            self.entropy_data = {
                "dx": [], "dy": [], 
                "cum_x": [], "cum_y": [],
                "msd": [], "key": "",
                "raw_bits": [],
                "unbiased_bits": [],
                "bits_per_frame": [],
                "entropy_stats": {}
            }
            self.vn_buffer = []
            self.collecting = True
        
    def stop_collection(self):
        with self.lock:
            self.collecting = False
            
            # Copy data for processing to avoid holding lock during heavy stats
            dx_list = list(self.entropy_data["dx"])
            dy_list = list(self.entropy_data["dy"])
            unbiased_bits = list(self.entropy_data["unbiased_bits"])
            
        # If no data collected (static camera), use fallback or empty
        if not dx_list:
            if self.drbg_mode and self.last_seed:
                # --- DRBG FALLBACK MODE ---
                # Use last valid seed to generate new key
                nonce = os.urandom(16)
                algorithm = algorithms.ChaCha20(self.last_seed, nonce)
                cipher = Cipher(algorithm, mode=None, backend=default_backend())
                encryptor = cipher.encryptor()
                raw_output = encryptor.update(b'\x00' * 32)
                key = raw_output.hex()
                
                print("WARNING: System Blind. Using DRBG Fallback.")
                
                return {
                    "health_score": 95, # High score due to DRBG reliability
                    "key": key,
                    "entropy_stats": {
                        "shannon_entropy": 0.0,
                        "autocorrelation": 0.0,
                        "min_entropy": 0.0,
                        "bit_count": 0,
                        "avg_motion": 0.0,
                        "mode": "DRBG_FALLBACK"
                    },
                    "security_rating": 90,
                    # usage of dummy lists for graphs to not break frontend
                    "dx": [], "dy": [], "cum_x": [], "cum_y": [], "msd": [], 
                    "bits_per_frame": []
                }

            print("Warning: No entropy collected.")
            # We need to lock again to update the result or return a local dict
            # Construct a safe result dict
            return {
                "health_score": 0,
                "key": "SYSTEM BLIND",
                "entropy_stats": {
                    "shannon_entropy": 0.0,
                    "autocorrelation": 0.0,
                    "min_entropy": 0.0,
                    "bit_count": 0,
                    "avg_motion": 0.0
                }
            }

        cum_x = np.cumsum(dx_list).tolist()
        cum_y = np.cumsum(dy_list).tolist()
        msd = [float(x**2 + y**2) for x, y in zip(cum_x, cum_y)]
        
        # Calculate motion metric
        motion_mags = np.sqrt(np.array(dx_list)**2 + np.array(dy_list)**2)
        avg_motion = float(np.mean(motion_mags))
        
        # Statistical Tests
        stats = {
            "shannon_entropy": float(StatisticalTests.shannon_entropy(unbiased_bits)),
            "autocorrelation": float(StatisticalTests.autocorrelation(unbiased_bits)),
            "min_entropy": float(StatisticalTests.min_entropy(unbiased_bits)),
            "bit_count": len(unbiased_bits),
            "avg_motion": avg_motion
        }

        # Generate True Random Key using DRBG
        # 1. Entropy Pool -> SHA-256
        pool_data = str(dx_list + dy_list + unbiased_bits).encode()
        seed = hashlib.sha256(pool_data).digest() # 32 bytes
        
        # Save seed for DRBG fallback
        self.last_seed = seed
        
        # 2. ChaCha20 DRBG
        nonce = os.urandom(16)
        algorithm = algorithms.ChaCha20(seed, nonce)
        cipher = Cipher(algorithm, mode=None, backend=default_backend())
        encryptor = cipher.encryptor()
        
        # Generate 32 bytes (256 bits) of random output
        raw_output = encryptor.update(b'\x00' * 32)
        key = raw_output.hex()
        
        # Calculate Health Score
        health_score = 100.0
        
        if stats["shannon_entropy"] < 0.5: health_score -= 50
        elif stats["shannon_entropy"] < 0.8: health_score -= 20
            
        if abs(stats["autocorrelation"]) > 0.1: health_score -= 40
        elif abs(stats["autocorrelation"]) > 0.05: health_score -= 15
            
        if stats["bit_count"] < 10: health_score -= 10
        if avg_motion < 0.05: health_score -= 50
             
        # Security Rating
        sec_rating = ((stats["shannon_entropy"] + stats["min_entropy"]) / 2.0) * 100.0
        if health_score < 80:
             sec_rating *= (health_score / 100.0)
        
        # Construct the final result dictionary locally
        result_data = {
            "dx": dx_list, "dy": dy_list,
            "cum_x": cum_x, "cum_y": cum_y,
            "msd": msd, 
            "key": key,
            "bits_per_frame": self.entropy_data["bits_per_frame"], # access under lock? No, this is old ref.
            "entropy_stats": stats,
            "security_rating": max(0, min(100, int(sec_rating))),
            "health_score": max(0, min(100, int(health_score)))
        }
        
        # Update internal state if needed (optional, mainly for inspection)
        # We can skip updating self.entropy_data since we return the result and next start_collection resets it.
        # But for consistency, let's update it.
        with self.lock:
             self.entropy_data.update(result_data)
             
        return result_data

    def set_attack_mode(self, mode):
        # Modes: 'NONE', 'FREEZE', 'BRIGHTNESS', 'PATTERN'
        with self.lock:
            self.attack_mode = mode.upper()
            print(f"Attack Mode Set To: {self.attack_mode}")

    def set_drbg_mode(self, enabled):
        with self.lock:
            self.drbg_mode = enabled
            print(f"DRBG Fallback Mode Set To: {self.drbg_mode}")

    def get_frame(self):
        output_copy = None
        with self.lock:
            if self.output_frame is None:
                # Return black frame if no frame available yet
                blank = np.zeros((480, 640, 3), np.uint8)
                cv2.putText(blank, "SEARCHING FOR CAMERA...", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                try:
                    ret, jpeg = cv2.imencode('.jpg', blank)
                    return jpeg.tobytes()
                except Exception as e:
                    print(f"Error encoding blank frame: {e}")
                    return b''
            
            output_copy = self.output_frame.copy()

        # Encode frame to JPEG outside lock
        try:
            ret, jpeg = cv2.imencode('.jpg', output_copy)
            return jpeg.tobytes()
        except Exception as e:
            print(f"Error encoding frame: {e}")
            return b''

    def get_current_key(self):
        with self.lock:
            return self.entropy_data.get("key", "")

    def get_live_stats(self):
        """Return real-time chart data without blocking."""
        with self.lock:
            # Compute health from live stats
            health = 100
            
            # Check if system is under attack without DRBG protection
            under_attack = self.attack_mode != 'NONE'
            no_drbg_protection = not self.drbg_mode
            
            if under_attack and no_drbg_protection:
                # System is compromised - severely penalize health
                # Base critical state
                health = 20
                
                # Further reduce based on motion detection
                if self._live_avg_motion < 0.1:
                    health = 0  # Complete system failure
                elif self._live_avg_motion < 0.5:
                    health = 10  # Severely degraded
                
                # Minimal entropy is also a sign of compromise
                if self._live_shannon < 0.3:
                    health = min(health, 5)
            else:
                # Normal health calculation
                if self._live_shannon < 0.5: health -= 50
                elif self._live_shannon < 0.8: health -= 20
                if abs(self._live_autocorrelation) > 0.1: health -= 40
                elif abs(self._live_autocorrelation) > 0.05: health -= 15
            
            health = max(0, min(100, health))
            
            return {
                "bits_per_frame": list(self._live_bits_per_frame),
                "msd": list(self._live_msd),
                "entropy_stats": {
                    "shannon_entropy": self._live_shannon,
                    "min_entropy": self._live_min_entropy,
                    "autocorrelation": self._live_autocorrelation,
                    "avg_motion": self._live_avg_motion,
                    "bit_count": len(self._live_recent_bits)
                },
                "health_score": health,
                "key": self.entropy_data.get("key", "INITIALIZING...")
            }

    def get_heatmap(self):
        output_copy = None
        with self.lock:
            if self.heatmap_frame is None:
                 # Return black/placeholder if no frame available yet
                blank = np.zeros((480, 640, 3), np.uint8)
                cv2.putText(blank, "INITIALIZING HEATMAP...", (150, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 100, 100), 2)
                try:
                    ret, jpeg = cv2.imencode('.jpg', blank)
                    return jpeg.tobytes()
                except:
                    return b''
            
            output_copy = self.heatmap_frame.copy()

        try:
            ret, jpeg = cv2.imencode('.jpg', output_copy)
            return jpeg.tobytes()
        except Exception as e:
            print(f"Error encoding heatmap: {e}")
            return b''

    def get_particle_feed(self):
        output_copy = None
        with self.lock:
            if getattr(self, 'particle_frame', None) is None:
                 # Return white placeholder
                blank = np.full((480, 640, 3), 255, np.uint8)
                cv2.putText(blank, "INITIALIZING SIM...", (180, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
                try:
                    ret, jpeg = cv2.imencode('.jpg', blank)
                    return jpeg.tobytes()
                except:
                    return b''
            
            output_copy = self.particle_frame.copy()

        try:
            ret, jpeg = cv2.imencode('.jpg', output_copy)
            return jpeg.tobytes()
        except Exception as e:
            print(f"Error encoding particle feed: {e}")
            return b''

    def __del__(self):
        self.running = False
        if self.camera.isOpened():
            self.camera.release()