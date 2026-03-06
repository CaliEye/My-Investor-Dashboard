// ============================================================
// MACRO DASHBOARD DATA LOADER v2.1
// Reads from data/data.json and populates all macro page widgets
// Includes: amber badge staleness logic, dynamic trend arrows,
//           color-coded metric tiles, and decision gate cross-ref
// ============================================================

(async function () {

// ── Helpers ──────────────────────────────────────────────
function riskColor(level) {
  if (level <= 30) return 'text-green-300';
  if (level <= 60) return 'text-yellow-300';
  return 'text-red-400';
}

function riskLabel(level) {
  if (level <= 30) return 'LOW RISK';
  if (level <= 60) return 'MODERATE RISK';
  return 'HIGH RISK';
}

function setEl(id, html) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = html;
}

// Returns { text, colorClass, badgeClass, isStale, isAmber }
function stalenessInfo(updatedUtcStr) {
  if (!updatedUtcStr) return { text: 'Unknown', colorClass: 'text-gray-500', badgeClass: '', isStale: false, isAmber: false };
  const updated = new Date(updatedUtcStr);
  const diffMin = Math.floor((Date.now() - updated) / 60000);
  if (diffMin < 60) {
    return { text: `Updated ${diffMin}m ago`, colorClass: 'text-green-400', badgeClass: '', isStale: false, isAmber: false };
  } else if (diffMin < 240) {
    // 1-4 hours: amber warning
    const hrs = Math.floor(diffMin / 60);
    const mins = diffMin % 60;
    return {
      text: `Updated ${hrs}h ${mins}m ago`,
      colorClass: 'text-yellow-400',
      badgeClass: 'stale-amber',
      isStale: false,
      isAmber: true
    };
  } else {
    // 4+ hours: red stale
    const hrs = Math.floor(diffMin / 60);
    return {
      text: `Updated ${hrs}h ago — DATA MAY BE STALE`,
      colorClass: 'text-red-400',
      badgeClass: 'stale-red',
      isStale: true,
      isAmber: false
    };
  }
}

// Trend arrow + color based on direction string or numeric delta
function trendArrow(context, value, thresholds) {
  // thresholds: { bullAbove, bearBelow } — optional numeric hints
  if (!context) return '';
  const ctx = context.toLowerCase();
  if (ctx.includes('rising') || ctx.includes('above') || ctx.includes('surge') || ctx.includes('high')) {
    return '<span class="text-red-400 ml-1 text-sm">▲</span>';
  }
  if (ctx.includes('falling') || ctx.includes('below') || ctx.includes('drop') || ctx.includes('low') || ctx.includes('weak')) {
    return '<span class="text-green-400 ml-1 text-sm">▼</span>';
  }
  if (ctx.includes('stable') || ctx.includes('contained') || ctx.includes('neutral') || ctx.includes('moderate')) {
    return '<span class="text-gray-400 ml-1 text-sm">→</span>';
  }
  return '';
}

// Color a metric tile value based on risk direction
function metricColor(id, value, context) {
  const ctx = (context || '').toLowerCase();
  // DXY: high = bearish for risk assets
  if (id === 'dxy') {
    const v = parseFloat(value);
    if (v > 106) return 'text-red-400';
    if (v > 100) return 'text-yellow-300';
    return 'text-green-300';
  }
  // 10Y yield: high = tighter conditions
  if (id === 'us10y') {
    const v = parseFloat(value);
    if (v > 5.0) return 'text-red-400';
    if (v > 4.0) return 'text-yellow-300';
    return 'text-green-300';
  }
  // SPX: context-driven
  if (id === 'spx') {
    if (ctx.includes('-') || ctx.includes('drop') || ctx.includes('below')) return 'text-red-400';
    if (ctx.includes('+') || ctx.includes('above') || ctx.includes('gain')) return 'text-green-300';
    return 'text-purple-300';
  }
  // CPI: high = bad
  if (id === 'cpi') {
    const v = parseFloat(value);
    if (v > 4.0) return 'text-red-400';
    if (v > 2.5) return 'text-yellow-300';
    return 'text-green-300';
  }
  // Fed rate: high = tight
  if (id === 'fed') {
    const v = parseFloat(value);
    if (v > 5.0) return 'text-red-400';
    if (v > 3.5) return 'text-yellow-300';
    return 'text-green-300';
  }
  return 'text-cyan-300';
}

// Inject a stale banner at the top of main if data is amber/red
function injectStaleBanner(info) {
  const existing = document.getElementById('stale-data-banner');
  if (existing) existing.remove();
  if (!info.isAmber && !info.isStale) return;

  const main = document.querySelector('main');
  if (!main) return;

  const banner = document.createElement('div');
  banner.id = 'stale-data-banner';
  banner.style.cssText = `
    display: flex; align-items: center; gap: 10px;
    padding: 10px 16px; border-radius: 6px; margin-bottom: 16px;
    font-size: 12px; font-family: monospace; letter-spacing: 0.05em;
    border: 1px solid ${info.isStale ? '#ef4444' : '#f59e0b'};
    background: ${info.isStale ? 'rgba(239,68,68,0.08)' : 'rgba(245,158,11,0.08)'};
    color: ${info.isStale ? '#ef4444' : '#f59e0b'};
  `;
  banner.innerHTML = `
    <span style="font-size:16px">${info.isStale ? '🔴' : '🟡'}</span>
    <span><strong>${info.isStale ? 'STALE DATA' : 'DATA AGING'}:</strong> ${info.text}. 
    ${info.isStale ? 'Macro signals may not reflect current conditions.' : 'Refresh or check data source.'}</span>
  `;
  main.insertBefore(banner, main.firstChild);
}

// ── Main ─────────────────────────────────────────────────
try {
  const res = await fetch('./data/data.json', { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to load data.json');
  const d = await res.json();

  const m = d.macro || {};
  const s = d.sentiment || {};
  const gate = d.decision_gate || {};

  // ── Staleness badge ──────────────────────────────────
  const staleInfo = stalenessInfo(d.updated_utc);
  const updEl = document.getElementById('macro-updated');
  if (updEl) {
    updEl.textContent = staleInfo.text;
    updEl.style.color = staleInfo.isStale ? '#ef4444' : staleInfo.isAmber ? '#f59e0b' : '#10b981';
    if (staleInfo.isAmber || staleInfo.isStale) {
      updEl.style.fontWeight = 'bold';
      updEl.title = `Data last updated: ${new Date(d.updated_utc).toLocaleString()}`;
    }
  }
  injectStaleBanner(staleInfo);

  // ── Key metric tiles with dynamic color + trend arrows ──
  const dxyColor = metricColor('dxy', m.dxy, m.dxy_context);
  const dxyArrow = trendArrow(m.dxy_context);
  setEl('dxy-value', `<span class="data-metric ${dxyColor}">${m.dxy || '—'}${dxyArrow}</span>`);
  setEl('dxy-context', m.dxy_context || '—');

  const us10yColor = metricColor('us10y', m.us10y_yield, m.us10y_context);
  const us10yArrow = trendArrow(m.us10y_context);
  setEl('us10y-value', `<span class="data-metric ${us10yColor}">${m.us10y_yield || '—'}${us10yArrow}</span>`);
  setEl('us10y-context', m.us10y_context || '—');

  const fedColor = metricColor('fed', m.fed_funds_rate, m.fed_rate_context);
  setEl('fed-rate-value', `<span class="data-metric ${fedColor}">${m.fed_funds_rate || '—'}</span>`);
  setEl('fed-rate-context', m.fed_rate_context || '—');

  const cpiColor = metricColor('cpi', m.cpi, m.cpi_context);
  setEl('cpi-value', `<span class="data-metric ${cpiColor}">${m.cpi || '—'}</span>`);
  setEl('cpi-context', m.cpi_context || '—');

  setEl('gdp-value', `<span class="data-metric text-cyan-300">${m.gdp_growth || '—'}</span>`);
  setEl('gdp-context', m.gdp_context || '—');

  const spxColor = metricColor('spx', m.spx, m.spx_context);
  const spxArrow = trendArrow(m.spx_context);
  setEl('spx-value', `<span class="data-metric ${spxColor}">${m.spx ? m.spx : '—'}${spxArrow}</span>`);
  setEl('spx-context', m.spx_context || '—');

  // ── Macro Risk Indicator ─────────────────────────────
  const riskLevel = m.risk_level || 0;
  const colorClass = riskColor(riskLevel);
  const label = riskLabel(riskLevel);
  setEl('macro-risk-content', `
    <div class="flex items-center gap-8 flex-wrap">
      <div class="text-center">
        <div class="text-7xl font-orbitron font-black ${colorClass}">${riskLevel}</div>
        <div class="text-xs tracking-widest mt-1 ${colorClass}">${label}</div>
        <div class="text-xs text-gray-500 mt-1">0-30 Low · 31-60 Moderate · 61-100 High</div>
      </div>
      <div class="flex-1 min-w-48">
        <div class="h-2 bg-gray-700 rounded mb-4">
          <div class="h-2 rounded transition-all duration-1000" style="width:${riskLevel}%; background:${riskLevel > 60 ? '#ef4444' : riskLevel > 30 ? '#f59e0b' : '#10b981'}"></div>
        </div>
        <p class="text-sm text-gray-300">${m.risk_context || '—'}</p>
        ${staleInfo.isAmber ? `<p class="text-xs text-yellow-400 mt-2">⚠ Data aging — verify before acting</p>` : ''}
        ${staleInfo.isStale ? `<p class="text-xs text-red-400 mt-2">🔴 Stale data — do not trade on this</p>` : ''}
      </div>
    </div>
  `);

  // ── Decision Gate Cross-Reference ────────────────────
  const gateScore = gate.confluence_score || 0;
  const gateMax = gate.max_score || 5;
  const gateHit = gate.threshold_hit || false;
  const gatePosture = gate.risk_posture || '—';
  const gateAction = gate.next_best_action || '—';
  const hardRule = gate.hard_rule_reminder || '';
  const gateColor = gateHit ? '#ef4444' : gateScore >= 3 ? '#f59e0b' : '#10b981';
  const gateLabel = gateHit ? 'THRESHOLD HIT' : gateScore >= 3 ? 'BUILDING' : 'CLEAR';

  // Inject decision gate panel if it doesn't exist yet
  let gatePanel = document.getElementById('decision-gate-panel');
  if (!gatePanel) {
    const riskPanel = document.querySelector('.hud-panel');
    if (riskPanel && riskPanel.parentNode) {
      gatePanel = document.createElement('div');
      gatePanel.id = 'decision-gate-panel';
      gatePanel.className = 'hud-panel p-6 mb-5';
      gatePanel.innerHTML = `
        <h3 class="text-lg font-orbitron mb-3 matrix-important" style="color:${gateColor}">CONFLUENCE GATE — ${gateLabel}</h3>
        <div id="gate-content"></div>
      `;
      riskPanel.parentNode.insertBefore(gatePanel, riskPanel.nextSibling);
    }
  }
  setEl('gate-content', `
    <div class="flex items-center gap-6 flex-wrap">
      <div class="text-center">
        <div class="text-5xl font-orbitron font-black" style="color:${gateColor}">${gateScore}/${gateMax}</div>
        <div class="text-xs tracking-widest mt-1" style="color:${gateColor}">${gateLabel}</div>
      </div>
      <div class="flex-1 min-w-48 space-y-2">
        <div class="h-2 bg-gray-700 rounded">
          <div class="h-2 rounded transition-all duration-1000" style="width:${(gateScore/gateMax)*100}%; background:${gateColor}"></div>
        </div>
        <p class="text-sm text-gray-300"><span class="text-gray-400">Posture:</span> <span class="font-bold" style="color:${gateColor}">${gatePosture}</span></p>
        <p class="text-sm text-gray-300">${gateAction}</p>
        ${hardRule ? `<p class="text-xs text-yellow-400 border border-yellow-800 rounded px-2 py-1 mt-2">⚡ ${hardRule}</p>` : ''}
      </div>
    </div>
    ${gate.signals && gate.signals.length ? `
      <div class="mt-3 pt-3 border-t border-gray-700">
        <div class="text-xs text-gray-400 mb-1 tracking-widest">ACTIVE SIGNALS:</div>
        ${gate.signals.map(sig => `<div class="text-xs text-yellow-300">▸ ${sig}</div>`).join('')}
      </div>
    ` : ''}
  `);

  // ── Fear & Greed ─────────────────────────────────────
  const fg = s.fear_greed_index;
  const fgLabel = s.fear_greed_label || '—';
  const fgMeaning = s.fear_greed_meaning || '—';
  const fgColor = fg <= 25 ? 'text-red-400' : fg <= 45 ? 'text-orange-300' : fg <= 55 ? 'text-yellow-300' : fg <= 75 ? 'text-green-300' : 'text-emerald-300';

  // Contrarian signal detection: deeply negative funding + price above support
  const fundingRate = parseFloat(s.funding_rate) || 0;
  const isContrarian = fundingRate < -0.02 && fg < 30;
  const contrarian = isContrarian ? `
    <div class="mt-3 px-3 py-2 rounded border border-cyan-700 bg-cyan-900 bg-opacity-20">
      <span class="text-cyan-300 text-xs font-bold tracking-widest">⚡ CONTRARIAN SETUP DETECTED</span>
      <p class="text-xs text-gray-300 mt-1">Funding deeply negative (shorts crowded) + Fear &amp; Greed below 30. Historically precedes short squeezes. Watch for volume confirmation before acting.</p>
    </div>
  ` : '';

  setEl('fear-greed-content', `
    <div class="flex items-center gap-8 flex-wrap">
      <div class="text-center">
        <div class="text-6xl font-orbitron font-black ${fgColor}">${fg !== undefined ? fg : '—'}</div>
        <div class="text-sm tracking-widest font-bold mt-1 ${fgColor}">${fgLabel}</div>
      </div>
      <div class="flex-1 min-w-48">
        <div class="h-2 bg-gray-700 rounded mb-3">
          <div class="h-2 rounded" style="width:${fg !== undefined ? fg : 0}%; background:${fg <= 25 ? '#ef4444' : fg <= 45 ? '#f97316' : fg <= 55 ? '#eab308' : '#10b981'}"></div>
        </div>
        <p class="text-sm text-gray-300">${fgMeaning}</p>
        <div class="flex justify-between text-xs text-gray-600 mt-1">
          <span>0 Extreme Fear</span><span>50 Neutral</span><span>100 Extreme Greed</span>
        </div>
        ${s.funding_rate ? `<p class="text-xs text-gray-400 mt-2">Funding rate: <span class="font-mono ${fundingRate < -0.02 ? 'text-cyan-300' : 'text-gray-300'}">${s.funding_rate}</span></p>` : ''}
      </div>
    </div>
    ${contrarian}
  `);

  // ── Risk Triggers ────────────────────────────────────
  const triggers = m.trigger_breakdown || d.triggers || [];
  if (triggers.length) {
    setEl('macro-triggers', triggers.map(t =>
      `<li class="flex items-start gap-2"><span class="text-red-400 mt-0.5">▸</span><span>${t}</span></li>`
    ).join(''));
  } else {
    setEl('macro-triggers', '<li class="text-gray-500">No active triggers data</li>');
  }

  // ── Macro Context Summary ────────────────────────────
  const bias = d.bias || '—';
  const unemploy = m.unemployment || '—';
  setEl('macro-news-content', `
    <div class="space-y-3 text-sm text-gray-300">
      <div class="flex gap-3 items-center">
        <span class="font-bold text-cyan-300 font-orbitron">BIAS:</span>
        <span class="font-bold ${bias === 'Bearish' ? 'text-red-400' : bias === 'Bullish' ? 'text-green-300' : 'text-yellow-300'}">${bias}</span>
      </div>
      <div><span class="text-gray-400">Unemployment:</span> <span class="text-white font-mono">${unemploy}</span> — ${m.unemployment_context || '—'}</div>
      <div><span class="text-gray-400">Next review:</span> <span class="text-gray-300 font-mono">${d.next_review_utc ? new Date(d.next_review_utc).toLocaleString() : '—'}</span></div>
      <p class="text-xs text-gray-500 border-t border-gray-700 pt-3">Rule: Macro leads all decisions. Check Confluence Gate before any risk entry.</p>
    </div>
  `);

} catch (err) {
  console.error('[MacroJS] Failed to load data:', err);
  const el = document.getElementById('macro-risk-content');
  if (el) el.innerHTML = '<div class="text-red-400 text-sm">Failed to load macro data. Check console.</div>';
}
})();
