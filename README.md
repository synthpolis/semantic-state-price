# Semantic State Prices

**Inferring latent indices from prediction-market event securities.**

[Read the PDF](paper/semantic-state-prices.pdf) · [Read the manuscript](paper/semantic-state-prices.md) · [View the data](data/empirical_summary.md)

![Semantic state-price operator](figures/figure_1_semantic_operator.png)

## Abstract

Prediction markets trade thousands of binary contracts tied to future states of the world. This repository shows how to treat related contracts as noisy state-price observations, project them into a coherent latent distribution, and report the resulting expectation as an index candidate. The intended use is an oracle input for perpetual futures on variables that do not have native spot markets.

The manuscript validates the method on a 29-month Polymarket BTC/ETH entity pool and a Kalshi weather panel, then applies it to a 1,030-market OpenAI semantic pool and compares the result with Hyperliquid pre-IPO perpetuals.

## Core Operator

```math
\widehat q_{\theta,T}(t)
=
\arg\min_{q\in\Delta_K}
\left[
\sum_{i\in\mathcal M_{\theta,T}(t)}
\omega_i(t)\rho_\tau\!\left(
\ell(A_iq)-\ell(\widetilde p_i(t))
\right)
+\lambda\,\mathrm{KL}(q\Vert\pi_{\theta,T})
+\mu\lVert D^2\log q\rVert_2^2
\right]

I_{\theta,T}(t)=\sum_{k=1}^{K}x_k\,\widehat q_k(t),
\qquad
\ell(p)=\log\frac{p}{1-p}
```

Where:

- `p_i` is the observed prediction-market YES price.
- `A_i` maps a natural-language market rule into payoffs over latent state buckets.
- `omega_i` weights relevance, liquidity, specificity, maturity fit, calibration, and attack cost.
- `q_hat` is the nearest coherent distribution over the latent state.
- `I(theta,T)` is the resulting index.

## Empirical Results

| Surface | Venue | Sample | Result |
|---|---|---:|---|
| BTC/ETH entity pool | Polymarket | 3,197 markets over 29 months | 542 close thresholds, 423 range buckets; final Brier `0.075`; final accuracy `0.904` |
| High-temperature ladders | Kalshi | 195 city-date panels, 7,496 snapshots | Final MAE: `1.02F`; modal accuracy: `0.862` |
| OpenAI semantic pool | Polymarket | 1,030 markets over 33 months | Direct index: `$1.152T`; semantic-adjusted index: `$1.150T` |
| OpenAI pre-IPO perp | Hyperliquid | live `vntl` perp benchmark | Mark: `$1.112T`; oracle: `$1.023T` |

## Figures

| Figure | File |
|---|---|
| Semantic state-price operator | [`figures/figure_1_semantic_operator.png`](figures/figure_1_semantic_operator.png) |
| Polymarket crypto validation | [`figures/figure_2_polymarket_crypto.png`](figures/figure_2_polymarket_crypto.png) |
| Kalshi weather validation | [`figures/figure_3_kalshi_panel.png`](figures/figure_3_kalshi_panel.png) |
| OpenAI / Hyperliquid bridge | [`figures/figure_4_openai_bridge.png`](figures/figure_4_openai_bridge.png) |

## Repository Layout

```text
paper/
  semantic-state-prices.md      Manuscript source
  semantic-state-prices.pdf     Submission PDF
  semantic-state-prices.html    Rendered HTML source

figures/
  figure_*.png                  Manuscript figures

data/
  *.csv, *.json, *.md           Empirical outputs and summaries

scripts/
  build_figures.py              Rebuilds the public figures from data outputs
  render_paper_html.py          Renders manuscript Markdown to HTML
  polymarket_entity_pools.py    Fetches Polymarket BTC/ETH and OpenAI entity pools
  kalshi_temperature_panel.py   Fetches Kalshi/NOAA panel data
  kalshi_temperature_validation.py
  hyperliquid_private_perps.py
```

## Reproduce

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python scripts/build_figures.py
python scripts/render_paper_html.py
```

The included datasets are sufficient to regenerate the figures. To refresh the live Polymarket entity pools, run:

```bash
python scripts/polymarket_entity_pools.py --crypto-pages 20 --openai-pages 16 --history-limit 500
```

## Data Provenance

- Polymarket Gamma event discovery, CLOB market history, and order-book data
- Kalshi external market and candlestick APIs
- NOAA/NCEI daily weather summaries
- Hyperliquid perpetual-market info endpoint

## Disclaimer

This repository is research code and empirical analysis. It is not investment advice, trading advice, or a production oracle implementation.
