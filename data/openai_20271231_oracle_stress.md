# Oracle Stress: OpenAI 2027-12-31

Generated: `2026-05-08T03:20:06Z`
Shock: `+/- 0.050` probability points per constituent

## Baseline

- No IPO probability: `0.298`
- IPO probability: `0.702`
- Expected valuation, unconditional: `$932B`
- Expected valuation, conditional on IPO: `$1,328B`
- Projection loss: `0.131248`

## Stress Summary

- Max unconditional index move: `$31B`
- Median unconditional index move: `$8B`
- 75th percentile index move: `$16B`
- Oracle concentration ratio: `0.033`
- Stress confidence score: `0.967`

## Top Constituent Sensitivities

| Max Move | Conditional Move | P | Weight | Volume | Market |
|---:|---:|---:|---:|---:|---|
| $31B | $41B | 0.325 | 9.28 | $10,748 | Will OpenAI not IPO by December 31, 2027? |
| $25B | $24B | 0.470 | 41.56 | $1,038,346 | OpenAI IPO closing market cap above $1T? |
| $18B | $25B | 0.210 | 10.63 | $41,243 | OpenAI IPO closing market cap above $1.6T? |
| $16B | $10B | 0.685 | 11.42 | $91,304 | OpenAI IPO closing market cap above $800B? |
| $10B | $13B | 0.315 | 10.85 | $51,581 | OpenAI IPO closing market cap above $1.4T? |
| $9B | $6B | 0.275 | 4.01 | $54 | Will OpenAI’s market cap be between $750B and $1T at market close on IPO day by December 31, 2027? |
| $7B | $9B | 0.450 | 12.39 | $239,622 | OpenAI IPO closing market cap above $1.2T? |
| $6B | $9B | 0.170 | 7.95 | $2,848 | Will OpenAI’s market cap be between $1T and $1.25T at market close on IPO day by December 31, 2027? |
| $2B | $3B | 0.160 | 4.66 | $105 | Will OpenAI’s market cap be between $1.25T and $1.5T at market close on IPO day by December 31, 2027? |
| $2B | $2B | 0.170 | 1.00 | $0 | Will OpenAI’s market cap be $1.5T or greater at market close on IPO day by December 31, 2027? |
| $1B | $6B | 0.265 | 1.00 | $0 | Will OpenAI’s market cap be between $500B and $750B at market close on IPO day by December 31, 2027? |
| $0B | $0B | 0.160 | 1.00 | $0 | Will OpenAI’s market cap be less than $500B at market close on IPO day by December 31, 2027? |

## Interpretation

This is a constituent-level sensitivity test, not a full manipulation-cost model. It asks how far the fitted oracle moves if one source market's implied probability is shifted up or down by the shock size while all other markets are fixed.

A production perp oracle should combine this with order-book depth, TWAP windows, source-market inclusion rules, and leverage/funding caps.
