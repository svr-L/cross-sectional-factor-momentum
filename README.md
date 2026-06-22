# Factor Momentum on Equity Risk-Factor ETFs

An ETF-based implementation of **cross-sectional Factor Momentum** inspired by **Arnott, Clements, Kalesnik & Linnainmaa**, evaluated under a **historical risk-free rate**, **proxy transaction costs**, a **passive market benchmark**, and **dependence-aware resampling** (Politis–Romano stationary bootstrap, a paired-difference test, and a signal-permutation null).

---

## What changed in this revision

This version corrects two issues that affected the previously reported numbers and adds several robustness refinements. **The numeric result tables from the previous README are therefore no longer valid and have been removed** (see *Results* below for how to regenerate them).

**Corrections**

1. **Genuine next-day implementation (timing fix).** Previously the new target weights earned the *entry-day* close-to-close return, which is equivalent to executing at the **signal-date** close — a roughly one-day look-ahead that mildly flatters the more concentrated momentum portfolios relative to equal weight. Implementation is now controlled by `IMPLEMENTATION_LAG` (trading days). With the default `IMPLEMENTATION_LAG = 1`, the trade is executed at the **close of the day after the signal**, the portfolio holds the drifted *pre-trade* weights on the trade day, and the new weights first earn on the following day. `IMPLEMENTATION_LAG = 0` reproduces the old "execute at the signal-date close" convention.
2. **Bootstrap on the common sample.** The stationary bootstrap was being fed the *raw* return panel, which carries leading `NaN`s from the later-inception ETFs; resampling over the full index and dropping `NaN`s afterwards fragments the blocks at the inception boundary. Returns are now reduced to the **common (no-missing) sample before** resampling, so block structure is preserved.

**Refinements**

3. **Paired-difference robustness test.** Inside each bootstrap replica all strategies are computed on the same resampled panel, so the within-replica difference (e.g. `MomTop1_80_20 − EW`) is a valid **paired** bootstrap. The notebook reports the distribution of ΔCAGR / ΔSharpe / ΔMartin and the share of replicas in which the strategy beats the benchmark, `P(strat > bench)`. This is the headline robustness statistic.
4. **Passive market benchmark.** `SPY` (buy-and-hold) is added alongside the equal-weight factor blend, threaded through the realized tables, the wealth plots and the bootstrap.
5. **Signal-permutation null.** A new section benchmarks the strategy against structurally identical but **signal-free** strategies (see *Why EW is not a neutral benchmark*).
6. **Cost realism.** A flat **fixed-bps** one-way cost (`TC_FIXED_BPS`) is added next to the AR/CS proxies as a sanity check, since OHLC-based estimators are noisy and tend to *overstate* spreads on liquid ETFs. The omission of the Corwin–Schultz overnight (gap) adjustment — which needs open prices, not in this OHLC bundle — is documented in code.
7. **Sortino denominator.** Now the **target semideviation** `sqrt(E[min(excess, 0)²])` (root-mean-square of downside excess returns), rather than the standard deviation of the truncated series.
8. **Turnover labelling.** `Σ|Δw|` is reported as **two-way** turnover, with the **one-way** figure (half) alongside it for comparison with typical one-way turnover quotes. The cost charge `Σ c·|Δw|` with `c` = half-spread is unchanged and is not double-counting.

**Further robustness layers (this revision)**

9. **Spanning regression.** Newey-West (HAC) regression of the strategy's excess return on the five factor ETFs' excess returns (plus `SPY`); a zero alpha means the strategy is *spanned* by static factor exposure. This is the benchmark that sidesteps the `SPY` vs `SPY − rf` question (everything is in excess returns).
10. **Inverse-volatility weighting.** The same momentum selection sized by inverse volatility instead of fixed 80/20 / 35/35, to separate *selection* from *concentration*; plus an inverse-vol-of-all blend as a risk-parity-like alternative to equal weight.
11. **Serial-dependence diagnostics.** Ljung-Box on levels and squares and Engle's ARCH-LM, to test for the mean-reversion/autoregression and volatility clustering that determine whether the bootstrap engine matters.
12. **Dependence-aware bootstrap engines.** A **Filtered Historical Simulation** (AR(p)-GJR-GARCH(1,1) filtering, row-resampled standardized residuals, re-inflation) that preserves volatility clustering and fat left tails, and a **VAR(p)-sieve wild bootstrap** that preserves cross-factor lead-lag — both as selectable alternatives to the stationary bootstrap.
13. **Sharpe-ratio inference.** The **Ledoit-Wolf (2008)** HAC + studentized-block test for the difference of two Sharpe ratios, and the **Probabilistic Sharpe Ratio** (skew/kurtosis-aware).
14. **Break-even transaction cost.** The flat one-way cost (bps) at which the edge over EW / SPY vanishes — a single, robust cost-sensitivity number.
15. **BCa intervals.** Bias-corrected and accelerated intervals (circular-block bootstrap + block jackknife) for the realized Sharpe and CAGR.
16. **Regime / subsample stability.** Metrics by calendar year, by sample halves, and by trailing market-volatility regime.
17. **Multiple-testing control.** **White's (2000) Reality Check** and **Hansen's (2005) SPA** over the variant × concentration × cost grid, plus the **Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014)** on the best specification.

**Fixes after the first full run**

18. **Risk-free cascade.** FRED (`DGS3MO`) → Yahoo `^IRX` (13-week T-bill) → zero, so a FRED outage no longer silently forces a zero risk-free.
19. **Benchmark window alignment.** `SPY`'s realized metrics are computed on the same post-warm-up window as the strategies (both in the realized tables and inside every bootstrap replica).
20. **FHS numerical guard.** Simulated returns from the AR-GJR-GARCH re-inflation are sanitised and clipped to [−99%, +100%] (non-binding on real data) so pathological draws can no longer produce `NaN`/overflow in the wealth path.

**Extensions: localising the gap**

21. **Long-short academic factors.** The same cross-sectional momentum signal run on the Fama-French **long-short** factors (SMB, HML, RMW, CMA, Mom), **restricted to the ETF common-sample window** (`LONGSHORT_MATCH_ETF_WINDOW`) for an apples-to-apples comparison, with the paired-difference and signal-permutation tests and a side-by-side ETF-vs-long-short table — to test whether the edge lives in the factor construction or the long-only ETF vehicle.
22. **True out-of-sample walk-forward.** Expanding-window protocol that re-selects the best specification on past data only and banks its future returns, compared to equal-weight on the same window. The grid is **net-only** (`SPEC_GRID_NET_ONLY`), so the OOS pick is compared fairly to net equal-weight (no gross-spec auto-selection).
23. **Rank / quantile weighting + one-flag extended universe.** Long-top-quantile and rank-proportional builders that separate selection from concentration and scale to any N; setting `USE_EXTENDED_UNIVERSE = True` re-points the entire notebook onto a pre-committed extended single-factor ETF universe (`EXTENDED_TICKERS`) for the breadth test.
24. **Conditional (regime) spanning + rolling alpha.** A two-alpha spanning regression interacting the constant and loadings with a high/low market-volatility dummy (Newey-West), plus a rolling 2-year alpha, to see whether the zero full-sample alpha hides a regime-conditional one.
25. **Spanning decomposition + selection mechanism.** A static-replication portfolio (fixed spanning betas) that makes "spanned" concrete, and a selection-quality diagnostic that ranks the forward return of the picked factor by regime.
26. **Universe robustness.** Leave-one-out (drop each ETF) and a breadth gradient (Sharpe gap over equal-weight across random subsets of increasing size), to test whether the extended-breadth result is genuinely breadth-driven rather than a single-name or lucky-universe artefact. Also fixed two stale printed labels (the rank/quantile and selection-quality cells now report the live factor count) and hardened the weight builders so the breadth sweep is safe for small subsets (the 80/20 and 35/35 builders renormalise instead of dividing by zero when there is no "rest" bucket, e.g. a two-ETF subset).

---

## Project objective

The project studies whether an Arnott-style factor-momentum signal remains attractive once it is translated from an academic construct into a **tradable ETF implementation** and stress-tested with realistic frictions and dependence-aware inference. The notebook covers:

* **6–1** and **12–1** cross-sectional factor-momentum signal construction;
* a **monthly rebalancing backtest with genuine next-day implementation and drifting weights** between rebalances;
* realized **gross** and **net-of-costs** performance, plus a **passive market benchmark** (`SPY`);
* historical **daily risk-free** adjustment (default FRED `DGS3MO`, `SOFR` optional);
* proxy transaction costs via **Abdi–Ranaldo (2017)** and **Corwin–Schultz (2012)**, plus a **flat-bps** sanity check;
* **stationary-bootstrap** robustness with the full strategy rebuilt inside each replica;
* a **paired-difference** bootstrap test and a **signal-permutation null**.

## Data

Two data sources are supported:

1. the **original HDF dataset** used in the master project (`DATA_SOURCE = "hdf"`);
2. **Yahoo Finance** OHLC ETF data for a public-data replication (`DATA_SOURCE = "yahoo"`).

Public-data ETF mapping: `RPV` — Value, `SIZE` — Size, `MTUM` — Momentum, `SPHQ` — Quality, `SPLV` — Low Volatility. The passive benchmark is `SPY`.

## Methodology

* **Signal.** Cumulative log-return over the formation window, **skipping** the most recent month (`6−1` = 6-month formation, 1-month skip; `12−1` analogous), evaluated at each **month-end signal date**.
* **Portfolios.** `MomTop1_80_20` (80% in the top factor, 20% split across the rest), `MomTop2_35_35` (35%/35% in the top two, remainder split), and `EW` (equal weight). Weights are set at the rebalance and then **drift** with realized returns until the next rebalance.
* **Timing.** Signal at month-end close → trade at the close `IMPLEMENTATION_LAG` trading days later (default 1, i.e. next day) → new weights earn from the following day. On the trade day the portfolio holds the drifted pre-trade weights; the cost is charged on the first day the new weights are held.
* **Costs.** Daily one-way half-spread proxies (AR/CS) are smoothed with a trailing median and applied to `Σ c·|Δw|` against the **drifted pre-trade weights**. A flat `TC_FIXED_BPS` alternative is available. Spreads are clipped at `TC_SPREAD_CLIP_UPPER` (note: the 10% default is wide and rarely binds for liquid ETFs).
* **Risk-free.** Historical daily simple rate from FRED, lagged one day and forward-filled; risk-adjusted metrics use the realized excess series rather than a fixed zero.
* **Bootstrap.** Politis–Romano stationary bootstrap on the **common-sample** panel; returns, the aligned cost panel and the benchmark are resampled **jointly** (shared indices), and the signal/weights/backtests/metrics are rebuilt inside every replica. The average block length can be chosen by matching the autocorrelation of absolute returns.
* **Paired difference.** Within-replica `strat − bench` distributions and `P(strat > bench)` (higher-is-better convention; for max drawdown "higher" means shallower).
* **Signal-permutation null.** See below.

## Why EW is not a neutral benchmark (and the signal-permutation null)

Equal-weighting the five factor ETFs is **itself an active factor bet**: the equity risk premium is not the equal-weight combination of these risk factors, so EW carries its own static factor exposure. Comparing a concentrated momentum portfolio to EW therefore answers "does the momentum *tilt* beat equal weight?" but **conflates** two distinct things — the skill of the *signal* and the differences in *static factor exposure / concentration* between the two portfolios.

Two additions disentangle them:

* **`SPY` as a passive market benchmark** contextualises whether this tactical 5-ETF allocation beats simply holding the market.
* **A signal-permutation (random-selection) null.** The notebook builds a Monte-Carlo benchmark of strategies that are **structurally identical** to the real one — same 80/20 or 35/35 concentration, same rebalance dates, same costs, same timing — but that pick the held factor(s) **at random** each month. The one-sided p-value is the share of random strategies that match or beat the real strategy on each metric. Because the structure is held fixed and only the *selection rule* differs, any edge in the upper tail is attributable to the **momentum signal**, not to the static exposure of a particular benchmark blend. A small p-value (real strategy in the upper tail of the random distribution) is the clean evidence that the signal adds value.

For the broader specification-search concern (choosing among `6−1`/`12−1`, AR/CS/FIXED, top-1/top-2), the notebook now includes data-snooping-robust procedures — **White's (2000) Reality Check**, **Hansen's (2005) SPA** test and the **Deflated Sharpe Ratio** — over the full grid, on top of the per-specification paired-difference and permutation machinery.

---

## Results — executed run (data vintage 2026-06-04)

> The tables below come from **one full run** on Yahoo data: sample **2013-04-19 → 2026-06-04** (`common_rows = 3302`; strategy window `n = 3144` after the 6-1 warm-up), `VARIANT = "6-1"`, `IMPLEMENTATION_LAG = 1`, primary cost estimator **AR**. **Caveat:** in this run FRED was unreachable and the risk-free fell back to **0**, so the *absolute* Sharpe/Sortino/Martin are overstated by roughly the T-bill level (~1–1.5%/yr over the sample). All *relative* statistics (paired differences, spanning, Ledoit-Wolf) are unaffected because the risk-free cancels. The notebook now falls back to Yahoo `^IRX` before zero; re-running with a working risk-free nudges the absolute risk-adjusted numbers down slightly. Re-run to refresh against the current data vintage.

**Realized net-of-cost metrics (AR estimator), strategy window `n = 3144`:**

| Strategy | CAGR | AnnVol | MxDD | Sharpe | Sortino | Calmar | Martin |
|---|--:|--:|--:|--:|--:|--:|--:|
| MomTop1_80_20 | 0.135 | 0.176 | −0.332 | 0.810 | 1.147 | 0.408 | 2.42 |
| MomTop2_35_35 | 0.118 | 0.165 | −0.371 | 0.762 | 1.063 | 0.319 | 1.88 |
| EW | 0.122 | 0.164 | −0.381 | 0.785 | 1.096 | 0.321 | 1.96 |
| SPY (buy & hold) | 0.141 | 0.172 | −0.337 | 0.853 | 1.203 | 0.417 | 2.13 |

Gross MomTop1: CAGR 0.140, Sharpe 0.831, Martin 2.55. Estimated one-way costs: AR ≈ 16–22 bps, CS ≈ 5–14 bps, FIXED 2 bps — AR/CS are high for liquid ETFs and likely overstate the true spread, yet net conclusions are identical across AR/CS/FIXED. MomTop1 two-way turnover ≈ 5.2×/yr, cost drag ≈ 0.4%/yr; average MomTop1 weights tilt to Momentum (0.35) and Value (0.24), away from Size (0.06).

**Spanning regression (net, Newey-West) — the decisive test:**

| Strategy | α (annualised) | t(α) | p(α) | R² |
|---|--:|--:|--:|--:|
| MomTop1_80_20 | +0.40% | 0.23 | 0.82 | 0.89 |
| MomTop2_35_35 | −0.69% | −0.93 | 0.35 | 0.98 |

MomTop1 loadings: Momentum 0.42, Value 0.20, LowVol 0.15, Quality 0.13, Size −0.08, SPY 0.15. **The alpha is statistically zero** — the returns are explained by a fixed factor combination, so the timing/selection adds nothing beyond static exposure.

**Paired bootstrap differences (net, 1000 replicas):**

| Difference | ΔCAGR | ΔSharpe | ΔMartin | P(Sharpe>0) | P(Martin>0) |
|---|--:|--:|--:|--:|--:|
| MomTop1 − EW | −0.000 | −0.069 | −0.33 | 0.26 | 0.28 |
| MomTop2 − EW | +0.000 | −0.012 | −0.08 | 0.39 | 0.46 |
| MomTop1 − SPY | −0.019 | −0.126 | −0.52 | 0.16 | 0.19 |

`P(strat>bench) < 0.5` everywhere → **no robust risk-adjusted edge over EW**, and a robust **loss to SPY**. The slim realized Sharpe lead of MomTop1 over EW (0.810 vs 0.785) reverses under resampling, i.e. it is within sampling noise. **Ledoit-Wolf** ΔSharpe: vs EW p = 0.83, vs SPY p = 0.72 (neither significant). **PSR**(MomTop1 vs 0) = 0.998 — the strategy *is* reliably profitable in absolute terms (skew −0.18, excess kurtosis ≈ 15.6).

**Signal-permutation null — MomTop1 vs random top-1 of the same structure (1000):**

| Metric | actual | null mean | one-sided p |
|---|--:|--:|--:|
| CAGR | 0.135 | 0.111 | 0.081 |
| Sharpe | 0.810 | 0.692 | 0.093 |
| Calmar | 0.408 | 0.294 | **0.033** |
| Martin | 2.42 | 1.52 | **0.034** |
| MxDD | −0.332 | −0.383 | **0.033** |

The momentum signal **beats random selection**, significantly on the drawdown metrics — the signal is informative, especially for downside control. (MomTop2 vs random top-2: p ≈ 0.30–0.36, not significant — breadth is too small at 2 of 5.)

**Break-even one-way cost (bps):** MomTop1 vs EW = 30 (CAGR) / 16 (Sharpe); MomTop1 vs SPY = 0; MomTop2 = 0 everywhere. The Sharpe edge over EW dies around 16 bps — within the noise of the AR/CS cost estimate.

**Dependence diagnostics & engines:** ARCH-LM and Ljung-Box-on-squares reject at p ≈ 0 for every series (strong volatility clustering; kurtosis ≈ 16). The **FHS** engine, which preserves clustering and fat tails, therefore gives lower, more honest distributions than the stationary bootstrap (MomTop1 Sharpe 0.66 vs 0.79; Martin 1.11 vs 1.66) — confirming the stationary bootstrap was optimistic on tail-sensitive metrics. The MomTop1 − EW paired difference stays ≈ 0 under both **FHS** and the **VAR-sieve**, so the verdict is engine-robust.

**Regimes:** MomTop1 is far stronger in low-volatility regimes (Sharpe 1.34, Martin 4.96) than high-volatility ones (Sharpe 0.63, Martin 1.72), with losing years in 2018 (−1.8%) and 2022 (−5.1%).

**Multiple testing across the 16-spec grid (vs EW):** White Reality Check p = 0.26, Hansen SPA ("consistent") p = 0.26 → the best specification does **not** beat EW once the search is accounted for. The Deflated Sharpe Ratio prints ≈ 0.996 but is **unreliable here**: the 16 specs are near-collinear (trial-Sharpe dispersion ≈ 0.02), which violates its independent-trials assumption and collapses its threshold toward zero — trust the SPA p-value, not the DSR.

### Verdict

The ETF factor-momentum strategy is **profitable in absolute terms** (PSR ≈ 1, net CAGR ≈ 13.5%) and its **signal is genuinely informative** (it beats structurally-identical random selection, significantly on drawdowns). But it is **spanned by static factor exposure** (Newey-West α ≈ 0), it **does not beat equal-weight on a risk-adjusted basis**, it **loses to the market (SPY)** net of costs, and it **does not survive multiple-testing control**. The reconciling mechanism is diversification: the signal picks better-than-random factors, but concentrating into one or two of them sacrifices more diversification than the selection skill recovers — so smart concentration ties a naïve equal-weight blend and trails the market. This is a clean, defensible **theory-to-implementation gap**: the Arnott factor-momentum effect is real, but a long-only 5-ETF implementation does not translate it into tradable alpha.

> **Breadth result (extended run, `USE_EXTENDED_UNIVERSE = True`, 10 single-factor ETFs, same ~2013–2026 window).** Expanding the universe from 5 to 10 distinct single-factor ETFs largely rescues the strategy and re-points the conclusion from *vehicle* to **breadth**. Going 5 → 10: MomTop1 net Sharpe rises 0.73 → **0.87** (now above SPY 0.77 and EW 0.72); the spanning alpha goes from ≈ 0 (t = 0.3) to **+2.7%/yr (t = 1.4, p = 0.16)**; the signal-permutation null flips from marginal (Sharpe p ≈ 0.09) to **strongly significant** (p ≈ 0.002; CAGR/Calmar p ≈ 0.000); the out-of-sample **walk-forward** beats equal-weight (Sharpe 0.88 vs 0.70); the best specification beats equal-weight after **multiple-testing** (Hansen SPA p ≈ **0.044**, vs 0.26 at N = 5); rank/quantile weighting beats equal-weight (0.75 vs 0.72); and on the Fama-French **long-short** factors momentum now beats the equal-weight blend once the window is matched (P ≈ 0.76). **But the win is in return, not robustly in risk-adjusted terms:** the paired bootstrap still gives `P(MomTop1 Sharpe > EW) ≈ 0.28` and `> SPY ≈ 0.18` (the concentrated bet's realised Sharpe lead is within sampling noise), and the spanning alpha is not significant at 5%. The selection adds value mainly by over-weighting the strongest factor (it picks the best factor ≈ 2× more than random, but also the worst more than random — a high-variance, momentum-chasing edge), which is why it beats a random pick yet not a diversified blend on a risk-adjusted basis. **Net read:** the N = 5 failure was largely a *breadth* problem; at ~10 factors the factor-momentum signal is demonstrably skilled and SPA-significant against equal-weight, the edge is on mean return and best harvested with diversified (rank/quantile) weighting rather than 80/20 concentration, and it beats equal-weight but not robustly the market. Caveats: the extended universe is a candidate list (some members are debatable as factors — see the universe-robustness section), the sample is ~13 years, and "beats EW" is benchmark-specific (not "beats SPY"). The long-short section needs network access to Kenneth French's data library (or a CSV via `LONGSHORT_CSV_PATH`).

**Reproduction.** Default configuration (edit the *USER CONFIGURATION* cell):

```python
DATA_SOURCE = "yahoo"      # or "hdf" for the original master-project panel
VARIANT = "6-1"            # or "12-1"
IMPLEMENTATION_LAG = 1     # genuine next-day; 0 reproduces the legacy signal-close timing
USE_HISTORICAL_RF = True;  RF_SOURCE = "DGS3MO"     # falls back to Yahoo ^IRX, then to 0
RUN_BENCHMARK = True;      BENCH_TICKER = "SPY"
RUN_TRANSACTION_COSTS = True
TC_ESTIMATOR = "AR";       TC_ESTIMATORS_TO_COMPARE = ("AR", "CS", "FIXED");  TC_FIXED_BPS = 2.0
RUN_BOOTSTRAP = True;      N_BOOT = 1000;  BOOTSTRAP_SEED = 7
RUN_RANDOM_NULL = True;    N_RANDOM = 1000;  RANDOM_NULL_SEED = 12345
USE_EXTENDED_UNIVERSE = False   # set True to run the whole notebook on the extended ETF universe (breadth test)
```

Record the realized sample window printed by the load cell (`common_start` … `common_end`, `common_rows`) alongside the tables, since it depends on the data vintage.

## How to run

1. Create a virtual environment and install dependencies (`pip install -r requirements.txt`). The notebook needs `numpy`, `pandas`, `matplotlib`, `scipy`, `yfinance` (for `DATA_SOURCE="yahoo"`), `pandas_datareader` (for the FRED risk-free), and `arch` (for the Filtered Historical Simulation engine and the Hansen SPA test). `statsmodels` is optional.
2. Open the notebook: `jupyter notebook Factor_Momentum.ipynb`.
3. Set `DATA_SOURCE` (`"hdf"` or `"yahoo"`), `RF_SOURCE` (`"DGS3MO"` default, `"SOFR"` only from 2018-04-03), and the `RUN_*` flags in the *USER CONFIGURATION* cell. The full run is heavy; for a quick smoke test, switch off the layers you don't need and/or lower `N_BOOT`, `N_RANDOM`, `ENGINE_N_SIMS`, `MT_N_BOOT`.
4. Run all cells; each analysis cell prints the tables described above.

## Repository structure

```text
.
├── Factor_Momentum.ipynb
├── README.md
├── requirements.txt
├── .gitignore
└── LICENSE
```

## Planned extensions

* A **risk-managed momentum overlay** *à la* **Barroso & Santa-Clara (2015)** (volatility-managed momentum).
* A full **extended-universe run** (8–12 distinct single-factor ETFs chosen by an explicit pre-committed rule) — the rank/quantile builders and the `EXTENDED_TICKERS` hook are in place; this only needs the vetted ticker list and a data pull.

## Data sources

* Yahoo Finance (ETF OHLC, `SPY`, `^IRX`) via `yfinance`; FRED (`DGS3MO`) via `pandas_datareader`; **Kenneth French Data Library** (long-short factors `F-F_Research_Data_5_Factors_2x3_daily` + `F-F_Momentum_Factor_daily`) via `pandas_datareader`.

## References

* Arnott, R., Clements, A., Kalesnik, V., & Linnainmaa, J. (2023). *Factor Momentum.* Review of Financial Studies.
* Gupta, T., & Kelly, B. (2019). *Factor Momentum Everywhere.* Journal of Portfolio Management.
* Ehsani, S., & Linnainmaa, J. (2022). *Factor Momentum and the Momentum Factor.* Journal of Finance.
* Politis, D. N., & Romano, J. P. (1994). *The Stationary Bootstrap.* JASA.
* Politis, D. N., & White, H. (2004). *Automatic Block-Length Selection for the Dependent Bootstrap.* Econometric Reviews.
* Glosten, L., Jagannathan, R., & Runkle, D. (1993). *On the Relation between the Expected Value and the Volatility of the Nominal Excess Return on Stocks (GJR-GARCH).* Journal of Finance.
* Corwin, S. A., & Schultz, P. (2012). *A Simple Way to Estimate Bid-Ask Spreads from Daily High and Low Prices.* Journal of Finance.
* Abdi, F., & Ranaldo, A. (2017). *A Simple Estimation of Bid-Ask Spreads from Daily Close, High, and Low Prices.* Review of Financial Studies.
* Barroso, P., & Santa-Clara, P. (2015). *Momentum Has Its Moments.* Journal of Financial Economics.
* Ledoit, O., & Wolf, M. (2008). *Robust Performance Hypothesis Testing with the Sharpe Ratio.* Journal of Empirical Finance.
* Bailey, D. H., & López de Prado, M. (2014). *The Deflated Sharpe Ratio.* Journal of Portfolio Management.
* White, H. (2000). *A Reality Check for Data Snooping.* Econometrica.
* Hansen, P. R. (2005). *A Test for Superior Predictive Ability.* Journal of Business & Economic Statistics.
