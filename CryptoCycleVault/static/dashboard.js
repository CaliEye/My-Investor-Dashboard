const BASE_URL = "http://127.0.0.1:8000";

// Fetch and update Market Overview
async function updateMarketOverview() {
  console.log("Updating Market Overview...");

  try {
    // Fetch BTC Price
    const btcResponse = await fetch(`${BASE_URL}/api/price/bitcoin`);
    if (!btcResponse.ok) throw new Error("Failed to fetch BTC price");
    const btcData = await btcResponse.json();
    document.getElementById("btc-price").innerText = `$${btcData.usd}`;

    // Fetch ETH Price
    const ethResponse = await fetch(`${BASE_URL}/api/price/ethereum`);
    if (!ethResponse.ok) throw new Error("Failed to fetch ETH price");
    const ethData = await ethResponse.json();
    document.getElementById("eth-price").innerText = `$${ethData.usd}`;

    // Fetch SPX Price
    const spxResponse = await fetch(`${BASE_URL}/api/price/spx`);
    if (!spxResponse.ok) throw new Error("Failed to fetch SPX price");
    const spxData = await spxResponse.json();
    document.getElementById("spx-price").innerText = `$${spxData.price}`;

    // Fetch USD Index
    const dxyResponse = await fetch(`${BASE_URL}/api/price/dxy`);
    if (!dxyResponse.ok) throw new Error("Failed to fetch USD Index price");
    const dxyData = await dxyResponse.json();
    document.getElementById("usd-index").innerText = `$${dxyData.price}`;

    // Fetch Fear & Greed Index
    const sentimentResponse = await fetch(`${BASE_URL}/api/market/sentiment`);
    if (!sentimentResponse.ok) throw new Error("Failed to fetch Fear & Greed Index");
    const sentimentData = await sentimentResponse.json();
    document.getElementById("fear-greed").innerText = `${sentimentData.index} (${sentimentData.classification})`;
  } catch (error) {
    console.error("Error updating Market Overview:", error);
  }
}

// Initialize the dashboard
function initializeDashboard() {
  updateMarketOverview();
}

// Run the initialization function on page load
document.addEventListener("DOMContentLoaded", initializeDashboard);