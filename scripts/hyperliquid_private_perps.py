from __future__ import annotations

import argparse
import json
import math
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INFO_URL = "https://api.hyperliquid.xyz/info"
USER_AGENT = "semantic-state-price-research/0.1"


def post_info(body: dict[str, Any]) -> Any:
    req = urllib.request.Request(
        INFO_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read())


def parse_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def iso_from_ms(ms: int | float | None) -> str | None:
    if ms is None:
        return None
    return datetime.fromtimestamp(float(ms) / 1000, UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def get_annotation(coin: str) -> dict[str, Any]:
    try:
        data = post_info({"type": "perpAnnotation", "coin": coin})
        return data if isinstance(data, dict) else {}
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


def get_book_summary(coin: str) -> dict[str, Any]:
    try:
        data = post_info({"type": "l2Book", "coin": coin})
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}

    levels = data.get("levels", [[], []]) if isinstance(data, dict) else [[], []]
    bids = levels[0] if len(levels) > 0 else []
    asks = levels[1] if len(levels) > 1 else []
    bid_rows = [(parse_float(row.get("px")), parse_float(row.get("sz"))) for row in bids]
    ask_rows = [(parse_float(row.get("px")), parse_float(row.get("sz"))) for row in asks]
    bid_rows = [(px, sz) for px, sz in bid_rows if px is not None and sz is not None]
    ask_rows = [(px, sz) for px, sz in ask_rows if px is not None and sz is not None]

    best_bid = bid_rows[0][0] if bid_rows else None
    best_ask = ask_rows[0][0] if ask_rows else None
    mid = (best_bid + best_ask) / 2 if best_bid is not None and best_ask is not None else None

    def depth_within(rows: list[tuple[float, float]], pct: float, side: str) -> dict[str, float]:
        if mid is None:
            return {"base": 0.0, "notional": 0.0}
        if side == "bid":
            selected = [(px, sz) for px, sz in rows if px >= mid * (1 - pct)]
        else:
            selected = [(px, sz) for px, sz in rows if px <= mid * (1 + pct)]
        return {
            "base": sum(sz for _px, sz in selected),
            "notional": sum(px * sz for px, sz in selected),
        }

    return {
        "book_time": iso_from_ms(data.get("time")) if isinstance(data, dict) else None,
        "best_bid": best_bid,
        "best_ask": best_ask,
        "mid": mid,
        "spread": (best_ask - best_bid) if best_bid is not None and best_ask is not None else None,
        "spread_pct": ((best_ask - best_bid) / mid) if mid else None,
        "bid_depth_1pct": depth_within(bid_rows, 0.01, "bid"),
        "ask_depth_1pct": depth_within(ask_rows, 0.01, "ask"),
        "bid_depth_5pct": depth_within(bid_rows, 0.05, "bid"),
        "ask_depth_5pct": depth_within(ask_rows, 0.05, "ask"),
        "raw_bid_levels": len(bid_rows),
        "raw_ask_levels": len(ask_rows),
    }


def get_candles(coin: str, days: int, interval: str) -> list[dict[str, Any]]:
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - days * 24 * 60 * 60 * 1000
    data = post_info(
        {
            "type": "candleSnapshot",
            "req": {
                "coin": coin,
                "interval": interval,
                "startTime": start_ms,
                "endTime": now_ms,
            },
        }
    )
    return data if isinstance(data, list) else []


def get_funding(coin: str, days: int) -> list[dict[str, Any]]:
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - days * 24 * 60 * 60 * 1000
    data = post_info(
        {
            "type": "fundingHistory",
            "coin": coin,
            "startTime": start_ms,
            "endTime": now_ms,
        }
    )
    return data if isinstance(data, list) else []


def summarize_candles(candles: list[dict[str, Any]]) -> dict[str, Any]:
    closes = [parse_float(row.get("c")) for row in candles]
    closes = [close for close in closes if close is not None and close > 0]
    volumes = [parse_float(row.get("v")) for row in candles]
    volumes = [volume for volume in volumes if volume is not None]
    trades = [int(row.get("n", 0) or 0) for row in candles]
    returns = [math.log(closes[idx] / closes[idx - 1]) for idx in range(1, len(closes))]
    return {
        "candles": len(candles),
        "first_close": closes[0] if closes else None,
        "last_close": closes[-1] if closes else None,
        "price_change_pct": ((closes[-1] / closes[0]) - 1) if len(closes) >= 2 else None,
        "daily_base_volume_mean": mean(volumes) if volumes else None,
        "daily_trades_mean": mean(trades) if trades else None,
        "daily_log_return_vol": stdev(returns) if len(returns) >= 2 else None,
        "annualized_log_return_vol": stdev(returns) * math.sqrt(365) if len(returns) >= 2 else None,
    }


def summarize_funding(rows: list[dict[str, Any]]) -> dict[str, Any]:
    rates = [parse_float(row.get("fundingRate")) for row in rows]
    rates = [rate for rate in rates if rate is not None]
    premiums = [parse_float(row.get("premium")) for row in rows]
    premiums = [premium for premium in premiums if premium is not None]
    return {
        "observations": len(rows),
        "mean_hourly_funding": mean(rates) if rates else None,
        "median_hourly_funding": median(rates) if rates else None,
        "latest_hourly_funding": rates[-1] if rates else None,
        "annualized_mean_funding": mean(rates) * 24 * 365 if rates else None,
        "mean_premium": mean(premiums) if premiums else None,
        "latest_time": iso_from_ms(rows[-1].get("time")) if rows else None,
    }


def select_private_perps(dex: str) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    meta, contexts = post_info({"type": "metaAndAssetCtxs", "dex": dex})
    selected: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for asset, context in zip(meta.get("universe", []), contexts, strict=False):
        coin = asset.get("name", "")
        annotation = get_annotation(coin)
        if annotation.get("category") == "preipo":
            selected.append((asset, context))
    return selected


def build_payload(dex: str, days: int, interval: str) -> dict[str, Any]:
    rows = []
    for asset, context in select_private_perps(dex):
        coin = asset["name"]
        mark = parse_float(context.get("markPx"))
        oracle = parse_float(context.get("oraclePx"))
        mid = parse_float(context.get("midPx"))
        open_interest = parse_float(context.get("openInterest"))
        day_base_volume = parse_float(context.get("dayBaseVlm"))
        day_notional_volume = parse_float(context.get("dayNtlVlm"))
        row = {
            "coin": coin,
            "asset": asset,
            "annotation": get_annotation(coin),
            "context": context,
            "mark_px": mark,
            "oracle_px": oracle,
            "mid_px": mid,
            "premium": parse_float(context.get("premium")),
            "funding": parse_float(context.get("funding")),
            "open_interest_base": open_interest,
            "open_interest_notional": open_interest * mark if open_interest is not None and mark is not None else None,
            "day_base_volume": day_base_volume,
            "day_notional_volume": day_notional_volume,
            "mark_vs_oracle_pct": ((mark / oracle) - 1) if mark is not None and oracle not in (None, 0) else None,
            "book": get_book_summary(coin),
            "candles": summarize_candles(get_candles(coin, days, interval)),
            "funding_history": summarize_funding(get_funding(coin, days)),
        }
        rows.append(row)
    rows.sort(key=lambda row: row.get("open_interest_notional") or 0.0, reverse=True)

    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "source": "Hyperliquid info endpoint",
        "dex": dex,
        "lookback_days": days,
        "candle_interval": interval,
        "rows": rows,
        "summary": summarize_rows(rows),
    }


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    oi = [row["open_interest_notional"] for row in rows if row.get("open_interest_notional") is not None]
    volume = [row["day_notional_volume"] for row in rows if row.get("day_notional_volume") is not None]
    return {
        "markets": len(rows),
        "total_open_interest_notional": sum(oi) if oi else None,
        "total_24h_notional_volume": sum(volume) if volume else None,
        "largest_open_interest_coin": rows[0]["coin"] if rows else None,
    }


def fmt_money(value: float | None, digits: int = 0) -> str:
    if value is None:
        return "n/a"
    return f"${value:,.{digits}f}"


def fmt_pct(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.{digits}f}%"


def write_outputs(payload: dict[str, Any]) -> None:
    data_dir = ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    slug = f"hyperliquid_{payload['dex']}_private_perps"
    json_path = data_dir / f"{slug}.json"
    md_path = data_dir / f"{slug}.md"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    summary = payload["summary"]
    lines = [
        f"# Hyperliquid {payload['dex'].upper()} Private Perps",
        "",
        f"Generated: `{payload['generated_at']}`",
        f"Lookback: `{payload['lookback_days']}` days, candles: `{payload['candle_interval']}`",
        "",
        "## Summary",
        "",
        f"- Private / pre-IPO markets: `{summary['markets']}`",
        f"- Total open interest notional: `{fmt_money(summary['total_open_interest_notional'])}`",
        f"- Total 24h notional volume: `{fmt_money(summary['total_24h_notional_volume'])}`",
        f"- Largest OI market: `{summary['largest_open_interest_coin']}`",
        "",
        "## Markets",
        "",
        "| Coin | Mark | Oracle | Mark/Oracle | Funding Hr | Funding Ann. | OI Notional | 24h Vol | 7d Change | Book Spread |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload["rows"]:
        book = row.get("book", {})
        funding = row.get("funding_history", {})
        candles = row.get("candles", {})
        lines.append(
            "| {coin} | {mark} | {oracle} | {premium} | {funding} | {ann} | {oi} | {vol} | {chg} | {spread} |".format(
                coin=row["coin"],
                mark=fmt_money(row["mark_px"], 1),
                oracle=fmt_money(row["oracle_px"], 1),
                premium=fmt_pct(row["mark_vs_oracle_pct"]),
                funding=fmt_pct(row["funding"]),
                ann=fmt_pct(funding.get("annualized_mean_funding")),
                oi=fmt_money(row["open_interest_notional"]),
                vol=fmt_money(row["day_notional_volume"]),
                chg=fmt_pct(candles.get("price_change_pct")),
                spread=fmt_pct(book.get("spread_pct")),
            )
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Hyperliquid annotations define these contracts as `preipo`; each unit tracks total company valuation in billions.",
            "- `mark_px` is directly comparable to a valuation in billions. For example, `OPENAI = 1111` implies roughly `$1.111T` total valuation.",
            "- Funding and order-book depth give the paper a live perp benchmark that Polymarket binary markets alone cannot supply.",
        ]
    )
    md_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dex", default="vntl")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--interval", default="1d")
    args = parser.parse_args()
    write_outputs(build_payload(args.dex, args.days, args.interval))


if __name__ == "__main__":
    main()
