# TradingView Alert Architecture v2.0 (Dashboard Integration)

This dashboard now supports a historical-grade confluence escalation pipeline:

- Tier 1 alerts are parsed silently into a rolling 72-hour score.
- Tier 2 black-swan alerts immediately trigger override state.
- Cross-asset confluence (`3+` score from `2+` asset classes) is surfaced in the dashboard gate.

## Alert Message Format (Required)

Use this exact format in TradingView alert messages:

`TIER1 | ASSET:YIELD_CURVE | SIGNAL:INVERTED | DIR:BEAR | NOTE:Full inversion - recession signal active.`

Fields:
- `TIER1` or `TIER2`
- `ASSET:<symbolic_asset_name>`
- `SIGNAL:<signal_key>`
- `DIR:BULL|BEAR|WATCH|DYNAMIC`
- `NOTE:<human readable note>`

## Files and Automation

- Feed input: `data/tradingview_alert_feed.json`
- Parsed confluence output: `data/confluence_alerts.json`
- Processor: `scripts/process_tradingview_alerts.py`
- Full pipeline runner: `scripts/update_command_center.py`

## Escalation Rules Implemented

- Rolling window: 72 hours
- Confluence threshold: score >= 3 and at least 2 asset classes
- Elevated threshold: score >= 5
- Pre-crisis threshold: score >= 7
- Tier2 override: immediate gate override for black-swan mode

## Recommended Operational Flow

1. TradingView sends alerts to your ingestion endpoint/email parser.
2. Ingestor appends normalized alerts into `data/tradingview_alert_feed.json`.
3. Run:
   - `python scripts/process_tradingview_alerts.py`
   - or `python scripts/update_command_center.py`
4. Dashboard reads `data/confluence_alerts.json` and updates gate + escalation panel.

## Notes

- Keep signal naming consistent to preserve scoring accuracy.
- Add new asset/signal mappings in `scripts/process_tradingview_alerts.py` (`ASSET_CLASS_MAP`, `WEIGHTS`) as your architecture evolves.
- Tier2 entries should remain rare and high-conviction by design.
