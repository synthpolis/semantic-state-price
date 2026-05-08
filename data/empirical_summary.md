# Empirical Summary

Generated from the current research artifacts.

## Public Rolling Validation

| Surface | Venue | Sample | Quote Source | Reference | Main Result |
|---|---|---:|---|---|---|
| BTC/ETH entity pool | Polymarket | 3,197 markets / 29 months | Gamma API + CLOB `batch-prices-history` | Resolved market outcomes | 542 close thresholds, 423 range buckets; final Brier 0.075; final accuracy 0.904 |
| City high temp | Kalshi | 195 date-city panels / 7,496 snapshots | External API candlesticks | NOAA/NCEI daily TMAX | 1.69F MAE at 24h; 1.02F final; 0.843 final actual-bucket P |

Interpretation: Polymarket now enters as a dense entity-level pool, not an eight-date sample. Direct close-threshold markets provide binary calibration; barrier and proxy markets expand semantic coverage with lower weights. Kalshi temperature range contracts validate the distribution projection on a larger non-crypto panel.

## Polymarket Crypto Calibration

| Snapshot | N | Brier | Log loss | Accuracy | Mean Realized-Side P |
|---|---:|---:|---:|---:|---:|
| 48h before close | 212 | 0.142 | 0.434 | 0.759 | 0.721 |
| 24h before close | 250 | 0.127 | 0.384 | 0.812 | 0.758 |
| 6h before close | 342 | 0.091 | 0.288 | 0.874 | 0.817 |
| Final pre-close | 342 | 0.075 | 0.235 | 0.904 | 0.854 |

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
| Polymarket | BTC/ETH entity pool | 3,197 matched markets over 29 months |
| Polymarket | OpenAI semantic pool | 1,030 matched markets over 33 months |
| Polymarket | Private-company valuation / IPO | 135 matched markets |
| Polymarket | AI capability semantics | 414 matched markets |
| Polymarket | Macro policy | 610 matched markets |
| Kalshi | BTC / ETH hourly ranges | 2 series, 2,000 returned markets |
| Kalshi | CPI / Core CPI / Fed | 3 series, 272 returned markets |
| Kalshi | Weather ranges | 3 series, 1,242 returned markets |

Interpretation: the paper should frame the method as a general prediction-market surface reconstruction problem. Private-company perps are one application, not the whole contribution.

## Private-Asset Projection

| Asset | Horizon | Source Markets | Implied IPO P | Implied No-IPO P | Direct Valuation | Semantic-Adjusted Valuation | Conditional IPO Valuation |
|---|---|---|---:|---:|---:|---:|---:|
| OpenAI | 2027-12-31 | Direct valuation ladder + 1,030-market semantic pool | 0.760 | 0.240 | $1.152T | $1.150T | $1.515T |

Interpretation: private-company valuation ladders are noisier and internally inconsistent, but the same projection method creates a coherent distribution and residual table. The semantic pocket uses active prices from model, product, legal/governance, competitor, and sector markets with conservative shrinkage rather than replacing the direct valuation ladder.

## Live Private Perp Benchmark

| Venue | Market | Category | Mark | Oracle | Mark/Oracle | OI Notional | 24h Volume | Mean Ann. Funding |
|---|---|---|---:|---:|---:|---:|---:|---:|
| Hyperliquid `vntl` | ANTHROPIC | pre-IPO | $1.157T | $974B | 18.71% | $6.89M | $0.94M | 127.20% |
| Hyperliquid `vntl` | SPACEX | pre-IPO | $1.832T | $1.647T | 11.19% | $3.39M | $1.19M | 31.44% |
| Hyperliquid `vntl` | OPENAI | pre-IPO | $1.112T | $1.023T | 8.61% | $3.35M | $0.52M | 24.76% |

Interpretation: the private-market perp is a tradable benchmark for the same latent state. It gives the paper an external comparison point for marks, funding, open interest, and order-book depth. The OpenAI Polymarket projection produced a $1.152T direct unconditional valuation, a $1.150T semantic-adjusted valuation, and $1.515T conditional-IPO valuation; Hyperliquid's `vntl:OPENAI` mark is close to but below the unconditional values at roughly $1.112T.

## Oracle Stress

| Asset | Horizon | Shock | Baseline Index | Max One-Market Move | Median Move | Stress Confidence |
|---|---|---:|---:|---:|---:|---:|
| OpenAI | 2027-12-31 | +/- 0.05 | $1.152T | $24B | $8B | 0.979 |

Interpretation: for the current OpenAI 2027 ladder, a five-point probability shock to the most sensitive constituent moves the fitted unconditional valuation index by roughly 2.1%. This measures index sensitivity. A production perp oracle extends it with order-book-depth-aware manipulation cost, TWAPs, and inclusion rules.

## Research Frontier

The current evidence establishes the core claim:

> Semantically matched binary threshold markets can be calibrated over dense month-scale panels, and direct/proxy prediction-market pools can be assembled into transparent entity-level state-price inputs.

The next frontier is the production oracle:

> A general semantic prediction-market oracle can support large, continuously traded perps on arbitrary non-traded states.

That frontier requires more resolved market families, richer semantic proxy markets, learned proxy loadings, and order-book-aware manipulation stress tests.
