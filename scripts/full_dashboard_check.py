#!/usr/bin/env python3
"""One-command full dashboard validation.

Checks:
1) Runs data update pipelines.
2) Serves dashboard locally.
3) Smoke-tests all key pages.
4) Validates payload freshness + required keys.
5) Runs user-style browser checks (Playwright) for dynamic widgets.

Exit code:
- 0: all required checks passed
- 1: one or more required checks failed
"""

from __future__ import annotations

import json
import runpy
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = REPO_ROOT / "data" / "data.json"
AI_FILE = REPO_ROOT / "data" / "ai_insights.json"

PAGES = [
    "index.html",
    "macro.html",
    "crypto.html",
    "sentiment.html",
    "insights.html",
    "warroom.html",
    "scenario.html",
    "links.html",
    "system_test.html",
]

REQUIRED_DATA_PATHS = [
    ("bias",),
    ("updated_utc",),
    ("next_review_utc",),
    ("crypto", "risk_level"),
    ("macro", "risk_level"),
    ("sentiment", "fear_greed_index"),
    ("sector_etfs", "sectors", "tech", "change_pct_day"),
    ("sector_etfs", "sectors", "defense", "change_pct_day"),
    ("sector_etfs", "sectors", "metals", "change_pct_day"),
    ("sector_etfs", "basket", "equal_weight_change_pct_day"),
]

REQUIRED_AI_PATHS = [
    ("updated_utc",),
    ("confidence_score",),
    ("confluence", "score"),
]


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def print_result(result: CheckResult) -> None:
    status = "PASS" if result.ok else "FAIL"
    print(f"[{status}] {result.name}: {result.detail}")


def pick_free_port(default: int = 5500) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        if sock.connect_ex(("127.0.0.1", default)) != 0:
            return default

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def get_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def has_path(payload: dict[str, Any], path: tuple[str, ...]) -> bool:
    cur: Any = payload
    for part in path:
        if not isinstance(cur, dict) or part not in cur:
            return False
        cur = cur[part]
    return True


def parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def run_updaters() -> list[CheckResult]:
    results: list[CheckResult] = []

    try:
        runpy.run_path(str(REPO_ROOT / "scripts" / "update_data.py"), run_name="__main__")
        results.append(CheckResult("update_data.py", True, "completed"))
    except Exception as exc:
        results.append(CheckResult("update_data.py", False, f"{type(exc).__name__}: {exc}"))

    try:
        runpy.run_path(str(REPO_ROOT / "scripts" / "update_ai_insights.py"), run_name="__main__")
        results.append(CheckResult("update_ai_insights.py", True, "completed"))
    except Exception as exc:
        results.append(CheckResult("update_ai_insights.py", False, f"{type(exc).__name__}: {exc}"))

    return results


def fetch_text(base_url: str, path: str) -> tuple[int, str]:
    url = f"{base_url}/{path.lstrip('/')}"
    req = Request(url, headers={"Cache-Control": "no-cache"})
    with urlopen(req, timeout=20) as response:
        body = response.read().decode("utf-8", "ignore")
        return int(response.status), body


def run_http_checks(base_url: str) -> list[CheckResult]:
    results: list[CheckResult] = []

    for page in PAGES:
        try:
            status, body = fetch_text(base_url, page)
            ok = status == 200 and len(body) > 200
            results.append(CheckResult(f"page:{page}", ok, f"status={status}, len={len(body)}"))
        except (URLError, HTTPError, TimeoutError) as exc:
            results.append(CheckResult(f"page:{page}", False, f"request error: {exc}"))

    try:
        _, _ = fetch_text(base_url, "data/data.json")
        _, _ = fetch_text(base_url, "data/ai_insights.json")
        results.append(CheckResult("data_endpoints", True, "reachable"))
    except Exception as exc:
        results.append(CheckResult("data_endpoints", False, f"{type(exc).__name__}: {exc}"))

    return results


def run_payload_checks() -> list[CheckResult]:
    results: list[CheckResult] = []
    now = datetime.now(timezone.utc)

    try:
        data = get_json(DATA_FILE)
        ai = get_json(AI_FILE)
    except Exception as exc:
        return [CheckResult("payload_read", False, f"{type(exc).__name__}: {exc}")]

    missing_data = [".".join(p) for p in REQUIRED_DATA_PATHS if not has_path(data, p)]
    missing_ai = [".".join(p) for p in REQUIRED_AI_PATHS if not has_path(ai, p)]

    results.append(CheckResult("data_required_keys", not missing_data, "ok" if not missing_data else ", ".join(missing_data)))
    results.append(CheckResult("ai_required_keys", not missing_ai, "ok" if not missing_ai else ", ".join(missing_ai)))

    freshness_items = [
        ("data.updated_utc", data.get("updated_utc")),
        ("data.sector_etfs.updated_utc", data.get("sector_etfs", {}).get("updated_utc")),
        ("ai.updated_utc", ai.get("updated_utc")),
    ]

    for label, ts in freshness_items:
        if not ts:
            results.append(CheckResult(label, False, "missing timestamp"))
            continue
        try:
            age_min = int((now - parse_iso(str(ts))).total_seconds() / 60)
            ok = age_min <= 180
            results.append(CheckResult(label, ok, f"age={age_min} min"))
        except Exception as exc:
            results.append(CheckResult(label, False, f"parse error: {exc}"))

    return results


def run_playwright_checks(base_url: str) -> list[CheckResult]:
    results: list[CheckResult] = []

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        results.append(CheckResult("playwright_available", False, f"{type(exc).__name__}: {exc}"))
        return results

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context()

            for page_name in PAGES:
                page = ctx.new_page()
                console_errors: list[tuple[str, str]] = []
                request_failed: list[tuple[str, str]] = []

                page.on("console", lambda m, e=console_errors: e.append((m.type, m.text)) if m.type == "error" else None)
                page.on("requestfailed", lambda r, rf=request_failed: rf.append((r.url, str(r.failure))))

                page.goto(f"{base_url}/{page_name}", wait_until="networkidle", timeout=60000)

                # Only treat local failed requests as hard failures.
                local_failures = [f for f in request_failed if "127.0.0.1" in f[0] or "localhost" in f[0]]
                ok = len(console_errors) == 0 and len(local_failures) == 0
                detail = f"console_errors={len(console_errors)}, local_failed_requests={len(local_failures)}"
                results.append(CheckResult(f"browser:{page_name}", ok, detail))
                page.close()

            page = ctx.new_page()
            page.goto(f"{base_url}/index.html", wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(3000)

            def text(selector: str) -> str:
                return page.locator(selector).inner_text().strip()

            selectors = [
                "#macro-unemployment",
                "#sector-tech-status",
                "#sector-etf-status",
                "#confluence-score",
                "#crypto-risk-gauge",
                "#macro-risk-gauge",
                "#risk-alert-ticker",
            ]

            missing = [s for s in selectors if page.locator(s).count() == 0]
            results.append(CheckResult("browser:index_selectors", not missing, "ok" if not missing else f"missing={missing}"))

            if not missing:
                signal_ok = all(
                    len(text(sel)) > 0
                    for sel in [
                        "#macro-unemployment",
                        "#sector-tech-status",
                        "#confluence-score",
                        "#crypto-risk-gauge",
                        "#macro-risk-gauge",
                        "#risk-alert-ticker",
                    ]
                )
                results.append(CheckResult("browser:index_dynamic_values", signal_ok, "populated" if signal_ok else "one or more values empty"))

            browser.close()

    except Exception as exc:
        results.append(CheckResult("playwright_checks", False, f"{type(exc).__name__}: {exc}"))

    return results


def main() -> int:
    print("== Full Dashboard Check ==")
    print(f"Repo: {REPO_ROOT}")

    all_results: list[CheckResult] = []

    print("\n[1/4] Running update pipelines...")
    all_results.extend(run_updaters())

    port = pick_free_port(5500)
    base_url = f"http://127.0.0.1:{port}"

    server_cmd = [sys.executable, "-m", "http.server", str(port)]
    server = subprocess.Popen(server_cmd, cwd=str(REPO_ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    try:
        time.sleep(1.2)

        print("[2/4] Running HTTP/page checks...")
        all_results.extend(run_http_checks(base_url))

        print("[3/4] Running payload checks...")
        all_results.extend(run_payload_checks())

        print("[4/4] Running browser flow checks...")
        all_results.extend(run_playwright_checks(base_url))

    finally:
        server.terminate()
        try:
            server.wait(timeout=3)
        except Exception:
            server.kill()

    print("\n== Results ==")
    for result in all_results:
        print_result(result)

    failed = [r for r in all_results if not r.ok]
    print(f"\nSummary: {len(all_results) - len(failed)}/{len(all_results)} checks passed")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
