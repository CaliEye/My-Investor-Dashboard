// ============================================================
// MACRO DASHBOARD DATA LOADER
// Reads from data/data.json and populates all macro page widgets
// ============================================================

(async function () {
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

  try {
    const res = await fetch('./data/data.json', { cache: 'no-store' });
    if (!res.ok) throw new Error('Failed to load data.json');
    const d = await res.json();

    const m = d.macro || {};
    const s = d.sentiment || {};

    // Last update timestamp
    if (d.updated_utc) {
      const updated = new Date(d.updated_utc);
      const diffMin = Math.floor((Date.now() - updated) / 60000);
      let text, color;
      if (diffMin < 60) { text = `Updated ${diffMin}m ago`; color = '#10b981'; }
      else if (diffMin < 360) { text = `Updated ${Math.floor(diffMin / 60)}h ago`; color = '#f59e0b'; }
      else { text = `Updated ${Math.floor(diffMin / 60)}h ago — may be stale`; color = '#ef4444'; }
      const updEl = document.getElementById('macro-updated');
      if (updEl) { updEl.textContent = text; updEl.style.color = color; }
    }

    // Key metric tiles
    setEl('dxy-value', `<span class="data-metric">${m.dxy || '—'}</span>`);
    setEl('dxy-context', m.dxy_context || '—');
    setEl('us10y-value', `<span class="data-metric">${m.us10y_yield || '—'}</span>`);
    setEl('us10y-context', m.us10y_context || '—');
    setEl('fed-rate-value', `<span class="data-metric">${m.fed_funds_rate || '—'}</span>`);
    setEl('fed-rate-context', m.fed_rate_context || '—');
    setEl('cpi-value', `<span class="data-metric">${m.cpi || '—'}</span>`);
    setEl('cpi-context', m.cpi_context || '—');
    setEl('gdp-value', `<span class="data-metric">${m.gdp_growth || '—'}</span>`);
    setEl('gdp-context', m.gdp_context || '—');
    setEl('spx-value', `<span class="data-metric">${m.spx ? '$' + m.spx : '—'}</span>`);
    setEl('spx-context', m.spx_context || '—');

    // Macro Risk Indicator
    const riskLevel = m.risk_level || 0;
    const colorClass = riskColor(riskLevel);
    const label = riskLabel(riskLevel);
    setEl('macro-risk-content', `
      <div class="flex items-center gap-8 flex-wrap">
        <div class="text-center">
          <div class="text-7xl font-orbitron font-black ${colorClass}">${riskLevel}</div>
          <div class="text-xs tracking-widest mt-1 ${colorClass}">${label}</div>
          <div class="text-xs text-gray-500 mt-1">0–30 Low · 31–60 Moderate · 61–100 High</div>
        </div>
        <div class="flex-1 min-w-48">
          <div class="h-2 bg-gray-700 rounded mb-4">
            <div class="h-2 rounded transition-all duration-1000" style="width:${riskLevel}%; background:${riskLevel > 60 ? '#ef4444' : riskLevel > 30 ? '#f59e0b' : '#10b981'}"></div>
          </div>
          <p class="text-sm text-gray-300">${m.risk_context || '—'}</p>
        </div>
      </div>
    `);

    // Fear & Greed
    const fg = s.fear_greed_index;
    const fgLabel = s.fear_greed_label || '—';
    const fgMeaning = s.fear_greed_meaning || '—';
    const fgColor = fg <= 25 ? 'text-red-400' : fg <= 45 ? 'text-orange-300' : fg <= 55 ? 'text-yellow-300' : fg <= 75 ? 'text-green-300' : 'text-emerald-300';
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
        </div>
      </div>
    `);

    // Risk triggers
    const triggers = m.trigger_breakdown || d.triggers || [];
    if (triggers.length) {
      setEl('macro-triggers', triggers.map(t =>
        `<li class="flex items-start gap-2"><span class="text-red-400 mt-0.5">▸</span><span>${t}</span></li>`
      ).join(''));
    } else {
      setEl('macro-triggers', '<li class="text-gray-500">No active triggers data</li>');
    }

    // Macro context summary (using bias + trigger context)
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
        <p class="text-xs text-gray-500 border-t border-gray-700 pt-3">Rule: Macro leads all decisions. Check War Room confluence gate before any risk entry.</p>
      </div>
    `);

  } catch (err) {
    console.error('[MacroJS] Failed to load data:', err);
    document.getElementById('macro-risk-content').innerHTML =
      '<div class="text-red-400 text-sm">Failed to load macro data. Check console.</div>';
  }
})();
