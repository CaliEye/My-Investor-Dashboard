 # GitHub Secrets Setup

The dashboard's AI confluence system supports 8 data providers. Currently only Yahoo Finance
works without an API key. Adding keys for the other 7 providers dramatically improves resilience
and analysis quality — multi-AI consensus requires at least 2–3 independent live sources.

---

## Current Status

| Provider | Secret Name | Status |
|----------|-------------|--------|
| Yahoo Finance | (none required) | ACTIVE — free, no key |
| OpenAI (ChatGPT) | `OPENAI_API_KEY` | MISSING — add to GitHub Secrets |
| X.AI (Grok) | `XAI_API_KEY` | MISSING — add to GitHub Secrets |
| Anthropic (Claude) | `ANTHROPIC_API_KEY` | MISSING — add to GitHub Secrets |
| Google Gemini | `GEMINI_API_KEY` | MISSING — add to GitHub Secrets |
| Perplexity | `PERPLEXITY_API_KEY` | MISSING — add to GitHub Secrets |
| Alpha Vantage | `ALPHA_VANTAGE_API_KEY` | MISSING — add to GitHub Secrets |
| Polygon.io | `POLYGON_API_KEY` | MISSING — add to GitHub Secrets |

---

## How to Add a Secret

1. Go to: https://github.com/CaliEye/My-Investor-Dashboard/settings/secrets/actions
2. Click **New repository secret**
3. Enter the exact secret name from the table above
4. Paste your API key value
5. Click **Add secret**

Repeat for each provider you want to activate.

---

## Priority Order (add these first)

1. **OPENAI_API_KEY** — Powers ChatGPT regime analysis. Most impactful for AI insights quality.
   - Get at: https://platform.openai.com/api-keys
   - Cost: Pay-per-use (very cheap for daily analysis runs)

2. **ALPHA_VANTAGE_API_KEY** — RSI and technical indicator data for BTC.
   - Get at: https://www.alphavantage.co/support/#api-key
   - Cost: Free tier available (5 requests/min, 500/day)
   - NOTE: The old key `ZGA6Y5FY790NO4QE` was exposed publicly — rotate it first.

3. **ANTHROPIC_API_KEY** — Claude analysis layer. Already using Claude Code locally.
   - Get at: https://console.anthropic.com/settings/keys
   - Cost: Pay-per-use

4. **XAI_API_KEY** — Grok contrarian perspective. Good for counter-analysis.
   - Get at: https://console.x.ai/
   - Cost: Pay-per-use

5. **GEMINI_API_KEY** — Google Gemini analysis.
   - Get at: https://aistudio.google.com/apikey
   - Cost: Free tier available

6. **PERPLEXITY_API_KEY** — News-grounded analysis.
   - Get at: https://www.perplexity.ai/settings/api
   - Cost: Pay-per-use

7. **POLYGON_API_KEY** — Market news and sentiment data.
   - Get at: https://polygon.io/dashboard/api-keys
   - Cost: Free tier available

---

## Verification

After adding each key, the nightly GitHub Actions run will update
`logs/ai_confluence_health_report.json`. Check:

```
summary.providers_configured  — should increase with each key added
summary.resilience_warning     — should go false once 3+ providers are configured
```

Or trigger a manual run:
1. Go to: https://github.com/CaliEye/My-Investor-Dashboard/actions
2. Select the "Update AI Insights" workflow
3. Click **Run workflow**

---

## Security Notes

- Never commit API keys directly to code or data files
- `config/alpha_vantage_key.js` and `.env` files are in `.gitignore`
- If a key is ever committed by accident: rotate it immediately at the provider's dashboard,
  then remove from git history using `git filter-repo` or contact GitHub support
- The Alpha Vantage key `ZGA6Y5FY790NO4QE` was exposed in a previous commit — rotate it
