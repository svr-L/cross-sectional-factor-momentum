# Executed results — data vintage 2026-09-18

This document records the reference run shipped in `Factor_Momentum.ipynb`. It separates realized performance, signal identification and benchmark-relative inference so that a strong backtest endpoint is not confused with a conclusive alpha claim.

## Run card

| Item | Setting |
|---|---|
| Common ETF sample | 2013-07-19 to 2026-09-18 |
| Common observations | 3,312 |
| Strategy observations after warm-up | 3,156 |
| Factor ETFs | 10 |
| Signal | 6-1 cross-sectional momentum |
| Rebalance | Monthly |
| Implementation | One trading day after signal; weights earn from the next day |
| Primary cost model | Abdi–Ranaldo, trailing 21-day median |
| Cash rate | FRED `DGS3MO`, lagged one day |
| Market benchmark | SPY buy-and-hold |

## Realized net performance

| Strategy | CAGR | Ann. vol. | MaxDD | Sharpe | Sortino | Calmar | Martin |
|---|---:|---:|---:|---:|---:|---:|---:|
| Top-1 80/20 | **17.10%** | 19.03% | -34.29% | **0.851** | **1.206** | **0.499** | **2.195** |
| Top-2 35/35 | 14.54% | 18.00% | -34.82% | 0.766 | 1.078 | 0.418 | 1.803 |
| Equal weight | 12.93% | 17.51% | -37.09% | 0.702 | 0.983 | 0.349 | 1.692 |
| SPY | 13.88% | 17.18% | **-33.72%** | 0.761 | 1.071 | 0.412 | 1.894 |

Gross Top-1 CAGR and Sharpe are 17.57% and 0.873. The AR cost model therefore removes about 47 bps of CAGR and 0.022 Sharpe. Approximate two-way turnover is 5.23× per year.

## Signal-permutation null

Each null portfolio has the same concentration rule, rebalance dates, execution lag and costs as the real strategy; only the selected factor is randomized.

### Top-1 against random Top-1

| Metric | Actual | Null mean | Null 95th percentile | One-sided p |
|---|---:|---:|---:|---:|
| CAGR | 17.10% | 11.38% | 14.33% | **0.001** |
| Sharpe | 0.851 | 0.600 | 0.746 | **0.001** |
| Sortino | 1.206 | 0.843 | 1.062 | **0.002** |
| Calmar | 0.499 | 0.306 | 0.402 | **<0.001** |
| Martin | 2.195 | 1.251 | 1.907 | **0.009** |
| MaxDD | -34.29% | -37.50% | -33.47% | 0.085 |

### Top-2 against random Top-2

| Metric | Actual | Null mean | Null 95th percentile | One-sided p |
|---|---:|---:|---:|---:|
| CAGR | 14.54% | 11.87% | 13.39% | **<0.001** |
| Sharpe | 0.766 | 0.641 | 0.719 | **0.003** |
| Sortino | 1.078 | 0.897 | 1.014 | **0.003** |
| Calmar | 0.418 | 0.319 | 0.369 | **<0.001** |
| Martin | 1.803 | 1.418 | 1.804 | 0.051 |
| MaxDD | -34.82% | -37.27% | -35.00% | **0.034** |

This is the cleanest evidence that the ranking signal contains information.

## Benchmark-relative inference

### Spanning regressions

Net strategy excess returns are regressed on all ten factor-ETF excess returns plus SPY with Newey–West standard errors.

| Strategy | Annualized alpha | t-stat | Two-sided p | R² |
|---|---:|---:|---:|---:|
| Top-1 80/20 | **2.82%** | 1.51 | 0.132 | 0.886 |
| Top-2 35/35 | 0.66% | 0.61 | 0.545 | 0.956 |

For a pre-specified positive-alpha alternative, the Top-1 one-sided p-value is approximately 0.066. That is directionally significant at 10%, but it is not a conventional 5% result and should not be described without qualification.

![Rolling two-year spanning alpha](../assets/rolling_spanning_alpha.png)

The rolling estimate is episodic and turns negative late in the sample, which is why the positive full-period alpha should not be read as a stable annual return premium.

### Difference in Sharpe

| Comparison | Realized ΔSharpe | Ledoit–Wolf t | p |
|---|---:|---:|---:|
| Top-1 minus EW | +0.149 | 1.34 | 0.175 |
| Top-1 minus SPY | +0.090 | 0.77 | 0.445 |

### Paired stationary bootstrap

| Comparison | Mean ΔCAGR | Mean ΔSharpe | P(CAGR > benchmark) | P(Sharpe > benchmark) |
|---|---:|---:|---:|---:|
| Top-1 minus EW | +0.14% | -0.077 | 0.524 | 0.234 |
| Top-2 minus EW | +0.17% | -0.029 | 0.543 | 0.336 |
| Top-1 minus SPY | -0.61% | -0.124 | 0.400 | 0.138 |

The FHS and VAR-sieve engines likewise fail to establish a robust risk-adjusted advantage. This does not contradict the signal-permutation result: an informative selector can beat random concentration while still giving up diversification relative to EW or SPY.

## Multiple-testing control

The grid contains 12 net specifications: 6-1/12-1 × Top-1/Top-2 × AR/CS/fixed costs.

| Test | p-value | Reading |
|---|---:|---|
| White Reality Check | **0.026** | Best mean-return specification beats EW after search correction |
| Hansen SPA, consistent | **0.025** | Same conclusion under a less conservative superior-predictive-ability test |

These tests concern the mean return differential against EW, not the Sharpe difference and not SPY.

## Expanding-window walk-forward

| OOS result | Selected specification | EW, same window |
|---|---:|---:|
| CAGR | **18.94%** | 13.94% |
| Sharpe | **0.849** | 0.679 |
| Martin | **2.089** | 1.557 |
| MaxDD | **-34.29%** | -37.09% |

The test makes 37 quarterly reselections over 2,273 OOS observations. It chooses `6-1|top1|FIXED` 33 times and `6-1|top1|CS` four times. Because the current grid allows the cost proxy to be selected, this is supportive model-selection evidence rather than a final production-grade OOS claim. The cost model should be fixed ex ante in the next run.

## Breadth and universe robustness

Top-1 minus EW Sharpe gaps by breadth:

| Number of factors | Mean gap | 5th percentile | 95th percentile | Share positive |
|---:|---:|---:|---:|---:|
| 4 | 0.033 | -0.085 | 0.095 | 80.0% |
| 5 | 0.031 | -0.072 | 0.115 | 66.7% |
| 6 | 0.059 | -0.024 | 0.144 | 86.7% |
| 7 | 0.089 | 0.041 | 0.129 | 100% |
| 8 | 0.103 | 0.065 | 0.137 | 100% |
| 9 | 0.130 | 0.096 | 0.157 | 100% |
| 10 | 0.149 | 0.149 | 0.149 | 100% |

The leave-one-out gap stays positive after removing every ETF. The minimum is 0.087 when Value is removed; the maximum is 0.162 when LowVol is removed. Intermediate breadth buckets use only 15 random subsets, so an exhaustive subset analysis remains desirable.

## Risk overlays

### Volatility targeting

| Target | Mean exposure | Net CAGR | Realized vol. | MaxDD | Sharpe gap vs matched SPY |
|---:|---:|---:|---:|---:|---:|
| 5.0% | 0.38× | 6.04% | 5.72% | -6.74% | +0.082 |
| 7.5% | 0.56× | 8.35% | 8.49% | -10.26% | +0.089 |
| 10.0% | 0.74× | 10.42% | 11.17% | -13.19% | +0.072 |
| 12.5% | 0.90× | 12.34% | 13.66% | -16.58% | +0.043 |
| 15.0% | 1.03× | 14.38% | 15.91% | -19.87% | +0.024 |
| 17.5% | 1.14× | 16.20% | 17.83% | -22.63% | +0.006 |
| 20.0% | 1.22× | 17.63% | 19.45% | -24.71% | +0.009 |

The overlay strongly reshapes the path but adds little relative Sharpe at high targets when SPY receives the same treatment.

### Fixed Low-Vol sleeve

| Strategy | Net CAGR | Ann. vol. | Sharpe | MaxDD | Martin |
|---|---:|---:|---:|---:|---:|
| Top-1 base | 17.10% | 19.03% | 0.851 | -34.29% | 2.195 |
| Top-1 + 20% sleeve | 15.85% | 17.51% | 0.848 | -33.93% | 2.213 |
| Top-2 base | 14.54% | 18.00% | 0.766 | -34.82% | 1.803 |
| Top-2 + 33% sleeve | 13.29% | 16.13% | 0.768 | -34.21% | 1.921 |

Because the unsleeved strategy already holds LowVol, the combined average LowVol weights are about 32.9% for Top-1 and 40.7% for Top-2. The sleeve smooths the path modestly but does not improve Top-1 Sharpe.

## Reference-run caveats

1. The 2026 endpoint is unusually strong; repeat the analysis at historical cutoffs.
2. The ten-ETF common sample is short and begins in 2013.
3. The long–short academic-factor module did not run because the remote data endpoint returned a `TypeError`; use a local CSV fallback.
4. Do not interpret White/SPA as evidence of a Sharpe advantage or market alpha.
5. Treat the DSR as secondary because the trial specifications are highly correlated.
6. PSR, BCa-Sharpe and DSR callers were corrected to use excess returns consistently; their legacy outputs were intentionally cleared pending a refreshed run.

All machine-readable values used in README figures are stored in `results/run_2026-09-18.json`.
