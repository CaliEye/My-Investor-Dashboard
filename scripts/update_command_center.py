#!/usr/bin/env python3
"""Run all core command-center data pipelines in sequence."""

from __future__ import annotations

import runpy
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = [
    "scripts/update_data.py",
    "scripts/update_ai_insights.py",
    "scripts/update_bots_data.py",
    "scripts/process_tradingview_alerts.py",
    "scripts/dispatch_confluence_alerts.py",
]


def main() -> None:
    for script in SCRIPTS:
        path = REPO_ROOT / script
        print(f"Running {script}...")
        runpy.run_path(str(path), run_name="__main__")
    print("Command-center pipelines completed.")


if __name__ == "__main__":
    main()
