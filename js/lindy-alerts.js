// ============================================================
// LINDY INVESTMENT ALERT SYSTEM
// Fires SMS alert when confluence confidence score hits 8+
// Webhook URL: https://public.lindy.ai/api/v1/webhooks/lindy/8b5fef48-2992-4ab8-b904-b16a9ca690b9
// ============================================================

const LINDY_WEBHOOK_URL = "https://public.lindy.ai/api/v1/webhooks/lindy/8b5fef48-2992-4ab8-b904-b16a9ca690b9";

// Track last alert time to avoid duplicate alerts (5 min cooldown)
let lastAlertTime = 0;
const ALERT_COOLDOWN_MS = 5 * 60 * 1000;

/**
 * Call this function whenever your confluence score updates.
 * It will fire an SMS alert if confidence >= 8 and cooldown has passed.
 *
 * @param {number} confidence  - The confluence score (0-10)
 * @param {string} asset       - Asset name e.g. "BTC", "ETH", "SPX"
 * @param {string} signal      - Signal direction e.g. "long", "short", "neutral"
 * @param {string} timeframe   - Timeframe e.g. "4H", "1D", "Weekly"
 * @param {string} notes       - Optional context e.g. "QQE + Wyckoff confluence"
 */
async function checkAndFireAlert(confidence, asset = "BTC", signal = "neutral", timeframe = "4H", notes = "") {
  if (confidence < 8) return; // Below threshold — stay silent

  const now = Date.now();
  if (now - lastAlertTime < ALERT_COOLDOWN_MS) {
    console.log(`[Lindy] Alert suppressed — cooldown active (${Math.round((ALERT_COOLDOWN_MS - (now - lastAlertTime)) / 1000)}s remaining)`);
    return;
  }

  const payload = {
    asset,
    confidence,
    signal,
    timeframe,
    notes: notes || `Confluence score hit ${confidence}/10 on ${asset}`
  };

  try {
    const response = await fetch(LINDY_WEBHOOK_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (response.ok) {
      lastAlertTime = now;
      console.log(`[Lindy] ⚡ Alert fired — ${asset} confidence ${confidence}/10`);
    } else {
      console.error(`[Lindy] Alert failed — HTTP ${response.status}`);
    }
  } catch (err) {
    console.error("[Lindy] Alert error:", err.message);
  }
}

/**
 * Hook into your existing confluence score element.
 * Watches for changes and auto-fires alerts.
 * Call initLindyAlertWatcher() once on page load.
 */
function initLindyAlertWatcher() {
  const scoreEl = document.querySelector(".confluence-score, #confluence-score, [data-confluence-score]");

  if (!scoreEl) {
    console.warn("[Lindy] Confluence score element not found — call checkAndFireAlert() manually.");
    return;
  }

  // Watch for DOM changes to the score element
  const observer = new MutationObserver(() => {
    const raw = scoreEl.textContent.trim();
    const score = parseFloat(raw);
    if (!isNaN(score)) {
      checkAndFireAlert(score, "BTC", score >= 9 ? "long" : "watch", "4H", `Auto-detected from dashboard score: ${score}/10`);
    }
  });

  observer.observe(scoreEl, { childList: true, subtree: true, characterData: true });
  console.log("[Lindy] Alert watcher active — monitoring confluence score.");
}

// Auto-init on page load
document.addEventListener("DOMContentLoaded", initLindyAlertWatcher);
