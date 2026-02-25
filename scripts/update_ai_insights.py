#!/usr/bin/env python3
"""
AI Insights Update Script

Reads market data and logs to generate focused AI insights.
Keeps prompts short, deterministic, and tied to actual portfolio data.
"""

import json
import os
import requests
from datetime import datetime, timezone
from pathlib import Path

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
                'model': 'grok-beta',
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
    """Main execution function"""
    print("Starting AI insights update...")
    
    # Read data
    market_data = read_market_data()
    context = read_recent_context()
    state = create_state_object(market_data, context)
    
    print(f"Market state: BTC ${state['btc_price']}, Bias: {state['current_bias']}")
    
    # Get AI analysis
    print("Calling ChatGPT for regime analysis...")
    chatgpt_result = get_chatgpt_analysis(state)
    
    print("Calling Grok for counter-analysis...")
    grok_result = get_grok_counter_analysis(state)
    
    # Calculate confidence
    confidence_score = calculate_confidence_score(chatgpt_result, market_data)
    
    # Build output JSON
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
        "next_update": "6 hours"
    }
    
    # Write output
    output_path = Path('data/ai_insights.json')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(ai_insights, f, indent=2)
    
    print(f"AI insights updated: Regime={ai_insights['regime']}, Confidence={confidence_score}")
    print(f"Output written to: {output_path}")
    
    # Notify if high confidence
    if confidence_score >= 8:
        print(f"🚨 HIGH CONFIDENCE SIGNAL (Score: {confidence_score})")
        
        # Optional Lindy webhook notification
        webhook_url = os.getenv('LINDY_WEBHOOK_URL')
        if webhook_url:
            try:
                webhook_data = {
                    "text": f"🚨 High Confidence Signal (Score: {confidence_score})\n"
                           f"Regime: {ai_insights['regime']}\n"
                           f"Key Risk: {grok_result[:100]}...\n"
                           f"Invalidation: {ai_insights['invalidation']}"
                }
                requests.post(webhook_url, json=webhook_data, timeout=10)
                print("Lindy webhook notification sent")
            except Exception as e:
                print(f"Lindy notification failed: {e}")

if __name__ == "__main__":
    main()