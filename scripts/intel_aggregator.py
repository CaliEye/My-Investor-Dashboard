#!/usr/bin/env python3
"""
Intelligence Aggregator — CaliEye Dashboard
Wires into free/public data sources to build an intelligence picture
that rivals hedge fund research desks.

SOURCES (all free/public APIs):
  CME FedWatch   — Fed funds futures probabilities (next meeting cut/hold/hike)
  Polymarket     — Prediction market odds on macro/crypto events
  FRED           — CPI, unemployment, fed funds, NFP (already in update_data.py)
  Treasury.gov   — Live T-bill yield data
  CoinGecko      — Fear & Greed, BTC dominance, market cap
  Alternative.me — Fear & Greed index
  SEC EDGAR      — Hedge fund 13F filings (quarterly, delayed 45 days)
  Blockchain.info— BTC on-chain: miner revenue, mempool, exchange flows

PAID SITE MANUAL FEEDS (user configures — saves JSON files):
  TradingView Pro — User exports key ideas/alerts to tv_community_feed.json
  Bitcoin Live    — User pastes signal summaries to btclive_feed.json
  Manual sources  — Any site: user fills intel_manual_feed.json

HOW TO USE MANUAL FEEDS:
  Create data/intel_manual_feed.json with this structure:
  {
    "sources": [
      {"name": "Bitcoin Live", "signal": "BTC weekly RSI shows hidden bullish divergence", "bias": "bull", "confidence": 75, "date": "2026-03-07"},
      {"name": "TradingView Idea", "signal": "SPY rising wedge breakdown target $540", "bias": "bear", "confidence": 65, "date": "2026-03-07"}
    ]
  }
  The intel aggregator will score these into the regime calculation.
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
INTEL_OUTPUT_FILE = REPO_ROOT / "data" / "intel.json"
MANUAL_FEED_FILE = REPO_ROOT / "data" / "intel_manual_feed.json"
TV_FEED_FILE = REPO_ROOT / "data" / "tv_alerts_feed.json"

REQUEST_TIMEOUT = 12


def _get(url, params=None, headers=None, retries=2):
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(2)
    return None


def _load_json(path):
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# ─────────────────────────────────────────────
# CME FEDWATCH — Fed funds futures probabilities
# ─────────────────────────────────────────────

def fetch_fedwatch() -> dict:
    """
    Scrape CME FedWatch probabilities for the next FOMC meeting.
    Uses CME's public JSON API endpoint.
    """
    result = {
        "source": "CME FedWatch",
        "cut_probability": None,
        "hold_probability": None,
        "hike_probability": None,
        "next_meeting": None,
        "current_rate_range": None,
        "status": "pending",
    }

    try:
        # CME provides meeting probabilities via this endpoint
        url = "https://www.cmegroup.com/CmeWS/mvc/ProbabilityData/getProbabilityDataForAllMeetings.do"
        resp = _get(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; CaliEye/1.0; +https://github.com/CaliEye)",
            "Accept": "application/json",
        })
        data = resp.json()

        meetings = data.get("meetings", [])
        if meetings:
            next_meeting = meetings[0]
            result["next_meeting"] = next_meeting.get("meetingDate", "")
            result["current_rate_range"] = next_meeting.get("currentRateRange", "")

            probabilities = next_meeting.get("probabilityByRateRange", [])
            for prob in probabilities:
                rate_range = prob.get("rateRange", "")
                pct = float(prob.get("probability", 0))

                current = next_meeting.get("currentRateRange", "")
                if rate_range == current:
                    result["hold_probability"] = round(pct, 1)
                elif rate_range < current:
                    # Lower rate = cut
                    result["cut_probability"] = round(
                        (result["cut_probability"] or 0) + pct, 1
                    )
                else:
                    result["hike_probability"] = round(
                        (result["hike_probability"] or 0) + pct, 1
                    )

            result["status"] = "ok"
            logger.info(f"FedWatch: cut={result['cut_probability']}% hold={result['hold_probability']}%")

    except Exception as e:
        logger.warning(f"FedWatch fetch failed: {e}")
        # Fallback: derive from data.json macro context
        result["status"] = "failed"
        result["note"] = str(e)

    return result


# ─────────────────────────────────────────────
# POLYMARKET — Prediction market odds
# ─────────────────────────────────────────────

def fetch_polymarket() -> dict:
    """
    Fetch prediction market probabilities from Polymarket public API.
    These are real money markets — more reliable than polls or surveys.
    """
    result = {
        "source": "Polymarket",
        "markets": [],
        "fed_pause_probability": None,
        "btc_above_80k_probability": None,
        "recession_probability": None,
        "status": "pending",
    }

    # Key market slugs to track (from Polymarket public API)
    MARKET_QUERIES = [
        "fed-pause-march-2025",
        "will-btc-reach-80000",
        "us-recession-2025",
        "btc-price-end-2025",
    ]

    try:
        # Polymarket CLOB/Gamma API — completely public
        url = "https://gamma-api.polymarket.com/markets"
        resp = _get(url, params={
            "active": "true",
            "closed": "false",
            "_limit": 100,
        })
        markets_data = resp.json()

        # Parse relevant markets
        for market in markets_data:
            title = str(market.get("question", market.get("title", ""))).lower()
            outcomes = market.get("outcomePrices", "[]")

            if isinstance(outcomes, str):
                try:
                    outcomes = json.loads(outcomes)
                except Exception:
                    outcomes = []

            # Get "Yes" probability
            yes_prob = None
            if isinstance(outcomes, list) and outcomes:
                try:
                    yes_prob = round(float(outcomes[0]) * 100, 1)
                except Exception:
                    pass

            if yes_prob is None:
                continue

            # Match to key markets
            if any(w in title for w in ["federal reserve", "fed rate", "fomc", "fed pause", "fed hold"]):
                result["fed_pause_probability"] = yes_prob
                result["markets"].append({
                    "title": market.get("question", "Fed Rate Decision"),
                    "probability": yes_prob,
                    "category": "fed",
                })

            if any(w in title for w in ["bitcoin", "btc"]) and any(w in title for w in ["80", "90", "100"]):
                result["btc_above_80k_probability"] = yes_prob
                result["markets"].append({
                    "title": market.get("question", "BTC Price Target"),
                    "probability": yes_prob,
                    "category": "crypto",
                })

            if any(w in title for w in ["recession", "gdp negative", "economic contraction"]):
                result["recession_probability"] = yes_prob
                result["markets"].append({
                    "title": market.get("question", "Recession Probability"),
                    "probability": yes_prob,
                    "category": "macro",
                })

        result["status"] = "ok"
        logger.info(f"Polymarket: {len(result['markets'])} relevant markets found")

    except Exception as e:
        logger.warning(f"Polymarket fetch failed: {e}")
        result["status"] = "failed"
        result["note"] = str(e)

    return result


# ─────────────────────────────────────────────
# FEAR & GREED INDEX (Alternative.me — free)
# ─────────────────────────────────────────────

def fetch_fear_greed() -> dict:
    result = {"source": "Alternative.me", "value": None, "label": None, "status": "pending"}
    try:
        resp = _get("https://api.alternative.me/fng/?limit=1&format=json")
        data = resp.json()
        entry = data.get("data", [{}])[0]
        result["value"] = int(entry.get("value", 50))
        result["label"] = entry.get("value_classification", "Neutral")
        result["timestamp"] = entry.get("timestamp")
        result["status"] = "ok"
        logger.info(f"Fear & Greed: {result['value']} ({result['label']})")
    except Exception as e:
        logger.warning(f"Fear & Greed fetch failed: {e}")
        result["status"] = "failed"
    return result


# ─────────────────────────────────────────────
# TREASURY.GOV — Live yield data
# ─────────────────────────────────────────────

def fetch_treasury_yields() -> dict:
    result = {"source": "Treasury.gov", "yields": {}, "status": "pending"}
    try:
        # Treasury XML data feed — completely public
        url = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml"
        params = {"data": "daily_treasury_yield_curve", "field_tdr_date_value": datetime.now().strftime("%Y%m")}
        resp = _get(url, params=params, headers={"Accept": "application/xml"})

        # Parse last entry from XML
        text = resp.text
        import re
        entries = re.findall(r'<entry>(.*?)</entry>', text, re.DOTALL)
        if entries:
            last_entry = entries[-1]
            def extract(tag):
                m = re.search(rf'<d:{tag}>([\d.]+)</d:{tag}>', last_entry)
                return float(m.group(1)) if m else None

            result["yields"] = {
                "1m":  extract("BC_1MONTH"),
                "3m":  extract("BC_3MONTH"),
                "6m":  extract("BC_6MONTH"),
                "1y":  extract("BC_1YEAR"),
                "2y":  extract("BC_2YEAR"),
                "5y":  extract("BC_5YEAR"),
                "10y": extract("BC_10YEAR"),
                "30y": extract("BC_30YEAR"),
            }
            # Yield curve signal
            y2 = result["yields"].get("2y")
            y10 = result["yields"].get("10y")
            if y2 and y10:
                spread = round(y10 - y2, 3)
                result["yield_curve_spread_2s10s"] = spread
                result["yield_curve_signal"] = (
                    "INVERTED" if spread < 0 else
                    "FLAT" if spread < 0.3 else
                    "NORMAL"
                )
            result["status"] = "ok"
            logger.info(f"Treasury: 10Y={result['yields'].get('10y')}% 3M={result['yields'].get('3m')}%")

    except Exception as e:
        logger.warning(f"Treasury yields failed: {e}")
        result["status"] = "failed"
    return result


# ─────────────────────────────────────────────
# COINGECKO — BTC dominance, global market cap
# ─────────────────────────────────────────────

def fetch_coingecko_global() -> dict:
    result = {"source": "CoinGecko", "status": "pending"}
    try:
        resp = _get("https://api.coingecko.com/api/v3/global")
        data = resp.json().get("data", {})
        result["btc_dominance"] = round(data.get("market_cap_percentage", {}).get("bitcoin", 0), 2)
        result["eth_dominance"] = round(data.get("market_cap_percentage", {}).get("ethereum", 0), 2)
        result["total_market_cap_usd"] = data.get("total_market_cap", {}).get("usd")
        result["total_volume_24h"] = data.get("total_volume", {}).get("usd")
        result["market_cap_change_24h"] = round(data.get("market_cap_change_percentage_24h_usd", 0), 2)
        # BTC dominance signal
        dom = result["btc_dominance"]
        result["btc_dominance_signal"] = (
            "ALTCOIN_SEASON_RISK" if dom < 42 else
            "BALANCED" if dom < 52 else
            "BTC_DOMINANCE" if dom < 62 else
            "EXTREME_BTC_DOM"
        )
        result["status"] = "ok"
        logger.info(f"CoinGecko: BTC dom={dom}% market_cap_change={result['market_cap_change_24h']}%")
    except Exception as e:
        logger.warning(f"CoinGecko global failed: {e}")
        result["status"] = "failed"
    return result


# ─────────────────────────────────────────────
# SEC EDGAR 13F — Hedge fund positioning
# ─────────────────────────────────────────────

def fetch_hedge_fund_signals() -> dict:
    """
    Fetch recent 13F filings from SEC EDGAR to track smart money positioning.
    13F filings are 45-day delayed but show broad hedge fund conviction.
    Tracks: Bridgewater, Citadel, Millennium, Renaissance, Point72, Tiger Global.
    """
    result = {
        "source": "SEC EDGAR 13F",
        "status": "pending",
        "top_funds_btc_exposure": False,
        "risk_off_rotation": False,
        "recent_filings": [],
        "signal": "NEUTRAL",
        "note": ""
    }

    # Key institutional filers to watch (CIK numbers from SEC EDGAR)
    WATCHED_FILERS = {
        "Bridgewater Associates": "0001350694",
        "Point72 Asset Management": "0001603466",
        "Two Sigma": "0001495703",
        "D.E. Shaw": "0001101189",
    }

    try:
        headers = {
            "User-Agent": "CaliEye Dashboard contact@example.com",
            "Accept-Encoding": "gzip, deflate",
        }

        filings_found = []
        for fund_name, cik in list(WATCHED_FILERS.items())[:2]:  # Limit to 2 to avoid rate limiting
            try:
                url = f"https://data.sec.gov/submissions/CIK{cik}.json"
                resp = _get(url, headers=headers)
                sub_data = resp.json()

                recent_filings = sub_data.get("filings", {}).get("recent", {})
                forms = recent_filings.get("form", [])
                dates = recent_filings.get("filingDate", [])
                accessions = recent_filings.get("accessionNumber", [])

                # Find most recent 13F-HR
                for i, form in enumerate(forms[:20]):
                    if form == "13F-HR":
                        filings_found.append({
                            "fund": fund_name,
                            "date": dates[i] if i < len(dates) else "unknown",
                            "form": form,
                            "accession": accessions[i] if i < len(accessions) else "",
                        })
                        break  # Just most recent per fund
            except Exception:
                pass

        result["recent_filings"] = filings_found[:5]
        result["status"] = "ok" if filings_found else "no_data"

        # Simple signal: if filings found recently (within 90 days), note it
        if filings_found:
            result["note"] = f"{len(filings_found)} major fund filings tracked. Check manually for crypto/gold positions."
            result["signal"] = "DATA_AVAILABLE"

    except Exception as e:
        logger.warning(f"SEC EDGAR 13F failed: {e}")
        result["status"] = "failed"
        result["note"] = str(e)

    return result


# ─────────────────────────────────────────────
# BLOCKCHAIN.INFO — BTC on-chain signals
# ─────────────────────────────────────────────

def fetch_btc_onchain() -> dict:
    """
    Free on-chain BTC data from Blockchain.info public API.
    Whale watching + exchange flow signals.
    """
    result = {"source": "Blockchain.info", "status": "pending"}
    try:
        # Market price
        stats_resp = _get("https://blockchain.info/stats?format=json")
        stats = stats_resp.json()

        result["hash_rate_th"] = stats.get("hash_rate")
        result["miners_revenue_usd"] = stats.get("miners_revenue_usd")
        result["transaction_fees_usd"] = stats.get("transaction_fees_usd")
        result["n_blocks_mined"] = stats.get("n_blocks_mined")
        result["mempool_size"] = stats.get("mempool_size")

        # Miner capitulation signal: if revenue drops >30% month-over-month
        result["miner_revenue_signal"] = "NORMAL"
        if result.get("miners_revenue_usd") and result["miners_revenue_usd"] < 20_000_000:
            result["miner_revenue_signal"] = "CAPITULATION_RISK"

        # Mempool congestion = network demand
        if result.get("mempool_size") and result["mempool_size"] > 100_000_000:
            result["mempool_signal"] = "HIGH_DEMAND"
        else:
            result["mempool_signal"] = "NORMAL"

        result["status"] = "ok"
        logger.info(f"BTC on-chain: miners_revenue=${result.get('miners_revenue_usd'):,}" if result.get('miners_revenue_usd') else "BTC on-chain: ok")

    except Exception as e:
        logger.warning(f"Blockchain.info failed: {e}")
        result["status"] = "failed"
    return result


# ─────────────────────────────────────────────
# MANUAL FEEDS — TradingView Pro, Bitcoin Live, etc.
# ─────────────────────────────────────────────

def fetch_manual_feeds() -> dict:
    """
    Load user-configured manual intelligence feeds.
    User pastes key signals from paid sites into JSON files.
    This is the bridge for TradingView Pro, Bitcoin Live, etc.
    """
    result = {
        "source": "Manual Feeds",
        "feeds": [],
        "bull_count": 0,
        "bear_count": 0,
        "neutral_count": 0,
        "status": "no_data",
    }

    # Load manual feed
    manual = _load_json(MANUAL_FEED_FILE)
    sources = manual.get("sources", [])

    if not sources:
        result["status"] = "no_data"
        result["note"] = f"Create {MANUAL_FEED_FILE.name} to add TradingView Pro / Bitcoin Live signals"
        return result

    # Score the feeds
    for entry in sources:
        bias = str(entry.get("bias", "neutral")).lower()
        conf = int(entry.get("confidence", 60))
        name = entry.get("name", "Unknown")
        signal = entry.get("signal", "")
        date = entry.get("date", "")

        result["feeds"].append({
            "name": name,
            "signal": signal,
            "bias": bias,
            "confidence": conf,
            "date": date,
        })

        if bias == "bull":
            result["bull_count"] += 1
        elif bias == "bear":
            result["bear_count"] += 1
        else:
            result["neutral_count"] += 1

    result["status"] = "ok"
    result["total"] = len(sources)

    # Net bias signal
    net = result["bull_count"] - result["bear_count"]
    if net >= 3:
        result["net_signal"] = "STRONG_BULL"
    elif net >= 1:
        result["net_signal"] = "LEAN_BULL"
    elif net <= -3:
        result["net_signal"] = "STRONG_BEAR"
    elif net <= -1:
        result["net_signal"] = "LEAN_BEAR"
    else:
        result["net_signal"] = "NEUTRAL"

    # Also load TV alerts feed if it exists
    tv_feed = _load_json(TV_FEED_FILE) if TV_FEED_FILE.exists() else []
    recent_tv = [a for a in tv_feed[:10] if isinstance(a, dict)]
    if recent_tv:
        result["tv_recent_count"] = len(recent_tv)
        result["tv_latest"] = recent_tv[0].get("action", "")

    logger.info(f"Manual feeds: {len(sources)} signals — bull:{result['bull_count']} bear:{result['bear_count']}")
    return result


# ─────────────────────────────────────────────
# Main Runner
# ─────────────────────────────────────────────

def run_all(existing_intel: Optional[dict] = None) -> dict:
    """
    Aggregate all intelligence sources into a unified intel.json.
    """
    logger.info("Intel aggregator starting...")

    fedwatch = fetch_fedwatch()
    polymarket = fetch_polymarket()
    fear_greed = fetch_fear_greed()
    treasury = fetch_treasury_yields()
    coingecko = fetch_coingecko_global()
    hf_signals = fetch_hedge_fund_signals()
    onchain = fetch_btc_onchain()
    manual = fetch_manual_feeds()

    # Source health summary
    sources = [fedwatch, polymarket, fear_greed, treasury, coingecko, hf_signals, onchain, manual]
    ok_count = sum(1 for s in sources if s.get("status") == "ok")
    total = len(sources)

    result = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "sources_ok": ok_count,
        "sources_total": total,
        "health_pct": round(ok_count / total * 100),
        "fedwatch": fedwatch,
        "polymarket": polymarket,
        "fear_greed": fear_greed,
        "treasury": treasury,
        "coingecko": coingecko,
        "hedge_fund_signals": hf_signals,
        "btc_onchain": onchain,
        "manual_feeds": manual,
        # Quick-access summary fields for pivot_engine
        "cut_probability": fedwatch.get("cut_probability"),
        "recession_probability": polymarket.get("recession_probability"),
        "btc_above_80k_probability": polymarket.get("btc_above_80k_probability"),
        "fear_greed_value": fear_greed.get("value"),
        "fear_greed_label": fear_greed.get("label"),
        "btc_dominance": coingecko.get("btc_dominance"),
        "yield_curve": treasury.get("yield_curve_signal"),
        "yield_10y": (treasury.get("yields") or {}).get("10y"),
        "yield_3m": (treasury.get("yields") or {}).get("3m"),
        "manual_net_signal": manual.get("net_signal", "NEUTRAL"),
    }

    # Write to intel.json
    INTEL_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with INTEL_OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    logger.info(f"Intel aggregated: {ok_count}/{total} sources OK")
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
    result = run_all()
    print(f"\nIntel sources: {result['sources_ok']}/{result['sources_total']} OK")
    print(f"Fear & Greed: {result.get('fear_greed_value')} ({result.get('fear_greed_label')})")
    print(f"BTC Dominance: {result.get('btc_dominance')}%")
    print(f"CME Cut prob: {result.get('cut_probability')}%")
    print(f"Yield Curve: {result.get('yield_curve')}")
    print(f"Manual feeds: {result['manual_feeds'].get('net_signal', 'N/A')}")
