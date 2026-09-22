# Changelog

## 2026-09 — extended-universe release

### Research additions

- Activated a pre-committed ten-ETF factor universe and reran the full pipeline through 2026-09-18.
- Added leave-one-out and breadth-gradient robustness.
- Added Newey–West unconditional and volatility-conditional spanning, rolling alpha and a static-replication decomposition.
- Added selection-quality diagnostics based on subsequent cross-sectional factor ranks.
- Added expanding-window walk-forward model selection.
- Added rank, quantile and inverse-volatility portfolio builders.
- Added White Reality Check and Hansen SPA data-snooping controls.
- Added Ledoit–Wolf Sharpe-difference inference, break-even costs and BCa intervals.
- Added FHS AR–GJR–GARCH and VAR-sieve simulation engines.
- Added deterministic volatility targeting and fixed Low-Vol sleeves.

### Implementation corrections

- Enforced genuine next-day execution: signal at month-end, trade at the next close, earn from the following day.
- Restricted resampling to the no-missing common sample.
- Aligned SPY and the historical risk-free rate to the strategy window.
- Added a FRED → Yahoo `^IRX` → zero risk-free fallback chain.
- Corrected Sortino to use target semideviation.
- Clarified one-way and two-way turnover conventions.
- Added numerical guards to FHS simulations.
- Corrected volatility-target display labels.
- Corrected the effective LowVol-sleeve interpretation.
- Corrected the selection-mechanism narrative: the signal selects both cross-sectional tails rather than simply avoiding the worst factor.
- Normalized PSR, BCa-Sharpe and DSR callers to excess returns and cleared the incompatible legacy outputs.

### Documentation

- Replaced the historical change-log-style README with a result-led project page.
- Added machine-readable run results and reproducible README figures.
- Added detailed results and research-design notes.

## Earlier public revision

- Added SPY, signal-permutation nulls, paired stationary-bootstrap differences and AR/CS/fixed cost sensitivities.
- Added long–short academic-factor hooks and CSV fallback.
- Added conditional and subsample diagnostics.
