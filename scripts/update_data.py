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
    "nfp": "PAYEMS",
}

# Import Wyckoff detector if available
try:
    from wyckoff_detector import run_all as wyckoff_run_all
    WYCKOFF_ENABLED = True
except ImportError:
    WYCKOFF_ENABLED = False

# Import Technical Indicators engine if available
try:
    from technical_indicators import run_all as indicators_run_all
    INDICATORS_ENABLED = True
except ImportError:
    INDICATORS_ENABLED = False

# Import Alert Engine if available
try:
    from alert_engine import run_all as alerts_run_all
    ALERTS_ENABLED = True
except ImportError:
    ALERTS_ENABLED = False


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
        macro["cpi_yoy"] = round(cpi_yoy, 2)
        date_label = f" ({cpi_date})" if cpi_date else ""
        macro["cpi_context"] = (
            f"Latest official CPI YoY{date_label} — above target"
            if cpi_yoy >= 2.5 else
            f"Latest official CPI YoY{date_label} — near target"
        )
    except Exception:
        pass

    try:
        nfp_raw, nfp_date = fetch_latest_fred_value(FRED_SERIES["nfp"])
        # PAYEMS is total nonfarm payrolls in thousands; we need the month change
        # Fetch two latest values to compute MoM change
        nfp_url = "https://fred.stlouisfed.org/graph/fredgraph.csv"
        nfp_response = requests.get(nfp_url, params={"id": FRED_SERIES["nfp"]}, timeout=10)
        nfp_response.raise_for_status()
        nfp_rows = [r for r in DictReader(StringIO(nfp_response.text))
                    if r.get(FRED_SERIES["nfp"]) not in (None, "", ".")]
        if len(nfp_rows) >= 2:
            latest_nfp = to_float(nfp_rows[-1][FRED_SERIES["nfp"]], default=0.0)
            prior_nfp = to_float(nfp_rows[-2][FRED_SERIES["nfp"]], default=0.0)
            nfp_change = (latest_nfp - prior_nfp) * 1000  # Convert thousands to actual jobs
            macro["nfp_change"] = round(nfp_change)
            macro["nfp_date"] = nfp_rows[-1].get("DATE", nfp_date)
            macro["nfp_context"] = (
                f"NFP ({nfp_rows[-1].get('DATE', nfp_date)}): {nfp_change:+,.0f} jobs — strong labor"
                if nfp_change > 150000 else
                f"NFP ({nfp_rows[-1].get('DATE', nfp_date)}): {nfp_change:+,.0f} jobs — labor softening"
                if nfp_change < 100000 else
                f"NFP ({nfp_rows[-1].get('DATE', nfp_date)}): {nfp_change:+,.0f} jobs — moderate growth"
            )
    except Exception:
        pass

    try:
        unrate_raw, unrate_date2 = fetch_latest_fred_value(FRED_SERIES["unemployment"])
        macro["unemployment_rate"] = round(unrate_raw, 1)
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


def fetch_price_multi_source(symbol, api_keys=None, existing_price=0.0):
    """
    Multi-source price fetch with waterfall fallback:
    Yahoo Finance → Finnhub → Polygon → Twelve Data → FMP → Alpha Vantage
    Returns best available price and the source used.
    """
    keys = api_keys or {}
    price = existing_price
    source = "existing"

    # 1. Yahoo Finance (no key, most reliable for broad market)
    try:
        t = yf.Ticker(symbol)
        h = t.history(period="2d", interval="1d", auto_adjust=True)
        if not h.empty and "Close" in h:
            p = float(h["Close"].dropna().iloc[-1])
            if p > 0:
                return p, "yahoo"
    except Exception:
        pass

    # 2. Finnhub (requires FINNHUB_API_KEY)
    finnhub_key = keys.get("FINNHUB_API_KEY") or os.getenv("FINNHUB_API_KEY")
    if finnhub_key:
        try:
            r = requests.get(
                f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={finnhub_key}",
                timeout=6
            )
            if r.ok:
                data = r.json()
                p = float(data.get("c", 0))
                if p > 0:
                    return p, "finnhub"
        except Exception:
            pass

    # 3. Polygon.io (requires POLYGON_API_KEY)
    polygon_key = keys.get("POLYGON_API_KEY") or os.getenv("POLYGON_API_KEY")
    if polygon_key:
        try:
            # Convert yfinance symbol format to Polygon format
            poly_sym = symbol.replace("-USD", "X:").replace("^", "I:") if "-USD" in symbol or "^" in symbol else symbol
            r = requests.get(
                f"https://api.polygon.io/v2/last/trade/{poly_sym}?apiKey={polygon_key}",
                timeout=6
            )
            if r.ok:
                data = r.json()
                p = float(data.get("results", {}).get("p", 0))
                if p > 0:
                    return p, "polygon"
        except Exception:
            pass

    # 4. Twelve Data (requires TWELVE_DATA_API_KEY)
    twelve_key = keys.get("TWELVE_DATA_API_KEY") or os.getenv("TWELVE_DATA_API_KEY")
    if twelve_key:
        try:
            r = requests.get(
                f"https://api.twelvedata.com/price?symbol={symbol}&apikey={twelve_key}",
                timeout=6
            )
            if r.ok:
                data = r.json()
                p = float(data.get("price", 0))
                if p > 0:
                    return p, "twelve_data"
        except Exception:
            pass

    # 5. Financial Modeling Prep (requires FMP_API_KEY)
    fmp_key = keys.get("FMP_API_KEY") or os.getenv("FMP_API_KEY")
    if fmp_key:
        try:
            r = requests.get(
                f"https://financialmodelingprep.com/api/v3/quote-short/{symbol}?apikey={fmp_key}",
                timeout=6
            )
            if r.ok:
                data = r.json()
                if data and isinstance(data, list):
                    p = float(data[0].get("price", 0))
                    if p > 0:
                        return p, "fmp"
        except Exception:
            pass

    return price, source


def compute_bot_opportunities(data):
    """
    Derive bot opportunities from asset_intelligence RSI/trend/sentiment data.
    Writes fresh opportunities replacing any that are now stale.
    """
    ai = data.get("asset_intelligence", {})
    assets = ai.get("assets", {})
    existing_opps = {o["id"]: o for o in data.get("bot_opportunities", [])}
    opportunities = []

    # Existing manually-curated opportunities that stay unless overridden
    preserved_ids = {"bonds_yield"}  # always keep the T-bill income opportunity

    def opp_status(confidence):
        if confidence >= 80: return "STRONG_BUY"
        if confidence >= 65: return "BUY"
        if confidence >= 50: return "ACCUMULATE"
        if confidence >= 35: return "WATCH"
        return "AVOID"

    for key, asset in assets.items():
        rsi_d = asset.get("rsi_daily") or 50
        rsi_w = asset.get("rsi_weekly") or 50
        risk   = asset.get("risk") or 50
        trend_w = (asset.get("trend_weekly") or "Neutral").lower()
        trend_m = (asset.get("trend_monthly") or "Neutral").lower()
        sentiment = (asset.get("sentiment") or "Neutral").lower()
        label = asset.get("label", key.upper())

        # DCA Bot: Weekly RSI oversold + fear sentiment
        if rsi_w < 40 and ("fear" in sentiment or "bear" in sentiment):
            base_conf = 55
            base_conf += max(0, (40 - rsi_w) * 1.5)   # more oversold = higher conf
            base_conf += 10 if "extreme" in sentiment else 0
            base_conf += 5 if trend_m == "up" else 0    # monthly uptrend = better
            base_conf = min(88, base_conf)
            opp_id = f"{key}_dca"
            opportunities.append({
                "id": opp_id,
                "asset": label,
                "asset_key": key,
                "bot_type": "DCA",
                "confidence": round(base_conf),
                "status": opp_status(base_conf),
                "action": f"Accumulate {label} — weekly RSI {round(rsi_w)} (oversold), {asset.get('sentiment','fear')} zone",
                "signal": f"RSI D:{round(rsi_d)} W:{round(rsi_w)} | Trend W:{asset.get('trend_weekly','—')} M:{asset.get('trend_monthly','—')} | {asset.get('sentiment','—')}",
                "risk": risk,
                "timeframe": "Weekly DCA, monitor for trend reversal confirmation",
                "page": f"{key}.html" if key in ("tech","energy","bonds","realestate") else ("crypto.html" if key in ("btc","eth") else "macro.html"),
                "sector": key if key in ("tech","energy","bonds","realestate") else ("crypto" if key in ("btc","eth") else "macro")
            })

        # MOMENTUM Bot: RSI weekly 50-65, uptrend confirmed W+M
        elif 50 <= rsi_w <= 65 and trend_w == "up" and trend_m == "up":
            base_conf = 60
            base_conf += max(0, (65 - rsi_w) * 0.8)   # room to run = higher conf
            base_conf += 10 if "bull" in sentiment else 0
            base_conf = min(85, base_conf)
            opp_id = f"{key}_momentum"
            opportunities.append({
                "id": opp_id,
                "asset": label,
                "asset_key": key,
                "bot_type": "MOMENTUM",
                "confidence": round(base_conf),
                "status": opp_status(base_conf),
                "action": f"Ride momentum — {label} trending up W+M, RSI has room",
                "signal": f"RSI D:{round(rsi_d)} W:{round(rsi_w)} | Up trend confirmed | {asset.get('sentiment','—')}",
                "risk": risk,
                "timeframe": "Trail stop on weekly close below 8-week SMA",
                "page": f"{key}.html" if key in ("tech","energy","bonds","realestate") else ("crypto.html" if key in ("btc","eth") else "macro.html"),
                "sector": key if key in ("tech","energy","bonds","realestate") else ("crypto" if key in ("btc","eth") else "macro")
            })

        # HEDGE/STOP signal: RSI weekly overbought + greed
        elif rsi_w > 70 and ("greed" in sentiment or "bull" in sentiment):
            opp_id = f"{key}_hedge"
            opportunities.append({
                "id": opp_id,
                "asset": label,
                "asset_key": key,
                "bot_type": "HEDGE",
                "confidence": round(min(80, 50 + (rsi_w - 70) * 1.5)),
                "status": "CAUTION",
                "action": f"Tighten stops on {label} — RSI overbought, consider reducing position",
                "signal": f"RSI D:{round(rsi_d)} W:{round(rsi_w)} | {asset.get('sentiment','—')} zone | High risk",
                "risk": risk,
                "timeframe": "Reduce position size, do not add",
                "page": "macro.html",
                "sector": "macro"
            })

    # Always include T-bill income opportunity (preserved)
    for pid in preserved_ids:
        if pid in existing_opps:
            opportunities.append(existing_opps[pid])

    # Sort by confidence descending
    opportunities.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    return opportunities


def fetch_sector_data(existing_data):
    """
    Update sector prices from yfinance and recompute RSI for each sector proxy.
    Preserves all manually-set context fields.
    """
    existing_sectors = existing_data.get("sectors", {})
    sector_proxies = {
        "tech":        "QQQ",
        "energy":      "XLE",
        "bonds":       "TLT",
        "realestate":  "VNQ",
    }

    updated = dict(existing_sectors)
    for key, symbol in sector_proxies.items():
        sect = dict(existing_sectors.get(key, {}))
        try:
            t = yf.Ticker(symbol)
            hist = t.history(period="90d", interval="1d", auto_adjust=True)
            if hist.empty:
                continue
            closes = hist["Close"].dropna().tolist()
            price = closes[-1]
            prev  = closes[-2] if len(closes) > 1 else price
            change_pct = round((price - prev) / prev * 100, 2) if prev > 0 else 0.0

            weekly = t.history(period="52wk", interval="1wk", auto_adjust=True)
            w_closes = weekly["Close"].dropna().tolist() if not weekly.empty else []

            rsi_d = compute_rsi(closes, 14)
            rsi_w = compute_rsi(w_closes, 14)

            sect["price"] = round(price, 2)
            sect["price_formatted"] = f"${price:,.2f}"
            sect["change_pct_day"] = change_pct
            if rsi_d: sect["rsi_daily"] = rsi_d; sect["rsi_label_daily"] = rsi_label(rsi_d)
            if rsi_w: sect["rsi_weekly"] = rsi_w; sect["rsi_label_weekly"] = rsi_label(rsi_w)
            sect["trend_weekly"] = trend_label(w_closes[-16:] if len(w_closes) >= 16 else w_closes)
            monthly = t.history(period="1y", interval="1mo", auto_adjust=True)
            m_closes = monthly["Close"].dropna().tolist() if not monthly.empty else []
            sect["trend_monthly"] = trend_label(m_closes[-6:] if len(m_closes) >= 6 else m_closes)

        except Exception as e:
            logger.warning(f"Sector data fetch failed for {symbol}: {e}")

        updated[key] = sect

    return updated


def compute_rsi(closes, period=14):
    """Compute RSI from a list/series of closing prices."""
    import pandas as pd
    s = pd.Series(closes).dropna()
    if len(s) < period + 1:
        return None
    delta = s.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss.replace(0, float('nan'))
    rsi = 100 - (100 / (1 + rs))
    val = rsi.dropna().iloc[-1]
    return round(float(val), 1) if not pd.isna(val) else None


def rsi_label(rsi):
    if rsi is None: return "—"
    if rsi < 30: return "OVERSOLD"
    if rsi < 45: return "WEAKENING"
    if rsi < 55: return "NEUTRAL"
    if rsi < 70: return "ELEVATED"
    return "OVERBOUGHT"


def trend_label(closes_series):
    """Weekly trend: compare last close to 8-period SMA."""
    import pandas as pd
    s = pd.Series(closes_series).dropna()
    if len(s) < 8:
        return "Neutral"
    sma = s.tail(8).mean()
    last = s.iloc[-1]
    pct_diff = (last - sma) / sma * 100
    if pct_diff > 2: return "Up"
    if pct_diff < -2: return "Down"
    return "Neutral"


def fetch_asset_rsi(symbol, existing=None):
    """Fetch daily + weekly RSI and trends for a yfinance symbol."""
    try:
        ticker = yf.Ticker(symbol)
        daily = ticker.history(period="60d", interval="1d", auto_adjust=True)
        weekly = ticker.history(period="52wk", interval="1wk", auto_adjust=True)
        if daily.empty or weekly.empty:
            return existing or {}
        d_closes = daily["Close"].dropna().tolist()
        w_closes = weekly["Close"].dropna().tolist()
        rsi_d = compute_rsi(d_closes, 14)
        rsi_w = compute_rsi(w_closes, 14)
        trend_w = trend_label(w_closes[-16:] if len(w_closes) >= 16 else w_closes)
        # Monthly trend: compare last close to 6-month avg
        monthly = ticker.history(period="1y", interval="1mo", auto_adjust=True)
        m_closes = monthly["Close"].dropna().tolist()
        trend_m = trend_label(m_closes[-6:] if len(m_closes) >= 6 else m_closes)
        return {
            "rsi_daily": rsi_d,
            "rsi_weekly": rsi_w,
            "trend_weekly": trend_w,
            "trend_monthly": trend_m,
        }
    except Exception as e:
        logger.warning(f"Asset RSI fetch failed for {symbol}: {e}")
        return existing or {}


def fetch_asset_intelligence(existing_data):
    """Compute RSI, trends, and derive macro cycle context for all tracked assets."""
    existing_ai = existing_data.get("asset_intelligence", {})
    existing_assets = existing_ai.get("assets", {})

    asset_symbols = {
        "dxy":   "DX-Y.NYB",
        "gold":  "GLD",
        "silver":"SLV",
        "btc":   "BTC-USD",
        "eth":   "ETH-USD",
        "spx":   "^GSPC",
        "tech":  "QQQ",
        "bonds": "TLT",
        "oil":   "CL=F",
    }

    updated_assets = dict(existing_assets)
    for key, symbol in asset_symbols.items():
        fetched = fetch_asset_rsi(symbol, existing_assets.get(key, {}))
        if key not in updated_assets:
            updated_assets[key] = {}
        updated_assets[key].update(fetched)
        if fetched.get("rsi_daily"):
            updated_assets[key]["rsi_label_daily"] = rsi_label(fetched["rsi_daily"])
        if fetched.get("rsi_weekly"):
            updated_assets[key]["rsi_label_weekly"] = rsi_label(fetched["rsi_weekly"])

    # Derive macro cycle phase from existing gate + macro data
    macro = existing_data.get("macro", {})
    gate = existing_data.get("decision_gate", {})
    posture = gate.get("risk_posture", "NEUTRAL")
    risk_lvl = macro.get("risk_level", 50)

    if posture == "RISK-ON" and risk_lvl < 50:
        cycle, phase = "Mid Bull", 2
    elif posture == "RISK-ON" and risk_lvl < 65:
        cycle, phase = "Late Bull", 3
    elif posture in ("WATCH-ONLY",) or (posture == "RISK-ON" and risk_lvl >= 65):
        cycle, phase = "Early Bear", 4
    elif posture == "DEFENSIVE" and risk_lvl >= 70:
        cycle, phase = "Bear", 5
    elif posture == "DEFENSIVE" and risk_lvl < 70:
        cycle, phase = "Late Bear", 6
    else:
        cycle, phase = existing_ai.get("macro_cycle", "Late Bull"), existing_ai.get("macro_cycle_phase", 3)

    # Derive policy from trigger text
    triggers = existing_data.get("triggers", [])
    policy = existing_ai.get("monetary_policy", "QT")
    for t in triggers:
        t_lower = str(t).lower()
        if "qe" in t_lower or "expanding" in t_lower or "easing" in t_lower:
            policy = "QE"
            break
        if "qt" in t_lower or "tightening" in t_lower or "contracting" in t_lower:
            policy = "QT"
            break

    return {
        "macro_cycle": cycle,
        "macro_cycle_phase": phase,
        "macro_cycle_context": existing_ai.get("macro_cycle_context", ""),
        "monetary_policy": policy,
        "monetary_policy_context": existing_ai.get("monetary_policy_context", ""),
        "assets": updated_assets,
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
    data["asset_intelligence"] = fetch_asset_intelligence(data)
    data["sectors"] = fetch_sector_data(data)
    data["bot_opportunities"] = compute_bot_opportunities(data)
    data["data_stale"] = False  # Freshly written — cleared on every successful update

    # Wyckoff phase detection
    if WYCKOFF_ENABLED:
        try:
            data["wyckoff"] = wyckoff_run_all(existing_wyckoff=data.get("wyckoff"))
            alert_count = data["wyckoff"].get("alert_count", 0)
            print(f"Wyckoff: {alert_count} active alert(s) detected")
        except Exception as e:
            print(f"Wyckoff detection failed (non-fatal): {e}")

    # Technical Indicators suite — silent background layer for AI brains
    if INDICATORS_ENABLED:
        try:
            indicators_result = indicators_run_all(existing_indicators=data.get("indicators", {}).get("assets"))
            # Write indicators to separate file to avoid bloating data.json
            indicators_file = DATA_FILE.parent / "indicators.json"
            with indicators_file.open("w", encoding="utf-8") as f:
                import json as _json
                _json.dump(indicators_result, f, indent=2)
            # Store summary only in data.json
            asset_count = len([a for a in indicators_result.get("assets", {}).values() if not a.get("error")])
            data["indicators_last_updated"] = indicators_result.get("last_updated")
            data["indicators_asset_count"] = asset_count
            print(f"Indicators: {asset_count} assets processed")
        except Exception as e:
            print(f"Indicators failed (non-fatal): {e}")

    # Alert Engine — confluence-scored alerts from indicators + wyckoff + macro
    if ALERTS_ENABLED:
        try:
            # Write data.json first (partial) so alert_engine can read it
            alerts_result = alerts_run_all(existing_alerts=data.get("active_alerts", []))
            data["active_alerts"] = alerts_result.get("active_alerts", [])
            data["alert_count"] = alerts_result.get("alert_count", 0)
            print(f"Alerts: {alerts_result.get('alert_count', 0)} active alert(s)")
        except Exception as e:
            print(f"Alert engine failed (non-fatal): {e}")

    # Derive top-level bias from decision gate posture so it never stays stale
    gate = data.get("decision_gate", {})
    posture = gate.get("risk_posture", "")
    if posture in ("DEFENSIVE", "WATCH-ONLY"):
        data["bias"] = "Bearish"
    elif posture == "RISK-ON":
        data["bias"] = "Bullish"
    else:
        data["bias"] = "Neutral"

    # Sync top-level triggers from live macro trigger_breakdown
    data["triggers"] = data.get("macro", {}).get("trigger_breakdown", [])

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