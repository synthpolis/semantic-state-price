from __future__ import annotations

import argparse
import csv
import json
import math
import re
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from statistics import mean
from typing import Any

import numpy as np
from scipy.optimize import minimize


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
GAMMA_EVENTS_URL = "https://gamma-api.polymarket.com/events"
CLOB_HISTORY_URL = "https://clob.polymarket.com/batch-prices-history"
USER_AGENT = "semantic-state-price-research/0.2"

CRYPTO_TAGS = ["crypto"]
OPENAI_TAGS = ["artificial-intelligence", "ai", "business", "legal-cases"]
OPENAI_TARGET_DATE = datetime(2027, 12, 31, tzinfo=UTC)
OPENAI_BUCKETS = [
    ("$0B-$500B", 250.0, 0.0, 500.0),
    ("$500B-$750B", 625.0, 500.0, 750.0),
    ("$750B-$800B", 775.0, 750.0, 800.0),
    ("$800B-$1000B", 900.0, 800.0, 1000.0),
    ("$1000B-$1200B", 1100.0, 1000.0, 1200.0),
    ("$1200B-$1250B", 1225.0, 1200.0, 1250.0),
    ("$1250B-$1400B", 1325.0, 1250.0, 1400.0),
    ("$1400B-$1500B", 1450.0, 1400.0, 1500.0),
    ("$1500B-$1600B", 1550.0, 1500.0, 1600.0),
    (">$1600B", 1880.0, 1600.0, math.inf),
]


def http_json(url: str, *, body: dict[str, Any] | None = None, timeout: int = 30) -> Any:
    headers = {"User-Agent": USER_AGENT}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    last_exc: Exception | None = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return json.loads(response.read())
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            time.sleep(0.35 * (attempt + 1))
    raise RuntimeError(f"failed to fetch {url}: {last_exc}") from last_exc


def parse_json_field(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []
    return []


def parse_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace("$", "").replace(",", "").replace("%", "").strip()
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def parse_dt(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def fetch_events(tags: list[str], *, max_pages: int, include_closed: bool = True) -> list[dict[str, Any]]:
    seen: set[str] = set()
    events: list[dict[str, Any]] = []
    closed_values = ["true", "false"] if include_closed else ["false"]
    for tag in tags:
        for closed in closed_values:
            for page in range(max_pages):
                params = {
                    "limit": 100,
                    "offset": page * 100,
                    "tag_slug": tag,
                    "closed": closed,
                }
                url = f"{GAMMA_EVENTS_URL}?{urllib.parse.urlencode(params)}"
                rows = http_json(url)
                if not isinstance(rows, list) or not rows:
                    break
                for event in rows:
                    key = f"{tag}:{closed}:{event.get('id')}"
                    if key not in seen:
                        seen.add(key)
                        events.append(event)
                if len(rows) < 100:
                    break
                time.sleep(0.04)
    return events


def iter_market_records(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen_markets: set[str] = set()
    for event in events:
        event_title = event.get("title") or event.get("question") or event.get("slug") or ""
        event_id = str(event.get("id") or "")
        event_slug = event.get("slug") or ""
        event_tags = [
            str(tag.get("slug") or tag.get("label") or tag.get("name"))
            for tag in event.get("tags", [])
            if isinstance(tag, dict)
        ]
        for market in event.get("markets") or []:
            market_id = str(market.get("id") or market.get("conditionId") or market.get("slug") or "")
            if not market_id or market_id in seen_markets:
                continue
            seen_markets.add(market_id)
            question = market.get("question") or market.get("title") or event_title
            outcomes = parse_json_field(market.get("outcomes"))
            outcome_prices = parse_json_field(market.get("outcomePrices"))
            token_ids = parse_json_field(market.get("clobTokenIds"))
            yes_idx = 0
            for idx, outcome in enumerate(outcomes):
                if str(outcome).strip().lower() == "yes":
                    yes_idx = idx
                    break
            yes_price = parse_float(outcome_prices[yes_idx]) if yes_idx < len(outcome_prices) else None
            yes_token = str(token_ids[yes_idx]) if yes_idx < len(token_ids) else None
            end_dt = parse_dt(market.get("endDate") or event.get("endDate"))
            volume = (
                parse_float(market.get("volumeNum"))
                or parse_float(market.get("volume"))
                or parse_float(market.get("volumeClob"))
                or 0.0
            )
            liquidity = parse_float(market.get("liquidityNum")) or parse_float(market.get("liquidity")) or 0.0
            records.append(
                {
                    "market_id": market_id,
                    "condition_id": market.get("conditionId"),
                    "slug": market.get("slug") or "",
                    "event_id": event_id,
                    "event_slug": event_slug,
                    "event_title": event_title,
                    "question": question,
                    "search_text": " ".join([question, event_title, " ".join(map(str, outcomes))]),
                    "end_dt": end_dt,
                    "end_date": iso(end_dt),
                    "closed": bool(market.get("closed") or event.get("closed")),
                    "active": bool(market.get("active", False)),
                    "outcomes": outcomes,
                    "outcome_prices": outcome_prices,
                    "yes_price": yes_price,
                    "yes_token_id": yes_token,
                    "volume": volume,
                    "liquidity": liquidity,
                    "event_tags": event_tags,
                }
            )
    return records


def asset_mentions(text: str) -> list[str]:
    matches: list[str] = []
    if re.search(r"\b(bitcoin|btc)\b", text, re.I):
        matches.append("BTC")
    eth_word = re.search(r"\beth\b", text, re.I)
    eth_as_unit = re.search(r"(?:[><=]\s*)?\d[\d,.]*\s*eth\b", text, re.I)
    eth_asset_context = re.search(
        r"\beth\b.*\b(above|over|below|under|ath|all[- ]time|record|price|etf|sol|btc|bitcoin)\b",
        text,
        re.I,
    ) or re.search(
        r"\b(above|over|below|under|ath|all[- ]time|record|price|etf|sol|btc|bitcoin)\b.*\beth\b",
        text,
        re.I,
    )
    if re.search(r"\bethereum\b", text, re.I) or (eth_word and (eth_asset_context or not eth_as_unit)):
        matches.append("ETH")
    return matches


def parse_threshold(text: str) -> tuple[str | None, str | None, float | None]:
    side_pattern = r"above|over|below|under|less than|greater than|at least|at or above|at or below"
    patterns = [
        re.compile(
            rf"\b(?P<asset>bitcoin|btc|ethereum|eth)\b.*?\b(?P<side>{side_pattern})\s+\$?(?P<th>[0-9][0-9,]*(?:\.\d+)?)(?P<suf>[kmb])?",
            re.I,
        ),
        re.compile(
            rf"\b(?P<side>{side_pattern})\s+\$?(?P<th>[0-9][0-9,]*(?:\.\d+)?)(?P<suf>[kmb])?.*?\b(?P<asset>bitcoin|btc|ethereum|eth)\b",
            re.I,
        ),
    ]
    for pattern in patterns:
        match = pattern.search(text)
        if not match:
            continue
        raw_asset = match.group("asset").lower()
        asset = "BTC" if raw_asset in {"bitcoin", "btc"} else "ETH"
        side = match.group("side").lower()
        side = {
            "less than": "below",
            "at or below": "below",
            "greater than": "above",
            "at least": "above",
            "at or above": "above",
        }.get(side, side)
        threshold = float(match.group("th").replace(",", ""))
        suffix = (match.group("suf") or "").lower()
        if suffix == "k":
            threshold *= 1_000
        elif suffix == "m":
            threshold *= 1_000_000
        elif suffix == "b":
            threshold *= 1_000_000_000
        return asset, side, threshold
    return None, None, None


def parse_range(text: str) -> tuple[str | None, float | None, float | None]:
    pattern = re.compile(
        r"\b(?P<asset>bitcoin|btc|ethereum|eth)\b.*?\bbetween\s+\$?(?P<lo>[0-9][0-9,]*(?:\.\d+)?)(?P<losuf>[kmb])?\s+(?:and|-)\s+\$?(?P<hi>[0-9][0-9,]*(?:\.\d+)?)(?P<hisuf>[kmb])?",
        re.I,
    )
    match = pattern.search(text)
    if not match:
        return None, None, None
    raw_asset = match.group("asset").lower()
    asset = "BTC" if raw_asset in {"bitcoin", "btc"} else "ETH"

    def parse_amount(value: str, suffix: str | None) -> float:
        amount = float(value.replace(",", ""))
        suffix = (suffix or "").lower()
        if suffix == "k":
            amount *= 1_000
        elif suffix == "m":
            amount *= 1_000_000
        elif suffix == "b":
            amount *= 1_000_000_000
        return amount

    return asset, parse_amount(match.group("lo"), match.group("losuf")), parse_amount(match.group("hi"), match.group("hisuf"))


def crypto_type_and_weight(text: str, threshold: float | None, *, is_range: bool = False) -> tuple[str, float, float]:
    lowered = text.lower()
    if is_range:
        return "range_bucket", 0.95, 0.95
    if threshold is not None:
        if re.search(r"\bon\b", lowered) and not re.search(r"\b(hit|touch|reach|ath|all-time high)\b", lowered):
            return "close_threshold", 1.0, 1.0
        return "barrier_threshold", 0.72, 0.80
    if re.search(r"\b(all[- ]time high|ath|record high|reach)\b", lowered):
        return "record_or_race", 0.48, 0.60
    if re.search(r"\b(etf|sec|approval|blackrock|coinbase|binance|kraken|insolvent|lawsuit)\b", lowered):
        return "institutional_proxy", 0.28, 0.42
    if re.search(r"\bor\b", lowered):
        return "relative_proxy", 0.24, 0.38
    return "semantic_proxy", 0.18, 0.30


def classify_crypto(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        text = record["search_text"]
        assets = asset_mentions(text)
        if not assets:
            continue
        range_asset, range_low, range_high = parse_range(text)
        if range_asset is not None:
            market_type, relevance, specificity = crypto_type_and_weight(text, None, is_range=True)
            rows.append(
                {
                    **record,
                    "target": range_asset,
                    "market_type": market_type,
                    "threshold": range_low,
                    "threshold_high": range_high,
                    "threshold_side": "between",
                    "relevance": relevance,
                    "specificity": specificity,
                    "semantic_weight": relevance * specificity,
                }
            )
            continue
        threshold_asset, threshold_side, threshold = parse_threshold(text)
        market_type, relevance, specificity = crypto_type_and_weight(text, threshold)
        target_assets = [threshold_asset] if threshold_asset else assets
        for asset in target_assets:
            if asset is None:
                continue
            row = {
                **record,
                "target": asset,
                "market_type": market_type,
                "threshold": threshold,
                "threshold_high": None,
                "threshold_side": threshold_side,
                "relevance": relevance,
                "specificity": specificity,
                "semantic_weight": relevance * specificity,
            }
            rows.append(row)
    return rows


OPENAI_DIRECT_TERMS = [
    r"\bopenai\b",
    r"\bchatgpt\b",
    r"\bgpt[- ]?[45]\b",
    r"\bgpt[- ]?5\b",
    r"\bsora\b",
    r"\bsam altman\b",
    r"\baltman\b",
]
OPENAI_COMPETITOR_TERMS = [
    r"\banthropic\b",
    r"\bclaude\b",
    r"\bgemini\b",
    r"\bgoogle ai\b",
    r"\bgrok\b",
    r"\bxai\b",
    r"\bdeepseek\b",
    r"\bmistral\b",
    r"\bperplexity\b",
    r"\bmeta ai\b",
    r"\bllama\b",
]
AI_SECTOR_TERMS = [
    r"\bnvidia\b",
    r"\bgpu\b",
    r"\bcompute\b",
    r"\bartificial intelligence\b",
    r"\bfrontier model\b",
    r"\bai safety\b",
    r"\bagi\b",
]


def any_pattern(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, re.I) for pattern in patterns)


def classify_openai_record(record: dict[str, Any]) -> dict[str, Any] | None:
    text = record["search_text"]
    lowered = text.lower()
    has_direct = any_pattern(text, OPENAI_DIRECT_TERMS)
    has_competitor = any_pattern(text, OPENAI_COMPETITOR_TERMS)
    has_sector = any_pattern(text, AI_SECTOR_TERMS)
    has_model_terms = re.search(r"\b(best|worst|top|leader|leaderboard|benchmark|arena|model|agi|as good as)\b", lowered)
    if (
        has_sector
        and not (has_direct or has_competitor)
        and re.search(r"\b(say|says|said|mention|mentions|mentioned|tweet|tweets|state of the union)\b", lowered)
    ):
        return None
    if not (has_direct or (has_competitor and has_model_terms) or has_sector):
        return None

    loading_sign = 1.0
    if has_competitor and not has_direct:
        loading_sign = -1.0
    if re.search(r"\b(lawsuit|sued|lose|worse|worst|bankrupt|shutdown|delayed|fail|blocked)\b", lowered) and has_direct:
        loading_sign = -1.0

    if has_direct and re.search(r"\b(market cap|valuation|ipo|go public|public ticker|tender|shares|stock)\b", lowered):
        market_type, relevance, specificity = "valuation_or_liquidity", 1.0, 0.95
    elif has_direct and re.search(r"\b(agi|best|worst|model|benchmark|arena|leaderboard|gpt|sora)\b", lowered):
        market_type, relevance, specificity = "capability_or_product", 0.70, 0.66
    elif has_direct and re.search(r"\b(elon|musk|lawsuit|court|board|altman|microsoft|for-profit|nonprofit)\b", lowered):
        market_type, relevance, specificity = "legal_governance", 0.50, 0.52
    elif has_direct:
        market_type, relevance, specificity = "openai_semantic", 0.44, 0.46
    elif has_competitor and has_model_terms:
        market_type, relevance, specificity = "competitor_capability", 0.36, 0.44
    else:
        market_type, relevance, specificity = "ai_sector_proxy", 0.18, 0.26

    maturity = 0.55
    end_dt = record.get("end_dt")
    if isinstance(end_dt, datetime):
        mismatch_days = abs((end_dt - OPENAI_TARGET_DATE).days)
        maturity = math.exp(-mismatch_days / 730)
        maturity = max(0.18, min(1.0, maturity))

    return {
        **record,
        "target": "OPENAI",
        "market_type": market_type,
        "loading_sign": loading_sign,
        "relevance": relevance,
        "specificity": specificity,
        "maturity_fit": maturity,
        "semantic_weight": relevance * specificity * maturity,
    }


def classify_openai(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for record in records:
        row = classify_openai_record(record)
        if row is not None:
            rows.append(row)
    return rows


def resolved_yes_outcome(row: dict[str, Any]) -> int | None:
    if row.get("yes_price") is None:
        return None
    if not row.get("closed") and row.get("yes_price") not in (0, 1):
        return None
    yes = float(row["yes_price"])
    if yes >= 0.98:
        return 1
    if yes <= 0.02:
        return 0
    return None


def fetch_history(token_id: str, end_dt: datetime, *, lookback_days: int) -> list[dict[str, float]]:
    end_ts = int(end_dt.timestamp())
    start_ts = int((end_dt - timedelta(days=lookback_days)).timestamp())
    data = http_json(
        CLOB_HISTORY_URL,
        body={
            "markets": [token_id],
            "start_ts": start_ts,
            "end_ts": end_ts,
            "interval": "1h",
            "fidelity": 60,
        },
        timeout=45,
    )
    rows = (data.get("history") or {}).get(token_id) if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return []
    clean = []
    for item in rows:
        price = parse_float(item.get("p"))
        ts = parse_float(item.get("t"))
        if price is not None and ts is not None:
            clean.append({"t": float(ts), "p": min(0.999, max(0.001, float(price)))})
    clean.sort(key=lambda item: item["t"])
    return clean


def price_as_of(history: list[dict[str, float]], cutoff_ts: float, *, max_age_hours: float) -> float | None:
    eligible = [row for row in history if row["t"] <= cutoff_ts]
    if not eligible:
        return None
    latest = eligible[-1]
    if cutoff_ts - latest["t"] > max_age_hours * 3600:
        return None
    return latest["p"]


def build_crypto_validation(rows: list[dict[str, Any]], *, history_limit: int) -> list[dict[str, Any]]:
    direct = [
        row
        for row in rows
        if row["market_type"] == "close_threshold"
        and row.get("yes_token_id")
        and isinstance(row.get("end_dt"), datetime)
        and resolved_yes_outcome(row) is not None
    ]
    direct.sort(key=lambda row: (row["end_dt"], row["target"], row["threshold"] or 0))
    if history_limit > 0:
        direct = direct[:history_limit]

    output: list[dict[str, Any]] = []
    for idx, row in enumerate(direct, start=1):
        try:
            history = fetch_history(row["yes_token_id"], row["end_dt"], lookback_days=10)
        except Exception as exc:  # noqa: BLE001
            row_out = {**row, "history_error": str(exc)}
            output.append(row_out)
            continue
        if idx % 25 == 0:
            print(f"fetched crypto CLOB history for {idx}/{len(direct)} direct markets")
        end_ts = row["end_dt"].timestamp()
        y = resolved_yes_outcome(row)
        enriched = {
            **row,
            "settled_yes": y,
            "history_points": len(history),
            "p_7d": price_as_of(history, end_ts - 7 * 86400, max_age_hours=36),
            "p_72h": price_as_of(history, end_ts - 72 * 3600, max_age_hours=18),
            "p_48h": price_as_of(history, end_ts - 48 * 3600, max_age_hours=18),
            "p_24h": price_as_of(history, end_ts - 24 * 3600, max_age_hours=12),
            "p_6h": price_as_of(history, end_ts - 6 * 3600, max_age_hours=8),
            "p_final": price_as_of(history, end_ts - 3600, max_age_hours=8),
        }
        output.append(enriched)
        time.sleep(0.035)
    return output


def score_binary(p: float, y: int) -> dict[str, float]:
    p = min(0.999, max(0.001, p))
    return {
        "brier": (p - y) ** 2,
        "log_loss": -(y * math.log(p) + (1 - y) * math.log(1 - p)),
        "accuracy": 1.0 if (p >= 0.5) == bool(y) else 0.0,
        "realized_side_probability": p if y else 1 - p,
    }


def summarize_validation(rows: list[dict[str, Any]]) -> dict[str, Any]:
    horizons = {
        "7d": "p_7d",
        "72h": "p_72h",
        "48h": "p_48h",
        "24h": "p_24h",
        "6h": "p_6h",
        "final": "p_final",
    }
    summary: dict[str, Any] = {}
    for horizon, key in horizons.items():
        scored = []
        for row in rows:
            y = row.get("settled_yes")
            p = row.get(key)
            if y in (0, 1) and p is not None:
                scored.append(score_binary(float(p), int(y)) | {"asset": row["target"]})
        by_asset: dict[str, Any] = {}
        for asset in ["BTC", "ETH"]:
            subset = [row for row in scored if row["asset"] == asset]
            by_asset[asset] = aggregate_scores(subset)
        summary[horizon] = aggregate_scores(scored) | {"by_asset": by_asset}
    return summary


def aggregate_scores(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"n": 0}
    return {
        "n": len(rows),
        "brier": mean(row["brier"] for row in rows),
        "log_loss": mean(row["log_loss"] for row in rows),
        "accuracy": mean(row["accuracy"] for row in rows),
        "realized_side_probability": mean(row["realized_side_probability"] for row in rows),
    }


def month_span(rows: list[dict[str, Any]]) -> dict[str, Any]:
    months = sorted({row["end_date"][:7] for row in rows if row.get("end_date")})
    dates = sorted(row["end_date"][:10] for row in rows if row.get("end_date"))
    return {
        "start_date": dates[0] if dates else None,
        "end_date": dates[-1] if dates else None,
        "months": len(months),
        "month_labels": months,
    }


def pool_summary(rows: list[dict[str, Any]], *, target_key: str = "target") -> dict[str, Any]:
    by_target_type: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        by_target_type[row[target_key]][row["market_type"]] += 1
    weights = [float(row.get("semantic_weight") or 0.0) for row in rows]
    effective_n = (sum(weights) ** 2 / sum(w * w for w in weights)) if any(weights) else 0.0
    return {
        "total_markets": len(rows),
        "active_markets": sum(1 for row in rows if row.get("active") and not row.get("closed")),
        "closed_markets": sum(1 for row in rows if row.get("closed")),
        "effective_market_count": effective_n,
        "span": month_span(rows),
        "by_target_type": {target: dict(counter) for target, counter in by_target_type.items()},
    }


def logit(p: float) -> float:
    p = min(0.999, max(0.001, p))
    return math.log(p / (1 - p))


def openai_payoff(question: str) -> list[float] | None:
    text = question.lower().replace(",", "")
    payoff = [0.0] * (1 + len(OPENAI_BUCKETS))
    if "not ipo by december 31 2027" in text:
        payoff[0] = 1.0
        return payoff
    if "market cap" not in text and "ipo closing" not in text:
        return None
    if "openai" not in text:
        return None
    if "less than $500b" in text:
        payoff[1] = 1.0
        return payoff

    between = re.search(r"between \$(?P<lo>[0-9.]+)t?b? and \$(?P<hi>[0-9.]+)t?b?", text)
    if between:
        lo = openai_amount_to_b(between.group("lo"), text[between.start("lo") : between.end("lo") + 2])
        hi = openai_amount_to_b(between.group("hi"), text[between.start("hi") : between.end("hi") + 2])
        for idx, (_label, _rep, bucket_lo, bucket_hi) in enumerate(OPENAI_BUCKETS, start=1):
            if bucket_lo >= lo and bucket_hi <= hi:
                payoff[idx] = 1.0
        return payoff if any(payoff) else None

    threshold = re.search(r"above \$(?P<th>[0-9.]+)t?b?", text)
    if not threshold and "$1.5t or greater" in text:
        threshold_b = 1500.0
    elif threshold:
        threshold_b = openai_amount_to_b(threshold.group("th"), text[threshold.start("th") : threshold.end("th") + 2])
    else:
        return None
    for idx, (_label, rep, _lo, _hi) in enumerate(OPENAI_BUCKETS, start=1):
        if rep >= threshold_b:
            payoff[idx] = 1.0
    return payoff


def openai_amount_to_b(raw: str, context: str) -> float:
    value = float(raw)
    if "t" in context.lower():
        return value * 1000
    return value


def build_openai_projection(rows: list[dict[str, Any]]) -> dict[str, Any]:
    observations = []
    for row in rows:
        if row.get("closed") or row.get("yes_price") is None:
            continue
        payoff = openai_payoff(str(row.get("question") or ""))
        if payoff is None:
            continue
        volume = float(row.get("volume") or 0.0)
        observations.append(
            {
                "question": row["question"],
                "p": float(row["yes_price"]),
                "weight": max(1.0, math.log1p(volume) / 3.0),
                "payoff": payoff,
            }
        )
    if not observations:
        return {}

    a = np.array([obs["payoff"] for obs in observations], dtype=float)
    p = np.array([obs["p"] for obs in observations], dtype=float)
    w = np.array([obs["weight"] for obs in observations], dtype=float)
    reps = np.array([0.0] + [bucket[1] for bucket in OPENAI_BUCKETS], dtype=float)

    def objective_for(p_vec: np.ndarray):
        def objective(q: np.ndarray) -> float:
            residual = a @ q - p_vec
            smooth = np.diff(q[1:], n=2)
            return float(np.sum(w * residual * residual) + 0.002 * np.sum(smooth * smooth))

        return objective

    def solve(p_vec: np.ndarray, x0: np.ndarray) -> tuple[np.ndarray, Any, float]:
        objective = objective_for(p_vec)
        result = minimize(
            objective,
            x0,
            method="SLSQP",
            bounds=[(0.0, 1.0)] * len(x0),
            constraints=[{"type": "eq", "fun": lambda q: float(np.sum(q) - 1.0)}],
            options={"maxiter": 2000, "ftol": 1e-12},
        )
        q_vec = result.x if result.success else x0
        q_vec = np.maximum(q_vec, 0)
        q_vec = q_vec / q_vec.sum()
        return q_vec, result, objective(q_vec)

    def objective(q: np.ndarray) -> float:
        residual = a @ q - p
        smooth = np.diff(q[1:], n=2)
        return float(np.sum(w * residual * residual) + 0.002 * np.sum(smooth * smooth))

    initial = np.ones(1 + len(OPENAI_BUCKETS), dtype=float) / (1 + len(OPENAI_BUCKETS))
    no_ipo_obs = [obs["p"] for obs in observations if "not ipo by december 31 2027" in obs["question"].lower().replace(",", "")]
    if no_ipo_obs:
        initial[0] = no_ipo_obs[0]
        initial[1:] = (1 - initial[0]) / len(OPENAI_BUCKETS)
    q, result, loss = solve(p, initial)
    expected_unconditional = float(np.sum(q * reps))
    ipo_probability = float(1 - q[0])
    expected_conditional = expected_unconditional / ipo_probability if ipo_probability > 0 else None
    fitted = a @ q
    residuals = []
    for obs, fit in zip(observations, fitted, strict=False):
        residuals.append(
            {
                "market": obs["question"],
                "observed": obs["p"],
                "fitted": float(fit),
                "residual": float(fit - obs["p"]),
                "weight": obs["weight"],
            }
        )
    residuals.sort(key=lambda row: abs(row["residual"]), reverse=True)
    stress_moves = []
    for idx, obs in enumerate(observations):
        for direction in [-1, 1]:
            shocked_p = p.copy()
            shocked_p[idx] = min(0.999, max(0.001, shocked_p[idx] + direction * 0.05))
            shocked_q, _shocked_result, _shocked_loss = solve(shocked_p, q)
            shocked_expected = float(np.sum(shocked_q * reps))
            stress_moves.append(
                {
                    "market": obs["question"],
                    "direction": direction,
                    "shocked_probability": float(shocked_p[idx]),
                    "index_b": shocked_expected,
                    "move_b": shocked_expected - expected_unconditional,
                    "abs_move_b": abs(shocked_expected - expected_unconditional),
                }
            )
    stress_moves.sort(key=lambda row: row["abs_move_b"], reverse=True)
    median_move = sorted(row["abs_move_b"] for row in stress_moves)[len(stress_moves) // 2] if stress_moves else 0.0
    max_move = stress_moves[0]["abs_move_b"] if stress_moves else 0.0
    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "target": "OpenAI 2027-12-31",
        "source": "Polymarket Gamma API active valuation markets",
        "success": bool(result.success),
        "loss": float(loss),
        "observations": len(observations),
        "no_ipo_probability": float(q[0]),
        "ipo_probability": ipo_probability,
        "expected_unconditional_b": expected_unconditional,
        "expected_conditional_b": expected_conditional,
        "buckets": [
            {
                "bucket": "No IPO",
                "probability": float(q[0]),
                "conditional_on_ipo": None,
                "representative_b": 0.0,
            }
        ]
        + [
            {
                "bucket": label,
                "probability": float(q[idx]),
                "conditional_on_ipo": float(q[idx] / ipo_probability) if ipo_probability > 0 else None,
                "representative_b": rep,
            }
            for idx, (label, rep, _lo, _hi) in enumerate(OPENAI_BUCKETS, start=1)
        ],
        "residuals": residuals,
        "stress": {
            "shock": 0.05,
            "baseline_unconditional_b": expected_unconditional,
            "max_one_market_move_b": max_move,
            "median_one_market_move_b": median_move,
            "stress_confidence_score": max(0.0, 1.0 - max_move / expected_unconditional) if expected_unconditional else None,
            "moves": stress_moves,
        },
    }


def write_openai_projection(projection: dict[str, Any]) -> None:
    if not projection:
        return
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "openai_20271231_projection.json").write_text(json.dumps(projection, indent=2), encoding="utf-8")
    stress_payload = {
        "generated_at": projection["generated_at"],
        "target": projection["target"],
        "source": projection["source"],
        **projection["stress"],
    }
    (DATA / "openai_20271231_oracle_stress.json").write_text(json.dumps(stress_payload, indent=2), encoding="utf-8")
    lines = [
        "# Projection: OpenAI 2027-12-31",
        "",
        f"Generated: `{projection['generated_at']}`",
        f"Loss: `{projection['loss']:.6f}`",
        f"Observations: `{projection['observations']}`",
        "",
        "## Implied Distribution",
        "",
        f"- No IPO probability: `{projection['no_ipo_probability']:.3f}`",
        f"- IPO probability: `{projection['ipo_probability']:.3f}`",
        f"- Expected valuation, unconditional: `${projection['expected_unconditional_b']:,.0f}B`",
        f"- Expected valuation, conditional on IPO: `${projection['expected_conditional_b']:,.0f}B`",
        "",
        "| Bucket | Probability | Conditional on IPO | Representative |",
        "|---|---:|---:|---:|",
    ]
    for row in projection["buckets"][1:]:
        cond = "n/a" if row["conditional_on_ipo"] is None else f"{row['conditional_on_ipo']:.3f}"
        lines.append(
            f"| {row['bucket']} | {row['probability']:.3f} | {cond} | ${row['representative_b']:,.0f}B |"
        )
    lines.extend(
        [
            "",
            "## Residuals",
            "",
            "| Observed | Fitted | Residual | Weight | Market |",
            "|---:|---:|---:|---:|---|",
        ]
    )
    for row in projection["residuals"]:
        market = str(row["market"]).replace("|", "/")
        lines.append(
            f"| {row['observed']:.3f} | {row['fitted']:.3f} | {row['residual']:+.3f} | {row['weight']:.2f} | {market} |"
        )
    (DATA / "openai_20271231_projection.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    stress = projection["stress"]
    stress_lines = [
        "# OpenAI 2027 Oracle Stress",
        "",
        f"Generated: `{projection['generated_at']}`",
        f"Shock: `+/- {stress['shock']:.2f}` YES probability",
        "",
        "## Summary",
        "",
        f"- Baseline unconditional index: `${stress['baseline_unconditional_b']:,.0f}B`",
        f"- Max one-market index move: `${stress['max_one_market_move_b']:,.0f}B`",
        f"- Median one-market index move: `${stress['median_one_market_move_b']:,.0f}B`",
        f"- Stress confidence score: `{stress['stress_confidence_score']:.3f}`",
        "",
        "## Largest Moves",
        "",
        "| Abs move | Direction | Shocked P | Market |",
        "|---:|---:|---:|---|",
    ]
    for row in stress["moves"][:12]:
        market = str(row["market"]).replace("|", "/")
        stress_lines.append(f"| ${row['abs_move_b']:,.0f}B | {row['direction']:+d} | {row['shocked_probability']:.3f} | {market} |")
    (DATA / "openai_20271231_oracle_stress.md").write_text("\n".join(stress_lines) + "\n", encoding="utf-8")


def summarize_openai(rows: list[dict[str, Any]], projection: dict[str, Any]) -> dict[str, Any]:
    direct_unconditional = parse_float(projection.get("expected_unconditional_b")) or 932.0
    direct_conditional = parse_float(projection.get("expected_conditional_b")) or 1328.0
    active = [
        row
        for row in rows
        if not row.get("closed")
        and row.get("market_type") != "valuation_or_liquidity"
        and row.get("yes_price") is not None
        and 0.001 < float(row["yes_price"]) < 0.999
    ]
    weighted_signal_num = 0.0
    weighted_signal_den = 0.0
    for row in active:
        w = float(row.get("semantic_weight") or 0.0)
        signed = float(row.get("loading_sign") or 1.0) * logit(float(row["yes_price"]))
        weighted_signal_num += w * signed
        weighted_signal_den += abs(w)
    signal = weighted_signal_num / weighted_signal_den if weighted_signal_den else 0.0
    shrinkage = 0.08
    multiplier = math.exp(shrinkage * math.tanh(signal / 2.0))
    return {
        "pool": pool_summary(rows),
        "active_signal": {
            "n": len(active),
            "weighted_logit_signal": signal,
            "shrinkage": shrinkage,
            "semantic_multiplier": multiplier,
            "direct_unconditional_b": direct_unconditional,
            "semantic_adjusted_unconditional_b": direct_unconditional * multiplier,
            "direct_conditional_b": direct_conditional,
            "semantic_adjusted_conditional_b": direct_conditional * multiplier,
        },
    }


def serializable(row: dict[str, Any]) -> dict[str, Any]:
    output = dict(row)
    output.pop("search_text", None)
    output.pop("end_dt", None)
    return output


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def fmt_pct(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{float(value) * 100:.1f}%"


def write_crypto_outputs(rows: list[dict[str, Any]], validation: list[dict[str, Any]]) -> dict[str, Any]:
    DATA.mkdir(parents=True, exist_ok=True)
    summary = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "source": "Polymarket Gamma API and CLOB batch-prices-history",
        "pool": pool_summary(rows),
        "direct_threshold_validation": summarize_validation(validation),
    }
    payload = {
        **summary,
        "markets": [serializable(row) for row in rows],
        "validation_rows": [serializable(row) for row in validation],
    }
    (DATA / "polymarket_crypto_entity_pool.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_csv(
        DATA / "polymarket_crypto_entity_pool.csv",
        [serializable(row) for row in rows],
        [
            "target",
            "market_type",
            "semantic_weight",
            "threshold",
            "threshold_high",
            "threshold_side",
            "question",
            "end_date",
            "closed",
            "active",
            "yes_price",
            "volume",
            "liquidity",
            "market_id",
            "slug",
        ],
    )
    write_csv(
        DATA / "polymarket_crypto_threshold_validation.csv",
        [serializable(row) for row in validation],
        [
            "target",
            "question",
            "end_date",
            "threshold",
            "threshold_side",
            "settled_yes",
            "history_points",
            "p_7d",
            "p_72h",
            "p_48h",
            "p_24h",
            "p_6h",
            "p_final",
            "market_id",
            "slug",
        ],
    )
    pool = summary["pool"]
    val = summary["direct_threshold_validation"]
    lines = [
        "# Polymarket Crypto Entity Pool",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Pool Coverage",
        "",
        f"- Markets: `{pool['total_markets']}`",
        f"- Closed markets: `{pool['closed_markets']}`",
        f"- Active markets: `{pool['active_markets']}`",
        f"- Effective semantic market count: `{pool['effective_market_count']:.1f}`",
        f"- Date span: `{pool['span']['start_date']}` to `{pool['span']['end_date']}`",
        f"- Months covered: `{pool['span']['months']}`",
        "",
        "| Target | Market type | Count |",
        "|---|---|---:|",
    ]
    for target, counter in sorted(pool["by_target_type"].items()):
        for market_type, count in sorted(counter.items()):
            lines.append(f"| {target} | `{market_type}` | {count} |")
    lines.extend(
        [
            "",
            "## Direct Threshold Validation",
            "",
            "| Horizon | N | Brier | Log loss | Accuracy | Mean probability on realized side |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for horizon in ["7d", "72h", "48h", "24h", "6h", "final"]:
        row = val[horizon]
        lines.append(
            f"| {horizon} | {fmt(row.get('n'), 0)} | {fmt(row.get('brier'))} | {fmt(row.get('log_loss'))} | "
            f"{fmt_pct(row.get('accuracy'))} | {fmt_pct(row.get('realized_side_probability'))} |"
        )
    (DATA / "polymarket_crypto_entity_pool.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


def write_openai_outputs(rows: list[dict[str, Any]]) -> dict[str, Any]:
    DATA.mkdir(parents=True, exist_ok=True)
    projection = build_openai_projection(rows)
    write_openai_projection(projection)
    summary = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "source": "Polymarket Gamma API",
        **summarize_openai(rows, projection),
    }
    payload = {**summary, "markets": [serializable(row) for row in rows]}
    (DATA / "openai_semantic_market_pool.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_csv(
        DATA / "openai_semantic_market_pool.csv",
        [serializable(row) for row in rows],
        [
            "market_type",
            "semantic_weight",
            "loading_sign",
            "maturity_fit",
            "question",
            "end_date",
            "closed",
            "active",
            "yes_price",
            "volume",
            "liquidity",
            "market_id",
            "slug",
        ],
    )
    pool = summary["pool"]
    signal = summary["active_signal"]
    lines = [
        "# OpenAI Semantic Market Pool",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Pool Coverage",
        "",
        f"- Markets: `{pool['total_markets']}`",
        f"- Closed markets: `{pool['closed_markets']}`",
        f"- Active markets: `{pool['active_markets']}`",
        f"- Effective semantic market count: `{pool['effective_market_count']:.1f}`",
        f"- Date span: `{pool['span']['start_date']}` to `{pool['span']['end_date']}`",
        f"- Months covered: `{pool['span']['months']}`",
        "",
        "| Market type | Count |",
        "|---|---:|",
    ]
    for market_type, count in sorted(pool["by_target_type"].get("OPENAI", {}).items()):
        lines.append(f"| `{market_type}` | {count} |")
    lines.extend(
        [
            "",
            "## Semantic Signal",
            "",
            f"- Active priced markets used in signal: `{signal['n']}`",
            f"- Weighted logit signal: `{signal['weighted_logit_signal']:.3f}`",
            f"- Conservative semantic multiplier: `{signal['semantic_multiplier']:.3f}`",
            f"- Direct valuation index: `${signal['direct_unconditional_b']:.0f}B`",
            f"- Semantic-adjusted valuation index: `${signal['semantic_adjusted_unconditional_b']:.0f}B`",
            "",
            "## Highest-Weight Active Markets",
            "",
            "| Weight | Direction | Type | YES price | Market |",
            "|---:|---:|---|---:|---|",
        ]
    )
    active = [row for row in rows if not row.get("closed") and row.get("yes_price") is not None]
    active.sort(key=lambda row: float(row.get("semantic_weight") or 0.0), reverse=True)
    for row in active[:12]:
        question = str(row["question"]).replace("|", "/")
        lines.append(
            f"| {row['semantic_weight']:.3f} | {row['loading_sign']:+.0f} | `{row['market_type']}` | "
            f"{float(row['yes_price']):.3f} | {question} |"
        )
    (DATA / "openai_semantic_market_pool.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--crypto-pages", type=int, default=18, help="100-event pages per crypto closed/open status")
    parser.add_argument("--openai-pages", type=int, default=14, help="100-event pages per OpenAI tag/status")
    parser.add_argument("--history-limit", type=int, default=500, help="max direct threshold markets to fetch CLOB history for")
    args = parser.parse_args()

    print("fetching Polymarket crypto events")
    crypto_events = fetch_events(CRYPTO_TAGS, max_pages=args.crypto_pages)
    crypto_records = iter_market_records(crypto_events)
    crypto_rows = classify_crypto(crypto_records)
    print(f"classified {len(crypto_rows)} BTC/ETH crypto markets")
    crypto_validation = build_crypto_validation(crypto_rows, history_limit=args.history_limit)
    crypto_payload = write_crypto_outputs(crypto_rows, crypto_validation)
    print(
        "wrote crypto pool:",
        crypto_payload["pool"]["total_markets"],
        "markets,",
        crypto_payload["pool"]["span"]["months"],
        "months",
    )

    print("fetching Polymarket OpenAI/AI events")
    openai_events = fetch_events(OPENAI_TAGS, max_pages=args.openai_pages)
    openai_records = iter_market_records(openai_events)
    openai_rows = classify_openai(openai_records)
    openai_payload = write_openai_outputs(openai_rows)
    print(
        "wrote OpenAI pool:",
        openai_payload["pool"]["total_markets"],
        "markets,",
        openai_payload["pool"]["span"]["months"],
        "months",
    )


if __name__ == "__main__":
    main()
