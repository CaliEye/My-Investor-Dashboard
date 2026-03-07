#!/usr/bin/env python3
"""
PIVOT ENGINE — CaliEye Dashboard
Military-grade regime switching logic based on OODA Loop framework.

OODA LOOP:
  OBSERVE  — Continuously ingest macro + technical + on-chain signals
  ORIENT   — Score regime across 6 dimensions, detect pivot conditions
  DECIDE   — Fire PIVOT alert when threshold crossed, generate action order
  ACT      — Clear action: what to do NOW, what to exit, what to enter

MILITARY RISK PRINCIPLES:
  1. Rules of Engagement (ROE) — Hard rules that override emotions
  2. Mission Clarity — Always know the objective before entering
  3. Intelligence Before Action — Never move without 3+ signal confluence
  4. Layered Defense — Stop losses at 3 levels (soft / firm / max pain)
  5. Exit First, Entry Second — Always plan the exit before the entry
  6. After Action Review (AAR) — Every pivot logged for pattern learning
  7. Commander's Intent — When comms are down, default to the last order

PIVOT TYPES:
  RISK-OFF  — Defensive pivot: exit risk, hold cash/T-bills/gold
  RISK-ON   — Offensive pivot: deploy capital into BTC/equities
  NEUTRAL   — Hold current positions, no new exposure
  ROTATE    — Sector rotation signal (shift from X to Y)
  EMERGENCY — Immediate stop-loss trigger (black swan)
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = REPO_ROOT / "data" / "data.json"
INTEL_FILE = REPO_ROOT / "data" / "intel.json"
PIVOT_LOG_FILE = REPO_ROOT / "logs" / "pivot_history.json"
PIVOT_OUTPUT_FILE = REPO_ROOT / "data" / "pivot_status.json"


def _load_json(path):
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _to_float(val, default=0.0):
    try:
        return float(str(val).replace("%", "").replace("$", "").replace(",", ""))
    except Exception:
        return default


# ─────────────────────────────────────────────
# OBSERVE: Signal scoring functions
# ─────────────────────────────────────────────

def score_macro_regime(macro: dict) -> dict:
    """
    Score macro regime: 0 = extreme bear, 100 = extreme bull
    Returns score + contributing factors
    """
    score = 50  # Neutral baseline
    factors = []
    signals = []

    dxy = _to_float(macro.get("dxy"), 104)
    us10y = _to_float(macro.get("us10y_yield"), 4.5)
    fed_rate = _to_float(macro.get("fed_funds_rate"), 4.5)
    cpi = _to_float(macro.get("cpi", macro.get("cpi_yoy")), 3.0)
    unemployment = _to_float(macro.get("unemployment", macro.get("unemployment_rate")), 4.0)
    risk_level = _to_float(macro.get("risk_level"), 60)

    # DXY: High dollar = headwind for risk assets
    if dxy > 108:
        score -= 15
        signals.append(f"DXY {dxy} CRUSHING risk assets (>108)")
    elif dxy > 104:
        score -= 8
        signals.append(f"DXY {dxy} elevated headwind")
    elif dxy < 100:
        score += 12
        signals.append(f"DXY {dxy} weak — tailwind for risk assets")
    elif dxy < 102:
        score += 5
        signals.append(f"DXY {dxy} easing")

    # 10Y Yield: High yields = competition for risk assets
    if us10y > 5.0:
        score -= 18
        signals.append(f"10Y yield {us10y}% CRITICAL — financial conditions very tight")
    elif us10y > 4.5:
        score -= 10
        signals.append(f"10Y yield {us10y}% elevated pressure")
    elif us10y < 3.5:
        score += 15
        signals.append(f"10Y yield {us10y}% low — favorable for equities/crypto")
    elif us10y < 4.0:
        score += 8
        signals.append(f"10Y yield {us10y}% easing")

    # CPI: High inflation = Fed stays hawkish
    if cpi > 4.0:
        score -= 20
        signals.append(f"CPI {cpi}% WELL above target — Fed cannot pivot")
    elif cpi > 3.0:
        score -= 10
        signals.append(f"CPI {cpi}% above 2% target — Fed cautious")
    elif cpi < 2.5:
        score += 15
        signals.append(f"CPI {cpi}% near target — Fed has room to cut")
    elif cpi < 3.0:
        score += 5
        signals.append(f"CPI {cpi}% approaching target")

    # Unemployment: Rising unemployment often precedes cuts (initially bad, then good)
    if unemployment > 5.0:
        score -= 5
        signals.append(f"Unemployment {unemployment}% rising — recession risk")
    elif unemployment < 4.0:
        score += 5
        signals.append(f"Unemployment {unemployment}% — strong labor market")

    # Overall macro risk level from data.json
    score -= (risk_level - 50) * 0.3

    return {
        "score": round(max(0, min(100, score)), 1),
        "signals": signals,
        "raw": {"dxy": dxy, "us10y": us10y, "fed_rate": fed_rate, "cpi": cpi, "unemployment": unemployment}
    }


def score_crypto_regime(crypto: dict) -> dict:
    """Score crypto-specific regime signals"""
    score = 50
    signals = []

    btc_rsi = _to_float(crypto.get("btc_rsi", crypto.get("rsi_weekly")), 50)
    eth_rsi = _to_float(crypto.get("eth_rsi", crypto.get("rsi_weekly")), 50)
    fear_greed = _to_float(crypto.get("fear_greed_index"), 50)
    cycle_phase = str(crypto.get("cycle_phase", crypto.get("cycle_status", ""))).lower()
    whale_activity = str(crypto.get("whale_activity", "")).lower()
    funding_rate = str(crypto.get("funding_rate", "")).lower()

    if btc_rsi < 25:
        score += 20
        signals.append(f"BTC RSI {btc_rsi} EXTREME OVERSOLD — historically strong buy zone")
    elif btc_rsi < 35:
        score += 12
        signals.append(f"BTC RSI {btc_rsi} oversold — accumulation opportunity")
    elif btc_rsi > 75:
        score -= 15
        signals.append(f"BTC RSI {btc_rsi} overbought — distribution risk")
    elif btc_rsi > 65:
        score -= 8
        signals.append(f"BTC RSI {btc_rsi} elevated — caution on new entries")

    if fear_greed < 20:
        score += 18
        signals.append(f"Fear & Greed {fear_greed} EXTREME FEAR — contrarian buy signal")
    elif fear_greed < 35:
        score += 10
        signals.append(f"Fear & Greed {fear_greed} Fear zone — favorable entry conditions")
    elif fear_greed > 80:
        score -= 15
        signals.append(f"Fear & Greed {fear_greed} EXTREME GREED — distribution zone")
    elif fear_greed > 65:
        score -= 8
        signals.append(f"Fear & Greed {fear_greed} Greed — tighten stops")

    if "accumulat" in cycle_phase or "post-halving" in cycle_phase:
        score += 15
        signals.append(f"Cycle phase: ACCUMULATION — historically optimal DCA zone")
    elif "bull" in cycle_phase or "markup" in cycle_phase:
        score += 10
        signals.append(f"Cycle phase: BULL — ride with stops")
    elif "distribut" in cycle_phase:
        score -= 15
        signals.append(f"Cycle phase: DISTRIBUTION — reduce exposure")
    elif "bear" in cycle_phase or "markdown" in cycle_phase:
        score -= 20
        signals.append(f"Cycle phase: BEAR/MARKDOWN — cash is king")

    if "distributing" in whale_activity:
        score -= 10
        signals.append("Whale activity: DISTRIBUTING — smart money exiting")
    elif "accumulating" in whale_activity:
        score += 10
        signals.append("Whale activity: ACCUMULATING — smart money entering")

    if "negative" in funding_rate or "-" in funding_rate:
        score += 8
        signals.append("Funding rate negative — shorts paying longs (contrarian bull)")
    elif "high" in funding_rate or "extreme" in funding_rate:
        score -= 8
        signals.append("Funding rate elevated — longs overextended")

    return {"score": round(max(0, min(100, score)), 1), "signals": signals}


def score_intel_regime(intel: dict) -> dict:
    """Score signals from intel aggregator (Polymarket, CME FedWatch, etc.)"""
    score = 50
    signals = []

    # Polymarket signals
    polymarket = intel.get("polymarket", {})
    fed_pause_prob = _to_float(polymarket.get("fed_pause_probability"), 50)
    btc_above_80k = _to_float(polymarket.get("btc_above_80k_probability"), 30)
    recession_prob = _to_float(polymarket.get("recession_probability"), 30)

    if fed_pause_prob > 75:
        score += 10
        signals.append(f"Polymarket: {fed_pause_prob:.0f}% chance Fed pauses — bullish for risk")
    elif fed_pause_prob < 30:
        score -= 8
        signals.append(f"Polymarket: only {fed_pause_prob:.0f}% Fed pause probability — hawkish risk")

    if btc_above_80k > 60:
        score += 8
        signals.append(f"Polymarket: {btc_above_80k:.0f}% BTC above $80k prediction")

    if recession_prob > 50:
        score -= 15
        signals.append(f"Polymarket: {recession_prob:.0f}% recession probability — defensive posture")

    # CME FedWatch
    fedwatch = intel.get("fedwatch", {})
    cut_probability = _to_float(fedwatch.get("cut_probability"), 30)
    next_meeting = fedwatch.get("next_meeting", "")
    if cut_probability > 70:
        score += 15
        signals.append(f"CME FedWatch: {cut_probability:.0f}% rate CUT probability — risk-on catalyst")
    elif cut_probability > 40:
        score += 7
        signals.append(f"CME FedWatch: {cut_probability:.0f}% cut probability — mildly bullish")

    # Hedge fund / 13F signals
    hf_signals = intel.get("hedge_fund_signals", {})
    if hf_signals.get("top_funds_btc_exposure"):
        score += 5
        signals.append("Hedge fund 13F: Major funds adding BTC/crypto exposure")
    if hf_signals.get("risk_off_rotation"):
        score -= 10
        signals.append("Hedge fund 13F: Risk-off rotation detected in latest filings")

    return {"score": round(max(0, min(100, score)), 1), "signals": signals}


# ─────────────────────────────────────────────
# ORIENT: Composite regime scoring
# ─────────────────────────────────────────────

def orient_regime(data: dict, intel: dict) -> dict:
    """
    Combine all signal scores into a unified regime orientation.
    Returns regime label, score, confidence, and recommended posture.
    """
    macro = data.get("macro", {})
    crypto = data.get("crypto", {})
    gate = data.get("decision_gate", {})

    macro_result = score_macro_regime(macro)
    crypto_result = score_crypto_regime(crypto)
    intel_result = score_intel_regime(intel)

    # Weighted composite: macro 40%, crypto 35%, intel 25%
    composite = (
        macro_result["score"] * 0.40 +
        crypto_result["score"] * 0.35 +
        intel_result["score"] * 0.25
    )
    composite = round(composite, 1)

    all_signals = macro_result["signals"] + crypto_result["signals"] + intel_result["signals"]

    # Signal counts for confidence
    bull_signals = len([s for s in all_signals if any(w in s.lower() for w in
        ["buy", "bullish", "oversold", "fear", "accumul", "cut", "weak dollar", "tailwind", "pause"])])
    bear_signals = len([s for s in all_signals if any(w in s.lower() for w in
        ["bear", "distribut", "overbought", "recession", "crushing", "tight", "critical", "hawk"])])

    signal_imbalance = abs(bull_signals - bear_signals)
    confluence_confidence = min(95, 40 + signal_imbalance * 8)

    # Regime classification
    if composite >= 70:
        regime = "RISK-ON"
        posture = "RISK-ON"
        color = "#39ff14"
        action_brief = "Deploy capital. BTC DCA + equity positions justified. Tight stops."
    elif composite >= 58:
        regime = "CAUTIOUSLY_BULLISH"
        posture = "SELECTIVE"
        color = "#00D2FF"
        action_brief = "Selective entries on high-confluence setups only. 50% normal position size."
    elif composite >= 42:
        regime = "NEUTRAL"
        posture = "WATCH-ONLY"
        color = "#FFD166"
        action_brief = "Hold current positions. No new risk. T-bills for fresh capital."
    elif composite >= 28:
        regime = "CAUTIOUSLY_BEARISH"
        posture = "DEFENSIVE"
        color = "#FF4757"
        action_brief = "Reduce risk exposure. Tighten stops. Gold/T-bills for safety."
    else:
        regime = "RISK-OFF"
        posture = "DEFENSIVE"
        color = "#FF4757"
        action_brief = "Exit risk assets. Capital preservation mode. Wait for regime reset."

    return {
        "regime": regime,
        "posture": posture,
        "composite_score": composite,
        "confidence": confluence_confidence,
        "color": color,
        "action_brief": action_brief,
        "macro_score": macro_result["score"],
        "crypto_score": crypto_result["score"],
        "intel_score": intel_result["score"],
        "all_signals": all_signals,
        "bull_signal_count": bull_signals,
        "bear_signal_count": bear_signals,
    }


# ─────────────────────────────────────────────
# DECIDE: Pivot detection + OODA action orders
# ─────────────────────────────────────────────

def decide_pivot(current_regime: dict, previous_pivot: dict) -> dict:
    """
    Compare current regime to previous pivot state.
    Returns pivot decision: fire alert if regime shifted significantly.
    """
    prev_posture = previous_pivot.get("posture", "WATCH-ONLY")
    prev_score = previous_pivot.get("composite_score", 50)
    current_posture = current_regime["posture"]
    current_score = current_regime["composite_score"]

    score_delta = abs(current_score - prev_score)
    posture_changed = prev_posture != current_posture

    # Pivot fires when posture changes OR score moves >15 points
    if posture_changed or score_delta >= 15:
        direction = "BULL" if current_score > prev_score else "BEAR"
        if posture_changed:
            pivot_type = "POSTURE_CHANGE"
            urgency = "HIGH"
        elif score_delta >= 25:
            pivot_type = "MAJOR_SHIFT"
            urgency = "HIGH"
        else:
            pivot_type = "GRADUAL_SHIFT"
            urgency = "MEDIUM"

        return {
            "pivot_fired": True,
            "pivot_type": pivot_type,
            "direction": direction,
            "urgency": urgency,
            "from_posture": prev_posture,
            "to_posture": current_posture,
            "score_delta": round(score_delta, 1),
            "fired_utc": datetime.now(timezone.utc).isoformat(),
        }

    return {"pivot_fired": False, "reason": f"Stable regime — delta {score_delta:.1f} < 15"}


def generate_action_order(regime: dict, pivot: dict, data: dict) -> dict:
    """
    OODA ACT phase — Generate a specific action order.
    Military format: SITUATION → MISSION → EXECUTION → SERVICE/SUPPORT → COMMAND
    """
    posture = regime["posture"]
    regime_name = regime["regime"]
    score = regime["composite_score"]
    confidence = regime["confidence"]
    signals = regime["all_signals"]

    crypto = data.get("crypto", {})
    btc_price = _to_float(crypto.get("btc_usd"), 0)
    btc_rsi = _to_float(crypto.get("btc_rsi"), 50)

    macro = data.get("macro", {})
    us10y = _to_float(macro.get("us10y_yield"), 4.5)

    # SITUATIONAL AWARENESS
    situation = f"Regime: {regime_name} (score {score}/100, confidence {confidence}%). " \
                f"{regime['bull_signal_count']} bull signals vs {regime['bear_signal_count']} bear signals."

    # MISSION
    if posture == "RISK-ON":
        mission = "DEPLOY CAPITAL. Accumulate BTC and high-conviction positions."
        execution = [
            f"BTC DCA: Increase weekly purchase by 50% at current ${btc_price:,.0f}",
            "Equities: Add to QQQ/SPY on next pullback",
            "Stop loss: Set BTC stop at -8% from entry (military rule: never lose more than 8% per position)",
            "Target: Oct/Nov 2026 bull run peak",
        ]
    elif posture == "SELECTIVE":
        mission = "SELECTIVE ENGAGEMENT. Only highest confluence setups."
        execution = [
            "BTC: Continue base DCA (normal size only)",
            "New positions: Only enter if 3+ confirming signals",
            "Position size: Max 50% normal allocation",
            f"T-bills: Park excess cash at 5%+ risk-free",
        ]
    elif posture == "WATCH-ONLY":
        mission = "HOLD POSITION. No new risk exposure. Observe and gather intel."
        execution = [
            "No new crypto purchases",
            "Hold existing BTC stack — do not sell",
            f"Fresh capital: T-bills only (risk-free 5%+)",
            "Monitor for regime flip — set alerts on DXY <100, RSI <30",
        ]
    elif posture == "DEFENSIVE":
        mission = "DEFENSIVE POSTURE. Capital preservation is the objective."
        execution = [
            "Reduce any leveraged positions immediately",
            "Tighten stops: Move to -5% from current price",
            "Gold allocation: Consider adding GLD as hedge",
            "T-bills: Move 30-50% of liquid capital to risk-free",
            f"Watch: 10Y yield {us10y}% — if crosses 5.2%, emergency defensive",
        ]
    else:
        mission = "EMERGENCY PROTOCOL. Exit risk assets."
        execution = [
            "EXIT: Sell risk assets above support levels (no panic selling below)",
            "CASH: Move to T-bills and gold",
            "BTC: Hold cold storage — never sell the core stack",
            "Re-entry criteria: Wait for Fear & Greed < 20 AND RSI < 30",
        ]

    # RULES OF ENGAGEMENT (invariant hard rules)
    rules_of_engagement = [
        "HARD RULE 1: Never invest more than you can afford to lose entirely",
        "HARD RULE 2: BTC core stack (cold storage) is NEVER sold — ever",
        "HARD RULE 3: No new crypto risk before Oct 2026 unless gate flips to RISK-ON",
        "HARD RULE 4: Maximum 8% loss per position before forced exit",
        "HARD RULE 5: Confluence gate must show 3+ signals before any major move",
        "HARD RULE 6: Emotions = enemy. The dashboard decides, not feelings",
    ]

    # LAYERED STOP LOSS LEVELS
    if btc_price > 0:
        soft_stop = round(btc_price * 0.92, 0)
        firm_stop = round(btc_price * 0.85, 0)
        max_pain_stop = round(btc_price * 0.75, 0)
        stop_levels = {
            "soft": f"${soft_stop:,.0f} (-8% — first warning, review position)",
            "firm": f"${firm_stop:,.0f} (-15% — exit half position)",
            "max_pain": f"${max_pain_stop:,.0f} (-25% — full defensive exit)",
        }
    else:
        stop_levels = {}

    return {
        "situation": situation,
        "mission": mission,
        "execution": execution,
        "rules_of_engagement": rules_of_engagement,
        "stop_levels": stop_levels,
        "commander_intent": f"FREEDOM BY 2030. Every decision must serve this mission. Current posture: {posture}.",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }


# ─────────────────────────────────────────────
# Main Runner
# ─────────────────────────────────────────────

def run_all(existing_pivot: Optional[dict] = None) -> dict:
    """
    Full OODA cycle. Returns pivot_status dict for data.json.
    """
    data = _load_json(DATA_FILE)
    intel = _load_json(INTEL_FILE)

    previous = existing_pivot or _load_json(PIVOT_OUTPUT_FILE) or {"posture": "WATCH-ONLY", "composite_score": 50}

    # OBSERVE + ORIENT
    regime = orient_regime(data, intel)

    # DECIDE
    pivot = decide_pivot(regime, previous)

    # ACT
    action_order = generate_action_order(regime, pivot, data)

    result = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "regime": regime["regime"],
        "posture": regime["posture"],
        "composite_score": regime["composite_score"],
        "confidence": regime["confidence"],
        "color": regime["color"],
        "action_brief": regime["action_brief"],
        "macro_score": regime["macro_score"],
        "crypto_score": regime["crypto_score"],
        "intel_score": regime["intel_score"],
        "bull_signals": regime["bull_signal_count"],
        "bear_signals": regime["bear_signal_count"],
        "all_signals": regime["all_signals"],
        "pivot": pivot,
        "action_order": action_order,
        "ooda_cycle": "COMPLETE",
    }

    # Log pivot if fired
    if pivot.get("pivot_fired"):
        history = _load_json(PIVOT_LOG_FILE) if PIVOT_LOG_FILE.exists() else {"pivots": []}
        pivots = history.get("pivots", [])
        pivots.insert(0, {**pivot, "regime_snapshot": regime})
        pivots = pivots[:50]  # Keep last 50
        PIVOT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with PIVOT_LOG_FILE.open("w") as f:
            import json as _json
            _json.dump({"pivots": pivots}, f, indent=2)

        print(f"PIVOT FIRED: {pivot['pivot_type']} — {pivot['from_posture']} → {pivot['to_posture']} (delta {pivot['score_delta']})")
    else:
        print(f"Regime stable: {regime['regime']} score={regime['composite_score']} ({pivot.get('reason','')})")

    # Write pivot status
    PIVOT_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with PIVOT_OUTPUT_FILE.open("w") as f:
        import json as _json
        _json.dump(result, f, indent=2)

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    result = run_all()
    print(f"\nRegime: {result['regime']}")
    print(f"Score: {result['composite_score']}/100 (confidence {result['confidence']}%)")
    print(f"Posture: {result['posture']}")
    print(f"Action: {result['action_brief']}")
    if result["pivot"].get("pivot_fired"):
        print(f"\nPIVOT ALERT: {result['pivot']['pivot_type']}")
