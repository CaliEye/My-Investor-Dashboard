#!/usr/bin/env python3
"""Overnight research pull for trading intelligence.

Builds a morning report from public, high-signal sources across:
- AI trading tooling
- large datasets / data repository patterns
- confluence and automation research
- war-room / scenario / red-team operating models
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus
from xml.etree import ElementTree

import requests


REPO_ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = REPO_ROOT / "logs"
REPORT_JSON = LOGS_DIR / "overnight_research_report.json"
REPORT_MD = LOGS_DIR / "overnight_research_report.md"


RESEARCH_TOPICS: dict[str, list[str]] = {
    "ai_trading_agents": [
        "multi agent trading",
        "llm trading agent",
        "autonomous finance agent",
    ],
    "data_repositories": [
        "financial time series dataset",
        "alternative data investing",
        "market microstructure dataset",
    ],
    "risk_and_portfolio": [
        "portfolio risk parity automation",
        "dynamic position sizing",
        "portfolio rebalancing bot",
    ],
    "confluence_automation": [
        "signal confluence trading",
        "decision engine confluence",
        "automated trading orchestration",
    ],
    "warroom_redteam": [
        "red team algorithmic trading",
        "scenario analysis trading",
        "market manipulation detection",
    ],
}

RELEVANCE_KEYWORDS: dict[str, list[str]] = {
    "ai_trading_agents": ["trading", "market", "finance", "portfolio", "execution", "alpha"],
    "data_repositories": ["dataset", "market", "financial", "timeseries", "price", "order book"],
    "risk_and_portfolio": ["risk", "portfolio", "drawdown", "allocation", "rebalance", "volatility"],
    "confluence_automation": ["signal", "confluence", "automation", "orchestration", "decision"],
    "warroom_redteam": ["red team", "scenario", "stress", "manipulation", "adversarial", "defense"],
}

STRICT_TOPIC_TERMS: dict[str, list[str]] = {
    "ai_trading_agents": [
        "trading agent",
        "algorithmic trading",
        "portfolio",
        "execution",
        "order",
        "backtest",
        "strategy",
        "quant",
    ],
    "data_repositories": [
        "dataset",
        "time series",
        "timeseries",
        "order book",
        "ohlcv",
        "tick",
        "feature store",
        "market data",
    ],
    "risk_and_portfolio": [
        "drawdown",
        "volatility",
        "rebalancing",
        "risk parity",
        "position sizing",
        "allocation",
        "tracking error",
    ],
    "confluence_automation": [
        "signal confluence",
        "decision engine",
        "orchestration",
        "automation",
        "pipeline",
        "workflow",
    ],
    "warroom_redteam": [
        "red team",
        "scenario",
        "stress test",
        "market manipulation",
        "adversarial",
        "threat",
        "defense",
    ],
}

NOISE_TERMS = [
    "affiliate marketing",
    "influencer",
    "youtube",
    "consumer finance operations",
    "payments orchestration",
    "press release",
    "listed for spot trading",
]

GLOBAL_FINANCE_TERMS = [
    "trading",
    "market",
    "finance",
    "financial",
    "portfolio",
    "investment",
    "risk",
    "asset",
    "alpha",
    "execution",
    "equity",
    "crypto",
    "etf",
]


def count_hits(text: str, terms: list[str]) -> int:
    return sum(1 for term in terms if term in text)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_get_json(url: str, timeout: int = 20) -> Any:
    try:
        response = requests.get(url, timeout=timeout, headers={"User-Agent": "lindy-research-pull/1.0"})
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def safe_get_text(url: str, timeout: int = 20) -> str:
    try:
        response = requests.get(url, timeout=timeout, headers={"User-Agent": "lindy-research-pull/1.0"})
        response.raise_for_status()
        return response.text
    except Exception:
        return ""


def github_repo_search(query: str, per_page: int = 5) -> list[dict[str, Any]]:
    url = (
        "https://api.github.com/search/repositories"
        f"?q={quote_plus(query)}&sort=updated&order=desc&per_page={per_page}"
    )
    payload = safe_get_json(url)
    if not isinstance(payload, dict):
        return []
    items = payload.get("items", [])
    results: list[dict[str, Any]] = []
    if not isinstance(items, list):
        return results
    for item in items[:per_page]:
        if not isinstance(item, dict):
            continue
        results.append(
            {
                "name": item.get("full_name"),
                "url": item.get("html_url"),
                "stars": item.get("stargazers_count", 0),
                "updated_at": item.get("updated_at"),
                "description": item.get("description") or "",
                "source": "github",
                "query": query,
            }
        )
    return results


def arxiv_search(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    url = (
        "http://export.arxiv.org/api/query"
        f"?search_query=all:{quote_plus(query)}&start=0&max_results={max_results}"
        "&sortBy=submittedDate&sortOrder=descending"
    )
    xml_text = safe_get_text(url)
    if not xml_text:
        return []
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return []

    ns = {"a": "http://www.w3.org/2005/Atom"}
    entries = root.findall("a:entry", ns)
    results: list[dict[str, Any]] = []
    for entry in entries[:max_results]:
        title = (entry.findtext("a:title", default="", namespaces=ns) or "").strip()
        link = entry.findtext("a:id", default="", namespaces=ns)
        published = entry.findtext("a:published", default="", namespaces=ns)
        summary = (entry.findtext("a:summary", default="", namespaces=ns) or "").strip()
        summary = re.sub(r"\s+", " ", summary)
        results.append(
            {
                "title": title,
                "url": link,
                "published": published,
                "summary": summary[:300],
                "source": "arxiv",
                "query": query,
            }
        )
    return results


def huggingface_dataset_search(query: str, limit: int = 5) -> list[dict[str, Any]]:
    url = f"https://huggingface.co/api/datasets?search={quote_plus(query)}&limit={limit}"
    payload = safe_get_json(url)
    if not isinstance(payload, list):
        return []
    results: list[dict[str, Any]] = []
    for item in payload[:limit]:
        if not isinstance(item, dict):
            continue
        dataset_id = item.get("id") or ""
        results.append(
            {
                "name": dataset_id,
                "url": f"https://huggingface.co/datasets/{dataset_id}" if dataset_id else "",
                "likes": item.get("likes", 0),
                "downloads": item.get("downloads", 0),
                "updated_at": item.get("lastModified", ""),
                "source": "huggingface",
                "query": query,
            }
        )
    return results


def google_news_rss(query: str, limit: int = 5) -> list[dict[str, Any]]:
    url = f"https://news.google.com/rss/search?q={quote_plus(query)}"
    xml_text = safe_get_text(url)
    if not xml_text:
        return []
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return []

    channel = root.find("channel")
    if channel is None:
        return []

    items = channel.findall("item")
    results: list[dict[str, Any]] = []
    for item in items[:limit]:
        title = item.findtext("title", default="")
        link = item.findtext("link", default="")
        pub_date = item.findtext("pubDate", default="")
        results.append(
            {
                "title": title,
                "url": link,
                "published": pub_date,
                "source": "google_news",
                "query": query,
            }
        )
    return results


def score_signals(bucket: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    scored: list[dict[str, Any]] = []
    for topic, items in bucket.items():
        for item in items:
            score = 0.0
            source = item.get("source", "")
            text = " ".join(
                [
                    str(item.get("name", "")),
                    str(item.get("title", "")),
                    str(item.get("description", "")),
                    str(item.get("summary", "")),
                ]
            ).lower()
            strict_hits = count_hits(text, STRICT_TOPIC_TERMS.get(topic, []))
            if source == "github":
                stars = float(item.get("stars", 0) or 0)
                score += min(stars / 200.0, 8)
            elif source == "huggingface":
                likes = float(item.get("likes", 0) or 0)
                downloads = float(item.get("downloads", 0) or 0)
                score += min(likes / 20.0, 4)
                score += min(downloads / 5000.0, 4)
            elif source == "arxiv":
                score += 5
            elif source == "google_news":
                score += 2

            if topic in {"risk_and_portfolio", "confluence_automation", "ai_trading_agents"}:
                score += 1.5

            score += min(strict_hits * 0.6, 2.4)

            scored.append({"topic": topic, "score": round(score, 2), "item": item})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


def is_relevant_item(topic: str, item: dict[str, Any]) -> bool:
    text = " ".join(
        [
            str(item.get("name", "")),
            str(item.get("title", "")),
            str(item.get("description", "")),
            str(item.get("summary", "")),
        ]
    ).lower()
    source = str(item.get("source", "")).lower()

    if any(term in text for term in NOISE_TERMS):
        return False

    required = RELEVANCE_KEYWORDS.get(topic, [])
    topic_match = any(keyword in text for keyword in required) if required else True
    global_hits = count_hits(text, GLOBAL_FINANCE_TERMS)
    strict_hits = count_hits(text, STRICT_TOPIC_TERMS.get(topic, []))

    if source == "google_news":
        return topic_match and global_hits >= 1 and strict_hits >= 2

    if source == "arxiv":
        return topic_match and global_hits >= 1 and strict_hits >= 1

    return topic_match and global_hits >= 1


def dedupe_and_filter(bucket: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    cleaned: dict[str, list[dict[str, Any]]] = {}
    for topic, items in bucket.items():
        seen: set[str] = set()
        topic_clean: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            if not is_relevant_item(topic, item):
                continue
            key = (str(item.get("url", "")) + "|" + str(item.get("name", "")) + "|" + str(item.get("title", ""))).lower()
            if key in seen:
                continue
            seen.add(key)
            topic_clean.append(item)
        cleaned[topic] = topic_clean
    return cleaned


def build_actions(scored: list[dict[str, Any]]) -> list[str]:
    top = scored[:10]
    actions: list[str] = []

    github_top = [x for x in top if x["item"].get("source") == "github"][:3]
    for entry in github_top:
        repo = entry["item"].get("name", "repo")
        actions.append(f"Sandbox test {repo} and evaluate integration fit within 24h.")

    data_top = [x for x in top if x["item"].get("source") == "huggingface"][:2]
    for entry in data_top:
        ds = entry["item"].get("name", "dataset")
        actions.append(f"Run data quality + leakage audit on {ds} before adding to feature store.")

    paper_top = [x for x in top if x["item"].get("source") == "arxiv"][:2]
    for entry in paper_top:
        title = entry["item"].get("title", "paper")
        actions.append(f"Extract implementable hypothesis from paper: {title[:90]}.")

    if not actions:
        actions.append("No high-confidence external signals detected; keep current system and re-scan next cycle.")

    actions.append("Maintain strict risk controls; external research informs process, not guaranteed returns.")
    return actions[:8]


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"# Lindy Overnight Research Report ({report.get('generated_utc')})")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append(f"- Sources scanned: {report.get('source_count', 0)}")
    lines.append(f"- High-signal items: {len(report.get('top_signals', []))}")
    lines.append("- Objective: find practical tools, datasets, and operating patterns for your investing stack.")
    lines.append("")

    lines.append("## Top Signals")
    for signal in report.get("top_signals", [])[:12]:
        item = signal.get("item", {})
        title = item.get("name") or item.get("title") or "Untitled"
        url = item.get("url", "")
        lines.append(f"- [{signal.get('score')}] {title} ({item.get('source')}) {url}")
    lines.append("")

    lines.append("## What Seems to Work")
    lines.append("- Multi-source confluence with explicit risk gates outperforms single-signal bots in noisy regimes.")
    lines.append("- Portfolio + bot systems with hard stop/risk tiers survive better than high-conviction all-in systems.")
    lines.append("- Research-agent workflows are highest value when bounded to concrete deploy/test/rollback gates.")
    lines.append("- Data repositories work best with schema/versioning, leakage checks, and feature drift monitoring.")
    lines.append("")

    lines.append("## What Usually Fails")
    lines.append("- Overfitting from unvetted large datasets and no out-of-sample walk-forward validation.")
    lines.append("- Automation without red-team checks, scenario stress tests, and manual override paths.")
    lines.append("- Chasing crowded strategies after adoption saturation or social-media hype spikes.")
    lines.append("")

    lines.append("## Recommended Next Actions")
    for action in report.get("recommended_actions", []):
        lines.append(f"- {action}")
    lines.append("")

    lines.append("## Focus Areas for Tomorrow")
    lines.append("- Validate 1 new tool in sandbox and 1 new dataset in feature QA pipeline.")
    lines.append("- Run one war-room scenario drill: manipulation shock + liquidity drop + bot failover.")
    lines.append("- Promote only signals that pass confluence + risk-threshold + paper-trade gates.")
    lines.append("")

    lines.append("## Reliability Note")
    lines.append("- This research improves decision quality but does not guarantee profits.")
    return "\n".join(lines) + "\n"


def main() -> int:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    raw_bucket: dict[str, list[dict[str, Any]]] = {}

    for topic, queries in RESEARCH_TOPICS.items():
        topic_items: list[dict[str, Any]] = []
        for query in queries:
            topic_items.extend(github_repo_search(query, per_page=3))
            topic_items.extend(arxiv_search(query, max_results=3))
            topic_items.extend(huggingface_dataset_search(query, limit=3))
            topic_items.extend(google_news_rss(query, limit=2))
        raw_bucket[topic] = topic_items

    filtered_bucket = dedupe_and_filter(raw_bucket)
    scored = score_signals(filtered_bucket)
    high_confidence = [entry for entry in scored if float(entry.get("score", 0)) >= 3.5]
    report = {
        "generated_utc": utc_now(),
        "source_count": sum(len(v) for v in filtered_bucket.values()),
        "top_signals": high_confidence[:20],
        "recommended_actions": build_actions(high_confidence),
        "topics_scanned": list(RESEARCH_TOPICS.keys()),
    }

    with REPORT_JSON.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    md = render_markdown(report)
    REPORT_MD.write_text(md, encoding="utf-8")

    print("Overnight research pull: COMPLETE")
    print(f"Top signals: {len(report['top_signals'])}")
    print(f"Report JSON: {REPORT_JSON}")
    print(f"Report MD: {REPORT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
