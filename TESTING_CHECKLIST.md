# Dashboard Regression Test Checklist

Run this before every push to main. Open each page in browser, check DevTools console for errors.

---

## Pre-Push: Quick Visual Check (< 5 min)

Open DevTools (F12) and check the Console tab on each page. Zero red 404 errors = pass.

### Pages to check
| Page | URL | Key thing to verify |
|------|-----|---------------------|
| Summary | index.html | BTC price loads, regime label not "UNKNOWN" |
| Macro | macro.html | DXY, US10Y, SPX values all populate |
| Crypto | crypto.html | BTC/ETH prices show, scan log loads or shows "No scan entries yet" |
| Bots | bots.html | Bot table renders, no racing text above backtest section |
| Scenario | scenario.html | Risk posture shows, confluence score visible |
| Insights | insights.html | Confluence score, briefing text, source count badge |
| Goals | goals.html | Goal progress bars load |
| Portfolio | portfolio.html | No all-zeros — hard property values show |
| War Room | warroom.html | Page loads, full nav top and bottom |
| Sentiment | sentiment.html | Page loads, code rain visible |
| Mindmap | mindmap.html | Page loads |
| Links | links.html | Page loads, links render |
| Fortress | fortress-command.html | BTC/ETH change fields not stuck at +0.00% |

---

## Visual Checks (every page)

- [ ] Cinematic background image is visible (not washed out by blue or green overlay)
- [ ] Code rain falls transparently over background, does not block the image
- [ ] Code rain extends full page height (does not stop halfway)
- [ ] No horizontal scrollbar shake or page width jitter
- [ ] Navigation bar present at TOP of page
- [ ] Navigation bar present at BOTTOM of page (footer)
- [ ] No racing/scrolling text visible anywhere on the page
- [ ] Page fade-in transition works on load
- [ ] Mouse movement does NOT cause parallax pull on background image
- [ ] Panel backgrounds are dark neutral (not blue-tinted)

---

## Data Checks

- [ ] `data.json` → `updated_utc` is within last 3 hours (check after a run)
- [ ] `data.json` → `data_stale` field is `false`
- [ ] `data.json` → `crypto.btc_usd` is > 10000 (not the stale $43,200 value)
- [ ] `data.json` → `macro.spx` is > 3000 (not stale)
- [ ] `ai_insights.json` → `updated_at` is within last 8 hours
- [ ] `ai_insights.json` → no field contains "API key missing" as a value
- [ ] `logs/ai_confluence_health_report.json` → `summary.resilience_warning` is checked and understood

---

## Navigation Link Check

On any page, verify these links are in both top nav AND footer nav:
- Summary / index.html
- War Room / warroom.html
- Macro / macro.html
- Crypto / crypto.html
- Bots / bots.html
- Sentiment / sentiment.html
- Scenario Engine / scenario.html
- Mindmap / mindmap.html
- Goals / goals.html
- Portfolio / portfolio.html
- Insights / insights.html
- Quick Links / links.html

---

## After a Code Change (additional)

- [ ] No new CSS 404s in console
- [ ] No new JS 404s in console
- [ ] No new JSON fetch errors in console
- [ ] Confirm the changed page still shows data (not blank)
- [ ] If CSS was changed: check bots.html for the bot-status-card racing text regression
- [ ] If cinematic-background.js was changed: confirm no parallax pull on mouse move
- [ ] If matrix.js was changed: confirm code rain is transparent (no green hue on backgrounds)

---

## API Key / Secrets Check (monthly)

- [ ] Open `logs/ai_confluence_health_report.json` — note `summary.providers_configured`
- [ ] If `providers_configured < 3`, refer to `SECRETS_SETUP.md` and add missing keys
- [ ] Verify no hardcoded API keys in JS/Python files: `grep -r "ZGA6Y5FY" .` should return nothing
- [ ] Rotate any key that has been exposed to a public commit

---

## Deployment Check (after git push)

- [ ] GitHub Actions "Update Market Data" workflow runs without error
- [ ] GitHub Actions "Update AI Insights" workflow runs without error
- [ ] Live site at https://calieye.github.io/My-Investor-Dashboard/ loads correctly
- [ ] Live macro.html shows current data (not stale from before push)
