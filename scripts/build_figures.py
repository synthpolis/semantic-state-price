from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
from matplotlib.patches import Rectangle


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


def semantic_operator():
    fig, ax = plt.subplots(figsize=(10.0, 4.0))
    fig.patch.set_facecolor(PAPER)
    ax.set_facecolor(PAPER)
    ax.axis("off")
    ax.add_patch(
        Rectangle(
            (0.025, 0.055),
            0.95,
            0.89,
            transform=ax.transAxes,
            fill=False,
            edgecolor=DORMANT,
            linewidth=1.0,
        )
    )
    ax.plot([0.07, 0.93], [0.72, 0.72], color=DORMANT, linewidth=0.9, transform=ax.transAxes)
    ax.text(
        0.07,
        0.86,
        "Semantic state-price operator",
        transform=ax.transAxes,
        ha="left",
        va="center",
        fontsize=18,
        fontweight="bold",
        color=INK,
    )
    ax.text(
        0.07,
        0.785,
        "prediction-market claims -> latent state distribution -> index oracle",
        transform=ax.transAxes,
        ha="left",
        va="center",
        fontsize=10.3,
        color=MID,
    )

    eq1 = (
        r"$\widehat q_{\theta,T}(t)=\underset{q\in\Delta_K}{\arg\min}\ "
        r"\mathcal{J}_{\theta,T}(q;t)$"
    )
    eq2 = (
        r"$\mathcal{J}_{\theta,T}(q;t)=\sum_{i\in\mathcal{M}_{\theta,T}(t)}"
        r"\omega_i(t)\rho_\tau\!\left(\ell(A_iq)-\ell(\tilde p_i(t))\right)"
        r"+\lambda\,\mathrm{KL}(q\Vert\pi_{\theta,T})+\mu\Vert D^2\log q\Vert_2^2$"
    )
    eq3 = (
        r"$I_{\theta,T}(t)=\sum_{k=1}^{K}x_k\,\widehat q_k(t),"
        r"\qquad \ell(p)=\log\frac{p}{1-p}$"
    )
    ax.text(0.5, 0.56, eq1, transform=ax.transAxes, ha="center", va="center", fontsize=18, color=INK)
    ax.text(0.5, 0.40, eq2, transform=ax.transAxes, ha="center", va="center", fontsize=11.2, color=INK)
    ax.text(0.5, 0.20, eq3, transform=ax.transAxes, ha="center", va="center", fontsize=15, color=INK)
    save(fig, "figure_1_semantic_operator.png")


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


def crypto_panel():
    data = load("polymarket_crypto_entity_pool.json")
    pool = data["pool"]
    validation = data["direct_threshold_validation"]

    type_order = [
        "close_threshold",
        "range_bucket",
        "barrier_threshold",
        "record_or_race",
        "institutional_proxy",
        "relative_proxy",
        "semantic_proxy",
    ]
    type_labels = {
        "close_threshold": "Close thresholds",
        "range_bucket": "Range buckets",
        "barrier_threshold": "Barrier thresholds",
        "record_or_race": "Record/race",
        "institutional_proxy": "Institutional proxy",
        "relative_proxy": "Relative proxy",
        "semantic_proxy": "Semantic proxy",
    }
    colors = [BLUE, GREEN, ORANGE, "#7B5B9A", "#8E8E8E", "#C7C7C7", LIGHT]

    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.0), gridspec_kw={"width_ratios": [1.12, 1.0], "wspace": 0.38})
    fig.patch.set_facecolor(PAPER)

    ax = axes[0]
    style_axes(ax)
    labels = ["BTC", "ETH"]
    x = range(len(labels))
    bottoms = [0, 0]
    for market_type, color in zip(type_order, colors):
        counts = [pool["by_target_type"].get(asset, {}).get(market_type, 0) for asset in labels]
        bars = ax.bar(x, counts, bottom=bottoms, width=0.50, color=color, edgecolor=MID, linewidth=0.3, label=type_labels[market_type])
        bottoms = [bottom + count for bottom, count in zip(bottoms, counts)]
        if market_type == "close_threshold":
            for bar, count, bottom in zip(bars, counts, bottoms):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bottom + 45,
                    f"{count}",
                    ha="center",
                    va="bottom",
                    color=INK,
                    fontsize=7.3,
                )
    ax.set_xticks(list(x), labels)
    ax.set_ylabel("Markets")
    ax.set_title("(a) 29-month BTC/ETH market pool")
    ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(-0.02, 1.02), handlelength=1.0)

    ax = axes[1]
    style_axes(ax)
    horizons = ["48h", "24h", "6h", "final"]
    brier = [validation[h]["brier"] for h in horizons]
    realized_prob = [validation[h]["realized_side_probability"] for h in horizons]
    accuracy = [validation[h]["accuracy"] for h in horizons]
    x = range(len(horizons))
    ax.bar(x, brier, color=LIGHT, edgecolor=MID, linewidth=0.7, width=0.48, label="Brier")
    ax.set_ylim(0, max(brier) * 1.45)
    ax.set_xticks(list(x), horizons)
    ax.set_ylabel("Brier score")
    ax.set_title("(b) Binary threshold calibration")
    for idx, value in enumerate(brier):
        ax.text(idx, value + max(brier) * 0.05, f"{value:.2f}", ha="center", va="bottom", fontsize=7.3)
    ax2 = ax.twinx()
    ax2.plot(x, realized_prob, color=BLUE, marker="o", markersize=4, linewidth=1.6, label="Realized-side P")
    ax2.plot(x, accuracy, color=GREEN, marker="s", markersize=4, linewidth=1.6, label="Accuracy")
    ax2.set_ylim(0, 1.03)
    ax2.tick_params(colors=INK)
    ax2.yaxis.set_major_formatter(PercentFormatter(1.0))
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_color(DORMANT)
    lines, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labels1 + labels2, loc="upper left", frameon=False, handlelength=1.3)

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
    openai_pool = load("openai_semantic_market_pool.json")
    hyper = load("hyperliquid_vntl_private_perps.json")
    openai = next(row for row in hyper["rows"] if row["coin"] == "vntl:OPENAI")
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.0), gridspec_kw={"width_ratios": [1.0, 1.12], "wspace": 0.54})
    fig.patch.set_facecolor(PAPER)

    ax = axes[0]
    style_axes(ax)
    type_counts = openai_pool["pool"]["by_target_type"]["OPENAI"]
    type_order = [
        "valuation_or_liquidity",
        "capability_or_product",
        "legal_governance",
        "competitor_capability",
        "openai_semantic",
        "ai_sector_proxy",
    ]
    labels = [
        "Valuation/liquidity",
        "Capability/product",
        "Legal/governance",
        "Competitor models",
        "OpenAI semantic",
        "AI sector",
    ]
    values = [type_counts.get(key, 0) for key in type_order]
    y = list(range(len(labels)))
    ax.barh(y, values, color=[BLUE, GREEN, ORANGE, "#7B5B9A", "#777777", LIGHT], edgecolor=MID, linewidth=0.5)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlabel("Markets")
    ax.set_title("(a) OpenAI semantic pocket")
    for idx, value in enumerate(values):
        ax.text(value + max(values) * 0.025, idx, f"{value}", va="center", color=INK, fontsize=7.5)

    ax = axes[1]
    style_axes(ax)
    signal = openai_pool["active_signal"]
    labels = [
        "Polymarket direct",
        "Semantic-adjusted",
        "Hyperliquid oracle",
        "Hyperliquid mark",
        "Conditional IPO",
    ]
    values = [
        projection["expected_unconditional_b"],
        signal["semantic_adjusted_unconditional_b"],
        openai["oracle_px"],
        openai["mark_px"],
        projection["expected_conditional_b"],
    ]
    y = list(range(len(labels)))
    ax.barh(y, values, color=[LIGHT, GREEN, BLUE, ORANGE, "#7B5B9A"], edgecolor=[MID, GREEN, BLUE, ORANGE, "#7B5B9A"], linewidth=0.7)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlabel("Implied OpenAI valuation ($B)")
    ax.set_title("(b) State price to perp bridge")
    for idx, value in enumerate(values):
        ax.text(value + 18, idx, f"${value:,.0f}B", va="center", color=INK, fontsize=8)
    ax.set_xlim(0, max(values) * 1.17)
    save(fig, "figure_4_openai_bridge.png")


def main():
    semantic_operator()
    crypto_panel()
    kalshi_panel()
    openai_bridge()


if __name__ == "__main__":
    main()
