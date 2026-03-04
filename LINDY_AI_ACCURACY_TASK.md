# Lindy AI Task — Nightly Data Accuracy Guard

## Objective
Ensure all dashboard figures are live, numerically valid, and actively updating. Detect stale feeds, placeholders, and broken updates before the next session.

## Runbook (Nightly)
1. Run: `python scripts/nightly_accuracy_check.py`
2. Read: `logs/nightly_accuracy_report.json`
3. If `ok=false`, send immediate alert with all `failures`.
4. Attach latest full validation excerpt from `full_dashboard_check.py` output.

## Lindy Prompt Template
Use this prompt in your Lindy automation:

"Run the nightly dashboard accuracy guard in `scripts/nightly_accuracy_check.py`. If any check fails, summarize each failure in plain English, include the impacted metric/page, and propose the minimal fix path. If all checks pass, send a one-line PASS report with the newest timestamps for `data.updated_utc`, `ai.updated_utc`, and `confluence.updated_utc`."

## Escalation Rules
- Escalate immediately if any of these fail:
  - `btc_usd`, `eth_usd`, `spx`, `dxy`, `us10y_yield`, `fear_greed_index` missing/non-numeric/out-of-range
  - freshness older than 6 hours
  - full dashboard check non-zero exit code
- Severity:
  - **P1**: full check failure + stale timestamps
  - **P2**: one or more numeric fields invalid
  - **P3**: warning-only notes (e.g., unchanged values overnight)

## Output Targets
- Machine report: `logs/nightly_accuracy_report.json`
- Human log: `logs/nightly_accuracy.md`
- Baseline snapshot: `data/nightly_accuracy_snapshot.json`
