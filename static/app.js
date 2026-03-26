/* MathLineage — Frontend application */

const API_BASE = window.location.origin;
let API_TOKEN = ''; // Set via ?token=xxx query param or configure in UI

// ── Initialization ─────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  // Check for token in URL
  const params = new URLSearchParams(window.location.search);
  if (params.get('token')) API_TOKEN = params.get('token');

  setupRouting();
  setupSearch();
  checkApiHealth();
});

// ── Routing ────────────────────────────────────────────────────────────────

function setupRouting() {
  document.querySelectorAll('[data-view]').forEach(el => {
    el.addEventListener('click', e => {
      e.preventDefault();
      showView(el.dataset.view);
    });
  });
}

function showView(name) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));

  const view = document.getElementById(`view-${name}`);
  if (view) view.classList.add('active');

  document.querySelectorAll(`.nav-link[data-view="${name}"]`).forEach(l => l.classList.add('active'));

  if (name === 'stats') loadStats();
  if (name === 'search') document.getElementById('searchInput')?.focus();
}

// ── API Helpers ────────────────────────────────────────────────────────────

function apiHeaders() {
  const h = { 'Accept': 'application/json' };
  if (API_TOKEN) h['Authorization'] = `Bearer ${API_TOKEN}`;
  return h;
}

async function apiFetch(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const resp = await fetch(url, { headers: apiHeaders(), ...options });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail || `HTTP ${resp.status}`);
  }
  return resp.json();
}

async function apiPost(path, body) {
  return apiFetch(path, {
    method: 'POST',
    headers: { ...apiHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

// ── Health Check ───────────────────────────────────────────────────────────

async function checkApiHealth() {
  const dot = document.querySelector('.status-dot');
  const text = document.querySelector('.status-text');
  try {
    const data = await apiFetch('/healthz');
    dot.classList.add('connected');
    dot.classList.remove('error');
    text.textContent = `v${data.version} | ${Math.floor(data.uptime_seconds)}s uptime`;
  } catch {
    dot.classList.add('error');
    dot.classList.remove('connected');
    text.textContent = 'API offline';
  }
}

// ── Search ─────────────────────────────────────────────────────────────────

let searchTimeout = null;

function setupSearch() {
  const input = document.getElementById('searchInput');

  input.addEventListener('input', () => {
    clearTimeout(searchTimeout);
    const q = input.value.trim();
    if (q.length < 2) {
      hideResults();
      return;
    }
    searchTimeout = setTimeout(() => doSearch(q), 300);
  });

  // Keyboard shortcut: / to focus search
  document.addEventListener('keydown', e => {
    if (e.key === '/' && document.activeElement !== input) {
      e.preventDefault();
      input.focus();
      showView('search');
    }
    if (e.key === 'Escape') {
      input.blur();
      hideResults();
    }
  });
}

async function doSearch(query) {
  const resultsSection = document.getElementById('searchResults');
  const resultsList = document.getElementById('resultsList');
  const resultsCount = document.getElementById('resultsCount');
  const resultsTime = document.getElementById('resultsTime');
  const featured = document.getElementById('featured');

  const t0 = performance.now();

  try {
    // Use the process endpoint with a single entry to get full pipeline results
    const data = await apiPost('/api/v1/process', {
      entries: [{ CanonicalLatin: query }],
      mode: 'quick',
    });

    const elapsed = ((performance.now() - t0) / 1000).toFixed(2);
    const entries = data.entries || [];

    if (entries.length === 0) {
      resultsCount.textContent = 'No results';
      resultsTime.textContent = `${elapsed}s`;
      resultsList.innerHTML = '<div class="loading">No matching records found</div>';
    } else {
      resultsCount.textContent = `${entries.length} result${entries.length > 1 ? 's' : ''}`;
      resultsTime.textContent = `${elapsed}s`;
      resultsList.innerHTML = entries.map(e => renderResultCard(e)).join('');

      // Attach click handlers
      resultsList.querySelectorAll('.result-card').forEach(card => {
        card.addEventListener('click', () => showDetail(JSON.parse(card.dataset.entry)));
      });
    }

    resultsSection.classList.remove('hidden');
    featured.style.display = 'none';
  } catch (err) {
    resultsCount.textContent = 'Error';
    resultsTime.textContent = err.message;
    resultsList.innerHTML = `<div class="loading">${escapeHtml(err.message)}</div>`;
    resultsSection.classList.remove('hidden');
  }
}

function hideResults() {
  document.getElementById('searchResults').classList.add('hidden');
  document.getElementById('featured').style.display = '';
}

function renderResultCard(entry) {
  const name = entry.CanonicalLatin || '?';
  const region = entry.RegionCode || entry.DetectedRegion || '?';
  const conf = entry.Confidence || 0;
  const method = entry.DetectionMethod || '';
  const country = (entry.CountryCodes || [])[0] || '';
  const orderKey = entry.OrderKey || '';

  const confClass = conf >= 80 ? 'high' : conf >= 50 ? 'med' : 'low';

  return `
    <div class="result-card" data-entry='${escapeAttr(JSON.stringify(entry))}'>
      <div>
        <div class="result-name">${escapeHtml(name)}</div>
        <div class="result-meta">
          ${country ? `<span>${countryFlag(country)} ${country}</span>` : ''}
          ${method ? `<span>${escapeHtml(method)}</span>` : ''}
          ${orderKey ? `<span>${escapeHtml(orderKey)}</span>` : ''}
        </div>
      </div>
      <div class="result-badges">
        <span class="badge badge-region">${escapeHtml(region)}</span>
        <span class="badge badge-confidence-${confClass}">${conf.toFixed(0)}%</span>
      </div>
    </div>`;
}

// ── Detail View ────────────────────────────────────────────────────────────

function showDetail(entry) {
  showView('detail');
  const container = document.getElementById('detailContent');

  const name = entry.CanonicalLatin || '?';
  const native = entry.CanonicalNative || '';
  const region = entry.RegionCode || entry.DetectedRegion || '?';
  const conf = entry.Confidence || 0;
  const gid = entry.GlobalID || '?';
  const country = (entry.CountryCodes || [])[0] || '';
  const sources = entry._sources || [];
  const shortForms = entry.ShortFormClusters ? Object.keys(entry.ShortFormClusters) : [];
  const confClass = conf >= 80 ? 'high' : conf >= 50 ? 'med' : 'low';
  const initial = name.charAt(0).toUpperCase();

  container.innerHTML = `
    <div class="detail-header">
      <div class="detail-avatar">${initial}</div>
      <div class="detail-title">
        <h1>${escapeHtml(name)}</h1>
        ${native && native !== name ? `<div class="detail-native">${escapeHtml(native)}</div>` : ''}
        <div class="detail-tags">
          <span class="badge badge-region">${escapeHtml(region)}</span>
          <span class="badge badge-confidence-${confClass}">${conf.toFixed(0)}% confidence</span>
          ${country ? `<span class="badge" style="background:var(--bg-active);color:var(--text-muted)">${countryFlag(country)} ${country}</span>` : ''}
        </div>
      </div>
    </div>

    <div class="detail-stats">
      <div class="stat-card">
        <div class="stat-value">${escapeHtml(region)}</div>
        <div class="stat-label">Region</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${sources.length}</div>
        <div class="stat-label">Sources</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${shortForms.length}</div>
        <div class="stat-label">Name Variants</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${entry.RoundtripScore ? (entry.RoundtripScore * 100).toFixed(0) + '%' : 'N/A'}</div>
        <div class="stat-label">Roundtrip Score</div>
      </div>
    </div>

    ${sources.length > 0 ? `
    <div class="detail-section">
      <h2>Authority Sources</h2>
      <div class="source-list">
        ${sources.map(s => `<span class="source-badge">${escapeHtml(s)}</span>`).join('')}
      </div>
    </div>` : ''}

    ${shortForms.length > 0 ? `
    <div class="detail-section">
      <h2>Name Variants</h2>
      <div class="shortform-list">
        ${shortForms.map(sf => `<span class="shortform">${escapeHtml(sf)}</span>`).join('')}
      </div>
    </div>` : ''}

    <div class="detail-section">
      <h2>Global ID</h2>
      <div class="globalid-row">
        <span class="globalid">${escapeHtml(gid)}</span>
        <button class="copy-btn" onclick="copyToClipboard('${escapeAttr(gid)}', this)">Copy</button>
      </div>
    </div>

    <div class="detail-section">
      <h2>Academic Lineage</h2>
      <div class="lineage-container" id="lineageContainer">
        <div class="lineage-controls">
          <label>Depth: <input type="range" min="1" max="5" value="3" id="lineageDepth"></label>
          <span id="lineageDepthLabel">3 levels</span>
        </div>
        <div id="lineageContent" class="loading"><div class="spinner"></div>Loading lineage...</div>
      </div>
    </div>
  `;

  // Load lineage if GlobalID available
  if (gid && gid !== '?') loadLineage(gid, 3);

  const depthInput = document.getElementById('lineageDepth');
  if (depthInput) {
    depthInput.addEventListener('input', () => {
      document.getElementById('lineageDepthLabel').textContent = `${depthInput.value} levels`;
      if (gid && gid !== '?') loadLineage(gid, parseInt(depthInput.value));
    });
  }
}

// ── Lineage Visualization ──────────────────────────────────────────────────

async function loadLineage(globalId, depth) {
  const container = document.getElementById('lineageContent');
  container.innerHTML = '<div class="loading"><div class="spinner"></div>Loading lineage...</div>';

  try {
    const data = await apiFetch(`/api/v1/lineage/${encodeURIComponent(globalId)}?depth=${depth}`);
    renderLineageTree(container, data);
  } catch (err) {
    container.innerHTML = `<div class="lineage-empty">Lineage data not available for this record.<br><small>${escapeHtml(err.message)}</small></div>`;
  }
}

function renderLineageTree(container, data) {
  if (!data || (!data.ancestors?.length && !data.descendants?.length)) {
    container.innerHTML = '<div class="lineage-empty">No advisor/student relationships found in the graph database.</div>';
    return;
  }

  const root = data.root || {};
  const ancestors = data.ancestors || [];
  const descendants = data.descendants || [];

  // Build simple vertical tree layout
  const nodes = [];
  const edges = [];

  // Ancestors above root
  ancestors.forEach((a, i) => {
    nodes.push({ ...a, x: 300, y: 40 + i * 80, type: 'ancestor' });
  });

  // Root
  const rootY = 40 + ancestors.length * 80;
  nodes.push({ ...root, x: 300, y: rootY, type: 'root' });

  // Descendants below root
  descendants.forEach((d, i) => {
    const cols = Math.min(descendants.length, 3);
    const col = i % cols;
    const row = Math.floor(i / cols);
    nodes.push({
      ...d,
      x: 150 + col * 200,
      y: rootY + 80 + row * 80,
      type: 'descendant',
    });
  });

  // Edges
  (data.edges || []).forEach(e => {
    edges.push({ from: e.advisor_id, to: e.student_id });
  });

  const svgH = Math.max(300, (ancestors.length + 1 + Math.ceil(descendants.length / 3)) * 80 + 60);

  let svg = `<svg class="lineage-svg" viewBox="0 0 600 ${svgH}" xmlns="http://www.w3.org/2000/svg">`;

  // Draw edges
  edges.forEach(e => {
    const from = nodes.find(n => n.global_id === e.from);
    const to = nodes.find(n => n.global_id === e.to);
    if (from && to) {
      svg += `<path class="lineage-edge" d="M${from.x},${from.y + 12} C${from.x},${(from.y + to.y) / 2} ${to.x},${(from.y + to.y) / 2} ${to.x},${to.y - 12}"/>`;
    }
  });

  // Draw nodes
  nodes.forEach(n => {
    const cls = n.type === 'root' ? 'lineage-node root' : 'lineage-node';
    const r = n.type === 'root' ? 16 : 12;
    const label = (n.name || n.canonical_latin || '?').split(',')[0];
    const years = n.birth_year ? ` (${n.birth_year}${n.death_year ? '-' + n.death_year : ''})` : '';

    svg += `<g class="${cls}" data-id="${escapeAttr(n.global_id || '')}">`;
    svg += `<circle cx="${n.x}" cy="${n.y}" r="${r}"/>`;
    svg += `<text x="${n.x}" y="${n.y + r + 16}" font-size="11">${escapeHtml(label)}${years}</text>`;
    svg += `</g>`;
  });

  svg += '</svg>';
  container.innerHTML = svg;
}

// ── Statistics View ────────────────────────────────────────────────────────

async function loadStats() {
  const container = document.getElementById('statsContent');
  container.innerHTML = '<div class="loading"><div class="spinner"></div>Loading statistics...</div>';

  try {
    const health = await apiFetch('/healthz');
    const metricsText = await fetch(`${API_BASE}/metrics`).then(r => r.text());

    // Parse Prometheus metrics
    const metrics = {};
    metricsText.split('\n').forEach(line => {
      if (line.startsWith('#') || !line.trim()) return;
      const match = line.match(/^(\S+?)(?:\{.*?\})?\s+(.+)$/);
      if (match) metrics[match[1]] = parseFloat(match[2]);
    });

    const pipelineRuns = metrics['gmnap_pipeline_runs_total'] || 0;
    const entriesProcessed = metrics['gmnap_entries_processed_total'] || 0;
    const uptimeSec = health.uptime_seconds || 0;

    container.innerHTML = `
      <div class="stats-card">
        <h3>Pipeline Runs</h3>
        <div class="stats-big">${pipelineRuns.toLocaleString()}</div>
      </div>
      <div class="stats-card">
        <h3>Entries Processed</h3>
        <div class="stats-big">${entriesProcessed.toLocaleString()}</div>
      </div>
      <div class="stats-card">
        <h3>Uptime</h3>
        <div class="stats-big">${formatDuration(uptimeSec)}</div>
      </div>
      <div class="stats-card">
        <h3>API Version</h3>
        <div class="stats-big">v${health.version}</div>
      </div>
      <div class="stats-card" style="grid-column: span 2">
        <h3>Supported Regions</h3>
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(80px,1fr));gap:6px;margin-top:8px">
          ${['A1','A2','A3','A4','A5','B1','B2','B3','C1','C2','C3','C4','C5','C6','C7','C8','C9','D1','D2','D3','D4','D5','E1','E2','E3','E4','E5','E6','E7','F1','F2','F3','F4','G1','H1','R0','Z0'].map(r =>
            `<span class="badge badge-region" style="text-align:center">${r}</span>`
          ).join('')}
        </div>
      </div>
      <div class="stats-card" style="grid-column: span 2">
        <h3>Authority Sources</h3>
        ${renderSourceBars()}
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="loading">Could not load statistics: ${escapeHtml(err.message)}</div>`;
  }
}

function renderSourceBars() {
  const sources = [
    { name: 'OpenAlex', tier: 0, status: 'active' },
    { name: 'Crossref', tier: 0, status: 'active' },
    { name: 'ORCID', tier: 0, status: 'active' },
    { name: 'CrossrefThesis', tier: 0, status: 'active' },
    { name: 'HAL', tier: 1, status: 'active' },
    { name: 'GND', tier: 1, status: 'active' },
    { name: 'Wikidata', tier: 1, status: 'active' },
    { name: 'OAI/BASE', tier: 1, status: 'active' },
    { name: 'zbMATH', tier: 1, status: 'active' },
    { name: 'MathSciNet', tier: 2, status: 'gated' },
    { name: 'Scopus', tier: 2, status: 'gated' },
    { name: 'Dimensions', tier: 2, status: 'gated' },
    { name: 'ProQuest', tier: 3, status: 'deferred' },
    { name: 'GoogleScholar', tier: 3, status: 'deferred' },
  ];

  return sources.map(s => {
    const color = s.status === 'active' ? 'var(--green)' : s.status === 'gated' ? 'var(--yellow)' : 'var(--text-dim)';
    const width = s.status === 'active' ? '100%' : s.status === 'gated' ? '30%' : '10%';
    return `
      <div class="stats-bar-row">
        <span class="stats-bar-label">${s.name}</span>
        <div class="stats-bar">
          <div class="stats-bar-fill" style="width:${width};background:${color}"></div>
        </div>
        <span class="stats-bar-count">T${s.tier}</span>
      </div>`;
  }).join('');
}

// ── Utilities ──────────────────────────────────────────────────────────────

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function escapeAttr(str) {
  return str.replace(/&/g, '&amp;').replace(/'/g, '&#39;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function countryFlag(code) {
  if (!code || code.length !== 2) return '';
  const offset = 127397;
  return String.fromCodePoint(...[...code.toUpperCase()].map(c => c.charCodeAt(0) + offset));
}

function copyToClipboard(text, btn) {
  navigator.clipboard.writeText(text).then(() => {
    const orig = btn.textContent;
    btn.textContent = 'Copied!';
    setTimeout(() => btn.textContent = orig, 1500);
  });
}

function formatDuration(seconds) {
  if (seconds < 60) return `${Math.floor(seconds)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
}
