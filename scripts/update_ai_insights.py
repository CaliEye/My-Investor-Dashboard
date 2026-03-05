#!/usr/bin/env python3
"""
AI Confluence Master - Multi-Source Investment Intelligence

Aggregates analysis from:
- ChatGPT (OpenAI) - Regime analysis
- Grok (X.AI) - Contrarian perspective  
- Alpha Vantage - Technical indicators
- Polygon - Market data & sentiment
- Yahoo Finance - Price/volume data

Generates confluence score based on agreement across sources.
"""

import json
import os
import sys
import requests
import yfinance as yf
from datetime import datetime, timezone
from pathlib import Path


def safe_print(message):
    """Print safely across terminals that may not support emoji/utf-8."""
    encoding = (sys.stdout.encoding or '').lower()
    if 'utf' in encoding:
        print(message)
        return

    fallback = message.encode('ascii', errors='replace').decode('ascii')
    print(fallback)

def load_existing_ai_insights(path: Path):
    """Load current ai_insights file if present."""
    if not path.exists():
        return None

    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        safe_print(f"Warning: could not read existing ai_insights.json: {e}")
        return None

def assess_insights_quality(insights: dict):
    """Score output quality and detect downgrade indicators."""
    if not isinstance(insights, dict):
        return {
            "score": 0,
            "critical_failure": True,
            "reasons": ["Insights payload is not a valid object"]
        }

    reasons = []
    score = 10

    regime = str(insights.get('regime', '')).lower()
    guidance = str(insights.get('contextual_guidance', '')).lower()
    invalidation = str(insights.get('invalidation', '')).lower()
    grok = str(insights.get('grok_counter', '')).lower()
    top_triggers = insights.get('top_triggers', [])
    market = insights.get('market_data', {}) if isinstance(insights.get('market_data', {}), dict) else {}
    sources = insights.get('confluence', {}).get('sources', []) if isinstance(insights.get('confluence', {}), dict) else []

    placeholder_tokens = [
        'api key missing',
        'not configured',
        'cannot provide guidance',
        'cannot analyze',
        'request failed',
        'analysis error'
    ]

    text_fields = [regime, guidance, invalidation, grok]
    placeholder_hits = sum(1 for field in text_fields for token in placeholder_tokens if token in field)
    if placeholder_hits:
        score -= min(placeholder_hits * 2, 6)
        reasons.append('Contains placeholder/error language in core AI fields')

    non_empty_triggers = len([t for t in top_triggers if isinstance(t, str) and t.strip() and 'not configured' not in t.lower()])
    if non_empty_triggers < 2:
        score -= 2
        reasons.append('Insufficient actionable triggers')

    missing_source_notes = 0
    if isinstance(sources, list):
        for src in sources:
            note = str(src.get('note', '')).lower() if isinstance(src, dict) else ''
            if any(token in note for token in ['missing', 'unavailable', 'error']):
                missing_source_notes += 1

    if missing_source_notes >= 2:
        score -= 2
        reasons.append('Multiple confluence sources report missing/error data')

    btc_price = market.get('btc_price')
    if not isinstance(btc_price, (int, float)) or btc_price <= 0:
        score -= 2
        reasons.append('Invalid BTC market snapshot')

    critical_failure = (
        placeholder_hits >= 2 or
        non_empty_triggers == 0 or
        missing_source_notes >= 2
    )

    return {
        "score": max(score, 0),
        "critical_failure": critical_failure,
        "reasons": reasons
    }

def should_write_ai_insights(new_insights: dict, existing_insights: dict):
    """Prevent harmful/downgrade writes that reduce dashboard quality."""
    new_quality = assess_insights_quality(new_insights)

    if existing_insights is None:
        return True, new_quality, None

    existing_quality = assess_insights_quality(existing_insights)

    severe_downgrade = new_quality['score'] < existing_quality['score'] - 2
    harmful_payload = new_quality['critical_failure'] and severe_downgrade
    unnecessary_low_quality_rewrite = (
        new_quality['critical_failure'] and
        new_quality['score'] <= existing_quality['score']
    )

    if harmful_payload or unnecessary_low_quality_rewrite:
        return False, new_quality, existing_quality

    return True, new_quality, existing_quality

def get_yahoo_finance_data():
    """Get current market data from Yahoo Finance"""
    try:
        btc = yf.Ticker("BTC-USD")
        btc_info = btc.history(period="5d")
        
        spy = yf.Ticker("SPY")
        spy_info = spy.history(period="5d")
        
        vix = yf.Ticker("^VIX")
        vix_info = vix.history(period="5d")
        
        return {
            "btc_price": float(btc_info['Close'][-1]),
            "btc_change_5d": float((btc_info['Close'][-1] / btc_info['Close'][0] - 1) * 100),
            "spy_price": float(spy_info['Close'][-1]),
            "spy_change_5d": float((spy_info['Close'][-1] / spy_info['Close'][0] - 1) * 100),
            "vix_level": float(vix_info['Close'][-1]),
            "btc_volume": float(btc_info['Volume'][-1])
        }
    except Exception as e:
        print(f"Yahoo Finance error: {e}")
        return {
            "btc_price": 43200,
            "btc_change_5d": -2.1,
            "spy_price": 445,
            "spy_change_5d": -1.5,
            "vix_level": 18.5,
            "btc_volume": 25000000
        }

def get_alpha_vantage_analysis(btc_price):
    """Get technical analysis from Alpha Vantage"""
    api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
    if not api_key:
        return {"signal": "neutral", "strength": 5, "note": "Alpha Vantage API key missing"}
    
    try:
        url = f"https://www.alphavantage.co/query?function=RSI&symbol=BTCUSD&interval=daily&time_period=14&series_type=close&apikey={api_key}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'Technical Analysis: RSI' in data:
                rsi_data = data['Technical Analysis: RSI']
                latest_date = max(rsi_data.keys())
                current_rsi = float(rsi_data[latest_date]['RSI'])
                
                if current_rsi < 30:
                    return {"signal": "bullish", "strength": 8, "note": f"RSI oversold at {current_rsi:.1f}"}
                elif current_rsi > 70:
                    return {"signal": "bearish", "strength": 7, "note": f"RSI overbought at {current_rsi:.1f}"}
                else:
                    return {"signal": "neutral", "strength": 5, "note": f"RSI neutral at {current_rsi:.1f}"}
        
        return {"signal": "neutral", "strength": 5, "note": "Alpha Vantage data unavailable"}
            
    except Exception as e:
        return {"signal": "neutral", "strength": 5, "note": f"Alpha Vantage error: {str(e)}"}

def get_polygon_sentiment():
    """Get market sentiment from Polygon"""
    api_key = os.getenv('POLYGON_API_KEY')
    if not api_key:
        return {"signal": "neutral", "strength": 5, "note": "Polygon API key missing"}
    
    try:
        url = f"https://api.polygon.io/v2/reference/news?ticker=BTC&limit=10&apikey={api_key}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'results' in data and len(data['results']) > 0:
                news_count = len(data['results'])
                
                positive_words = ['bull', 'rise', 'gain', 'up', 'surge', 'rally']
                negative_words = ['bear', 'fall', 'drop', 'down', 'crash', 'dump']
                
                sentiment_score = 0
                for article in data['results'][:5]:
                    title = article.get('title', '').lower()
                    description = article.get('description', '').lower()
                    text = title + ' ' + description
                    
                    for word in positive_words:
                        sentiment_score += text.count(word)
                    for word in negative_words:
                        sentiment_score -= text.count(word)
                
                if sentiment_score > 2:
                    return {"signal": "bullish", "strength": 7, "note": f"Positive news sentiment (+{sentiment_score})"}
                elif sentiment_score < -2:
                    return {"signal": "bearish", "strength": 7, "note": f"Negative news sentiment ({sentiment_score})"}
                else:
                    return {"signal": "neutral", "strength": 5, "note": "Mixed news sentiment"}
        
        return {"signal": "neutral", "strength": 5, "note": "Polygon data unavailable"}
            
    except Exception as e:
        return {"signal": "neutral", "strength": 5, "note": f"Polygon error: {str(e)}"}

def calculate_confluence_score(chatgpt_result, grok_result, alpha_vantage_result, polygon_result, market_data):
    """Calculate confluence score based on agreement across sources"""
    
    sources = []
    
    regime = chatgpt_result.get('regime', '').lower()
    if 'bear' in regime or 'sell' in regime or 'short' in regime:
        chatgpt_signal = {"signal": "bearish", "strength": 8, "source": "ChatGPT"}
    elif 'bull' in regime or 'buy' in regime or 'long' in regime:
        chatgpt_signal = {"signal": "bullish", "strength": 8, "source": "ChatGPT"}
    else:
        chatgpt_signal = {"signal": "neutral", "strength": 6, "source": "ChatGPT"}
    
    sources.append(chatgpt_signal)
    
    alpha_vantage_result['source'] = 'Alpha Vantage'
    polygon_result['source'] = 'Polygon'
    sources.append(alpha_vantage_result)
    sources.append(polygon_result)
    
    bullish_signals = [s for s in sources if s['signal'] == 'bullish']
    bearish_signals = [s for s in sources if s['signal'] == 'bearish']
    neutral_signals = [s for s in sources if s['signal'] == 'neutral']
    
    bullish_weight = sum([s['strength'] for s in bullish_signals])
    bearish_weight = sum([s['strength'] for s in bearish_signals])
    neutral_weight = sum([s['strength'] for s in neutral_signals])
    
    total_weight = bullish_weight + bearish_weight + neutral_weight
    
    if total_weight == 0:
        return {
            "confluence_score": 5,
            "dominant_signal": "neutral",
            "agreement_pct": 0,
            "source_breakdown": sources,
            "confluence_note": "No valid signals from sources"
        }
    
    bullish_pct = (bullish_weight / total_weight) * 100
    bearish_pct = (bearish_weight / total_weight) * 100
    neutral_pct = (neutral_weight / total_weight) * 100
    
    if bullish_pct > 60:
        dominant_signal = "bullish"
        confluence_score = min(10, int(6 + (bullish_pct - 60) / 10))
    elif bearish_pct > 60:
        dominant_signal = "bearish"
        confluence_score = min(10, int(6 + (bearish_pct - 60) / 10))
    else:
        dominant_signal = "neutral"
        confluence_score = 5
    
    agreement_pct = max(bullish_pct, bearish_pct, neutral_pct)
    
    return {
        "confluence_score": confluence_score,
        "dominant_signal": dominant_signal,
        "agreement_pct": int(agreement_pct),
        "source_breakdown": sources,
        "confluence_note": f"{len(bullish_signals)}B/{len(bearish_signals)}Be/{len(neutral_signals)}N sources"
    }

def read_market_data():
    """Read current market state from data.json"""
    try:
        with open('data/data.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Warning: data/data.json not found, using defaults")
        return {
            "btc_usd": 65000,
            "bias": "Neutral", 
            "triggers": ["No data available"],
            "fear_greed_index": 50,
            "updated_utc": datetime.now(timezone.utc).isoformat()
        }

def read_recent_context():
    """Read recent logs for context (last 1000 chars each)"""
    context = {}
    
    try:
        with open('logs/weekly_scans.md', 'r') as f:
            context['recent_scans'] = f.read()[:1000]
    except FileNotFoundError:
        context['recent_scans'] = "No recent scans available"
    
    try:
        with open('logs/command_log.md', 'r') as f:
            context['recent_commands'] = f.read()[:800]
    except FileNotFoundError:
        context['recent_commands'] = "No recent commands available"
    
    return context

def create_state_object(market_data, context):
    """Create focused state object for AI analysis"""
    return {
        "btc_price": market_data.get('btc_usd', 'N/A'),
        "current_bias": market_data.get('bias', 'Neutral'),
        "active_triggers": market_data.get('triggers', [])[:3],
        "fear_greed": market_data.get('fear_greed_index', 50),
        "recent_scans": context['recent_scans'],
        "recent_commands": context['recent_commands'],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

def get_chatgpt_analysis(state):
    """Get focused regime analysis from ChatGPT"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return {
            "regime": "API key missing",
            "top_triggers": ["OpenAI API key not configured", "", ""],
            "invalidation": "Cannot analyze without API access",
            "contextual_guidance": "Cannot provide guidance without API access"
        }
    
    prompt = f"""
You are a portfolio advisor analyzing current market state for actionable investment guidance.

Current Market State:
- BTC: ${state['btc_price']}
- Current Bias: {state['current_bias']}
- Active Triggers: {', '.join(state['active_triggers'][:3])}
- Fear & Greed: {state['fear_greed']}

Recent Market Analysis:
{state['recent_scans'][:300]}...

Recent Portfolio Actions:
{state['recent_commands'][:200]}...

Provide analysis in this EXACT JSON format:
{{
  "regime": "One clear phrase (e.g., Late Cycle Bullish, Bear Rally, Consolidation)",
  "top_triggers": ["Trigger 1 to monitor", "Trigger 2 to monitor", "Trigger 3 to monitor"],
  "invalidation": "Specific price/event that changes the thesis (e.g., BTC below $62k)",
  "contextual_guidance": "Specific actionable advice based on recent commands and current position. Reference actual trades when possible. 2-3 sentences max."
}}

Make contextual_guidance actionable and specific to the portfolio situation shown in recent commands.
"""

    try:
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'gpt-4',
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 200,
                'temperature': 0.2
            },
            timeout=30
        )
        
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content'].strip()
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {
                    "regime": "Analysis Error", 
                    "top_triggers": ["Failed to parse response", "", ""],
                    "invalidation": content[:100] + "...",
                    "contextual_guidance": "Error parsing AI response"
                }
        else:
            return {
                "regime": f"API Error {response.status_code}",
                "top_triggers": ["OpenAI API failed", "", ""], 
                "invalidation": "Check API status",
                "contextual_guidance": "Cannot provide guidance due to API error"
            }
            
    except Exception as e:
        return {
            "regime": "Request Failed",
            "top_triggers": [f"Error: {str(e)}", "", ""],
            "invalidation": "Check network connection",
            "contextual_guidance": f"Network error: {str(e)}"
        }

def get_grok_counter_analysis(state):
    """Get contrarian perspective from Grok"""
    api_key = os.getenv('XAI_API_KEY')
    if not api_key:
        return "Grok API key not configured"
    
    prompt = f"""
Current consensus: {state['current_bias']}
BTC at ${state['btc_price']}, Fear/Greed: {state['fear_greed']}

What's the strongest counter-argument or narrative risk this week?

Be contrarian and specific. What could the crowd be missing? 1-2 sentences max.
"""

    try:
        response = requests.post(
            'https://api.x.ai/v1/chat/completions',  
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'grok-3',
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 100,
                'temperature': 0.6
            },
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content'].strip()
        else:
            return f"Grok API Error: {response.status_code}"
            
    except Exception as e:
        return f"Grok Error: {str(e)}"

def calculate_confidence_score(chatgpt_result, market_data):
    """Calculate confidence score based on trigger count and consistency"""
    triggers = market_data.get('triggers', [])
    active_triggers = len([t for t in triggers if t and t != "—"])
    
    base_score = min(active_triggers, 6)
    
    regime = chatgpt_result.get('regime', '').lower()
    if 'neutral' not in regime and 'uncertain' not in regime:
        base_score += 2
    
    return min(base_score, 10)


def parse_float_safe(value, default=0.0):
    """Parse numeric strings with symbols safely."""
    if value is None:
        return float(default)
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).replace(',', '')
    token = []
    dot_seen = False
    sign_allowed = True
    for ch in text:
        if ch in '+-' and sign_allowed:
            token.append(ch)
            sign_allowed = False
            continue
        sign_allowed = False
        if ch.isdigit():
            token.append(ch)
            continue
        if ch == '.' and not dot_seen:
            dot_seen = True
            token.append(ch)
            continue
        if token:
            break

    candidate = ''.join(token)
    if not candidate or candidate in {'+', '-', '.', '+.', '-.'}:
        return float(default)

    try:
        return float(candidate)
    except ValueError:
        return float(default)


def infer_market_phase(market_data: dict, yahoo_data: dict, confluence_data: dict) -> str:
    """Classify current behavioral phase for investor psychology mapping."""
    fear_greed = float(market_data.get('sentiment', {}).get('fear_greed_index', 50) or 50)
    vix_level = float(yahoo_data.get('vix_level', 18.0) or 18.0)
    btc_5d = float(yahoo_data.get('btc_change_5d', 0.0) or 0.0)
    signal = str(confluence_data.get('dominant_signal', 'neutral')).lower()

    if fear_greed <= 30 or vix_level >= 25 or btc_5d <= -8:
        return 'crisis'
    if fear_greed >= 70 or (btc_5d >= 8 and signal == 'bullish'):
        return 'euphoria'
    if signal == 'bullish' and btc_5d > 0:
        return 'recovery'
    if signal == 'bearish' and btc_5d < 0:
        return 'distribution'
    return 'range'


def build_investor_behavior_intelligence(market_data: dict, yahoo_data: dict, confluence_data: dict) -> dict:
    """Behavioral finance intelligence for crisis/euphoria and monetization tactics."""
    phase = infer_market_phase(market_data, yahoo_data, confluence_data)
    fear_greed = float(market_data.get('sentiment', {}).get('fear_greed_index', 50) or 50)
    btc_change = float(yahoo_data.get('btc_change_5d', 0.0) or 0.0)
    confluence_score = int(confluence_data.get('confluence_score', 5) or 5)

    crisis_behaviors = [
        "Forced deleveraging and panic selling into support zones",
        "Flight-to-safety toward cash, treasuries, and defensive factors",
        "News-reactive overtrading and short-horizon decision compression",
    ]
    crisis_playbook = [
        "Scale entries in tranches at pre-defined support; never all-in on first dip",
        "Prioritize quality/liquidity assets and cut weak-conviction tails",
        "Use volatility spikes to sell premium or hedge beta when confluence permits",
    ]

    euphoria_behaviors = [
        "FOMO chasing, leverage expansion, and momentum crowding",
        "Narrative extrapolation (assuming recent gains persist indefinitely)",
        "Risk underpricing and stop-discipline decay",
    ]
    euphoria_playbook = [
        "Trim winners into strength and rotate to asymmetric setups",
        "Tighten invalidations and reduce leverage as crowding increases",
        "Favor relative-strength leaders, avoid late low-quality breakouts",
    ]

    if phase == 'crisis':
        current_edge = "Behavioral edge favors patient accumulation + risk-defined hedges while crowd panics."
    elif phase == 'euphoria':
        current_edge = "Behavioral edge favors distribution discipline while crowd overextends risk."
    elif phase == 'recovery':
        current_edge = "Behavioral edge favors selective re-risking in quality leaders after confirmation."
    elif phase == 'distribution':
        current_edge = "Behavioral edge favors defense, cash buffers, and short-bias tactical hedges."
    else:
        current_edge = "Behavioral edge favors mean-reversion discipline and patience until regime resolves."

    conviction = "high" if confluence_score >= 8 else "moderate" if confluence_score >= 6 else "low"

    return {
        "phase": phase,
        "phase_confidence": conviction,
        "state_metrics": {
            "fear_greed": fear_greed,
            "btc_change_5d_pct": round(btc_change, 2),
            "confluence_score": confluence_score,
        },
        "crisis": {
            "typical_investor_behavior": crisis_behaviors,
            "capitalization_playbook": crisis_playbook,
        },
        "euphoria": {
            "typical_investor_behavior": euphoria_behaviors,
            "capitalization_playbook": euphoria_playbook,
        },
        "current_behavioral_edge": current_edge,
    }


def build_predictive_prescriptive_analytics(market_data: dict, yahoo_data: dict, confluence_data: dict) -> dict:
    """Generate predictive and prescriptive analytics for portfolio decisioning."""
    signal = str(confluence_data.get('dominant_signal', 'neutral')).lower()
    score = int(confluence_data.get('confluence_score', 5) or 5)
    fear_greed = parse_float_safe(market_data.get('sentiment', {}).get('fear_greed_index', 50), 50.0)
    dxy = parse_float_safe(market_data.get('macro', {}).get('dxy', 100), 100.0)
    us10y = parse_float_safe(market_data.get('macro', {}).get('us10y_yield', 4), 4.0)

    bearish_prob = 35
    bullish_prob = 35
    range_prob = 30

    if signal == 'bearish':
        bearish_prob += 20
        bullish_prob -= 10
    elif signal == 'bullish':
        bullish_prob += 20
        bearish_prob -= 10

    if fear_greed <= 30:
        range_prob += 5
        bullish_prob += 5
    if fear_greed >= 70:
        bearish_prob += 10

    if dxy >= 103 or us10y >= 4.2:
        bearish_prob += 10
        bullish_prob -= 5

    total = max(1, bearish_prob + bullish_prob + range_prob)
    probs = {
        "bearish_continuation": round((bearish_prob / total) * 100, 1),
        "bullish_reversal": round((bullish_prob / total) * 100, 1),
        "range_mean_reversion": round((range_prob / total) * 100, 1),
    }

    if score >= 8 and signal == 'bullish':
        primary_action = "Risk-on allowed: size into quality strength with strict invalidation."
    elif score >= 8 and signal == 'bearish':
        primary_action = "Risk-off priority: raise cash, hedge beta, avoid weak-breadth dip buys."
    elif score >= 6:
        primary_action = "Moderate conviction: keep smaller sizing, demand cross-asset confirmation."
    else:
        primary_action = "Low conviction: preserve optionality, focus on prep and watchlists."

    return {
        "predictive": {
            "horizon": "1-4 weeks",
            "scenario_probabilities_pct": probs,
            "drivers": [
                "Confluence dominant signal + score",
                "Sentiment extremes (Fear & Greed)",
                "Macro pressure from DXY and US10Y",
            ],
        },
        "prescriptive": {
            "primary_action": primary_action,
            "position_sizing_rule": "Scale 25/25/50 only after confluence gate and invalidation clarity.",
            "risk_controls": [
                "No all-in entries during crisis/euphoria transitions",
                "Cut exposure if macro cascade triggers two or more stress nodes",
                "Prefer liquid instruments when volatility regime is elevated",
            ],
        },
    }


def build_market_pattern_library(market_data: dict) -> list[dict]:
    """Typical market patterns, causes, and portfolio implications."""
    return [
        {
            "pattern": "Liquidity tightening risk-off",
            "typical_causes": [
                "Hawkish policy communication",
                "Balance-sheet contraction / funding stress",
                "Dollar strength and real-yield rise",
            ],
            "market_effects": [
                "High-beta underperforms",
                "Credit spreads widen",
                "Volatility rises and breadth weakens",
            ],
            "investor_implication": "Favor defense/cash, reduce leverage, demand stronger setup quality.",
        },
        {
            "pattern": "Capitulation then reflex rally",
            "typical_causes": [
                "Positioning unwind",
                "Forced liquidations",
                "Extreme negative sentiment",
            ],
            "market_effects": [
                "Sharp downside wick and volatility spike",
                "Fast short-covering rebound",
                "Dispersion between quality and low-quality rebounds",
            ],
            "investor_implication": "Use staged entries and prioritize quality assets over speculative laggards.",
        },
        {
            "pattern": "Late-cycle euphoria blow-off",
            "typical_causes": [
                "Narrative mania + leverage expansion",
                "Chasing breakouts without breadth",
                "Complacency on macro risk",
            ],
            "market_effects": [
                "Momentum crowding",
                "Higher correlation on drawdown",
                "Violent mean-reversion risk",
            ],
            "investor_implication": "Harvest gains into strength and keep tight invalidation discipline.",
        },
    ]


def build_macro_cascade_map(market_data: dict) -> list[dict]:
    """Map large macro shocks into cascading second-order effects and investment impacts."""
    return [
        {
            "macro_shock": "Hawkish Fed surprise",
            "cascade_chain": [
                "Front-end yields jump",
                "USD appreciates",
                "Liquidity tightens across risk assets",
                "Growth/high-duration equities and crypto de-rate",
            ],
            "portfolio_impact": "Increase defense/cash, reduce duration risk and high-beta exposure.",
        },
        {
            "macro_shock": "Energy supply disruption",
            "cascade_chain": [
                "Oil/gas prices rise",
                "Inflation expectations re-accelerate",
                "Rate-cut expectations pushed out",
                "Consumer discretionary margins compress",
            ],
            "portfolio_impact": "Prefer energy/defensive quality, avoid weak balance-sheet cyclicals.",
        },
        {
            "macro_shock": "Credit event / banking stress",
            "cascade_chain": [
                "Credit spreads widen",
                "Funding risk reprices",
                "Risk parity/levered books de-gross",
                "Cross-asset volatility regime shifts higher",
            ],
            "portfolio_impact": "Hedge beta, prioritize liquidity, and wait for stress normalization before re-risking.",
        },
    ]


def build_black_swan_intelligence(market_data: dict, yahoo_data: dict, confluence_data: dict) -> dict:
    """Black swan protection and capitalization framework."""
    fear_greed = parse_float_safe(market_data.get('sentiment', {}).get('fear_greed_index', 50), 50.0)
    vix_level = parse_float_safe(yahoo_data.get('vix_level', 18.0), 18.0)
    score = int(confluence_data.get('confluence_score', 5) or 5)
    signal = str(confluence_data.get('dominant_signal', 'neutral')).lower()

    stress_flags = []
    if vix_level >= 25:
        stress_flags.append('volatility_spike')
    if fear_greed <= 25:
        stress_flags.append('sentiment_capitulation')
    if signal == 'bearish' and score >= 7:
        stress_flags.append('high_conviction_risk_off')

    probability = 'elevated' if len(stress_flags) >= 2 else 'moderate' if len(stress_flags) == 1 else 'low'

    return {
        "probability_assessment": probability,
        "active_stress_flags": stress_flags,
        "protective_playbook": [
            "Pre-define kill-switch levels for beta and leverage before event day",
            "Raise cash buffer and reduce crowded high-beta exposures",
            "Use hedges (index puts / inverse beta / vol overlays) when confluence turns risk-off",
            "Prioritize liquidity-first exits over perfect pricing in shock windows",
        ],
        "capitalization_playbook": [
            "Stage buy ladders into dislocation only after volatility starts normalizing",
            "Rotate into relative-strength defensive leaders first, then cyclicals on confirmation",
            "Exploit forced-liquidation overshoots with strict invalidation and position caps",
            "Harvest mean-reversion gains quickly while uncertainty remains elevated",
        ],
        "risk_controls": {
            "max_single_entry_pct": 25,
            "max_total_deployment_during_shock_pct": 50,
            "mandatory_confirmation": "Require confluence gate + stabilization signal before adding full risk",
        },
    }


def build_black_swan_bot_automation() -> dict:
    """Automation blueprints for capital preservation and opportunistic deployment."""
    return {
        "design_principles": [
            "Automate downside protection first, upside capture second",
            "Use deterministic triggers with human override",
            "Rate-limit execution to avoid overreaction during microstructure noise",
        ],
        "bots": [
            {
                "name": "Volatility Circuit Breaker Bot",
                "trigger": "VIX proxy spike + risk-off confluence + breadth deterioration",
                "actions": [
                    "Auto-reduce beta exposure in tranches",
                    "Raise cash target to pre-set defensive threshold",
                    "Send priority alert with executed hedge summary",
                ],
                "goal": "Preserve gains during shock acceleration",
            },
            {
                "name": "Liquidity Stress Sentinel",
                "trigger": "USD surge + yield spike + widening cross-asset drawdown",
                "actions": [
                    "Pause non-essential new entries",
                    "Enforce tighter stop/invalidation policy",
                    "Escalate to war-room mode with cascade diagnostics",
                ],
                "goal": "Prevent cascading portfolio damage",
            },
            {
                "name": "Dislocation Opportunity Bot",
                "trigger": "Capitulation metrics + stabilization confirmation",
                "actions": [
                    "Deploy staged buy ladder into predefined zones",
                    "Favor high-liquidity quality assets first",
                    "Auto-log expected RR and risk budget before each tranche",
                ],
                "goal": "Capitalize on post-shock mean reversion",
            },
        ],
        "automation_safety": {
            "human_override_required_for_leverage": True,
            "max_orders_per_hour": 4,
            "hard_stop_on_data_quality_degradation": True,
        },
    }


def build_war_market_history_playbook() -> dict:
    """Historical war-regime market behavior and investing playbook for onset vs ending phases."""
    historical_patterns = [
        {
            "event_type": "War onset / surprise escalation",
            "typical_market_response": [
                "Initial risk-off gap and volatility spike",
                "Energy/commodities and defense outperformance",
                "Broad index drawdown followed by policy-driven stabilization",
            ],
            "drivers": [
                "Uncertainty shock",
                "Supply-chain and energy risk repricing",
                "Flight-to-safety positioning",
            ],
        },
        {
            "event_type": "Prolonged conflict",
            "typical_market_response": [
                "High dispersion across sectors",
                "Inflation/commodity sensitivity dominates",
                "Frequent headline whipsaws",
            ],
            "drivers": [
                "Fiscal/defense spending shifts",
                "Commodity supply constraints",
                "Policy-rate path uncertainty",
            ],
        },
        {
            "event_type": "War de-escalation / ending",
            "typical_market_response": [
                "Volatility compression and multiple expansion",
                "Rotation from defensives to cyclicals/risk assets",
                "Improved confidence and cross-border flow normalization",
            ],
            "drivers": [
                "Risk premium unwind",
                "Rebuild/recovery expectations",
                "Lower macro uncertainty",
            ],
        },
    ]

    return {
        "historical_patterns": historical_patterns,
        "war_start_investing_playbook": [
            "Reduce leverage and tighten liquidity management immediately",
            "Overweight resilient sectors (defense, energy, critical infrastructure) selectively",
            "Avoid narrative-chasing; demand confirmation after initial shock",
            "Keep dry powder for dislocation entries once volatility regime stabilizes",
        ],
        "war_ending_investing_playbook": [
            "Gradually rotate from defensives into cyclical/recovery beneficiaries",
            "Increase risk only as breadth and macro confirmations improve",
            "Watch for inflation-growth rebalancing before full beta expansion",
            "Capture re-rating opportunities while maintaining staggered exits",
        ],
        "execution_rule": "Treat war headlines as regime events: update scenario tree before placing discretionary risk.",
    }

def main():
    """Main execution function - Multi-Source AI Confluence System"""
    print("Starting AI Confluence Master - Multi-Source Intelligence Update...")
    
    market_data = read_market_data()
    context = read_recent_context()
    state = create_state_object(market_data, context)
    
    print(f"Market state: BTC ${state['btc_price']}, Bias: {state['current_bias']}")
    
    print("Fetching Yahoo Finance data...")
    yahoo_data = get_yahoo_finance_data()
    
    print("Calling ChatGPT for regime analysis...")
    chatgpt_result = get_chatgpt_analysis(state)
    
    print("Calling Grok for contrarian analysis...")
    grok_result = get_grok_counter_analysis(state)
    
    print("Getting Alpha Vantage technical analysis...")
    alpha_vantage_result = get_alpha_vantage_analysis(yahoo_data['btc_price'])
    
    print("Getting Polygon sentiment analysis...")
    polygon_result = get_polygon_sentiment()
    
    print("Calculating confluence across all sources...")
    confluence_data = calculate_confluence_score(
        chatgpt_result, 
        grok_result, 
        alpha_vantage_result, 
        polygon_result, 
        yahoo_data
    )
    
    confidence_score = calculate_confidence_score(chatgpt_result, market_data)
    
    ai_insights = {
        "updated_utc": datetime.now(timezone.utc).isoformat(),
        "regime": chatgpt_result.get('regime', 'Unknown'),
        "top_triggers": chatgpt_result.get('top_triggers', ["—", "—", "—"]),
        "invalidation": chatgpt_result.get('invalidation', 'No invalidation specified'),
        "contextual_guidance": chatgpt_result.get('contextual_guidance', 'No guidance available'),
        "grok_counter": grok_result,
        "confidence_score": confidence_score,
        "btc_price_snapshot": state['btc_price'],
        "fear_greed_snapshot": state['fear_greed'],
        "next_update": "6 hours",
        
        "confluence": {
            "score": confluence_data['confluence_score'],
            "dominant_signal": confluence_data['dominant_signal'],
            "agreement_pct": confluence_data['agreement_pct'],
            "sources": confluence_data['source_breakdown'],
            "note": confluence_data['confluence_note']
        },
        "market_data": {
            "btc_price": yahoo_data['btc_price'],
            "btc_change_5d": yahoo_data['btc_change_5d'],
            "spy_price": yahoo_data['spy_price'],
            "spy_change_5d": yahoo_data['spy_change_5d'],
            "vix_level": yahoo_data['vix_level'],
            "btc_volume": yahoo_data['btc_volume']
        },
        "technical_analysis": alpha_vantage_result,
        "sentiment_analysis": polygon_result,
        "investor_behavior_intelligence": build_investor_behavior_intelligence(market_data, yahoo_data, confluence_data),
        "analytics": build_predictive_prescriptive_analytics(market_data, yahoo_data, confluence_data),
        "market_pattern_library": build_market_pattern_library(market_data),
        "macro_cascade_map": build_macro_cascade_map(market_data),
        "black_swan_intelligence": build_black_swan_intelligence(market_data, yahoo_data, confluence_data),
        "black_swan_bot_automation": build_black_swan_bot_automation(),
        "war_market_history_playbook": build_war_market_history_playbook()
    }
    
    output_path = Path('data/ai_insights.json')
    output_path.parent.mkdir(parents=True, exist_ok=True)

    existing_insights = load_existing_ai_insights(output_path)
    should_write, new_quality, existing_quality = should_write_ai_insights(ai_insights, existing_insights)

    if not should_write:
        safe_print("Guard: blocked ai_insights.json overwrite to prevent dashboard downgrade")
        safe_print(f"  New quality score: {new_quality['score']}/10")
        if existing_quality:
            safe_print(f"  Existing quality score: {existing_quality['score']}/10")
        if new_quality['reasons']:
            safe_print("  Reasons: " + '; '.join(new_quality['reasons']))
        if isinstance(existing_insights, dict):
            protected_refresh = dict(existing_insights)
            protected_refresh["updated_utc"] = datetime.now(timezone.utc).isoformat()
            protected_refresh["guard_refresh"] = {
                "core_ai_preserved": True,
                "reason": "low_quality_api_output_blocked",
                "core_snapshot_preserved_at": existing_insights.get("updated_utc"),
            }
            protected_refresh["investor_behavior_intelligence"] = build_investor_behavior_intelligence(market_data, yahoo_data, confluence_data)
            protected_refresh["analytics"] = build_predictive_prescriptive_analytics(market_data, yahoo_data, confluence_data)
            protected_refresh["market_pattern_library"] = build_market_pattern_library(market_data)
            protected_refresh["macro_cascade_map"] = build_macro_cascade_map(market_data)
            protected_refresh["black_swan_intelligence"] = build_black_swan_intelligence(market_data, yahoo_data, confluence_data)
            protected_refresh["black_swan_bot_automation"] = build_black_swan_bot_automation()
            protected_refresh["war_market_history_playbook"] = build_war_market_history_playbook()

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(protected_refresh, f, indent=2)

            safe_print("  Core AI text preserved; deterministic intelligence modules refreshed")
        else:
            safe_print("  Kept previous ai_insights.json unchanged")
        return

    if output_path.exists():
        backup_path = output_path.with_suffix('.json.bak')
        try:
            with open(output_path, 'r', encoding='utf-8') as src, open(backup_path, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
        except Exception as e:
            safe_print(f"Warning: could not create backup before write: {e}")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(ai_insights, f, indent=2)

    safe_print(f"Guard quality check passed: {new_quality['score']}/10")
    
    print(f"AI Confluence updated:")
    print(f"  Regime: {ai_insights['regime']}")
    print(f"  Confluence Score: {confluence_data['confluence_score']}/10")
    print(f"  Dominant Signal: {confluence_data['dominant_signal'].upper()}")
    print(f"  Sources Agreement: {confluence_data['agreement_pct']}%")
    print(f"  Output written to: {output_path}")
    
    high_confluence = (
        not new_quality['critical_failure'] and
        confluence_data['confluence_score'] >= 8 and
        confluence_data['dominant_signal'] != 'neutral'
    )
    
    if high_confluence:
        safe_print(f"HIGH CONFLUENCE SIGNAL! Score: {confluence_data['confluence_score']}/10, Agreement: {confluence_data['agreement_pct']}%")
        
        webhook_url = os.getenv('LINDY_WEBHOOK_URL')
        if webhook_url:
            try:
                webhook_data = {
                    "asset": "BTC",
                    "confidence": confluence_data['confluence_score'],
                    "signal": confluence_data['dominant_signal'],
                    "timeframe": "6H",
                    "notes": f"CONFLUENCE: {confluence_data['agreement_pct']}% agreement - {confluence_data['confluence_note']}",
                    "sources": len(confluence_data['source_breakdown']),
                    "btc_price": yahoo_data['btc_price']
                }
                
                response = requests.post(webhook_url, json=webhook_data, timeout=10)
                if response.status_code == 200:
                    safe_print("Enhanced Lindy confluence notification sent successfully")
                else:
                    safe_print(f"Lindy webhook failed: {response.status_code}")
            except Exception as e:
                safe_print(f"Lindy notification error: {e}")
    else:
        safe_print(f"Normal confluence: Score {confluence_data['confluence_score']}/10, Agreement {confluence_data['agreement_pct']}%")

if __name__ == '__main__':
    main()
