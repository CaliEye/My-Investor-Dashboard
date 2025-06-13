# CyberSci-Dash v2 FastAPI Backend
# Features: Live price fetch, scenario storage, trusted insights API, health check
# Note: Ensure the 'ALPHA_VANTAGE_KEY' environment variable is set for SPX price fetching.

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from typing import List
from datetime import datetime
from time import sleep
import logging
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import random

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
import os
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY", "ZGA6Y5FY790NO4QE")  # Default key for development

if not ALPHA_VANTAGE_KEY:
    logging.exception("Alpha Vantage API Key is required and not set. Set it as an environment variable 'ALPHA_VANTAGE_KEY'.")
    raise ValueError("Alpha Vantage API Key is required and not set.")

# ==== Helper Functions ====
def fetch_data_with_retry(url, retries=3, delay=2):
    """Fetch data from an API with retry logic."""
    for attempt in range(retries):
        try:
            for attempt in range(3):  # Retry up to 3 times
                try:
                    response = requests.get(url, timeout=10)
                    response.raise_for_status()  # Ensure HTTP errors are caught early
                    break  # Exit retry loop on success
                except requests.exceptions.RequestException as e:
                    logging.warning(f"Attempt {attempt + 1} failed: {e}")
                    if attempt == 2:  # Last attempt
                        raise HTTPException(status_code=500, detail=f"Failed to fetch SPX price after retries: {e}")
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
        btc_dominance = cg_data["data"].get("market_cap_percentage", {}).get("btc", 0)
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

# Mount the static directory
import os

# In-memory storage for scenarios
SCENARIOS = []

static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../static"))
if not os.path.exists(static_dir):
    raise FileNotFoundError(f"Static directory does not exist: {static_dir}")

app.mount("/static", StaticFiles(directory=static_dir), name="static")
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

@app.get("/api/insights/{timeframe}")
def get_insights(timeframe: str):
    """Retrieve insights for a specific timeframe."""
    valid_timeframes = ['3day', 'weekly', 'monthly']
    if timeframe not in valid_timeframes:
        raise HTTPException(status_code=400, detail=f"Invalid timeframe. Expected one of {valid_timeframes}.")
    found = [i.dict() for i in INSIGHTS if i.timeframe == timeframe]
    if not found:
        raise HTTPException(status_code=404, detail="No insights found for timeframe.")
    return found
def get_insights(timeframe: str):
    """Retrieve insights for a specific timeframe."""
    found = [i.dict() for i in INSIGHTS if i.timeframe == timeframe]
    if not found:
        raise HTTPException(status_code=404, detail="No insights found for timeframe.")
    return found

@app.get("/api/insights/all")
def get_all_insights():
    """Retrieve all insights."""
import json

@app.get("/api/quotes/random")
def random_quote():
    """Retrieve a random trusted source quote."""
    try:
        with open("quotes.json", "r", encoding="utf-8") as file:
            quotes = json.load(file)
        return random.choice(quotes)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Quotes configuration file not found.")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Error parsing quotes configuration file.")
        {"src": "Crypto Face", "quote": "Risk management first, FOMO last."}
    return random.choice(quotes)

# -- Root endpoint --
@app.get("/")
def root():
    return {"message": "Welcome to the CyberSci-Dash API!"}

@app.get("/api/price/bitcoin")
def get_bitcoin_price():
    """Fetch the current Bitcoin price in USD."""
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        if "bitcoin" not in data:
            raise ValueError("Missing 'bitcoin' key in API response")
        price = data["bitcoin"].get("usd")
        if price is None:
            raise ValueError("Invalid response structure from CoinGecko API")
        return {"symbol": "BTC", "usd": price}
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error fetching Bitcoin price: {e}")
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Error parsing API response: {e}")

@app.get("/api/price/spx")
async def get_spx_price():
    """Fetch the current SPX price with fallback mechanisms."""
    import os
    import requests
    from fastapi.responses import JSONResponse
    from fastapi import HTTPException

    # Primary and backup API keys
    api_keys = [
        os.getenv("ALPHA_VANTAGE_KEY", "PRIMARY_API_KEY"),  # Replace with your primary key
        os.getenv("BACKUP_API_KEY_1", "BACKUP_API_KEY_1"),  # Replace with your backup key
        os.getenv("BACKUP_API_KEY_2", "BACKUP_API_KEY_2")   # Replace with another backup key
    ]

    valid_symbols = ["SPX", "SPY"]  # Add valid symbols for Alpha Vantage API
    symbol = "SPX"  # Hardcoded for now; can be parameterized if needed

    if symbol not in valid_symbols:
        raise HTTPException(status_code=400, detail=f"Invalid symbol '{symbol}'. Please use a valid symbol.")

    # Try fetching data using each API key
    for api_key in api_keys:
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval=1min&apikey={api_key}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()  # Ensure HTTP errors are caught early
            data = response.json()

            # Validate response structure
            if "Time Series (1min)" not in data:
                continue  # Skip to the next API key if the response is invalid

            # Sort timestamps to ensure the latest one is selected
            sorted_timestamps = sorted(data["Time Series (1min)"].keys(), reverse=True)
            latest_time = sorted_timestamps[0]

            if "1. open" in data["Time Series (1min)"][latest_time]:
                price = data["Time Series (1min)"][latest_time]["1. open"]
                response_data = {"symbol": symbol, "price": float(price), "source": "Alpha Vantage"}
                return JSONResponse(content=response_data, headers={"Content-Type": "application/json; charset=utf-8"})
            else:
                continue  # Skip to the next API key if the price key is missing
        except requests.exceptions.RequestException as e:
            # Log the error and continue to the next API key
            print(f"Error fetching SPX price with API key {api_key}: {e}")
            continue

    # If all API keys fail, return an error
    raise HTTPException(status_code=500, detail="Failed to fetch SPX price from all available APIs.")
