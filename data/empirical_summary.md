# Empirical Summary

Generated from the current research artifacts.

## Public Rolling Validation

| Asset | Venue | Dates / Snapshots | Quote Source | Reference | Mean As-Of Abs Error | Mean Last Abs Error | Mean Last Realized-Bucket P |
|---|---|---:|---|---|---:|---:|---:|
| BTC | Polymarket | 8 dates / 120 snapshots | CLOB `batch-prices-history` | CoinGecko BTC-USD | $798 | $451 | 0.732 |
| ETH | Polymarket | 8 dates / 141 snapshots | CLOB `batch-prices-history` | CoinGecko ETH-USD | $26 | $20 | 0.685 |
| City high temp | Kalshi | 195 date-city panels / 7,496 snapshots | External API candlesticks | NOAA/NCEI daily TMAX | 1.69F at 24h, 1.02F final | 1.02F final mean | 0.843 final mean |

Interpretation: direct Polymarket threshold ladders can be projected into continuous as-of terminal price distributions for public crypto assets. Kalshi temperature range contracts validate the same projection idea on a larger non-crypto panel: three cities, 65 dates each, and 7,496 hourly snapshots against NOAA/NCEI actuals.

## Kalshi Horizon Robustness

| Snapshot | N | Mean Abs Error | Median Abs Error | Mean Actual-Bucket P | Modal Accuracy |
|---|---:|---:|---:|---:|---:|
| 48h before close | 195 | 2.07F | 1.31F | 0.281 | 0.369 |
| 24h before close | 195 | 1.69F | 1.24F | 0.373 | 0.549 |
| Final pre-close | 195 | 1.02F | 0.53F | 0.843 | 0.862 |

Interpretation: the improvement from 48h to 24h to final pre-close is exactly what a prediction-market state-price surface should show: uncertainty collapses as the underlying state is revealed.

## Prediction-Market Surface Inventory

| Venue | Family | Matched Markets / Series |
|---|---|---:|
| Polymarket | Crypto terminal ladders | 365 matched markets |
| Polymarket | Private-company valuation / IPO | 135 matched markets |
| Polymarket | AI capability semantics | 414 matched markets |
| Polymarket | Macro policy | 610 matched markets |
| Kalshi | BTC / ETH hourly ranges | 2 series, 2,000 returned markets |
| Kalshi | CPI / Core CPI / Fed | 3 series, 272 returned markets |
| Kalshi | Weather ranges | 3 series, 1,242 returned markets |

Interpretation: the paper should frame the method as a general prediction-market surface reconstruction problem. Private-company perps are one application, not the whole contribution.

## Private-Asset Projection

| Asset | Horizon | Source Markets | Implied IPO P | Implied No-IPO P | Expected Valuation | Conditional IPO Valuation |
|---|---|---|---:|---:|---:|---:|
| OpenAI | 2027-12-31 | Polymarket IPO valuation ladder | 0.702 | 0.298 | $932B | $1.328T |

Interpretation: private-company valuation ladders are noisier and internally inconsistent, but the same projection method creates a coherent distribution and residual table. This is the bridge from public validation to latent private-asset indices.

## Live Private Perp Benchmark

| Venue | Market | Category | Mark | Oracle | Mark/Oracle | OI Notional | 24h Volume | Mean Ann. Funding |
|---|---|---|---:|---:|---:|---:|---:|---:|
| Hyperliquid `vntl` | ANTHROPIC | pre-IPO | $1.157T | $974B | 18.71% | $6.89M | $0.94M | 127.20% |
| Hyperliquid `vntl` | SPACEX | pre-IPO | $1.832T | $1.647T | 11.19% | $3.39M | $1.19M | 31.44% |
| Hyperliquid `vntl` | OPENAI | pre-IPO | $1.112T | $1.023T | 8.61% | $3.35M | $0.52M | 24.76% |

Interpretation: the private-market perp already exists as a tradable benchmark. It does not remove the need for a semantic prediction-market oracle; it gives the paper an external comparison point for marks, funding, open interest, and order-book depth. The OpenAI Polymarket projection produced a $932B unconditional valuation and $1.328T conditional-IPO valuation; Hyperliquid's `vntl:OPENAI` mark sits between them at roughly $1.112T.

## Oracle Stress

| Asset | Horizon | Shock | Baseline Index | Max One-Market Move | Median Move | Stress Confidence |
|---|---|---:|---:|---:|---:|---:|
| OpenAI | 2027-12-31 | +/- 0.05 | $932B | $31B | $8B | 0.967 |

Interpretation: for the current OpenAI 2027 ladder, a five-point probability shock to the most sensitive constituent moves the fitted unconditional valuation index by roughly 3.3%. This is encouraging, but it is only a sensitivity result. A production perp oracle still needs order-book-depth-aware manipulation cost, TWAPs, and inclusion rules.

## Source-Market Order-Book Cost

| Asset | Horizon | Books | Median Spread | Inside-Spread Stress Cases | Finite Crossed-Depth Cases | Cheapest Notional / $1B Move | Median Notional / $1B Move |
|---|---|---:|---:|---:|---:|---:|---:|
| OpenAI | 2027-12-31 | 12 | 72.9% | 14 | 10 | $1.40 | $13.04 |

Interpretation: this is the most important negative result so far. The source markets exist and can be joined directly to Polymarket books, but many useful valuation brackets are extremely wide. A naive midpoint oracle would be manipulable or unstable. The paper should frame this as the reason the oracle formula must include spread penalties, trade/TWAP rules, depth caps, and source-market exclusion.

## Current Claim Strength

The current evidence supports a narrow claim:

> Semantically matched binary threshold markets can be projected into coherent continuous distributions, and direct Polymarket quote history is sufficient to generate rolling as-of public-asset indices.

It does not yet support the stronger claim:

> A general semantic prediction-market oracle can robustly price arbitrary non-traded assets.

That stronger claim still needs more market families, richer semantic proxy markets, and manipulation/oracle stress tests.
