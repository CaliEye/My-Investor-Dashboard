#!/usr/bin/env python3
"""Update dashboard market payload with live ETF sector feeds."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
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


def assess_market_payload_quality(payload):
    if not isinstance(payload, dict):
        return {"score": 0, "critical_failure": True, "reasons": ["Payload is not a JSON object"]}

    reasons = []
    score = 10

    macro = payload.get("macro", {}) if isinstance(payload.get("macro", {}), dict) else {}
    crypto = payload.get("crypto", {}) if isinstance(payload.get("crypto", {}), dict) else {}
    sector_etfs = payload.get("sector_etfs", {}) if isinstance(payload.get("sector_etfs", {}), dict) else {}

    required_macro = ["spx", "dxy", "us10y_yield", "fed_funds_rate"]
    missing_macro = [field for field in required_macro if not macro.get(field)]
    if missing_macro:
        score -= 3
        reasons.append(f"Missing macro fields: {', '.join(missing_macro)}")

    btc = to_float(crypto.get("btc_usd"), default=0.0)
    eth = to_float(crypto.get("eth_usd"), default=0.0)
    if btc <= 0 or eth <= 0:
        score -= 3
        reasons.append("Invalid crypto prices")

    sectors = sector_etfs.get("sectors", {}) if isinstance(sector_etfs.get("sectors", {}), dict) else {}
    if len(sectors) < 3:
        score -= 2
        reasons.append("Sector ETF coverage incomplete")

    basket = sector_etfs.get("basket", {}) if isinstance(sector_etfs.get("basket", {}), dict) else {}
    if not basket.get("leader") or not basket.get("laggard"):
        score -= 1
        reasons.append("ETF basket ranking missing")

    critical_failure = (btc <= 0 or eth <= 0) or bool(missing_macro)
    return {
        "score": max(score, 0),
        "critical_failure": critical_failure,
        "reasons": reasons,
    }


def should_write_market_payload(new_payload, existing_payload):
    new_quality = assess_market_payload_quality(new_payload)
    if not existing_payload:
        return True, new_quality, None

    existing_quality = assess_market_payload_quality(existing_payload)
    severe_downgrade = new_quality["score"] < existing_quality["score"] - 2
    unnecessary_low_quality_rewrite = (
        new_quality["critical_failure"] and
        new_quality["score"] <= existing_quality["score"]
    )

    if severe_downgrade and new_quality["critical_failure"]:
        return False, new_quality, existing_quality
    if unnecessary_low_quality_rewrite:
        return False, new_quality, existing_quality

    return True, new_quality, existing_quality


def to_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def format_price(value):
    return f"${value:,.2f}"


def fetch_crypto_prices(existing_crypto):
    btc_price = to_float(existing_crypto.get("btc_usd"), default=0.0)
    eth_price = to_float(existing_crypto.get("eth_usd"), default=0.0)

    try:
        btc_hist = yf.Ticker("BTC-USD").history(period="5d", interval="1d", auto_adjust=True)
        eth_hist = yf.Ticker("ETH-USD").history(period="5d", interval="1d", auto_adjust=True)

        if not btc_hist.empty and "Close" in btc_hist:
            btc_price = to_float(btc_hist["Close"].dropna().iloc[-1], default=btc_price)
        if not eth_hist.empty and "Close" in eth_hist:
            eth_price = to_float(eth_hist["Close"].dropna().iloc[-1], default=eth_price)
    except Exception:
        pass

    if not btc_price or not eth_price:
        try:
            response = requests.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "bitcoin,ethereum", "vs_currencies": "usd"},
                timeout=8,
            )
            response.raise_for_status()
            payload = response.json()
            btc_price = to_float(payload.get("bitcoin", {}).get("usd"), default=btc_price)
            eth_price = to_float(payload.get("ethereum", {}).get("usd"), default=eth_price)
        except Exception:
            pass

    updated_fields = {}
    if btc_price:
        updated_fields["btc_usd"] = round(btc_price, 2)
        updated_fields["btc_price_formatted"] = f"${btc_price:,.0f}"
    if eth_price:
        updated_fields["eth_usd"] = round(eth_price, 2)
        updated_fields["eth_price_formatted"] = f"${eth_price:,.0f}"

    return updated_fields


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
    crypto = data.get("crypto", {})
    crypto_updates = fetch_crypto_prices(crypto)
    if crypto_updates:
        data["crypto"] = {**crypto, **crypto_updates}

    data["updated_utc"] = now.isoformat()
    data["next_review_utc"] = (now + timedelta(hours=4)).isoformat()
    data["sector_etfs"] = sector_etfs

    existing_data = read_existing_data()
    should_write, new_quality, existing_quality = should_write_market_payload(data, existing_data)

    if not should_write:
        print("Guard: blocked data.json overwrite to prevent dashboard downgrade")
        print(f"  New quality score: {new_quality['score']}/10")
        if existing_quality:
            print(f"  Existing quality score: {existing_quality['score']}/10")
        if new_quality["reasons"]:
            print("  Reasons: " + "; ".join(new_quality["reasons"]))
        return

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if DATA_FILE.exists():
        backup_file = DATA_FILE.with_suffix(".json.bak")
        with DATA_FILE.open("r", encoding="utf-8") as src, backup_file.open("w", encoding="utf-8") as dst:
            dst.write(src.read())

    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

    print(f"Guard quality check passed: {new_quality['score']}/10")
    print(f"Updated {DATA_FILE}")


if __name__ == "__main__":
    main()