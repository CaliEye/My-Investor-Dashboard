#!/usr/bin/env python3
"""
TradingView Webhook Integration — CaliEye Dashboard
==================================================

PURPOSE:
  Receives alerts from TradingView Pine Script alerts and merges them
  into the dashboard's active_alerts feed. TradingView is the FINAL
  external trigger layer — it provides real-time price action alerts
  that complement the AI confluence system.

ARCHITECTURE:
  TradingView Alert → HTTP POST → This webhook → dashboard/logs/tv_alerts.json
  → alert_engine.py reads tv_alerts.json → merges into data.json active_alerts

HOW TO DEPLOY:
  Option A (Cloudflare Worker - RECOMMENDED - free, no server needed):
    1. Create a Cloudflare Worker at workers.cloudflare.com
    2. Deploy the JS handler below as the worker
    3. Use the worker URL as your TradingView webhook URL
    4. Worker writes to KV storage or sends to GitHub dispatch API

  Option B (Local Flask server - for testing only):
    pip install flask
    python tradingview_webhook.py --serve
    Use ngrok to expose locally: ngrok http 5000

  Option C (GitHub Actions webhook dispatch):
    TradingView → GitHub repository_dispatch → workflow runs alert processing
    This is the ZERO-INFRASTRUCTURE approach.

TRADINGVIEW ALERT FORMAT (Pine Script):
  Use this JSON template in your TradingView alert message:
  {
    "ticker": "{{ticker}}",
    "exchange": "{{exchange}}",
    "interval": "{{interval}}",
    "time": "{{time}}",
    "price": {{close}},
    "volume": {{volume}},
    "alert_name": "{{strategy.order.alert_message}}",
    "source": "tradingview"
  }

RECOMMENDED TRADINGVIEW ALERTS TO CREATE:
  1. RSI Weekly Oversold (< 28) on BTC, ETH, SPY, QQQ
  2. MACD Bullish Cross (daily) on key assets
  3. Price breaks 200 SMA (daily) — both directions
  4. Volume Surge (> 2x 20-day average) with directional move
  5. Bollinger Band squeeze breakout
  6. Wyckoff Spring/UTAD confirmation (manual annotation)

CLOUDFLARE WORKER (JavaScript — paste at workers.cloudflare.com):
---
export default {
  async fetch(request, env) {
    if (request.method !== 'POST') {
      return new Response('Method Not Allowed', { status: 405 });
    }

    const SECRET = env.WEBHOOK_SECRET || '';
    const authHeader = request.headers.get('X-Webhook-Secret') || '';
    if (SECRET && authHeader !== SECRET) {
      return new Response('Unauthorized', { status: 401 });
    }

    try {
      const alert = await request.json();
      alert.received_utc = new Date().toISOString();
      alert.source = 'tradingview';

      // Forward to GitHub Actions dispatch
      const ghResponse = await fetch(
        `https://api.github.com/repos/${env.GH_REPO}/dispatches`,
        {
          method: 'POST',
          headers: {
            'Authorization': `token ${env.GH_TOKEN}`,
            'Content-Type': 'application/json',
            'Accept': 'application/vnd.github.v3+json',
          },
          body: JSON.stringify({
            event_type: 'tradingview_alert',
            client_payload: { alert }
          })
        }
      );

      if (ghResponse.ok) {
        return new Response(JSON.stringify({ status: 'ok', forwarded: true }), {
          headers: { 'Content-Type': 'application/json' }
        });
      } else {
        return new Response('GitHub dispatch failed', { status: 500 });
      }
    } catch (e) {
      return new Response(`Error: ${e.message}`, { status: 400 });
    }
  }
};
---

ENV VARS needed in Cloudflare Worker:
  WEBHOOK_SECRET=your_random_secret_here
  GH_TOKEN=your_github_pat_here
  GH_REPO=CaliEye/My-Investor-Dashboard

GITHUB ACTIONS WORKFLOW (triggered by dispatch):
  See .github/workflows/process-tv-alert.yml
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
TV_ALERTS_FILE = REPO_ROOT / "logs" / "tv_alerts.json"
TV_ALERTS_FEED_FILE = REPO_ROOT / "data" / "tv_alerts_feed.json"

# Maximum alerts to keep in feed
MAX_FEED_SIZE = 50


def _load_feed() -> list:
    if TV_ALERTS_FEED_FILE.exists():
        with TV_ALERTS_FEED_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    return []


def normalize_tv_alert(raw: dict) -> dict:
    """
    Normalize a TradingView webhook payload into a standard alert format.
    TradingView sends variable formats — this normalizes to dashboard format.
    """
    ticker = str(raw.get("ticker", raw.get("symbol", "UNKNOWN"))).upper()
    price = raw.get("price", raw.get("close", 0))
    interval = raw.get("interval", raw.get("timeframe", "D"))
    alert_name = str(raw.get("alert_name", raw.get("message", "TV Alert")))
    ts = raw.get("time", datetime.now(timezone.utc).isoformat())

    # Map ticker to dashboard key
    ticker_map = {
        "BTCUSD": "btc", "BTC": "btc", "BTCUSDT": "btc",
        "ETHUSD": "eth", "ETH": "eth", "ETHUSDT": "eth",
        "SPY": "spx", "SPX": "spx", "ES1!": "spx",
        "QQQ": "qqq", "NQ1!": "qqq",
        "GLD": "gold", "GOLD": "gold", "XAUUSD": "gold",
        "SLV": "silver", "XAGUSD": "silver",
        "TLT": "tlt", "ZB1!": "tlt",
        "DXY": "dxy", "DX1!": "dxy",
        "USO": "oil", "CL1!": "oil", "USOIL": "oil",
        "ITA": "ita", "LMT": "lmt", "RTX": "rtx", "NOC": "noc",
        "GDX": "gdx", "REMX": "remx",
    }
    key = ticker_map.get(ticker, ticker.lower()[:6])

    # Auto-classify alert type from name
    name_lower = alert_name.lower()
    if any(w in name_lower for w in ["oversold", "rsi low", "below 30"]):
        alert_type = "TV_RSI_OVERSOLD"
        severity = "HIGH"
    elif any(w in name_lower for w in ["overbought", "rsi high", "above 70"]):
        alert_type = "TV_RSI_OVERBOUGHT"
        severity = "MEDIUM"
    elif any(w in name_lower for w in ["macd cross", "bullish cross", "bull cross"]):
        alert_type = "TV_MACD_CROSS"
        severity = "MEDIUM"
    elif any(w in name_lower for w in ["200 sma", "200ma", "200-day"]):
        alert_type = "TV_200SMA_EVENT"
        severity = "HIGH"
    elif any(w in name_lower for w in ["volume", "vol surge"]):
        alert_type = "TV_VOLUME_SURGE"
        severity = "MEDIUM"
    elif any(w in name_lower for w in ["breakout", "breakdown"]):
        alert_type = "TV_BREAKOUT"
        severity = "HIGH"
    elif any(w in name_lower for w in ["spring", "wyckoff", "utad"]):
        alert_type = "TV_WYCKOFF"
        severity = "HIGH"
    else:
        alert_type = "TV_CUSTOM"
        severity = "INFO"

    return {
        "id": f"tv_{key}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "source": "tradingview",
        "key": key,
        "ticker": ticker,
        "label": f"{ticker} ({interval})",
        "alert_type": alert_type,
        "severity": severity,
        "confidence": 65,  # TV alerts get base 65% — boosted by confluence with indicators
        "action": f"TradingView: {alert_name}",
        "signals": [f"TradingView alert: {alert_name}", f"Price: {price}", f"Interval: {interval}"],
        "price": price,
        "interval": interval,
        "risk_level": 50,
        "timeframe": "current session",
        "fired_utc": ts,
        "raw": raw,
    }


def process_incoming_alert(raw_payload: dict) -> dict:
    """
    Process a single incoming TradingView alert.
    Normalizes, scores, writes to feed.
    """
    alert = normalize_tv_alert(raw_payload)

    # Load existing feed
    feed = _load_feed()

    # Deduplicate: don't add same alert type + key within 30 minutes
    recent_ids = {f"{a['key']}_{a['alert_type']}" for a in feed[-20:]}
    dedup_key = f"{alert['key']}_{alert['alert_type']}"

    if dedup_key in recent_ids:
        logger.info(f"Deduplication: skipping repeated {dedup_key}")
        return {"status": "deduplicated", "alert": alert}

    # Prepend to feed (newest first)
    feed.insert(0, alert)

    # Trim to max size
    feed = feed[:MAX_FEED_SIZE]

    # Write feed
    TV_ALERTS_FEED_FILE.parent.mkdir(parents=True, exist_ok=True)
    with TV_ALERTS_FEED_FILE.open("w", encoding="utf-8") as f:
        json.dump(feed, f, indent=2)

    logger.info(f"TV alert saved: {alert['key'].upper()} {alert['alert_type']}")
    return {"status": "saved", "alert": alert}


def get_active_tv_alerts(max_age_hours: int = 24) -> list:
    """
    Return TV alerts from the last N hours — for use by alert_engine.py.
    """
    feed = _load_feed()
    cutoff = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)

    active = []
    for alert in feed:
        try:
            ts = datetime.fromisoformat(alert.get("fired_utc", "")).timestamp()
            if ts >= cutoff:
                active.append(alert)
        except Exception:
            active.append(alert)  # Include if can't parse timestamp

    return active


def serve():
    """
    Local Flask development server for testing TradingView webhooks.
    NOT for production — use Cloudflare Worker in production.
    """
    try:
        from flask import Flask, request, jsonify
    except ImportError:
        print("Flask not installed. Run: pip install flask")
        sys.exit(1)

    app = Flask(__name__)
    logging.basicConfig(level=logging.INFO)

    @app.route("/webhook/tradingview", methods=["POST"])
    def tv_webhook():
        secret = request.headers.get("X-Webhook-Secret", "")
        # In production, validate secret
        payload = request.get_json(force=True)
        if not payload:
            return jsonify({"error": "Invalid JSON"}), 400

        result = process_incoming_alert(payload)
        return jsonify(result)

    @app.route("/alerts", methods=["GET"])
    def get_alerts():
        alerts = get_active_tv_alerts()
        return jsonify({"count": len(alerts), "alerts": alerts})

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "server": "tradingview-webhook-local"})

    print("TradingView webhook server running at http://localhost:5000")
    print("Webhook endpoint: POST http://localhost:5000/webhook/tradingview")
    print("Use ngrok to expose: ngrok http 5000")
    app.run(host="0.0.0.0", port=5000, debug=False)


if __name__ == "__main__":
    if "--serve" in sys.argv:
        serve()
    else:
        # Test with sample payload
        test_payload = {
            "ticker": "BTCUSDT",
            "exchange": "BINANCE",
            "interval": "1D",
            "time": datetime.now(timezone.utc).isoformat(),
            "price": 67000,
            "volume": 42000,
            "alert_name": "RSI Weekly Oversold < 28",
            "source": "tradingview"
        }
        result = process_incoming_alert(test_payload)
        print(f"Test result: {result['status']}")
        print(f"Alert type: {result['alert']['alert_type']}")
        print(f"Feed size: {len(_load_feed())} alerts")
