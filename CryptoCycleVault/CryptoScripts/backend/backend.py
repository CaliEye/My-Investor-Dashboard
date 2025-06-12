# CyberSci-Dash v2 FastAPI Backend
# Features: Live price fetch, scenario storage, trusted insights API, health check

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from typing import List
from datetime import datetime
from time import sleep
import logging
from fastapi.staticfiles import StaticFiles

# Initialize FastAPI app
app = FastAPI(
    title="CyberSci-Dash API",
    description="Backend for live data, scenarios, and insights.",
    version="2.0.0"
)

# Allow local frontend & localhost for development
origins = [
    "http://localhost",
    "http://127.0.0.1",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# API Endpoints
fear_greed_url = "https://api.alternative.me/fng/?limit=1"
coingecko_url = "https://api.coingecko.com/api/v3/global"

# Alpha Vantage API Key
ALPHA_VANTAGE_KEY = "ZGA6Y5FY790NO4QE"

if not ALPHA_VANTAGE_KEY:
    logging.error("Alpha Vantage API Key is not set. Please configure it before running the application.")
    raise ValueError("Alpha Vantage API Key is required.")

# ==== Helper Functions ====
def fetch_data_with_retry(url, retries=3, delay=2):
    """Fetch data from an API with retry logic."""
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                sleep(delay)
    logging.error("All attempts to fetch data failed.")
    return None

def write_to_file(filename, content):
    """Write content to a file."""
    try:
        with open(filename, "w", encoding="utf-8") as file:
            file.write(content)
        logging.info(f"File written successfully: {filename}")
    except PermissionError as e:
        logging.error(f"Error writing to file {filename}: {e}")

# ==== Fetch Data ====
def fetch_market_data():
    """Fetch market data from Fear & Greed Index and CoinGecko."""
    # Fetch Fear & Greed Index
    fear_data = fetch_data_with_retry(fear_greed_url)
    if fear_data:
        greed_index = fear_data["data"][0].get("value", "N/A")
        greed_classification = fear_data["data"][0].get("value_classification", "N/A")
    else:
        greed_index = "N/A"
        greed_classification = "N/A"

    # Fetch CoinGecko data
    cg_data = fetch_data_with_retry(coingecko_url)
    if cg_data:
        btc_dominance = cg_data["data"]["market_cap_percentage"].get("btc", 0)
        total_market_cap = round(cg_data["data"]["total_market_cap"]["usd"] / 1e12, 2)
    else:
        btc_dominance = 0
        total_market_cap = 0

    return greed_index, greed_classification, btc_dominance, total_market_cap

# ==== Generate Daily Report ====
def generate_daily_report():
    """Generate a daily market report."""
    logging.info("Generating daily report...")

    # Fetch market data
    greed_index, greed_classification, btc_dominance, total_market_cap = fetch_market_data()

    # Format Markdown
    today = datetime.today().strftime('%Y-%m-%d')
    output_file = "daily_market_update.md"
    report = f"""
# 📅 Market Snapshot – {today}

## 🧠 Sentiment
- Fear & Greed Index: **{greed_index} ({greed_classification})**

## 🌐 Market Overview
- BTC Dominance: **{btc_dominance:.2f}%**
- Global Crypto Market Cap: **${total_market_cap} Trillion**

## 📊 Key Observations
- 📈 BTC Dominance ↑ means early bull phase / altseason delayed
- 📉 BTC Dominance ↓ may indicate altseason rotation
- 🧠 High fear = possible contrarian long signal

## 🔍 Technical Summary
- Check RSI on Weekly (target: > 44 = trend up)
- Bollinger Band Position: ___
- Exchange inflows/outflows: ___ (Glassnode)
- BTC price structure (HH/HL): ___

## 🔌 Macro Backdrop
- Fed Position: ___ (QT / pause / cut)
- CPI Trend: ___
- DXY (Dollar Index): ___
- ISM Manufacturing Index: ___

## 📝 Strategy Notes
- [ ] Any take-profit zones hit today?
- [ ] Set new limit buys at key levels?
- [ ] New alerts needed?
- [ ] Update long-term portfolio exposure?
"""

    # Save the report to a file
    write_to_file(output_file, report)
    logging.info(f"✅ Report created: {output_file}")

# ==== Models ====
class Scenario(BaseModel):
    scenario_type: str
    macro_trigger: str
    entry_price: float
    position_size: float
    stop_loss: float
    take_profit: float
    support_resistance: str
    notes: str = ""
    created_at: datetime = datetime.utcnow()

class Insight(BaseModel):
    timeframe: str  # '3day', 'weekly', 'monthly'
    title: str
    content: str
    source: str

# ==== In-Memory Storage (for demo purposes) ====
SCENARIOS: List[Scenario] = []
INSIGHTS = [
    Insight(timeframe="3day", title="BTC RSI Oversold Bounce", content="RSI signals a possible bottom; crowd fearful.", source="CryptoQuant"),
    Insight(timeframe="weekly", title="Pi Cycle Top - No Signal", content="Cycle top not reached; trend intact.", source="LookIntoBitcoin"),
    Insight(timeframe="monthly", title="Macro Uptrend", content="Long-term uptrend, but volatility rising.", source="Benjamin Cowen"),
]

# Mount the static directory
app.mount("/static", StaticFiles(directory="../../static"), name="static")

# ==== Routes ====

@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok", "time": datetime.utcnow()}

# -- Live price fetch (CoinGecko public API, no key needed) --
@app.get("/api/price/{symbol}")
def get_price(symbol: str):
    """Fetch live price for a cryptocurrency."""
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={symbol}&vs_currencies=usd"
        resp = requests.get(url, timeout=6)
        resp.raise_for_status()
        data = resp.json()
        return {"symbol": symbol, "usd": data[symbol]["usd"], "source": "CoinGecko"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -- Scenario endpoints --
@app.post("/api/scenario/save")
def save_scenario(scenario: Scenario):
    """Save a new scenario."""
    SCENARIOS.append(scenario)
    return {"success": True, "message": "Scenario saved.", "created_at": scenario.created_at}

@app.get("/api/scenario/all")
def all_scenarios():
    """Retrieve all saved scenarios."""
    return sorted([s.dict() for s in SCENARIOS], key=lambda x: x['created_at'], reverse=True)

# -- Insights API --
@app.get("/api/insights/{timeframe}")
def get_insights(timeframe: str):
    """Retrieve insights for a specific timeframe."""
    found = [i.dict() for i in INSIGHTS if i.timeframe == timeframe]
    if not found:
        raise HTTPException(status_code=404, detail="No insights found for timeframe.")
    return found

@app.get("/api/insights/all")
def get_all_insights():
    """Retrieve all insights."""
    return [i.dict() for i in INSIGHTS]

# -- Trusted source quotes randomizer --
@app.get("/api/quotes/random")
def random_quote():
    """Retrieve a random trusted source quote."""
    quotes = [
        {"src": "Benjamin Cowen", "quote": "Patience beats intelligence during sideways cycles."},
        {"src": "Bob Loukas", "quote": "Cycle lows are opportunity, not fear."},
        {"src": "Trader Geo", "quote": "When the crowd is all-in, look for the fade."},
        {"src": "Crypto Face", "quote": "Risk management first, FOMO last."}
    ]
    return random.choice(quotes)

# -- Root endpoint --
@app.get("/")
def root():
    """Root endpoint for health check."""
    return {"msg": "CyberSci-Dash backend running."}