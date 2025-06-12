// CyberSci-Dash v2 Custom JavaScript
// Author: CaliEye Copilot
// Features: Chart switching, insights toggles, theme control, quick link add, simple local storage, dynamic tooltips, Alpha Vantage integration

const ALPHA_VANTAGE_KEY = "ZGA6Y5FY790NO4QE"; // Your Alpha Vantage API Key

document.addEventListener('DOMContentLoaded', function () {
  /* === 1. Chart Switching (my charts.html) === */
  const chartMap = {
    spx: 'https://www.tradingview.com/chart/?symbol=SPX',
    dxy: 'https://www.tradingview.com/chart/?symbol=TVC:DXY',
    btcusd: 'https://www.tradingview.com/chart/?symbol=BITSTAMP:BTCUSD',
    ethusd: 'https://www.tradingview.com/chart/?symbol=BITSTAMP:ETHUSD',
    total3: 'https://www.tradingview.com/chart/?symbol=CRYPTOCAP:TOTAL3',
    btcd: 'https://www.tradingview.com/chart/?symbol=CRYPTOCAP:BTC.D'
  };

  window.showMainChart = function (chartKey) {
    const mainFrame = document.getElementById('main-chart-frame');
    if (mainFrame && chartMap[chartKey]) {
      mainFrame.src = chartMap[chartKey];
      document.querySelectorAll('.chart-thumb').forEach(el => el.classList.remove('selected'));
      const thumb = document.getElementById('thumb-' + chartKey);
      if (thumb) thumb.classList.add('selected');
    }
  };

  // Set initial default (BTCUSD)
  const defaultThumb = document.getElementById('thumb-btcusd');
  if (defaultThumb) defaultThumb.classList.add('selected');

  /* === 2. Insights Panel: Toggle 3D/Weekly/Monthly (all pages) === */
  const insightBtns = document.querySelectorAll('.insight-toggle-btn');
  if (insightBtns.length) {
    insightBtns.forEach(btn => {
      btn.addEventListener('click', function () {
        const target = this.dataset.target;
        document.querySelectorAll('.insight-panel-section').forEach(panel => {
          panel.style.display = panel.id === target ? 'block' : 'none';
        });
        insightBtns.forEach(b => b.classList.remove('active'));
        this.classList.add('active');
      });
    });
  }

  /* === 3. Quick Links: Add Favorite Link (links.html) === */
  const quickLinkForm = document.querySelector('form.quick-links-form');
  if (quickLinkForm) {
    quickLinkForm.addEventListener('submit', function (e) {
      e.preventDefault();
      const name = this.querySelector('input[type="text"]').value.trim();
      const url = this.querySelector('input[type="url"]').value.trim();
      if (!name || !url) {
        alert('Please enter both a website name and a valid URL.');
        return;
      }
      addQuickLinkToLocalStorage(name, url);
      this.reset();
      displayQuickLinks();
    });
    displayQuickLinks();
  }

  function addQuickLinkToLocalStorage(name, url) {
    const links = JSON.parse(localStorage.getItem('cybersci_quicklinks') || '[]');
    links.push({ name, url });
    localStorage.setItem('cybersci_quicklinks', JSON.stringify(links));
  }

  function displayQuickLinks() {
    const links = JSON.parse(localStorage.getItem('cybersci_quicklinks') || '[]');
    const list = document.getElementById('my-quick-links');
    if (!list) return;
    list.innerHTML = '';
    links.forEach(link => {
      const li = document.createElement('li');
      li.innerHTML = `<a href="${link.url}" target="_blank" class="text-cyan-300 underline">${link.name}</a>`;
      list.appendChild(li);
    });
  }

  /* === 4. Theme Toggle (dark/cyber/bright) === */
  const themeBtn = document.getElementById('theme-toggle');
  if (themeBtn) {
    themeBtn.addEventListener('click', function () {
      const body = document.body;
      if (body.classList.contains('theme-dark')) {
        body.classList.replace('theme-dark', 'theme-cyber');
      } else if (body.classList.contains('theme-cyber')) {
        body.classList.replace('theme-cyber', 'theme-bright');
      } else {
        body.classList.replace('theme-bright', 'theme-dark');
      }
    });
  }

  /* === 5. Tooltips for Chart Thumbnails === */
  document.querySelectorAll('.chart-thumb').forEach(thumb => {
    thumb.addEventListener('mouseenter', function () {
      const label = this.querySelector('div.font-bold');
      if (!label) return;
      const tip = document.createElement('div');
      tip.className = 'chart-tooltip';
      tip.innerText = 'Click to expand and analyze';
      tip.style.position = 'absolute';
      tip.style.background = '#232946';
      tip.style.color = '#fff';
      tip.style.border = '1.5px solid #06b6d4';
      tip.style.padding = '0.4em 1em';
      tip.style.borderRadius = '0.7em';
      tip.style.top = `${this.offsetTop + 120}px`;
      tip.style.left = `${this.offsetLeft + 30}px`;
      tip.style.zIndex = 1000;
      tip.style.pointerEvents = 'none';
      tip.id = 'chart-tip';
      document.body.appendChild(tip);
    });
    thumb.addEventListener('mouseleave', function () {
      const tip = document.getElementById('chart-tip');
      if (tip) tip.remove();
    });
  });

  /* === 6. Marquee Pause/Play (for news tickers) === */
  document.querySelectorAll('marquee, .alert-ticker').forEach(marquee => {
    marquee.addEventListener('mouseenter', () => marquee.stop && marquee.stop());
    marquee.addEventListener('mouseleave', () => marquee.start && marquee.start());
  });

  /* === 7. Scenario Builder: Save & Retrieve Scenarios (scenario.html) === */
  const scenarioForm = document.querySelector('form.scenario-form');
  if (scenarioForm) {
    scenarioForm.addEventListener('submit', function (e) {
      e.preventDefault();
      const data = {};
      this.querySelectorAll('input, select, textarea').forEach(input => {
        data[input.name || input.id || input.placeholder] = input.value;
      });
      const scenarios = JSON.parse(localStorage.getItem('cybersci_scenarios') || '[]');
      scenarios.push({ ...data, time: new Date().toISOString() });
      localStorage.setItem('cybersci_scenarios', JSON.stringify(scenarios));
      alert('Scenario saved! (Check the console for details)');
      console.log(scenarios);
      this.reset();
    });
  }

  // Validate user-entered scenarios with live market data
  async function validateScenario(symbol, userPrice) {
    const url = `https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=${symbol}&apikey=${ALPHA_VANTAGE_KEY}`;
    try {
      const response = await fetch(url);
      const data = await response.json();
      const latestDate = Object.keys(data['Time Series (Daily)'])[0];
      const livePrice = parseFloat(data['Time Series (Daily)'][latestDate]['4. close']);
      if (Math.abs(livePrice - userPrice) / livePrice > 0.05) {
        alert(`Warning: Your entered price for ${symbol} (${userPrice}) deviates significantly from the live price (${livePrice}).`);
      } else {
        alert(`Your entered price for ${symbol} (${userPrice}) is close to the live price (${livePrice}).`);
      }
    } catch (error) {
      console.error(`Error validating scenario for ${symbol}:`, error);
      alert('Error validating scenario. Please try again later.');
    }
  }

  // Helper function for API calls
  async function fetchAlphaVantageData(url) {
    try {
      const response = await fetch(url);
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error(`Error fetching data from Alpha Vantage: ${error.message}`);
      return null;
    }
  }

  // Fetch live prices for BTC and ETH
  async function fetchCryptoPrices() {
    const symbols = ['BTCUSD', 'ETHUSD'];
    const promises = symbols.map(symbol => {
      const url = `https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=${symbol.slice(0, 3)}&to_currency=USD&apikey=${ALPHA_VANTAGE_KEY}`;
      return fetchAlphaVantageData(url);
    });

    const results = await Promise.all(promises);
    results.forEach((data, index) => {
      const symbol = symbols[index];
      if (data) {
        const price = data['Realtime Currency Exchange Rate']['5. Exchange Rate'];
        document.getElementById(`live-${symbol.toLowerCase()}-price`).innerText = `$${parseFloat(price).toFixed(2)}`;
      } else {
        document.getElementById(`live-${symbol.toLowerCase()}-price`).innerText = 'Error';
      }
    });
  }

  // Call the function on page load
  fetchCryptoPrices();

  // Fetch macroeconomic data for SPX and DXY
  async function fetchMacroData() {
    const symbols = ['SPX', 'DXY'];
    const promises = symbols.map(symbol => {
      const url = `https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=${symbol}&apikey=${ALPHA_VANTAGE_KEY}`;
      return fetchAlphaVantageData(url);
    });

    const results = await Promise.all(promises);
    results.forEach((data, index) => {
      const symbol = symbols[index];
      if (data) {
        const latestDate = Object.keys(data['Time Series (Daily)'])[0];
        const price = data['Time Series (Daily)'][latestDate]['4. close'];
        document.getElementById(`macro-${symbol.toLowerCase()}`).innerText = `$${parseFloat(price).toFixed(2)}`;
      } else {
        document.getElementById(`macro-${symbol.toLowerCase()}`).innerText = 'Error';
      }
    });
  }

  // Call the function on page load
  fetchMacroData();

  // Fetch live RSI and SMA for BTC
  async function fetchLiveMetrics() {
    const rsiUrl = `https://www.alphavantage.co/query?function=RSI&symbol=BTCUSD&interval=daily&time_period=14&series_type=close&apikey=${ALPHA_VANTAGE_KEY}`;
    const smaUrl = `https://www.alphavantage.co/query?function=SMA&symbol=BTCUSD&interval=daily&time_period=50&series_type=close&apikey=${ALPHA_VANTAGE_KEY}`;
    try {
      const rsiResponse = await fetch(rsiUrl);
      const rsiData = await rsiResponse.json();
      const rsi = rsiData['Technical Analysis: RSI'][Object.keys(rsiData['Technical Analysis: RSI'])[0]]['RSI'];
      document.getElementById('live-btc-rsi').innerText = parseFloat(rsi).toFixed(2);

      const smaResponse = await fetch(smaUrl);
      const smaData = await smaResponse.json();
      const sma = smaData['Technical Analysis: SMA'][Object.keys(smaData['Technical Analysis: SMA'])[0]]['SMA'];
      document.getElementById('live-btc-sma').innerText = `$${parseFloat(sma).toFixed(2)}`;
    } catch (error) {
      console.error('Error fetching live metrics:', error);
      document.getElementById('live-btc-rsi').innerText = 'Error';
      document.getElementById('live-btc-sma').innerText = 'Error';
    }
  }

  // Call the function on page load
  fetchLiveMetrics();
});