<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CyberSci-Dash</title>
  <script defer src="dashboard.js"></script>
</head>
<body>
  <h1>CyberSci-Dash</h1>

  <!-- Live Price Section -->
  <section id="live-price">
    <h2>Live Prices</h2>
    <p>Bitcoin (BTC): <span id="btc-price">Loading...</span></p>
    <p>Ethereum (ETH): <span id="eth-price">Loading...</span></p>
    <p>S&P 500 (SPX): <span id="spx-price">Loading...</span></p>
    <p>USD Index (DXY): <span id="usd-index">Loading...</span></p>
    <p>Fear & Greed Index: <span id="fear-greed">Loading...</span></p>
  </section>

  <!-- Scenarios Section -->
  <section id="scenarios">
    <h2>Scenarios</h2>
    <form id="scenario-form">
      <label for="entry-price">Entry Price:</label>
      <input type="number" id="entry-price" name="entry_price" required>
      <label for="position-size">Position Size:</label>
      <input type="number" id="position-size" name="position_size" required>
      <button type="submit">Save Scenario</button>
    </form>
    <h3>Saved Scenarios</h3>
    <ul id="saved-scenarios"></ul>
  </section>

  <!-- Insights Section -->
  <section id="insights">
    <h2>Insights</h2>
    <button onclick="fetchInsights('3day')">3-Day Insights</button>
    <button onclick="fetchInsights('weekly')">Weekly Insights</button>
    <button onclick="fetchInsights('monthly')">Monthly Insights</button>
    <ul id="insights-list"></ul>
  </section>

  <script>
const BASE_URL = "http://127.0.0.1:8000";

// Fetch and update Market Overview
async function updateMarketOverview() {
  try {
    // Fetch BTC Price
    const btcResponse = await fetch(`${BASE_URL}/api/price/bitcoin`);
    const btcData = await btcResponse.json();
    document.getElementById("btc-price").innerText = `$${btcData.usd}`;

    // Fetch ETH Price
    const ethResponse = await fetch(`${BASE_URL}/api/price/ethereum`);
    const ethData = await ethResponse.json();
    document.getElementById("eth-price").innerText = `$${ethData.usd}`;

    // Fetch SPX Price
    const spxResponse = await fetch(`${BASE_URL}/api/price/spx`);
    const spxData = await spxResponse.json();
    document.getElementById("spx-price").innerText = `$${spxData.price}`;

    // Fetch USD Index
    const dxyResponse = await fetch(`${BASE_URL}/api/price/dxy`);
    const dxyData = await dxyResponse.json();
    document.getElementById("usd-index").innerText = `$${dxyData.price}`;

    // Fetch Fear & Greed Index
    const sentimentResponse = await fetch(`${BASE_URL}/api/market/sentiment`);
    const sentimentData = await sentimentResponse.json();
    document.getElementById("fear-greed").innerText = `${sentimentData.index} (${sentimentData.classification})`;
  } catch (error) {
    console.error("Error updating Market Overview:", error);
  }
}

// Save a new scenario
document.getElementById("scenario-form").addEventListener("submit", async function (e) {
  e.preventDefault();

  const entryPrice = document.getElementById("entry-price").value;
  const positionSize = document.getElementById("position-size").value;

  const scenario = {
    scenario_type: "Long",
    macro_trigger: "Bullish breakout",
    entry_price: parseFloat(entryPrice),
    position_size: parseFloat(positionSize),
    stop_loss: 25000,
    take_profit: 30000,
    support_resistance: "Strong support at 26000",
    notes: "Test scenario"
  };

  try {
    const response = await fetch(`${BASE_URL}/api/scenario/save`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(scenario)
    });

    const data = await response.json();
    alert(data.message);
    fetchSavedScenarios(); // Refresh the list of saved scenarios
  } catch (error) {
    console.error("Error saving scenario:", error);
  }
});

// Fetch all saved scenarios
async function fetchSavedScenarios() {
  try {
    const response = await fetch(`${BASE_URL}/api/scenario/all`);
    if (!response.ok) throw new Error("Failed to fetch scenarios");

    const scenarios = await response.json();
    const scenariosList = document.getElementById("saved-scenarios");
    scenariosList.innerHTML = ""; // Clear the list

    scenarios.forEach((scenario) => {
      const li = document.createElement("li");
      li.innerText = `Type: ${scenario.scenario_type}, Entry: $${scenario.entry_price}, Size: ${scenario.position_size}`;
      scenariosList.appendChild(li);
    });
  } catch (error) {
    console.error("Error fetching scenarios:", error);
  }
}

// Fetch insights for a specific timeframe
async function fetchInsights(timeframe) {
  try {
    const response = await fetch(`${BASE_URL}/api/insights/${timeframe}`);
    if (!response.ok) throw new Error("Failed to fetch insights");

    const insights = await response.json();
    const insightsList = document.getElementById("insights-list");
    insightsList.innerHTML = ""; // Clear the list

    insights.forEach((insight) => {
      const li = document.createElement("li");
      li.innerText = `${insight.title}: ${insight.content} (Source: ${insight.source})`;
      insightsList.appendChild(li);
    });
  } catch (error) {
    console.error("Error fetching insights:", error);
  }
}

// Initialize the dashboard
function initializeDashboard() {
  updateMarketOverview();
  fetchSavedScenarios();
}

// Run the initialization function on page load
document.addEventListener("DOMContentLoaded", initializeDashboard);
  </script>
</body>
</html>