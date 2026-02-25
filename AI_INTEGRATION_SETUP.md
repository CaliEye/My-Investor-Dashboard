# AI Integration Setup Guide

## Overview
Your dashboard now integrates ChatGPT, Grok, and Lindy using GitHub Actions as the secure brainstem. API keys stay in GitHub Secrets (never exposed in browser), and your dashboard reads AI insights from same-origin JSON files.

## Architecture
```
GitHub Actions (secure) → APIs → data/ai_insights.json → Dashboard (display)
                      → Optional: Lindy webhook notifications
```

## Setup Steps

### 1. Configure GitHub Secrets

In your GitHub repository:
1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add these secrets:

**Required:**
- `OPENAI_API_KEY` — Your OpenAI API key
- `XAI_API_KEY` — Your xAI/Grok API key  

**Optional:**
- `LINDY_WEBHOOK_URL` — Lindy webhook URL for notifications

### 2. Get API Keys

**OpenAI API Key:**
1. Go to https://platform.openai.com/api-keys
2. Create new secret key
3. Copy and paste into `OPENAI_API_KEY` secret

**xAI/Grok API Key:**  
1. Go to https://console.x.ai/ 
2. Create API key
3. Copy and paste into `XAI_API_KEY` secret

**Lindy Webhook (Optional):**
1. Set up Lindy automation
2. Get webhook URL
3. Add to `LINDY_WEBHOOK_URL` secret

### 3. Test the Integration

**Manual Trigger:**
1. Go to **Actions** tab in GitHub
2. Click **AI Insights Update** workflow
3. Click **Run workflow** → **Run workflow**
4. Watch the action run and update `data/ai_insights.json`

**Automatic Schedule:**
- Runs every 3 hours during market hours (9 AM, 12 PM, 3 PM, 6 PM UTC)
- Only on weekdays (Monday-Friday)

### 4. Dashboard Features

Your dashboard now shows:
- **ChatGPT Analysis** — Regime assessment and position guidance
- **Grok Alternative View** — Contrarian perspective and hidden risks
- **Confluence Score** — Signal strength gauge (0-10)
- **Action Bias** — Specific trading recommendations

## How It Works

### Data Flow
1. **GitHub Action triggers** (scheduled or manual)
2. **Reads your market data** (`data/data.json`) and recent logs
3. **Calls OpenAI API** for regime analysis with context
4. **Calls Grok API** for contrarian perspective  
5. **Processes and combines** insights with confluence scoring
6. **Updates** `data/ai_insights.json` and commits to repo
7. **Your dashboard** fetches the new data automatically
8. **Optional**: High-confluence alerts sent to Lindy

### Security Benefits
- ✅ API keys stored securely in GitHub Secrets
- ✅ Never exposed to browser/public code
- ✅ Same-origin JSON loading (no CORS issues)
- ✅ No client-side API calls
- ✅ GitHub Actions environment isolation

### Intelligence Features
- **Context-Aware**: Uses your actual market data and trading history
- **Contrarian Analysis**: Grok provides alternative viewpoints
- **Confluence Scoring**: Measures signal strength across triggers
- **Actionable Guidance**: Specific position sizing recommendations
- **Alert System**: Lindy notifications on high-confidence signals

## Customization

### Adjust Update Frequency
Edit `.github/workflows/ai-insights.yml`:
```yaml
schedule:
  - cron: '0 */2 * * 1-5'  # Every 2 hours, weekdays
```

### Modify AI Prompts
Edit the Python script in the workflow file to customize:
- ChatGPT analysis focus
- Grok contrarian angle  
- Confluence scoring logic
- Action bias thresholds

### Add More AI Models
Extend the workflow with additional API calls:
- Claude (Anthropic)
- Gemini (Google) 
- Custom fine-tuned models

## Troubleshooting

### Action Fails
1. Check **Actions** tab for error logs
2. Verify API keys are correct in Secrets
3. Check API quotas/billing
4. Ensure `data/data.json` exists

### No Data Loading
1. Verify `data/ai_insights.json` exists and has valid JSON
2. Check browser console for fetch errors
3. Ensure GitHub Pages is serving the files

### Missing Insights
1. Check if APIs returned errors in action logs
2. Verify JSON structure matches expected format
3. Look for timeout issues in network requests

## Cost Estimates

**OpenAI (GPT-4):**
- ~150 tokens per request
- 4 requests/day = $0.10-0.30/day

**xAI (Grok):**  
- ~120 tokens per request
- 4 requests/day = pricing varies

**Total:** ~$10-30/month for automated AI insights

## Next Steps

1. **Monitor Performance** — Watch action logs and dashboard updates
2. **Refine Prompts** — Adjust AI instructions based on output quality  
3. **Add Notifications** — Set up Lindy for critical alerts
4. **Expand Context** — Include more data sources in AI analysis
5. **Custom Models** — Train specialized models on your trading data

Your dashboard is now a true **AI-powered investment command center**! 🚀