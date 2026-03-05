# COMPETITIVE INTEL AGENT
**Weekly GitHub AI Surveillance | CaliEye Command Center**
*Runs every Monday 9am MT — auto-delivered via Lindy*

---

## MISSION
Track the AI arms race in real time. Find open-source tools before they go mainstream.
Replace paid APIs before the bill arrives. Deploy locally on A9 Max. Compound quietly.

---

## SURVEILLANCE TARGETS

### Tier 1 — Core Infrastructure (check weekly)
| Repo | Why It Matters | Alert Trigger |
|------|---------------|---------------|
| ollama/ollama | Local LLM server — backbone of free stack | New release |
| ggml-org/llama.cpp | Inference engine — speed improvements | 500+ new stars/week |
| huggingface/transformers | New model families drop here first | New model tag |
| agno-agi/agno | Best multi-agent framework (38k stars) | Major version bump |

### Tier 2 — Trading & Finance Bots (check weekly)
| Repo | Why It Matters | Alert Trigger |
|------|---------------|---------------|
| freqtrade/freqtrade | Crypto trading bot — production-grade | New strategy release |
| jesse-ai/jesse | Backtesting engine — Wyckoff-compatible | New indicator |
| microsoft/qlib | AI quant research from Microsoft | New paper/model |
| QuantConnect/Lean | Institutional-grade algo trading | New asset class support |

### Tier 3 — Passive Income Automation (check bi-weekly)
| Repo | Why It Matters | Alert Trigger |
|------|---------------|---------------|
| n8n-io/n8n | No-code workflow automation | New AI node |
| FlowiseAI/Flowise | Visual LLM pipeline builder | New integration |
| crewAIInc/crewAI | Role-based AI agents | New tool connector |
| Significant-Gravitas/AutoGPT | Autonomous agent framework | New plugin |

---

## WEEKLY SCAN SCRIPT (run on A9 Max)

```bash
#!/bin/bash
# competitive_intel_scan.sh
# Run every Monday morning on A9 Max
# Output: summary of new AI tools worth deploying

echo "=== COMPETITIVE INTEL SCAN — $(date) ==="
echo ""

# Requires: gh CLI authenticated, jq installed
# Install: sudo apt install gh jq

TARGETS=(
 "ollama/ollama"
 "ggml-org/llama.cpp"
 "freqtrade/freqtrade"
 "jesse-ai/jesse"
 "agno-agi/agno"
 "n8n-io/n8n"
 "FlowiseAI/Flowise"
 "microsoft/qlib"
)

echo "--- WATCHED REPOS STATUS ---"
for repo in "${TARGETS[@]}"; do
 stars=$(gh api "repos/$repo" --jq '.stargazers_count' 2>/dev/null)
 updated=$(gh api "repos/$repo" --jq '.updated_at' 2>/dev/null)
 echo "⭐ $stars | $repo | last updated: $updated"
done

echo ""
echo "--- TRENDING THIS WEEK (AI/LLM) ---"
gh api "search/repositories?q=topic:llm+topic:ai+pushed:>$(date -d '7 days ago' +%Y-%m-%d)&sort=stars&order=desc&per_page=5" \
 --jq '.items[] | "⭐ \(.stargazers_count) | \(.full_name) | \(.description)"' 2>/dev/null

echo ""
echo "--- TRENDING THIS WEEK (TRADING BOTS) ---"
gh api "search/repositories?q=topic:trading-bot+topic:crypto+pushed:>$(date -d '7 days ago' +%Y-%m-%d)&sort=stars&order=desc&per_page=5" \
 --jq '.items[] | "⭐ \(.stargazers_count) | \(.full_name) | \(.description)"' 2>/dev/null

echo ""
echo "=== SCAN COMPLETE ==="
```

---

## PAYWALL BYPASS DECISION TREE

```
New AI tool discovered on GitHub
        |
   Is it open-source?
   /              \
 YES               NO
  |                 |
Can it run on       Skip it
A9 Max (CPU)?       (for now)
 /       \
YES        NO (GPU only)
|          |
Deploy     Bookmark —
locally    wait for
          CPU port
  |
Does it replace a paid tool?
 /              \
YES               NO
|                 |
Calculate        Does it
savings          automate
|               income?
>$10/mo          /    \
|             YES     NO
Deploy        Add to   Skip
immediately   passive
             income
             pipeline
```

---

## OPEN-SOURCE REPLACEMENTS DEPLOYED

### Already Live on A9 (after Phase 1 complete)
- [x] **Ollama** → replaces OpenAI API ($0 vs $15-150/mo)
- [x] **SearXNG** → replaces Perplexity Pro ($0 vs $20/mo)
- [x] **Continue.dev** → replaces GitHub Copilot ($0 vs $10/mo)
- [x] **Freqtrade** → replaces paid signal services ($0 vs $50-500/mo)

### Queued for Deployment
- [ ] **n8n (self-hosted)** → replaces Zapier/Make ($0 vs $20-100/mo)
- [ ] **Flowise** → replaces LangChain Cloud ($0 vs $40/mo)
- [ ] **Whisper.cpp** → replaces speech-to-text APIs ($0 vs $30/mo)
- [ ] **Stable Diffusion** → replaces image generation APIs ($0 vs $20/mo)

**Total potential monthly savings: $135-820/month**

---

## INTEL DELIVERY FORMAT (SMS via Lindy — every Monday)

```
🔍 Weekly AI Intel — [Date]

📦 New Deployable Tools:
› [tool name] — [what it replaces] — [savings/mo]

🔥 Trending Repos This Week:
› [repo] — [stars] — [why it matters]

💰 Passive Income Angle:
› [specific automation opportunity]

⚡ Deploy This Week:
› [1 specific action to take]
```

---

## CONFLUENCE RULE FOR DEPLOYMENT

Before deploying any new tool from this list, require:
1. Open-source license confirmed (MIT, Apache 2.0, or GPL)
2. Active maintenance (commit in last 30 days)
3. CPU-compatible OR GPU not required for core function
4. Replaces a paid tool OR directly automates income

All 4 = deploy. Fewer than 4 = watch list only.

---

*Built for CaliEye | Quiet power. No subscriptions. Own the stack.*