// ============================================================
// Lindy Alert Watcher — CaliEye Investor Dashboard
// v2.0 — Full pipeline integration
//
// What this does:
//   1. Watches dashboard confluence score (MutationObserver)
//   2. Ingests signals into SignalTally (72hr rolling window)
//   3. Cross-references tally against decision gate before alerting
//   4. Tier 2 black swan → fires webhook AND patches data.json via GitHub API
//   5. Confluence threshold (score ≥3 from 2+ asset classes) → SMS via webhook
//
// SECURITY: Webhook URL loaded from config/lindy_config.json (gitignored)
// GitHub token for data.json patching loaded from same config file.
// Format: { "webhook_url": "...", "github_token": "...", "github_repo": "CaliEye/My-Investor-Dashboard" }
// ============================================================

// ── Config ─────────────────────────────────────────────────
let LINDY_WEBHOOK_URL  = null;
let GITHUB_TOKEN       = null;
let GITHUB_REPO        = 'CaliEye/My-Investor-Dashboard';
let GITHUB_DATA_PATH   = 'data.json';

const ALERT_COOLDOWN_MS     = 5 * 60 * 1000;   // 5 min between standard alerts
const TIER2_COOLDOWN_MS     = 60 * 60 * 1000;  // 1 hr between Tier 2 patches
let lastAlertTime           = 0;
let lastTier2PatchTime      = 0;
let decisionGateCache       = null;

// ── Load Config ────────────────────────────────────────────
async function loadLindyConfig() {
try {
  const res = await fetch('config/lindy_config.json');
  if (res.ok) {
    const cfg = await res.json();
    LINDY_WEBHOOK_URL = cfg.webhook_url  || null;
    GITHUB_TOKEN      = cfg.github_token || null;
    GITHUB_REPO       = cfg.github_repo  || GITHUB_REPO;
  }
} catch (_) {
  console.warn('[Lindy] Config not found — alerts and patching disabled.');
}
}

// ── Load Decision Gate from data.json ─────────────────────
async function loadDecisionGate() {
try {
  const res = await fetch('data.json?t=' + Date.now());
  if (res.ok) {
    const data = await res.json();
    decisionGateCache = data.decision_gate || data || null;
    console.log('[Lindy] Decision gate loaded — regime:', decisionGateCache?.regime?.label || 'unknown');
  }
} catch (e) {
  console.warn('[Lindy] Could not load decision gate:', e.message);
}
return decisionGateCache;
}

// ── Patch data.json via GitHub API (Tier 2 only) ──────────
async function patchDataJson(tier2Label, direction, score) {
if (!GITHUB_TOKEN) {
  console.warn('[Lindy] No GitHub token — cannot patch data.json');
  return false;
}

const now = Date.now();
if (now - lastTier2PatchTime < TIER2_COOLDOWN_MS) {
  console.log('[Lindy] Tier 2 patch cooldown active — skipping.');
  return false;
}

try {
  // 1. Get current file SHA
  const metaRes = await fetch(
    `https://api.github.com/repos/${GITHUB_REPO}/contents/${GITHUB_DATA_PATH}`,
    { headers: { Authorization: `token ${GITHUB_TOKEN}`, Accept: 'application/vnd.github.v3+json' } }
  );
  if (!metaRes.ok) throw new Error('Could not fetch data.json metadata');
  const meta = await metaRes.json();
  const currentSha = meta.sha;

  // 2. Decode current content
  const currentContent = JSON.parse(atob(meta.content.replace(/\n/g, '')));

  // 3. Patch the decision_gate block
  const timestamp = new Date().toISOString();
  if (!currentContent.decision_gate) currentContent.decision_gate = {};
  if (!currentContent.decision_gate.tier2_events) currentContent.decision_gate.tier2_events = [];

  currentContent.decision_gate.tier2_events.unshift({
    timestamp,
    label: tier2Label,
    direction,
    confluence_score: score,
    auto_patched: true,
  });

  // Keep only last 10 Tier 2 events
  currentContent.decision_gate.tier2_events = currentContent.decision_gate.tier2_events.slice(0, 10);

  // Update regime alert flag
  currentContent.decision_gate.last_tier2_alert = timestamp;
  currentContent.decision_gate.tier2_active = true;

  // 4. Encode and push
  const newContent = btoa(unescape(encodeURIComponent(JSON.stringify(currentContent, null, 2))));
  const pushRes = await fetch(
    `https://api.github.com/repos/${GITHUB_REPO}/contents/${GITHUB_DATA_PATH}`,
    {
      method: 'PUT',
      headers: {
        Authorization: `token ${GITHUB_TOKEN}`,
        Accept: 'application/vnd.github.v3+json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: `auto: Tier 2 black swan — ${tier2Label} [${timestamp}]`,
        content: newContent,
        sha: currentSha,
      }),
    }
  );

  if (pushRes.ok) {
    lastTier2PatchTime = now;
    console.log('[Lindy] data.json patched — Tier 2 event recorded:', tier2Label);
    return true;
  } else {
    const err = await pushRes.json();
    console.error('[Lindy] GitHub push failed:', err.message);
    return false;
  }
} catch (e) {
  console.error('[Lindy] patchDataJson error:', e.message);
  return false;
}
}

// ── Fire Webhook (SMS via Lindy) ───────────────────────────
function fireWebhook(payload) {
if (!LINDY_WEBHOOK_URL) {
  console.warn('[Lindy] Webhook URL not configured — skipping.');
  return;
}
fetch(LINDY_WEBHOOK_URL, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload),
})
  .then(res => console.log('[Lindy] Webhook fired — status:', res.status))
  .catch(err => console.error('[Lindy] Webhook failed:', err));
}

// ── Main Alert Logic ───────────────────────────────────────
async function checkAndFireAlert(score, asset, signal, timeframe, notes, signalObj) {
const now = Date.now();

// Build signal object for tally ingestion
const ingestObj = signalObj || {
  asset: asset || 'DASHBOARD',
  direction: notes && notes.includes('BULL') ? 'BULL' : notes && notes.includes('BEAR') ? 'BEAR' : 'UNKNOWN',
  source: 'dashboard_observer',
};

// Ingest into tally engine
let tally = null;
if (window.SignalTally) {
  tally = window.SignalTally.ingest(ingestObj);
  if (!tally) tally = window.SignalTally.load();
}

const tallyScore = tally ? tally.score : parseInt(score, 10);
const tier2Fired = tally ? tally.tier2_fired : false;

// ── Tier 2: Immediate bypass — no cross-ref needed ────────
if (tier2Fired) {
  const tier2Signal = tally.signals.find(s => s.tier === 2);
  const alertText = window.SignalTally
    ? window.SignalTally.buildAlert(tally)
    : `TIER 2 BLACK SWAN: ${asset} — ${signal}`;

  console.log('[Lindy] TIER 2 BLACK SWAN — bypassing cross-ref, firing immediately');

  // Fire SMS webhook
  fireWebhook({
    tier: 2,
    asset: asset || 'DASHBOARD',
    signal: tier2Signal ? tier2Signal.label : signal,
    confluence_score: tallyScore,
    direction: ingestObj.direction,
    alert_text: alertText,
    timestamp: new Date().toISOString(),
    notes: 'TIER 2 BLACK SWAN — immediate bypass',
  });

  // Patch data.json
  await patchDataJson(
    tier2Signal ? tier2Signal.label : signal,
    ingestObj.direction,
    tallyScore
  );

  return;
}

// ── Tier 1: Cross-reference decision gate before alerting ─
if (tallyScore < 3) {
  console.log('[Lindy] Score below threshold (' + tallyScore + '/10) — watching.');
  return;
}

if (now - lastAlertTime < ALERT_COOLDOWN_MS) {
  console.log('[Lindy] Cooldown active — skipping alert.');
  return;
}

// Load decision gate if not cached
if (!decisionGateCache) await loadDecisionGate();

// Cross-reference: both must agree
const gateAgrees = window.SignalTally
  ? window.SignalTally.crossRef(tally, decisionGateCache)
  : true; // fallback: fire if no tally engine

if (!gateAgrees) {
  console.log('[Lindy] Decision gate disagrees with tally direction — holding alert. Score:', tallyScore);
  return;
}

// Both agree — fire confluence alert
lastAlertTime = now;
const alertText = window.SignalTally
  ? window.SignalTally.buildAlert(tally)
  : `CONFLUENCE ALERT — Score: ${tallyScore}/10 | ${asset}: ${signal}`;

console.log('[Lindy] Confluence confirmed — firing alert. Score:', tallyScore);

fireWebhook({
  tier: 1,
  asset: asset || 'DASHBOARD',
  signal: signal || 'confluence',
  confluence_score: tallyScore,
  direction: ingestObj.direction,
  alert_text: alertText,
  timestamp: new Date().toISOString(),
  notes: notes || `Confluence score ${tallyScore}/10 — decision gate confirmed`,
});
}

// ── MutationObserver — watches confluence score element ────
function startLindyWatcher() {
const selectors = [
  '#confluence-score', '.confluence-score',
  '[data-metric="confluence"]',
  '#ai-confidence', '.ai-confidence',
  '#score-value', '.score-value',
];

let targetEl = null;
for (const sel of selectors) {
  targetEl = document.querySelector(sel);
  if (targetEl) { console.log('[Lindy] Watching element:', sel); break; }
}

if (!targetEl) {
  console.warn('[Lindy] Score element not found — retrying in 3s...');
  setTimeout(startLindyWatcher, 3000);
  return;
}

const observer = new MutationObserver(() => {
  const raw   = targetEl.textContent.trim().replace(/[^0-9.]/g, '');
  const score = parseFloat(raw);
  if (!isNaN(score)) {
    checkAndFireAlert(score, 'DASHBOARD', 'confluence', 'multi', null, null);
  }
});

observer.observe(targetEl, { childList: true, subtree: true, characterData: true });
console.log('[Lindy] Watcher active — monitoring for confluence threshold');
}

// ── Init ───────────────────────────────────────────────────
async function init() {
await loadLindyConfig();
await loadDecisionGate();
startLindyWatcher();
console.log('[Lindy] v2.0 initialized — tally + cross-ref + Tier2 patch active');
}

if (document.readyState === 'loading') {
document.addEventListener('DOMContentLoaded', init);
} else {
init();
}

// ── Public API ─────────────────────────────────────────────
// Call this from any page to manually inject a TradingView signal:
// LindyAlerts.injectSignal({ asset: 'GOLD', value: 3200, key_level_break: true, volume_confirmed: true, direction: 'BULL' })
window.LindyAlerts = {
injectSignal: (signalObj) => checkAndFireAlert(0, signalObj.asset, signalObj.label || '', 'manual', null, signalObj),
loadGate:     loadDecisionGate,
patchData:    patchDataJson,
fireWebhook:  fireWebhook,
};
