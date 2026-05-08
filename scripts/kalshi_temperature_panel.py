from __future__ import annotations

import argparse
import csv
import json
import re
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from statistics import mean, median
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
KALSHI_BASE_URL = "https://external-api.kalshi.com/trade-api/v2"
NCEI_URL = "https://www.ncei.noaa.gov/access/services/data/v1"
USER_AGENT = "semantic-state-price-research ojas@example.com"

TITLE_BRACKET_RE = re.compile(r"\b(\d+)-(\d+)\s*°")
TITLE_ABOVE_RE = re.compile(r">\s*(-?\d+(?:\.\d+)?)\s*°")
TITLE_BELOW_RE = re.compile(r"<\s*(-?\d+(?:\.\d+)?)\s*°")
DATE_TOKEN_RE = re.compile(r"-(\d{2})([A-Z]{3})(\d{2})-")

MONTHS = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}

DEFAULT_CITY_CONFIG = {
    "nyc": {"series": "KXHIGHNY", "station": "USW00094728", "label": "New York City / Central Park"},
    "chicago": {"series": "KXHIGHCHI", "station": "USW00094846", "label": "Chicago / O'Hare"},
    "miami": {"series": "KXHIGHMIA", "station": "USW00012839", "label": "Miami"},
}


@dataclass
class MarketBucket:
    ticker: str
    title: str
    relation: str
    lower: float | None
    upper: float | None
    representative: float
    close_time: datetime


def get_json(url: str) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json, text/html, */*"})
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.loads(response.read())


def parse_float(raw: Any) -> float | None:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if value != value:
        return None
    return value


def parse_ts(raw: Any) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def ticker_date(ticker: str) -> date | None:
    match = DATE_TOKEN_RE.search(ticker)
    if not match:
        return None
    year = 2000 + int(match.group(1))
    month = MONTHS.get(match.group(2))
    day = int(match.group(3))
    if not month:
        return None
    return date(year, month, day)


def parse_market(row: dict[str, Any]) -> MarketBucket | None:
    target_date = ticker_date(str(row.get("ticker") or ""))
    close_time = parse_ts(row.get("close_time"))
    if target_date is None or close_time is None:
        return None
    title = str(row.get("title") or "")
    bracket = TITLE_BRACKET_RE.search(title)
    if bracket:
        lower = float(bracket.group(1))
        upper = float(bracket.group(2))
        return MarketBucket(str(row["ticker"]), title, "between", lower, upper, (lower + upper) / 2, close_time)
    above = TITLE_ABOVE_RE.search(title)
    if above:
        threshold = float(above.group(1))
        return MarketBucket(str(row["ticker"]), title, "above", threshold, None, threshold + 1.0, close_time)
    below = TITLE_BELOW_RE.search(title)
    if below:
        threshold = float(below.group(1))
        return MarketBucket(str(row["ticker"]), title, "below", None, threshold, threshold - 1.0, close_time)
    return None


def bucket_label(row: MarketBucket) -> str:
    if row.relation == "below":
        return f"<{row.upper:g}F"
    if row.relation == "above":
        return f">{row.lower:g}F"
    return f"{row.lower:g}-{row.upper:g}F"


def contains(row: MarketBucket, actual: float) -> bool:
    if row.relation == "below":
        return actual < float(row.upper)
    if row.relation == "above":
        return actual > float(row.lower)
    return float(row.lower) <= actual <= float(row.upper)


def probability_from_candle(candle: dict[str, Any]) -> float | None:
    bid = parse_float((candle.get("yes_bid") or {}).get("close_dollars"))
    ask = parse_float((candle.get("yes_ask") or {}).get("close_dollars"))
    if bid is not None and ask is not None and 0 <= bid <= ask <= 1:
        return (bid + ask) / 2
    return parse_float((candle.get("price") or {}).get("close_dollars"))


def fetch_kalshi_markets(series: str) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode({"limit": 1000, "series_ticker": series})
    payload = get_json(f"{KALSHI_BASE_URL}/markets?{params}")
    return payload.get("markets", [])


def fetch_ncei_actuals(station: str, start: date, end: date) -> dict[date, float]:
    params = urllib.parse.urlencode(
        {
            "dataset": "daily-summaries",
            "stations": station,
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "dataTypes": "TMAX",
            "units": "standard",
            "format": "json",
        }
    )
    rows = get_json(f"{NCEI_URL}?{params}")
    actuals: dict[date, float] = {}
    for row in rows:
        if row.get("TMAX") in (None, ""):
            continue
        actuals[datetime.strptime(row["DATE"], "%Y-%m-%d").date()] = float(row["TMAX"])
    return actuals


def fetch_batch_candles(series: str, buckets: list[MarketBucket], start: datetime, end: datetime, retries: int = 3) -> dict[str, list[dict[str, Any]]]:
    params = urllib.parse.urlencode(
        {
            "market_tickers": ",".join(bucket.ticker for bucket in buckets),
            "start_ts": int(start.timestamp()),
            "end_ts": int(end.timestamp()),
            "period_interval": 60,
        }
    )
    url = f"{KALSHI_BASE_URL}/markets/candlesticks?{params}"
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            payload = get_json(url)
            return {
                market.get("market_ticker") or market.get("ticker") or buckets[idx].ticker: market.get("candlesticks", [])
                for idx, market in enumerate(payload.get("markets", []))
            }
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"failed Kalshi candles batch for {series}: {last_exc}")


def project(buckets: list[MarketBucket], probabilities: dict[str, float], actual: float, ts: int) -> dict[str, Any]:
    raw = [max(0.0, probabilities.get(bucket.ticker, 0.0)) for bucket in buckets]
    raw_sum = sum(raw)
    normalized = [value / raw_sum for value in raw] if raw_sum else [0.0 for _ in raw]
    expected = sum(prob * bucket.representative for prob, bucket in zip(normalized, buckets, strict=False))
    modal_idx = max(range(len(normalized)), key=lambda idx: normalized[idx]) if normalized else 0
    actual_bucket_p = sum(prob for prob, bucket in zip(normalized, buckets, strict=False) if contains(bucket, actual))
    return {
        "ts": ts,
        "time": datetime.fromtimestamp(ts, UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "expected_high_f": expected,
        "abs_error_f": abs(expected - actual),
        "actual_bucket_probability": actual_bucket_p,
        "modal_bucket": bucket_label(buckets[modal_idx]) if buckets else None,
        "modal_probability": normalized[modal_idx] if normalized else None,
        "actual_inside_modal": contains(buckets[modal_idx], actual) if buckets else False,
        "raw_probability_sum": raw_sum,
    }


def select_snapshot(snapshots: list[dict[str, Any]], target_ts: int, mode: str) -> dict[str, Any] | None:
    if not snapshots:
        return None
    if mode == "before":
        eligible = [row for row in snapshots if row["ts"] <= target_ts]
        return eligible[-1] if eligible else None
    return min(snapshots, key=lambda row: abs(row["ts"] - target_ts))


def summarize(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"mean": None, "median": None}
    return {"mean": mean(values), "median": median(values)}


def build_panel(start: date, end: date, cities: list[str]) -> dict[str, Any]:
    date_rows: list[dict[str, Any]] = []
    snapshot_rows: list[dict[str, Any]] = []
    city_payloads = []

    for city in cities:
        config = DEFAULT_CITY_CONFIG[city]
        series = config["series"]
        raw_markets = fetch_kalshi_markets(series)
        market_groups: dict[date, list[MarketBucket]] = defaultdict(list)
        for raw_market in raw_markets:
            bucket = parse_market(raw_market)
            if bucket is None:
                continue
            target_date = ticker_date(bucket.ticker)
            if target_date is not None and start <= target_date <= end:
                market_groups[target_date].append(bucket)
        for target_date in list(market_groups):
            market_groups[target_date].sort(key=lambda row: (row.lower if row.lower is not None else -999, row.upper or 999))

        actuals = fetch_ncei_actuals(config["station"], start, end)
        city_payloads.append(
            {
                "city": city,
                "label": config["label"],
                "series": series,
                "station": config["station"],
                "market_dates": len(market_groups),
                "actual_dates": len(actuals),
            }
        )

        for target_date, buckets in sorted(market_groups.items()):
            actual = actuals.get(target_date)
            if actual is None or len(buckets) < 5:
                continue
            close_time = max(bucket.close_time for bucket in buckets)
            start_time = close_time - timedelta(hours=72)
            end_time = close_time + timedelta(hours=3)
            candle_map = fetch_batch_candles(series, buckets, start_time, end_time)
            by_ts: dict[int, dict[str, float]] = defaultdict(dict)
            for bucket in buckets:
                for candle in candle_map.get(bucket.ticker, []):
                    ts = int(candle.get("end_period_ts") or 0)
                    prob = probability_from_candle(candle)
                    if ts and prob is not None:
                        by_ts[ts][bucket.ticker] = prob
            tickers = {bucket.ticker for bucket in buckets}
            snapshots = []
            for ts, probs in sorted(by_ts.items()):
                if tickers.issubset(probs):
                    snap = project(buckets, probs, actual, ts)
                    snapshots.append(snap)
                    snapshot_rows.append({"city": city, "date": target_date.isoformat(), **snap})

            close_ts = int(close_time.timestamp())
            final_snapshot = select_snapshot(snapshots, close_ts, "before")
            day_before_snapshot = select_snapshot(snapshots, close_ts - 24 * 3600, "nearest")
            two_day_snapshot = select_snapshot(snapshots, close_ts - 48 * 3600, "nearest")
            date_rows.append(
                {
                    "city": city,
                    "label": config["label"],
                    "series": series,
                    "station": config["station"],
                    "date": target_date.isoformat(),
                    "actual_high_f": actual,
                    "bucket_count": len(buckets),
                    "snapshot_count": len(snapshots),
                    "close_time": close_time.isoformat(timespec="seconds").replace("+00:00", "Z"),
                    **prefix_snapshot("final", final_snapshot),
                    **prefix_snapshot("t_minus_24h", day_before_snapshot),
                    **prefix_snapshot("t_minus_48h", two_day_snapshot),
                }
            )
    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "source": "Kalshi external API market candlesticks + NOAA/NCEI daily summaries",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "cities": city_payloads,
        "summary": summarize_panel(date_rows),
        "date_rows": date_rows,
        "snapshot_rows": snapshot_rows,
    }


def prefix_snapshot(prefix: str, row: dict[str, Any] | None) -> dict[str, Any]:
    fields = ["time", "expected_high_f", "abs_error_f", "actual_bucket_probability", "modal_bucket", "modal_probability", "actual_inside_modal", "raw_probability_sum"]
    return {f"{prefix}_{field}": (row.get(field) if row else None) for field in fields}


def summarize_panel(rows: list[dict[str, Any]]) -> dict[str, Any]:
    usable_final = [row for row in rows if row.get("final_abs_error_f") is not None]
    usable_24 = [row for row in rows if row.get("t_minus_24h_abs_error_f") is not None]
    usable_48 = [row for row in rows if row.get("t_minus_48h_abs_error_f") is not None]

    def block(prefix: str, usable: list[dict[str, Any]]) -> dict[str, Any]:
        errors = [float(row[f"{prefix}_abs_error_f"]) for row in usable]
        probs = [float(row[f"{prefix}_actual_bucket_probability"]) for row in usable]
        modal = [bool(row[f"{prefix}_actual_inside_modal"]) for row in usable]
        return {
            "n": len(usable),
            "mean_abs_error_f": mean(errors) if errors else None,
            "median_abs_error_f": median(errors) if errors else None,
            "mean_actual_bucket_probability": mean(probs) if probs else None,
            "median_actual_bucket_probability": median(probs) if probs else None,
            "modal_accuracy": sum(1 for value in modal if value) / len(modal) if modal else None,
        }

    by_city = {}
    for city in sorted({row["city"] for row in rows}):
        city_rows = [row for row in rows if row["city"] == city]
        by_city[city] = block("final", [row for row in city_rows if row.get("final_abs_error_f") is not None])

    return {
        "date_panels": len(rows),
        "total_snapshots": sum(int(row.get("snapshot_count") or 0) for row in rows),
        "final": block("final", usable_final),
        "t_minus_24h": block("t_minus_24h", usable_24),
        "t_minus_48h": block("t_minus_48h", usable_48),
        "by_city_final": by_city,
    }


def fmt(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def write_outputs(payload: dict[str, Any]) -> None:
    data_dir = ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    slug = f"kalshi_temperature_panel_{payload['start_date'].replace('-', '')}_{payload['end_date'].replace('-', '')}"
    json_path = data_dir / f"{slug}.json"
    csv_path = data_dir / f"{slug}.csv"
    snapshot_csv_path = data_dir / f"{slug}_snapshots.csv"
    md_path = data_dir / f"{slug}.md"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    date_fields = list(payload["date_rows"][0].keys()) if payload["date_rows"] else []
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=date_fields)
        writer.writeheader()
        writer.writerows(payload["date_rows"])

    snapshot_fields = list(payload["snapshot_rows"][0].keys()) if payload["snapshot_rows"] else []
    with snapshot_csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=snapshot_fields)
        writer.writeheader()
        writer.writerows(payload["snapshot_rows"])

    summary = payload["summary"]
    lines = [
        "# Kalshi Temperature Panel",
        "",
        f"Generated: `{payload['generated_at']}`",
        f"Window: `{payload['start_date']}` to `{payload['end_date']}`",
        f"Source: `{payload['source']}`",
        "",
        "## Coverage",
        "",
        f"- Date panels: `{summary['date_panels']}`",
        f"- Hourly snapshots: `{summary['total_snapshots']}`",
        f"- Cities: `{', '.join(city['label'] for city in payload['cities'])}`",
        "",
        "## Accuracy",
        "",
        "| Snapshot | N | Mean Abs Error | Median Abs Error | Mean Actual-Bucket P | Median Actual-Bucket P | Modal Accuracy |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for key, label in (("t_minus_48h", "48h before close"), ("t_minus_24h", "24h before close"), ("final", "Final pre-close")):
        row = summary[key]
        lines.append(
            f"| {label} | {row['n']} | {fmt(row['mean_abs_error_f'])}F | {fmt(row['median_abs_error_f'])}F | "
            f"{fmt(row['mean_actual_bucket_probability'], 3)} | {fmt(row['median_actual_bucket_probability'], 3)} | {fmt(row['modal_accuracy'], 3)} |"
        )

    lines.extend(["", "## Final Accuracy By City", "", "| City | N | Mean Abs Error | Mean Actual-Bucket P | Modal Accuracy |", "|---|---:|---:|---:|---:|"])
    for city, row in summary["by_city_final"].items():
        lines.append(
            f"| {city} | {row['n']} | {fmt(row['mean_abs_error_f'])}F | {fmt(row['mean_actual_bucket_probability'], 3)} | {fmt(row['modal_accuracy'], 3)} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This is the first multi-month Kalshi panel. Each date-city panel treats the full set of Kalshi high-temperature range contracts as a discrete probability distribution, projects it into an expected daily high, and compares that value to NOAA/NCEI daily TMAX.",
            "",
            "The 24h and 48h rows are included to avoid relying only on near-settlement markets. The final row measures the quality of the market-implied state distribution near contract close.",
        ]
    )
    md_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"wrote {json_path}")
    print(f"wrote {csv_path}")
    print(f"wrote {snapshot_csv_path}")
    print(f"wrote {md_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date", default="2026-03-01")
    parser.add_argument("--end-date", default="2026-05-04")
    parser.add_argument("--cities", default="nyc,chicago,miami")
    args = parser.parse_args()
    cities = [city.strip() for city in args.cities.split(",") if city.strip()]
    payload = build_panel(
        datetime.strptime(args.start_date, "%Y-%m-%d").date(),
        datetime.strptime(args.end_date, "%Y-%m-%d").date(),
        cities,
    )
    write_outputs(payload)


if __name__ == "__main__":
    main()
