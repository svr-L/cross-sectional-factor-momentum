# Research design

## Question

Does cross-sectional momentum across investable equity factor ETFs add value after realistic timing, costs, static-exposure controls, dependence-aware inference and specification-search correction?

The project deliberately separates three hypotheses:

1. **Signal information:** does the momentum ranking select factors better than chance?
2. **Portfolio improvement:** does exploiting that information beat a diversified factor blend or SPY?
3. **Dynamic alpha:** does the strategy add return beyond a static combination of the same factor ETFs and the market?

These are not equivalent. A signal can beat random selection while a concentrated implementation still loses diversification benefits.

## Causal timeline

For signal date \(t\) at month-end:

1. build 6-1 or 12-1 momentum using prices available at the close of \(t\);
2. rank the factor ETFs cross-sectionally;
3. retain the drifted pre-trade portfolio on the next trading day;
4. execute target weights at that next close;
5. charge costs against the absolute change from drifted pre-trade weights;
6. let the new portfolio first earn returns on the following trading day.

`IMPLEMENTATION_LAG = 1` enforces this convention. The historical risk-free series is also lagged one day.

## Signal

The 6-1 score sums 126 daily log returns after shifting the return panel by 21 trading days. The 12-1 score uses 252 formation days with the same 21-day skip. Skipping the most recent month avoids conflating medium-term factor momentum with one-month reversal and matches the standard momentum convention.

The research grid contains:

- formation horizons: 6-1 and 12-1;
- concentration: Top-1 80/20 and Top-2 35/35;
- cost sensitivities: AR, CS and fixed 2 bps.

Inverse-volatility, rank and quantile builders are diagnostics rather than hidden extra search dimensions in the headline result.

## Benchmarks

### Equal-weight factor blend

EW asks whether dynamic ranking improves on diversified exposure to the same opportunity set. It is economically relevant but not a neutral market portfolio.

### SPY

SPY asks whether the additional machinery beats a passive market investment. It is included in realized metrics, paired resampling, Sharpe-difference tests and spanning.

### Random-selection null

Random portfolios preserve dates, costs, concentration and execution while randomizing only the selected factor. They test the ranking rule itself and avoid conflating signal quality with concentration.

### Static spanning replica

The Newey–West regression is

\[
r_{p,t}-r_{f,t}=\alpha+\beta^{\top}(f_t-r_{f,t})+\gamma(r_{SPY,t}-r_{f,t})+\varepsilon_t.
\]

A zero alpha means the dynamic return is statistically reproducible by constant exposures. The static-replication portfolio makes that statement economically tangible.

## Transaction costs

The backtest estimates daily one-way costs from OHLC data using:

- Abdi–Ranaldo (primary);
- Corwin–Schultz;
- fixed 2 bps sensitivity.

Estimates are smoothed with a trailing median and charged as

\[
TC_t=\sum_i c_{i,t}\lvert w^{target}_{i,t}-w^{drift}_{i,t}\rvert.
\]

The sum of absolute changes is reported as two-way turnover; half of that number is also shown for comparison with common one-way turnover conventions.

## Inference map

| Question | Primary method | Null |
|---|---|---|
| Is the signal informative? | Signal-permutation Monte Carlo | Random selection is at least as good |
| Does Top-1 beat EW/SPY on Sharpe? | Ledoit–Wolf studentized block test | Equal Sharpe ratios |
| Is the strategy robust to dependence? | Stationary bootstrap, FHS, VAR-sieve | Paired metric difference is non-positive |
| Is there dynamic alpha? | Newey–West spanning regression | \(\alpha = 0\) |
| Did specification search create the result? | White Reality Check / Hansen SPA | Best candidate does not beat EW |
| Does the chosen model survive time? | Expanding-window walk-forward | Selected model does not beat same-window EW |
| Is the finding universe-specific? | Leave-one-out / breadth gradient | Gap depends on one ETF or does not rise with breadth |

## Dependence-aware engines

### Stationary bootstrap

The full common-sample return panel, cost panel and benchmark are resampled jointly with common indices. The signal and complete portfolio are rebuilt inside each replica.

### Filtered Historical Simulation

Each factor is filtered with AR(p)–GJR–GARCH(1,1). Standardized residual rows are resampled jointly to preserve contemporaneous cross-factor dependence and then reinflated through their volatility recursions.

### VAR-sieve wild bootstrap

A VAR preserves linear cross-factor lead/lag structure, while wild residual multipliers retain heteroskedasticity.

## Risk overlays

The deterministic volatility-target experiment is designed as a fair control:

- each strategy and benchmark receives its own trailing-volatility estimate;
- exposure is lagged one day;
- uninvested capital earns the historical risk-free rate;
- exposure turnover pays a fixed one-way cost;
- leverage is capped at 1.5×.

The Low-Vol sleeve is blended into the monthly factor weights and processed by the original backtest engine. Since LowVol is already in the selection universe, the effective combined LowVol allocation is

\[
w_{LV}^{combined}=\lambda+(1-\lambda)w_{LV}^{FM},
\]

and the incremental LowVol exposure is \(\lambda(1-w_{LV}^{FM})\), not \(\lambda-w_{LV}^{FM}\).

## Pre-specified next extension

The next substantive extension is a dynamic allocation between Factor Momentum and LowVol driven by forecast volatility or a probabilistic tail-state estimate. It should be evaluated in a frozen horse race:

1. raw Factor Momentum;
2. deterministic volatility-targeted Factor Momentum;
3. static FM–LowVol blend;
4. dynamic FM–LowVol allocation;
5. same-rule SPY and EW controls.

The decision rule and all hyperparameters should be fixed before examining the final holdout. The objective is not merely a smoother wealth path, but incremental alpha or Sharpe after applying the identical risk rule to the benchmarks.

## Known threats to validity

- latest-inception bias truncates the ten-factor sample to 2013;
- style ETFs overlap and contain large common market exposure;
- Yahoo OHLC data and spread estimators are proxies, not executable quotes;
- a strong final vintage can dominate a short sample;
- the current walk-forward grid also varies cost estimator and should be rerun with costs frozen;
- only a limited number of random subsets are sampled at intermediate breadth;
- academic long–short factors require a stable local input for reproducibility.
