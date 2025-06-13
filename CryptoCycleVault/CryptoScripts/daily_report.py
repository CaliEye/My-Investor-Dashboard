from datetime import datetime
import requests
import logging
from time import sleep
from requests.exceptions import RequestException
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("daily_report.log"),
        logging.StreamHandler()
    ]
)

# API Endpoints
fear_greed_url = "https://api.alternative.me/fng/?limit=1"
coingecko_url = "https://api.coingecko.com/api/v3/global"

# Alpha Vantage API Key
ALPHA_VANTAGE_KEY = "ZGA6Y5FY790NO4QE"

def fetch_data_with_retry(url, retries=3, delay=2):
    for attempt in range(retries):
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                sleep(delay)
    logging.error("All attempts to fetch data failed.")
    return None

# Fetch Data with Error Handling
try:
    fear_data = requests.get(fear_greed_url, timeout=10).json()
    print(fear_data)  # Debugging: Print the response
    greed_index = fear_data["data"][0]["value"]
    greed_classification = fear_data["data"][0]["value_classification"]
except (RequestException, KeyError, IndexError) as e:
    print(f"Error fetching or parsing Fear & Greed data: {e}")
    greed_index = "N/A"
    greed_classification = "N/A"

try:
    cg_data = requests.get(coingecko_url, timeout=10).json()
    print(cg_data)  # Debugging: Print the response
    btc_dominance = cg_data["data"]["market_cap_percentage"]["btc"]
    total_market_cap = round(cg_data["data"]["total_market_cap"]["usd"] / 1e12, 2)
except (RequestException, KeyError) as e:
    print(f"Error fetching or parsing CoinGecko data: {e}")
    btc_dominance = 0
    total_market_cap = 0

# Format Markdown
today = datetime.today().strftime('%Y-%m-%d')
output_file = "daily_market_update.md"

try:
    with open(output_file, "w") as file:
        file.write(f"# 📅 Market Snapshot – {today}\n\n")
        file.write("## 🧠 Sentiment\n")
        file.write(f"- Fear & Greed Index: **{greed_index} ({greed_classification})**\n\n")
        
        file.write("## 🌐 Market Overview\n")
        file.write(f"- BTC Dominance: **{btc_dominance:.2f}%**\n")
        file.write(f"- Global Crypto Market Cap: **${total_market_cap} Trillion**\n\n")
        
        file.write("## 📊 Key Observations\n")
        file.write("- 📈 BTC Dominance ↑ means early bull phase / altseason delayed\n")
        file.write("- 📉 BTC Dominance ↓ may indicate altseason rotation\n")
        file.write("- 🧠 High fear = possible contrarian long signal\n\n")
        
        file.write("## 🔍 Technical Summary\n")
        file.write("- Check RSI on Weekly (target: > 44 = trend up)\n")
        file.write("- Bollinger Band Position: ___\n")
        file.write("- Exchange inflows/outflows: ___ (Glassnode)\n")
        file.write("- BTC price structure (HH/HL): ___\n\n")
        
        file.write("## 🔌 Macro Backdrop\n")
        file.write("- Fed Position: ___ (QT / pause / cut)\n")
        file.write("- CPI Trend: ___\n")
        file.write("- DXY (Dollar Index): ___\n")
        file.write("- ISM Manufacturing Index: ___\n\n")
        
        file.write("## 📝 Strategy Notes\n")
        file.write("- [ ] Any take-profit zones hit today?\n")
        file.write("- [ ] Set new limit buys at key levels?\n")
        file.write("- [ ] New alerts needed?\n")
        file.write("- [ ] Update long-term portfolio exposure?\n")
    print(f"✅ Report created: {output_file}")
except PermissionError as e:
    print(f"Error writing to file: {e}")

print("Debug: Starting script...")
print(f"Debug: Writing to file {output_file}")

# Fetch stock data (e.g., SPX)
def fetch_stock_data(symbol):
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={ALPHA_VANTAGE_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        latest_date = list(data['Time Series (Daily)'].keys())[0]
        close_price = data['Time Series (Daily)'][latest_date]['4. close']
        logging.info(f"{symbol} Latest Close Price: ${close_price}")
        return close_price
    except Exception as e:
        logging.error(f"Error fetching data for {symbol}: {e}")
        return None

# Fetch cryptocurrency data (e.g., BTC/USD)
def fetch_crypto_data(symbol):
    url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency={symbol}&to_currency=USD&apikey={ALPHA_VANTAGE_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        exchange_rate = data['Realtime Currency Exchange Rate']['5. Exchange Rate']
        logging.info(f"{symbol}/USD Exchange Rate: ${exchange_rate}")
        return exchange_rate
    except Exception as e:
        logging.error(f"Error fetching data for {symbol}: {e}")
        return None

# Generate daily report
def generate_daily_report():
    logging.info("Generating daily report...")

    # Fetch stock data
    spx_price = fetch_stock_data("SPX")
    dxy_price = fetch_stock_data("DXY")

    # Fetch cryptocurrency data
    btc_price = fetch_crypto_data("BTC")
    eth_price = fetch_crypto_data("ETH")

    # Compile the report
    report = f"""
    Daily Market Report:
    ---------------------
    S&P 500 (SPX): ${spx_price if spx_price else 'Error fetching data'}
    US Dollar Index (DXY): ${dxy_price if dxy_price else 'Error fetching data'}
    Bitcoin (BTC/USD): ${btc_price if btc_price else 'Error fetching data'}
    Ethereum (ETH/USD): ${eth_price if eth_price else 'Error fetching data'}
    """
    logging.info(report)

    # Save the report to a file
    with open("daily_report.txt", "w") as file:
        file.write(report)

    logging.info("Daily report saved to daily_report.txt")

# Main execution
if __name__ == "__main__":
    generate_daily_report()