// ============================================================
// Lindy Alert Watcher — Auto-fires webhook on high conviction
// Webhook: https://public.lindy.ai/api/v1/webhooks/lindy/8b5fef48-2992-4ab8-b904-b16a9ca690b9
// Triggers when Confluence Score >= 8
// Cooldown: 5 minutes between alerts
// ============================================================

const LINDY_WEBHOOK_URL = 'https://public.lindy.ai/api/v1/webhooks/lindy/8b5fef48-2992-4ab8-b904-b16a9ca690b9';
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

// Start after DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', startLindyWatcher);
} else {
  startLindyWatcher();
}
