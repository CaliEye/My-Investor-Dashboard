"""
wyckoff_confluence_scanner.py
High-Confluence Wyckoff Smart Money Scanner
CaliEye / My-Investor-Dashboard
Schedule: Every Monday 9am MT
Delivery: Email to dicenso01@gmail.com

CORE RULE: 3+ confluences required before ANY signal fires.
Signals must span 2+ asset classes.
Under threshold = silence. No weak flags.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

SCAN_DATE = datetime.today().strftime("%B %d, %Y")
LOOKBACK_DAYS = 90
VOLUME_MULTIPLIER = 2.0       # 2x avg volume required for confirmation
CONFLUENCE_THRESHOLD = 3      # minimum points before alert fires
ASSET_CLASS_MINIMUM = 2       # signals must span at least 2 asset classes

WATCHLIST = {
"indices":  ["SPY", "QQQ", "DIA"],
"metals":   ["GLD", "SLV"],
"crypto":   ["BTC-USD", "ETH-USD"],
"energy":   ["XLE", "USO"],
"defense":  ["ITA"],
"banking":  ["XLF", "KRE"],
"bonds":    ["HYG", "TLT"],
"macro":    ["DX-Y.NYB"],   # DXY proxy
}

# Key price levels (hard-coded thresholds)
KEY_LEVELS = {
"GLD":     {"breakout": 290,  "breakdown": 230},   # ~$3200/$2500 gold
"BTC-USD": {"breakout": 100000, "breakdown": 50000},
"HYG":     {"stress": 75,    "crisis": 70},
"SPY":     {"watch": None},  # dynamic: 200SMA
"QQQ":     {"watch": None},
}

# ─────────────────────────────────────────────
# DATA FETCH
# ─────────────────────────────────────────────

def fetch(ticker, days=LOOKBACK_DAYS):
"""Fetch OHLCV data for a ticker."""
end = datetime.today()
start = end - timedelta(days=days)
try:
    df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
    if df.empty:
        return None
    df.dropna(inplace=True)
    return df
except Exception as e:
    print(f"[FETCH ERROR] {ticker}: {e}")
    return None


def avg_volume(df, window=20):
"""20-day average volume."""
return df["Volume"].rolling(window).mean().iloc[-1]


def latest_volume(df):
return df["Volume"].iloc[-1]


def is_high_volume(df):
"""True if latest candle is 2x+ average volume."""
av = avg_volume(df)
lv = latest_volume(df)
if av == 0:
    return False
return (lv / av) >= VOLUME_MULTIPLIER


def sma(df, window):
return df["Close"].rolling(window).mean().iloc[-1]


def price_change_pct(df, days=5):
"""% change over last N days."""
if len(df) < days + 1:
    return 0
return ((df["Close"].iloc[-1] - df["Close"].iloc[-(days+1)]) / df["Close"].iloc[-(days+1)]) * 100


def adl(df):
"""
Accumulation/Distribution Line.
ADL = prev_ADL + ((Close - Low) - (High - Close)) / (High - Low) * Volume
Rising ADL + rising price = healthy markup.
Falling ADL + rising price = distribution warning.
"""
clv = ((df["Close"] - df["Low"]) - (df["High"] - df["Close"])) / (df["High"] - df["Low"] + 1e-9)
adl_line = (clv * df["Volume"]).cumsum()
return adl_line


def adl_divergence(df, window=10):
"""
Returns 'distribution' if price rising but ADL falling (last N bars).
Returns 'accumulation' if price falling but ADL rising.
Returns None if no divergence.
"""
if len(df) < window + 1:
    return None
adl_line = adl(df)
price_trend = df["Close"].iloc[-1] - df["Close"].iloc[-window]
adl_trend = adl_line.iloc[-1] - adl_line.iloc[-window]

if price_trend > 0 and adl_trend < 0:
    return "distribution"
elif price_trend < 0 and adl_trend > 0:
    return "accumulation"
return None


def wyckoff_phase(df):
"""
Simplified Wyckoff phase detection.
- Accumulation: price near lows, ADL rising, volume on up days > down days
- Markup: price above 50SMA and 200SMA, ADL rising
- Distribution: price near highs, ADL falling, volume on down days > up days
- Markdown: price below 50SMA and 200SMA, ADL falling
"""
if len(df) < 50:
    return "unknown"

close = df["Close"].iloc[-1]
s50 = sma(df, 50)
s200 = sma(df, 200) if len(df) >= 200 else None
adl_line = adl(df)
adl_rising = adl_line.iloc[-1] > adl_line.iloc[-10]

above_50 = close > s50
above_200 = (close > s200) if s200 else None

if above_50 and (above_200 is None or above_200) and adl_rising:
    return "markup"
elif above_50 and (above_200 is None or above_200) and not adl_rising:
    return "distribution"
elif not above_50 and adl_rising:
    return "accumulation"
else:
    return "markdown"


# ─────────────────────────────────────────────
# CONFLUENCE SCORING ENGINE
# ─────────────────────────────────────────────

def score_signal(asset_class, signal_type, points):
"""Return a scored signal dict."""
return {
    "asset_class": asset_class,
    "signal": signal_type,
    "points": points
}


def run_scan():
signals = []
asset_classes_hit = set()
report_lines = []

# ── 1. MAJOR INDICES ──────────────────────────────────────────────
for ticker in WATCHLIST["indices"]:
    df = fetch(ticker)
    if df is None:
        continue
    phase = wyckoff_phase(df)
    div = adl_divergence(df)
    close = df["Close"].iloc[-1]
    s200 = sma(df, 200) if len(df) >= 200 else None
    chg5 = price_change_pct(df, 5)
    high_vol = is_high_volume(df)

    # SPY/QQQ below 200SMA with high volume = +1
    if s200 and close < s200 and high_vol:
        signals.append(score_signal("indices", f"{ticker} below 200SMA on 2x volume ({close:.2f} < {s200:.2f})", 1))
        asset_classes_hit.add("indices")

    # Distribution phase with ADL divergence = +2
    if phase == "distribution" and div == "distribution":
        signals.append(score_signal("indices", f"{ticker} Wyckoff distribution + ADL divergence (phase: {phase})", 2))
        asset_classes_hit.add("indices")

    # Accumulation phase = +1
    if phase == "accumulation" and div == "accumulation":
        signals.append(score_signal("indices", f"{ticker} Wyckoff accumulation + ADL rising (phase: {phase})", 1))
        asset_classes_hit.add("indices")

    # 5-day drop > 5% on high volume = +2
    if chg5 < -5 and high_vol:
        signals.append(score_signal("indices", f"{ticker} dropped {chg5:.1f}% in 5 days on 2x volume", 2))
        asset_classes_hit.add("indices")

# ── 2. RECESSION & BANKING STRESS ────────────────────────────────
# HYG credit spreads
hyg = fetch("HYG")
if hyg is not None:
    hyg_close = hyg["Close"].iloc[-1]
    hyg_s50 = sma(hyg, 50)
    hyg_high_vol = is_high_volume(hyg)

    if hyg_close < hyg_s50 and hyg_high_vol:
        signals.append(score_signal("macro", f"HYG credit spreads breaking 50SMA ({hyg_close:.2f}) on 2x volume", 2))
        asset_classes_hit.add("macro")
    if hyg_close < KEY_LEVELS["HYG"]["stress"]:
        signals.append(score_signal("macro", f"HYG below stress level ${KEY_LEVELS['HYG']['stress']} ({hyg_close:.2f})", 2))
        asset_classes_hit.add("macro")

# XLF / KRE banking
for ticker in ["XLF", "KRE"]:
    df = fetch(ticker)
    if df is None:
        continue
    chg5 = price_change_pct(df, 5)
    high_vol = is_high_volume(df)
    div = adl_divergence(df)

    if chg5 < -3 and high_vol:
        signals.append(score_signal("banking", f"{ticker} dropped {chg5:.1f}% in 5 days on 2x volume (banking stress)", 2))
        asset_classes_hit.add("banking")
    if div == "distribution":
        signals.append(score_signal("banking", f"{ticker} ADL distribution divergence (smart money exiting banks)", 1))
        asset_classes_hit.add("banking")

# TLT (flight to safety)
tlt = fetch("TLT")
if tlt is not None:
    tlt_chg5 = price_change_pct(tlt, 5)
    tlt_high_vol = is_high_volume(tlt)
    if tlt_chg5 > 3 and tlt_high_vol:
        signals.append(score_signal("macro", f"TLT (bonds) up {tlt_chg5:.1f}% in 5 days on 2x volume (flight to safety)", 2))
        asset_classes_hit.add("macro")

# ── 3. METALS ─────────────────────────────────────────────────────
gld = fetch("GLD")
slv = fetch("SLV")

if gld is not None:
    gld_close = gld["Close"].iloc[-1]
    gld_div = adl_divergence(gld)
    gld_high_vol = is_high_volume(gld)
    gld_chg5 = price_change_pct(gld, 5)

    if gld_close > KEY_LEVELS["GLD"]["breakout"] and gld_high_vol:
        signals.append(score_signal("metals", f"Gold (GLD) breaking key level ${KEY_LEVELS['GLD']['breakout']} on 2x volume ({gld_close:.2f})", 2))
        asset_classes_hit.add("metals")
    if gld_div == "accumulation":
        signals.append(score_signal("metals", f"Gold ADL accumulation divergence (smart money buying dips)", 1))
        asset_classes_hit.add("metals")
    if gld_div == "distribution":
        signals.append(score_signal("metals", f"Gold ADL distribution divergence (smart money exiting at highs)", 2))
        asset_classes_hit.add("metals")

if gld is not None and slv is not None:
    gld_close = gld["Close"].iloc[-1]
    slv_close = slv["Close"].iloc[-1]
    # Gold/Silver Ratio proxy
    gsr = gld_close / slv_close if slv_close > 0 else 0
    if gsr < 75:
        signals.append(score_signal("metals", f"Gold/Silver Ratio at {gsr:.1f} (below 75) - silver leading, risk-on metals signal", 1))
        asset_classes_hit.add("metals")
    if gsr > 90:
        signals.append(score_signal("metals", f"Gold/Silver Ratio at {gsr:.1f} (above 90) - fear trade, gold-only market", 1))
        asset_classes_hit.add("metals")

# ── 4. CRYPTO ─────────────────────────────────────────────────────
btc = fetch("BTC-USD")
eth = fetch("ETH-USD")

if btc is not None:
    btc_close = btc["Close"].iloc[-1]
    btc_chg5 = price_change_pct(btc, 5)
    btc_high_vol = is_high_volume(btc)

    if btc_close > KEY_LEVELS["BTC-USD"]["breakout"] and btc_high_vol:
        signals.append(score_signal("crypto", f"BTC breaking $100K on 2x volume ({btc_close:,.0f}) - euphoria watch", 2))
        asset_classes_hit.add("crypto")
    if btc_close < KEY_LEVELS["BTC-USD"]["breakdown"] and btc_high_vol:
        signals.append(score_signal("crypto", f"BTC below $50K on 2x volume ({btc_close:,.0f}) - accumulation zone or capitulation", 2))
        asset_classes_hit.add("crypto")
    if abs(btc_chg5) > 10 and btc_high_vol:
        direction = "up" if btc_chg5 > 0 else "down"
        signals.append(score_signal("crypto", f"BTC moved {btc_chg5:.1f}% in 5 days ({direction}) on 2x volume", 1))
        asset_classes_hit.add("crypto")

if btc is not None and eth is not None:
    btc_close = btc["Close"].iloc[-1]
    eth_close = eth["Close"].iloc[-1]
    eth_btc_ratio = eth_close / btc_close if btc_close > 0 else 0
    if eth_btc_ratio < 0.03:
        signals.append(score_signal("crypto", f"ETH/BTC ratio at {eth_btc_ratio:.4f} (below 0.03) - ETH severely underperforming, BTC dominance rising", 1))
        asset_classes_hit.add("crypto")

# ── 5. ENERGY ─────────────────────────────────────────────────────
for ticker in ["XLE", "USO"]:
    df = fetch(ticker)
    if df is None:
        continue
    chg5 = price_change_pct(df, 5)
    high_vol = is_high_volume(df)
    s200 = sma(df, 200) if len(df) >= 200 else None
    close = df["Close"].iloc[-1]

    if abs(chg5) > 5 and high_vol:
        direction = "surge" if chg5 > 0 else "drop"
        signals.append(score_signal("energy", f"{ticker} {direction} {chg5:.1f}% in 5 days on 2x volume (geopolitical/supply signal)", 1))
        asset_classes_hit.add("energy")
    if s200 and close < s200 and high_vol:
        signals.append(score_signal("energy", f"{ticker} broke below 200SMA on 2x volume ({close:.2f} < {s200:.2f})", 1))
        asset_classes_hit.add("energy")

# ── 6. DEFENSE ────────────────────────────────────────────────────
ita = fetch("ITA")
if ita is not None:
    ita_close = ita["Close"].iloc[-1]
    ita_52wk_high = ita["Close"].rolling(252).max().iloc[-1]
    ita_high_vol = is_high_volume(ita)
    ita_chg5 = price_change_pct(ita, 5)

    if ita_close >= ita_52wk_high * 0.99 and ita_high_vol:
        signals.append(score_signal("defense", f"ITA (defense ETF) at/near 52-week high on 2x volume ({ita_close:.2f}) - geopolitical escalation signal", 1))
        asset_classes_hit.add("defense")
    if ita_chg5 > 5 and ita_high_vol:
        signals.append(score_signal("defense", f"ITA up {ita_chg5:.1f}% in 5 days on 2x volume", 1))
        asset_classes_hit.add("defense")

# ── 7. DXY (MACRO OVERLAY) ────────────────────────────────────────
dxy = fetch("DX-Y.NYB")
if dxy is not None:
    dxy_close = dxy["Close"].iloc[-1]
    dxy_chg5 = price_change_pct(dxy, 5)

    if dxy_close > 106:
        signals.append(score_signal("macro", f"DXY above 106 ({dxy_close:.2f}) - risk-off pressure on metals/crypto", 1))
        asset_classes_hit.add("macro")
    if dxy_close < 100:
        signals.append(score_signal("macro", f"DXY below 100 ({dxy_close:.2f}) - risk-on, commodities/crypto tailwind", 1))
        asset_classes_hit.add("macro")
    if abs(dxy_chg5) > 2:
        direction = "surging" if dxy_chg5 > 0 else "dropping"
        signals.append(score_signal("macro", f"DXY {direction} {dxy_chg5:.1f}% in 5 days - major liquidity shift", 1))
        asset_classes_hit.add("macro")

# ─────────────────────────────────────────────
# CONFLUENCE GATE
# ─────────────────────────────────────────────

total_points = sum(s["points"] for s in signals)
asset_classes_count = len(asset_classes_hit)

confluence_met = (
    total_points >= CONFLUENCE_THRESHOLD and
    asset_classes_count >= ASSET_CLASS_MINIMUM
)

return signals, total_points, asset_classes_hit, confluence_met


# ─────────────────────────────────────────────
# REPORT BUILDER
# ─────────────────────────────────────────────

def build_report(signals, total_points, asset_classes_hit, confluence_met):
lines = []
lines.append(f"WYCKOFF SMART MONEY SCAN - {SCAN_DATE}")
lines.append("=" * 50)
lines.append(f"Confluence Score: {total_points} pts | Asset Classes: {len(asset_classes_hit)} | Threshold: {CONFLUENCE_THRESHOLD}+ pts / {ASSET_CLASS_MINIMUM}+ classes")
lines.append("")

if not confluence_met:
    lines.append("No high-confluence signals this week - patience compounds.")
    lines.append("")
    lines.append(f"Signals scanned: {len(signals)} sub-threshold signals detected.")
    lines.append("None met the 3+ confluence / 2+ asset class requirement.")
    lines.append("")
    lines.append("Watching: SPY 200SMA, Gold key levels, BTC.D, HYG credit spreads, DXY.")
    return "\n".join(lines)

# Group by asset class
by_class = {}
for s in signals:
    ac = s["asset_class"]
    if ac not in by_class:
        by_class[ac] = []
    by_class[ac].append(s)

class_labels = {
    "indices": "MAJOR INDICES",
    "macro": "MACRO / RECESSION SIGNALS",
    "banking": "BANKING STRESS",
    "metals": "METALS",
    "crypto": "CRYPTO",
    "energy": "ENERGY",
    "defense": "DEFENSE",
}

for ac, label in class_labels.items():
    if ac in by_class:
        lines.append(f"[ {label} ]")
        for s in by_class[ac]:
            lines.append(f"  - {s['signal']} (+{s['points']} pts)")
        lines.append("")

lines.append("-" * 50)
lines.append(f"TOTAL CONFLUENCE SCORE: {total_points} pts across {len(asset_classes_hit)} asset classes")
lines.append("")

# Playbook
lines.append("PLAYBOOK:")
if "metals" in asset_classes_hit and "macro" in asset_classes_hit:
    lines.append("  - Metals + macro confluence: consider scaling GLD/SLV position or adding physical gold exposure.")
if "crypto" in asset_classes_hit and "macro" in asset_classes_hit:
    lines.append("  - Crypto + macro confluence: BTC accumulation zone or liquidity-driven rally - watch BTC.D for alt rotation signal.")
if "banking" in asset_classes_hit or "macro" in asset_classes_hit:
    lines.append("  - Recession signals building: rotate toward TLT, GLD, XLU (utilities), XLP (staples). Reduce speculative exposure.")
if "energy" in asset_classes_hit:
    lines.append("  - Energy signal: geopolitical or supply shock in play - monitor oil for follow-through.")
if "defense" in asset_classes_hit:
    lines.append("  - Defense signal: geopolitical escalation risk elevated - ITA/LMT worth watching.")

lines.append("")
lines.append("QUESTIONS TO SIT WITH:")
lines.append("  1. Are the signals pointing toward a liquidity-driven rally or a fear-driven flight to safety?")
lines.append("  2. Is the smart money accumulating hard assets (gold, BTC) ahead of a macro shift - or distributing into retail strength?")

return "\n".join(lines)


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":
print(f"Running Wyckoff High-Confluence Scanner - {SCAN_DATE}")
signals, total_points, asset_classes_hit, confluence_met = run_scan()
report = build_report(signals, total_points, asset_classes_hit, confluence_met)
print(report)

# Output to file for GitHub Actions / Lindy pickup
output_path = os.path.join(os.path.dirname(__file__), "..", "data", "wyckoff_scan_latest.txt")
with open(output_path, "w") as f:
    f.write(report)
print(f"\nReport saved to {output_path}")
