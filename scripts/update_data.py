#!/usr/bin/env python3
"""
Enhanced Data Update Script - Military Grade Resilience System
Fortress Status: ENHANCED with multi-source confluence validation
Implements: Yahoo Finance + Alpha Vantage + Polygon backup chain
Zero Tolerance: Data breaches eliminated through aggressive validation
"""

import json
import re
from csv import DictReader  
from datetime import datetime, timedelta, timezone
from pathlib import Path
from io import StringIO
import logging

import requests
import yfinance as yf

# Import our fortress system
try:
    from data_fortress import data_fortress, load_api_keys
    FORTRESS_ENABLED = True
    logger = logging.getLogger(__name__)
    logger.info("Data Fortress System: LOADED - Multi-source validation ACTIVE")
except ImportError:
    FORTRESS_ENABLED = False
    logger = logging.getLogger(__name__)
    logger.warning("Data Fortress System: NOT FOUND - Falling back to legacy mode")


REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = REPO_ROOT / "data" / "data.json"

ETF_MAP = {
    "tech": {"symbol": "QQQ", "label": "TECH / NASDAQ-100"},
    "defense": {"symbol": "ITA", "label": "DEFENSE"},
    "metals": {"symbol": "GLD", "label": "PRECIOUS METALS"},
    "broad": {"symbol": "VOO", "label": "BROAD MARKET"},
}

BASKET_SYMBOLS = ["VOO", "QQQ", "XLI", "ITA", "GLD"]

FRED_SERIES = {
    "unemployment": "UNRATE",
    "fed_funds_rate": "FEDFUNDS",
    "cpi_index": "CPIAUCSL",
}


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


def to_number(value, default=0.0):
    if isinstance(value, (int, float)):
        return float(value)
    if value is None:
        return default
    text = str(value)
    match = re.search(r"-?\d+(?:\.\d+)?", text.replace(",", ""))
    if not match:
        return default
    return to_float(match.group(0), default=default)


def format_price(value):
    return f"${value:,.2f}"


def fetch_crypto_prices(existing_crypto):
    """Enhanced crypto price fetching with fortress-grade multi-source validation"""
    btc_price = to_float(existing_crypto.get("btc_usd"), default=0.0)
    eth_price = to_float(existing_crypto.get("eth_usd"), default=0.0)
    
    # Get API keys for fortress system
    api_keys = load_api_keys() if FORTRESS_ENABLED else {}
    
    # Fetch BTC with fortress protection
    if FORTRESS_ENABLED:
        logger.info("Fortress Mode: Fetching BTC with multi-source validation")
        btc_data = data_fortress.get_confluence_data("BTC-USD", api_keys)
        if 'error' not in btc_data:
            btc_price = btc_data.get('price', btc_price)
            fortress_status = btc_data.get('fortress_status', 'UNKNOWN')
            logger.info(f"BTC Fortress Status: {fortress_status} - Sources: {btc_data.get('sources_used', [])}")
    
    # Fallback to legacy Yahoo + CoinGecko if fortress disabled/failed
    if not btc_price or btc_price <= 0:
        try:
            logger.info("Legacy Mode: Fetching BTC from Yahoo Finance")
            btc_hist = yf.Ticker("BTC-USD").history(period="5d", interval="1d", auto_adjust=True)
            if not btc_hist.empty and "Close" in btc_hist:
                btc_price = to_float(btc_hist["Close"].dropna().iloc[-1], default=btc_price)
        except Exception as e:
            logger.warning(f"Yahoo Finance BTC fetch failed: {e}")
    
    # Fetch ETH with fortress protection
    if FORTRESS_ENABLED:
        logger.info("Fortress Mode: Fetching ETH with multi-source validation")
        eth_data = data_fortress.get_confluence_data("ETH-USD", api_keys)
        if 'error' not in eth_data:
            eth_price = eth_data.get('price', eth_price)
            fortress_status = eth_data.get('fortress_status', 'UNKNOWN')
            logger.info(f"ETH Fortress Status: {fortress_status} - Sources: {eth_data.get('sources_used', [])}")
    
    # Fallback to legacy Yahoo + CoinGecko if fortress disabled/failed
    if not eth_price or eth_price <= 0:
        try:
            logger.info("Legacy Mode: Fetching ETH from Yahoo Finance")
            eth_hist = yf.Ticker("ETH-USD").history(period="5d", interval="1d", auto_adjust=True)
            if not eth_hist.empty and "Close" in eth_hist:
                eth_price = to_float(eth_hist["Close"].dropna().iloc[-1], default=eth_price)
        except Exception as e:
            logger.warning(f"Yahoo Finance ETH fetch failed: {e}")

    # CoinGecko backup for both (unchanged legacy fallback)
    if not btc_price or not eth_price:
        try:
            logger.info("Emergency Backup: Using CoinGecko API")
            response = requests.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "bitcoin,ethereum", "vs_currencies": "usd"},
                timeout=8,
            )
            response.raise_for_status()
            payload = response.json()
            if not btc_price:
                btc_price = to_float(payload.get("bitcoin", {}).get("usd"), default=btc_price)
            if not eth_price:
                eth_price = to_float(payload.get("ethereum", {}).get("usd"), default=eth_price)
        except Exception as e:
            logger.error(f"CoinGecko backup failed: {e}")

    updated_fields = {}
    if btc_price:
        updated_fields["btc_usd"] = round(btc_price, 2)
        updated_fields["btc_price_formatted"] = f"${btc_price:,.0f}"
        logger.info(f"BTC Final Price: ${btc_price:,.2f}")
    if eth_price:
        updated_fields["eth_usd"] = round(eth_price, 2)
        updated_fields["eth_price_formatted"] = f"${eth_price:,.0f}"
        logger.info(f"ETH Final Price: ${eth_price:,.2f}")

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
    """Enhanced ETF snapshot with fortress-grade multi-source validation"""
    
    # Load API keys for fortress system
    api_keys = load_api_keys() if FORTRESS_ENABLED else {}
    
    # Attempt fortress-protected data fetch first
    if FORTRESS_ENABLED:
        logger.info(f"Fortress Mode: Fetching {symbol} with multi-source validation")
        fortress_data = data_fortress.get_confluence_data(symbol, api_keys)
        
        if 'error' not in fortress_data and fortress_data.get('price'):
            logger.info(f"{symbol} Fortress Status: {fortress_data.get('fortress_status', 'UNKNOWN')}")
            
            # Use fortress data for current price, but we still need historical data for trends
            fortress_price = fortress_data.get('price')
            fortress_prev_price = fortress_data.get('prev_price', fortress_price)
            
            # Try to get additional historical data from Yahoo for trend analysis
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="1mo", interval="1d", auto_adjust=True)
                
                if not hist.empty and "Close" in hist:
                    closes = hist["Close"].dropna()
                    volumes = hist["Volume"].dropna()
                    
                    # Use fortress price as latest, but historical for trends
                    if len(closes) > 5:
                        close_5d_ago = to_float(closes.iloc[-6])
                    else:
                        close_5d_ago = to_float(closes.iloc[0]) if not closes.empty else fortress_price
                    
                    # Calculate trends using fortress current price
                    day_change_pct = ((fortress_price / fortress_prev_price) - 1.0) * 100 if fortress_prev_price else 0.0
                    five_day_change_pct = ((fortress_price / close_5d_ago) - 1.0) * 100 if close_5d_ago else 0.0
                    
                    # Volume analysis from historical data
                    latest_volume = to_float(volumes.iloc[-1]) if not volumes.empty else 0.0
                    avg_volume_20d = to_float(volumes.tail(20).mean()) if not volumes.empty else 0.0
                    vol_ratio = (latest_volume / avg_volume_20d) if avg_volume_20d else 0.0
                    
                    trend = infer_trend(day_change_pct, five_day_change_pct, vol_ratio)
                    
                    logger.info(f"{symbol} Fortress Success: Price=${fortress_price:.2f}, Change={day_change_pct:.2f}%")
                    
                    return {
                        "symbol": symbol,
                        "price": round(fortress_price, 2),
                        "price_formatted": format_price(fortress_price),
                        "change_pct_day": round(day_change_pct, 2),
                        "change_pct_5d": round(five_day_change_pct, 2),
                        "volume": int(latest_volume) if latest_volume else 0,
                        "volume_vs_20d": round(vol_ratio, 2),
                        "trend": trend,
                        "fortress_status": fortress_data.get('fortress_status', 'SECURE'),
                        "data_sources": fortress_data.get('sources_used', [])
                    }
            except Exception as e:
                logger.warning(f"{symbol} historical data fetch failed: {e}")
                # Fall through to legacy mode below
    
    # Legacy Yahoo Finance mode (fallback when fortress fails or disabled)
    logger.info(f"Legacy Mode: Fetching {symbol} from Yahoo Finance")
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
    
    logger.info(f"{symbol} Legacy Success: Price=${latest_close:.2f}, Change={day_change_pct:.2f}%")

    return {
        "symbol": symbol,
        "price": round(latest_close, 2),
        "price_formatted": format_price(latest_close),
        "change_pct_day": round(day_change_pct, 2),
        "change_pct_5d": round(five_day_change_pct, 2),
        "volume": int(latest_volume) if latest_volume else 0,
        "volume_vs_20d": round(vol_ratio, 2),
        "trend": trend,
        "fortress_status": "LEGACY_MODE",
        "data_sources": ["yahoo"]
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


def fetch_latest_fred_value(series_id):
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv"
    response = requests.get(url, params={"id": series_id}, timeout=10)
    response.raise_for_status()

    rows = list(DictReader(StringIO(response.text)))
    for row in reversed(rows):
        value = row.get(series_id)
        date = row.get("DATE")
        if value and value != "." and date:
            return to_float(value), date
    raise ValueError(f"No valid FRED value for {series_id}")


def fetch_cpi_yoy():
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv"
    response = requests.get(url, params={"id": FRED_SERIES["cpi_index"]}, timeout=10)
    response.raise_for_status()

    rows = list(DictReader(StringIO(response.text)))
    valid_rows = [row for row in rows if row.get(FRED_SERIES["cpi_index"]) not in (None, "", ".")]
    if len(valid_rows) < 13:
        raise ValueError("Not enough CPI history for YoY calculation")

    latest = valid_rows[-1]
    prev_year = valid_rows[-13]
    latest_value = to_float(latest[FRED_SERIES["cpi_index"]], default=0.0)
    prev_value = to_float(prev_year[FRED_SERIES["cpi_index"]], default=0.0)
    if prev_value <= 0:
        raise ValueError("Invalid prior CPI value")

    yoy = ((latest_value / prev_value) - 1.0) * 100.0
    return yoy, latest.get("DATE", "")


def fetch_macro_market_inputs(existing_macro):
    macro = dict(existing_macro or {})

    try:
        spx_hist = yf.Ticker("^GSPC").history(period="10d", interval="1d", auto_adjust=True)
        if not spx_hist.empty and "Close" in spx_hist:
            spx_value = to_float(spx_hist["Close"].dropna().iloc[-1], default=0.0)
            prev_spx = to_float(spx_hist["Close"].dropna().iloc[-2], default=spx_value) if len(spx_hist["Close"].dropna()) > 1 else spx_value
            if spx_value > 0:
                macro["spx"] = f"{spx_value:,.0f}"
                day_change = ((spx_value / prev_spx) - 1.0) * 100 if prev_spx else 0.0
                macro["spx_context"] = f"Daily move {day_change:+.2f}% (live market snapshot)"
    except Exception:
        pass

    dxy_value = None
    for symbol in ("DX-Y.NYB", "DX=F"):
        try:
            dxy_hist = yf.Ticker(symbol).history(period="10d", interval="1d", auto_adjust=True)
            if not dxy_hist.empty and "Close" in dxy_hist:
                dxy_value = to_float(dxy_hist["Close"].dropna().iloc[-1], default=0.0)
                if dxy_value > 0:
                    macro["dxy"] = f"{dxy_value:.1f}"
                    macro["dxy_context"] = (
                        "Elevated (risk-off pressure)" if dxy_value >= 103
                        else "Contained (reduced dollar pressure)"
                    )
                    break
        except Exception:
            continue

    try:
        us10y_hist = yf.Ticker("^TNX").history(period="10d", interval="1d", auto_adjust=True)
        if not us10y_hist.empty and "Close" in us10y_hist:
            raw_yield = to_float(us10y_hist["Close"].dropna().iloc[-1], default=0.0)
            us10y = raw_yield / 10.0 if raw_yield > 20 else raw_yield
            if us10y > 0:
                macro["us10y_yield"] = f"{us10y:.2f}%"
                macro["us10y_context"] = (
                    "High (tight financial conditions)" if us10y >= 4.0
                    else "Moderate (less restrictive rates)"
                )
    except Exception:
        pass

    try:
        unrate, unrate_date = fetch_latest_fred_value(FRED_SERIES["unemployment"])
        macro["unemployment"] = f"{unrate:.1f}%"
        macro["unemployment_context"] = (
            f"Latest official print ({unrate_date}) — labor softening"
            if unrate >= 4.2 else
            f"Latest official print ({unrate_date}) — labor still firm"
        )
    except Exception:
        pass

    try:
        fed_rate, fed_date = fetch_latest_fred_value(FRED_SERIES["fed_funds_rate"])
        macro["fed_funds_rate"] = f"{fed_rate:.2f}%"
        macro["fed_rate_context"] = (
            f"Latest effective rate ({fed_date}) — restrictive"
            if fed_rate >= 4.5 else
            f"Latest effective rate ({fed_date}) — easing/neutral zone"
        )
    except Exception:
        pass

    try:
        cpi_yoy, cpi_date = fetch_cpi_yoy()
        macro["cpi"] = f"{cpi_yoy:.1f}%"
        macro["cpi_context"] = (
            f"Latest official CPI YoY ({cpi_date}) — above target"
            if cpi_yoy >= 2.5 else
            f"Latest official CPI YoY ({cpi_date}) — near target"
        )
    except Exception:
        pass

    return macro


def build_decision_gate_payload(existing_data, sector_etfs):
    macro = existing_data.get("macro", {}) if isinstance(existing_data.get("macro", {}), dict) else {}
    triggers = existing_data.get("triggers", []) if isinstance(existing_data.get("triggers", []), list) else []

    dxy = to_number(macro.get("dxy"), default=0.0)
    us10y = to_number(macro.get("us10y_yield"), default=0.0)
    unemployment = to_number(macro.get("unemployment"), default=0.0)
    macro_risk = to_number(macro.get("risk_level"), default=50.0)
    basket_day = to_number((sector_etfs.get("basket", {}) or {}).get("equal_weight_change_pct_day"), default=0.0)
    spx_context = str(macro.get("spx_context", "")).lower()

    signal_details = []

    if dxy >= 108:
        signal_details.append("DXY > 108 (liquidity headwind)")
    if us10y >= 4.25:
        signal_details.append("US10Y >= 4.25% (tight financial conditions)")
    if unemployment >= 4.2:
        signal_details.append("Unemployment >= 4.2% (growth softening)")
    if basket_day <= -0.8 or "risk-off" in spx_context or "down" in spx_context:
        signal_details.append("Broad risk assets weakening (SPX/ETF breadth pressure)")
    if macro_risk >= 65 or len([t for t in triggers if t]) >= 3:
        signal_details.append("Macro regime flagged high risk")

    confluence_score = min(len(signal_details), 5)
    threshold_hit = confluence_score >= 3

    if confluence_score >= 4:
        risk_posture = "DEFENSIVE"
        next_action = "Hold. Reduce optional risk and update scenarios before any re-entry."
    elif confluence_score >= 3:
        risk_posture = "WATCH-ONLY"
        next_action = "Hold. Update scenario and wait for cleaner alignment before action."
    elif confluence_score == 2:
        risk_posture = "MODERATE"
        next_action = "Small, staged positioning only if invalidation levels are predefined."
    else:
        risk_posture = "RISK-ON"
        next_action = "No immediate stress signal; keep sizing disciplined and confluence-gated."

    return {
        "updated_utc": datetime.now(timezone.utc).isoformat(),
        "confluence_score": confluence_score,
        "max_score": 5,
        "threshold_hit": threshold_hit,
        "signal_count": confluence_score,
        "signals": signal_details,
        "risk_posture": risk_posture,
        "next_best_action": next_action,
        "hard_rule_reminder": "No new crypto risk until Oct/Nov 2026 unless confluence gate flips.",
        "watch_only_until": "2026-11-01",
    }


def main():
    data = read_existing_data()
    now = datetime.now(timezone.utc)

    sector_etfs = build_sector_etf_payload(data)
    crypto = data.get("crypto", {})
    crypto_updates = fetch_crypto_prices(crypto)
    if crypto_updates:
        data["crypto"] = {**crypto, **crypto_updates}

    data["macro"] = fetch_macro_market_inputs(data.get("macro", {}))

    data["updated_utc"] = now.isoformat()
    data["next_review_utc"] = (now + timedelta(hours=4)).isoformat()
    data["sector_etfs"] = sector_etfs
    data["decision_gate"] = build_decision_gate_payload(data, sector_etfs)

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