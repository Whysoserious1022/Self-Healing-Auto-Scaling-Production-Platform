/**
 * AegisAuto Cloud — Mission Control Application Engine
 * Autonomous Healing Engine & Real-Time Telemetry Matrix
 */

let lastState = null;
let currentDeck = 'self-healing';
let trafficChart = null;
let cpuChart = null;
let mutationVelocityData = [12, 15, 18, 14, 22, 19, 28, 34, 25, 20, 18, 22, 16, 24, 29, 34, 21, 19];
let pollTimer = null;

// =========================================================================
// 1. INITIALIZATION
// =========================================================================

document.addEventListener('DOMContentLoaded', () => {
  initMutationVelocityCanvas();
  initClusterCharts();
  loadGuardianFaqs();
  fetchState();
  pollTimer = setInterval(fetchState, 1000);

  // Keyboard shortcut ⌘K / Ctrl+K
  document.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      const search = document.getElementById('global-search-input');
      if (search) search.focus();
    }
  });
});

// =========================================================================
// 2. REAL-TIME TELEMETRY POLLING & STATE SYNC
// =========================================================================

async function fetchState() {
  try {
    const res = await fetch('/api/state');
    if (!res.ok) return;
    const data = await res.json();
    lastState = data;
    renderAllViews(data);
  } catch (err) {
    console.error('State poll error:', err);
  }
}

function renderAllViews(state) {
  renderTopRibbon(state);
  renderKpiCards(state);
  renderPlaybooksTable(state);
  renderMutationVelocity(state);
  renderIncidentDeepDive(state);
  renderAiSynthesizer(state);
  renderPodFleet(state);
  renderClusterCharts(state);
  renderEventStreams(state);
  renderAzTopology(state);
}

// -------------------------------------------------------------------------
// Top Ribbon Rendering
// -------------------------------------------------------------------------
function renderTopRibbon(state) {
  const ribbonCpu = document.getElementById('ribbon-cpu');
  if (ribbonCpu) ribbonCpu.textContent = `${state.fleet_cpu_load || state.avg_cpu_percent}%`;

  const ribbonRps = document.getElementById('ribbon-rps');
  if (ribbonRps) ribbonRps.textContent = state.global_rps_str || `${state.traffic_rps} RPS`;

  const ribbonRemediations = document.getElementById('ribbon-remediations');
  if (ribbonRemediations) ribbonRemediations.textContent = `${state.auto_remediations_hr || 38}/hr resolved`;

  const ribbonP99 = document.getElementById('ribbon-p99');
  if (ribbonP99) ribbonP99.textContent = `${state.p99_latency_ms || 16.2}ms`;

  const ribbonDaemon = document.getElementById('ribbon-daemon-status');
  if (ribbonDaemon) {
    ribbonDaemon.textContent = state.manual_safety_override ? 'MANUAL OVERRIDE ENGAGED' : (state.autonomous_daemon_status || 'ACTIVE / ENFORCING');
  }

  const overrideBtn = document.getElementById('override-btn');
  if (overrideBtn) {
    overrideBtn.textContent = state.manual_safety_override ? 'Disengage Safety Override' : 'Engage Manual Safety Override';
    overrideBtn.classList.toggle('active-override', !!state.manual_safety_override);
  }

  const l4Badge = document.getElementById('l4-badge');
  if (l4Badge) {
    l4Badge.innerHTML = state.manual_safety_override
      ? '<span class="dot-red">●</span> <span>MANUAL OVERRIDE MODE</span>'
      : '<span class="dot-red">●</span> <span>L4 FULL AUTONOMOUS ACTIVE</span>';
  }
}

// -------------------------------------------------------------------------
// Top 4 KPI Cards
// -------------------------------------------------------------------------
function renderKpiCards(state) {
  const healingNominal = document.getElementById('kpi-healing-nominal');
  if (healingNominal) healingNominal.textContent = state.healing_rate_nominal || '99.4% NOMINAL';

  const healingVal = document.getElementById('kpi-healing-val');
  if (healingVal) healingVal.textContent = `${state.healing_rate || 99.4}%`;

  const healingResolved = document.getElementById('kpi-healing-resolved');
  if (healingResolved) healingResolved.textContent = `${state.resolved_incidents || 420} of ${state.total_incidents || 422} Resolved`;

  const mttrVal = document.getElementById('kpi-mttr-val');
  if (mttrVal) mttrVal.textContent = `${state.mttr_seconds || 1.4}s`;

  const daemonsVal = document.getElementById('kpi-daemons-val');
  if (daemonsVal) daemonsVal.textContent = Number(state.self_healing_daemons || 14820).toLocaleString();

  const costSavingsNum = document.getElementById('cost-savings-num');
  if (costSavingsNum) costSavingsNum.textContent = `${state.cost_savings_percent || 60}%`;
}

// -------------------------------------------------------------------------
// Active Remediation Playbooks Table
// -------------------------------------------------------------------------
function renderPlaybooksTable(state) {
  const tbody = document.getElementById('playbooks-tbody');
  if (!tbody || !state.playbooks) return;

  tbody.innerHTML = state.playbooks.map(pb => {
    const stateClass = (pb.state || 'NOMINAL').toLowerCase();
    return `
      <tr class="playbook-row" onclick="triggerPlaybook('${pb.id}')" title="Click to trigger playbook '${pb.name}'">
        <td>
          <div class="playbook-name-cell">
            <span class="playbook-primary-name">
              <span class="playbook-dot-indicator"></span>
              ${escapeHtml(pb.name)}
            </span>
            <span class="playbook-spec-token">${escapeHtml(pb.spec)}</span>
          </div>
        </td>
        <td class="td-num">${pb.events_24h} events</td>
        <td class="td-num">${escapeHtml(pb.avg_latency)}</td>
        <td class="td-num">${escapeHtml(pb.success_rate)}</td>
        <td class="td-state">
          <span class="table-state-badge ${stateClass}">${escapeHtml(pb.state)}</span>
        </td>
      </tr>
    `;
  }).join('');
}

// -------------------------------------------------------------------------
// Real-Time Mutation Velocity Sparkline (Canvas Drawing)
// -------------------------------------------------------------------------
function initMutationVelocityCanvas() {
  const canvas = document.getElementById('mutationVelocityCanvas');
  if (!canvas) return;
  drawMutationVelocity();
}

function renderMutationVelocity(state) {
  if (!state) return;
  // Push live pods count change or traffic variation
  const rps = state.traffic_rps || 100;
  const jitter = Math.sin(Date.now() / 2000) * 6;
  const currentVal = Math.max(8, Math.min(38, Math.round((rps / 500) * 26 + 10 + jitter)));
  
  mutationVelocityData.push(currentVal);
  if (mutationVelocityData.length > 24) {
    mutationVelocityData.shift();
  }
  
  const peak = Math.max(...mutationVelocityData);
  const peakDisplay = document.getElementById('timeline-peak-display');
  if (peakDisplay) peakDisplay.textContent = `PEAK: ${peak} pods/s`;

  drawMutationVelocity();
}

function drawMutationVelocity() {
  const canvas = document.getElementById('mutationVelocityCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const parent = canvas.parentElement;
  const w = parent ? parent.clientWidth : 600;
  const h = 110;

  if (canvas.width !== Math.floor(w * dpr) || canvas.height !== Math.floor(h * dpr)) {
    canvas.width = Math.floor(w * dpr);
    canvas.height = Math.floor(h * dpr);
    canvas.style.width = `${w}px`;
    canvas.style.height = `${h}px`;
  }

  ctx.save();
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, w, h);

  if (mutationVelocityData.length < 2) {
    ctx.restore();
    return;
  }

  const maxVal = 40;
  const step = w / (mutationVelocityData.length - 1);

  // Gradient Fill
  const grad = ctx.createLinearGradient(0, 0, 0, h);
  grad.addColorStop(0, 'rgba(222, 84, 55, 0.20)');
  grad.addColorStop(1, 'rgba(222, 84, 55, 0.0)');

  ctx.beginPath();
  ctx.moveTo(0, h);
  mutationVelocityData.forEach((val, i) => {
    const x = i * step;
    const y = h - (val / maxVal) * (h - 24) - 10;
    ctx.lineTo(x, y);
  });
  ctx.lineTo(w, h);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();

  // Line
  ctx.beginPath();
  mutationVelocityData.forEach((val, i) => {
    const x = i * step;
    const y = h - (val / maxVal) * (h - 24) - 10;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.strokeStyle = '#DE5437';
  ctx.lineWidth = 2.0;
  ctx.stroke();

  // Peak dots
  const peakVal = Math.max(...mutationVelocityData);
  mutationVelocityData.forEach((val, i) => {
    const x = i * step;
    const y = h - (val / maxVal) * (h - 24) - 10;
    
    if (val === peakVal) {
      ctx.beginPath();
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.fillStyle = '#DE5437';
      ctx.fill();
      ctx.strokeStyle = '#FFFFFF';
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }
  });

  ctx.restore();
}

// -------------------------------------------------------------------------
// Incident Deep-Dive
// -------------------------------------------------------------------------
function renderIncidentDeepDive(state) {
  if (!state.incident_deep_dive) return;
  const inc = state.incident_deep_dive;
  
  const incTitle = document.getElementById('incident-title');
  if (incTitle) incTitle.textContent = `${inc.incident_id}: ${inc.target}`;

  const incStatus = document.getElementById('incident-status-pill');
  if (incStatus) incStatus.textContent = `${inc.status} ${inc.time_ago}`;
}

// -------------------------------------------------------------------------
// AI Synthesizer
// -------------------------------------------------------------------------
function renderAiSynthesizer(state) {
  if (!state.ai_root_cause) return;
  const pr = state.ai_root_cause.pr_proposal;
  const mergeBtn = document.getElementById('btn-merge-pr');
  const mergeText = document.getElementById('merge-pr-text');

  if (mergeBtn && mergeText) {
    if (pr.merged) {
      mergeBtn.classList.add('merged');
      mergeText.textContent = `✓ PR ${pr.pr_ref} Merged & Deployed`;
    } else {
      mergeBtn.classList.remove('merged');
      mergeText.textContent = `Create & Merge PR ${pr.pr_ref}`;
    }
  }
}

// -------------------------------------------------------------------------
// Pod Fleet Grid (Cluster Overview View)
// -------------------------------------------------------------------------
function renderPodFleet(state) {
  const grid = document.getElementById('pods-grid');
  if (!grid || !state.active_pods) return;

  const fleetPill = document.getElementById('fleet-count-pill');
  if (fleetPill) {
    const readyCount = state.active_pods.filter(p => p.ready).length;
    fleetPill.textContent = `${readyCount} / ${state.active_pods.length} Pods Running`;
  }

  grid.innerHTML = state.active_pods.map(pod => {
    const isReady = pod.ready && pod.status === 'Running';
    const badgeClass = !isReady ? 'crashed' : '';
    return `
      <div class="pod-card" id="${pod.id}">
        <button class="pod-kill-action" onclick="killSpecificPod('${pod.id}')" title="Kill pod (Chaos test)">💥</button>
        <div class="pod-top-row">
          <span class="pod-callsign">${escapeHtml(pod.callsign || pod.name.slice(0, 12))}</span>
          <span class="pod-badge ${badgeClass}">${escapeHtml(pod.mood_badge || pod.status)}</span>
        </div>
        <div class="pod-name-sub">${escapeHtml(pod.name)}</div>
        <div class="pod-metrics-row">
          <span>CPU: <strong>${pod.cpu_percent}%</strong></span>
          <span>RAM: <strong>${pod.memory_mb}MB</strong></span>
          <span>Node: <strong>${pod.node.split('.')[0]}</strong></span>
        </div>
      </div>
    `;
  }).join('');
}

// -------------------------------------------------------------------------
// Real-Time Chart.js Visualizations
// -------------------------------------------------------------------------
function initClusterCharts() {
  const tCanvas = document.getElementById('trafficChartCanvas');
  const cCanvas = document.getElementById('cpuChartCanvas');
  if (!tCanvas || !cCanvas) return;

  const chartOpts = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 300 },
    plugins: { legend: { display: false } },
    scales: {
      x: {
        grid: { color: 'rgba(0, 0, 0, 0.04)' },
        ticks: { color: '#726A5E', font: { family: 'JetBrains Mono', size: 9 }, maxTicksLimit: 6 }
      },
      y: {
        grid: { color: 'rgba(0, 0, 0, 0.04)' },
        ticks: { color: '#726A5E', font: { family: 'JetBrains Mono', size: 9 } }
      }
    }
  };

  trafficChart = new Chart(tCanvas.getContext('2d'), {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        label: 'Traffic (RPS)',
        data: [],
        borderColor: '#DE5437',
        backgroundColor: 'rgba(222, 84, 55, 0.08)',
        fill: true,
        borderWidth: 2,
        tension: 0.3,
        pointRadius: 2
      }]
    },
    options: chartOpts
  });

  cpuChart = new Chart(cCanvas.getContext('2d'), {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        label: 'CPU (%)',
        data: [],
        borderColor: '#181512',
        backgroundColor: 'rgba(24, 21, 18, 0.06)',
        fill: true,
        borderWidth: 2,
        tension: 0.3,
        pointRadius: 2
      }]
    },
    options: chartOpts
  });
}

function renderClusterCharts(state) {
  if (!state.history || !trafficChart || !cpuChart) return;
  const h = state.history;
  if (!h.timestamps || h.timestamps.length === 0) return;

  trafficChart.data.labels = h.timestamps;
  trafficChart.data.datasets[0].data = h.rps;
  trafficChart.update('none');

  cpuChart.data.labels = h.timestamps;
  cpuChart.data.datasets[0].data = h.cpu;
  cpuChart.update('none');

  const rpsInd = document.getElementById('chart-rps-indicator');
  if (rpsInd) rpsInd.textContent = `${state.traffic_rps} req/sec`;
}

// -------------------------------------------------------------------------
// Event Streams & Topology View
// -------------------------------------------------------------------------
function renderEventStreams(state) {
  const stream = document.getElementById('event-stream-list');
  const modalStream = document.getElementById('modal-log-stream');
  if (!state.events) return;

  const html = state.events.slice(0, 30).map(ev => {
    return `
      <div class="stream-event-item ${ev.level}">
        <span class="event-time">${ev.time}</span>
        <strong class="event-source">[${escapeHtml(ev.source)}]</strong>
        <span class="event-msg">${escapeHtml(ev.message)}</span>
      </div>
    `;
  }).join('');

  if (stream) stream.innerHTML = html;
  if (modalStream && !modalStream.dataset.filtered) modalStream.innerHTML = html;
}

function renderAzTopology(state) {
  if (!state.active_pods) return;
  const az1a = document.getElementById('az-1a-pods');
  const az1b = document.getElementById('az-1b-pods');
  const az1c = document.getElementById('az-1c-pods');

  const pods1a = state.active_pods.filter((_, i) => i % 3 === 0);
  const pods1b = state.active_pods.filter((_, i) => i % 3 === 1);
  const pods1c = state.active_pods.filter((_, i) => i % 3 === 2);

  const renderList = (pods) => pods.map(p => `
    <div class="stream-event-item">
      <span>●</span> <strong>${escapeHtml(p.callsign || p.name.slice(0, 10))}</strong> (${p.cpu_percent}%)
    </div>
  `).join('');

  if (az1a) az1a.innerHTML = renderList(pods1a);
  if (az1b) az1b.innerHTML = renderList(pods1b);
  if (az1c) az1c.innerHTML = pods1c.length ? renderList(pods1c) : '<small style="color:#726A5E">Standby Canary</small>';
}

// =========================================================================
// 3. USER ACTIONS & INTERACTIVITY
// =========================================================================

// Navigation Deck Switching
function switchNavDeck(deckId) {
  currentDeck = deckId;

  document.querySelectorAll('.deck-nav-item').forEach(btn => {
    btn.classList.toggle('active', btn.id === `nav-btn-${deckId}`);
  });

  document.querySelectorAll('.deck-view').forEach(view => {
    view.classList.toggle('active', view.id === `view-${deckId}`);
  });

  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Safety Override Toggle
async function toggleSafetyOverride() {
  try {
    const res = await fetch('/api/control', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'toggle_override' })
    });
    const data = await res.json();
    showToast(data.manual_override ? '⚠️ Safety Override Engaged: Manual Control' : '✓ Full Autonomous L4 Enforcing');
    fetchState();
  } catch (err) {
    showToast('Failed to toggle safety override');
  }
}

// Live Dry Run
async function triggerLiveDryRun() {
  showToast('▶ Executing Synthetic Dry-Run across all 5 Playbooks...');
  try {
    const res = await fetch('/api/control', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'trigger_dry_run' })
    });
    const data = await res.json();
    showToast(`✓ Dry Run: ${data.results}`);
    fetchState();
  } catch (err) {
    showToast('Dry run failed');
  }
}

// Trigger Playbook directly
async function triggerPlaybook(playbookId) {
  showToast(`⚡ Triggering Playbook: ${playbookId}...`);
  try {
    const res = await fetch('/api/control', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'trigger_playbook', playbook_id: playbookId })
    });
    const data = await res.json();
    showToast(`Playbook executed: ${data.playbook}`);
    fetchState();
  } catch (err) {
    showToast('Failed to execute playbook');
  }
}

// Create & Merge PR
async function mergePrProposal() {
  showToast('⑂ Merging PR #4482 and deploying canary hotfix...');
  try {
    const res = await fetch('/api/control', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'merge_pr' })
    });
    const data = await res.json();
    showToast(`🎉 Hotfix patch merged! PR ${data.pr} deployed.`);
    fetchState();
  } catch (err) {
    showToast('Failed to merge PR');
  }
}

function copyPrDiff() {
  const diff = `--- a/stream_reconciler.go\n+++ b/stream_reconciler.go\n@@ -142,2 +142,2 @@\n- mu.RLock(); defer mu.RUnlock()\n+ select { case ch <- event: default: log.warn("dropped") }`;
  navigator.clipboard.writeText(diff).then(() => {
    showToast('📋 Unified diff copied to clipboard');
  }).catch(() => {
    showToast('Failed to copy diff');
  });
}

// Chaos Controls
async function triggerChaos(action, targetRps = null) {
  closeModal('chaos-drill-modal');
  showToast(`⚡ Initiating Chaos Scenario: ${action}...`);
  try {
    await fetch('/api/control', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, target_rps: targetRps })
    });
    fetchState();
  } catch (err) {
    showToast('Failed to execute chaos command');
  }
}

async function killSpecificPod(podId) {
  showToast(`💥 Terminating pod ${podId}...`);
  try {
    await fetch('/api/control', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'kill_pod', pod_id: podId })
    });
    fetchState();
  } catch (err) {
    showToast('Failed to kill pod');
  }
}

async function triggerResetBaseline() {
  showToast('Resetting cluster to nominal baseline...');
  try {
    await fetch('/api/control', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'reset' })
    });
    fetchState();
  } catch (err) {
    showToast('Reset failed');
  }
}

async function triggerFullDemonstration() {
  closeModal('chaos-drill-modal');
  showToast('⚡ Running 5-Phase End-to-End Automated Platform Verification...');
  try {
    await fetch('/api/control', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'run_full_demonstration' })
    });
    fetchState();
  } catch (err) {
    showToast('Demonstration launch failed');
  }
}

// Sliders and Presets
function updateSliderDisplay(val) {
  const disp = document.getElementById('slider-val-display');
  if (disp) disp.textContent = `${val} RPS`;
}

function applySliderTraffic(val) {
  triggerTrafficSpike(parseInt(val, 10));
}

function applyPresetRps(rps) {
  document.querySelectorAll('.preset-btn').forEach(b => {
    b.classList.toggle('active', b.textContent.includes(`${rps} RPS`));
  });
  const slider = document.getElementById('traffic-slider');
  if (slider) slider.value = rps;
  updateSliderDisplay(rps);
  triggerTrafficSpike(rps);
}

async function triggerTrafficSpike(rps) {
  showToast(`Traffic load adjusting to ${rps} req/sec...`);
  try {
    await fetch('/api/control', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'set_traffic', target_rps: rps })
    });
    fetchState();
  } catch (err) {
    showToast('Failed to adjust traffic');
  }
}

// Global Search
function handleGlobalSearch(term) {
  const q = term.toLowerCase().trim();
  if (!q) return;

  if (q.includes('pod') || q.includes('cluster') || q.includes('node')) {
    switchNavDeck('cluster');
  } else if (q.includes('scale') || q.includes('hpa') || q.includes('traffic')) {
    switchNavDeck('autoscaling');
  } else if (q.includes('incident') || q.includes('mesh') || q.includes('log')) {
    switchNavDeck('topology');
  } else {
    switchNavDeck('self-healing');
  }
}

// =========================================================================
// 4. GUARDIAN SRE COPILOT
// =========================================================================

async function loadGuardianFaqs() {
  try {
    const res = await fetch('/api/guardian/faq');
    if (!res.ok) return;
    const data = await res.json();
    const container = document.getElementById('copilot-faqs');
    if (!container || !data.faqs) return;

    container.innerHTML = data.faqs.map(faq => `
      <button class="faq-chip" onclick="askCopilotQuestion('${escapeHtml(faq.question)}')">
        ${escapeHtml(faq.question)}
      </button>
    `).join('');
  } catch (err) {
    console.warn('FAQ load warning:', err);
  }
}

function askCopilotQuestion(question) {
  const input = document.getElementById('copilot-input');
  if (input) input.value = question;
  handleCopilotSubmit(new Event('submit'));
}

async function handleCopilotSubmit(e) {
  if (e) e.preventDefault();
  const input = document.getElementById('copilot-input');
  const chat = document.getElementById('copilot-chat-history');
  if (!input || !chat) return;

  const query = input.value.trim();
  if (!query) return;

  // Append user bubble
  chat.innerHTML += `
    <div class="chat-bubble user">
      <strong>Marcus:</strong>
      <p>${escapeHtml(query)}</p>
    </div>
  `;
  input.value = '';
  chat.scrollTop = chat.scrollHeight;

  try {
    const res = await fetch('/api/guardian/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query })
    });
    const data = await res.json();
    chat.innerHTML += `
      <div class="chat-bubble bot">
        <strong>Ava Copilot:</strong>
        <p>${escapeHtml(data.answer)}</p>
        <small style="color:#726A5E; display:block; margin-top:4px;">${escapeHtml(data.cluster_context || '')}</small>
      </div>
    `;
    chat.scrollTop = chat.scrollHeight;
  } catch (err) {
    chat.innerHTML += `
      <div class="chat-bubble bot">
        <strong>Ava Copilot:</strong>
        <p>Sorry, I encountered an issue retrieving real-time telemetry.</p>
      </div>
    `;
  }
}

// =========================================================================
// 5. MODAL MANAGEMENT & EXPORT LOGS
// =========================================================================

function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.add('open');
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove('open');
}

function closeModalOnBackdrop(e, modalId) {
  if (e.target.id === modalId) {
    closeModal(modalId);
  }
}

function filterModalLogs(term) {
  const modalStream = document.getElementById('modal-log-stream');
  if (!modalStream || !lastState || !lastState.events) return;

  const q = term.toLowerCase().trim();
  if (!q) {
    modalStream.dataset.filtered = '';
    renderEventStreams(lastState);
    return;
  }

  modalStream.dataset.filtered = 'true';
  const filtered = lastState.events.filter(ev =>
    ev.source.toLowerCase().includes(q) ||
    ev.message.toLowerCase().includes(q) ||
    ev.level.toLowerCase().includes(q)
  );

  modalStream.innerHTML = filtered.map(ev => `
    <div class="stream-event-item ${ev.level}">
      <span class="event-time">${ev.time}</span>
      <strong class="event-source">[${escapeHtml(ev.source)}]</strong>
      <span class="event-msg">${escapeHtml(ev.message)}</span>
    </div>
  `).join('') || '<div style="padding:10px; color:#726A5E;">No matching events found</div>';
}

async function exportAuditLogs() {
  try {
    const res = await fetch('/api/export-logs');
    const data = await res.json();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `aegis-remediation-audit-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('✓ Audit logs exported as JSON');
  } catch (err) {
    showToast('Failed to export audit logs');
  }
}

// Toast System
function showToast(message) {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.25s ease';
    setTimeout(() => toast.remove(), 250);
  }, 3200);
}

// Helper Escape HTML
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
