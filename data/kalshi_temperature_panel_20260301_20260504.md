# Kalshi Temperature Panel

Generated: `2026-05-08T04:02:16Z`
Window: `2026-03-01` to `2026-05-04`
Source: `Kalshi external API market candlesticks + NOAA/NCEI daily summaries`

## Coverage

- Date panels: `195`
- Hourly snapshots: `7496`
- Cities: `New York City / Central Park, Chicago / O'Hare, Miami`

## Accuracy

| Snapshot | N | Mean Abs Error | Median Abs Error | Mean Actual-Bucket P | Median Actual-Bucket P | Modal Accuracy |
|---|---:|---:|---:|---:|---:|---:|
| 48h before close | 195 | 2.07F | 1.31F | 0.281 | 0.268 | 0.369 |
| 24h before close | 195 | 1.69F | 1.24F | 0.373 | 0.327 | 0.549 |
| Final pre-close | 195 | 1.02F | 0.53F | 0.843 | 0.975 | 0.862 |

## Final Accuracy By City

| City | N | Mean Abs Error | Mean Actual-Bucket P | Modal Accuracy |
|---|---:|---:|---:|---:|
| chicago | 65 | 1.61F | 0.602 | 0.615 |
| miami | 65 | 0.52F | 0.974 | 1.000 |
| nyc | 65 | 0.95F | 0.952 | 0.969 |

## Interpretation

This is the first multi-month Kalshi panel. Each date-city panel treats the full set of Kalshi high-temperature range contracts as a discrete probability distribution, projects it into an expected daily high, and compares that value to NOAA/NCEI daily TMAX.

The 24h and 48h rows are included to avoid relying only on near-settlement markets. The final row measures the quality of the market-implied state distribution near contract close.
