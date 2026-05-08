# Prediction-Market Surface Inventory

Generated: `2026-05-08T03:54:40Z`

## Polymarket Families

| Family | Target | Matched Markets | Sample Evidence |
|---|---|---:|---|
| `crypto_terminal_ladders` | BTC / ETH terminal prices | 365 | Will the price of Bitcoin be above $76,000 on April 10? |
| `private_company_valuation` | OpenAI / Anthropic / SpaceX / Anduril valuations | 135 | Will SpaceX's public ticker be $SEX? |
| `ai_capability_semantics` | AI model leadership / adoption | 414 | Will Perplexity AI be acquired before 2027? |
| `macro_policy` | rates, inflation, macro prints | 610 | Will the Fed decrease interest rates by 50+ bps after the April 2026 meeting? |
| `public_equity_index` | equities and equity indices | 298 | Will Tesla announce a Bitcoin purchase before March 1, 2021? |
| `weather_climate` | weather / climate states | 2,174 | Named storm forms before hurricane season? |

## Kalshi Series

| Series | Family | Target | Markets | Active | Sample Evidence |
|---|---|---|---:|---:|---|
| `KXBTC` | `crypto_terminal_ladders` | Bitcoin hourly range | 1,000 | 238 | Bitcoin price range  on May 9, 2026? |
| `KXETH` | `crypto_terminal_ladders` | Ethereum hourly range | 1,000 | 125 | Ethereum price at May 9, 2026 at 12am EDT? |
| `KXNASDAQ100` | `public_equity_index` | Nasdaq-100 daily close | 1,000 | 30 | Will the Nasdaq-100 be between 28500 and 28599.9900 at the end of May 7, 2026 at 4pm EDT? |
| `KXCPI` | `macro_policy` | CPI monthly change | 89 | 68 | Will CPI rise more than 0.7% in March 2026? |
| `KXCPICORE` | `macro_policy` | Core CPI monthly change | 52 | 38 | Will CPI Core rise more than 0.1% in March? |
| `KXFED` | `macro_policy` | Fed funds upper bound | 131 | 109 | Will the upper bound of the federal funds rate be above 3.75% following the Fed's Apr 29, 2026 meeting? |
| `KXHIGHNY` | `weather_climate` | NYC high temperature | 414 | 12 | Will the **high temp in NYC** be <62° on Mar 27, 2026? |
| `KXHIGHCHI` | `weather_climate` | Chicago high temperature | 414 | 12 | Will the high temp in Chicago be 41-42° on Mar 3, 2026? |
| `KXHIGHMIA` | `weather_climate` | Miami high temperature | 414 | 12 | Will the **high temp in Miami** be 80-81° on Apr 8, 2026? |

## Interpretation

The empirical object is broader than one private-company ladder. Prediction-market venues already contain many partial option surfaces: crypto price ladders, weather ranges, CPI and Fed thresholds, equity-index ranges, and semantic AI/company proxy markets. The paper's operator is designed to consume these surfaces whenever market text can be mapped into payoff functions over a target latent variable.

Polymarket supplies deep semantic breadth and CLOB price history for selected token IDs. Kalshi supplies regulated market series with recurring ladder structure and official settlement sources. Together they make the framework a general prediction-market index construction problem rather than a one-off OpenAI valuation exercise.
