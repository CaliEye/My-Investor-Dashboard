#!/usr/bin/env python3
"""Nightly data accuracy check.

Runs full dashboard checks, validates critical market fields, and stores a nightly report.
Exit code 0 only when all accuracy checks pass.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = REPO_ROOT / "data" / "data.json"
AI_FILE = REPO_ROOT / "data" / "ai_insights.json"
CONFLUENCE_FILE = REPO_ROOT / "data" / "confluence_alerts.json"
SNAPSHOT_FILE = REPO_ROOT / "data" / "nightly_accuracy_snapshot.json"
REPORT_FILE = REPO_ROOT / "logs" / "nightly_accuracy_report.json"
REPORT_MD_FILE = REPO_ROOT / "logs" / "nightly_accuracy.md"
FAIL_FLAG_FILE = REPO_ROOT / "logs" / "nightly_accuracy_failed.flag"
ALERT_TXT_FILE = REPO_ROOT / "logs" / "nightly_accuracy_alert.txt"
LINDY_BRIEF_FILE = REPO_ROOT / "logs" / "lindy_morning_brief.txt"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def parse_numeric(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    token = []
    dot = False
    sign = True
    for ch in text:
        if ch in "+-" and sign:
            token.append(ch)
            sign = False
            continue
        sign = False
        if ch.isdigit():
            token.append(ch)
            continue
        if ch == "." and not dot:
            token.append(ch)
            dot = True
            continue
        if token:
            break
    candidate = "".join(token)
    if not candidate or candidate in {"+", "-", ".", "+.", "-."}:
        return None
    try:
        return float(candidate)
    except ValueError:
        return None


def iso_age_minutes(ts: str) -> int:
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return int((datetime.now(timezone.utc) - dt).total_seconds() / 60)


def run_full_dashboard_check() -> tuple[int, str]:
    command = [sys.executable, str(REPO_ROOT / "scripts" / "full_dashboard_check.py")]
    proc = subprocess.run(command, cwd=str(REPO_ROOT), capture_output=True, text=True)
    output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return proc.returncode, output


def run_anti_ai_red_team() -> tuple[int, str]:
    command = [sys.executable, str(REPO_ROOT / "scripts" / "anti_ai_red_team.py")]
    proc = subprocess.run(command, cwd=str(REPO_ROOT), capture_output=True, text=True)
    output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return proc.returncode, output


def load_latest_json(logs_dir: Path, pattern: str) -> dict[str, Any] | None:
    matches = sorted(logs_dir.glob(pattern), key=lambda p: p.stat().st_mtime)
    if not matches:
        return None
    try:
        return load_json(matches[-1])
    except (json.JSONDecodeError, OSError):
        return None


def build_lindy_brief(logs_dir: Path) -> str | None:
    vulnerability = load_latest_json(logs_dir, "vulnerability_report_*.json")
    manipulation = load_latest_json(logs_dir, "manipulation_detection_*.json")
    osint = load_latest_json(logs_dir, "osint_report_*.json")
    competitive = load_latest_json(logs_dir, "competitive_intel_*.json")

    signals: list[str] = []
    severe_triggers: list[str] = []

    if vulnerability:
        critical_count = len(vulnerability.get("critical", []))
        high_count = len(vulnerability.get("high", []))
        if critical_count > 0 or high_count > 0:
            signals.append(f"Strategy vulnerability risk: {critical_count} critical, {high_count} high.")
            severe_triggers.append("strategy_vulnerability")

    if manipulation:
        threat_level = str(manipulation.get("threat_level", "low")).lower()
        active = len(manipulation.get("active_threats", []))
        if threat_level in {"high", "critical"}:
            signals.append(f"Market manipulation {threat_level.upper()} with {active} active threat patterns.")
            severe_triggers.append("market_manipulation")

    if competitive:
        comp_level = str(competitive.get("threat_level", "low")).lower()
        queue = competitive.get("deployment_queue", [])
        if comp_level in {"high", "critical"}:
            signals.append(f"Competitive crowding {comp_level.upper()}; rotate saturated tactics.")
            severe_triggers.append("competitive_crowding")
        if isinstance(queue, list) and queue:
            top = queue[0]
            score = float(top.get("deployment_score", 0))
            if score >= 7:
                signals.append(
                    f"Tool edge: prioritize {top.get('tool', 'top candidate')} (score {score:.1f}) for fast deployment."
                )

    if osint:
        analysis = osint.get("analysis", {}) if isinstance(osint, dict) else {}
        threat_summary = analysis.get("threat_summary", {}) if isinstance(analysis, dict) else {}
        if isinstance(threat_summary, dict):
            if str(threat_summary.get("scam_risk", "")).lower() == "critical":
                severe_triggers.append("critical_scam_risk")
            if str(threat_summary.get("regulatory_risk", "")).lower() in {"elevated", "high", "critical"}:
                severe_triggers.append("regulatory_risk")
        priorities = analysis.get("alert_priorities", []) if isinstance(analysis, dict) else []
        if isinstance(priorities, list):
            high_signal_items = [
                item for item in priorities
                if isinstance(item, dict) and item.get("type") in {"threat", "opportunity"}
            ]
            for item in high_signal_items[:2]:
                message = str(item.get("message", "")).strip()
                if message:
                    signals.append(message)

    # Hard gate: only produce morning brief if high/critical-severity risk exists.
    if not severe_triggers or not signals:
        return None

    now_utc = datetime.now(timezone.utc).isoformat()
    lines = [
        f"LINDY MORNING BRIEF ({now_utc})",
        "Only high-signal items:",
    ]
    for signal in signals[:5]:
        lines.append(f"- {signal}")
    return "\n".join(lines) + "\n"


def main() -> int:
    failures: list[str] = []
    notes: list[str] = []

    return_code, full_check_output = run_full_dashboard_check()
    if return_code != 0:
        failures.append("full_dashboard_check.py failed")

    red_team_return_code, red_team_output = run_anti_ai_red_team()
    if red_team_return_code != 0:
        failures.append("anti_ai_red_team.py failed")
    else:
        notes.append("anti_ai_red_team.py completed")

    data = load_json(DATA_FILE)
    ai = load_json(AI_FILE)
    confluence = load_json(CONFLUENCE_FILE)

    timestamps = {
        "data.updated_utc": data.get("updated_utc"),
        "ai.updated_utc": ai.get("updated_utc"),
        "confluence.updated_utc": confluence.get("updated_utc"),
    }

    for key, ts in timestamps.items():
        if not ts:
            failures.append(f"{key} missing")
            continue
        age = iso_age_minutes(str(ts))
        if age > 360:
            failures.append(f"{key} stale ({age} min)")
        else:
            notes.append(f"{key} age={age}m")

    numeric_checks = [
        ("btc_usd", data.get("crypto", {}).get("btc_usd"), 1000, 500000),
        ("eth_usd", data.get("crypto", {}).get("eth_usd"), 50, 50000),
        ("spx", data.get("macro", {}).get("spx"), 1000, 100000),
        ("dxy", data.get("macro", {}).get("dxy"), 70, 130),
        ("us10y_yield", data.get("macro", {}).get("us10y_yield"), 0, 20),
        ("fear_greed_index", data.get("sentiment", {}).get("fear_greed_index"), 0, 100),
    ]

    snapshot = {
        "updated_utc": datetime.now(timezone.utc).isoformat(),
        "values": {},
    }

    for name, raw, low, high in numeric_checks:
        value = parse_numeric(raw)
        snapshot["values"][name] = value
        if value is None:
            failures.append(f"{name} missing or non-numeric")
            continue
        if not (low <= value <= high):
            failures.append(f"{name} out of range ({value})")

    if SNAPSHOT_FILE.exists():
        previous = load_json(SNAPSHOT_FILE)
        previous_values = previous.get("values", {}) if isinstance(previous.get("values", {}), dict) else {}
        unchanged_keys = []
        for key, value in snapshot["values"].items():
            if value is not None and previous_values.get(key) == value:
                unchanged_keys.append(key)
        if len(unchanged_keys) >= 4:
            notes.append("Many values unchanged vs last nightly snapshot (can be normal off-hours).")

    SNAPSHOT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with SNAPSHOT_FILE.open("w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, indent=2)

    report = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "ok": len(failures) == 0,
        "failures": failures,
        "notes": notes,
        "full_dashboard_check_return_code": return_code,
        "anti_ai_red_team_return_code": red_team_return_code,
    }

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_FILE.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    if report["ok"]:
        if FAIL_FLAG_FILE.exists():
            FAIL_FLAG_FILE.unlink()
    else:
        FAIL_FLAG_FILE.parent.mkdir(parents=True, exist_ok=True)
        FAIL_FLAG_FILE.write_text(
            f"FAILED {report['checked_at_utc']}\n" + "\n".join(failures) + "\n",
            encoding="utf-8",
        )

    summary = "PASS" if report["ok"] else "FAIL"
    with REPORT_MD_FILE.open("a", encoding="utf-8") as fh:
        fh.write(f"\n## {datetime.now(timezone.utc).isoformat()}\n")
        fh.write(f"- Status: **{summary}**\n")
        if failures:
            for issue in failures:
                fh.write(f"- Failure: {issue}\n")
        else:
            fh.write("- Failures: none\n")
        for note in notes:
            fh.write(f"- Note: {note}\n")

    alert_lines = [
        f"Subject: [Dashboard Accuracy] {summary} - {report['checked_at_utc']}",
        "",
        f"Nightly accuracy status: {summary}",
        f"Checked at (UTC): {report['checked_at_utc']}",
        "",
        "Failures:" if failures else "Failures: none",
    ]
    if failures:
        alert_lines.extend([f"- {issue}" for issue in failures])
    if notes:
        alert_lines.append("")
        alert_lines.append("Notes:")
        alert_lines.extend([f"- {note}" for note in notes])
    alert_lines.append("")
    alert_lines.append(f"Report JSON: {REPORT_FILE}")
    alert_lines.append(f"Report Log: {REPORT_MD_FILE}")
    alert_lines.append(f"Fail Flag: {FAIL_FLAG_FILE}")

    ALERT_TXT_FILE.parent.mkdir(parents=True, exist_ok=True)
    ALERT_TXT_FILE.write_text("\n".join(alert_lines) + "\n", encoding="utf-8")

    brief = build_lindy_brief(REPO_ROOT / "logs")
    if brief:
        LINDY_BRIEF_FILE.write_text(brief, encoding="utf-8")
        print("\n--- Lindy Morning Brief ---\n")
        print(brief)
    else:
        if LINDY_BRIEF_FILE.exists():
            LINDY_BRIEF_FILE.unlink()
        print("\nLindy Morning Brief: no high-signal items (noise suppressed).")

    print("Nightly accuracy check:", summary)
    if failures:
        for issue in failures:
            print("-", issue)

    if full_check_output:
        print("\n--- full_dashboard_check.py output ---\n")
        print(full_check_output)

    if red_team_output:
        print("\n--- anti_ai_red_team.py output ---\n")
        print(red_team_output)

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
