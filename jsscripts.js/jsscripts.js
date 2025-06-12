// ==== DASHBOARD JAVASCRIPT ====

document.addEventListener("DOMContentLoaded", function () {

  // Hamburger menu for mobile navigation
  const hamburger = document.getElementById('hamburger');
  const mainNav = document.getElementById('main-nav');
  const mobileNav = document.getElementById('mobile-nav');
  hamburger.onclick = () => {
    if (mobileNav.style.display === "none" || !mobileNav.style.display) {
      mobileNav.style.display = "flex";
    } else {
      mobileNav.style.display = "none";
    }
  };
  document.body.addEventListener('click', function (e) {
    if (!hamburger.contains(e.target) && !mobileNav.contains(e.target)) {
      mobileNav.style.display = "none";
    }
  }, true);

  // Optional Loader
  const loader = document.getElementById('dashboard-loader');
  function showLoader() { if (loader) loader.style.display = 'block'; }
  function hideLoader() { if (loader) loader.style.display = 'none'; }

  // Storage helpers
  const storage = key => localStorage.getItem(key);
  const save = (key, val) => localStorage.setItem(key, val);
  const clearAll = () => localStorage.clear();

  const KEYS = {
    spx: 'cs_spx',
    usd: 'cs_usd',
    btc: 'cs_btc',
    nvt: 'cs_nvt',
    fg: 'cs_fg'
  };

  // ----- API KEYS -----
  // IMPORTANT: Replace this with your own Alpha Vantage API key!
  const ALPHA_VANTAGE_KEY = "ZGA6Y5FY790NO4QE"; // Replace with your actual key;

  // ----- FETCH HELPERS -----
  async function fetchJSON(url) {
    try {
      const response = await fetch(url);
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error(`Error fetching data from ${url}:`, error);
      return null;
    }
  }

  // SPX & USD Charts (Alpha Vantage)
  async function fetchTimeSeries(symbol) {
    const apikey = ALPHA_VANTAGE_KEY;
    try {
      const res = await fetch(`https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=${encodeURIComponent(symbol)}&interval=60min&outputsize=compact&apikey=${apikey}`);
      const json = await res.json();
      if (json['Note'] || json['Information']) {
        console.error('Alpha Vantage API limit or invalid API key:', json);
        return [];
      }
      const data = json['Time Series (60min)'];
      if (!data) throw new Error('No data returned from Alpha Vantage');
      return Object.entries(data).slice(0, 48).reverse().map(([ts, val]) => ({ x: new Date(ts), y: +val['4. close'] }));
    } catch (error) {
      console.error(`Error fetching ${symbol} data:`, error);
      return [];
    }
  }

  // Chart rendering
  function makeChart(ctx, label, data, color) {
    if (!ctx) return;
    // Destroy previous chart instance if exists for smoother updates
    if (ctx._chartInstance) {
      ctx._chartInstance.destroy();
    }
    ctx._chartInstance = new Chart(ctx, {
      type: 'line',
      data: { datasets: [{ label, data, borderColor: color, pointRadius: 0, fill: false, tension: 0.3 }] },
      options: {
        responsive: true,
        scales: {
          x: { type: 'time', time: { unit: 'hour', displayFormats: { hour: 'HH:mm' } }, grid: { color: '#23283a' } },
          y: { grid: { color: '#23283a' } }
        },
        plugins: { legend: { display: false } },
        elements: { line: { borderWidth: 2 } }
      }
    });
  }

  // BTC Chart (Coingecko)
  async function fetchBTC() {
    try {
      const res = await fetch('https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=1&interval=hourly');
      const j = await res.json();
      if (!j.prices) throw new Error('No BTC price data');
      return j.prices.map(p => ({ x: new Date(p[0]), y: p[1] }));
    } catch (error) {
      console.error('Error fetching BTC data:', error);
      return [];
    }
  }

  // ETH Price (Coingecko)
  async function fetchETHPrice() {
    try {
      const res = await fetch('https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd');
      const d = await res.json();
      if (!d.ethereum || !d.ethereum.usd) throw new Error('No ETH price data');
      return d.ethereum.usd;
    } catch (error) {
      console.error('Error fetching ETH price:', error);
      return null;
    }
  }

  // Fear & Greed (Alternative.me)
  async function fetchFG() {
    try {
      const j = await fetchJSON('https://api.alternative.me/fng/?limit=1');
      if (!j || !j.data || !j.data[0]) throw new Error('No F&G data');
      return +j.data[0].value;
    } catch (error) {
      console.error('Error fetching Fear & Greed data:', error);
      return null;
    }
  }

  // ----- DASHBOARD REFRESH -----
  async function refreshAll() {
    if (loader) showLoader();
    try {
      // SPX
      const spxData = await fetchTimeSeries('^GSPC');
      if (spxData && spxData.length) {
        makeChart(document.getElementById('spxChart'), 'S&P 500', spxData, '#00e5ff');
        const lastSPX = spxData.at(-1).y;
        const prevSPX = spxData.at(-2).y;
        document.getElementById('spx-latest').textContent = lastSPX.toLocaleString();
        document.getElementById(lastSPX > prevSPX ? 'spx-up' : 'spx-down').checked = true;
        save(KEYS.spx, lastSPX > prevSPX ? 'up' : 'down');
      } else {
        document.getElementById('spx-latest').textContent = "N/A";
      }
      // USD (DXY)
      const usdData = await fetchTimeSeries('DX-Y.NYB');
      if (usdData && usdData.length) {
        makeChart(document.getElementById('usdChart'), 'USD Index', usdData, '#ff00d6');
        const lastUSD = usdData.at(-1).y, prevUSD = usdData.at(-2).y;
        document.getElementById('usd-latest').textContent = lastUSD.toLocaleString();
        document.getElementById(lastUSD > prevUSD ? 'usd-strong' : 'usd-weak').checked = true;
        save(KEYS.usd, lastUSD > prevUSD ? 'strong' : 'weak');
      } else {
        document.getElementById('usd-latest').textContent = "N/A";
      }
      // BTC
      const btcData = await fetchBTC();
      if (btcData && btcData.length) {
        makeChart(document.getElementById('btcChart'), 'Bitcoin', btcData, 'yellow');
        const lastBTC = btcData.at(-1).y, prevBTC = btcData.at(-2).y;
        document.getElementById('btc-price').textContent = '$' + lastBTC.toLocaleString();
        document.getElementById('btc-up').checked = lastBTC > prevBTC;
        save(KEYS.btc, lastBTC > prevBTC);
      } else {
        document.getElementById('btc-price').textContent = "N/A";
      }
      // ETH
      const eth = await fetchETHPrice();
      if (eth !== null) {
        document.getElementById('eth-price').textContent = '$' + eth.toLocaleString();
      } else {
        document.getElementById('eth-price').textContent = "N/A";
      }
      // Fear & Greed
      const fg = await fetchFG();
      if (fg !== null) {
        document.getElementById('fgSlider').value = fg;
        document.getElementById('fgValue').textContent = fg;
        document.getElementById('fg-latest').textContent = fg;
        save(KEYS.fg, fg);
      } else {
        document.getElementById('fg-latest').textContent = "N/A";
      }
    } catch (err) {
      console.error("refreshAll error", err);
    } finally {
      if (loader) hideLoader();
    }
  }

  // Sentiment slider
  document.getElementById('fgSlider').oninput = e => {
    document.getElementById('fgValue').textContent = e.target.value;
    save(KEYS.fg, e.target.value);
  };

  // Reset All
  document.getElementById('reset').onclick = () => {
    if (confirm("Are you sure you want to reset all data? This cannot be undone.")) {
      clearAll();
      document.querySelectorAll('input[type="checkbox"],input[type="radio"]').forEach(i => i.checked = false);
      document.getElementById('fgSlider').value = 0;
      document.getElementById('fgValue').textContent = '0';
      document.getElementById('fg-latest').textContent = '0';
      document.getElementById('insights').innerHTML = "<strong>Market insights and suggested actions will appear here based on your scenario.</strong>";
    }
  };

  // Insights
  window.generateInsights = function () {
    const fed = document.querySelector('input[name="fed"]:checked');
    const macros = Array.from(document.querySelectorAll('input[name="macro"]:checked')).map(cb => cb.value);
    const cycle = document.querySelector('input[name="cycle"]:checked');
    const thoughts = document.getElementById('user-thoughts').value.trim();
    let insights = [];
    if (fed && fed.value.includes('QE')) {
      insights.push("Fed is starting QE: Risk assets (crypto, stocks) may benefit. Consider increasing exposure.");
    }
    if (macros.includes('Recession')) {
      insights.push("Recession: Defensive positioning, consider gold, cash, or low-beta assets.");
    }
    if (macros.includes('Inflation')) {
      insights.push("Inflation: Hard assets like BTC and gold may outperform.");
    }
    if (cycle && cycle.value === 'Year 4') {
      insights.push("BTC Cycle Year 4: Historically, late-cycle risk. Consider profit-taking strategies.");
    }
    if (thoughts) {
      insights.push("Your thoughts: " + thoughts);
    }
    if (insights.length === 0) {
      insights.push("Select scenario options and add your thoughts for tailored insights.");
    }
    document.getElementById('insights').innerHTML = insights.map(i => `<div>• ${i}</div>`).join('');
  };

  // Navigation highlight (desktop & mobile)
  function highlightNav() {
    let navs = [mainNav, mobileNav];
    navs.forEach(navEl => {
      Array.from(navEl.querySelectorAll('a')).forEach(link => {
        link.onclick = function () {
          navs.forEach(nv => nv.querySelectorAll('a').forEach(l => l.classList.remove('active')));
          this.classList.add('active');
        }
      });
    });
  }
  highlightNav();

  // Run refresh on load and every 60s
  refreshAll();
  setInterval(refreshAll, 60_000);

});