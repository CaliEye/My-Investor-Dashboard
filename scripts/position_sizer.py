#!/usr/bin/env python3
"""
Position Sizer — CaliEye Dashboard
Kelly Criterion + Military Risk Management Framework

PHILOSOPHY:
  "Amateurs think about how much they can make.
   Professionals think about how much they can lose."
   — Every hedge fund risk manager ever.

KELLY CRITERION:
  f* = (bp - q) / b
  where:
    f* = fraction of capital to deploy
    b  = net odds received (profit/loss ratio)
    p  = probability of win (from confluence score)
    q  = probability of loss (1 - p)

  NEVER use full Kelly. Use 1/4 or 1/2 Kelly for safety.
  Full Kelly has severe drawdown risk even if correct.

MILITARY RISK LEVELS (adapted from DEFCON / threat levels):
  LEVEL 1 — MAXIMUM READINESS   : Full risk-on, bull regime confirmed (>80/100)
  LEVEL 2 — ELEVATED READINESS  : Cautiously bullish (65-80/100)
  LEVEL 3 — NORMAL OPERATIONS   : Watch-only, standard allocation (45-65/100)
  LEVEL 4 — INCREASED CAUTION   : Defensive, reduce exposure (25-45/100)
  LEVEL 5 — MAXIMUM CAUTION     : Capital preservation, near-zero risk (<25/100)

POSITION SIZING RULES:
  - Base capital = liquid investable capital (NOT emergency fund, NOT rent)
  - BTC core stack = NEVER in position sizing calculation (it's sacred)
  - Maximum single position: 15% of base capital
  - Maximum crypto exposure: 40% of base capital
  - Maximum single trade risk: 2% of base capital (standard risk per trade)
  - Stop loss ALWAYS set before entry — this is non-negotiable
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = REPO_ROOT / "data" / "data.json"
PIVOT_FILE = REPO_ROOT / "data" / "pivot_status.json"
POSITION_OUTPUT_FILE = REPO_ROOT / "data" / "position_sizing.json"

# ─────────────────────────────────────────────
# Core Constants
# ─────────────────────────────────────────────

MAX_SINGLE_POSITION_PCT = 0.15      # 15% max of base capital per position
MAX_CRYPTO_EXPOSURE_PCT = 0.40      # 40% max crypto of total base capital
RISK_PER_TRADE_PCT = 0.02           # 2% of capital at risk per trade (military standard)
KELLY_FRACTION = 0.25               # Use 1/4 Kelly for safety (proven optimal for volatile assets)

# Asset risk multipliers (higher = more volatile = smaller position)
ASSET_RISK_MULTIPLIERS = {
    "btc":    1.0,   # Baseline
    "eth":    1.3,   # More volatile than BTC
    "gold":   0.4,   # Less volatile — larger position allowed
    "silver": 0.7,
    "spx":    0.5,
    "qqq":    0.6,
    "tlt":    0.3,   # Bonds — least volatile
    "lmt":    0.6,
    "rtx":    0.6,
    "noc":    0.6,
    "ita":    0.5,
    "gdx":    0.9,
    "remx":   1.5,   # Rare earth ETF — very volatile
    "oil":    1.2,
}


# ─────────────────────────────────────────────
# Kelly Criterion Calculator
# ─────────────────────────────────────────────

def kelly_criterion(
    win_probability: float,
    win_multiplier: float = 2.0,
    kelly_fraction: float = KELLY_FRACTION
) -> dict:
    """
    Calculate Kelly-optimal position size.

    Args:
        win_probability: 0.0 to 1.0 (from confluence score)
        win_multiplier:  How much you win per $1 risked (e.g., 2.0 = 2:1 RR)
        kelly_fraction:  Safety factor (0.25 = quarter Kelly, recommended)

    Returns:
        Dict with full, quarter, half Kelly fractions + recommendation
    """
    p = max(0.01, min(0.99, win_probability))
    q = 1 - p
    b = win_multiplier

    # Full Kelly
    full_kelly = (b * p - q) / b
    full_kelly = max(0, full_kelly)

    # Fractional Kelly variants
    half_kelly = full_kelly * 0.5
    quarter_kelly = full_kelly * 0.25

    # Recommendation: quarter Kelly for highly volatile assets
    recommended = quarter_kelly

    return {
        "win_probability": round(p, 3),
        "win_multiplier": round(b, 2),
        "full_kelly_pct": round(full_kelly * 100, 2),
        "half_kelly_pct": round(half_kelly * 100, 2),
        "quarter_kelly_pct": round(quarter_kelly * 100, 2),
        "recommended_pct": round(recommended * 100, 2),
        "recommended_fraction": round(recommended, 4),
        "edge": round((b * p - q), 4),  # Positive = favorable bet
    }


# ─────────────────────────────────────────────
# Military Risk Level Assessment
# ─────────────────────────────────────────────

def assess_military_risk_level(regime_score: float, macro_risk: float, confluence_confidence: float) -> dict:
    """
    Map regime + macro conditions to military-style threat level.
    Higher level = more defensive.
    """
    # Composite risk: regime (inverted = low regime score = high risk), macro risk, confidence
    composite_risk = (
        (100 - regime_score) * 0.45 +
        macro_risk * 0.35 +
        (100 - confluence_confidence) * 0.20
    )

    if composite_risk < 20:
        level = 1
        label = "MAXIMUM READINESS"
        color = "#39ff14"
        description = "All signals aligned bull. Full deployment authorized."
        max_position_multiplier = 1.0
    elif composite_risk < 40:
        level = 2
        label = "ELEVATED READINESS"
        color = "#00D2FF"
        description = "Cautiously bullish. Deploy selectively with tight stops."
        max_position_multiplier = 0.75
    elif composite_risk < 60:
        level = 3
        label = "NORMAL OPERATIONS"
        color = "#FFD166"
        description = "Mixed signals. Standard allocation, no new large positions."
        max_position_multiplier = 0.50
    elif composite_risk < 80:
        level = 4
        label = "INCREASED CAUTION"
        color = "#FF8C00"
        description = "Risk elevated. Reduce exposure, tighten stops, hold cash."
        max_position_multiplier = 0.25
    else:
        level = 5
        label = "MAXIMUM CAUTION"
        color = "#FF4757"
        description = "Capital preservation mode. Near-zero new risk."
        max_position_multiplier = 0.10

    return {
        "level": level,
        "label": label,
        "color": color,
        "description": description,
        "composite_risk_score": round(composite_risk, 1),
        "max_position_multiplier": max_position_multiplier,
    }


# ─────────────────────────────────────────────
# Stop Loss Calculator (3-layer military defense)
# ─────────────────────────────────────────────

def calculate_stops(entry_price: float, asset_key: str, atr: Optional[float] = None) -> dict:
    """
    Calculate 3-layer stop loss system.
    Layer 1 (Soft)   — Warning, review position
    Layer 2 (Firm)   — Exit half position
    Layer 3 (Max)    — Full exit, capital preservation triggered
    """
    risk_mult = ASSET_RISK_MULTIPLIERS.get(asset_key, 1.0)

    # If we have ATR, use ATR-based stops (more precise)
    if atr and atr > 0:
        soft_distance = atr * 1.5 * risk_mult
        firm_distance = atr * 2.5 * risk_mult
        max_distance = atr * 4.0 * risk_mult
    else:
        # Percentage-based fallback
        soft_distance = entry_price * 0.06 * risk_mult
        firm_distance = entry_price * 0.12 * risk_mult
        max_distance = entry_price * 0.20 * risk_mult

    soft_stop = round(entry_price - soft_distance, 2)
    firm_stop = round(entry_price - firm_distance, 2)
    max_stop = round(entry_price - max_distance, 2)

    # Upside targets (risk:reward 2:1 and 3:1)
    target_2r = round(entry_price + soft_distance * 2, 2)
    target_3r = round(entry_price + soft_distance * 3, 2)

    return {
        "entry": entry_price,
        "soft_stop": soft_stop,
        "firm_stop": firm_stop,
        "max_stop": max_stop,
        "soft_stop_pct": round((soft_stop - entry_price) / entry_price * 100, 2),
        "firm_stop_pct": round((firm_stop - entry_price) / entry_price * 100, 2),
        "max_stop_pct": round((max_stop - entry_price) / entry_price * 100, 2),
        "target_2r": target_2r,
        "target_3r": target_3r,
        "risk_reward_ratio": "2:1 (soft stop) / 3:1 (firm stop)",
        "atr_based": atr is not None,
    }


# ─────────────────────────────────────────────
# Position Size Calculator
# ─────────────────────────────────────────────

def calculate_position_size(
    base_capital: float,
    asset_key: str,
    entry_price: float,
    win_probability: float,
    military_level: int,
    stop_loss_price: Optional[float] = None,
    win_multiplier: float = 2.0,
) -> dict:
    """
    Calculate exact position size in USD and units.

    Uses the tighter of:
    a) Kelly Criterion (probability-based)
    b) 2% risk rule (military standard)
    c) Max position cap (15%)

    Args:
        base_capital:    Total liquid investable capital
        asset_key:       Asset identifier (btc, eth, gold, etc.)
        entry_price:     Current or intended entry price
        win_probability: 0.0-1.0, from confluence confidence
        military_level:  1-5 threat level
        stop_loss_price: Defined stop loss (if known)
        win_multiplier:  Expected reward / risk ratio
    """
    risk_mult = ASSET_RISK_MULTIPLIERS.get(asset_key, 1.0)

    # Military level position multiplier
    level_multipliers = {1: 1.0, 2: 0.75, 3: 0.50, 4: 0.25, 5: 0.10}
    level_mult = level_multipliers.get(military_level, 0.50)

    # Kelly sizing
    kelly = kelly_criterion(win_probability, win_multiplier)
    kelly_usd = base_capital * kelly["recommended_fraction"]

    # 2% risk rule: position size = (2% of capital) / stop loss distance pct
    if stop_loss_price and stop_loss_price < entry_price:
        stop_pct = abs(entry_price - stop_loss_price) / entry_price
        risk_rule_usd = (base_capital * RISK_PER_TRADE_PCT) / stop_pct if stop_pct > 0 else base_capital * 0.05
    else:
        # Default to 8% stop if not defined
        risk_rule_usd = (base_capital * RISK_PER_TRADE_PCT) / (0.08 * risk_mult)

    # Max position cap: 15% of capital
    max_position_usd = base_capital * MAX_SINGLE_POSITION_PCT

    # Apply military level and asset volatility scaling
    kelly_usd_scaled = kelly_usd * level_mult / risk_mult
    risk_rule_usd_scaled = risk_rule_usd * level_mult

    # Use the MINIMUM of Kelly, risk rule, and max cap (most conservative)
    recommended_usd = min(kelly_usd_scaled, risk_rule_usd_scaled, max_position_usd)
    recommended_usd = round(max(0, recommended_usd), 2)

    # Convert to units
    units = round(recommended_usd / entry_price, 8) if entry_price > 0 else 0
    pct_of_capital = round(recommended_usd / base_capital * 100, 2) if base_capital > 0 else 0

    return {
        "asset": asset_key,
        "entry_price": entry_price,
        "base_capital": base_capital,
        "recommended_usd": recommended_usd,
        "recommended_units": units,
        "pct_of_capital": pct_of_capital,
        "kelly_usd_raw": round(kelly_usd, 2),
        "risk_rule_usd_raw": round(risk_rule_usd, 2),
        "limiting_factor": (
            "kelly" if kelly_usd_scaled < risk_rule_usd_scaled else
            "risk_rule"
        ),
        "military_level_applied": military_level,
        "win_probability": win_probability,
        "kelly_edge": kelly["edge"],
        "verdict": (
            "STRONG_ENTRY" if kelly["edge"] > 0.2 and military_level <= 2 else
            "VALID_ENTRY" if kelly["edge"] > 0.05 and military_level <= 3 else
            "MARGINAL" if kelly["edge"] > 0 else
            "NO_EDGE — DO NOT ENTER"
        ),
    }


# ─────────────────────────────────────────────
# Portfolio Allocation Framework
# ─────────────────────────────────────────────

def generate_portfolio_framework(
    base_capital: float,
    military_level: int,
    posture: str,
) -> dict:
    """
    Generate full portfolio allocation framework based on current regime.
    This is the macro capital allocation, not individual trade sizing.
    """
    level_allocations = {
        1: {"btc": 0.25, "equities": 0.25, "gold": 0.10, "tbills": 0.20, "cash": 0.10, "speculative": 0.10},
        2: {"btc": 0.20, "equities": 0.20, "gold": 0.15, "tbills": 0.30, "cash": 0.10, "speculative": 0.05},
        3: {"btc": 0.10, "equities": 0.15, "gold": 0.15, "tbills": 0.40, "cash": 0.15, "speculative": 0.05},
        4: {"btc": 0.05, "equities": 0.10, "gold": 0.20, "tbills": 0.50, "cash": 0.15, "speculative": 0.00},
        5: {"btc": 0.00, "equities": 0.05, "gold": 0.25, "tbills": 0.55, "cash": 0.15, "speculative": 0.00},
    }

    alloc_pcts = level_allocations.get(military_level, level_allocations[3])
    alloc_usd = {k: round(base_capital * v, 2) for k, v in alloc_pcts.items()}

    return {
        "military_level": military_level,
        "posture": posture,
        "base_capital": base_capital,
        "allocations_pct": alloc_pcts,
        "allocations_usd": alloc_usd,
        "notes": {
            "btc": "DCA accumulation — weekly purchases at this allocation",
            "equities": "ETFs: QQQ/SPY/ITA — broad exposure, not individual picks",
            "gold": "GLD or physical gold — portfolio insurance",
            "tbills": "3-month T-bill ladder — risk-free income while waiting",
            "cash": "Operational buffer — always keep 10%+ liquid",
            "speculative": "High-risk/high-reward setups — ONLY on RISK-ON posture",
        }
    }


# ─────────────────────────────────────────────
# Main Runner
# ─────────────────────────────────────────────

def run_all(base_capital: Optional[float] = None) -> dict:
    """
    Generate complete position sizing and risk framework for current regime.
    """
    data = _load_json(DATA_FILE)
    pivot = _load_json(PIVOT_FILE)

    macro = data.get("macro", {})
    crypto = data.get("crypto", {})
    gate = data.get("decision_gate", {})

    regime_score = float(pivot.get("composite_score", 50))
    macro_risk = float(macro.get("risk_level", 60) or 60)
    confluence_conf = float(pivot.get("confidence", 50))
    posture = pivot.get("posture", gate.get("risk_posture", "WATCH-ONLY"))

    # Get current BTC price
    btc_price = float(crypto.get("btc_usd", 67000) or 67000)
    eth_price = float(crypto.get("eth_usd", 2000) or 2000)

    # Military risk assessment
    mil_risk = assess_military_risk_level(regime_score, macro_risk, confluence_conf)
    military_level = mil_risk["level"]

    # Default base capital if not provided (user can override)
    if not base_capital:
        base_capital = 10000  # Default $10k — user should update this

    # Win probability from regime score (normalized)
    win_prob = max(0.35, min(0.85, regime_score / 100 * 0.8 + 0.1))

    # Position sizing for key assets
    positions = {}
    for key, price in [("btc", btc_price), ("eth", eth_price), ("gold", 180), ("qqq", 480)]:
        pos = calculate_position_size(
            base_capital=base_capital,
            asset_key=key,
            entry_price=price,
            win_probability=win_prob,
            military_level=military_level,
            win_multiplier=2.0,
        )
        stops = calculate_stops(price, key)
        pos["stops"] = stops
        positions[key] = pos

    # Portfolio allocation framework
    portfolio = generate_portfolio_framework(base_capital, military_level, posture)

    result = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "base_capital": base_capital,
        "military_risk": mil_risk,
        "regime_score": regime_score,
        "win_probability": round(win_prob, 3),
        "positions": positions,
        "portfolio_framework": portfolio,
        "hard_rules": [
            f"Max single position: ${base_capital * MAX_SINGLE_POSITION_PCT:,.0f} ({MAX_SINGLE_POSITION_PCT*100:.0f}%)",
            f"Max crypto exposure: ${base_capital * MAX_CRYPTO_EXPOSURE_PCT:,.0f} ({MAX_CRYPTO_EXPOSURE_PCT*100:.0f}%)",
            f"Risk per trade: ${base_capital * RISK_PER_TRADE_PCT:,.0f} (2% rule)",
            "Stop loss ALWAYS set before entry",
            "BTC core stack is sacred — NOT included in position sizing",
            f"Current Kelly fraction: {KELLY_FRACTION} (Quarter Kelly for safety)",
        ],
    }

    POSITION_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with POSITION_OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"Military Risk Level: {military_level} — {mil_risk['label']}")
    print(f"Win probability: {win_prob:.1%}")
    print(f"BTC position: ${positions['btc']['recommended_usd']:,.0f} ({positions['btc']['pct_of_capital']:.1f}% of capital)")
    print(f"Verdict: {positions['btc']['verdict']}")

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    run_all(base_capital=10000)
