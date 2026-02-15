document.addEventListener('DOMContentLoaded', () => {
    // High-Fidelity Dashboard Logic
    
    // --- Chart Configs ---
    Chart.defaults.color = '#9ca3af';
    Chart.defaults.font.family = "'JetBrains Mono', monospace";
    Chart.defaults.borderColor = 'rgba(229, 231, 235, 0.5)';

    // 1. Entropy Per Frame (Vertical Bar Chart)
    const ctxEntropy = document.getElementById('entropyBarChart').getContext('2d');
    const entropyGradient = ctxEntropy.createLinearGradient(0, 0, 0, 400);
    entropyGradient.addColorStop(0, '#6366f1'); 
    entropyGradient.addColorStop(1, 'rgba(99, 102, 241, 0.08)');

    const entropyChart = new Chart(ctxEntropy, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Entropy Bits',
                data: [],
                backgroundColor: entropyGradient,
                borderColor: '#6366f1',
                borderWidth: 1,
                barPercentage: 0.8,
                categoryPercentage: 0.9
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { display: false },
                y: { 
                    beginAtZero: true, 
                    grid: { color: 'rgba(229, 231, 235, 0.6)' },
                    ticks: { color: '#9ca3af' }
                }
            }
        }
    });

    // 2. MSD Chart (Line)
    const ctxMSD = document.getElementById('msdChart').getContext('2d');
    const msdChart = new Chart(ctxMSD, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Mean Squared Displacement',
                data: [],
                borderColor: '#6366f1',
                backgroundColor: 'rgba(99, 102, 241, 0.08)',
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { display: false },
                y: { grid: { color: 'rgba(229, 231, 235, 0.6)' }, beginAtZero: true }
            }
        }
    });

    // 3. Quality Gauge (Doughnut)
    const ctxGauge = document.getElementById('qualityGauge').getContext('2d');
    const gaugeChart = new Chart(ctxGauge, {
        type: 'doughnut',
        data: {
            labels: ['Quality', 'Gap'],
            datasets: [{
                data: [95, 5],
                backgroundColor: ['#6366f1', '#e5e7eb'],
                borderWidth: 0,
                cutout: '85%',
                rotation: -90,
                circumference: 180
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { tooltip: { enabled: false }, legend: { display: false } }
        }
    });

    // --- State & Cycle Logic ---
    let timeLeft = 30;
    const cycleDuration = 30;
    
    // DOM Elements
    const keyDisplay = document.getElementById('key-display');
    const timerText = document.getElementById('timer-text');
    const cycleProgress = document.getElementById('cycle-progress');
    
    // Stats Elements
    const valShannon = document.getElementById('val-shannon');
    const valMin = document.getElementById('val-min');
    const valAuto = document.getElementById('val-auto');
    const valBitrate = document.getElementById('val-bitrate');
    const valHealth = document.getElementById('val-health');
    const gaugeScore = document.getElementById('gauge-score');

    // --- Live Stats Polling (updates charts every second) ---
    async function pollLiveStats() {
        try {
            const response = await fetch('/live-stats');
            const data = await response.json();
            
            // Update Entropy Bar Chart
            if (data.bits_per_frame && data.bits_per_frame.length > 0) {
                const bpf = data.bits_per_frame;
                entropyChart.data.labels = bpf.map((_, i) => '');
                entropyChart.data.datasets[0].data = bpf;
                entropyChart.update();
            }

            // Update MSD Chart
            if (data.msd && data.msd.length > 0) {
                const msd = data.msd;
                msdChart.data.labels = msd.map((_, i) => '');
                msdChart.data.datasets[0].data = msd;
                msdChart.update();
            }

            // Update Stats
            if (data.entropy_stats) {
                valShannon.innerText = `${data.entropy_stats.shannon_entropy.toFixed(3)} / 8 bits`;
                valMin.innerText = `${data.entropy_stats.min_entropy.toFixed(3)} / bit`;
                valAuto.innerText = data.entropy_stats.autocorrelation.toFixed(4);
                valBitrate.innerText = `${data.entropy_stats.bit_count * 2} bps`;
            }

            // Update Health
            if (data.health_score !== undefined) {
                const health = data.health_score;
                valHealth.innerText = health >= 80 ? "SECURE" : (health >= 50 ? "DEGRADED" : "CRITICAL");
                valHealth.style.color = health >= 80 ? "#22c55e" : (health >= 50 ? "#f59e0b" : "#ef4444");
                
                // Update Gauge
                gaugeChart.data.datasets[0].data = [health, 100 - health];
                gaugeChart.data.datasets[0].backgroundColor = [
                    health >= 80 ? '#6366f1' : (health >= 50 ? '#f59e0b' : '#ef4444'), 
                    '#e5e7eb'
                ];
                gaugeChart.update();
                gaugeScore.innerText = health;
            }

        } catch (e) {
            console.error("Live stats poll error:", e);
        }
    }
    
    // Poll every 1 second for live chart updates
    setInterval(pollLiveStats, 1000);
    // Initial poll
    pollLiveStats();

    // --- Key Rotation Cycle (30 seconds) ---
    function updateTimer() {
        const percentage = ((cycleDuration - timeLeft) / cycleDuration) * 100;
        cycleProgress.style.width = `${percentage}%`;
        timerText.innerText = `${timeLeft}s`;
        
        if (timeLeft > 0) {
            timeLeft--;
        } else {
            triggerRotation();
        }
    }
    setInterval(updateTimer, 1000);

    async function triggerRotation() {
        timeLeft = 30;
        keyDisplay.innerText = "GENERATING NEW KEY...";
        keyDisplay.style.color = "#a0aec0";

        try {
            const response = await fetch('/rotate-key');
            const data = await response.json();
            
            // Update Key
            keyDisplay.innerText = data.key || "ERROR GENERATING KEY";
            keyDisplay.style.color = "#111827";
            
            // Check for DRBG Fallback
            if (data.entropy_stats && data.entropy_stats.mode === 'DRBG_FALLBACK') {
                 keyDisplay.innerHTML += ' <span style="color: #f59e0b; font-size: 0.5em; vertical-align: middle;">[DRBG FALLBACK]</span>';
                 keyDisplay.style.color = "#f59e0b";
            }

        } catch (e) {
            console.error(e);
            keyDisplay.innerText = "CONNECTION LOST";
            keyDisplay.style.color = "#ef4444";
        }
    }

    // Initial key rotation
    triggerRotation();
});

// --- Feed Logic ---
function switchFeedTab(type, btn) {
    const img = document.getElementById('live-feed-img');
    const badge = document.getElementById('live-badge-text');
    const tabs = document.querySelectorAll('.feed-tab');
    
    tabs.forEach(t => {
        t.classList.remove('active');
    });
    btn.classList.add('active');
    
    const ts = new Date().getTime();
    if (type === 'camera') {
        img.src = `/video_feed?t=${ts}`;
        badge.innerText = "LIVE CAMERA FEED";
    } else if (type === 'heatmap') {
        img.src = `/heatmap_feed?t=${ts}`;
        badge.innerText = "ENTROPY HEATMAP";
    } else if (type === 'particle') {
        img.src = `/particle_feed?t=${ts}`;
        badge.innerText = "PARTICLE SIMULATION";
    }
}

// --- Attack & Control Logic ---

let drbgEnabled = false;

function toggleThreatMode() {
    const toggle = document.getElementById('attack-toggle');
    toggle.checked = !toggle.checked;
    toggleAttackMenu(toggle);
    
    // Scroll to widget if needed
    document.querySelector('.widget-hybrid-header').scrollIntoView({behavior: 'smooth'});
}

function toggleAttackMenu(checkbox) {
    const controls = document.getElementById('attack-controls');
    controls.style.display = checkbox.checked ? 'flex' : 'none';
}

async function setAttack(mode) {
    try {
        await fetch(`/set-attack/${mode}`);
        console.log(`Attack set to ${mode}`);
    } catch(e) { console.error(e); }
}

async function toggleDRBG(btn) {
    drbgEnabled = !drbgEnabled;
    const state = drbgEnabled ? 'ON' : 'OFF';
     try {
        const response = await fetch(`/toggle-drbg/${state}`);
        const data = await response.json();
        if (data.drbg_mode) {
             btn.style.backgroundColor = "#f59e0b";
             btn.style.color = "#000";
             btn.innerText = "DRBG: ON";
        } else {
             btn.style.backgroundColor = "";
             btn.style.color = "";
             btn.innerText = "DRBG FALLBACK";
        }
    } catch (e) {
        console.error("Failed to toggle DRBG", e);
        drbgEnabled = !drbgEnabled;
    }
}

async function runComparison(btn) {
    btn.innerText = "RUNNING ANALYSIS...";
    btn.disabled = true;
    
    // Hide previous results if any
    const resultsDiv = document.getElementById('nist-results');
    resultsDiv.style.display = 'none';
    resultsDiv.innerHTML = '';
    
    try {
        const response = await fetch('/compare-rng');
        const results = await response.json();
        
        // Build HTML table
        let tableHTML = `
            <div style="background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin-top: 20px;">
                <h3 style="margin: 0 0 15px 0; color: #111827; font-size: 1.1rem; font-weight: 700;">NIST Comparative Analysis Results</h3>
                <table style="width: 100%; border-collapse: collapse; font-size: 0.85rem;">
                    <thead>
                        <tr style="border-bottom: 2px solid #e5e7eb;">
                            <th style="text-align: left; padding: 12px 8px; color: #6b7280; font-weight: 600;">Source</th>
                            <th style="text-align: center; padding: 12px 8px; color: #6b7280; font-weight: 600;">Monobit Test</th>
                            <th style="text-align: center; padding: 12px 8px; color: #6b7280; font-weight: 600;">Runs Test</th>
                            <th style="text-align: center; padding: 12px 8px; color: #6b7280; font-weight: 600;">Reboot Vuln</th>
                            <th style="text-align: left; padding: 12px 8px; color: #6b7280; font-weight: 600;">Notes</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        results.forEach((r, idx) => {
            const monoBadge = r.monobit_p > 0.01 
                ? `<span style="background: #dcfce7; color: #166534; padding: 4px 8px; border-radius: 4px; font-weight: 600;">PASS</span>`
                : `<span style="background: #fee2e2; color: #991b1b; padding: 4px 8px; border-radius: 4px; font-weight: 600;">FAIL</span>`;
            
            const runsBadge = r.runs_p > 0.01 
                ? `<span style="background: #dcfce7; color: #166534; padding: 4px 8px; border-radius: 4px; font-weight: 600;">PASS</span>`
                : `<span style="background: #fee2e2; color: #991b1b; padding: 4px 8px; border-radius: 4px; font-weight: 600;">FAIL</span>`;
            
            const vulnBadge = r.reboot_vulnerability === 'DETECTED'
                ? `<span style="background: #fef3c7; color: #92400e; padding: 4px 8px; border-radius: 4px; font-weight: 600;">⚠ DETECTED</span>`
                : `<span style="background: #dcfce7; color: #166534; padding: 4px 8px; border-radius: 4px; font-weight: 600;">✓ SECURE</span>`;
            
            const rowBg = idx % 2 === 0 ? '#f9fafb' : '#ffffff';
            
            tableHTML += `
                <tr style="border-bottom: 1px solid #f3f4f6; background: ${rowBg};">
                    <td style="padding: 12px 8px; color: #111827; font-weight: 500;">${r.source}</td>
                    <td style="padding: 12px 8px; text-align: center;">
                        <div>${monoBadge}</div>
                        <div style="font-size: 0.75rem; color: #9ca3af; margin-top: 4px;">p=${r.monobit_p.toFixed(4)}</div>
                    </td>
                    <td style="padding: 12px 8px; text-align: center;">
                        <div>${runsBadge}</div>
                        <div style="font-size: 0.75rem; color: #9ca3af; margin-top: 4px;">p=${r.runs_p.toFixed(4)}</div>
                    </td>
                    <td style="padding: 12px 8px; text-align: center;">${vulnBadge}</td>
                    <td style="padding: 12px 8px; color: #6b7280; font-size: 0.8rem;">${r.notes}</td>
                </tr>
            `;
        });
        
        tableHTML += `
                    </tbody>
                </table>
                <div style="margin-top: 15px; padding: 12px; background: #f0f9ff; border-left: 3px solid #3b82f6; border-radius: 4px; font-size: 0.8rem; color: #1e40af;">
                    <strong>Note:</strong> P-values > 0.01 indicate the sequence appears random (PASS). P-values ≤ 0.01 suggest non-random patterns (FAIL).
                </div>
            </div>
        `;
        
        resultsDiv.innerHTML = tableHTML;
        resultsDiv.style.display = 'block';
        btn.innerText = "RUN NIST COMPARATIVE ANALYSIS";
        btn.disabled = false;
        
        // Scroll results into view
        resultsDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        
    } catch(e) {
        console.error(e);
        resultsDiv.innerHTML = `
            <div style="background: #fee2e2; border: 1px solid #fca5a5; border-radius: 8px; padding: 15px; margin-top: 20px; color: #991b1b;">
                <strong>Analysis Failed:</strong> ${e.message || 'Unknown error occurred'}
            </div>
        `;
        resultsDiv.style.display = 'block';
        btn.innerText = "RUN NIST COMPARATIVE ANALYSIS";
        btn.disabled = false;
    }
}