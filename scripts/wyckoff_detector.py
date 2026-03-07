#!/usr/bin/env python3
"""
Wyckoff Phase Detection Engine — CaliEye Endgame Dashboard
------------------------------------------------------------
Implements Richard Wyckoff's market cycle methodology algorithmically.
Detects: Accumulation, Distribution, Markup, Markdown phases.
Identifies Spring (false breakdown) and UTAD (false breakout) events.

Phase logic:
  ACCUMULATION — smart money loading. Volume > on up-days. Price ranging near lows.
  MARKUP       — breakout confirmed. Price trending above SMA20 > SMA50. Momentum building.
  DISTRIBUTION — smart money unloading. Volume > on down-days. Price ranging near highs.
  MARKDOWN     — breakdown confirmed. Price trending below SMA20 < SMA50.

Alert conditions (surfaces to dashboard):
  Spring alert  — Wyckoff Accumulation Phase C. Price tested below support and recovered.
  UTAD alert    — Wyckoff Distribution Phase C. Price pierced above resistance and fell back.
  High-conf acc — Accumulation confidence >= 70. Potential markup building.
  High-conf dist— Distribution confidence >= 70. Potential markdown risk.

Only alerts with confidence >= 65 are pushed to active_alerts in data.json.
AIs and red team should feed from data["wyckoff"]["active_alerts"].
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

try:
    import numpy as np
    NUMPY_OK = True
except ImportError:
    NUMPY_OK = False
    logger.warning("numpy not available — Wyckoff detection disabled")

try:
    import yfinance as yf
    YFINANCE_OK = True
except ImportError:
    YFINANCE_OK = False
    logger.warning("yfinance not available — Wyckoff fetching disabled")


# ---------------------------------------------------------------------------
# Asset map: internal key → yfinance symbol
# ---------------------------------------------------------------------------
WYCKOFF_ASSETS = {
    "btc":      {"symbol": "BTC-USD",   "label": "Bitcoin"},
    "eth":      {"symbol": "ETH-USD",   "label": "Ethereum"},
    "gold":     {"symbol": "GLD",       "label": "Gold / GLD"},
    "silver":   {"symbol": "SLV",       "label": "Silver / SLV"},
    "spx":      {"symbol": "SPY",       "label": "S&P 500 / SPY"},
    "tech":     {"symbol": "QQQ",       "label": "Nasdaq-100 / QQQ"},
    "bonds":    {"symbol": "TLT",       "label": "Long Bonds / TLT"},
    "oil":      {"symbol": "USO",       "label": "Oil / USO"},
    "defense":  {"symbol": "ITA",       "label": "Defense / ITA"},
    "lmt":      {"symbol": "LMT",       "label": "Lockheed Martin"},
    "rtx":      {"symbol": "RTX",       "label": "RTX Corp"},
    "noc":      {"symbol": "NOC",       "label": "Northrop Grumman"},
    "antimony": {"symbol": "REMX",      "label": "Antimony / Strategic Metals (REMX)"},
    "miners":   {"symbol": "GDX",       "label": "Gold Miners / GDX"},
}

ALERT_CONFIDENCE_THRESHOLD = 65
SPRING_UTAD_THRESHOLD      = 60   # lower — spring/UTAD events are always noteworthy


# ---------------------------------------------------------------------------
# Core computation helpers
# ---------------------------------------------------------------------------

def _compute_rsi(closes, period=14):
    """RSI via Wilder's smoothed average."""
    if len(closes) < period + 1:
        return 50.0
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains  = [max(d, 0) for d in deltas]
    losses = [max(-d, 0) for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)


def _sma(closes, period):
    if len(closes) < period:
        return closes[-1] if closes else 0
    return sum(closes[-period:]) / period


def _vol_ratio(closes, volumes, window=20):
    """
    Ratio of average volume on up-days to average volume on down-days.
    > 1.0 = demand dominant (bullish pressure)
    < 1.0 = supply dominant (bearish pressure)
    """
    if len(closes) < window + 1 or len(volumes) < window + 1:
        return 1.0
    recent_c = closes[-(window + 1):]
    recent_v = volumes[-window:]
    up_vol, dn_vol, up_n, dn_n = 0.0, 0.0, 0, 0
    for i in range(window):
        if recent_c[i + 1] >= recent_c[i]:
            up_vol += recent_v[i]
            up_n += 1
        else:
            dn_vol += recent_v[i]
            dn_n += 1
    avg_up = up_vol / up_n if up_n else 0
    avg_dn = dn_vol / dn_n if dn_n else 1
    return round(avg_up / avg_dn, 3) if avg_dn > 0 else 1.0


# ---------------------------------------------------------------------------
# Main phase detection
# ---------------------------------------------------------------------------

def detect_phase(closes, volumes, highs, lows):
    """
    Detect Wyckoff phase from OHLCV arrays (oldest first, most recent last).

    Returns dict:
        phase            — ACCUMULATION / MARKUP / DISTRIBUTION / MARKDOWN / RANGING
        confidence       — 0-100
        range_high       — upper bound of detected trading range
        range_low        — lower bound
        range_position   — 0.0 (at low) to 1.0 (at high) within range
        vol_ratio        — demand/supply volume ratio
        rsi              — current RSI-14 daily
        spring_detected  — bool: price dipped below support and recovered
        utad_detected    — bool: price pierced above resistance and fell back
        alert            — bool: should surface to dashboard
        alert_type       — SPRING | UTAD | ACCUMULATION | DISTRIBUTION | None
        trending_up      — bool
        trending_down    — bool
        sma20            — 20-period SMA
        sma50            — 50-period SMA
    """
    min_candles = 60
    if len(closes) < min_candles:
        return _empty_result("Insufficient data")

    closes  = list(closes)
    volumes = list(volumes)
    highs   = list(highs)
    lows    = list(lows)

    # ── Trading range analysis (last 30 days) ──────────────────────────────
    range_window = min(30, len(closes))
    range_high   = max(closes[-range_window:])
    range_low    = min(closes[-range_window:])
    price_range  = range_high - range_low
    range_pct    = price_range / range_low if range_low > 0 else 0
    is_ranging   = range_pct < 0.15          # price within 15% = range-bound

    current = closes[-1]
    range_pos = (current - range_low) / price_range if price_range > 0 else 0.5

    # ── Volume analysis ─────────────────────────────────────────────────────
    vr = _vol_ratio(closes, volumes, window=20)

    # ── RSI ─────────────────────────────────────────────────────────────────
    rsi = _compute_rsi(closes, 14)

    # ── Trend analysis ──────────────────────────────────────────────────────
    sma20 = _sma(closes, 20)
    sma50 = _sma(closes, 50)
    trending_up   = current > sma20 and sma20 > sma50
    trending_down = current < sma20 and sma20 < sma50

    # ── 6-month context ─────────────────────────────────────────────────────
    ctx_window   = min(130, len(closes))
    six_mo_high  = max(closes[-ctx_window:])
    six_mo_low   = min(closes[-ctx_window:])
    near_high    = current > six_mo_high * 0.88
    near_low     = current < six_mo_high * 0.70

    # ── Spring detection ────────────────────────────────────────────────────
    # Price dipped below range_low in last 15 days but is now back inside range
    spring_window = min(15, len(lows))
    spring_detected = (
        any(l < range_low * 0.985 for l in lows[-spring_window:])
        and current > range_low
    )

    # ── UTAD detection ──────────────────────────────────────────────────────
    # Price pierced above range_high in last 15 days but fell back
    utad_window = min(15, len(highs))
    utad_detected = (
        any(h > range_high * 1.015 for h in highs[-utad_window:])
        and current < range_high
    )

    # ── Phase scoring ───────────────────────────────────────────────────────
    accum_score = 0
    dist_score  = 0
    markup_score  = 0
    markdown_score = 0

    # Accumulation signals
    if is_ranging:            accum_score += 25
    if vr > 1.1:              accum_score += int((vr - 1.0) * 25)
    if 30 <= rsi <= 55:       accum_score += int((55 - rsi) * 0.6)
    if near_low:              accum_score += 15
    if range_pos < 0.45:      accum_score += 10
    if spring_detected:       accum_score += 20

    # Distribution signals
    if is_ranging:            dist_score += 25
    if vr < 0.92:             dist_score += int((1.0 - vr) * 35)
    if 55 <= rsi <= 80:       dist_score += int((rsi - 55) * 0.7)
    if near_high:             dist_score += 15
    if range_pos > 0.55:      dist_score += 10
    if utad_detected:         dist_score += 20

    # Markup signals
    if trending_up:           markup_score += 40
    if rsi > 55:              markup_score += int((rsi - 55) * 0.8)
    if not is_ranging:        markup_score += 15
    if current > range_high * 1.02: markup_score += 15

    # Markdown signals
    if trending_down:         markdown_score += 40
    if rsi < 45:              markdown_score += int((45 - rsi) * 0.8)
    if not is_ranging:        markdown_score += 15
    if current < range_low * 0.98:  markdown_score += 15

    # ── Phase selection ──────────────────────────────────────────────────────
    scores = {
        "ACCUMULATION": min(accum_score, 95),
        "DISTRIBUTION": min(dist_score, 95),
        "MARKUP":       min(markup_score, 90),
        "MARKDOWN":     min(markdown_score, 90),
    }
    phase      = max(scores, key=scores.get)
    confidence = scores[phase]

    # Ambiguous → RANGING
    sorted_scores = sorted(scores.values(), reverse=True)
    if sorted_scores[0] - sorted_scores[1] < 8:
        phase = "RANGING"
        confidence = 40

    # ── Alert logic ─────────────────────────────────────────────────────────
    alert      = False
    alert_type = None

    if spring_detected and phase == "ACCUMULATION" and confidence >= SPRING_UTAD_THRESHOLD:
        alert      = True
        alert_type = "SPRING"
    elif utad_detected and phase == "DISTRIBUTION" and confidence >= SPRING_UTAD_THRESHOLD:
        alert      = True
        alert_type = "UTAD"
    elif phase in ("ACCUMULATION", "DISTRIBUTION") and confidence >= ALERT_CONFIDENCE_THRESHOLD:
        alert      = True
        alert_type = phase

    return {
        "phase":           phase,
        "confidence":      round(confidence),
        "range_high":      round(range_high, 4),
        "range_low":       round(range_low, 4),
        "range_position":  round(range_pos, 3),
        "vol_ratio":       vr,
        "rsi":             rsi,
        "sma20":           round(sma20, 4),
        "sma50":           round(sma50, 4),
        "spring_detected": spring_detected,
        "utad_detected":   utad_detected,
        "trending_up":     trending_up,
        "trending_down":   trending_down,
        "alert":           alert,
        "alert_type":      alert_type,
    }


def _empty_result(reason=""):
    return {
        "phase": "UNKNOWN", "confidence": 0,
        "range_high": 0, "range_low": 0, "range_position": 0.5,
        "vol_ratio": 1.0, "rsi": 50.0, "sma20": 0, "sma50": 0,
        "spring_detected": False, "utad_detected": False,
        "trending_up": False, "trending_down": False,
        "alert": False, "alert_type": None,
        "error": reason,
    }


# ---------------------------------------------------------------------------
# Alert message generator
# ---------------------------------------------------------------------------

def build_alert_message(result, label):
    phase = result.get("phase", "UNKNOWN")
    conf  = result.get("confidence", 0)
    rsi   = result.get("rsi", 50)
    vr    = result.get("vol_ratio", 1.0)

    if result.get("alert_type") == "SPRING":
        return (
            f"⚡ SPRING DETECTED — {label} | Wyckoff Accumulation Phase C. "
            f"Price tested below support and recovered. Smart money defended the low. "
            f"Potential markup imminent. RSI {rsi} | Vol ratio {vr:.2f}x | Confidence {conf}%"
        )
    if result.get("alert_type") == "UTAD":
        return (
            f"⚠ UTAD DETECTED — {label} | Wyckoff Distribution Phase C. "
            f"Price pierced above resistance and fell back. Supply absorbing demand at highs. "
            f"Markdown approaching. RSI {rsi} | Vol ratio {vr:.2f}x | Confidence {conf}%"
        )
    if phase == "ACCUMULATION":
        return (
            f"🟢 ACCUMULATION — {label} | Smart money loading. "
            f"Vol demand {vr:.2f}x supply. RSI {rsi} (basing). "
            f"Building cause for markup. Confidence {conf}%"
        )
    if phase == "DISTRIBUTION":
        return (
            f"🔴 DISTRIBUTION — {label} | Smart money unloading. "
            f"Supply {(1/vr):.2f}x demand. RSI {rsi} (elevated). "
            f"Risk of markdown increasing. Confidence {conf}%"
        )
    if phase == "MARKUP":
        return f"📈 MARKUP — {label} | Trending up. RSI {rsi}. Ride the trend, watch for distribution near highs."
    if phase == "MARKDOWN":
        return f"📉 MARKDOWN — {label} | Trending down. RSI {rsi}. Avoid longs. Watch for accumulation at lows."
    return f"⬜ RANGING — {label} | No clear Wyckoff signal. RSI {rsi}. Monitor for breakout or breakdown."


# ---------------------------------------------------------------------------
# Fetcher: pulls OHLCV from yfinance and runs detection
# ---------------------------------------------------------------------------

def analyze_asset(key, existing_result=None):
    """
    Fetch OHLCV data for one asset key and run Wyckoff analysis.
    Falls back to existing_result on any error.
    """
    if not YFINANCE_OK:
        return existing_result or _empty_result("yfinance unavailable")

    asset_meta = WYCKOFF_ASSETS.get(key)
    if not asset_meta:
        return _empty_result(f"Unknown asset key: {key}")

    symbol = asset_meta["symbol"]
    label  = asset_meta["label"]

    try:
        ticker = yf.Ticker(symbol)
        hist   = ticker.history(period="6mo", interval="1d", auto_adjust=True)

        if hist.empty or len(hist) < 60:
            raise ValueError(f"Insufficient history ({len(hist)} candles)")

        closes  = hist["Close"].dropna().tolist()
        volumes = hist["Volume"].dropna().tolist()
        highs   = hist["High"].dropna().tolist()
        lows    = hist["Low"].dropna().tolist()

        # Align lengths
        min_len = min(len(closes), len(volumes), len(highs), len(lows))
        closes  = closes[-min_len:]
        volumes = volumes[-min_len:]
        highs   = highs[-min_len:]
        lows    = lows[-min_len:]

        result = detect_phase(closes, volumes, highs, lows)
        result["label"]      = label
        result["symbol"]     = symbol
        result["message"]    = build_alert_message(result, label)
        result["asset_key"]  = key
        result["updated"]    = datetime.now(timezone.utc).isoformat()
        return result

    except Exception as exc:
        logger.warning("Wyckoff fetch failed for %s (%s): %s", key, symbol, exc)
        fallback = dict(existing_result) if existing_result else _empty_result(str(exc))
        fallback["label"]     = label
        fallback["symbol"]    = symbol
        fallback["asset_key"] = key
        return fallback


# ---------------------------------------------------------------------------
# Batch runner — called from update_data.py
# ---------------------------------------------------------------------------

def run_all(existing_wyckoff=None):
    """
    Run Wyckoff analysis across all tracked assets.
    Returns the full wyckoff dict for data.json["wyckoff"].
    """
    existing_wyckoff = existing_wyckoff or {}
    existing_assets  = existing_wyckoff.get("assets", {})

    results      = {}
    active_alerts = []

    for key in WYCKOFF_ASSETS:
        existing = existing_assets.get(key)
        result   = analyze_asset(key, existing_result=existing)
        results[key] = result

        if result.get("alert") and result.get("confidence", 0) >= ALERT_CONFIDENCE_THRESHOLD:
            active_alerts.append({
                "asset_key":  key,
                "asset":      result.get("label", key),
                "phase":      result.get("phase"),
                "confidence": result.get("confidence"),
                "alert_type": result.get("alert_type"),
                "message":    result.get("message", ""),
                "rsi":        result.get("rsi"),
                "vol_ratio":  result.get("vol_ratio"),
            })

    # Sort alerts: springs/UTADs first, then by confidence desc
    def sort_key(a):
        priority = 0 if a["alert_type"] in ("SPRING", "UTAD") else 1
        return (priority, -a["confidence"])

    active_alerts.sort(key=sort_key)

    return {
        "last_updated":  datetime.now(timezone.utc).isoformat(),
        "assets":        results,
        "active_alerts": active_alerts,
        "alert_count":   len(active_alerts),
    }


if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO)
    data = run_all()
    print(json.dumps({
        "alert_count":   data["alert_count"],
        "active_alerts": data["active_alerts"],
        "phases": {k: v.get("phase") for k, v in data["assets"].items()},
    }, indent=2))
