// ============================================================
// Signal Tally Engine — CaliEye Investor Dashboard
// Real-time scoring of TradingView signals against the
// decision gate. 72-hour rolling window. Tier1/Tier2 logic.
// ============================================================

const TALLY_STORAGE_KEY = 'calieye_signal_tally';
const TALLY_WINDOW_MS   = 72 * 60 * 60 * 1000; // 72 hours

// ── Tier 2 Black Swan Triggers (immediate SMS bypass) ──────
const TIER2_RULES = [
{ asset: 'BTC',    condition: s => s.move_pct && Math.abs(s.move_pct) >= 20,          label: 'BTC ±20% in 24h',            points: 5 },
{ asset: 'UNEMP',  condition: s => s.value    && s.value >= 7,                         label: 'Unemployment ≥7%',           points: 5 },
{ asset: 'FED',    condition: s => s.emergency === true,                                label: 'Fed Emergency Action',       points: 5 },
{ asset: 'DXY',    condition: s => s.value    && (s.value >= 108 || s.value <= 98),    label: 'DXY >108 or <98',            points: 5 },
{ asset: 'GOLD',   condition: s => s.value    && s.value >= 6000,                      label: 'Gold ≥$6,000',               points: 5 },
{ asset: 'SPY',    condition: s => s.move_pct && s.move_pct <= -5,                     label: 'SPY -5% single session',     points: 5 },
{ asset: 'YIELD10',condition: s => s.value    && (s.value >= 5.5 || s.rapid_drop),     label: '10Y ≥5.5% or rapid crash',   points: 5 },
{ asset: 'VIX',    condition: s => s.value    && s.value >= 45,                        label: 'VIX ≥45',                    points: 5 },
{ asset: 'MARKET', condition: s => s.circuit_breaker === true,                          label: 'Circuit Breaker Halt',       points: 5 },
{ asset: 'SPY',    condition: s => s.drawdown  && s.drawdown <= -20,                   label: 'S&P Bear Market -20%',       points: 5 },
];

// ── Tier 1 Confluence Scoring Rules ───────────────────────
const TIER1_RULES = [
// +2 point signals
{ asset: 'YIELD_CURVE', condition: s => s.uninverting || s.inverting,                  label: 'Yield Curve Event',          points: 2 },
{ asset: 'SAHM',        condition: s => s.value && s.value >= 0.3,                     label: 'Sahm Rule Building',         points: 2 },
{ asset: 'HYG',         condition: s => s.breakdown === true,                           label: 'HYG Credit Breakdown',       points: 2 },
{ asset: 'VIX',         condition: s => s.value && s.value >= 30,                      label: 'VIX ≥30',                    points: 2 },
{ asset: 'SPY',         condition: s => s.below_200sma === true,                        label: 'SPY Below 200SMA',           points: 2 },
{ asset: 'GOLD',        condition: s => s.key_level_break && s.volume_confirmed,        label: 'Gold Key Level + Volume',    points: 2 },
// +1 point signals
{ asset: 'DXY',         condition: s => s.value && (s.value >= 106 || s.value <= 100), label: 'DXY Extreme',                points: 1 },
{ asset: 'YIELD10',     condition: s => s.rapid_move === true,                          label: '10Y Rapid Move',             points: 1 },
{ asset: 'QQQ',         condition: s => s.below_200sma === true,                        label: 'QQQ Below 200SMA',           points: 1 },
{ asset: 'JOBLESS',     condition: s => s.value && s.value >= 300000,                  label: 'Jobless Claims Rising',      points: 1 },
{ asset: 'BTC_D',       condition: s => s.value && (s.value <= 40 || s.value >= 60),   label: 'BTC.D Extreme',              points: 1 },
{ asset: 'XLF',         condition: s => s.distribution === true,                        label: 'XLF/KRE Distribution',       points: 1 },
{ asset: 'ENERGY',      condition: s => s.move_pct && Math.abs(s.move_pct) >= 5,       label: 'Energy ±5% Move',            points: 1 },
{ asset: 'DEFENSE',     condition: s => s.new_52wk_high === true,                       label: 'Defense New 52wk High',      points: 1 },
];

// ── Historical Analogs ─────────────────────────────────────
const HISTORICAL_ANALOGS = [
{ minScore: 9,  label: '2008 Financial Crisis',  playbook: 'Max defensive. BTC accumulate on capitulation. Gold core position.' },
{ minScore: 7,  label: '2020 COVID Crash',        playbook: 'Liquidity event. BTC dip buy zone. Gold hold. Watch Fed response.' },
{ minScore: 5,  label: '2022 Rate Shock',         playbook: 'Risk-off rotation. DXY strength = metals headwind short-term.' },
{ minScore: 3,  label: '1970s Stagflation',       playbook: 'Gold and hard assets outperform. BTC analog unclear.' },
];

// ── Storage Helpers ────────────────────────────────────────
function loadTally() {
try {
  const raw = localStorage.getItem(TALLY_STORAGE_KEY);
  return raw ? JSON.parse(raw) : { signals: [], score: 0, tier2_fired: false, last_updated: null };
} catch (_) {
  return { signals: [], score: 0, tier2_fired: false, last_updated: null };
}
}

function saveTally(tally) {
try {
  localStorage.setItem(TALLY_STORAGE_KEY, JSON.stringify(tally));
} catch (_) {}
}

function pruneOldSignals(tally) {
const cutoff = Date.now() - TALLY_WINDOW_MS;
tally.signals = tally.signals.filter(s => s.timestamp > cutoff);
return tally;
}

function recalcScore(tally) {
tally.score = tally.signals.reduce((sum, s) => sum + (s.points || 0), 0);
return tally;
}

// ── Core: Ingest a new signal ──────────────────────────────
function ingestSignal(signalObj) {
// signalObj shape: { asset, value, move_pct, direction, below_200sma,
//                    breakdown, distribution, key_level_break, volume_confirmed,
//                    uninverting, inverting, rapid_move, rapid_drop,
//                    new_52wk_high, emergency, circuit_breaker, drawdown,
//                    source, raw_label }

let tally = loadTally();
tally = pruneOldSignals(tally);

const now = Date.now();
let matched = false;

// Check Tier 2 first
for (const rule of TIER2_RULES) {
  if (rule.asset === signalObj.asset && rule.condition(signalObj)) {
    const entry = {
      timestamp: now,
      asset: signalObj.asset,
      label: rule.label,
      points: rule.points,
      tier: 2,
      direction: signalObj.direction || 'UNKNOWN',
      source: signalObj.source || 'tradingview',
    };
    tally.signals.push(entry);
    tally.tier2_fired = true;
    matched = true;
    console.log('[Tally] TIER 2 FIRED:', rule.label);
    break;
  }
}

// Check Tier 1 if not Tier 2
if (!matched) {
  for (const rule of TIER1_RULES) {
    if (rule.asset === signalObj.asset && rule.condition(signalObj)) {
      const entry = {
        timestamp: now,
        asset: signalObj.asset,
        label: rule.label,
        points: rule.points,
        tier: 1,
        direction: signalObj.direction || 'UNKNOWN',
        source: signalObj.source || 'tradingview',
      };
      tally.signals.push(entry);
      matched = true;
      console.log('[Tally] Tier 1 logged:', rule.label, '+' + rule.points + 'pts');
      break;
    }
  }
}

if (!matched) {
  console.log('[Tally] Signal did not match any rule — discarded:', signalObj.asset);
  return null;
}

tally = recalcScore(tally);
tally.last_updated = now;
saveTally(tally);

renderTallyWidget(tally);
return tally;
}

// ── Decision Gate Cross-Reference ─────────────────────────
// Returns true only if BOTH the tally score AND the dashboard
// decision gate agree on direction before firing an alert.
function crossReferenceDecisionGate(tally, decisionGate) {
if (!decisionGate) return false;

const score = tally.score;
if (score < 3) return false; // Minimum threshold

// Count directional signals in tally
const bullSignals = tally.signals.filter(s => s.direction === 'BULL').length;
const bearSignals = tally.signals.filter(s => s.direction === 'BEAR').length;
const tallyDirection = bullSignals > bearSignals ? 'BULL' : bearSignals > bullSignals ? 'BEAR' : 'MIXED';

// Read dashboard regime
const regime = (decisionGate.regime && decisionGate.regime.label) ? decisionGate.regime.label.toUpperCase() : '';
const bullProb = decisionGate.regime ? (decisionGate.regime.bull_probability || 0) : 0;
const bearProb = decisionGate.regime ? (decisionGate.regime.bear_probability || 0) : 0;
const dashboardDirection = bullProb > bearProb ? 'BULL' : 'BEAR';

const agreed = tallyDirection === dashboardDirection || tallyDirection === 'MIXED';

console.log('[Tally] Cross-ref — Tally:', tallyDirection, '| Dashboard:', dashboardDirection, '| Agreed:', agreed);
return agreed;
}

// ── Historical Analog Lookup ───────────────────────────────
function getHistoricalAnalog(score) {
for (const analog of HISTORICAL_ANALOGS) {
  if (score >= analog.minScore) return analog;
}
return { label: 'No strong historical match', playbook: 'Maintain current positioning. Watch for confluence build.' };
}

// ── Confluence Alert Formatter ─────────────────────────────
function buildConfluenceAlertText(tally) {
const score = tally.score;
const bullSignals = tally.signals.filter(s => s.direction === 'BULL');
const bearSignals = tally.signals.filter(s => s.direction === 'BEAR');
const direction = bullSignals.length > bearSignals.length ? 'BULL' : 'BEAR';
const topSignals = [...tally.signals].sort((a, b) => b.points - a.points).slice(0, 3);
const analog = getHistoricalAnalog(score);

let text = `CONFLUENCE ALERT - ${direction} - Score: ${score}/10
`;
topSignals.forEach(s => { text += `> ${s.asset}: ${s.label} (+${s.points}pts)
`; });
text += `Historical match: ${analog.label}
`;
text += `Playbook: ${analog.playbook}
`;
const nextSignal = tally.signals[tally.signals.length - 1];
text += `Watch next: ${nextSignal ? nextSignal.asset + ' follow-through' : 'key level confirmation'}`;
return text;
}

// ── Render Tally Widget ────────────────────────────────────
function renderTallyWidget(tally) {
const container = document.getElementById('signal-tally-widget');
if (!container) return;

const score = tally.score;
const tier2 = tally.tier2_fired;
const signals = tally.signals;

// Score color
let scoreColor = '#4ade80'; // green
let alertLevel = 'WATCHING';
if (score >= 7)      { scoreColor = '#ff4444'; alertLevel = 'PRE-CRISIS'; }
else if (score >= 5) { scoreColor = '#ff8c00'; alertLevel = 'ELEVATED'; }
else if (score >= 3) { scoreColor = '#f2c960'; alertLevel = 'CONFLUENCE'; }

const analog = getHistoricalAnalog(score);

// Build signal rows
const rows = signals.slice(-8).reverse().map(s => {
  const age = Math.round((Date.now() - s.timestamp) / 3600000);
  const tierBadge = s.tier === 2
    ? `<span style="color:#ff4444;font-weight:700">T2</span>`
    : `<span style="color:#f2c960">T1</span>`;
  const dirColor = s.direction === 'BULL' ? '#4ade80' : s.direction === 'BEAR' ? '#ff4444' : '#888';
  return `<tr>
    <td style="padding:3px 8px;color:#ccc">${tierBadge}</td>
    <td style="padding:3px 8px;color:#fff;font-weight:600">${s.asset}</td>
    <td style="padding:3px 8px;color:#aaa;font-size:11px">${s.label}</td>
    <td style="padding:3px 8px;color:${dirColor};font-weight:700">${s.direction}</td>
    <td style="padding:3px 8px;color:#f2c960">+${s.points}</td>
    <td style="padding:3px 8px;color:#666;font-size:10px">${age}h ago</td>
  </tr>`;
}).join('');

container.innerHTML = `
  <div style="background:#0d0d0d;border:1px solid #222;border-radius:8px;padding:16px;font-family:'Courier New',monospace">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
      <span style="color:#888;font-size:11px;letter-spacing:2px">SIGNAL TALLY — 72HR WINDOW</span>
      <span style="color:#444;font-size:10px">${tally.last_updated ? new Date(tally.last_updated).toLocaleTimeString() : '—'}</span>
    </div>

    <div style="display:flex;gap:24px;margin-bottom:16px;align-items:flex-end">
      <div>
        <div style="color:#555;font-size:10px;letter-spacing:1px;margin-bottom:2px">CONFLUENCE SCORE</div>
        <div style="font-size:42px;font-weight:700;color:${scoreColor};line-height:1">${score}<span style="font-size:18px;color:#444">/10</span></div>
      </div>
      <div>
        <div style="color:#555;font-size:10px;letter-spacing:1px;margin-bottom:2px">STATUS</div>
        <div style="font-size:14px;font-weight:700;color:${scoreColor};letter-spacing:2px">${alertLevel}</div>
        ${tier2 ? '<div style="color:#ff4444;font-size:11px;font-weight:700;margin-top:4px">⚠ TIER 2 ACTIVE</div>' : ''}
      </div>
      <div style="margin-left:auto;text-align:right">
        <div style="color:#555;font-size:10px;letter-spacing:1px;margin-bottom:2px">ANALOG</div>
        <div style="color:#aaa;font-size:11px;max-width:180px;text-align:right">${analog.label}</div>
      </div>
    </div>

    ${signals.length > 0 ? `
    <table style="width:100%;border-collapse:collapse;font-size:12px">
      <thead>
        <tr style="border-bottom:1px solid #222">
          <th style="padding:4px 8px;color:#555;text-align:left;font-weight:400">TIER</th>
          <th style="padding:4px 8px;color:#555;text-align:left;font-weight:400">ASSET</th>
          <th style="padding:4px 8px;color:#555;text-align:left;font-weight:400">SIGNAL</th>
          <th style="padding:4px 8px;color:#555;text-align:left;font-weight:400">DIR</th>
          <th style="padding:4px 8px;color:#555;text-align:left;font-weight:400">PTS</th>
          <th style="padding:4px 8px;color:#555;text-align:left;font-weight:400">AGE</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>` : `<div style="color:#444;font-size:12px;text-align:center;padding:16px">No signals in 72hr window — patience compounds.</div>`}

    <div style="margin-top:12px;padding-top:12px;border-top:1px solid #1a1a1a">
      <div style="color:#555;font-size:10px;letter-spacing:1px;margin-bottom:4px">PLAYBOOK</div>
      <div style="color:#888;font-size:11px;line-height:1.5">${analog.playbook}</div>
    </div>

    <div style="margin-top:8px;display:flex;gap:8px">
      <button onclick="clearTally()" style="background:#1a1a1a;border:1px solid #333;color:#666;padding:4px 10px;font-size:10px;cursor:pointer;border-radius:4px;font-family:inherit">CLEAR TALLY</button>
      <button onclick="exportTally()" style="background:#1a1a1a;border:1px solid #333;color:#666;padding:4px 10px;font-size:10px;cursor:pointer;border-radius:4px;font-family:inherit">EXPORT JSON</button>
    </div>
  </div>
`;
}

// ── Utility: Clear & Export ────────────────────────────────
function clearTally() {
localStorage.removeItem(TALLY_STORAGE_KEY);
renderTallyWidget({ signals: [], score: 0, tier2_fired: false, last_updated: null });
}

function exportTally() {
const tally = loadTally();
const blob = new Blob([JSON.stringify(tally, null, 2)], { type: 'application/json' });
const url = URL.createObjectURL(blob);
const a = document.createElement('a');
a.href = url;
a.download = `signal-tally-${new Date().toISOString().slice(0,10)}.json`;
a.click();
URL.revokeObjectURL(url);
}

// ── Init: Load and render on page load ────────────────────
function initTally() {
let tally = loadTally();
tally = pruneOldSignals(tally);
tally = recalcScore(tally);
saveTally(tally);
renderTallyWidget(tally);
console.log('[Tally] Initialized — score:', tally.score, '| signals:', tally.signals.length);
}

if (document.readyState === 'loading') {
document.addEventListener('DOMContentLoaded', initTally);
} else {
initTally();
}

// ── Exports for use by lindy-alerts.js ────────────────────
window.SignalTally = {
ingest: ingestSignal,
load: loadTally,
crossRef: crossReferenceDecisionGate,
buildAlert: buildConfluenceAlertText,
render: renderTallyWidget,
};
