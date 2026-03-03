#!/usr/bin/env python3
"""Update dashboard market payload with live ETF sector feeds."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yfinance as yf


REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = REPO_ROOT / "data" / "data.json"

ETF_MAP = {
    "tech": {"symbol": "QQQ", "label": "TECH / NASDAQ-100"},
    "defense": {"symbol": "ITA", "label": "DEFENSE"},
    "metals": {"symbol": "GLD", "label": "PRECIOUS METALS"},
    "broad": {"symbol": "VOO", "label": "BROAD MARKET"},
}

BASKET_SYMBOLS = ["VOO", "QQQ", "XLI", "ITA", "GLD"]


def read_existing_data():
    if DATA_FILE.exists():
        with DATA_FILE.open("r", encoding="utf-8") as file:
            return json.load(file)
    return {}


def to_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def format_price(value):
    return f"${value:,.2f}"


def infer_trend(day_change_pct, five_day_change_pct, vol_ratio):
    if day_change_pct >= 0.6 and five_day_change_pct >= 1.2:
        return "RELATIVE STRENGTH"
    if day_change_pct <= -0.6 and five_day_change_pct <= -1.2:
        return "UNDER PRESSURE"
    if vol_ratio >= 1.35 and day_change_pct > 0:
        return "MOMENTUM BUILD"
    if vol_ratio >= 1.35 and day_change_pct < 0:
        return "HIGH VOLATILITY"
    return "NEUTRAL / MIXED"


def build_etf_snapshot(symbol):
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="1mo", interval="1d", auto_adjust=True)
    if hist.empty:
        raise ValueError(f"No price history returned for {symbol}")

    closes = hist["Close"].dropna()
    volumes = hist["Volume"].dropna()

    if closes.empty:
        raise ValueError(f"No close data returned for {symbol}")

    latest_close = to_float(closes.iloc[-1])
    prev_close = to_float(closes.iloc[-2]) if len(closes) > 1 else latest_close
    close_5d_ago = to_float(closes.iloc[-6]) if len(closes) > 5 else to_float(closes.iloc[0])

    day_change_pct = ((latest_close / prev_close) - 1.0) * 100 if prev_close else 0.0
    five_day_change_pct = ((latest_close / close_5d_ago) - 1.0) * 100 if close_5d_ago else 0.0

    latest_volume = to_float(volumes.iloc[-1]) if not volumes.empty else 0.0
    avg_volume_20d = to_float(volumes.tail(20).mean()) if not volumes.empty else 0.0
    vol_ratio = (latest_volume / avg_volume_20d) if avg_volume_20d else 0.0

    trend = infer_trend(day_change_pct, five_day_change_pct, vol_ratio)

    return {
        "symbol": symbol,
        "price": round(latest_close, 2),
        "price_formatted": format_price(latest_close),
        "change_pct_day": round(day_change_pct, 2),
        "change_pct_5d": round(five_day_change_pct, 2),
        "volume": int(latest_volume) if latest_volume else 0,
        "volume_vs_20d": round(vol_ratio, 2),
        "trend": trend,
    }


def build_sector_etf_payload(existing_data):
    sectors = {}
    for key, config in ETF_MAP.items():
        snapshot = build_etf_snapshot(config["symbol"])
        snapshot["label"] = config["label"]
        sectors[key] = snapshot

    basket = []
    for symbol in BASKET_SYMBOLS:
        snap = build_etf_snapshot(symbol)
        basket.append(
            {
                "symbol": symbol,
                "change_pct_day": snap["change_pct_day"],
                "trend": snap["trend"],
            }
        )

    sorted_basket = sorted(basket, key=lambda item: item["change_pct_day"], reverse=True)
    basket_avg_day = sum(item["change_pct_day"] for item in basket) / len(basket)

    macro_risk = to_float(existing_data.get("macro", {}).get("risk_level"), default=50.0)
    regime_tilt = "DEFENSIVE STACK" if macro_risk >= 65 else "BALANCED STACK"

    return {
        "updated_utc": datetime.now(timezone.utc).isoformat(),
        "sectors": sectors,
        "basket": {
            "symbols": BASKET_SYMBOLS,
            "equal_weight_change_pct_day": round(basket_avg_day, 2),
            "leader": sorted_basket[0],
            "laggard": sorted_basket[-1],
            "regime_tilt": regime_tilt,
        },
    }


def main():
    data = read_existing_data()
    now = datetime.now(timezone.utc)

    sector_etfs = build_sector_etf_payload(data)

    data["updated_utc"] = now.isoformat()
    data["next_review_utc"] = (now + timedelta(hours=4)).isoformat()
    data["sector_etfs"] = sector_etfs

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

    print(f"Updated {DATA_FILE}")


if __name__ == "__main__":
    main()