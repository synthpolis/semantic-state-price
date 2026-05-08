# Polymarket Crypto Entity Pool

Generated: `2026-05-08T05:20:04Z`

## Pool Coverage

- Markets: `3197`
- Closed markets: `2210`
- Active markets: `987`
- Effective semantic market count: `1483.9`
- Date span: `2024-03-29` to `2027-01-01`
- Months covered: `29`

| Target | Market type | Count |
|---|---|---:|
| BTC | `barrier_threshold` | 25 |
| BTC | `close_threshold` | 270 |
| BTC | `institutional_proxy` | 10 |
| BTC | `range_bucket` | 230 |
| BTC | `record_or_race` | 172 |
| BTC | `relative_proxy` | 872 |
| BTC | `semantic_proxy` | 326 |
| ETH | `barrier_threshold` | 6 |
| ETH | `close_threshold` | 272 |
| ETH | `institutional_proxy` | 7 |
| ETH | `range_bucket` | 193 |
| ETH | `record_or_race` | 92 |
| ETH | `relative_proxy` | 548 |
| ETH | `semantic_proxy` | 174 |

## Direct Threshold Validation

| Horizon | N | Brier | Log loss | Accuracy | Mean probability on realized side |
|---|---:|---:|---:|---:|---:|
| 7d | 13 | 0.194 | 0.573 | 76.9% | 58.5% |
| 72h | 212 | 0.174 | 0.521 | 73.1% | 66.8% |
| 48h | 212 | 0.142 | 0.434 | 75.9% | 72.1% |
| 24h | 250 | 0.127 | 0.384 | 81.2% | 75.8% |
| 6h | 342 | 0.091 | 0.288 | 87.4% | 81.7% |
| final | 342 | 0.075 | 0.235 | 90.4% | 85.4% |
