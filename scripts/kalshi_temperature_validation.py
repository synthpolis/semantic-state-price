from __future__ import annotations

import argparse
import csv
import json
import re
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
KALSHI_BASE_URL = "https://external-api.kalshi.com/trade-api/v2"
NWS_PRODUCTS_URL = "https://api.weather.gov/products"
USER_AGENT = "semantic-state-price-research ojas@example.com"

DATE_FMT = "%Y-%m-%d"
TITLE_BRACKET_RE = re.compile(r"\b(\d+)-(\d+)\s*°")
TITLE_ABOVE_RE = re.compile(r">\s*(-?\d+(?:\.\d+)?)\s*°")
TITLE_BELOW_RE = re.compile(r"<\s*(-?\d+(?:\.\d+)?)\s*°")
MAXIMUM_RE = re.compile(r"^\s*MAXIMUM\s+(-?\d+)\b", re.MULTILINE)


def get_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/geo+json"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read())


def parse_float(raw: Any) -> float | None:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if value != value:
        return None
    return value


def date_token(target_date: date) -> str:
    return target_date.strftime("%y%b%d").upper()


def fetch_markets(series: str, target_date: date) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode({"limit": 1000, "series_ticker": series})
    payload = get_json(f"{KALSHI_BASE_URL}/markets?{params}")
    token = f"{series}-{date_token(target_date)}"
    rows = [row for row in payload.get("markets", []) if str(row.get("ticker", "")).startswith(token)]
    if not rows:
        raise SystemExit(f"no Kalshi markets found for {series} {target_date.isoformat()}")
    return rows


def parse_temperature_market(row: dict[str, Any]) -> dict[str, Any] | None:
    title = str(row.get("title") or "")
    bracket = TITLE_BRACKET_RE.search(title)
    if bracket:
        lower = float(bracket.group(1))
        upper = float(bracket.group(2))
        return {
            "ticker": row["ticker"],
            "title": title,
            "relation": "between",
            "lower": lower,
            "upper": upper,
            "representative": (lower + upper) / 2,
            "sort_key": lower,
        }
    above = TITLE_ABOVE_RE.search(title)
    if above:
        threshold = float(above.group(1))
        return {
            "ticker": row["ticker"],
            "title": title,
            "relation": "above",
            "lower": threshold,
            "upper": None,
            "representative": threshold + 1.0,
            "sort_key": threshold + 0.1,
        }
    below = TITLE_BELOW_RE.search(title)
    if below:
        threshold = float(below.group(1))
        return {
            "ticker": row["ticker"],
            "title": title,
            "relation": "below",
            "lower": None,
            "upper": threshold,
            "representative": threshold - 1.0,
            "sort_key": threshold - 0.1,
        }
    return None


def market_probability(row: dict[str, Any]) -> float:
    bid = parse_float(row.get("yes_bid_dollars"))
    ask = parse_float(row.get("yes_ask_dollars"))
    if bid is not None and ask is not None and 0 <= bid <= ask <= 1:
        return (bid + ask) / 2
    price = parse_float(row.get("last_price_dollars"))
    return price if price is not None else 0.0


def fetch_candles(series: str, ticker: str, start: datetime, end: datetime) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode(
        {
            "start_ts": int(start.timestamp()),
            "end_ts": int(end.timestamp()),
            "period_interval": 60,
        }
    )
    payload = get_json(f"{KALSHI_BASE_URL}/series/{series}/markets/{ticker}/candlesticks?{params}")
    return payload.get("candlesticks", [])


def candle_probability(candle: dict[str, Any]) -> float | None:
    bid = parse_float((candle.get("yes_bid") or {}).get("close_dollars"))
    ask = parse_float((candle.get("yes_ask") or {}).get("close_dollars"))
    if bid is not None and ask is not None and 0 <= bid <= ask <= 1:
        return (bid + ask) / 2
    price = parse_float((candle.get("price") or {}).get("close_dollars"))
    return price if price is not None else None


def actual_temperature_from_nws(location: str, target_date: date) -> dict[str, Any]:
    products = get_json(f"{NWS_PRODUCTS_URL}/types/CLI/locations/{location}")
    target_label = target_date.strftime("%B %-d %Y") if hasattr(target_date, "strftime") else ""
    for product in products.get("@graph", []):
        product_id = product.get("id")
        if not product_id:
            continue
        detail = get_json(f"{NWS_PRODUCTS_URL}/{product_id}")
        text = detail.get("productText") or ""
        if f"SUMMARY FOR {target_date.strftime('%B').upper()} {target_date.day} {target_date.year}" not in text.upper():
            continue
        match = MAXIMUM_RE.search(text)
        if not match:
            continue
        return {
            "source": "NWS Daily Climate Report",
            "location": location,
            "product_id": product_id,
            "issuance_time": detail.get("issuanceTime"),
            "target_label": target_label,
            "actual_high_f": int(match.group(1)),
        }
    raise SystemExit(f"could not find NWS CLI maximum for {location} {target_date.isoformat()}")


def bucket_contains(row: dict[str, Any], value: float) -> bool:
    if row["relation"] == "below":
        return value < row["upper"]
    if row["relation"] == "above":
        return value > row["lower"]
    return row["lower"] <= value <= row["upper"]


def project_snapshot(market_rows: list[dict[str, Any]], probabilities: dict[str, float], actual: float, ts: int | None = None) -> dict[str, Any]:
    raw = [max(0.0, probabilities.get(row["ticker"], 0.0)) for row in market_rows]
    raw_sum = sum(raw)
    normalized = [value / raw_sum for value in raw] if raw_sum > 0 else [0.0 for _ in raw]
    expected = sum(prob * row["representative"] for prob, row in zip(normalized, market_rows, strict=False))
    actual_prob = sum(prob for prob, row in zip(normalized, market_rows, strict=False) if bucket_contains(row, actual))
    modal_index = max(range(len(normalized)), key=lambda idx: normalized[idx]) if normalized else 0
    return {
        "ts": ts,
        "time": datetime.fromtimestamp(ts, UTC).isoformat(timespec="seconds").replace("+00:00", "Z") if ts else None,
        "raw_probability_sum": raw_sum,
        "expected_high_f": expected,
        "abs_error_f": abs(expected - actual),
        "actual_bucket_probability": actual_prob,
        "modal_bucket": bucket_label(market_rows[modal_index]) if market_rows else None,
        "modal_probability": normalized[modal_index] if normalized else None,
        "actual_inside_modal": bucket_contains(market_rows[modal_index], actual) if market_rows else False,
        "bucket_probabilities": [
            {
                "ticker": row["ticker"],
                "bucket": bucket_label(row),
                "probability": prob,
                "raw_probability": raw_prob,
            }
            for row, prob, raw_prob in zip(market_rows, normalized, raw, strict=False)
        ],
    }


def bucket_label(row: dict[str, Any]) -> str:
    if row["relation"] == "below":
        return f"<{row['upper']:g}F"
    if row["relation"] == "above":
        return f">{row['lower']:g}F"
    return f"{row['lower']:g}-{row['upper']:g}F"


def build_payload(series: str, location: str, target_date: date, lookback_hours: int) -> dict[str, Any]:
    raw_markets = fetch_markets(series, target_date)
    market_rows = [parse_temperature_market(row) for row in raw_markets]
    market_rows = sorted([row for row in market_rows if row is not None], key=lambda row: row["sort_key"])
    actual = actual_temperature_from_nws(location, target_date)
    actual_high = float(actual["actual_high_f"])

    live_probs = {
        row["ticker"]: market_probability(next(raw for raw in raw_markets if raw["ticker"] == row["ticker"]))
        for row in market_rows
    }
    latest_snapshot = project_snapshot(market_rows, live_probs, actual_high)

    end = datetime.now(UTC)
    start = end - timedelta(hours=lookback_hours)
    by_time: dict[int, dict[str, float]] = defaultdict(dict)
    for row in market_rows:
        for candle in fetch_candles(series, row["ticker"], start, end):
            ts = int(candle.get("end_period_ts") or 0)
            prob = candle_probability(candle)
            if ts and prob is not None:
                by_time[ts][row["ticker"]] = prob

    snapshots = []
    tickers = {row["ticker"] for row in market_rows}
    for ts, probs in sorted(by_time.items()):
        if tickers.issubset(probs):
            snapshots.append(project_snapshot(market_rows, probs, actual_high, ts=ts))

    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "source": "Kalshi external API candlesticks + NWS Daily Climate Report",
        "series": series,
        "nws_location": location,
        "target_date": target_date.isoformat(),
        "actual": actual,
        "markets": market_rows,
        "latest_snapshot": latest_snapshot,
        "rolling_summary": summarize_snapshots(snapshots),
        "snapshots": snapshots,
    }


def summarize_snapshots(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    if not snapshots:
        return {}
    return {
        "snapshots": len(snapshots),
        "first_time": snapshots[0]["time"],
        "last_time": snapshots[-1]["time"],
        "mean_abs_error_f": mean(row["abs_error_f"] for row in snapshots),
        "last_abs_error_f": snapshots[-1]["abs_error_f"],
        "mean_actual_bucket_probability": mean(row["actual_bucket_probability"] for row in snapshots),
        "last_actual_bucket_probability": snapshots[-1]["actual_bucket_probability"],
        "last_modal_bucket": snapshots[-1]["modal_bucket"],
        "last_actual_inside_modal": snapshots[-1]["actual_inside_modal"],
    }


def fmt(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def write_outputs(payload: dict[str, Any]) -> None:
    data_dir = ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    slug = f"kalshi_{payload['series'].lower()}_{payload['target_date'].replace('-', '')}_temperature_validation"
    json_path = data_dir / f"{slug}.json"
    csv_path = data_dir / f"{slug}.csv"
    md_path = data_dir / f"{slug}.md"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "time",
                "expected_high_f",
                "abs_error_f",
                "actual_bucket_probability",
                "modal_bucket",
                "modal_probability",
                "actual_inside_modal",
                "raw_probability_sum",
            ],
        )
        writer.writeheader()
        for row in payload["snapshots"]:
            writer.writerow({key: row.get(key) for key in writer.fieldnames})

    actual = payload["actual"]
    rolling = payload["rolling_summary"]
    latest = payload["latest_snapshot"]
    lines = [
        f"# Kalshi Temperature Validation: {payload['series']} {payload['target_date']}",
        "",
        f"Generated: `{payload['generated_at']}`",
        f"Source: `{payload['source']}`",
        "",
        "## Actual",
        "",
        f"- NWS location: `{actual['location']}`",
        f"- Actual high: `{actual['actual_high_f']}F`",
        f"- NWS issuance time: `{actual['issuance_time']}`",
        f"- NWS product ID: `{actual['product_id']}`",
        "",
        "## Rolling Validation",
        "",
        f"- Snapshots: `{rolling.get('snapshots', 0)}`",
        f"- First snapshot: `{rolling.get('first_time')}`",
        f"- Last snapshot: `{rolling.get('last_time')}`",
        f"- Mean absolute error: `{fmt(rolling.get('mean_abs_error_f'))}F`",
        f"- Last absolute error: `{fmt(rolling.get('last_abs_error_f'))}F`",
        f"- Mean actual-bucket probability: `{fmt(rolling.get('mean_actual_bucket_probability'), 3)}`",
        f"- Last actual-bucket probability: `{fmt(rolling.get('last_actual_bucket_probability'), 3)}`",
        f"- Last modal bucket: `{rolling.get('last_modal_bucket')}`",
        f"- Actual inside last modal bucket: `{rolling.get('last_actual_inside_modal')}`",
        "",
        "## Latest Distribution",
        "",
        f"- Expected high: `{fmt(latest.get('expected_high_f'))}F`",
        f"- Raw probability sum: `{fmt(latest.get('raw_probability_sum'), 3)}`",
        "",
        "| Bucket | Probability | Raw P | Ticker |",
        "|---|---:|---:|---|",
    ]
    for bucket in latest["bucket_probabilities"]:
        lines.append(
            f"| {bucket['bucket']} | {bucket['probability']:.3f} | {bucket['raw_probability']:.3f} | `{bucket['ticker']}` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This is a direct Kalshi validation of the same projection idea on a non-crypto, non-Polymarket market family. The mutually exclusive temperature contracts are treated as a noisy distribution over the realized daily high temperature and compared to the official NWS settlement source.",
        ]
    )
    md_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"wrote {json_path}")
    print(f"wrote {csv_path}")
    print(f"wrote {md_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--series", default="KXHIGHNY")
    parser.add_argument("--nws-location", default="NYC")
    parser.add_argument("--date", default="2026-05-07")
    parser.add_argument("--lookback-hours", type=int, default=96)
    args = parser.parse_args()
    target_date = datetime.strptime(args.date, DATE_FMT).date()
    write_outputs(build_payload(args.series, args.nws_location, target_date, args.lookback_hours))


if __name__ == "__main__":
    main()
