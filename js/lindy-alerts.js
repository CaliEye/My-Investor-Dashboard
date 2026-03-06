// ============================================================
// Lindy Alert Watcher — Auto-fires webhook on high conviction
// Triggers when Confluence Score >= 8
// Cooldown: 5 minutes between alerts
//
// SECURITY: Set LINDY_WEBHOOK_URL in config/lindy_config.json
// (excluded from git via .gitignore) OR use a Cloudflare Worker
// proxy so the real URL never appears in the public repo.
// Format: { "webhook_url": "https://public.lindy.ai/..." }
// ============================================================

let LINDY_WEBHOOK_URL = null;

async function loadLindyConfig() {
  try {
    const res = await fetch('config/lindy_config.json');
    if (res.ok) {
      const cfg = await res.json();
      LINDY_WEBHOOK_URL = cfg.webhook_url || null;
    }
  } catch (_) {
    // Config not present — alerts disabled until URL is configured
  }
}
const ALERT_COOLDOWN_MS = 5 * 60 * 1000; // 5 minutes
let lastAlertTime = 0;

function checkAndFireAlert(score, asset, signal, timeframe, notes) {
  const confidence = parseInt(score, 10);
  if (isNaN(confidence) || confidence < 8) return;

  const now = Date.now();
  if (now - lastAlertTime < ALERT_COOLDOWN_MS) {
    console.log('[Lindy] Cooldown active — skipping alert.');
    return;
  }

  if (!LINDY_WEBHOOK_URL) {
    console.warn('[Lindy] Webhook URL not configured — skipping alert. Add to config/lindy_config.json.');
    return;
  }

  lastAlertTime = now;

  const payload = {
    asset: asset || 'DASHBOARD',
    confidence: confidence,
    signal: signal || 'confluence',
    timeframe: timeframe || 'multi',
    notes: notes || `Confluence score hit ${confidence}/10 on live dashboard`
  };

  fetch(LINDY_WEBHOOK_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
    .then(res => console.log('[Lindy] Alert fired — status:', res.status))
    .catch(err => console.error('[Lindy] Alert failed:', err));
}

// === MutationObserver — watches confluence score element ===
function startLindyWatcher() {
  // Try common selectors for the confluence score display
  const selectors = [
    '#confluence-score',
    '.confluence-score',
    '[data-metric="confluence"]',
    '#ai-confidence',
    '.ai-confidence',
    '#score-value',
    '.score-value'
  ];

  let targetEl = null;
  for (const sel of selectors) {
    targetEl = document.querySelector(sel);
    if (targetEl) {
      console.log('[Lindy] Watching element:', sel);
      break;
    }
  }

  if (!targetEl) {
    console.warn('[Lindy] Score element not found — retrying in 3s...');
    setTimeout(startLindyWatcher, 3000);
    return;
  }

  const observer = new MutationObserver(() => {
    const raw = targetEl.textContent.trim().replace(/[^0-9.]/g, '');
    const score = parseFloat(raw);
    if (!isNaN(score)) {
      checkAndFireAlert(score, 'DASHBOARD', 'confluence', 'multi', null);
    }
  });

  observer.observe(targetEl, { childList: true, subtree: true, characterData: true });
  console.log('[Lindy] Watcher active — monitoring for score >= 8');
}

// Start after DOM is ready — load config first, then begin watching
async function init() {
  await loadLindyConfig();
  startLindyWatcher();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
