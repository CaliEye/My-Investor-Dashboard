#!/usr/bin/env python3
"""
Technical Indicators Engine — CaliEye Dashboard
Silent background processing layer. AI brains read this data to detect
signals, early pattern shifts, and setups 24/7.

Calculates per-asset:
  RSI (14), MACD (12/26/9), Bollinger Bands (20,2), SMA/EMA (9/20/50/200),
  Stochastic (14,3), Ichimoku (simplified), Fibonacci retracements,
  On-Balance Volume (OBV), Volume Profile (relative), ATR, Williams %R,
  CCI, Wyckoff scoring metrics, Bear/Bull phase probability
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yfinance as yf

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent

# Assets to analyze — mapped to yfinance symbols
INDICATOR_ASSETS = {
    "btc":     {"symbol": "BTC-USD",  "label": "Bitcoin",       "category": "crypto"},
    "eth":     {"symbol": "ETH-USD",  "label": "Ethereum",      "category": "crypto"},
    "gold":    {"symbol": "GLD",      "label": "Gold / GLD",    "category": "metals"},
    "silver":  {"symbol": "SLV",      "label": "Silver / SLV",  "category": "metals"},
    "spx":     {"symbol": "SPY",      "label": "S&P 500 / SPY", "category": "macro"},
    "qqq":     {"symbol": "QQQ",      "label": "Nasdaq / QQQ",  "category": "tech"},
    "tlt":     {"symbol": "TLT",      "label": "Bonds / TLT",   "category": "bonds"},
    "dxy":     {"symbol": "DX-Y.NYB", "label": "USD / DXY",     "category": "macro"},
    "oil":     {"symbol": "USO",      "label": "Oil / USO",     "category": "energy"},
    "ita":     {"symbol": "ITA",      "label": "Defense / ITA", "category": "defense"},
    "lmt":     {"symbol": "LMT",      "label": "Lockheed LMT",  "category": "defense"},
    "rtx":     {"symbol": "RTX",      "label": "Raytheon RTX",  "category": "defense"},
    "noc":     {"symbol": "NOC",      "label": "Northrop NOC",  "category": "defense"},
    "gdx":     {"symbol": "GDX",      "label": "Gold Miners GDX","category": "metals"},
    "remx":    {"symbol": "REMX",     "label": "Rare Earth REMX","category": "metals"},
}


def _rsi(closes, period=14):
    """Wilder's RSI"""
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def _ema(closes, period):
    """Exponential Moving Average"""
    if len(closes) < period:
        return None
    k = 2 / (period + 1)
    ema = sum(closes[:period]) / period
    for price in closes[period:]:
        ema = price * k + ema * (1 - k)
    return round(ema, 4)


def _sma(closes, period):
    if len(closes) < period:
        return None
    return round(sum(closes[-period:]) / period, 4)


def _macd(closes):
    """MACD (12,26,9) — returns macd_line, signal_line, histogram"""
    if len(closes) < 35:
        return None, None, None
    k12 = 2 / 13
    k26 = 2 / 27
    k9 = 2 / 10

    ema12 = sum(closes[:12]) / 12
    ema26 = sum(closes[:26]) / 26

    for price in closes[12:]:
        ema12 = price * k12 + ema12 * (1 - k12)
    for price in closes[26:]:
        ema26 = price * k26 + ema26 * (1 - k26)

    macd_line = ema12 - ema26

    # Signal line from last 9 MACD values (simplified)
    macd_values = []
    e12 = sum(closes[:12]) / 12
    e26 = sum(closes[:26]) / 26
    for price in closes[26:]:
        e12 = price * k12 + e12 * (1 - k12)
        e26 = price * k26 + e26 * (1 - k26)
        macd_values.append(e12 - e26)

    if len(macd_values) < 9:
        return round(macd_line, 6), None, None

    signal = sum(macd_values[-9:]) / 9
    for m in macd_values[-8:]:
        signal = m * k9 + signal * (1 - k9)

    histogram = macd_line - signal
    return round(macd_line, 6), round(signal, 6), round(histogram, 6)


def _bollinger_bands(closes, period=20, std_mult=2):
    """Bollinger Bands — returns upper, middle, lower, %B, bandwidth"""
    if len(closes) < period:
        return None, None, None, None, None

    recent = closes[-period:]
    sma = sum(recent) / period
    variance = sum((p - sma) ** 2 for p in recent) / period
    std = variance ** 0.5

    upper = sma + std_mult * std
    lower = sma - std_mult * std
    price = closes[-1]

    pct_b = (price - lower) / (upper - lower) if upper != lower else 0.5
    bandwidth = (upper - lower) / sma if sma != 0 else 0

    return round(upper, 4), round(sma, 4), round(lower, 4), round(pct_b, 4), round(bandwidth, 4)


def _stochastic(closes, highs, lows, k_period=14, d_period=3):
    """Stochastic Oscillator %K and %D"""
    if len(closes) < k_period:
        return None, None

    low_min = min(lows[-k_period:])
    high_max = max(highs[-k_period:])

    if high_max == low_min:
        k = 50.0
    else:
        k = 100 * (closes[-1] - low_min) / (high_max - low_min)

    if len(closes) >= k_period + d_period:
        k_values = []
        for i in range(d_period):
            idx = -(d_period - i)
            lo = min(lows[idx - k_period:idx if idx != 0 else None])
            hi = max(highs[idx - k_period:idx if idx != 0 else None])
            if hi == lo:
                k_values.append(50.0)
            else:
                k_values.append(100 * (closes[idx] - lo) / (hi - lo))
        d = sum(k_values) / d_period
    else:
        d = k

    return round(k, 2), round(d, 2)


def _atr(highs, lows, closes, period=14):
    """Average True Range"""
    if len(closes) < period + 1:
        return None

    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
        trs.append(tr)

    if len(trs) < period:
        return None

    atr = sum(trs[-period:]) / period
    return round(atr, 4)


def _williams_r(closes, highs, lows, period=14):
    """Williams %R"""
    if len(closes) < period:
        return None
    highest_high = max(highs[-period:])
    lowest_low = min(lows[-period:])
    if highest_high == lowest_low:
        return -50.0
    wr = -100 * (highest_high - closes[-1]) / (highest_high - lowest_low)
    return round(wr, 2)


def _cci(closes, highs, lows, period=20):
    """Commodity Channel Index"""
    if len(closes) < period:
        return None

    typical = [(highs[i] + lows[i] + closes[i]) / 3 for i in range(len(closes))]
    tp_slice = typical[-period:]
    tp_sma = sum(tp_slice) / period
    mean_dev = sum(abs(tp - tp_sma) for tp in tp_slice) / period

    if mean_dev == 0:
        return 0.0
    return round((typical[-1] - tp_sma) / (0.015 * mean_dev), 2)


def _obv(closes, volumes):
    """On-Balance Volume — returns current OBV and 20-period OBV SMA"""
    if len(closes) < 2:
        return None, None

    obv = 0
    obv_series = [0]
    for i in range(1, len(closes)):
        if closes[i] > closes[i-1]:
            obv += volumes[i]
        elif closes[i] < closes[i-1]:
            obv -= volumes[i]
        obv_series.append(obv)

    obv_sma = sum(obv_series[-20:]) / min(20, len(obv_series))
    trend = "RISING" if obv > obv_sma else "FALLING"
    return obv, trend


def _fibonacci_levels(closes, highs, lows, lookback=60):
    """Fibonacci retracement levels from recent swing high/low"""
    if len(closes) < lookback:
        lookback = len(closes)

    swing_high = max(highs[-lookback:])
    swing_low = min(lows[-lookback:])
    diff = swing_high - swing_low

    price = closes[-1]
    levels = {
        "0.0":   round(swing_low, 4),
        "0.236": round(swing_low + diff * 0.236, 4),
        "0.382": round(swing_low + diff * 0.382, 4),
        "0.5":   round(swing_low + diff * 0.5, 4),
        "0.618": round(swing_low + diff * 0.618, 4),
        "0.786": round(swing_low + diff * 0.786, 4),
        "1.0":   round(swing_high, 4),
    }

    # Find nearest levels
    level_values = sorted(levels.values())
    nearest_support = max((v for v in level_values if v <= price), default=None)
    nearest_resistance = min((v for v in level_values if v >= price), default=None)

    return {
        "swing_high": round(swing_high, 4),
        "swing_low": round(swing_low, 4),
        "levels": levels,
        "nearest_support": nearest_support,
        "nearest_resistance": nearest_resistance,
        "price_vs_range_pct": round((price - swing_low) / diff * 100, 1) if diff > 0 else 50.0,
    }


def _ichimoku_simplified(closes, highs, lows):
    """
    Simplified Ichimoku — Tenkan-sen (9), Kijun-sen (26), Senkou Span A+B
    Returns cloud position signal only (price above/below/in cloud)
    """
    if len(closes) < 52:
        return {"signal": "INSUFFICIENT_DATA", "above_cloud": None}

    tenkan = (max(highs[-9:]) + min(lows[-9:])) / 2
    kijun = (max(highs[-26:]) + min(lows[-26:])) / 2

    # Senkou Span A (midpoint of tenkan + kijun, plotted 26 ahead)
    span_a = (tenkan + kijun) / 2
    # Senkou Span B (52-period midpoint, plotted 26 ahead)
    span_b = (max(highs[-52:]) + min(lows[-52:])) / 2

    cloud_top = max(span_a, span_b)
    cloud_bottom = min(span_a, span_b)
    price = closes[-1]

    if price > cloud_top:
        signal = "ABOVE_CLOUD"  # Bullish
    elif price < cloud_bottom:
        signal = "BELOW_CLOUD"  # Bearish
    else:
        signal = "IN_CLOUD"  # Transitioning / uncertain

    return {
        "signal": signal,
        "tenkan": round(tenkan, 4),
        "kijun": round(kijun, 4),
        "span_a": round(span_a, 4),
        "span_b": round(span_b, 4),
        "cloud_top": round(cloud_top, 4),
        "cloud_bottom": round(cloud_bottom, 4),
        "above_cloud": price > cloud_top,
        "tk_cross": "BULLISH" if tenkan > kijun else "BEARISH",
    }


def _volume_profile(volumes, closes, period=20):
    """Volume vs moving average — simple relative volume scoring"""
    if len(volumes) < period:
        return None

    avg_vol = sum(volumes[-period:]) / period
    current_vol = volumes[-1]
    ratio = current_vol / avg_vol if avg_vol > 0 else 1.0

    if ratio > 2.0:
        label = "SURGE"
    elif ratio > 1.5:
        label = "HIGH"
    elif ratio > 0.8:
        label = "NORMAL"
    elif ratio > 0.5:
        label = "LOW"
    else:
        label = "VERY_LOW"

    return {"ratio": round(ratio, 2), "label": label, "avg_20d": round(avg_vol, 0)}


def _trend_classification(closes, sma20, sma50, sma200, rsi):
    """Multi-timeframe trend classification"""
    price = closes[-1]
    signals = []

    if sma20 and price > sma20:
        signals.append("above_20")
    if sma50 and price > sma50:
        signals.append("above_50")
    if sma200 and price > sma200:
        signals.append("above_200")
    if sma20 and sma50 and sma20 > sma50:
        signals.append("sma_bullish_stack")
    if rsi and rsi > 50:
        signals.append("rsi_bull_zone")

    bull_count = len(signals)
    if bull_count >= 4:
        return "STRONG_UPTREND"
    elif bull_count >= 3:
        return "UPTREND"
    elif bull_count == 2:
        return "NEUTRAL_LEAN_BULL"
    elif bull_count == 1:
        return "NEUTRAL_LEAN_BEAR"
    else:
        return "DOWNTREND"


def _momentum_score(rsi, macd_hist, stoch_k, pct_b, cci):
    """Composite momentum score -100 to +100"""
    score = 0
    count = 0

    if rsi is not None:
        score += (rsi - 50) * 1.2  # -60 to +60 range
        count += 1

    if macd_hist is not None:
        normalized = max(-1, min(1, macd_hist / (abs(macd_hist) + 0.001) * 15))
        score += normalized * 15
        count += 1

    if stoch_k is not None:
        score += (stoch_k - 50) * 0.6
        count += 1

    if pct_b is not None:
        score += (pct_b - 0.5) * 40
        count += 1

    if cci is not None:
        clamped = max(-200, min(200, cci))
        score += clamped * 0.1
        count += 1

    if count == 0:
        return 0

    raw = score / count
    return round(max(-100, min(100, raw)), 1)


def calculate_indicators(key: str, existing_result: Optional[dict] = None) -> dict:
    """
    Fetch OHLCV data and compute full indicator suite for one asset.
    Returns structured dict of all indicators.
    Falls back to existing_result on error.
    """
    meta = INDICATOR_ASSETS.get(key)
    if not meta:
        return {"error": f"Unknown asset: {key}"}

    symbol = meta["symbol"]

    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="6mo", interval="1d")

        if hist.empty or len(hist) < 30:
            logger.warning(f"Insufficient data for {symbol}: {len(hist)} rows")
            return existing_result or {"error": "insufficient_data", "symbol": symbol}

        closes = hist["Close"].tolist()
        highs = hist["High"].tolist()
        lows = hist["Low"].tolist()
        volumes = hist["Volume"].tolist()
        price = closes[-1]

        # Core indicators
        rsi_14 = _rsi(closes, 14)
        rsi_7 = _rsi(closes, 7)
        macd_line, macd_signal, macd_hist = _macd(closes)
        bb_upper, bb_mid, bb_lower, pct_b, bb_width = _bollinger_bands(closes)
        sma20 = _sma(closes, 20)
        sma50 = _sma(closes, 50)
        sma200 = _sma(closes, 200)
        ema9 = _ema(closes, 9)
        ema20 = _ema(closes, 20)
        ema50 = _ema(closes, 50)
        stoch_k, stoch_d = _stochastic(closes, highs, lows)
        atr_14 = _atr(highs, lows, closes, 14)
        williams_r = _williams_r(closes, highs, lows)
        cci_20 = _cci(closes, highs, lows)
        obv_current, obv_trend = _obv(closes, volumes)
        fib = _fibonacci_levels(closes, highs, lows)
        ichimoku = _ichimoku_simplified(closes, highs, lows)
        vol_profile = _volume_profile(volumes, closes)
        trend = _trend_classification(closes, sma20, sma50, sma200, rsi_14)
        momentum = _momentum_score(rsi_14, macd_hist, stoch_k, pct_b, cci_20)

        # Price change metrics
        change_1d = round((closes[-1] / closes[-2] - 1) * 100, 2) if len(closes) >= 2 else 0
        change_5d = round((closes[-1] / closes[-6] - 1) * 100, 2) if len(closes) >= 6 else 0
        change_20d = round((closes[-1] / closes[-21] - 1) * 100, 2) if len(closes) >= 21 else 0

        # Volatility (20-day)
        if len(closes) >= 20:
            returns = [(closes[i] / closes[i-1] - 1) for i in range(max(1, len(closes)-20), len(closes))]
            avg_ret = sum(returns) / len(returns)
            variance = sum((r - avg_ret) ** 2 for r in returns) / len(returns)
            volatility_20d = round((variance ** 0.5) * (252 ** 0.5) * 100, 2)
        else:
            volatility_20d = None

        # ATR as % of price (normalized volatility)
        atr_pct = round(atr_14 / price * 100, 2) if atr_14 and price else None

        return {
            "symbol": symbol,
            "label": meta["label"],
            "category": meta["category"],
            "price": round(price, 4),
            "price_formatted": f"${price:,.2f}",
            "change_1d": change_1d,
            "change_5d": change_5d,
            "change_20d": change_20d,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            # RSI
            "rsi_14": rsi_14,
            "rsi_7": rsi_7,
            "rsi_label": (
                "OVERSOLD" if rsi_14 and rsi_14 < 30 else
                "OVERBOUGHT" if rsi_14 and rsi_14 > 70 else
                "NEUTRAL" if rsi_14 and 40 <= rsi_14 <= 60 else
                "WEAKENING" if rsi_14 and rsi_14 < 40 else
                "ELEVATED" if rsi_14 else "UNKNOWN"
            ),
            # MACD
            "macd_line": macd_line,
            "macd_signal": macd_signal,
            "macd_hist": macd_hist,
            "macd_cross": (
                "BULLISH" if macd_hist and macd_hist > 0 else
                "BEARISH" if macd_hist and macd_hist < 0 else
                "NEUTRAL"
            ),
            # Bollinger Bands
            "bb_upper": bb_upper,
            "bb_mid": bb_mid,
            "bb_lower": bb_lower,
            "bb_pct_b": pct_b,
            "bb_width": bb_width,
            "bb_squeeze": bb_width is not None and bb_width < 0.05,
            # Moving Averages
            "sma_20": sma20,
            "sma_50": sma50,
            "sma_200": sma200,
            "ema_9": ema9,
            "ema_20": ema20,
            "ema_50": ema50,
            "price_vs_sma200": round((price / sma200 - 1) * 100, 2) if sma200 else None,
            "golden_cross": bool(sma50 and sma200 and sma50 > sma200),
            "death_cross": bool(sma50 and sma200 and sma50 < sma200),
            # Stochastic
            "stoch_k": stoch_k,
            "stoch_d": stoch_d,
            "stoch_label": (
                "OVERSOLD" if stoch_k and stoch_k < 20 else
                "OVERBOUGHT" if stoch_k and stoch_k > 80 else
                "NEUTRAL"
            ),
            # ATR & Volatility
            "atr_14": atr_14,
            "atr_pct": atr_pct,
            "volatility_20d": volatility_20d,
            # Williams %R
            "williams_r": williams_r,
            "williams_label": (
                "OVERSOLD" if williams_r and williams_r < -80 else
                "OVERBOUGHT" if williams_r and williams_r > -20 else
                "NEUTRAL"
            ),
            # CCI
            "cci": cci_20,
            "cci_label": (
                "OVERSOLD" if cci_20 and cci_20 < -100 else
                "OVERBOUGHT" if cci_20 and cci_20 > 100 else
                "NEUTRAL"
            ),
            # OBV
            "obv_trend": obv_trend,
            # Fibonacci
            "fibonacci": fib,
            # Ichimoku
            "ichimoku": ichimoku,
            # Volume
            "volume_profile": vol_profile,
            # Trend & Momentum
            "trend": trend,
            "momentum_score": momentum,
            "momentum_label": (
                "STRONG_BULL" if momentum > 60 else
                "BULL" if momentum > 20 else
                "NEUTRAL" if -20 <= momentum <= 20 else
                "BEAR" if momentum > -60 else
                "STRONG_BEAR"
            ),
        }

    except Exception as e:
        logger.error(f"Indicator calculation failed for {symbol}: {e}")
        return existing_result or {
            "symbol": symbol,
            "label": meta["label"],
            "error": str(e),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }


def run_all(existing_indicators: Optional[dict] = None) -> dict:
    """
    Calculate indicators for all tracked assets.
    Returns full indicators dict to be stored in data.json under 'indicators' key.
    """
    existing = existing_indicators or {}
    results = {}

    for key in INDICATOR_ASSETS:
        result = calculate_indicators(key, existing_result=existing.get(key))
        results[key] = result
        if not result.get("error"):
            label = result.get("rsi_label", "?")
            momentum = result.get("momentum_score", 0)
            logger.info(f"  {key}: RSI={result.get('rsi_14','?')} ({label}) momentum={momentum}")

    return {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "assets": results,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print("Running technical indicator suite...")
    result = run_all()
    output_file = REPO_ROOT / "data" / "indicators.json"
    output_file.parent.mkdir(exist_ok=True)
    with output_file.open("w") as f:
        json.dump(result, f, indent=2)
    print(f"Indicators written to {output_file}")
    print(f"Assets processed: {len(result['assets'])}")
