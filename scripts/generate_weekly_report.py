#!/usr/bin/env python3
"""
Weekly Market Report Generator
Reads data.json + ai_insights.json and produces a markdown brief
Runs every Sunday 6am UTC via GitHub Actions
"""

import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = REPO_ROOT / "data" / "data.json"
AI_INSIGHTS_FILE = REPO_ROOT / "data" / "ai_insights.json"
REPORTS_DIR = REPO_ROOT / "reports"


def load_json(path):
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def pct_change(current, reference):
    """Return formatted % change string"""
    if not current or not reference or reference == 0:
        return "N/A"
    change = ((current - reference) / reference) * 100
    sign = "+" if change >= 0 else ""
    return f"{sign}{change:.1f}%"


def posture_emoji(posture):
    mapping = {
        "RISK-ON": "RISK-ON",
        "WATCH-ONLY": "WATCH-ONLY",
        "DEFENSIVE": "DEFENSIVE",
        "SELECTIVE": "SELECTIVE",
    }
    return mapping.get(posture, posture or "UNKNOWN")


def wyckoff_section(wyckoff):
    if not wyckoff:
        return "_Wyckoff data not available this week._\n"

    alerts = wyckoff.get("active_alerts", [])
    if not alerts:
        return "_No high-confidence Wyckoff signals active._\n"

    lines = []
    for a in alerts[:5]:  # Top 5 alerts
        key = a.get("key", "").upper()
        phase = a.get("phase", "UNKNOWN")
        conf = a.get("confidence", 0)
        alert_type = a.get("alert_type", "")
        tag = f" [{alert_type}]" if alert_type else ""
        lines.append(f"- **{key}**: {phase} ({conf}% confidence){tag}")

    return "\n".join(lines) + "\n"


def ai_section(insights):
    if not insights:
        return "_AI insights not available._\n"

    summary = insights.get("weekly_brief", insights.get("executive_summary", ""))
    if not summary:
        summary = insights.get("market_summary", "")

    confluence = insights.get("confluence", {})
    score = confluence.get("score", "N/A") if isinstance(confluence, dict) else "N/A"
    posture = confluence.get("posture", "UNKNOWN") if isinstance(confluence, dict) else "UNKNOWN"

    lines = [f"**Confluence Score:** {score}  |  **Posture:** {posture}"]
    if summary:
        lines.append(f"\n{summary}")

    return "\n".join(lines) + "\n"


def macro_snapshot(macro):
    if not macro:
        return "_Macro data unavailable._\n"

    spx = macro.get("spx", "N/A")
    dxy = macro.get("dxy", "N/A")
    us10y = macro.get("us10y_yield", "N/A")
    fed = macro.get("fed_funds_rate", "N/A")
    cpi = macro.get("cpi_yoy", "N/A")
    nfp = macro.get("nfp_change", "N/A")
    unemployment = macro.get("unemployment_rate", "N/A")

    lines = [
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| S&P 500 | {spx} |",
        f"| DXY | {dxy} |",
        f"| 10Y Treasury | {us10y}% |",
        f"| Fed Funds Rate | {fed}% |",
        f"| CPI YoY | {cpi}% |",
        f"| NFP Change | {nfp:+,.0f}" + " jobs |" if isinstance(nfp, (int, float)) else f"| NFP Change | {nfp} |",
        f"| Unemployment | {unemployment}% |",
    ]
    return "\n".join(lines) + "\n"


def crypto_snapshot(crypto):
    if not crypto:
        return "_Crypto data unavailable._\n"

    btc = crypto.get("btc_usd", "N/A")
    eth = crypto.get("eth_usd", "N/A")
    btc_rsi = crypto.get("btc_rsi", "N/A")
    eth_rsi = crypto.get("eth_rsi", "N/A")
    phase = crypto.get("cycle_phase", "N/A")
    fear_greed = crypto.get("fear_greed_index", "N/A")

    btc_fmt = f"${btc:,.0f}" if isinstance(btc, (int, float)) else str(btc)
    eth_fmt = f"${eth:,.0f}" if isinstance(eth, (int, float)) else str(eth)

    lines = [
        f"| Asset | Price | RSI |",
        f"|-------|-------|-----|",
        f"| BTC | {btc_fmt} | {btc_rsi} |",
        f"| ETH | {eth_fmt} | {eth_rsi} |",
        f"",
        f"**Cycle Phase:** {phase}  |  **Fear & Greed:** {fear_greed}",
    ]
    return "\n".join(lines) + "\n"


def trigger_section(triggers):
    if not triggers:
        return "_No active triggers._\n"

    lines = []
    for t in triggers[:6]:
        if isinstance(t, dict):
            name = t.get("name", t.get("trigger", str(t)))
            status = t.get("status", "")
            lines.append(f"- {name}" + (f" — {status}" if status else ""))
        else:
            lines.append(f"- {t}")

    return "\n".join(lines) + "\n"


def main():
    now = datetime.now(timezone.utc)
    week_str = now.strftime("%Y-W%W")
    date_str = now.strftime("%Y-%m-%d")

    data = load_json(DATA_FILE)
    insights = load_json(AI_INSIGHTS_FILE)

    macro = data.get("macro", {})
    crypto = data.get("crypto", {})
    gate = data.get("decision_gate", {})
    wyckoff = data.get("wyckoff", {})
    triggers = data.get("triggers", [])
    bias = data.get("bias", "Neutral")
    posture = gate.get("risk_posture", "UNKNOWN")
    gate_score = gate.get("confluence_score", gate.get("score", "N/A"))

    report = f"""# CaliEye Weekly Market Brief — {date_str}

**Week:** {week_str}
**Generated:** {now.strftime("%Y-%m-%d %H:%M UTC")}
**Overall Bias:** {bias}
**Decision Gate:** {posture_emoji(posture)} (Score: {gate_score})

---

## Market Snapshot

### Macro Indicators
{macro_snapshot(macro)}

### Crypto
{crypto_snapshot(crypto)}

---

## Decision Gate — Active Triggers
{trigger_section(triggers)}

---

## Wyckoff Phase Signals
{wyckoff_section(wyckoff)}

---

## AI Confluence Summary
{ai_section(insights)}

---

## Week-in-Review Notes

> _Auto-generated weekly brief. Review active alerts in dashboard for real-time signals._
> _Next full review: {now.strftime("%Y-%m-%d")} + 7 days_

---
*CaliEye Investor Dashboard — Endgame 2030*
"""

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_file = REPORTS_DIR / f"weekly_{date_str}.md"

    with report_file.open("w", encoding="utf-8") as f:
        f.write(report)

    # Keep index of latest report
    index_file = REPORTS_DIR / "latest.md"
    with index_file.open("w", encoding="utf-8") as f:
        f.write(report)

    print(f"Weekly report written: {report_file}")
    print(f"Latest report symlink: {index_file}")


if __name__ == "__main__":
    main()
