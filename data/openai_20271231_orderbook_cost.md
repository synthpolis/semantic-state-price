# Polymarket Order-Book Cost: OpenAI 2027-12-31

Generated: `2026-05-08T03:28:21Z`
Shock: `+/- 0.050` YES-probability points

## Summary

- Source markets with books: `12`
- Median CLOB spread: `72.9%`
- Stress directions inside the current spread: `14`
- Finite crossed-depth cost cases: `10`
- Cheapest crossed-depth notional per `$1B` oracle move: `$1.40`
- Median crossed-depth notional per `$1B` oracle move: `$13.04`

## Top Sensitivities With Book Depth

| Market | Oracle Move | Bid | Ask | Spread | Up Cost | Down Pressure | Status |
|---|---:|---:|---:|---:|---:|---:|---|
| Will OpenAI not IPO by December 31, 2027? | $31B | 0.23 | 0.45 | 64.7% | n/a | n/a | target_inside_spread |
| OpenAI IPO closing market cap above $1T? | $25B | 0.59 | 0.60 | 1.7% | $358.33 | $224.93 | crosses_displayed_depth |
| OpenAI IPO closing market cap above $1.6T? | $18B | 0.46 | 0.50 | 8.3% | $25.20 | $46.97 | crosses_displayed_depth |
| OpenAI IPO closing market cap above $800B? | $16B | 0.71 | 0.73 | 2.8% | $258.09 | $39.69 | crosses_displayed_depth |
| OpenAI IPO closing market cap above $1.4T? | $10B | 0.50 | 0.51 | 2.0% | $393.43 | $262.12 | crosses_displayed_depth |
| Will OpenAI’s market cap be between $750B and $1T at market close on IPO day by December 31, 2027? | $9B | 0.11 | 0.29 | 90.0% | n/a | n/a | target_inside_spread |
| OpenAI IPO closing market cap above $1.2T? | $7B | 0.54 | 0.55 | 1.8% | $31.61 | $127.65 | crosses_displayed_depth |
| Will OpenAI’s market cap be between $1T and $1.25T at market close on IPO day by December 31, 2027? | $6B | 0.09 | 0.31 | 110.0% | n/a | n/a | target_inside_spread |
| Will OpenAI’s market cap be between $1.25T and $1.5T at market close on IPO day by December 31, 2027? | $2B | 0.06 | 0.18 | 100.0% | n/a | n/a | target_inside_spread |
| Will OpenAI’s market cap be $1.5T or greater at market close on IPO day by December 31, 2027? | $2B | 0.23 | 0.55 | 81.0% | n/a | n/a | target_inside_spread |
| Will OpenAI’s market cap be between $500B and $750B at market close on IPO day by December 31, 2027? | $1B | 0.08 | 0.19 | 81.5% | n/a | n/a | target_inside_spread |
| Will OpenAI’s market cap be less than $500B at market close on IPO day by December 31, 2027? | $0B | 0.05 | 0.17 | 109.1% | n/a | n/a | target_inside_spread |

## Interpretation

This is an approximate displayed-depth model, not a final manipulation-cost proof. `Up Cost` is the notional required to buy YES asks through the 5-point target. `Down Pressure` is the displayed bid notional that would be crossed by selling YES through the 5-point target.

Cases marked `target_inside_spread` are not free manipulation. They mean the stress target lies inside the current bid/ask spread, so a midpoint-based oracle would be fragile and should penalize or exclude the source market unless a trade/TWAP rule supplies a firmer price.
