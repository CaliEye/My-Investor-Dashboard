#!/usr/bin/env python3
"""Dispatch confluence escalation alerts with dedupe and safe fallback logging."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFLUENCE_FILE = REPO_ROOT / "data" / "confluence_alerts.json"
STATE_FILE = REPO_ROOT / "data" / "alert_dispatch_state.json"
LOG_FILE = REPO_ROOT / "data" / "alert_dispatch_log.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def build_event(confluence: dict[str, Any]) -> dict[str, Any] | None:
    summary = confluence.get("summary") if isinstance(confluence.get("summary"), dict) else {}
    tier2 = confluence.get("tier2") if isinstance(confluence.get("tier2"), dict) else {}

    dominant_direction = str(summary.get("dominant_direction") or "NEUTRAL").upper()
    dominant_score = int(summary.get("dominant_score") or 0)
    urgency = str(summary.get("urgency") or "NORMAL").upper()
    threshold_hit = bool(summary.get("threshold_hit"))
    tier2_active = bool(tier2.get("active"))
    tier2_count = int(tier2.get("count") or 0)

    if tier2_active:
        event_type = "TIER2_OVERRIDE"
        priority = "CRITICAL"
    elif threshold_hit and dominant_score >= 5:
        event_type = "CONFLUENCE_THRESHOLD"
        priority = "HIGH" if urgency in {"ELEVATED", "PRE-CRISIS"} else "MEDIUM"
    else:
        return None

    key = "|".join(
        [
            str(confluence.get("updated_utc") or utc_now_iso()),
            event_type,
            dominant_direction,
            str(dominant_score),
            str(tier2_count),
        ]
    )

    latest_tier2 = tier2.get("latest") if isinstance(tier2.get("latest"), dict) else None

    return {
        "event_key": key,
        "event_type": event_type,
        "priority": priority,
        "dominant_direction": dominant_direction,
        "dominant_score": dominant_score,
        "urgency": urgency,
        "threshold_hit": threshold_hit,
        "tier2_active": tier2_active,
        "tier2_count": tier2_count,
        "tier2_latest": latest_tier2,
        "source_updated_utc": confluence.get("updated_utc"),
        "created_utc": utc_now_iso(),
    }


def post_webhook(url: str, payload: dict[str, Any]) -> tuple[bool, str]:
    body = json.dumps(payload).encode("utf-8")
    req = Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=12) as res:
            status = int(getattr(res, "status", 200))
            if 200 <= status < 300:
                return True, f"HTTP {status}"
            return False, f"HTTP {status}"
    except (HTTPError, URLError, TimeoutError) as exc:
        return False, f"{type(exc).__name__}: {exc}"


def append_log(entry: dict[str, Any]) -> None:
    log_payload = read_json(LOG_FILE, default={"updated_utc": None, "events": []})
    events = log_payload.get("events") if isinstance(log_payload.get("events"), list) else []
    events.insert(0, entry)
    log_payload["updated_utc"] = utc_now_iso()
    log_payload["events"] = events[:100]
    write_json(LOG_FILE, log_payload)


def main() -> None:
    confluence = read_json(CONFLUENCE_FILE, default={})
    if not isinstance(confluence, dict):
        raise RuntimeError("Invalid confluence payload format")

    event = build_event(confluence)
    if not event:
        append_log(
            {
                "created_utc": utc_now_iso(),
                "status": "noop",
                "reason": "No threshold/tier2 dispatch condition",
                "source_updated_utc": confluence.get("updated_utc"),
            }
        )
        print("No dispatch needed: threshold not met and no Tier2 override.")
        return

    state = read_json(STATE_FILE, default={})
    last_event_key = state.get("last_event_key")

    if last_event_key == event["event_key"]:
        append_log(
            {
                "created_utc": utc_now_iso(),
                "status": "skipped_duplicate",
                "event_key": event["event_key"],
                "event_type": event["event_type"],
            }
        )
        print(f"Skipped duplicate dispatch for event: {event['event_type']}")
        return

    webhook_url = os.getenv("ENDGAME_ALERT_WEBHOOK_URL") or os.getenv("LINDY_WEBHOOK_URL")
    dispatch_result = {"delivered": False, "channel": "log_only", "detail": "webhook not configured"}

    if webhook_url:
        payload = {
            "asset": "ENDGAME-CONFLUENCE",
            "confidence": event["dominant_score"],
            "signal": event["dominant_direction"],
            "priority": event["priority"],
            "event_type": event["event_type"],
            "urgency": event["urgency"],
            "tier2_active": event["tier2_active"],
            "tier2_count": event["tier2_count"],
            "timestamp": utc_now_iso(),
            "note": "Automated dispatch from confluence escalation engine",
        }
        ok, detail = post_webhook(webhook_url, payload)
        dispatch_result = {
            "delivered": ok,
            "channel": "webhook",
            "detail": detail,
        }

    log_entry = {
        "created_utc": utc_now_iso(),
        "status": "delivered" if dispatch_result["delivered"] else "logged",
        "event": event,
        "dispatch": dispatch_result,
    }
    append_log(log_entry)

    state.update(
        {
            "last_event_key": event["event_key"],
            "last_event_type": event["event_type"],
            "last_dispatch_utc": utc_now_iso(),
            "last_delivered": bool(dispatch_result["delivered"]),
        }
    )
    write_json(STATE_FILE, state)

    print(
        f"Dispatch processed: {event['event_type']} | "
        f"delivered={dispatch_result['delivered']} | channel={dispatch_result['channel']}"
    )


if __name__ == "__main__":
    main()
