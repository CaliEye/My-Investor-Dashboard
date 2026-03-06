#!/usr/bin/env python3
"""AI confluence connectivity and readiness check.

Verifies all configured confluence sources so multi-AI consensus can be trusted.
Outputs:
- logs/ai_confluence_health_report.json
- logs/ai_confluence_health_report.md
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests
import yfinance as yf


REPO_ROOT = Path(__file__).resolve().parent.parent
JSON_REPORT = REPO_ROOT / "logs" / "ai_confluence_health_report.json"
MD_REPORT = REPO_ROOT / "logs" / "ai_confluence_health_report.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def mask(value: str | None) -> str:
    if not value:
        return "missing"
    if len(value) <= 8:
        return "set"
    return f"set({value[:4]}...{value[-4:]})"


def check_openai() -> dict:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return {"provider": "openai", "ok": False, "status": "missing_key", "detail": "OPENAI_API_KEY not set"}

    try:
        response = requests.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {key}"},
            timeout=12,
        )
        ok = response.status_code == 200
        return {
            "provider": "openai",
            "ok": ok,
            "status": "ok" if ok else "error",
            "detail": f"HTTP {response.status_code}",
            "key": mask(key),
        }
    except Exception as exc:
        return {"provider": "openai", "ok": False, "status": "error", "detail": str(exc), "key": mask(key)}


def check_xai() -> dict:
    key = os.getenv("XAI_API_KEY")
    if not key:
        return {"provider": "xai", "ok": False, "status": "missing_key", "detail": "XAI_API_KEY not set"}

    try:
        response = requests.get(
            "https://api.x.ai/v1/models",
            headers={"Authorization": f"Bearer {key}"},
            timeout=12,
        )
        ok = response.status_code == 200
        return {
            "provider": "xai",
            "ok": ok,
            "status": "ok" if ok else "error",
            "detail": f"HTTP {response.status_code}",
            "key": mask(key),
        }
    except Exception as exc:
        return {"provider": "xai", "ok": False, "status": "error", "detail": str(exc), "key": mask(key)}


def check_alpha_vantage() -> dict:
    key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not key:
        return {"provider": "alpha_vantage", "ok": False, "status": "missing_key", "detail": "ALPHA_VANTAGE_API_KEY not set"}

    try:
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=SPY&apikey={key}"
        response = requests.get(url, timeout=12)
        payload = response.json() if response.status_code == 200 else {}
        throttled = isinstance(payload, dict) and "Note" in payload
        ok = response.status_code == 200 and not throttled
        detail = "rate_limited" if throttled else f"HTTP {response.status_code}"
        return {
            "provider": "alpha_vantage",
            "ok": ok,
            "status": "ok" if ok else "error",
            "detail": detail,
            "key": mask(key),
        }
    except Exception as exc:
        return {"provider": "alpha_vantage", "ok": False, "status": "error", "detail": str(exc), "key": mask(key)}


def check_polygon() -> dict:
    key = os.getenv("POLYGON_API_KEY")
    if not key:
        return {"provider": "polygon", "ok": False, "status": "missing_key", "detail": "POLYGON_API_KEY not set"}

    try:
        response = requests.get(
            f"https://api.polygon.io/v2/reference/news?ticker=SPY&limit=1&apikey={key}",
            timeout=12,
        )
        ok = response.status_code == 200
        return {
            "provider": "polygon",
            "ok": ok,
            "status": "ok" if ok else "error",
            "detail": f"HTTP {response.status_code}",
            "key": mask(key),
        }
    except Exception as exc:
        return {"provider": "polygon", "ok": False, "status": "error", "detail": str(exc), "key": mask(key)}


def check_yahoo() -> dict:
    try:
        ticker = yf.Ticker("BTC-USD")
        hist = ticker.history(period="1d")
        ok = not hist.empty
        return {
            "provider": "yahoo_finance",
            "ok": ok,
            "status": "ok" if ok else "error",
            "detail": "history_received" if ok else "empty_history",
        }
    except Exception as exc:
        return {"provider": "yahoo_finance", "ok": False, "status": "error", "detail": str(exc)}


def check_optional_api(provider: str, env_var: str, endpoint: str, header_name: str = "Authorization") -> dict:
    key = os.getenv(env_var)
    if not key:
        return {"provider": provider, "ok": False, "status": "missing_key", "detail": f"{env_var} not set"}

    headers = {header_name: f"Bearer {key}"} if header_name.lower() == "authorization" else {header_name: key}
    try:
        response = requests.get(endpoint, headers=headers, timeout=12)
        ok = 200 <= response.status_code < 300
        return {
            "provider": provider,
            "ok": ok,
            "status": "ok" if ok else "error",
            "detail": f"HTTP {response.status_code}",
            "key": mask(key),
        }
    except Exception as exc:
        return {"provider": provider, "ok": False, "status": "error", "detail": str(exc), "key": mask(key)}


def main() -> int:
    checks = [
        check_openai(),
        check_xai(),
        check_alpha_vantage(),
        check_polygon(),
        check_yahoo(),
        check_optional_api("anthropic", "ANTHROPIC_API_KEY", "https://api.anthropic.com/v1/models", "x-api-key"),
        check_optional_api("gemini", "GEMINI_API_KEY", "https://generativelanguage.googleapis.com/v1beta/models"),
        check_optional_api("perplexity", "PERPLEXITY_API_KEY", "https://api.perplexity.ai/models"),
    ]

    core_providers = {"openai", "xai", "yahoo_finance"}
    core_checks = [item for item in checks if item.get("provider") in core_providers]
    core_ready = any(item.get("ok") for item in core_checks)

    providers_ok = len([item for item in checks if item.get("ok")])
    providers_total = len(checks)

    report = {
        "checked_at_utc": utc_now(),
        "summary": {
            "providers_ok": providers_ok,
            "providers_total": providers_total,
            "core_ready": core_ready,
            "core_policy": "At least one core provider (OpenAI, XAI, Yahoo) must be available",
        },
        "providers": checks,
    }

    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    with JSON_REPORT.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    with MD_REPORT.open("a", encoding="utf-8") as fh:
        fh.write(f"\n## {report['checked_at_utc']}\n")
        fh.write(f"- Providers healthy: {providers_ok}/{providers_total}\n")
        fh.write(f"- Core readiness: {'PASS' if core_ready else 'FAIL'}\n")
        for item in checks:
            status = "PASS" if item.get("ok") else "FAIL"
            fh.write(f"- [{status}] {item.get('provider')}: {item.get('detail')}\n")

    print("AI Confluence Health Check")
    print(f"Providers healthy: {providers_ok}/{providers_total}")
    print(f"Core readiness: {'PASS' if core_ready else 'FAIL'}")
    for item in checks:
        status = "PASS" if item.get("ok") else "FAIL"
        print(f"[{status}] {item.get('provider')}: {item.get('detail')}")

    return 0 if core_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
