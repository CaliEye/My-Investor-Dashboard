from datetime import datetime
import requests
from requests.exceptions import RequestException

# API Endpoints
fear_greed_url = "https://api.alternative.me/fng/?limit=1"
coingecko_url = "https://api.coingecko.com/api/v3/global"

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