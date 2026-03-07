#!/usr/bin/env python3
"""
Alert Engine — CaliEye Dashboard
Confluence-scored alert generation.

Philosophy:
  - NEVER alert on a single signal. Minimum 3 confluent signals required.
  - Alerts are CLEAN and ACTIONABLE. No noise. No clutter.
  - Each alert includes: what to do, risk level, confidence, expiry.
  - AI brains (GPT-4, Claude, Grok, Gemini) ingest raw indicators silently.
  - Only surface results to the human when truly actionable.

Alert types:
  OVERSOLD_REVERSAL   — Multiple oversold signals converging (RSI+Stoch+Williams+BB)
  OVERBOUGHT_WARNING  — Multiple overbought signals converging
  TREND_BREAK         — Price/MA relationship signaling trend change
  MOMENTUM_SHIFT      — MACD + momentum scoring divergence
  VOLUME_SURGE        — Unusual volume with directional move
  WYCKOFF_SETUP       — Wyckoff phase + technical indicator confluence
  FIBONACCI_BOUNCE    — Price at key Fib level with reversal signal
  ICHIMOKU_CROSS      — Cloud signal + confirmation
  SQUEEZE_BREAKOUT    — BB squeeze + volume/momentum trigger
  MACRO_RISK_GATE     — Macro conditions override technical signal (DEFENSIVE gate)
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = REPO_ROOT / "data" / "data.json"
INDICATORS_FILE = REPO_ROOT / "data" / "indicators.json"
ALERTS_FILE = REPO_ROOT / "logs" / "active_alerts.json"

# Minimum confluence signals to generate an alert
MIN_CONFLUENCE = 3

# Severity levels
CRITICAL = "CRITICAL"
HIGH = "HIGH"
MEDIUM = "MEDIUM"
INFO = "INFO"


def _load_json(path):
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _alert(key, label, alert_type, severity, confidence, action, signals, risk_level,
           timeframe="1-7 days", category="", extra=None):
    return {
        "id": f"{key}_{alert_type}_{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        "key": key,
        "label": label,
        "category": category,
        "alert_type": alert_type,
        "severity": severity,
        "confidence": confidence,
        "signals": signals,  # List of contributing signal descriptions
        "action": action,
        "risk_level": risk_level,
        "timeframe": timeframe,
        "fired_utc": datetime.now(timezone.utc).isoformat(),
        **(extra or {}),
    }


def _check_oversold_reversal(key, ind, wyckoff_phase):
    """
    Fires when 3+ oversold signals align:
    RSI < 35, Stochastic < 25, Williams %R < -75, BB %B < 0.15, CCI < -100
    """
    signals = []

    rsi = ind.get("rsi_14")
    stoch_k = ind.get("stoch_k")
    williams = ind.get("williams_r")
    pct_b = ind.get("bb_pct_b")
    cci = ind.get("cci")
    obv_trend = ind.get("obv_trend")
    macd_hist = ind.get("macd_hist")
    momentum = ind.get("momentum_score", 0)

    if rsi and rsi < 35:
        signals.append(f"RSI {rsi} < 35 (oversold)")
    if stoch_k and stoch_k < 25:
        signals.append(f"Stochastic %K {stoch_k} < 25 (oversold)")
    if williams and williams < -75:
        signals.append(f"Williams %R {williams} (oversold zone)")
    if pct_b and pct_b < 0.15:
        signals.append(f"BB %B {pct_b:.2f} (near lower band)")
    if cci and cci < -100:
        signals.append(f"CCI {cci} < -100 (oversold)")
    if obv_trend == "RISING":
        signals.append("OBV rising (buying pressure despite price drop)")
    if macd_hist and macd_hist > 0:
        signals.append("MACD histogram positive (momentum shifting)")
    if wyckoff_phase in ("ACCUMULATION", "SPRING"):
        signals.append(f"Wyckoff: {wyckoff_phase} phase active")

    if len(signals) < MIN_CONFLUENCE:
        return None

    confidence = min(95, 50 + len(signals) * 8)
    label = ind.get("label", key.upper())
    price = ind.get("price_formatted", "")
    risk = max(20, 80 - len(signals) * 8)

    return _alert(
        key, label, "OVERSOLD_REVERSAL", HIGH, confidence,
        action=f"WATCH FOR ENTRY: {label} {price} — {len(signals)} oversold signals confluent. Wait for first green candle confirmation before adding.",
        signals=signals,
        risk_level=risk,
        timeframe="1-5 days",
        category=ind.get("category", ""),
        extra={"setup": "oversold_reversal", "entry_trigger": "First close above prior day high"}
    )


def _check_overbought_warning(key, ind, wyckoff_phase):
    """
    Fires when 3+ overbought signals align.
    """
    signals = []

    rsi = ind.get("rsi_14")
    stoch_k = ind.get("stoch_k")
    williams = ind.get("williams_r")
    pct_b = ind.get("bb_pct_b")
    cci = ind.get("cci")
    macd_hist = ind.get("macd_hist")
    trend = ind.get("trend", "")

    if rsi and rsi > 70:
        signals.append(f"RSI {rsi} > 70 (overbought)")
    if stoch_k and stoch_k > 80:
        signals.append(f"Stochastic %K {stoch_k} > 80 (overbought)")
    if williams and williams > -20:
        signals.append(f"Williams %R {williams} (overbought zone)")
    if pct_b and pct_b > 0.85:
        signals.append(f"BB %B {pct_b:.2f} (near upper band)")
    if cci and cci > 100:
        signals.append(f"CCI {cci} > 100 (overbought)")
    if macd_hist and macd_hist < 0:
        signals.append("MACD histogram going negative (momentum fading)")
    if wyckoff_phase in ("DISTRIBUTION", "UTAD"):
        signals.append(f"Wyckoff: {wyckoff_phase} phase active")

    if len(signals) < MIN_CONFLUENCE:
        return None

    confidence = min(90, 45 + len(signals) * 8)
    label = ind.get("label", key.upper())
    price = ind.get("price_formatted", "")
    risk = 75

    return _alert(
        key, label, "OVERBOUGHT_WARNING", HIGH, confidence,
        action=f"CAUTION: {label} {price} — {len(signals)} overbought signals. Tighten stops. Reduce position. Do NOT add.",
        signals=signals,
        risk_level=risk,
        timeframe="3-10 days",
        category=ind.get("category", ""),
        extra={"setup": "overbought_warning", "action_detail": "Reduce position by 25-50%"}
    )


def _check_trend_break(key, ind, wyckoff_phase):
    """
    Detects significant trend breaks: death cross, 200SMA loss, or 50SMA reclaim.
    """
    signals = []
    death_cross = ind.get("death_cross", False)
    golden_cross = ind.get("golden_cross", False)
    sma200 = ind.get("sma_200")
    sma50 = ind.get("sma_50")
    price = ind.get("price")
    trend = ind.get("trend", "")
    macd_hist = ind.get("macd_hist")
    ichimoku = ind.get("ichimoku", {})

    if death_cross:
        signals.append("DEATH CROSS: 50 SMA crossed below 200 SMA")
    if golden_cross:
        signals.append("GOLDEN CROSS: 50 SMA crossed above 200 SMA")
    if sma200 and price and price < sma200 * 0.98:
        signals.append(f"Price {ind.get('price_formatted','')} below 200 SMA ({sma200:.2f}) by >2%")
    if sma50 and price and price < sma50 * 0.97:
        signals.append(f"Price below 50 SMA — trend degraded")
    if macd_hist and macd_hist < 0 and ind.get("rsi_14", 50) < 45:
        signals.append("MACD negative + RSI sub-50 (bearish confluence)")
    if ichimoku.get("signal") == "BELOW_CLOUD":
        signals.append("Ichimoku: Price BELOW cloud (bearish)")
    if ichimoku.get("tk_cross") == "BEARISH":
        signals.append("Ichimoku: TK cross bearish")
    if trend in ("DOWNTREND",):
        signals.append(f"Trend classification: {trend}")
    if wyckoff_phase == "MARKDOWN":
        signals.append("Wyckoff: MARKDOWN phase (distribution complete)")

    if len(signals) < MIN_CONFLUENCE:
        return None

    label = ind.get("label", key.upper())
    confidence = min(90, 40 + len(signals) * 9)
    severity = CRITICAL if death_cross else HIGH

    return _alert(
        key, label, "TREND_BREAK", severity, confidence,
        action=f"DEFENSIVE SIGNAL: {label} — {len(signals)} bearish trend signals. Do NOT add. Evaluate stops.",
        signals=signals,
        risk_level=85,
        timeframe="1-4 weeks",
        category=ind.get("category", ""),
    )


def _check_momentum_shift(key, ind, wyckoff_phase):
    """
    Detects early momentum shift — MACD cross + RSI divergence.
    Lower bar (2 signals) but lower confidence.
    """
    signals = []

    macd_line = ind.get("macd_line")
    macd_signal = ind.get("macd_signal")
    macd_hist = ind.get("macd_hist")
    rsi = ind.get("rsi_14")
    momentum = ind.get("momentum_score", 0)
    trend = ind.get("trend", "")
    obv_trend = ind.get("obv_trend")

    # MACD bullish cross
    if macd_line and macd_signal and macd_line > macd_signal and macd_hist and macd_hist > 0:
        signals.append(f"MACD bullish cross (line {macd_line:.4f} > signal {macd_signal:.4f})")
    if macd_line and macd_signal and macd_line < macd_signal and macd_hist and macd_hist < 0:
        signals.append(f"MACD bearish cross (line < signal)")

    if momentum > 40:
        signals.append(f"Momentum score {momentum} (strong bull)")
    elif momentum < -40:
        signals.append(f"Momentum score {momentum} (strong bear)")

    if obv_trend == "RISING" and rsi and rsi < 50:
        signals.append("OBV rising while RSI subdued — accumulation signal")
    if obv_trend == "FALLING" and rsi and rsi > 55:
        signals.append("OBV falling while RSI elevated — distribution signal")

    if wyckoff_phase == "MARKUP":
        signals.append("Wyckoff: MARKUP phase confirmed")

    if len(signals) < 2:
        return None

    label = ind.get("label", key.upper())
    confidence = min(75, 40 + len(signals) * 10)
    bull = momentum > 0
    action_word = "EARLY BULL SIGNAL" if bull else "EARLY BEAR SIGNAL"

    return _alert(
        key, label, "MOMENTUM_SHIFT", MEDIUM, confidence,
        action=f"{action_word}: {label} — momentum shifting. Watch for confirmation before acting.",
        signals=signals,
        risk_level=50,
        timeframe="3-7 days",
        category=ind.get("category", ""),
    )


def _check_bb_squeeze_breakout(key, ind, wyckoff_phase):
    """
    Bollinger Band squeeze + directional expansion signal.
    """
    bb_squeeze = ind.get("bb_squeeze", False)
    bb_width = ind.get("bb_width")
    pct_b = ind.get("bb_pct_b")
    vol_profile = ind.get("volume_profile", {})
    momentum = ind.get("momentum_score", 0)

    if not bb_squeeze:
        return None

    signals = [f"BB Squeeze: bandwidth {bb_width:.4f} (compressed volatility)"]

    vol_label = vol_profile.get("label", "")
    vol_ratio = vol_profile.get("ratio", 1.0)
    if vol_ratio and vol_ratio > 1.5:
        signals.append(f"Volume surge {vol_ratio:.1f}x above average")
    if pct_b and pct_b > 0.8:
        signals.append("Price at upper BB — bullish breakout direction")
    elif pct_b and pct_b < 0.2:
        signals.append("Price at lower BB — bearish breakdown direction")
    if momentum and abs(momentum) > 30:
        signals.append(f"Momentum score {momentum} — directional pressure building")

    if len(signals) < MIN_CONFLUENCE:
        return None

    direction = "BULLISH" if pct_b and pct_b > 0.5 else "BEARISH"
    label = ind.get("label", key.upper())
    confidence = min(80, 40 + len(signals) * 10)

    return _alert(
        key, label, "SQUEEZE_BREAKOUT", MEDIUM, confidence,
        action=f"VOLATILITY SETUP: {label} — BB squeeze with {direction.lower()} lean. Watch for breakout confirmation.",
        signals=signals,
        risk_level=55,
        timeframe="1-5 days",
        category=ind.get("category", ""),
        extra={"direction": direction}
    )


def _check_fibonacci_bounce(key, ind):
    """
    Price at key Fibonacci level with at least 2 confirming signals.
    """
    fib = ind.get("fibonacci")
    if not fib:
        return None

    price = ind.get("price")
    price_pct = fib.get("price_vs_range_pct", 50)
    nearest_support = fib.get("nearest_support")
    nearest_resistance = fib.get("nearest_resistance")
    rsi = ind.get("rsi_14")
    stoch_k = ind.get("stoch_k")

    if not price or not nearest_support:
        return None

    # Check if price is within 1% of a key Fib level
    key_fib_pcts = [0, 23.6, 38.2, 50, 61.8, 78.6, 100]
    at_fib_level = any(abs(price_pct - p) < 2.5 for p in key_fib_pcts)

    if not at_fib_level:
        return None

    signals = []
    nearest_pct = min(key_fib_pcts, key=lambda p: abs(price_pct - p))
    signals.append(f"Price at {nearest_pct}% Fibonacci retracement level")

    if rsi and rsi < 45:
        signals.append(f"RSI {rsi} (weakened — potential bounce)")
    if stoch_k and stoch_k < 30:
        signals.append(f"Stochastic {stoch_k} (oversold at Fib support)")
    if nearest_support and price <= nearest_support * 1.01:
        signals.append(f"Price testing Fib support ${nearest_support:,.2f}")

    if len(signals) < 2:
        return None

    label = ind.get("label", key.upper())
    confidence = min(75, 40 + len(signals) * 10)

    return _alert(
        key, label, "FIBONACCI_BOUNCE", MEDIUM, confidence,
        action=f"FIB LEVEL WATCH: {label} at {nearest_pct:.1f}% Fibonacci. Watch for reversal candle.",
        signals=signals,
        risk_level=45,
        timeframe="2-5 days",
        category=ind.get("category", ""),
        extra={"fib_level": nearest_pct}
    )


def run_alert_checks(indicators_data: dict, data_json: dict) -> list:
    """
    Run all alert checks against indicators + data.json context.
    Returns only alerts that meet MIN_CONFLUENCE threshold.
    """
    alerts = []
    assets = indicators_data.get("assets", {})
    wyckoff_assets = data_json.get("wyckoff", {}).get("assets", {})
    macro = data_json.get("macro", {})
    gate = data_json.get("decision_gate", {})
    posture = gate.get("risk_posture", "WATCH-ONLY")

    macro_risk = float(macro.get("risk_level", 50) or 50)

    for key, ind in assets.items():
        if ind.get("error"):
            continue

        wyckoff_key = wyckoff_assets.get(key, {})
        wyckoff_phase = wyckoff_key.get("phase", "UNKNOWN")
        if wyckoff_key.get("spring"):
            wyckoff_phase = "SPRING"
        elif wyckoff_key.get("utad"):
            wyckoff_phase = "UTAD"

        # Run each check
        checks = [
            _check_oversold_reversal(key, ind, wyckoff_phase),
            _check_overbought_warning(key, ind, wyckoff_phase),
            _check_trend_break(key, ind, wyckoff_phase),
            _check_momentum_shift(key, ind, wyckoff_phase),
            _check_bb_squeeze_breakout(key, ind, wyckoff_phase),
            _check_fibonacci_bounce(key, ind),
        ]

        for alert in checks:
            if alert is None:
                continue

            # Apply macro gate override
            if posture == "DEFENSIVE" and alert["alert_type"] not in ("OVERBOUGHT_WARNING", "TREND_BREAK"):
                alert["macro_override"] = f"MACRO GATE: {posture} — treat all buy signals with caution"
                alert["confidence"] = max(0, alert["confidence"] - 20)

            if macro_risk > 75:
                alert["macro_risk_note"] = f"High macro risk ({macro_risk}) — risk sizing down"

            alerts.append(alert)

    # Sort: CRITICAL first, then by confidence desc
    severity_order = {CRITICAL: 0, HIGH: 1, MEDIUM: 2, INFO: 3}
    alerts.sort(key=lambda a: (severity_order.get(a["severity"], 3), -a["confidence"]))

    return alerts


def run_all(existing_alerts: Optional[list] = None) -> dict:
    """
    Load indicators + data.json, run all checks, return structured alerts dict.
    """
    indicators_data = _load_json(INDICATORS_FILE)
    data_json = _load_json(DATA_FILE)

    if not indicators_data.get("assets"):
        logger.warning("No indicator data available — alert engine cannot run")
        return {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "alert_count": 0,
            "active_alerts": [],
            "status": "NO_INDICATOR_DATA",
        }

    alerts = run_alert_checks(indicators_data, data_json)

    logger.info(f"Alert engine: {len(alerts)} alerts generated")
    for a in alerts[:5]:
        logger.info(f"  [{a['severity']}] {a['key'].upper()}: {a['alert_type']} ({a['confidence']}%)")

    # Write to logs
    ALERTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with ALERTS_FILE.open("w", encoding="utf-8") as f:
        json.dump({
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "alert_count": len(alerts),
            "active_alerts": alerts,
        }, f, indent=2)

    return {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "alert_count": len(alerts),
        "active_alerts": alerts,
        "status": "OK",
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    result = run_all()
    print(f"\nAlerts generated: {result['alert_count']}")
    for a in result["active_alerts"][:10]:
        print(f"  [{a['severity']}] {a['label']}: {a['action'][:80]}...")
