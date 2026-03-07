/**
 * live-refresh.js — On-load live data injection
 * Fires on every page visit. Overrides stale cached data.json values
 * with truly live prices from free public APIs (no key required).
 *
 * Sources:
 *  1. CoinGecko — BTC, ETH prices (free, no key)
 *  2. Alternative.me — Fear & Greed Index (free, no key)
 *  3. data.json — full cached dataset (always loaded)
 *
 * Updates any element with matching IDs across all pages.
 */

(function () {
  'use strict';

  const LIVE_BADGE_ID = 'live-refresh-badge';
  const STALE_WARN_ID = 'data-freshness';

  // --- Element helpers ---
  function setEl(id, value) {
    const el = document.getElementById(id);
    if (el && value !== null && value !== undefined) el.textContent = value;
  }

  function setColor(id, color) {
    const el = document.getElementById(id);
    if (el) el.style.color = color;
  }

  function showLiveBadge(sources) {
    let badge = document.getElementById(LIVE_BADGE_ID);
    if (!badge) {
      badge = document.createElement('div');
      badge.id = LIVE_BADGE_ID;
      badge.style.cssText = [
        'position:fixed', 'bottom:12px', 'right:12px', 'z-index:9999',
        'font-family:Orbitron,monospace', 'font-size:0.5rem', 'font-weight:700',
        'letter-spacing:2px', 'padding:0.3rem 0.7rem', 'border-radius:2px',
        'background:rgba(0,0,0,0.9)', 'border:1px solid #39ff14',
        'color:#39ff14', 'cursor:pointer', 'transition:opacity 0.5s'
      ].join(';');
      badge.title = 'Live data loaded — click to dismiss';
      badge.onclick = () => { badge.style.opacity = '0'; setTimeout(() => badge.remove(), 600); };
      document.body.appendChild(badge);
    }
    badge.textContent = `LIVE — ${sources.join(' + ')}`;
    setTimeout(() => { if (badge) badge.style.opacity = '0'; setTimeout(() => badge && badge.remove(), 600); }, 8000);
  }

  // --- Freshness check ---
  function checkFreshness(updatedUtc) {
    if (!updatedUtc) return;
    const ageMs = Date.now() - new Date(updatedUtc).getTime();
    const ageH  = ageMs / 3_600_000;
    const el    = document.getElementById(STALE_WARN_ID);
    if (!el) return;
    if (ageH < 2) {
      const mins = Math.round(ageMs / 60_000);
      el.textContent = `Updated ${mins}m ago`;
      el.style.color = '#39ff14';
    } else if (ageH < 6) {
      el.textContent = `Updated ${Math.round(ageH)}h ago — verify before acting`;
      el.style.color = '#FFD166';
    } else {
      el.textContent = `DATA STALE — ${Math.round(ageH)}h old — manual refresh recommended`;
      el.style.color = '#FF4757';
    }
  }

  // --- Apply data.json to page ---
  function applyDataJson(d) {
    checkFreshness(d.updated_utc);

    // Common fields
    const fmt = x => (x === null || x === undefined) ? null : x;
    setEl('btc-price',   fmt(d.crypto?.btc_price_formatted || (d.crypto?.btc_usd ? '$' + Number(d.crypto.btc_usd).toLocaleString() : null)));
    setEl('eth-price',   fmt(d.crypto?.eth_price_formatted));
    setEl('fg-latest',   fmt(d.sentiment?.fear_greed_index));
    setEl('fg-value',    fmt(d.sentiment?.fear_greed_index));
    setEl('macro-updated', d.updated_utc ? new Date(d.updated_utc).toLocaleString() : null);

    // Macro page
    setEl('dxy-value',       fmt(d.macro?.dxy));
    setEl('dxy-context',     fmt(d.macro?.dxy_context));
    setEl('us10y-value',     fmt(d.macro?.us10y_yield));
    setEl('us10y-context',   fmt(d.macro?.us10y_context));
    setEl('fed-rate-value',  fmt(d.macro?.fed_funds_rate));
    setEl('fed-rate-context',fmt(d.macro?.fed_rate_context));
    setEl('cpi-value',       fmt(d.macro?.cpi));
    setEl('cpi-context',     fmt(d.macro?.cpi_context));
    setEl('gdp-value',       fmt(d.macro?.gdp_growth));
    setEl('gdp-context',     fmt(d.macro?.gdp_context));
    setEl('spx-value',       fmt(d.macro?.spx));
    setEl('spx-context',     fmt(d.macro?.spx_context));
    setEl('spx-latest',      fmt(d.macro?.spx));
    setEl('usd-latest',      fmt(d.macro?.dxy));

    // Sector hero elements (populated by sector-specific scripts, but IDs shared)
    const sectors = d.sectors || {};
    ['tech','energy','bonds','realestate'].forEach(key => {
      const s = sectors[key];
      if (!s) return;
      setEl(`${key}-price`,       fmt(s.price_formatted));
      setEl(`${key}-change`,      fmt(s.change_pct_day != null ? (s.change_pct_day > 0 ? '+' : '') + s.change_pct_day + '%' : null));
      setEl(`${key}-rsi-daily`,   fmt(s.rsi_daily));
      setEl(`${key}-rsi-weekly`,  fmt(s.rsi_weekly));
      setEl(`${key}-cycle`,       fmt(s.cycle));
      setEl(`${key}-sentiment`,   fmt(s.sentiment));
      setEl(`${key}-trend-w`,     fmt(s.trend_weekly));
      setEl(`${key}-trend-m`,     fmt(s.trend_monthly));
    });

    // Bot opportunities — populate any bot-opp containers on page
    renderBotOpportunities(d.bot_opportunities || [], d.sectors || {});
  }

  // --- Bot opportunity renderer ---
  function renderBotOpportunities(opps, sectors) {
    const container = document.getElementById('bot-opp-container');
    if (!container || !opps.length) return;

    // Filter to relevant sector if page has data-sector attribute
    const pageSector = container.dataset.sector || null;
    const relevant = pageSector
      ? opps.filter(o => o.sector === pageSector || o.asset_key === pageSector)
      : opps;

    if (!relevant.length) {
      container.innerHTML = '<div style="color:#555;font-size:0.75rem;font-style:italic;padding:1rem;">No high-confidence opportunities detected in current market conditions.</div>';
      return;
    }

    const statusColor = s => {
      const m = { STRONG_BUY: '#39ff14', BUY: '#7aff5a', ACCUMULATE: '#FFD166', WATCH: '#f59e0b', CAUTION: '#FF4757', AVOID: '#555', ACTIVE: '#00D2FF' };
      return m[s] || '#888';
    };

    const typeColor = t => {
      const m = { DCA: '#00D2FF', MOMENTUM: '#39ff14', HEDGE: '#FF4757', INCOME: '#FFD700', WATCH: '#888' };
      return m[t] || '#888';
    };

    const confBar = (conf) => {
      const color = conf >= 75 ? '#39ff14' : conf >= 55 ? '#FFD166' : '#f59e0b';
      return `<div style="height:3px;background:#1a1a1a;border-radius:2px;overflow:hidden;margin-top:0.4rem;">
        <div style="height:100%;width:${conf}%;background:${color};transition:width 1s ease;"></div>
      </div>`;
    };

    container.innerHTML = relevant.map(o => `
      <div style="background:rgba(5,12,8,0.95);border:1px solid rgba(0,255,120,0.12);border-radius:4px;padding:1rem 1.2rem;transition:border-color 0.2s;"
           onmouseover="this.style.borderColor='rgba(0,255,120,0.3)'" onmouseout="this.style.borderColor='rgba(0,255,120,0.12)'">
        <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:0.5rem;margin-bottom:0.5rem;">
          <div style="display:flex;align-items:center;gap:0.6rem;">
            <span style="font-family:'Orbitron',monospace;font-size:0.5rem;font-weight:700;letter-spacing:2px;padding:0.15rem 0.5rem;border-radius:2px;color:${typeColor(o.bot_type)};background:${typeColor(o.bot_type)}18;border:1px solid ${typeColor(o.bot_type)}44;">${o.bot_type} BOT</span>
            <span style="font-family:'Orbitron',monospace;font-size:0.75rem;font-weight:700;color:#e8e8e8;">${o.asset}</span>
          </div>
          <div style="display:flex;align-items:center;gap:0.75rem;">
            <span style="font-family:'JetBrains Mono',monospace;font-size:0.65rem;color:#555;">RISK ${o.risk}/100</span>
            <span style="font-family:'Orbitron',monospace;font-size:0.55rem;font-weight:700;padding:0.15rem 0.6rem;border-radius:2px;color:${statusColor(o.status)};border:1px solid ${statusColor(o.status)}55;">${o.status}</span>
            <span style="font-family:'JetBrains Mono',monospace;font-size:1rem;font-weight:700;color:${o.confidence>=75?'#39ff14':o.confidence>=55?'#FFD166':'#f59e0b'};">${o.confidence}%</span>
          </div>
        </div>
        <div style="font-size:0.8rem;color:#cccccc;margin-bottom:0.4rem;">${o.action}</div>
        <div style="font-size:0.65rem;color:#555;font-family:'IBM Plex Mono',monospace;">${o.signal}</div>
        ${confBar(o.confidence)}
        <div style="font-size:0.6rem;color:#444;font-family:'IBM Plex Mono',monospace;margin-top:0.4rem;">⏱ ${o.timeframe}</div>
      </div>`).join('');
  }

  // --- Main fetch chain ---
  async function runLiveRefresh() {
    const liveSources = [];

    // Always load data.json first (cached baseline)
    try {
      const res = await fetch('./data/data.json', { cache: 'no-store' });
      if (res.ok) {
        const d = await res.json();
        window.__dashData = d;
        applyDataJson(d);
      }
    } catch (e) {
      console.warn('[LiveRefresh] data.json load failed:', e);
    }

    // Live BTC + ETH from CoinGecko (free, no key)
    try {
      const res = await fetch(
        'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd&include_24hr_change=true',
        { cache: 'no-store', signal: AbortSignal.timeout(5000) }
      );
      if (res.ok) {
        const data = await res.json();
        const btc = data?.bitcoin;
        const eth = data?.ethereum;

        if (btc?.usd) {
          const btcFmt = '$' + Math.round(btc.usd).toLocaleString();
          const btcChg = btc.usd_24h_change?.toFixed(2);
          const chgColor = btcChg > 0 ? '#39ff14' : '#FF4757';
          ['btc-price', 'btc-price-live'].forEach(id => setEl(id, btcFmt));
          ['btc-change', 'btc-change-24h'].forEach(id => { setEl(id, (btcChg > 0 ? '+' : '') + btcChg + '%'); setColor(id, chgColor); });
          liveSources.push('BTC');
        }

        if (eth?.usd) {
          const ethFmt = '$' + Math.round(eth.usd).toLocaleString();
          const ethChg = eth.usd_24h_change?.toFixed(2);
          const chgColor = ethChg > 0 ? '#39ff14' : '#FF4757';
          ['eth-price', 'eth-price-live'].forEach(id => setEl(id, ethFmt));
          ['eth-change', 'eth-change-24h'].forEach(id => { setEl(id, (ethChg > 0 ? '+' : '') + ethChg + '%'); setColor(id, chgColor); });
          liveSources.push('ETH');
        }
      }
    } catch (e) {
      console.warn('[LiveRefresh] CoinGecko failed:', e?.message);
    }

    // Live Fear & Greed from Alternative.me (free, no key)
    try {
      const res = await fetch(
        'https://api.alternative.me/fng/?limit=1',
        { cache: 'no-store', signal: AbortSignal.timeout(5000) }
      );
      if (res.ok) {
        const data = await res.json();
        const fng = data?.data?.[0];
        if (fng) {
          const val   = parseInt(fng.value);
          const label = fng.value_classification;
          const color = val >= 75 ? '#FF4757' : val >= 60 ? '#f59e0b' : val >= 40 ? '#FFD166' : val >= 25 ? '#00D2FF' : '#39ff14';
          ['fg-value', 'fg-latest', 'fear-greed-value'].forEach(id => { setEl(id, val); setColor(id, color); });
          ['fg-label', 'fear-greed-label'].forEach(id => setEl(id, label.toUpperCase()));

          // Update arc gauge if present (sentiment.html)
          const arc = document.getElementById('fg-arc');
          if (arc) {
            const arcLen = 288.5;
            arc.style.strokeDashoffset = arcLen * (1 - val / 100);
            arc.style.stroke = color;
            arc.style.filter = `drop-shadow(0 0 8px ${color})`;
          }
          liveSources.push('F&G');
        }
      }
    } catch (e) {
      console.warn('[LiveRefresh] F&G failed:', e?.message);
    }

    if (liveSources.length) showLiveBadge(liveSources);
  }

  // Fire immediately on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', runLiveRefresh);
  } else {
    runLiveRefresh();
  }

  // Expose manual refresh for pages that add a refresh button
  window.liveRefresh = runLiveRefresh;

})();
