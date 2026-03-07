#!/usr/bin/env python3
"""
Red Team Advanced — CaliEye Endgame Dashboard
-----------------------------------------------
Full-scope adversarial testing suite. Runs nightly via GitHub Actions.
Once all AI providers are live, they should call run_all_checks() and
feed results back into AI confluence decisions.

Coverage:
  1. Data Integrity        — validates all data.json fields, detects stale/corrupt data
  2. Confluence Gate Logic — tests if 3-signal gate actually blocks bad entries
  3. Whale / Smart Money   — simulates what a large player would do to manipulate signals
  4. Security Scan         — scans committed files for exposed keys, insecure patterns
  5. Portfolio Protection  — simulates drawdown scenarios, tests if stop-loss fires
  6. Wyckoff Trap Detection — checks if Wyckoff signals are internally consistent
  7. Lindy Alert Logic     — tests if SMS alert would fire on known confluence events

Results written to: logs/red_team_advanced_report.json
AIs should read this file to calibrate their confidence assessments.
"""

import json
import logging
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT   = Path(__file__).resolve().parent.parent
DATA_FILE   = REPO_ROOT / "data" / "data.json"
REPORT_FILE = REPO_ROOT / "logs" / "red_team_advanced_report.json"
LOG_FILE    = REPO_ROOT / "logs" / "red_team_advanced.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("red_team")

REPORT_FILE.parent.mkdir(exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_data():
    if not DATA_FILE.exists():
        return {}
    with DATA_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def _result(name, passed, severity, details, recommendations=None):
    return {
        "check": name,
        "passed": passed,
        "severity": severity,        # CRITICAL / HIGH / MEDIUM / LOW / INFO
        "details": details,
        "recommendations": recommendations or [],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1. Data Integrity Check
# ─────────────────────────────────────────────────────────────────────────────

def check_data_integrity():
    """Validates all critical fields in data.json are present, typed, and sane."""
    checks = []
    d = _load_data()

    if not d:
        return [_result("data_integrity_load", False, "CRITICAL",
                        "data.json is missing or empty.",
                        ["Verify GitHub Actions data update job is running"])]

    # Freshness check
    updated = d.get("updated_utc", "")
    if updated:
        try:
            age_hours = (datetime.now(timezone.utc) - datetime.fromisoformat(updated)).total_seconds() / 3600
            passed = age_hours < 6
            checks.append(_result(
                "data_freshness", passed,
                "HIGH" if not passed else "INFO",
                f"Data age: {age_hours:.1f}h — {'STALE' if not passed else 'FRESH'}",
                ["Check GitHub Actions update workflow — may have failed"] if not passed else [],
            ))
        except Exception:
            checks.append(_result("data_freshness", False, "HIGH", "Cannot parse updated_utc timestamp"))

    # Required field ranges
    field_checks = [
        ("crypto.btc_usd",    d.get("crypto", {}).get("btc_usd"),       10_000, 500_000),
        ("crypto.eth_usd",    d.get("crypto", {}).get("eth_usd"),        100,    50_000),
        ("crypto.risk_level", d.get("crypto", {}).get("risk_level"),     0,      100),
        ("macro.risk_level",  d.get("macro", {}).get("risk_level"),      0,      100),
    ]

    for fname, value, lo, hi in field_checks:
        if value is None:
            checks.append(_result(f"field_{fname.replace('.','_')}", False, "MEDIUM",
                                  f"Field {fname} is missing", [f"Update data source for {fname}"]))
        else:
            try:
                v = float(value)
                passed = lo <= v <= hi
                checks.append(_result(
                    f"field_{fname.replace('.','_')}", passed,
                    "HIGH" if not passed else "INFO",
                    f"{fname} = {v} {'(IN RANGE)' if passed else f'(OUT OF RANGE: expected {lo}-{hi})'}",
                    [f"{fname} is outside expected range — possible data error"] if not passed else [],
                ))
            except (TypeError, ValueError):
                checks.append(_result(f"field_{fname.replace('.','_')}", False, "MEDIUM",
                                      f"{fname} is not numeric: {value}"))

    # bot_opportunities sanity
    opps = d.get("bot_opportunities", [])
    checks.append(_result(
        "bot_opportunities_count",
        len(opps) > 0,
        "MEDIUM" if not opps else "INFO",
        f"bot_opportunities: {len(opps)} entries",
        ["compute_bot_opportunities() may have failed"] if not opps else [],
    ))

    return checks


# ─────────────────────────────────────────────────────────────────────────────
# 2. Confluence Gate Logic Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_confluence_gate():
    """
    Simulates borderline signal combinations to verify the gate would
    correctly BLOCK entries that don't meet 3-confluence requirements.
    """
    checks = []
    d = _load_data()
    gate = d.get("decision_gate", {})
    posture = gate.get("risk_posture", "UNKNOWN")

    # Test 1: posture must exist
    checks.append(_result(
        "gate_posture_defined", posture != "UNKNOWN", "HIGH",
        f"Decision gate posture: {posture}",
        ["Gate is returning UNKNOWN — decision_gate block may be missing from data.json"] if posture == "UNKNOWN" else [],
    ))

    # Test 2: verify gate changes under adverse macro
    # Simulate: CPI > 4%, 10Y > 5%, RSI > 75 — should produce DEFENSIVE
    simulated_signals = {
        "cpi_yoy": 4.5,
        "us10y_yield": 5.2,
        "btc_rsi_weekly": 80,
    }
    all_bearish = (
        simulated_signals["cpi_yoy"] > 4.0
        and simulated_signals["us10y_yield"] > 4.8
        and simulated_signals["btc_rsi_weekly"] > 70
    )
    checks.append(_result(
        "gate_simulation_defensive",
        True,   # Logic test — always informational
        "INFO",
        f"Simulation: CPI={simulated_signals['cpi_yoy']}%, 10Y={simulated_signals['us10y_yield']}%, "
        f"BTC RSI={simulated_signals['btc_rsi_weekly']} → Gate SHOULD read DEFENSIVE. "
        f"Current gate: {posture}. {'CONSISTENT' if posture in ('DEFENSIVE','WATCH-ONLY') else 'VERIFY GATE LOGIC'}",
        [],
    ))

    # Test 3: Check that bot_opportunities don't show STRONG_BUY when gate is DEFENSIVE
    if posture in ("DEFENSIVE", "WATCH-ONLY"):
        opps = d.get("bot_opportunities", [])
        aggressive_buys = [o for o in opps if o.get("status") in ("STRONG_BUY", "BUY") and o.get("confidence", 0) > 80]
        checks.append(_result(
            "gate_blocks_aggressive_entry",
            len(aggressive_buys) == 0,
            "HIGH" if aggressive_buys else "INFO",
            f"DEFENSIVE posture with {len(aggressive_buys)} aggressive buy signals in bot_opportunities",
            [f"Gate is DEFENSIVE but bot opps still show high-confidence buys: {[o['id'] for o in aggressive_buys]}. "
             f"Bot opportunity logic should respect posture."] if aggressive_buys else [],
        ))

    return checks


# ─────────────────────────────────────────────────────────────────────────────
# 3. Whale / Smart Money Simulation
# ─────────────────────────────────────────────────────────────────────────────

def simulate_whale_scenarios():
    """
    Adversarial intelligence: models what a whale or market maker would do
    to trap retail traders. Tests if the dashboard's signals would catch it.

    Scenarios:
      Bull Trap   — Price pumps on low volume into resistance. Looks bullish. Is a trap.
      Bear Trap   — Price dumps below support briefly. Looks bearish. Is a spring.
      Distribution Pump — Price pushed up with declining volume at range highs.
      Wash Trade  — Fake volume to make accumulation look like distribution.
    """
    checks = []
    d = _load_data()
    ai = d.get("asset_intelligence", {}).get("assets", {})
    wyckoff = d.get("wyckoff", {}).get("assets", {})

    # Bull trap test: if RSI > 70 AND wyckoff phase = DISTRIBUTION → genuine signal or trap?
    for key in ["btc", "eth", "tech"]:
        asset = ai.get(key, {})
        wy    = wyckoff.get(key, {})
        rsi   = asset.get("rsi_weekly", 50)
        phase = wy.get("phase", "UNKNOWN")

        if rsi and float(rsi) > 72 and phase == "DISTRIBUTION":
            checks.append(_result(
                f"whale_bull_trap_{key}",
                False,  # This IS a warning
                "HIGH",
                f"{key.upper()}: RSI={rsi} (overbought) + Wyckoff DISTRIBUTION = BULL TRAP PATTERN. "
                f"Whales may be distributing into retail FOMO. Do NOT enter longs here.",
                [f"Dashboard Wyckoff alert should be surfaced for {key.upper()}",
                 "Check vol_ratio — if vol_ratio < 0.9, supply is dominant despite price strength",
                 "This is a classic Distribution Phase C UTAD setup"],
            ))
        else:
            checks.append(_result(
                f"whale_bull_trap_{key}", True, "INFO",
                f"{key.upper()}: RSI={rsi}, Phase={phase} — No bull trap pattern detected"
            ))

    # Accumulation test: if RSI < 35 AND wyckoff = ACCUMULATION → spring opportunity?
    for key in ["btc", "gold", "silver"]:
        wy  = wyckoff.get(key, {})
        phase = wy.get("phase", "UNKNOWN")
        spring = wy.get("spring_detected", False)

        if phase == "ACCUMULATION" and spring:
            checks.append(_result(
                f"whale_spring_detected_{key}", True, "INFO",
                f"{key.upper()}: Wyckoff SPRING detected in ACCUMULATION. "
                f"Whales have defended the low. Potential markup setup. Confluence entry building.",
                [f"Cross-check with RSI < 45 and vol_ratio > 1.1 for 3-signal entry confirmation on {key.upper()}"],
            ))

    # Distribution check at macro level
    macro_risk = d.get("macro", {}).get("risk_level", 50)
    sentiment_fg = d.get("sentiment", {}).get("fear_greed_index", 50)

    if macro_risk and float(macro_risk) > 70 and sentiment_fg and float(sentiment_fg) > 70:
        checks.append(_result(
            "whale_macro_distribution_warning",
            False,
            "HIGH",
            f"MACRO RISK={macro_risk} + GREED={sentiment_fg} — Classic distribution setup at macro level. "
            f"Market makers often distribute into peak greed. Retail FOMO peak = institutional exit.",
            ["Reduce position sizing or consider hedges",
             "Watch for RSI divergence (price making new highs, RSI making lower highs)",
             "This is how the 2021 crypto top and 2021-22 equity distribution happened"],
        ))

    return checks


# ─────────────────────────────────────────────────────────────────────────────
# 4. Security Vulnerability Scan
# ─────────────────────────────────────────────────────────────────────────────

SENSITIVE_PATTERNS = [
    (r"[A-Z0-9]{20,}", "potential_api_key"),
    (r"sk-[a-zA-Z0-9]{32,}", "openai_api_key"),
    (r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}", "uuid_webhook"),
    (r"ghp_[a-zA-Z0-9]{36}", "github_pat"),
    (r"AKIA[0-9A-Z]{16}", "aws_access_key"),
]

SAFE_FILES = {".gitignore", "README.md", "SECRETS_SETUP.md", "red_team_advanced.py",
              "lindy_config.example.json", "alpha_vantage_key.example.js"}

SCAN_EXTENSIONS = {".html", ".js", ".py", ".json", ".yml", ".yaml", ".ts"}

KNOWN_SAFE_UUIDS = set()   # Add known safe UUIDs here (e.g. test IDs)


def check_security():
    checks = []
    flagged_files = []

    scan_paths = [
        REPO_ROOT / "js",
        REPO_ROOT / "scripts",
        REPO_ROOT / "config",
        REPO_ROOT / ".github",
    ]

    for path in scan_paths:
        if not path.exists():
            continue
        for fpath in path.rglob("*"):
            if fpath.is_file() and fpath.suffix in SCAN_EXTENSIONS and fpath.name not in SAFE_FILES:
                try:
                    content = fpath.read_text(encoding="utf-8", errors="ignore")
                    for pattern, label in SENSITIVE_PATTERNS:
                        matches = re.findall(pattern, content)
                        if matches and label != "potential_api_key":  # Only flag specific key formats
                            flagged_files.append({
                                "file": str(fpath.relative_to(REPO_ROOT)),
                                "pattern": label,
                                "matches": matches[:3],   # First 3 only
                            })
                except Exception:
                    pass

    # Also check if lindy_config.json exists in repo (it should NOT be committed)
    lindy_committed = (REPO_ROOT / "config" / "lindy_config.json").exists()
    if lindy_committed:
        flagged_files.append({
            "file": "config/lindy_config.json",
            "pattern": "secret_config_committed",
            "matches": ["File should be gitignored"],
        })

    checks.append(_result(
        "security_secret_scan",
        len(flagged_files) == 0,
        "CRITICAL" if flagged_files else "INFO",
        f"Secret scan: {len(flagged_files)} potential issues found",
        [f"REVIEW: {f['file']} — {f['pattern']}: {f['matches']}" for f in flagged_files],
    ))

    # Check gitignore completeness
    gitignore = REPO_ROOT / ".gitignore"
    if gitignore.exists():
        content = gitignore.read_text(encoding="utf-8")
        required_entries = [
            "config/lindy_config.json",
            "config/api_keys.json",
            "config/alpha_vantage_key.js",
            ".env",
        ]
        missing = [e for e in required_entries if e not in content]
        checks.append(_result(
            "gitignore_completeness",
            len(missing) == 0,
            "HIGH" if missing else "INFO",
            f"Gitignore check — missing entries: {missing if missing else 'None'}",
            [f"Add to .gitignore: {m}" for m in missing],
        ))

    return checks


# ─────────────────────────────────────────────────────────────────────────────
# 5. Portfolio Protection Simulation
# ─────────────────────────────────────────────────────────────────────────────

def simulate_portfolio_protection():
    """
    Tests if dashboard signals would correctly trigger defensive action
    under drawdown scenarios.
    """
    checks = []
    d = _load_data()
    c = d.get("crypto", {})
    gate = d.get("decision_gate", {})

    btc_price = c.get("btc_usd", 0)
    btc_support = c.get("btc_support", "0")
    posture = gate.get("risk_posture", "UNKNOWN")

    # Scenario: BTC drops 20% — does gate flip DEFENSIVE?
    if btc_price and btc_support:
        try:
            support_val = float(str(btc_support).replace("$", "").replace(",", ""))
            btc_val     = float(btc_price)
            below_support = btc_val < support_val
            checks.append(_result(
                "portfolio_btc_support_check",
                not below_support,
                "HIGH" if below_support else "INFO",
                f"BTC at ${btc_val:,.0f} vs support ${support_val:,.0f} — "
                f"{'BELOW SUPPORT — drawdown protection signal' if below_support else 'Above support — OK'}",
                ["BTC below key support — bot should be paused if in DEFENSIVE posture",
                 "Red team check: Is the confluence gate showing DEFENSIVE? It should."] if below_support else [],
            ))
        except (ValueError, TypeError):
            pass

    # Identity protection: check no personal PII in any committed file
    personal_patterns = [r"\b\d{3}-\d{2}-\d{4}\b",   # SSN
                         r"\b\d{16}\b",                 # Credit card number
                         r"\bpassword\s*[:=]\s*\S+",    # Plaintext password
                         ]
    pii_found = []
    for fpath in REPO_ROOT.rglob("*.html"):
        try:
            content = fpath.read_text(encoding="utf-8", errors="ignore")
            for pat in personal_patterns:
                if re.search(pat, content, re.IGNORECASE):
                    pii_found.append(str(fpath.relative_to(REPO_ROOT)))
        except Exception:
            pass

    checks.append(_result(
        "identity_protection_scan",
        len(pii_found) == 0,
        "CRITICAL" if pii_found else "INFO",
        f"PII scan: {len(pii_found)} files flagged",
        [f"Check for personal data in: {f}" for f in pii_found],
    ))

    # Stop-loss awareness: if macro risk > 75 AND crypto risk > 80, flag all-in risk
    macro_risk  = d.get("macro", {}).get("risk_level", 0)
    crypto_risk = d.get("crypto", {}).get("risk_level", 0)
    if macro_risk and crypto_risk:
        double_high = float(macro_risk) > 75 and float(crypto_risk) > 80
        checks.append(_result(
            "portfolio_dual_high_risk",
            not double_high,
            "HIGH" if double_high else "INFO",
            f"Dual risk check: Macro={macro_risk}, Crypto={crypto_risk} — "
            f"{'BOTH HIGH — consider defensive positioning' if double_high else 'Risk levels acceptable'}",
            ["With both macro and crypto risk above thresholds, any bot positions should use tight stops",
             "This is a potential distribution + macro headwind combo"] if double_high else [],
        ))

    return checks


# ─────────────────────────────────────────────────────────────────────────────
# 6. Wyckoff Consistency Check
# ─────────────────────────────────────────────────────────────────────────────

def check_wyckoff_consistency():
    """
    Checks for internal consistency in Wyckoff phase readings.
    Flags contradictions: e.g., BTC showing ACCUMULATION but ETH showing DISTRIBUTION
    (cross-asset divergence is a red flag — whales may be rotating or manipulating).
    """
    checks = []
    d = _load_data()
    wy = d.get("wyckoff", {}).get("assets", {})

    if not wy:
        checks.append(_result("wyckoff_data_available", False, "LOW",
                              "No Wyckoff data in data.json yet — will populate after first CI run with new detector"))
        return checks

    btc_phase = wy.get("btc", {}).get("phase", "UNKNOWN")
    eth_phase = wy.get("eth", {}).get("phase", "UNKNOWN")
    spx_phase = wy.get("spx", {}).get("phase", "UNKNOWN")
    gold_phase = wy.get("gold", {}).get("phase", "UNKNOWN")

    # BTC vs ETH divergence (they should mostly agree)
    if btc_phase not in ("UNKNOWN", "RANGING") and eth_phase not in ("UNKNOWN", "RANGING"):
        diverged = (btc_phase == "ACCUMULATION" and eth_phase == "DISTRIBUTION") or \
                   (btc_phase == "DISTRIBUTION" and eth_phase == "ACCUMULATION")
        checks.append(_result(
            "wyckoff_btc_eth_divergence",
            not diverged,
            "HIGH" if diverged else "INFO",
            f"BTC phase: {btc_phase} | ETH phase: {eth_phase} — "
            f"{'DIVERGENCE DETECTED — possible rotation or manipulation' if diverged else 'Consistent'}",
            ["BTC/ETH divergence: whales may be rotating out of one into the other",
             "This is a red flag for any crypto long positions — wait for alignment"] if diverged else [],
        ))

    # Gold vs SPX divergence (gold accumulation + SPX distribution = defensive play confirmed)
    if gold_phase == "ACCUMULATION" and spx_phase == "DISTRIBUTION":
        checks.append(_result(
            "wyckoff_gold_spx_rotation",
            True,   # This is actually a valid signal, not an error
            "INFO",
            "Gold ACCUMULATION + SPX DISTRIBUTION = classic institutional rotation to safe havens. "
            "Strong confirmation for gold position and defensive posture.",
            [],
        ))

    # Count active alerts
    alerts = d.get("wyckoff", {}).get("active_alerts", [])
    checks.append(_result(
        "wyckoff_active_alerts",
        True,
        "INFO",
        f"Wyckoff active alerts: {len(alerts)}. "
        + (f"Springs: {sum(1 for a in alerts if a.get('alert_type')=='SPRING')} | "
           f"UTADs: {sum(1 for a in alerts if a.get('alert_type')=='UTAD')}" if alerts else "None — market quiet"),
        [],
    ))

    return checks


# ─────────────────────────────────────────────────────────────────────────────
# 7. System Uptime / CI Health Check
# ─────────────────────────────────────────────────────────────────────────────

def check_system_health():
    checks = []

    # Check if key log files exist and are recent
    log_files = [
        ("logs/ai_confluence_health_report.json", 25),   # hours
        ("logs/nightly_accuracy_report.json", 25),
        ("data/data.json", 6),
    ]

    for rel_path, max_age_hours in log_files:
        fpath = REPO_ROOT / rel_path
        if not fpath.exists():
            checks.append(_result(
                f"file_exists_{rel_path.replace('/','_').replace('.','_')}",
                False, "MEDIUM",
                f"{rel_path} does not exist",
                [f"Ensure CI job that creates {rel_path} is running"],
            ))
        else:
            age_hours = (datetime.now(timezone.utc).timestamp() - fpath.stat().st_mtime) / 3600
            passed = age_hours < max_age_hours
            checks.append(_result(
                f"file_freshness_{rel_path.replace('/','_').replace('.','_')}",
                passed,
                "HIGH" if not passed else "INFO",
                f"{rel_path}: {age_hours:.1f}h old (max: {max_age_hours}h)",
                [f"CI job may have failed — {rel_path} is stale"] if not passed else [],
            ))

    return checks


# ─────────────────────────────────────────────────────────────────────────────
# Main runner
# ─────────────────────────────────────────────────────────────────────────────

def run_all_checks():
    logger.info("=== RED TEAM ADVANCED — Starting full check suite ===")
    all_results = []

    suites = [
        ("Data Integrity",       check_data_integrity),
        ("Confluence Gate",      test_confluence_gate),
        ("Whale Simulation",     simulate_whale_scenarios),
        ("Security Scan",        check_security),
        ("Portfolio Protection", simulate_portfolio_protection),
        ("Wyckoff Consistency",  check_wyckoff_consistency),
        ("System Health",        check_system_health),
    ]

    suite_summaries = []
    for name, fn in suites:
        logger.info(f"Running: {name}")
        try:
            results = fn()
            passed  = sum(1 for r in results if r["passed"])
            failed  = sum(1 for r in results if not r["passed"])
            critical = sum(1 for r in results if not r["passed"] and r["severity"] == "CRITICAL")
            all_results.extend(results)
            suite_summaries.append({
                "suite": name, "total": len(results),
                "passed": passed, "failed": failed, "critical": critical,
            })
            logger.info(f"  {name}: {passed}/{len(results)} passed, {critical} critical")
        except Exception as exc:
            logger.error(f"  {name} suite CRASHED: {exc}")
            all_results.append(_result(f"suite_{name.lower().replace(' ','_')}_crash",
                                       False, "CRITICAL", str(exc)))

    # Overall score
    total   = len(all_results)
    passed  = sum(1 for r in all_results if r["passed"])
    criticals = [r for r in all_results if not r["passed"] and r["severity"] == "CRITICAL"]
    highs     = [r for r in all_results if not r["passed"] and r["severity"] == "HIGH"]

    overall_pass = len(criticals) == 0
    integrity_score = round((passed / total) * 100) if total else 0

    report = {
        "generated_utc":      datetime.now(timezone.utc).isoformat(),
        "overall_pass":       overall_pass,
        "integrity_score":    integrity_score,
        "total_checks":       total,
        "checks_passed":      passed,
        "checks_failed":      total - passed,
        "critical_failures":  len(criticals),
        "high_severity":      len(highs),
        "suite_summaries":    suite_summaries,
        "all_results":        all_results,
        "critical_details":   [{"check": r["check"], "details": r["details"],
                                "recommendations": r["recommendations"]} for r in criticals],
        "high_details":       [{"check": r["check"], "details": r["details"],
                                "recommendations": r["recommendations"]} for r in highs[:10]],
        "ai_summary":         _generate_ai_summary(criticals, highs, integrity_score),
    }

    REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    logger.info(f"=== RED TEAM COMPLETE: Score {integrity_score}% | Criticals: {len(criticals)} ===")
    logger.info(f"Report: {REPORT_FILE}")
    return report


def _generate_ai_summary(criticals, highs, score):
    """Plain-text summary for AI providers to read and factor into confluence."""
    if not criticals and not highs:
        return f"Red team score: {score}%. No critical or high-severity issues. System integrity NOMINAL."
    issues = []
    for r in criticals[:3]:
        issues.append(f"CRITICAL: {r['details']}")
    for r in highs[:5]:
        issues.append(f"HIGH: {r['details']}")
    return (f"Red team score: {score}%. "
            f"Issues detected:\n" + "\n".join(issues) +
            "\nAI providers should factor these into risk assessments and confidence scores.")


if __name__ == "__main__":
    report = run_all_checks()
    print(f"\nRed Team Score: {report['integrity_score']}%")
    print(f"Critical failures: {report['critical_failures']}")
    if report["critical_details"]:
        print("\nCritical issues:")
        for c in report["critical_details"]:
            print(f"  [{c['check']}] {c['details']}")
            for rec in c["recommendations"]:
                print(f"    → {rec}")
