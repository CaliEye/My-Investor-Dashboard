# 🔌 On-Chain & Macro API Integrations (Planned)

## ✅ Key API Sources
- **CoinGecko API**:
  - Real-time prices
  - BTC dominance
  - Volume metrics
- **Glassnode API** *(Pro account required)*:
  - MVRV Z-Score
  - SOPR
  - Exchange inflows/outflows
- **Alternative.me Fear & Greed Index**:
  - Simple and free
  - Great for contrarian signals
- **FRED / TradingEconomics API**:
  - Fed funds rate
  - CPI and inflation
  - Unemployment
  - ISM

---

## 🧪 Example API Call

📊 Fear & Greed Index (Alternative.me)  
https://api.alternative.me/fng/?limit=1

📊 BTC Dominance (CoinGecko)  
https://api.coingecko.com/api/v3/global

---

## 🛠 Planned Automation

- 🕰 **Daily cron script**:
  - Python script fetches data → parses JSON → outputs `.md` summary
  - Can tag events like “Cycle Risk Rising” or “Macro Liquidity Boost”

- 📬 **Alert Systems**:
  - RSI < 44
  - BTC dominance dropping rapidly
  - Derivative open interest collapsing
  - Alt/BTC rotation flips

---

## ⚙️ Tools Needed

- Python + Requests library
- GitHub Actions or Task Scheduler (for auto-update)
- `obsidian-dataview` plugin or `Notion API` for dynamic updates (optional)

---

## 🔐 Security Reminder

Do **not** store API keys in plaintext markdown.  
Use `.env` files or key vaults for sensitive credentials.
