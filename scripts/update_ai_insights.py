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
import requests
import yfinance as yf
from datetime import datetime, timezone
from pathlib import Path

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
        # Get technical indicators for BTC
        url = f"https://www.alphavantage.co/query?function=RSI&symbol=BTCUSD&interval=daily&time_period=14&series_type=close&apikey={api_key}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'Technical Analysis: RSI' in data:
                rsi_data = data['Technical Analysis: RSI']
                latest_date = max(rsi_data.keys())
                current_rsi = float(rsi_data[latest_date]['RSI'])
                
                # Simple RSI-based signal
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
        # Get market sentiment/news sentiment
        url = f"https://api.polygon.io/v2/reference/news?ticker=BTC&limit=10&apikey={api_key}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'results' in data and len(data['results']) > 0:
                # Simple sentiment analysis based on news count and keywords
                news_count = len(data['results'])
                
                # Basic sentiment scoring (would be enhanced with NLP)
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
    
    # Extract signals from each source
    sources = []
    
    # ChatGPT signal (from regime analysis)
    regime = chatgpt_result.get('regime', '').lower()
    if 'bear' in regime or 'sell' in regime or 'short' in regime:
        chatgpt_signal = {"signal": "bearish", "strength": 8, "source": "ChatGPT"}
    elif 'bull' in regime or 'buy' in regime or 'long' in regime:
        chatgpt_signal = {"signal": "bullish", "strength": 8, "source": "ChatGPT"}
    else:
        chatgpt_signal = {"signal": "neutral", "strength": 6, "source": "ChatGPT"}
    
    sources.append(chatgpt_signal)
    
    # Add other sources
    alpha_vantage_result['source'] = 'Alpha Vantage'
    polygon_result['source'] = 'Polygon'
    sources.append(alpha_vantage_result)
    sources.append(polygon_result)
    
    # Grok provides contrarian view (handled separately)
    
    # Calculate confluence
    bullish_signals = [s for s in sources if s['signal'] == 'bullish']
    bearish_signals = [s for s in sources if s['signal'] == 'bearish']
    neutral_signals = [s for s in sources if s['signal'] == 'neutral']
    
    # Weight by strength
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
    
    # Calculate percentages
    bullish_pct = (bullish_weight / total_weight) * 100
    bearish_pct = (bearish_weight / total_weight) * 100
    neutral_pct = (neutral_weight / total_weight) * 100
    
    # Determine dominant signal and confluence score
    if bullish_pct > 60:
        dominant_signal = "bullish"
        confluence_score = min(10, int(6 + (bullish_pct - 60) / 10))
    elif bearish_pct > 60:
        dominant_signal = "bearish"
        confluence_score = min(10, int(6 + (bearish_pct - 60) / 10))
    else:
        dominant_signal = "neutral"
        confluence_score = 5
    
    # Agreement percentage (how much sources agree)
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
    
    # Recent scans
    try:
        with open('logs/weekly_scans.md', 'r') as f:
            context['recent_scans'] = f.read()[:1000]
    except FileNotFoundError:
        context['recent_scans'] = "No recent scans available"
    
    # Recent commands  
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
            # Try to parse JSON response
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Fallback parsing if not valid JSON
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
                'model': 'grok-4-latest',
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
    
    # Base score from active triggers (0-6)
    base_score = min(active_triggers, 6)
    
    # Boost if regime is decisive (not neutral)
    regime = chatgpt_result.get('regime', '').lower()
    if 'neutral' not in regime and 'uncertain' not in regime:
        base_score += 2
    
    # Cap at 10
    return min(base_score, 10)

def main():
    """Main execution function - Multi-Source AI Confluence System"""
    print("Starting AI Confluence Master - Multi-Source Intelligence Update...")
    
    # Read data
    market_data = read_market_data()
    context = read_recent_context()
    state = create_state_object(market_data, context)
    
    print(f"Market state: BTC ${state['btc_price']}, Bias: {state['current_bias']}")
    
    # Get fresh Yahoo Finance data
    print("Fetching Yahoo Finance data...")
    yahoo_data = get_yahoo_finance_data()
    
    # Get AI analysis from all sources
    print("Calling ChatGPT for regime analysis...")
    chatgpt_result = get_chatgpt_analysis(state)
    
    print("Calling Grok for contrarian analysis...")
    grok_result = get_grok_counter_analysis(state)
    
    print("Getting Alpha Vantage technical analysis...")
    alpha_vantage_result = get_alpha_vantage_analysis(yahoo_data['btc_price'])
    
    print("Getting Polygon sentiment analysis...")
    polygon_result = get_polygon_sentiment()
    
    # Calculate confluence score
    print("Calculating confluence across all sources...")
    confluence_data = calculate_confluence_score(
        chatgpt_result, 
        grok_result, 
        alpha_vantage_result, 
        polygon_result, 
        yahoo_data
    )
    
    # Legacy confidence score for compatibility
    confidence_score = calculate_confidence_score(chatgpt_result, market_data)
    
    # Build enhanced output JSON with confluence data
    ai_insights = {
        "updated_utc": datetime.now(timezone.utc).isoformat(),
        # Core ChatGPT Analysis (legacy compatibility)
        "regime": chatgpt_result.get('regime', 'Unknown'),
        "top_triggers": chatgpt_result.get('top_triggers', ["—", "—", "—"]),
        "invalidation": chatgpt_result.get('invalidation', 'No invalidation specified'),
        "contextual_guidance": chatgpt_result.get('contextual_guidance', 'No guidance available'),
        "grok_counter": grok_result,
        "confidence_score": confidence_score,
        "btc_price_snapshot": state['btc_price'],
        "fear_greed_snapshot": state['fear_greed'],
        "next_update": "6 hours",
        
        # New Multi-Source Confluence Data
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
        "sentiment_analysis": polygon_result
    }
    
    # Write output
    output_path = Path('data/ai_insights.json')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(ai_insights, f, indent=2)
    
    print(f"AI Confluence updated:")
    print(f"  Regime: {ai_insights['regime']}")
    print(f"  Confluence Score: {confluence_data['confluence_score']}/10")
    print(f"  Dominant Signal: {confluence_data['dominant_signal'].upper()}")
    print(f"  Sources Agreement: {confluence_data['agreement_pct']}%")
    print(f"  Output written to: {output_path}")
    
    # High confluence notification (8+ score or 80%+ agreement)
    high_confluence = confluence_data['confluence_score'] >= 8 or confluence_data['agreement_pct'] >= 80
    
    if high_confluence:
        print(f"🚨 HIGH CONFLUENCE SIGNAL! Score: {confluence_data['confluence_score']}/10, Agreement: {confluence_data['agreement_pct']}%")
        
        # Enhanced Lindy webhook with confluence data
        webhook_url = os.getenv('LINDY_WEBHOOK_URL')
        if webhook_url:
            try:
                # Create enhanced Lindy payload with confluence data
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
                    print("✅ Enhanced Lindy confluence notification sent successfully")
                else:
                    print(f"⚠️ Lindy webhook failed: {response.status_code}")
            except Exception as e:
                print(f"❌ Lindy notification error: {e}")
    else:
        print(f"📊 Normal confluence: Score {confluence_data['confluence_score']}/10, Agreement {confluence_data['agreement_pct']}%")

if __name__ == '__main__':
    main()