/**
 * ENDGAME: Investment Command Center
 * Dashboard Data Engine v1.0
 * Macro-first. Confluence-driven. Zero noise.
 */

'use strict';

// ── CONFIG ──────────────────────────────────────────────────────────────────
const ENDGAME = {
  refreshInterval: 5 * 60 * 1000, // 5 minutes
  fredApiKey: (typeof ENDGAME_CONFIG !== 'undefined' && ENDGAME_CONFIG.fredApiKey) || '',
  dataPath: './data/data.json',
  insightsPath: './data/ai_insights.json',
  fredSeries: {
    unemployment: 'UNRATE',
    fedFunds:     'FEDFUNDS',
    cpi:          'CPIAUCSL',
    gdp:          'GDP',
    yieldCurve:   'T10Y2Y',
  },
};

// ── STATE ────────────────────────────────────────────────────────────────────
const state = {
  data:     null,
  insights: null,
  fred:     {},
  lastUpdate: null,
};

// ── INIT ─────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  updateClock();
  setInterval(updateClock, 1000);
  loadAll();
  setInterval(loadAll, ENDGAME.refreshInterval);
});

// ── CLOCK ────────────────────────────────────────────────────────────────────
function updateClock() {
  const el = document.getElementById('last-updated');
  if (!el) return;
  const now = new Date();
  el.textContent = now.toLocaleTimeString('en-US', {
    hour: '2-digit', minute: '2-digit', second: '2-digit',
    hour12: true, timeZoneName: 'short'
  });
}

// ── LOAD ALL DATA ─────────────────────────────────────────────────────────────
async function loadAll() {
  try {
    const [dataRes, insightsRes] = await Promise.allSettled([
      fetch(ENDGAME.dataPath + '?t=' + Date.now()),
      fetch(ENDGAME.insightsPath + '?t=' + Date.now()),
    ]);

    if (dataRes.status === 'fulfilled' && dataRes.value.ok) {
      state.data = await dataRes.value.json();
      setStatus('ai-status-dot', 'ai-status-text', true);
    } else {
      setStatus('ai-status-dot', 'ai-status-text', false);
    }

    if (insightsRes.status === 'fulfilled' && insightsRes.value.ok) {
      state.insights = await insightsRes.value.json();
    }

    state.lastUpdate = new Date();
    renderAll();
    loadFredData();

  } catch (err) {
    console.warn('[Endgame] Data load error:', err);
    renderFallback();
  }
}

// ── FRED DATA ─────────────────────────────────────────────────────────────────
async function loadFredData() {
  // If no API key, use embedded fallback values from data.json
  if (!ENDGAME.fredApiKey) {
    renderFredFallback();
    setStatus('fred-status-dot', 'fred-status-text', false, 'NO KEY');
    return;
  }

  try {
    const series = ['UNRATE', 'FEDFUNDS'];
    const results = await Promise.allSettled(
      series.map(s =>
        fetch(`https://api.stlouisfed.org/fred/series/observations?series_id=${s}&api_key=${ENDGAME.fredApiKey}&file_type=json&sort_order=desc&limit=2`)
          .then(r => r.json())
      )
    );

    const [unrate, fedfunds] = results;

    if (unrate.status === 'fulfilled' && unrate.value.observations) {
      const obs = unrate.value.observations;
      const current = parseFloat(obs[0].value);
      const prev    = parseFloat(obs[1].value);
      state.fred.unemployment = { current, prev, delta: current - prev };
    }

    if (fedfunds.status === 'fulfilled' && fedfunds.value.observations) {
      const obs = fedfunds.value.observations;
      const current = parseFloat(obs[0].value);
      const prev    = parseFloat(obs[1].value);
      state.fred.fedFunds = { current, prev, delta: current - prev };
    }

    setStatus('fred-status-dot', 'fred-status-text', true);
    renderFredCards();

  } catch (err) {
    console.warn('[Endgame] FRED error:', err);
    setStatus('fred-status-dot', 'fred-status-text', false, 'ERROR');
    renderFredFallback();
  }
}

// ── RENDER ALL ────────────────────────────────────────────────────────────────
function renderAll() {
  renderMacroCards();
  renderRegime();
  renderConfluence();
  renderSectors();
  renderAIIntelligence();
  renderOperationalIntel();
  renderSystemStatus();
}

// ── MACRO CARDS ───────────────────────────────────────────────────────────────
function renderMacroCards() {
  const d = state.data;
  if (!d) return;

  // Gold
  const gold = d.gold || d.assets?.gold || {};
  setMacroCard('gold', {
    price:  formatPrice(gold.price, '$', 2),
    change: formatChange(gold.change_pct),
    signal: gold.signal || wyckoffSignal(gold.change_pct),
    bar:    normalizeBar(gold.price, 1800, 3200),
    up:     (gold.change_pct || 0) >= 0,
  });

  // SPY / S&P 500
  const spy = d.spy || d.assets?.spy || d.sp500 || {};
  setMacroCard('spy', {
    price:  formatPrice(spy.price, '$', 2),
    change: formatChange(spy.change_pct),
    signal: spy.signal || wyckoffSignal(spy.change_pct),
    bar:    normalizeBar(spy.price, 350, 650),
    up:     (spy.change_pct || 0) >= 0,
  });

  // 10Y Yield
  const yield10 = d.yield10y || d.assets?.yield10y || d.tnx || {};
  setMacroCard('yield', {
    price:  formatPrice(yield10.rate || yield10.price, '', 2) + '%',
    change: formatChange(yield10.change_pct || yield10.change),
    signal: yield10.signal || yieldSignal(yield10.rate || yield10.price),
    bar:    normalizeBar(yield10.rate || yield10.price, 2, 6),
    up:     (yield10.change_pct || 0) >= 0,
  });

  // Unemployment - prefer FRED live, fall back to data.json
  if (!state.fred.unemployment) {
    const unemp = d.unemployment || d.macro?.unemployment || {};
    setMacroCard('unemp', {
      price:  formatPrice(unemp.rate || unemp.value, '', 1) + '%',
      change: formatChange(unemp.change || unemp.delta),
      signal: unemp.signal || unempSignal(unemp.rate || unemp.value),
      bar:    normalizeBar(unemp.rate || unemp.value, 3, 8),
      up:     false,
    });
  }

  // Fed Funds - prefer FRED live, fall back to data.json
  if (!state.fred.fedFunds) {
    const fed = d.fedFunds || d.macro?.fedFunds || d.fed_funds || {};
    setMacroCard('fed', {
      price:  formatPrice(fed.rate || fed.value, '', 2) + '%',
      change: formatChange(fed.change || fed.delta),
      signal: fed.signal || fedSignal(fed.rate || fed.value),
      bar:    normalizeBar(fed.rate || fed.value, 0, 6),
      up:     false,
    });
  }
}

function setMacroCard(id, { price, change, signal, bar, up }) {
  setText(`${id}-price`, price);
  const changeEl = document.getElementById(`${id}-change`);
  if (changeEl) {
    changeEl.textContent = change;
    changeEl.className = 'macro-card-change ' + (up ? 'val-up' : 'val-down');
  }
  setText(`${id}-signal`, signal);
  const barEl = document.getElementById(`${id}-bar`);
  if (barEl) barEl.style.width = Math.min(100, Math.max(0, bar)) + '%';
}

// ── FRED FALLBACK ─────────────────────────────────────────────────────────────
function renderFredFallback() {
  const d = state.data;
  if (!d) return;

  const unemp = d.unemployment || d.macro?.unemployment || {};
  setMacroCard('unemp', {
    price:  formatPrice(unemp.rate || unemp.value || 4.1, '', 1) + '%',
    change: formatChange(unemp.change || 0),
    signal: unempSignal(unemp.rate || unemp.value || 4.1),
    bar:    normalizeBar(unemp.rate || unemp.value || 4.1, 3, 8),
    up:     false,
  });

  const fed = d.fedFunds || d.macro?.fedFunds || d.fed_funds || {};
  setMacroCard('fed', {
    price:  formatPrice(fed.rate || fed.value || 4.33, '', 2) + '%',
    change: formatChange(fed.change || 0),
    signal: fedSignal(fed.rate || fed.value || 4.33),
    bar:    normalizeBar(fed.rate || fed.value || 4.33, 0, 6),
    up:     false,
  });
}

function renderFredCards() {
  if (state.fred.unemployment) {
    const u = state.fred.unemployment;
    setMacroCard('unemp', {
      price:  u.current.toFixed(1) + '%',
      change: formatChange(u.delta),
      signal: unempSignal(u.current),
      bar:    normalizeBar(u.current, 3, 8),
      up:     false,
    });
  }
  if (state.fred.fedFunds) {
    const f = state.fred.fedFunds;
    setMacroCard('fed', {
      price:  f.current.toFixed(2) + '%',
      change: formatChange(f.delta),
      signal: fedSignal(f.current),
      bar:    normalizeBar(f.current, 0, 6),
      up:     false,
    });
  }
}

// ── REGIME ────────────────────────────────────────────────────────────────────
function renderRegime() {
  const ins = state.insights;
  if (!ins) return;

  const regime = ins.regime || ins.market_regime || {};
  const label  = regime.label || regime.type || 'NEUTRAL';
  const desc   = regime.description || regime.summary || 'Regime analysis loading...';
  const bull   = regime.bull_probability || regime.bullProb || 50;
  const bear   = regime.bear_probability || regime.bearProb || 50;

  const badge = document.getElementById('regime-badge');
  if (badge) {
    badge.textContent = label.toUpperCase();
    badge.className = 'regime-badge ' + regimeClass(label);
  }

  setText('regime-description', desc);
  setText('bull-prob', bull + '%');
  setText('bear-prob', bear + '%');

  const bullBar = document.getElementById('bull-bar');
  const bearBar = document.getElementById('bear-bar');
  if (bullBar) bullBar.style.width = bull + '%';
  if (bearBar) bearBar.style.width = bear + '%';

  const updated = document.getElementById('regime-updated');
  if (updated && regime.updated) {
    updated.textContent = new Date(regime.updated).toLocaleDateString();
  }
}

// ── CONFLUENCE ────────────────────────────────────────────────────────────────
function renderConfluence() {
  const ins = state.insights;
  if (!ins) return;

  const conf  = ins.confluence || ins.confluence_score || {};
  const score = conf.score || conf.value || 0;
  const label = conf.label || conf.verdict || verdictFromScore(score);
  const detail = conf.detail || conf.description || '';

  setText('confluence-score', score);

  // Animate the ring
  const fill = document.getElementById('confluence-fill');
  if (fill) {
    const angle = (score / 100) * 360;
    const color = score >= 70 ? 'var(--acid)' : score >= 40 ? 'var(--amber)' : 'var(--blood)';
    fill.style.background = `conic-gradient(${color} 0deg, ${color} ${angle}deg, var(--ghost) ${angle}deg, var(--ghost) 360deg)`;
  }

  const scoreEl = document.getElementById('confluence-score');
  if (scoreEl) {
    scoreEl.style.color = score >= 70 ? 'var(--acid)' : score >= 40 ? 'var(--amber)' : 'var(--blood)';
    scoreEl.style.textShadow = score >= 70
      ? '0 0 12px rgba(57,255,20,0.6)'
      : score >= 40
      ? '0 0 12px rgba(255,140,0,0.6)'
      : '0 0 12px rgba(255,34,34,0.6)';
  }

  const verdict = document.getElementById('confluence-verdict');
  if (verdict) {
    verdict.textContent = label.toUpperCase();
    verdict.className = 'regime-badge ' + (score >= 70 ? 'regime-bull' : score >= 40 ? 'regime-neutral' : 'regime-bear');
  }

  setText('confluence-detail', detail);

  // Show alert banner if score >= 75
  const banner = document.getElementById('alert-banner');
  if (banner) {
    if (score >= 75) {
      banner.classList.remove('hidden');
      setText('alert-banner-text', `High-confluence signal detected: ${label}. ${detail.split('.')[0]}.`);
      setText('alert-banner-score', score + '/100');
    } else {
      banner.classList.add('hidden');
    }
  }
}

// ── SECTORS ───────────────────────────────────────────────────────────────────
function renderSectors() {
  const d = state.data;
  if (!d) return;

  const sectors = d.sectors || d.etfs || {};
  const tickers = ['GLD','XLE','XLF','XLK','XLU','XLV','TLT','DXY'];

  tickers.forEach(ticker => {
    const s = sectors[ticker] || sectors[ticker.toLowerCase()] || {};
    const price  = s.price || s.close || null;
    const change = s.change_pct || s.changePct || s.change || null;
    const signal = s.signal || wyckoffSignal(change);

    if (price !== null) {
      setText(`sec-${ticker}-price`, formatPrice(price, '$', 2));
    }
    if (change !== null) {
      const el = document.getElementById(`sec-${ticker}-change`);
      if (el) {
        el.textContent = formatChange(change);
        el.className = 'sector-change ' + (change >= 0 ? 'val-up' : 'val-down');
      }
    }
    setText(`sec-${ticker}-signal`, signal);
  });
}

// ── AI INTELLIGENCE ───────────────────────────────────────────────────────────
function renderAIIntelligence() {
  const ins = state.insights;
  if (!ins) return;

  // Wyckoff
  const wyckoff = ins.wyckoff || ins.wyckoff_analysis || {};
  const wyckoffText = wyckoff.summary || wyckoff.description || wyckoff.text || '';
  if (wyckoffText) setText('wyckoff-analysis', wyckoffText);

  // Rotation
  const rotation = ins.rotation || ins.cross_asset_rotation || {};
  const rotText  = rotation.summary || rotation.description || '';
  if (rotText) setText('rotation-analysis', rotText);

  // Rotation table
  const assets = rotation.assets || rotation.signals || [];
  const tbody  = document.getElementById('rotation-table');
  if (tbody && assets.length > 0) {
    tbody.innerHTML = assets.map(a => {
      const sig = a.signal || a.direction || '-';
      const str = a.strength || a.score || '-';
      const cls = sig.toLowerCase().includes('long') || sig.toLowerCase().includes('bull')
        ? 'val-up'
        : sig.toLowerCase().includes('short') || sig.toLowerCase().includes('bear')
        ? 'val-down'
        : 'val-flat';
      return `<tr>
        <td style="color:var(--ice);font-weight:700;">${a.ticker || a.asset || '-'}</td>
        <td class="${cls}">${sig}</td>
        <td>${str}</td>
      </tr>`;
    }).join('');
  }
}

// ── OPERATIONAL INTEL ─────────────────────────────────────────────────────────
function renderOperationalIntel() {
  const ins = state.insights;
  const d   = state.data;

  // Weekly scan log
  const scanLog = ins?.scan_log || ins?.weekly_scan || d?.scan_log || [];
  const scanEl  = document.getElementById('weekly-scan-log');
  if (scanEl && scanLog.length > 0) {
    scanEl.innerHTML = scanLog.map(entry =>
      `<div style="margin-bottom:0.4rem; padding-bottom:0.4rem; border-bottom:1px solid var(--ghost);">
        <span style="color:var(--muted);">${entry.date || ''}</span>
        <span style="color:var(--acid); margin:0 0.4rem;">></span>
        ${entry.note || entry.text || entry}
      </div>`
    ).join('');
  } else if (scanEl) {
    scanEl.innerHTML = '<span style="color:var(--muted);">No scan entries. Run weekly scan to populate.</span>';
  }

  // Command log
  const cmdLog = ins?.command_log || d?.command_log || [];
  const cmdEl  = document.getElementById('command-log');
  if (cmdEl && cmdLog.length > 0) {
    cmdEl.innerHTML = cmdLog.map(entry =>
      `<div style="margin-bottom:0.3rem;">
        <span style="color:var(--muted); font-size:0.58rem;">${entry.timestamp || entry.date || ''}</span><br/>
        <span style="color:var(--slate);">${entry.action || entry.text || entry}</span>
      </div>`
    ).join('');
  } else if (cmdEl) {
    const now = new Date();
    cmdEl.innerHTML = `
      <div style="margin-bottom:0.3rem;">
        <span style="color:var(--muted); font-size:0.58rem;">${now.toISOString()}</span><br/>
        <span style="color:var(--acid);">ENDGAME initialized. Macro-first mode active.</span>
      </div>
      <div style="margin-bottom:0.3rem;">
        <span style="color:var(--muted); font-size:0.58rem;">System</span><br/>
        <span style="color:var(--slate);">Data feeds connected. Awaiting confluence signals.</span>
      </div>`;
  }
}

// ── SYSTEM STATUS ─────────────────────────────────────────────────────────────
function renderSystemStatus() {
  const now  = state.lastUpdate || new Date();
  const next = new Date(now.getTime() + ENDGAME.refreshInterval);

  setText('sys-last-update', now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }));
  setText('sys-next-refresh', next.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }));
}

// ── FALLBACK ──────────────────────────────────────────────────────────────────
function renderFallback() {
  const fields = ['gold-price','spy-price','yield-price','unemp-rate','fed-rate'];
  fields.forEach(id => setText(id, 'NO DATA'));
  setText('regime-description', 'Data feed unavailable. Check data/data.json and data/ai_insights.json.');
  setText('confluence-detail', 'Offline mode. Reconnect data sources to activate confluence engine.');
  setStatus('ai-status-dot', 'ai-status-text', false, 'OFFLINE');
}

// ── SIGNAL HELPERS ────────────────────────────────────────────────────────────
function wyckoffSignal(changePct) {
  if (changePct === null || changePct === undefined) return '-';
  if (changePct > 1.5)  return 'MARKUP - Rising vol confirms';
  if (changePct > 0.3)  return 'ACCUMULATION - Quiet strength';
  if (changePct > -0.3) return 'RANGING - No directional edge';
  if (changePct > -1.5) return 'DISTRIBUTION - Watch volume';
  return 'MARKDOWN - Selling pressure';
}

function yieldSignal(rate) {
  if (!rate) return '-';
  if (rate > 5.0) return 'RESTRICTIVE - Growth headwind';
  if (rate > 4.0) return 'ELEVATED - Fed holding firm';
  if (rate > 3.0) return 'NEUTRAL - Balanced conditions';
  if (rate > 2.0) return 'ACCOMMODATIVE - Risk-on bias';
  return 'SUPPRESSED - Crisis/QE mode';
}

function unempSignal(rate) {
  if (!rate) return '-';
  if (rate > 5.5) return 'RECESSION RISK - Fed pivot likely';
  if (rate > 4.5) return 'SOFTENING - Watch NFP trend';
  if (rate > 4.0) return 'NORMALIZING - Mild cooling';
  if (rate > 3.5) return 'TIGHT - Labor market strong';
  return 'FULL EMPLOYMENT - Inflationary pressure';
}

function fedSignal(rate) {
  if (!rate) return '-';
  if (rate > 5.0) return 'RESTRICTIVE - Cuts incoming';
  if (rate > 4.0) return 'ELEVATED - Holding pattern';
  if (rate > 2.5) return 'NEUTRAL - Balanced stance';
  if (rate > 1.0) return 'ACCOMMODATIVE - Risk-on';
  return 'EMERGENCY - Crisis mode';
}

function verdictFromScore(score) {
  if (score >= 80) return 'STRONG CONFLUENCE';
  if (score >= 65) return 'MODERATE CONFLUENCE';
  if (score >= 45) return 'MIXED SIGNALS';
  if (score >= 25) return 'WEAK CONFLUENCE';
  return 'NO CONFLUENCE';
}

function regimeClass(label) {
  const l = (label || '').toLowerCase();
  if (l.includes('bull') || l.includes('risk-on') || l.includes('expansion')) return 'regime-bull';
  if (l.includes('bear') || l.includes('risk-off') || l.includes('recession')) return 'regime-bear';
  if (l.includes('caution') || l.includes('late')) return 'regime-caution';
  return 'regime-neutral';
}

// ── FORMATTING ────────────────────────────────────────────────────────────────
function formatPrice(val, prefix, decimals) {
  prefix = prefix !== undefined ? prefix : '$';
  decimals = decimals !== undefined ? decimals : 2;
  if (val === null || val === undefined || isNaN(val)) return '-';
  return prefix + parseFloat(val).toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function formatChange(val) {
  if (val === null || val === undefined || isNaN(val)) return '-';
  const v = parseFloat(val);
  const sign = v >= 0 ? '+' : '';
  return sign + v.toFixed(2) + '%';
}

function normalizeBar(val, min, max) {
  if (!val || isNaN(val)) return 0;
  return Math.min(100, Math.max(0, ((val - min) / (max - min)) * 100));
}

// ── DOM HELPERS ───────────────────────────────────────────────────────────────
function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

function setStatus(dotId, textId, ok, label) {
  const dot  = document.getElementById(dotId);
  const text = document.getElementById(textId);
  if (dot) {
    dot.className = 'dot ' + (ok ? 'dot-live' : 'dot-dead');
  }
  if (text) {
    text.textContent = label || (ok ? 'LIVE' : 'ERROR');
    text.className   = 'timestamp ' + (ok ? 'status-connected' : 'status-error');
  }
}
