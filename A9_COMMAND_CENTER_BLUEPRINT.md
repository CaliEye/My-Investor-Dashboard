# A9 Command Center & Bot Launch Blueprint
*Saved: March 4, 2026 | Lindy AI — CaliEye*

---

## OPERATING RULES
- Run phases **sequentially** — no skipping
- Email checkpoint at each phase end: **"Confluence Check: [Yes/No + Why]"**
- 3+ confluence signals required before any live capital deployment
- No side quests — middle-path focus on endgame money-making only

---

## PHASE 1 — Hardware & Network Foundation
**Target: 2-4 hours**

### Steps
1. Unbox A9 Max
2. Install 128GB Crucial DDR5 RAM
   - 2 screws on bottom panel
   - Swap sticks
   - Boot to BIOS — auto-detect RAM
3. Power on, connect to Pueblo network (Ethernet preferred, Wi-Fi fallback)
4. Power settings: **Never sleep** (Settings > Power > Never)
5. Enable Remote Desktop (Settings > System > Remote Desktop > On)
6. Install Ollama: `curl install.sh | sh`
7. Install LM Studio
8. Download model: `ollama pull llama3.2:3b`

### Confluence Check
- Ping google.com from A9 terminal — success = network live
- Run: `ollama run llama3.2:3b "Test: Confluence on gold cycle?"` — if output aligns, phase complete
- **Gate: Both checks pass = advance to Phase 2**

---

## PHASE 2 — Device Sync & Integration
**Target: 1-2 hours**

### Steps
1. Connect Windows PC to A9 via RDP (Windows RDP app > A9 local IP)
2. Connect Mac to A9 via Microsoft Remote Desktop app
3. Pair Mira glasses: A9 Bluetooth settings > Pair Mira > App setup on phone
4. Set A9 as shared network drive host (File Sharing on)
5. Configure Mira webhook to Lindy

### Confluence Check
- Test file transfer: drag `data.json` from dashboard repo to A9 desktop — success = sync live
- Say "Mira, test sync to A9" — if transcript feeds to Lindy via webhook, confirmed
- Access test file (`mindmap.json`) from Windows, Mac, and Mira app
- **Gate: All 3 devices access shared file = phase locked**

---

## PHASE 3 — Mindmap Brains & Portfolio Setup
**Target: 2-3 hours**

### Steps
1. Upload AI brains to `mindmap.html`
   - JSON/MD files: Buffett, Dalio, market maker frameworks
   - Python parse in `update_data.py` for query routing
2. Build `portfolio.html`
   - Asset classes: BTC, land, houses, art, precious metals
   - Banks, bots, bill/subscription tracking (date calc for dues)
   - CSV import or manual entry
   - Origin AI API fetch in `update_data.py` (if API access granted)
3. Connect trading accounts
   - Pionex API key in `.env` (encrypted with crypto-js)
   - No plaintext keys in repo

### Confluence Check
- Query: "Buffett on rates spike: 3+ signals?" — if response ties to jobs data, brains live
- Calculate total portfolio value + risk score (drop >5% + macro weak = flag)
- Verify 100% accuracy with mock data
- **Gate: "Portfolio Shield: 100% Integrity" confirmed = advance**

---

## PHASE 4 — Bot Setup & Initial Launch
**Target: 4-6 hours**

### Steps
1. Set up Pionex gold bot in `bots.html`
   - API pull for performance and backtests
   - Grok advice: "Optimize initial params: tight stop on 3+ confluence (volume + rates + jobs)"
2. Add long-term candidates: metals ETFs, defensive plays
   - Python loop in `update_data.py` for scans
   - Grok tweaks: "Stoic changes for profitability >85%"
3. Build threshold alerts in `bots.js`
   - Email on breach: drawdown -10% + macro shift
   - Alert fires only on 3+ metrics simultaneously

### Confluence Check
- Backtest 1yr data: Sharpe ratio >1.2 = deploy
- Mock capital test run: drawdown <10%, win rate >40%
- Simulate spike: confirm alert fires only on 3+ metrics
- **Gate: "Bots Armed: Ready to Compound" = phase locked**

---

## PHASE 5 — Activation & Endgame Monitoring
**Target: Ongoing**

### Steps
1. Activate bots live
   - Initial capital: 10% of portfolio max
   - First trade: only on 3+ signals (gold pump + rates drop + volume confirmation)
2. Tie to passive income streams
   - Grok scripts for YouTube Shorts on market cycles
   - Update `goals.html` with progress bar ($100/mo timeline)
3. Full system test
   - Log in from Windows, Mac, and Mira
   - Run macro scan + bot check
4. Lindy schedules weekly reviews, flags deviations

### Confluence Check
- 100% uptime across all devices
- No drift from endgame focus
- **Gate: Email "Endgame Active: Cycles Under Watch" = system live**

---

## CAPITAL RULES (Non-Negotiable)
| Rule | Value |
|------|-------|
| Initial deployment max | 10% of portfolio |
| Scale-up trigger | 7 consecutive profitable days |
| Min confluence to trade | 3+ signals |
| Max drawdown before pause | 10% |
| Min win rate to continue | >40% |
| Min Sharpe to deploy | >1.2 |

---

## HARDWARE STACK
| Device | Role |
|--------|------|
| A9 Max (128GB DDR5) | Always-on sentinel, local AI host |
| Mira Glasses (no-camera) | Eyes on the cycle, hands-free intel |
| Windows PC | Command post — primary trading interface |
| Mac | Command post — secondary / remote access |

---

## WEEKLY REVIEW PROTOCOL (Lindy Automated)
- Every Monday 9am MT: scan bots performance, flag deviations
- Confluence drift check: if 2+ bots underperforming, pause and reassess
- Capital rebalance: withdraw 50% of profits weekly to secure gains
- Report format: email to dicenso01@gmail.com

---

*Blueprint locked. Sequential execution only. No emotional drift. Quiet power.*
