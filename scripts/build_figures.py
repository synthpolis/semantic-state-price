from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FIG = ROOT / "figures"

INK = "#111111"
MID = "#555555"
DORMANT = "#D7D7D7"
BLUE = "#2F6F9F"
GREEN = "#3F7D4A"
ORANGE = "#B76836"
LIGHT = "#F2F2F2"
PAPER = "#FFFFFF"

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 8.5,
        "axes.titlesize": 9.5,
        "axes.labelsize": 8.5,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 7.5,
        "figure.dpi": 160,
    }
)


def load(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def style_axes(ax):
    ax.set_facecolor(PAPER)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(DORMANT)
    ax.spines["bottom"].set_color(DORMANT)
    ax.tick_params(colors=INK, labelsize=9)
    ax.grid(axis="y", color=DORMANT, alpha=0.45, linewidth=0.8)


def save(fig, name: str):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / name, dpi=300, bbox_inches="tight", facecolor=PAPER)
    plt.close(fig)
    print(f"wrote {FIG / name}")


def load_csv(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def crypto_panel():
    btc = load("btc_rolling_batch.json")["aggregate"]
    eth = load("eth_rolling_batch.json")["aggregate"]
    btc_rows = load_csv("btc_rolling_batch.csv")
    eth_rows = load_csv("eth_rolling_batch.csv")

    labels = ["BTC", "ETH"]
    native_errors = [btc["mean_last_abs_error_vs_terminal"], eth["mean_last_abs_error_vs_terminal"]]
    pct_errors = [
        sum(float(row["last_abs_error_vs_terminal"]) / float(row["realized_terminal"]) for row in btc_rows) / len(btc_rows),
        sum(float(row["last_abs_error_vs_terminal"]) / float(row["realized_terminal"]) for row in eth_rows) / len(eth_rows),
    ]
    probs = [btc["mean_last_realized_bucket_probability"], eth["mean_last_realized_bucket_probability"]]

    fig, axes = plt.subplots(1, 2, figsize=(6.8, 2.35), gridspec_kw={"wspace": 0.32})
    fig.patch.set_facecolor(PAPER)

    ax = axes[0]
    style_axes(ax)
    bars = ax.bar(labels, pct_errors, color=[BLUE, GREEN], width=0.52)
    ax.yaxis.set_major_formatter(PercentFormatter(1.0))
    ax.set_ylim(0, max(pct_errors) * 1.42)
    ax.set_ylabel("Last pre-close error")
    ax.set_title("(a) Mean absolute error as % of terminal")
    for bar, pct, native in zip(bars, pct_errors, native_errors):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(pct_errors) * 0.055,
            f"{pct:.2%}\n(${native:,.0f})",
            ha="center",
            va="bottom",
            color=INK,
            fontsize=7.5,
        )

    ax = axes[1]
    style_axes(ax)
    bars = ax.bar(labels, probs, color=[BLUE, GREEN], width=0.52)
    ax.yaxis.set_major_formatter(PercentFormatter(1.0))
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Probability")
    ax.set_title("(b) Realized-bucket probability")
    for bar, value in zip(bars, probs):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.035,
            f"{value:.1%}",
            ha="center",
            va="bottom",
            color=INK,
            fontsize=7.5,
        )

    save(fig, "figure_2_polymarket_crypto.png")


def kalshi_panel():
    data = load("kalshi_temperature_panel_20260301_20260504.json")
    summary = data["summary"]
    labels = ["48h", "24h", "final"]
    keys = ["t_minus_48h", "t_minus_24h", "final"]
    errors = [summary[key]["mean_abs_error_f"] for key in keys]
    probs = [summary[key]["mean_actual_bucket_probability"] for key in keys]
    modal = [summary[key]["modal_accuracy"] for key in keys]

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0), gridspec_kw={"width_ratios": [1.02, 1.18], "wspace": 0.54})
    fig.patch.set_facecolor(PAPER)
    ax1 = axes[0]
    style_axes(ax1)
    x = range(len(labels))
    ax1.bar(x, errors, width=0.45, color=LIGHT, edgecolor=MID, linewidth=0.6, label="MAE (F)")
    ax1.set_ylabel("Mean absolute error (F)", color=INK)
    ax1.set_ylim(0, max(errors) * 1.45)
    ax1.set_xticks(list(x), labels)
    ax1.set_title("(a) Forecast error falls toward settlement")
    for idx, value in enumerate(errors):
        ax1.text(idx, value + max(errors) * 0.045, f"{value:.2f}F", ha="center", va="bottom", fontsize=7.5, color=INK)

    ax2 = ax1.twinx()
    ax2.plot(x, probs, color=BLUE, marker="o", markersize=4, linewidth=1.6, label="Actual-bucket P")
    ax2.plot(x, modal, color=GREEN, marker="s", markersize=4, linewidth=1.6, label="Modal accuracy")
    ax2.set_ylim(0, 1.05)
    ax2.yaxis.set_major_formatter(PercentFormatter(1.0))
    ax2.tick_params(colors=INK)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_color(DORMANT)
    ax2.set_ylabel("")

    lines, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels1 + labels2, loc="upper left", frameon=False, handlelength=1.5)

    rows = [row for row in data["date_rows"] if row.get("final_expected_high_f") is not None]
    colors = {"nyc": ORANGE, "chicago": BLUE, "miami": GREEN}
    ax = axes[1]
    style_axes(ax)
    for city in sorted(colors):
        xs = [row["actual_high_f"] for row in rows if row["city"] == city]
        ys = [row["final_expected_high_f"] for row in rows if row["city"] == city]
        label = {"nyc": "New York", "chicago": "Chicago", "miami": "Miami"}[city]
        ax.scatter(xs, ys, s=13, alpha=0.70, color=colors[city], label=label, linewidths=0)
    all_vals = [row["actual_high_f"] for row in rows] + [row["final_expected_high_f"] for row in rows]
    lo, hi = min(all_vals) - 2, max(all_vals) + 2
    ax.plot([lo, hi], [lo, hi], color=MID, alpha=0.55, linewidth=0.8)
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_xlabel("NOAA/NCEI actual high (F)")
    ax.set_ylabel("Kalshi-implied expected high (F)")
    ax.set_title("(b) Final pre-close expectation vs. realized high")
    ax.legend(frameon=False, loc="upper left", handletextpad=0.3)
    save(fig, "figure_3_kalshi_panel.png")


def openai_bridge():
    projection = load("openai_20271231_projection.json")
    hyper = load("hyperliquid_vntl_private_perps.json")
    openai = next(row for row in hyper["rows"] if row["coin"] == "vntl:OPENAI")
    labels = [
        "Polymarket unconditional",
        "Hyperliquid oracle",
        "Hyperliquid mark",
        "Polymarket conditional IPO",
    ]
    values = [
        projection["expected_unconditional_b"],
        openai["oracle_px"],
        openai["mark_px"],
        projection["expected_conditional_b"],
    ]
    fig, ax = plt.subplots(figsize=(6.8, 2.55))
    fig.patch.set_facecolor(PAPER)
    style_axes(ax)
    y = list(range(len(labels)))
    ax.barh(y, values, color=[LIGHT, BLUE, ORANGE, GREEN], edgecolor=[MID, BLUE, ORANGE, GREEN], linewidth=0.7)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlabel("Implied OpenAI valuation ($B)")
    for idx, value in enumerate(values):
        ax.text(value + 18, idx, f"${value:,.0f}B", va="center", color=INK, fontsize=8)
    ax.set_xlim(0, max(values) * 1.17)
    save(fig, "figure_4_openai_bridge.png")


def main():
    crypto_panel()
    kalshi_panel()
    openai_bridge()


if __name__ == "__main__":
    main()
