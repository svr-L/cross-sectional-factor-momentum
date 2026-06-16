# ETF Factor Momentum: Alpha Validation Under Implementation Frictions

An ETF-based implementation and stress test of **cross-sectional factor momentum**. The project asks whether an Arnott-style factor-momentum idea remains useful after it is translated into a **tradable ETF implementation** with realistic timing, transaction-cost proxies, passive benchmarking, signal-permutation nulls, spanning regressions, dependence-aware bootstraps and data-snooping controls.

This is best read as an **alpha-validation / alpha due-diligence** project. It does not claim that the retained strategy is a production-ready standalone alpha. The main contribution is a disciplined research pipeline that separates a weak-but-interesting signal from static factor exposure, benchmark effects, implementation frictions and specification search.

---

## Research question

> Does cross-sectional factor momentum survive a tradable ETF implementation once we account for next-day execution, transaction costs, passive market exposure, random-selection nulls, dependence-aware inference and multiple-testing controls?

The answer from the current run is nuanced:

- **Yes, there is some signal value:** the top-factor momentum rule improves realized drawdown-adjusted performance and beats structurally identical random-selection strategies, especially on Calmar / Martin / max drawdown.
- **No, it is not a robust standalone alpha:** the edge is weak in paired bootstrap comparisons, is largely spanned by static factor/market exposure, and does not pass White / SPA data-snooping controls.

The most defensible interpretation is therefore:

> ETF factor momentum contains a modest **defensive timing effect**, but the realized performance is largely explained by static factor/market exposures rather than a strong dynamic alpha.

---

## Tradable universe

Public-data ETF mapping:

| Factor sleeve | ETF |
|---|---:|
| Value | `RPV` |
| Size | `SIZE` |
| Momentum | `MTUM` |
| Quality | `SPHQ` |
| Low Volatility | `SPLV` |

Passive market benchmark: `SPY`.

The current final run uses the common-data ETF sample from **2013-04-19 to 2026-06-05**. The raw panel starts in 2005 because some ETFs have earlier histories, but the strategy is evaluated on the common intersection.

---

## Methodology

### Signal

- Cross-sectional cumulative log-return momentum.
- Main variant: **6−1** formation window: 6-month lookback, skipping the most recent month.
- Alternative variant: **12−1**.
- Signals are sampled at month-end trading dates.

### Portfolio construction

Main portfolios:

- `MomTop1_80_20`: 80% in the strongest factor ETF, 20% split across the remaining four.
- `MomTop2_35_35`: 35% / 35% in the top two factors, 30% split across the remaining three.
- `EW`: equal-weighted blend of the five factor ETFs.

The notebook also tests inverse-volatility sizing, rank / quantile weighting and walk-forward model selection.

### Execution timing

The default setting uses genuine next-day implementation:

1. signal observed at month-end close;
2. trade executed at the close of the next trading day;
3. new weights first earn returns from the following trading day.

This avoids the common one-day look-ahead that occurs when a month-end signal earns the next day's close-to-close return as if it had already been implemented.

### Costs and risk-free rate

Transaction costs are estimated through:

- Abdi–Ranaldo high/low/close spread proxy (`AR`);
- Corwin–Schultz high/low spread proxy (`CS`);
- flat fixed-bps one-way cost sanity check (`FIXED`).

Costs are charged using drifted pre-trade weights and one-way half-spread estimates. The final run used `AR` as the primary estimator.

Risk-adjusted statistics use a historical risk-free series. The default source is FRED `DGS3MO`; the final run used Yahoo `^IRX` as a fallback because FRED timed out during execution.

---

## Headline realized results

Final run configuration:

| Item | Value |
|---|---:|
| Common ETF sample | 2013-04-19 → 2026-06-05 |
| Backtest observations | 3,145 |
| Implementation lag | 1 trading day |
| Primary cost estimator | Abdi–Ranaldo (`AR`) |
| Risk-free used in run | Yahoo `^IRX` fallback |
| Stationary-bootstrap block length | 30 |

### Realized net performance, primary AR cost estimator

| Strategy | CAGR | AnnVol | MaxDD | Sharpe | Sortino | Calmar | Ulcer | Martin |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `MomTop1_80_20` | 13.44% | 17.58% | -33.19% | 0.7315 | 1.0327 | 0.4048 | 0.0560 | 2.1671 |
| `MomTop2_35_35` | 11.61% | 16.46% | -37.07% | 0.6717 | 0.9344 | 0.3134 | 0.0627 | 1.6453 |
| `EW` | 12.09% | 16.44% | -38.10% | 0.6984 | 0.9721 | 0.3174 | 0.0622 | 1.7338 |
| `SPY` | 13.87% | 17.19% | -33.72% | 0.7666 | 1.0771 | 0.4113 | 0.0659 | 1.9054 |

Interpretation:

- `MomTop1_80_20` beats `EW` on realized CAGR, Sharpe, MaxDD and Martin.
- `SPY` remains stronger on realized CAGR and Sharpe.
- `MomTop1_80_20` improves drawdown-adjusted performance relative to `SPY` through a better Martin ratio and slightly shallower max drawdown.

---

## Signal-permutation null: where the positive result comes from

The cleanest evidence of signal value is the **random-selection null**. This test compares the real momentum strategy against strategies with the same 80/20 structure, same rebalance dates, same costs and same timing, but random factor selection each month.

### `MomTop1_80_20` vs structurally identical random top-1 strategies

| Metric | Actual | Null mean | Null p05 | Null p95 | One-sided p-value |
|---|---:|---:|---:|---:|---:|
| CAGR | 13.44% | 10.96% | 1.78% | 20.27% | 0.073 |
| Sharpe | 0.7315 | 0.6103 | 0.1294 | 1.0963 | 0.083 |
| Calmar | 0.4048 | 0.2902 | 0.0339 | 0.7201 | 0.029 |
| Martin | 2.1671 | 1.3305 | 0.0655 | 3.7925 | 0.034 |
| MaxDD | -33.19% | -38.34% | -58.71% | -20.72% | 0.042 |

This is the most constructive result in the project: the momentum signal is not merely a random way to concentrate the portfolio. Its advantage is strongest on drawdown-adjusted metrics, suggesting a **defensive selection effect** rather than a high-conviction return-forecasting alpha.

---

## Robustness: why this is not a standalone alpha claim

### Paired stationary bootstrap

The paired bootstrap rebuilds all strategies inside each resampled return panel and compares strategy-minus-benchmark metrics within the same bootstrap replica.

#### `MomTop1_80_20 − EW`, net AR

| Metric | Mean diff | p05 | p50 | p95 | P(strategy > benchmark) |
|---|---:|---:|---:|---:|---:|
| CAGR | -0.11% | -3.41% | -0.17% | 3.46% | 0.469 |
| Sharpe | -0.0637 | -0.2425 | -0.0642 | 0.1150 | 0.277 |
| Martin | -0.2941 | -1.2827 | -0.2158 | 0.5112 | 0.278 |
| MaxDD | -1.87% | -9.63% | -1.45% | 4.72% | 0.379 |

#### `MomTop1_80_20 − SPY`, net AR

| Metric | Mean diff | p05 | p50 | p95 | P(strategy > benchmark) |
|---|---:|---:|---:|---:|---:|
| CAGR | -1.91% | -6.74% | -1.75% | 2.59% | 0.215 |
| Sharpe | -0.1240 | -0.3522 | -0.1217 | 0.0886 | 0.167 |
| Martin | -0.5010 | -1.6426 | -0.4274 | 0.4091 | 0.171 |

The realized result is therefore not robustly dominant under dependence-aware paired resampling.

### Spanning and static replication

A Newey-West spanning regression of `MomTop1_80_20` on the five factor ETFs plus `SPY` gives:

| Statistic | Value |
|---|---:|
| Annualized alpha | 0.49% |
| alpha t-stat | 0.28 |
| alpha p-value | 0.778 |
| R² | 0.888 |

A static non-negative replication is highly similar to the actual strategy:

| Statistic | Value |
|---|---:|
| Corr(static, actual) | 0.942 |
| R² | 0.888 |
| Static Sharpe | 0.747 |
| Actual Sharpe | 0.732 |

Implied long-only static weights:

| Sleeve | Weight |
|---|---:|
| Momentum | 39.4% |
| Value | 19.2% |
| Size | 0.0% |
| Quality | 12.0% |
| LowVol | 15.1% |
| SPY | 14.3% |

This is the main reason the project does not claim standalone alpha. Much of the strategy can be replicated by a static factor/market blend.

### Multiple-testing controls

The specification grid covers 16 strategies across signal variants, concentrations and cost assumptions. Against the equal-weight benchmark:

| Test | Result |
|---|---:|
| White Reality Check p-value | 0.2697 |
| Hansen SPA consistent p-value | 0.2690 |
| Best specification | `6-1|top1|GROSS` |
| Best mean annualized excess over EW | 1.91% |

The Deflated Sharpe Ratio is high in the current run, but the specifications are highly correlated, making the independent-trials adjustment too lenient. The SPA result is treated as the more reliable multiplicity-robust verdict.

---

## Mechanism: defensive timing, not alpha cannon

The top-1 momentum pick does not systematically choose the best-performing factor in the next month. Selection quality is close to random on average:

| Regime | Mean rank | P(worst) | P(best) | Months |
|---|---:|---:|---:|---:|
| Overall | 3.020 | 22.52% | 23.84% | 151 |
| Low vol | 3.000 | 25.68% | 25.68% | 74 |
| High vol | 3.039 | 19.48% | 22.08% | 77 |

Rank 1 = next month's worst factor, rank 5 = best factor. The signal is not a strong winner-picker. The more plausible mechanism is defensive: in high-volatility months it appears to avoid the worst factor somewhat more often than random, which is consistent with the strategy's stronger evidence on Martin / Calmar / MaxDD than on mean returns.

---

## Additional checks

### Long-short academic factor comparison

To test whether the ETF wrapper is the issue, the notebook also applies the same logic to Fama-French-style long-short factor returns.

| Strategy | CAGR | Sharpe | MaxDD | Martin |
|---|---:|---:|---:|---:|
| Long-short `MomTop1` | 1.99% | 0.0683 | -59.37% | 0.0041 |
| Long-short `MomTop2` | 3.20% | 0.2315 | -28.18% | 0.1042 |
| Long-short `EW` | 2.88% | 0.2174 | -18.27% | 0.1344 |

The long-short result does not rescue the signal. This supports the interpretation that the ETF result is mostly a long-only/style/market-interaction effect rather than pure factor-momentum alpha.

### Walk-forward model selection

The notebook runs an expanding-window walk-forward exercise that reselects the best specification approximately quarterly.

| Strategy | CAGR | Sharpe | Sortino | Calmar | Martin | MaxDD |
|---|---:|---:|---:|---:|---:|---:|
| OOS selected | 13.88% | 0.6851 | 0.9661 | 0.4058 | 1.8975 | -34.21% |
| EW same window | 12.23% | 0.6351 | 0.8825 | 0.3210 | 1.4638 | -38.10% |

The selected specification is almost always `6-1|top1|GROSS`, so this is a useful OOS sanity check rather than evidence of a highly adaptive selector.

---

## Final interpretation

The project's best-supported claim is:

> A simple top-factor ETF momentum rule improves realized drawdown-adjusted performance and beats a structurally identical random-selection null, but its apparent edge is mostly defensive, substantially spanned by static factor/market exposures, and not robust enough under paired bootstrap and SPA controls to be presented as a standalone alpha.

That makes this repository useful as a **factor-timing alpha-validation case study**:

- it shows how to translate an academic idea into an investable ETF test;
- it evaluates timing, costs, benchmark choice and null models;
- it distinguishes signal value from concentration and static exposure;
- it avoids overclaiming when the evidence is mixed.

---

## Repository structure

```text
.
├── Factor_Momentum.ipynb          # Clean research notebook
├── factor_momentum_core.py        # Reusable implementation and inference utilities
├── README.md
├── requirements.txt
└── .gitignore
```

---

## How to run

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
jupyter notebook Factor_Momentum.ipynb
```

The notebook defaults to public Yahoo Finance data. If FRED is available, `DGS3MO` is used for the historical risk-free rate. If FRED times out, the code falls back to Yahoo `^IRX`; if all sources fail, it uses a zero-risk-free fallback and prints the source explicitly.

---

## Limitations

- The investable ETF universe is intentionally small; five ETFs limit cross-sectional breadth.
- Some cost proxies based on OHLC data are noisy and may overstate trading frictions for liquid ETFs.
- The current positive result is strongest on drawdown-adjusted metrics, not on robust mean-return dominance.
- Static spanning explains much of the realized strategy behaviour.
- Multiple-testing controls do not support a strong standalone alpha claim.
- Results can vary slightly with data-vintage updates from Yahoo Finance / FRED.

---

## Not investment advice

This repository is a research project and does not constitute investment advice or a production trading system.
