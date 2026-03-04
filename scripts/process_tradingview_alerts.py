#!/usr/bin/env python3
"""Process TradingView alert feed into confluence escalation output."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FEED_FILE = REPO_ROOT / "data" / "tradingview_alert_feed.json"
OUTPUT_FILE = REPO_ROOT / "data" / "confluence_alerts.json"

ROLLING_WINDOW_HOURS = 72

ASSET_CLASS_MAP = {
    "YIELD_CURVE": "macro",
    "CREDIT_SPREADS": "credit",
    "UNEMPLOYMENT": "macro",
    "JOBLESS_CLAIMS": "macro",
    "DXY": "dollar",
    "GOLD": "metals",
    "10Y_YIELD": "rates",
    "VIX": "volatility",
    "BREADTH": "breadth",
    "SPX": "equities",
    "QQQ": "equities",
    "BTC": "crypto",
    "BTC_DOMINANCE": "crypto",
    "ETH": "crypto",
    "ETH_BTC": "crypto",
    "CRYPTO_SENTIMENT": "crypto",
}

WEIGHTS = {
    "DE-INVERTED": 2,
    "SAHM_BUILDING": 2,
    "HYG_BELOW_50SMA": 2,
    "HYG_SPIKE_DOWN": 2,
    "ABOVE_30": 2,
    "BELOW_200SMA": 2,
    "ABOVE_106": 1,
    "BELOW_100": 1,
    "RAPID_DROP": 1,
    "CLAIMS_RISING": 1,
    "ABOVE_60": 1,
    "BELOW_40": 1,
    "ADD_MINUS_1000": 1,
    "CORRECTION_10PCT": 1,
    "DROP_15PCT": 1,
    "ABOVE_3200": 1,
    "BELOW_2500": 1,
    "ABOVE_100K": 1,
    "BELOW_30K": 1,
}

TIER2_SIGNALS = {
    "SAHM_TRIGGERED",
    "ABOVE_108",
    "BELOW_98",
    "ABOVE_5_5",
    "ABOVE_6000",
    "DROP_5PCT_SESSION",
    "BEAR_MARKET_20PCT",
    "ABOVE_45",
    "EXTREME_MOVE_20PCT",
    "CIRCUIT_BREAKER",
}


def parse_alert(message: str) -> dict:
    parts = [p.strip() for p in message.split("|")]
    parsed = {
        "tier": parts[0] if parts else "TIER1",
        "asset": "UNKNOWN",
        "signal": "UNKNOWN",
        "direction": "WATCH",
        "note": message,
    }

    for part in parts[1:]:
        if ":" not in part:
            continue
        key, value = [x.strip() for x in part.split(":", 1)]
        key_upper = key.upper()
        if key_upper == "ASSET":
            parsed["asset"] = value
        elif key_upper == "SIGNAL":
            parsed["signal"] = value
        elif key_upper == "DIR":
            parsed["direction"] = value
        elif key_upper == "NOTE":
            parsed["note"] = value

    parsed["asset_class"] = ASSET_CLASS_MAP.get(parsed["asset"], "other")
    parsed["weight"] = WEIGHTS.get(parsed["signal"], 1)
    return parsed


def load_feed() -> list[dict]:
    if not FEED_FILE.exists():
        return []

    try:
        with FEED_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, list):
            return data
        return data.get("alerts", []) if isinstance(data, dict) else []
    except Exception:
        return []


def iso_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_ts(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return iso_now()


def compute_confluence(alerts: list[dict]) -> dict:
    now = iso_now()
    cutoff = now - timedelta(hours=ROLLING_WINDOW_HOURS)

    parsed_recent = []
    tier2_recent = []
    scores = defaultdict(int)
    classes = defaultdict(set)

    for entry in alerts:
        ts = parse_ts(str(entry.get("timestamp", now.isoformat())))
        if ts < cutoff:
            continue

        parsed = parse_alert(str(entry.get("message", "")))
        parsed["timestamp"] = ts.isoformat()
        parsed_recent.append(parsed)

        direction = parsed.get("direction", "WATCH")
        if parsed.get("tier") == "TIER2" or parsed.get("signal") in TIER2_SIGNALS:
            tier2_recent.append(parsed)
        if direction in ("BEAR", "BULL", "BULL_ALTS", "BEAR_ALTS", "DYNAMIC"):
            key = "BEAR" if "BEAR" in direction else "BULL"
            scores[key] += parsed.get("weight", 1)
            classes[key].add(parsed.get("asset_class", "other"))

    dominant = "NEUTRAL"
    if scores["BEAR"] > scores["BULL"]:
        dominant = "BEAR"
    elif scores["BULL"] > scores["BEAR"]:
        dominant = "BULL"

    dominant_score = max(scores["BEAR"], scores["BULL"])
    dominant_classes = len(classes[dominant]) if dominant in classes else 0

    threshold_hit = dominant_score >= 3 and dominant_classes >= 2
    urgency = "NORMAL"
    if dominant_score >= 7:
        urgency = "PRE-CRISIS"
    elif dominant_score >= 5:
        urgency = "ELEVATED"

    return {
        "updated_utc": now.isoformat(),
        "window_hours": ROLLING_WINDOW_HOURS,
        "summary": {
            "dominant_direction": dominant,
            "score_bear": scores["BEAR"],
            "score_bull": scores["BULL"],
            "dominant_score": dominant_score,
            "asset_classes_in_dominant_direction": dominant_classes,
            "threshold_hit": threshold_hit,
            "urgency": urgency,
        },
        "tier2": {
            "active": len(tier2_recent) > 0,
            "count": len(tier2_recent),
            "latest": tier2_recent[0] if tier2_recent else None,
        },
        "recent_alerts": sorted(parsed_recent, key=lambda item: item["timestamp"], reverse=True)[:50],
    }


def main() -> None:
    feed = load_feed()
    result = compute_confluence(feed)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(result, file, indent=2)

    print(f"Processed {len(feed)} TradingView alerts -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
