/**
* lindy-alerts.js v2.0
* Intercepts TradingView signals, routes through SignalTally,
* cross-references Decision Gate, fires webhook on confluence.
* Patches data/data.json via GitHub API on Tier 2 black swan events.
*/

(function () {
 'use strict';

 // ── CONFIG ──────────────────────────────────────────────────────────────────
 const GITHUB_OWNER      = 'CaliEye';
 const GITHUB_REPO       = 'My-Investor-Dashboard';
 const GITHUB_DATA_PATH  = 'data/data.json';          // ← FIXED PATH
 // Load webhook URL from local config (gitignored). Empty in production — prevents public spam.
 const LINDY_WEBHOOK = (window.LINDY_CONFIG && window.LINDY_CONFIG.webhook_url) || '';

 // Load PAT from config (injected at build time or via window.LINDY_CONFIG)
 const GITHUB_TOKEN = (window.LINDY_CONFIG && window.LINDY_CONFIG.github_pat) || '';

 // ── TIER DEFINITIONS ────────────────────────────────────────────────────────
 const TIER2_KEYWORDS = [
   'BTC >20%', 'unemployment >7%', 'emergency rate', 'DXY >108', 'DXY <98',
   'gold >6000', 'S&P -5%', '10Y >5.5%', '10Y <3%', 'VIX >45',
   'circuit breaker', 'bear market'
 ];

 // ── DECISION GATE CROSS-REFERENCE ───────────────────────────────────────────
 async function crossRef(signal) {
   try {
     const res = await fetch(
       `https://raw.githubusercontent.com/${GITHUB_OWNER}/${GITHUB_REPO}/main/${GITHUB_DATA_PATH}`,
       { cache: 'no-store' }
     );
     if (!res.ok) { console.warn('[LindyAlerts] crossRef fetch failed:', res.status); return true; }
     const data = await res.json();
     const gate = data.decision_gate || {};
     // If gate says hold, suppress non-Tier2 alerts
     if (gate.status === 'HOLD' && !signal.tier2) {
       console.log('[LindyAlerts] Decision gate HOLD — suppressing Tier1 alert');
       return false;
     }
     return true;
   } catch (e) {
     console.warn('[LindyAlerts] crossRef error:', e);
     return true; // fail open
   }
 }

 // ── GITHUB DATA PATCH (Tier 2 only) ─────────────────────────────────────────
 async function patchDataJson(signal) {
   if (!GITHUB_TOKEN) { console.warn('[LindyAlerts] No GitHub PAT — skipping data patch'); return; }
   try {
     // 1. Get current SHA
     const getRes = await fetch(
       `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/contents/${GITHUB_DATA_PATH}`,
       { headers: { Authorization: `token ${GITHUB_TOKEN}`, Accept: 'application/vnd.github.v3+json' } }
     );
     if (!getRes.ok) { console.error('[LindyAlerts] SHA fetch failed:', getRes.status); return; }
     const fileData = await getRes.json();
     const sha = fileData.sha;
     const current = JSON.parse(atob(fileData.content.replace(/\n/g, '')));

     // 2. Inject black swan event
     if (!current.black_swan_events) current.black_swan_events = [];
     current.black_swan_events.unshift({
       timestamp: new Date().toISOString(),
       asset: signal.asset,
       signal: signal.signal,
       direction: signal.direction,
       score: signal.score
     });
     // Keep last 20
     current.black_swan_events = current.black_swan_events.slice(0, 20);

     // 3. Update decision gate
     current.decision_gate = {
       status: signal.direction === 'BEAR' ? 'HOLD' : 'ACTIVE',
       last_updated: new Date().toISOString(),
       trigger: signal.signal
     };

     // 4. PUT back
     const encoded = btoa(unescape(encodeURIComponent(JSON.stringify(current, null, 2))));
     const putRes = await fetch(
       `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/contents/${GITHUB_DATA_PATH}`,
       {
         method: 'PUT',
         headers: {
           Authorization: `token ${GITHUB_TOKEN}`,
           Accept: 'application/vnd.github.v3+json',
           'Content-Type': 'application/json'
         },
         body: JSON.stringify({
           message: `[Lindy] Black Swan: ${signal.asset} ${signal.signal}`,
           content: encoded,
           sha: sha
         })
       }
     );
     if (putRes.ok) {
       console.log('[LindyAlerts] data/data.json patched successfully');
     } else {
       const err = await putRes.json();
       console.error('[LindyAlerts] PUT failed:', putRes.status, err);
     }
   } catch (e) {
     console.error('[LindyAlerts] patchDataJson error:', e);
   }
 }

 // ── WEBHOOK FIRE ────────────────────────────────────────────────────────────
 async function fireWebhook(signal, score, level) {
   const payload = {
     source: 'lindy-alerts-dashboard',
     timestamp: new Date().toISOString(),
     asset: signal.asset,
     signal: signal.signal,
     direction: signal.direction,
     score: score,
     alert_level: level,
     tier2: signal.tier2 || false
   };
   if (!LINDY_WEBHOOK) {
     console.warn('[LindyAlerts] No webhook URL configured — alert suppressed. Add webhook_url to config/lindy_config.json');
     return;
   }
   try {
     await fetch(LINDY_WEBHOOK, {
       method: 'POST',
       headers: { 'Content-Type': 'application/json' },
       body: JSON.stringify(payload)
     });
     console.log('[LindyAlerts] Webhook fired:', level, signal.asset);
   } catch (e) {
     console.error('[LindyAlerts] Webhook error:', e);
   }
 }

 // ── SIGNAL INGESTION ─────────────────────────────────────────────────────────
 async function ingestSignal(raw) {
   const text = raw.toLowerCase();

   // Detect Tier 2
   const isTier2 = TIER2_KEYWORDS.some(kw => text.includes(kw.toLowerCase()));

   const signal = {
     asset: extractAsset(raw),
     signal: raw,
     direction: text.includes('bear') || text.includes('short') || text.includes('sell') ? 'BEAR' : 'BULL',
     tier2: isTier2,
     score: isTier2 ? 10 : 1
   };

   console.log('[LindyAlerts] Signal ingested:', signal);

   // Tier 2 — bypass everything, fire immediately
   if (isTier2) {
     console.warn('[LindyAlerts] TIER 2 BLACK SWAN — bypassing all filters');
     await patchDataJson(signal);
     await fireWebhook(signal, 10, 'TIER2_BLACK_SWAN');
     return;
   }

   // Tier 1 — run through tally + decision gate
   if (window.SignalTally) {
     const result = window.SignalTally.ingest(signal);
     const score = result.score;
     const allowed = await crossRef(signal);

     if (!allowed) return;

     if (score >= 7) {
       await fireWebhook(signal, score, 'PRE_CRISIS');
     } else if (score >= 5) {
       await fireWebhook(signal, score, 'ELEVATED_CONFLUENCE');
     } else if (score >= 3) {
       await fireWebhook(signal, score, 'CONFLUENCE');
     } else {
       console.log(`[LindyAlerts] Score ${score}/10 — below threshold, watching`);
     }
   }
 }

 // ── ASSET EXTRACTOR ──────────────────────────────────────────────────────────
 function extractAsset(text) {
   const assets = ['BTC', 'ETH', 'Gold', 'XAUUSD', 'SPY', 'QQQ', 'DXY', 'XLE', 'VIX', 'HYG', 'TLT', 'GLD', 'SLV'];
   for (const a of assets) {
     if (text.toUpperCase().includes(a.toUpperCase())) return a;
   }
   return 'UNKNOWN';
 }

 // ── MUTATION OBSERVER (watches dashboard for new signal elements) ─────────────
 const observer = new MutationObserver((mutations) => {
   for (const mutation of mutations) {
     for (const node of mutation.addedNodes) {
       if (node.nodeType === 1) {
         const text = node.textContent || '';
         if (text.includes('TIER1') || text.includes('TIER2')) {
           ingestSignal(text.trim());
         }
       }
     }
   }
 });

 observer.observe(document.body, { childList: true, subtree: true });

 // ── EXPOSE FOR MANUAL TESTING ────────────────────────────────────────────────
 window.LindyAlerts = { ingestSignal, patchDataJson, fireWebhook, crossRef };

 console.log('[LindyAlerts v2.0] Loaded — watching for signals. Path: data/data.json');
})();
