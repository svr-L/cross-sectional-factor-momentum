"""
Core utilities for the ETF Factor Momentum alpha-validation project.

This module contains the reusable implementation used by the notebook:
- data loading and risk-free-rate fallback logic;
- transaction-cost proxies;
- signal construction and portfolio backtesting;
- performance metrics and dependence-aware inference;
- signal-permutation nulls, spanning regressions and specification-search tests.

The module intentionally keeps all research functions in one file so the companion
notebook can remain short and readable.
"""

import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display

try:
    import yfinance as yf
except Exception:
    yf = None

try:
    from pandas_datareader import data as pdr
except Exception:
    pdr = None


# ============================================================
# DATA
# ============================================================

TICKERS = {
    "Value": "RPV",
    "Size": "SIZE",
    "Momentum": "MTUM",
    "Quality": "SPHQ",
    "LowVol": "SPLV",
}
FACTOR_NAMES = ["Value", "Size", "Momentum", "Quality", "LowVol"]


def load_factor_etf_returns_hdf(filepath: str, key: str = "/FactorETFs") -> pd.DataFrame:
    """Load daily factor-ETF returns from an HDF store (5 columns)."""
    r = pd.read_hdf(filepath, key)
    r.index = pd.to_datetime(r.index)
    r.index.name = "Date"
    start = r.dropna().index[0]
    r = r.loc[start:].copy()
    if r.shape[1] == 5:
        r.columns = FACTOR_NAMES
    return r.astype(float)


def download_factor_etf_bundle(start: str = "2000-01-01") -> dict:
    """Download adjusted OHLC for the factor ETF panel via Yahoo Finance."""
    if yf is None:
        raise ImportError("yfinance is not available in this environment.")
    raw = yf.download(list(TICKERS.values()), start=start, auto_adjust=True, progress=False)
    if not isinstance(raw.columns, pd.MultiIndex):
        raise ValueError("Expected a MultiIndex Yahoo Finance download for multiple tickers.")
    close = raw["Close"].rename(columns={v: k for k, v in TICKERS.items()})
    high = raw["High"].rename(columns={v: k for k, v in TICKERS.items()})
    low = raw["Low"].rename(columns={v: k for k, v in TICKERS.items()})
    for obj in (close, high, low):
        obj.index = pd.to_datetime(obj.index)
        obj.index.name = "Date"
        obj.sort_index(inplace=True)
    rets = close.pct_change().dropna(how="all")
    rets.index.name = "Date"
    return {"close": close.astype(float), "high": high.astype(float),
            "low": low.astype(float), "rets": rets.astype(float)}


def download_benchmark_returns(ticker: str = "SPY", start: str = "2000-01-01") -> pd.Series:
    """Daily close-to-close returns of a passive market benchmark (default SPY)."""
    if yf is None:
        raise ImportError("yfinance is not available in this environment.")
    raw = yf.download(ticker, start=start, auto_adjust=True, progress=False)
    close = raw["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    close.index = pd.to_datetime(close.index)
    rets = close.sort_index().pct_change().dropna()
    rets.name = ticker
    return rets.astype(float)


# ============================================================
# HISTORICAL RISK-FREE RATE
# ============================================================

def fetch_fred_series(series_id, start, end) -> pd.Series:
    """Download a daily FRED series and forward-fill missing business-day obs."""
    if pdr is None:
        raise ImportError("pandas_datareader is required for FRED, or set USE_HISTORICAL_RF = False.")
    s = pdr.DataReader(series_id, "fred", start, end)
    if isinstance(s, pd.DataFrame):
        s = s.iloc[:, 0]
    s.index = pd.to_datetime(s.index)
    s = s.astype(float).sort_index().ffill()
    s.name = series_id
    return s


def build_historical_rf_daily(index, rf_source="DGS3MO", day_count=360, lag_days=1) -> pd.Series:
    """Historical daily simple risk-free return series aligned to `index`."""
    idx = pd.DatetimeIndex(index).sort_values().unique()
    if len(idx) == 0:
        return pd.Series(dtype=float, name="rf_daily")
    rf_source = rf_source.upper()
    if rf_source == "SOFR" and idx.min() < pd.Timestamp("2018-04-03"):
        raise ValueError("SOFR starts 2018-04-03. For a full 2013+ sample use RF_SOURCE='DGS3MO'.")
    start = idx.min() - pd.Timedelta(days=10)
    end = idx.max() + pd.Timedelta(days=10)
    y = fetch_fred_series(rf_source, start, end)
    rf_daily = (y / 100.0) / day_count
    rf_daily = rf_daily.shift(lag_days).ffill()
    rf = rf_daily.reindex(idx).ffill().bfill()
    rf.name = "rf_daily"
    return rf.astype(float)


def download_irx_rf_daily(index, day_count=360, lag_days=1) -> pd.Series:
    """Daily simple risk-free from Yahoo `^IRX` (13-week T-bill discount yield, in %).
    Fallback for when FRED is unreachable."""
    if yf is None:
        raise ImportError("yfinance is not available in this environment.")
    idx = pd.DatetimeIndex(index).sort_values().unique()
    start = idx.min() - pd.Timedelta(days=10)
    raw = yf.download("^IRX", start=str(start.date()), auto_adjust=False, progress=False)
    y = raw["Close"]
    if isinstance(y, pd.DataFrame):
        y = y.iloc[:, 0]
    y.index = pd.to_datetime(y.index)
    y = y.astype(float).sort_index().ffill()
    rf_daily = (y / 100.0) / day_count
    rf_daily = rf_daily.shift(lag_days).ffill()
    rf = rf_daily.reindex(idx).ffill().bfill()
    rf.name = "rf_daily"
    return rf.astype(float)


def build_rf_with_fallback(index, rf_source="DGS3MO", day_count=360, lag_days=1, fred_attempts=3):
    """Risk-free cascade: FRED (`rf_source`) -> Yahoo `^IRX` -> zero. Returns (series, label)."""
    import time
    for k in range(1, fred_attempts + 1):
        try:
            rf = build_historical_rf_daily(index, rf_source=rf_source,
                                           day_count=day_count, lag_days=lag_days)
            return rf, f"FRED:{rf_source.upper()}"
        except Exception as e:
            print(f"FRED risk-free attempt {k}/{fred_attempts} failed: {type(e).__name__}")
            time.sleep(1.0)
    try:
        rf = download_irx_rf_daily(index, day_count=day_count, lag_days=lag_days)
        print("FRED unavailable -> using Yahoo ^IRX (13-week T-bill) as the risk-free.")
        return rf, "Yahoo:^IRX"
    except Exception as e:
        print(f"Yahoo ^IRX fallback failed: {type(e).__name__}")
    import warnings as _w
    _w.warn("All risk-free sources failed; falling back to rf_daily = 0.0. "
            "Reported Sharpe/Sortino/Martin will use a zero risk-free rate.")
    rf = pd.Series(0.0, index=pd.DatetimeIndex(index), name="rf_daily")
    return rf, "ZERO"

# ============================================================
# TRANSACTION-COST PROXIES
# ============================================================

def abdi_ranaldo_spread(high, low, close):
    high = pd.Series(high).astype(float)
    low = pd.Series(low).astype(float)
    close = pd.Series(close).astype(float)
    idx = high.dropna().index.intersection(low.dropna().index).intersection(close.dropna().index)
    high, low, close = high.loc[idx].sort_index(), low.loc[idx].sort_index(), close.loc[idx].sort_index()
    log_h, log_l, log_c = np.log(high), np.log(low), np.log(close)
    eta = 0.5 * (log_h + log_l)
    s2 = 4.0 * (log_c.shift(1) - eta.shift(1)) * (log_c.shift(1) - eta)
    spread = np.sqrt(np.maximum(s2, 0.0))
    spread.name = "ar_spread"
    return spread


def abdi_ranaldo_panel(px_high, px_low, px_close, tickers=None, clip_upper=0.10):
    if tickers is None:
        tickers = [c for c in px_high.columns if c in px_low.columns and c in px_close.columns]
    out = {}
    for t in tickers:
        h, l, c = px_high[t].dropna(), px_low[t].dropna(), px_close[t].dropna()
        idx = h.index.intersection(l.index).intersection(c.index)
        if len(idx) < 3:
            out[t] = pd.Series(dtype=float)
            continue
        s = abdi_ranaldo_spread(h.loc[idx], l.loc[idx], c.loc[idx])
        if clip_upper is not None:
            s = s.clip(upper=clip_upper)
        out[t] = s
    return pd.DataFrame(out).sort_index().reindex(columns=tickers)


def corwin_schultz_spread(high, low):
    """
    Corwin-Schultz (2012) FULL proportional spread from daily high/low.

    NOTE: the original paper also describes an *overnight adjustment* that shifts
    the previous day's high/low when the price gaps overnight, to strip the
    overnight drift out of the two-day range (gamma). That adjustment needs OPEN
    prices, which this OHLC bundle does not carry, so it is intentionally omitted.
    For liquid ETFs the bias from skipping it is small relative to the noise of
    the daily estimator, which is smoothed downstream with a trailing median.
    """
    high = pd.Series(high).astype(float)
    low = pd.Series(low).astype(float)
    idx = high.dropna().index.intersection(low.dropna().index)
    high, low = high.loc[idx].sort_index(), low.loc[idx].sort_index()
    hl = np.log(high / low)
    beta = hl.pow(2) + hl.shift(1).pow(2)
    high2 = pd.concat([high, high.shift(1)], axis=1).max(axis=1)
    low2 = pd.concat([low, low.shift(1)], axis=1).min(axis=1)
    gamma = np.log(high2 / low2).pow(2)
    k = 3 - 2 * np.sqrt(2)
    alpha = (np.sqrt(2 * beta) - np.sqrt(beta)) / k - np.sqrt(gamma / k)
    alpha = alpha.clip(lower=0)
    spread = 2 * (np.exp(alpha) - 1) / (1 + np.exp(alpha))
    spread.name = "cs_spread"
    return spread


def corwin_schultz_panel(px_high, px_low, tickers=None, clip_upper=0.10):
    px_high, px_low = px_high.copy(), px_low.copy()
    if tickers is None:
        tickers = [c for c in px_high.columns if c in px_low.columns]
    out = {}
    for t in tickers:
        h, l = px_high[t].dropna(), px_low[t].dropna()
        idx = h.index.intersection(l.index)
        if len(idx) < 3:
            out[t] = pd.Series(dtype=float)
            continue
        s = corwin_schultz_spread(h.loc[idx], l.loc[idx])
        if clip_upper is not None:
            s = s.clip(upper=clip_upper)
        out[t] = s
    return pd.DataFrame(out).sort_index().reindex(columns=tickers)


def spread_panel_to_one_way_cost(spreads):
    return 0.5 * spreads.astype(float)


def constant_one_way_cost_panel(index, columns, one_way_bps):
    """
    Build a flat one-way transaction-cost panel of `one_way_bps` basis points.
    Useful as a sanity check against the noisy OHLC proxies (AR/CS), which tend
    to OVERstate spreads for liquid ETFs.
    """
    val = float(one_way_bps) / 1e4
    return pd.DataFrame(val, index=pd.DatetimeIndex(index), columns=list(columns), dtype=float)


def smooth_daily_cost_panel(cost_daily, lookback_days=21, agg="median"):
    cost_daily = cost_daily.sort_index().astype(float)
    min_obs = min(5, lookback_days)
    if agg == "median":
        return cost_daily.rolling(lookback_days, min_periods=min_obs).median()
    elif agg == "mean":
        return cost_daily.rolling(lookback_days, min_periods=min_obs).mean()
    raise ValueError("agg must be 'median' or 'mean'")


def align_costs_to_signal_dates(cost_daily, signal_dates, lookback_days=21, agg="median"):
    cost_daily = cost_daily.sort_index().astype(float)
    smoothed = smooth_daily_cost_panel(cost_daily, lookback_days=lookback_days, agg=agg)
    return smoothed.reindex(signal_dates)

# ============================================================
# SIGNAL + WEIGHTS
# ============================================================

def month_end_trading_dates(idx):
    s = pd.Series(idx, index=idx)
    eom = s.groupby(s.index.to_period("M")).max()
    return pd.DatetimeIndex(eom.values)


def get_variant_params(variant):
    tdpm = 21
    if variant == "6-1":
        return 6 * tdpm, 1 * tdpm
    elif variant == "12-1":
        return 12 * tdpm, 1 * tdpm
    raise ValueError("variant must be '6-1' or '12-1'")


def cs_mom_signal_monthly(r, formation_days, skip_days):
    sig_daily = np.log1p(r).shift(skip_days).rolling(formation_days, min_periods=formation_days).sum()
    eom_dates = month_end_trading_dates(r.index)
    sig_m = sig_daily.loc[eom_dates].dropna(how="all")
    sig_m.index.name = "Date"
    return sig_m


def w_top1_80_20(sig_m):
    n = sig_m.shape[1]
    rest = 0.2 / (n - 1)
    w = pd.DataFrame(rest, index=sig_m.index, columns=sig_m.columns, dtype=float)
    top = sig_m.idxmax(axis=1)
    for dt, a in top.items():
        w.loc[dt, a] = 0.8
    return w


def w_top2_35_35(sig_m):
    n = sig_m.shape[1]
    rest = 0.3 / (n - 2)
    w = pd.DataFrame(rest, index=sig_m.index, columns=sig_m.columns, dtype=float)
    for dt in sig_m.index:
        top2 = sig_m.loc[dt].nlargest(2).index
        w.loc[dt, top2] = 0.35
    return w


def w_equal(sig_m):
    n = sig_m.shape[1]
    return pd.DataFrame(1.0 / n, index=sig_m.index, columns=sig_m.columns, dtype=float)


# --- random structurally-identical weight builders (for the signal-permutation null) ---

def w_random_top1_80_20(sig_index, columns, rng):
    n = len(columns)
    rest = 0.2 / (n - 1)
    m = len(sig_index)
    arr = np.full((m, n), rest, dtype=float)
    picks = rng.integers(0, n, size=m)
    arr[np.arange(m), picks] = 0.8
    return pd.DataFrame(arr, index=sig_index, columns=list(columns))


def w_random_top2_35_35(sig_index, columns, rng):
    n = len(columns)
    rest = 0.3 / (n - 2)
    m = len(sig_index)
    arr = np.full((m, n), rest, dtype=float)
    for k in range(m):
        picks = rng.choice(n, size=2, replace=False)
        arr[k, picks] = 0.35
    return pd.DataFrame(arr, index=sig_index, columns=list(columns))

# ============================================================
# BACKTEST
# ============================================================

def _entry_dates_from_signal_dates(trading_idx, signal_dates):
    trading_idx = pd.DatetimeIndex(trading_idx).sort_values().unique()
    signal_dates = pd.DatetimeIndex(signal_dates).sort_values().unique()
    entries, keep = [], []
    for dt in signal_dates:
        if dt < trading_idx[0]:
            continue
        pos = trading_idx.searchsorted(dt, side="right")
        if pos < len(trading_idx):
            entries.append(trading_idx[pos])
            keep.append(dt)
    return pd.DatetimeIndex(entries), pd.DatetimeIndex(keep)


def backtest_monthly_rebalance_with_drift(
    r, w_m,
    cost_oneway_daily=None,
    cost_lookback_days=21,
    cost_agg="median",
    charge_initial_trade=True,
    implementation_lag=1,
):
    """
    Monthly rebalance with intra-month drift and optional transaction costs.

    Timing (implementation_lag, in trading days):
      - signal observed at month-end close (signal date S);
      - the trade date is the NEXT trading day E (= first day after S);
      - the NEW target weights start earning returns `implementation_lag` days
        after the trade date.

      implementation_lag = 1 (default) => trade is executed at the close of E and
      the new weights first earn on E+1. On E itself the portfolio still holds the
      drifted PRE-trade weights. This is genuine next-day implementation and removes
      the ~1-day look-ahead present when new weights earn the trade-day return.

      implementation_lag = 0 reproduces the old "execute at the signal-date close"
      convention (new weights earn the E-day close-to-close return).
    """
    r = r.dropna(how="any").copy()
    entries, keep = _entry_dates_from_signal_dates(r.index, w_m.index)

    empty_s = pd.Series(dtype=float, name="portfolio")
    empty_w = pd.DataFrame(columns=r.columns, dtype=float)
    empty_info = pd.DataFrame(columns=["turnover", "tc_rate"], dtype=float)
    if len(entries) == 0:
        return empty_s, empty_s.copy(), empty_w, empty_w.copy(), empty_info

    w_sched = w_m.loc[keep].copy()
    w_sched.index = entries
    w_sched = w_sched[~w_sched.index.duplicated(keep="first")]
    entries = w_sched.index

    cost_sched = None
    if cost_oneway_daily is not None:
        cost_sig = align_costs_to_signal_dates(
            cost_oneway_daily.reindex(r.index), keep,
            lookback_days=cost_lookback_days, agg=cost_agg,
        )
        cost_sched = cost_sig.copy()
        cost_sched.index = entries
        cost_sched = cost_sched.reindex(index=entries, columns=r.columns).astype(float)

    n_days = len(r.index)
    base_pos = np.array([r.index.get_loc(dt) for dt in entries], dtype=int)
    eff_pos = base_pos + int(implementation_lag)

    valid = eff_pos < n_days
    keep_idx = np.where(valid)[0]
    eff_pos = eff_pos[valid]
    entries = entries[valid]
    w_sched = w_sched.iloc[keep_idx]
    if cost_sched is not None:
        cost_sched = cost_sched.iloc[keep_idx]
    if len(eff_pos) == 0:
        return empty_s, empty_s.copy(), empty_w, empty_w.copy(), empty_info

    port_gross = pd.Series(index=r.index, dtype=float, name="gross")
    port_net = pd.Series(index=r.index, dtype=float, name="net")
    w_d = pd.DataFrame(index=r.index, columns=r.columns, dtype=float)
    reb_info = pd.DataFrame(index=entries, columns=["turnover", "tc_rate"], dtype=float)

    current_w_pre = np.zeros(r.shape[1], dtype=float)
    rvals = r.values

    for i, start_pos in enumerate(eff_pos):
        end_pos = eff_pos[i + 1] - 1 if i + 1 < len(eff_pos) else n_days - 1

        target_w = w_sched.iloc[i].astype(float).values
        target_w = target_w / target_w.sum()

        if i == 0 and not charge_initial_trade:
            w_pre = target_w.copy()
        else:
            w_pre = current_w_pre.copy()

        turnover_rate = float(np.sum(np.abs(target_w - w_pre)))
        tc_rate = 0.0
        if cost_sched is not None:
            c_vec = np.nan_to_num(cost_sched.iloc[i].astype(float).values, nan=0.0)
            tc_rate = float(np.sum(c_vec * np.abs(target_w - w_pre)))
        reb_info.iloc[i] = [turnover_rate, tc_rate]

        current_w = target_w.copy()
        for pos in range(start_pos, end_pos + 1):
            x = rvals[pos]
            w_d.iloc[pos] = current_w
            gross_rp = float(np.dot(current_w, x))
            if pos == start_pos and tc_rate > 0:
                net_rp = (1.0 - tc_rate) * (1.0 + gross_rp) - 1.0
            else:
                net_rp = gross_rp
            port_gross.iloc[pos] = gross_rp
            port_net.iloc[pos] = net_rp
            current_w = current_w * (1.0 + x) / (1.0 + gross_rp)
        current_w_pre = current_w.copy()

    mask = port_gross.notna()
    return port_gross.loc[mask], port_net.loc[mask], w_d.loc[mask], w_sched, reb_info


def _turnover_summary_from_rebalance_info(reb_info):
    if reb_info.empty:
        return {k: np.nan for k in [
            "n_rebalances", "mean_turnover_two_way", "median_turnover_two_way",
            "mean_turnover_one_way", "annual_turnover_two_way_approx",
            "mean_tc_rate", "annual_tc_drag_approx", "total_tc_rate"]}
    n_reb = int(len(reb_info))
    mean_to = float(reb_info["turnover"].mean())
    med_to = float(reb_info["turnover"].median())
    mean_tc = float(reb_info["tc_rate"].mean())
    return {
        "n_rebalances": n_reb,
        "mean_turnover_two_way": mean_to,
        "median_turnover_two_way": med_to,
        "mean_turnover_one_way": 0.5 * mean_to,
        "annual_turnover_two_way_approx": 12.0 * mean_to,
        "mean_tc_rate": mean_tc,
        "annual_tc_drag_approx": 12.0 * mean_tc,
        "total_tc_rate": float(reb_info["tc_rate"].sum()),
    }


def run_factor_mom_from_returns(
    r, variant="6-1",
    cost_oneway_daily=None, cost_lookback_days=21, cost_agg="median",
    charge_initial_trade=True, implementation_lag=1,
):
    r_raw = r.copy()
    r = r.dropna(how="any").copy()

    formation_days, skip_days = get_variant_params(variant)
    sig_m = cs_mom_signal_monthly(r, formation_days=formation_days, skip_days=skip_days)

    weight_schemes = {
        "MomTop1_80_20": w_top1_80_20(sig_m),
        "MomTop2_35_35": w_top2_35_35(sig_m),
        "EW": w_equal(sig_m),
    }
    if cost_oneway_daily is not None:
        cost_oneway_daily = cost_oneway_daily.reindex(r.index)

    rets_gross, rets_net = {}, {}
    daily_weights, entry_weights, rebalance_info, turnover_summary = {}, {}, {}, {}

    for name, w_m in weight_schemes.items():
        p_gross, p_net, w_d, w_sched, reb_info = backtest_monthly_rebalance_with_drift(
            r, w_m, cost_oneway_daily=cost_oneway_daily,
            cost_lookback_days=cost_lookback_days, cost_agg=cost_agg,
            charge_initial_trade=charge_initial_trade, implementation_lag=implementation_lag,
        )
        rets_gross[name] = p_gross.rename(name)
        rets_net[name] = p_net.rename(name)
        daily_weights[name] = w_d
        entry_weights[name] = w_sched
        rebalance_info[name] = reb_info
        turnover_summary[name] = _turnover_summary_from_rebalance_info(reb_info)

    rets_gross = pd.concat(rets_gross.values(), axis=1)
    rets_net = pd.concat(rets_net.values(), axis=1)
    avg_daily_weights = pd.concat({k: v.mean() for k, v in daily_weights.items()}, axis=1)
    avg_entry_weights = pd.concat({k: v.mean() for k, v in entry_weights.items()}, axis=1)
    turnover_summary = pd.DataFrame(turnover_summary).T

    sample_info = {
        "raw_start": r_raw.index.min(), "raw_end": r_raw.index.max(),
        "common_start": r.index.min(), "common_end": r.index.max(),
        "raw_rows": int(len(r_raw)), "common_rows": int(len(r)),
    }
    return {
        "rets_gross": rets_gross, "rets_net": rets_net, "signal": sig_m,
        "daily_weights": daily_weights, "entry_weights": entry_weights,
        "avg_daily_weights": avg_daily_weights, "avg_entry_weights": avg_entry_weights,
        "rebalance_info": rebalance_info, "turnover_summary": turnover_summary,
        "sample_info": sample_info,
    }

# ============================================================
# PERFORMANCE METRICS
# ============================================================

def max_drawdown_from_wealth(wealth):
    wealth = wealth.dropna().astype(float)
    if len(wealth) == 0:
        return np.nan
    peak = wealth.cummax()
    return float((wealth / peak - 1.0).min())


def ulcer_index(r):
    r = r.dropna().astype(float)
    if len(r) == 0:
        return np.nan
    wealth = (1.0 + r).cumprod()
    dd = wealth / wealth.cummax() - 1.0
    return float(np.sqrt(np.mean(dd ** 2)))


def cagr(r, ann=252):
    r = r.dropna().astype(float)
    if len(r) == 0:
        return np.nan
    wealth = (1.0 + r).cumprod()
    years = len(r) / ann
    if years <= 0:
        return np.nan
    w_last = wealth.iloc[-1]
    if not np.isfinite(w_last) or w_last <= 0:
        return np.nan
    return float(w_last ** (1 / years) - 1)


def _align_rf_to_returns(r, rf_daily=None):
    idx = r.dropna().index
    if rf_daily is None:
        return pd.Series(0.0, index=idx, name="rf_daily")
    if np.isscalar(rf_daily):
        return pd.Series(float(rf_daily), index=idx, name="rf_daily")
    if isinstance(rf_daily, pd.DataFrame):
        if rf_daily.shape[1] != 1:
            raise ValueError("rf_daily DataFrame must have exactly one column.")
        rf_daily = rf_daily.iloc[:, 0]
    rf = pd.Series(rf_daily).astype(float).sort_index().reindex(idx).ffill().bfill()
    rf.name = "rf_daily"
    return rf


def _annualized_rf_from_series(rf, ann=252):
    rf = pd.Series(rf).dropna().astype(float)
    if len(rf) == 0:
        return 0.0
    gross = (1.0 + rf).prod()
    years = len(rf) / ann
    return float(gross ** (1 / years) - 1.0) if years > 0 else 0.0


def perf_metrics(r, rf_daily=None, ann=252):
    r = r.dropna().astype(float)
    if len(r) < 5:
        return {"n": int(len(r))}
    rf = _align_rf_to_returns(r, rf_daily=rf_daily)
    ex = r.loc[rf.index] - rf

    mu_d = ex.mean()
    vol_d = ex.std(ddof=1)
    shr = (mu_d / vol_d) * np.sqrt(ann) if vol_d > 0 else np.nan

    # Sortino: target semideviation = RMS of downside excess returns (MAR = rf, i.e. 0 excess)
    neg = np.minimum(ex.values, 0.0)
    dvol = float(np.sqrt(np.mean(neg ** 2)))
    sor = (mu_d / dvol) * np.sqrt(ann) if dvol > 0 else np.nan

    cagr_ = cagr(r, ann=ann)
    ann_vol = r.std(ddof=1) * np.sqrt(ann)
    mxdd = max_drawdown_from_wealth((1.0 + r).cumprod())
    calmar = (cagr_ / abs(mxdd)) if (mxdd < 0 and np.isfinite(mxdd)) else np.nan
    ui = ulcer_index(r)
    rf_ann = _annualized_rf_from_series(rf, ann=ann)
    martin = ((cagr_ - rf_ann) / ui) if (ui > 0 and np.isfinite(ui)) else np.nan

    return {
        "n": int(len(r)), "CAGR": float(cagr_), "AnnVol": float(ann_vol),
        "MxDD": float(mxdd), "ShR": float(shr), "SoR": float(sor),
        "Calmar": float(calmar), "Ulcer": float(ui), "Martin": float(martin),
    }


def perf_table(F, rf_daily=None, ann=252):
    return pd.DataFrame({c: perf_metrics(F[c], rf_daily=rf_daily, ann=ann) for c in F.columns}).T


def wealth_index(F):
    return (1.0 + F).cumprod()

# ============================================================
# STATIONARY BOOTSTRAP
# ============================================================

def stationary_bootstrap_indices(T, avg_block_len, rng):
    p = 1.0 / avg_block_len
    idx = np.empty(T, dtype=int)
    idx[0] = rng.integers(0, T)
    for t in range(1, T):
        if rng.random() < p:
            idx[t] = rng.integers(0, T)
        else:
            idx[t] = (idx[t - 1] + 1) % T
    return idx


def stationary_bootstrap_index_stream(T, avg_block_len, n_boot, seed):
    rng = np.random.default_rng(seed)
    for _ in range(n_boot):
        yield stationary_bootstrap_indices(T, avg_block_len, rng)


def summarize_vec(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return pd.Series({"mean": np.nan, "p05": np.nan, "p50": np.nan, "p95": np.nan, "n": 0})
    return pd.Series({
        "mean": float(np.mean(x)), "p05": float(np.quantile(x, 0.05)),
        "p50": float(np.quantile(x, 0.50)), "p95": float(np.quantile(x, 0.95)),
        "n": int(len(x)),
    })


def _metric_tables_from_vectors(mats, metrics, strategies):
    out = {}
    for m in metrics:
        rows = []
        for s in strategies:
            sm = summarize_vec(mats[(m, s)])
            sm["Strategy"] = s
            rows.append(sm)
        out[m] = pd.DataFrame(rows).set_index("Strategy")
    return out


# higher value = better, used for paired probabilities and null p-values
_HIGHER_IS_BETTER = {"CAGR": True, "AnnVol": False, "MxDD": True, "ShR": True,
                     "SoR": True, "Calmar": True, "Ulcer": False, "Martin": True}


def paired_difference_summary(mats, metrics, strat, bench):
    """Bootstrap distribution of (strat - bench), paired within each replica."""
    rows = {}
    for m in metrics:
        a = np.asarray(mats[(m, strat)], float)
        b = np.asarray(mats[(m, bench)], float)
        fin = np.isfinite(a) & np.isfinite(b)
        a, b = a[fin], b[fin]
        if len(a) == 0:
            rows[m] = {"mean_diff": np.nan, "p05": np.nan, "p50": np.nan,
                       "p95": np.nan, "P(strat>bench)": np.nan, "n": 0}
            continue
        d = a - b
        better = (a > b) if _HIGHER_IS_BETTER.get(m, True) else (a < b)
        rows[m] = {
            "mean_diff": float(np.mean(d)), "p05": float(np.quantile(d, 0.05)),
            "p50": float(np.quantile(d, 0.50)), "p95": float(np.quantile(d, 0.95)),
            "P(strat>bench)": float(np.mean(better)), "n": int(len(a)),
        }
    return pd.DataFrame(rows).T


def bootstrap_factor_mom_metrics(
    r, variant="6-1",
    cost_oneway_daily=None, cost_lookback_days=21, cost_agg="median",
    charge_initial_trade=True, implementation_lag=1,
    bench_returns=None, bench_name="SPY",
    metrics=("CAGR", "AnnVol", "ShR", "SoR", "Calmar", "Martin", "MxDD"),
    n_boot=1000, avg_block_len=10.0, seed=1, rf_daily=None, ann=252,
):
    """
    Stationary bootstrap on the COMMON sample (NaN rows dropped before resampling).
    The whole strategy is rebuilt inside every replica. Returns, the aligned cost
    panel and an optional benchmark series are resampled jointly (shared indices).
    """
    r = r.dropna(how="any").copy()                     # <-- common-sample fix
    if cost_oneway_daily is not None:
        cost_oneway_daily = cost_oneway_daily.reindex(r.index)
    if bench_returns is not None:
        bench_returns = pd.Series(bench_returns).reindex(r.index)

    actual = run_factor_mom_from_returns(
        r, variant=variant, cost_oneway_daily=cost_oneway_daily,
        cost_lookback_days=cost_lookback_days, cost_agg=cost_agg,
        charge_initial_trade=charge_initial_trade, implementation_lag=implementation_lag,
    )
    strategies = list(actual["rets_gross"].columns)
    if bench_returns is not None:
        strategies = strategies + [bench_name]

    actual_metrics_gross = perf_table(actual["rets_gross"], rf_daily=rf_daily, ann=ann)
    actual_metrics_net = perf_table(actual["rets_net"], rf_daily=rf_daily, ann=ann)
    strat_window = actual["rets_gross"].index   # post-warm-up window of the strategies
    if bench_returns is not None:
        # align the benchmark to the SAME window as the strategies for a fair head-to-head
        bench_aligned = bench_returns.reindex(strat_window)
        bm = pd.Series(perf_metrics(bench_aligned, rf_daily=rf_daily, ann=ann), name=bench_name)
        actual_metrics_gross = pd.concat([actual_metrics_gross, bm.to_frame().T])
        actual_metrics_net = pd.concat([actual_metrics_net, bm.to_frame().T])

    mats_gross = {(m, s): np.full(n_boot, np.nan) for m in metrics for s in strategies}
    mats_net = {(m, s): np.full(n_boot, np.nan) for m in metrics for s in strategies}

    T = len(r)
    for i, ii in enumerate(stationary_bootstrap_index_stream(T, avg_block_len, n_boot, seed)):
        sim_r = r.iloc[ii].copy(); sim_r.index = r.index
        sim_c = None
        if cost_oneway_daily is not None:
            sim_c = cost_oneway_daily.iloc[ii].copy(); sim_c.index = r.index
        sim_out = run_factor_mom_from_returns(
            sim_r, variant=variant, cost_oneway_daily=sim_c,
            cost_lookback_days=cost_lookback_days, cost_agg=cost_agg,
            charge_initial_trade=charge_initial_trade, implementation_lag=implementation_lag,
        )
        tab_gross = perf_table(sim_out["rets_gross"], rf_daily=rf_daily, ann=ann)
        tab_net = perf_table(sim_out["rets_net"], rf_daily=rf_daily, ann=ann)

        if bench_returns is not None:
            sim_b = bench_returns.iloc[ii].copy(); sim_b.index = r.index
            # restrict the benchmark to the same (post-warm-up) window as the strategies
            mb = perf_metrics(sim_b.reindex(sim_out["rets_gross"].index), rf_daily=rf_daily, ann=ann)

        for m in metrics:
            for s in actual["rets_gross"].columns:
                mats_gross[(m, s)][i] = tab_gross.loc[s, m] if m in tab_gross.columns else np.nan
                mats_net[(m, s)][i] = tab_net.loc[s, m] if m in tab_net.columns else np.nan
            if bench_returns is not None:
                v = mb.get(m, np.nan)
                mats_gross[(m, bench_name)][i] = v
                mats_net[(m, bench_name)][i] = v  # buy-and-hold: gross == net

    return {
        "actual_metrics_gross": actual_metrics_gross,
        "actual_metrics_net": actual_metrics_net,
        "bootstrap_tables_gross": _metric_tables_from_vectors(mats_gross, metrics, strategies),
        "bootstrap_tables_net": _metric_tables_from_vectors(mats_net, metrics, strategies),
        "simulated_metric_vectors_gross": mats_gross,
        "simulated_metric_vectors_net": mats_net,
        "strategies": strategies,
    }

# ============================================================
# RANDOM-SELECTION (SIGNAL-PERMUTATION) NULL
# ============================================================

def random_selection_null(
    r, sig_m, weight_builder,
    cost_oneway_daily=None, cost_lookback_days=21, cost_agg="median",
    charge_initial_trade=True, implementation_lag=1,
    metrics=("CAGR", "ShR", "SoR", "Calmar", "Martin", "MxDD"),
    use_net=True, n_random=1000, seed=12345, rf_daily=None, ann=252,
):
    """
    Build a null of strategies that are STRUCTURALLY IDENTICAL to the real one
    (same rebalance dates, same concentration profile, same costs, same timing)
    but pick the held factor(s) AT RANDOM each month. Any edge of the real
    strategy over this null is attributable to the momentum SIGNAL, not to the
    static factor exposure of a particular benchmark blend.
    """
    r = r.dropna(how="any").copy()
    if cost_oneway_daily is not None:
        cost_oneway_daily = cost_oneway_daily.reindex(r.index)
    rng = np.random.default_rng(seed)
    cols = list(sig_m.columns)
    out = {m: np.full(n_random, np.nan) for m in metrics}
    for j in range(n_random):
        w_rand = weight_builder(sig_m.index, cols, rng)
        p_gross, p_net, *_ = backtest_monthly_rebalance_with_drift(
            r, w_rand, cost_oneway_daily=cost_oneway_daily,
            cost_lookback_days=cost_lookback_days, cost_agg=cost_agg,
            charge_initial_trade=charge_initial_trade, implementation_lag=implementation_lag,
        )
        series = p_net if (use_net and cost_oneway_daily is not None) else p_gross
        mm = perf_metrics(series, rf_daily=rf_daily, ann=ann)
        for m in metrics:
            out[m][j] = mm.get(m, np.nan)
    return out


def null_pvalues(actual_metrics_row, null_dist, metrics):
    rows = {}
    for m in metrics:
        x = np.asarray(null_dist[m], float)
        x = x[np.isfinite(x)]
        a = float(actual_metrics_row[m])
        if len(x) == 0:
            rows[m] = {"actual": a, "null_mean": np.nan, "null_p05": np.nan,
                       "null_p95": np.nan, "pval_one_sided": np.nan, "n": 0}
            continue
        if _HIGHER_IS_BETTER.get(m, True):
            p = float(np.mean(x >= a))   # fraction of random strategies that do at least as well
        else:
            p = float(np.mean(x <= a))
        rows[m] = {
            "actual": a, "null_mean": float(np.mean(x)),
            "null_p05": float(np.quantile(x, 0.05)), "null_p95": float(np.quantile(x, 0.95)),
            "pval_one_sided": p, "n": int(len(x)),
        }
    return pd.DataFrame(rows).T

# ============================================================
# ACF BLOCK-LENGTH HEURISTIC
# ============================================================

def _acf(x, nlags):
    x = np.asarray(x, float)
    x = x - np.mean(x)
    denom = np.dot(x, x)
    if denom <= 0:
        return np.zeros(nlags + 1)
    out = np.empty(nlags + 1, float)
    out[0] = 1.0
    for k in range(1, nlags + 1):
        out[k] = np.dot(x[:-k], x[k:]) / denom
    return out


def choose_block_length_by_acf_matching(
    s, candidates=(5, 10, 20, 30), nlags=20, n_boot=300,
    use_abs=True, seed=1, distance="weighted",
):
    r = s.dropna().astype(float)
    x = np.abs(r.values) if use_abs else r.values
    target = _acf(x, nlags)
    rng = np.random.default_rng(seed)
    scores, boot_means = {}, {}
    for L in candidates:
        acfs = np.zeros((n_boot, nlags + 1))
        for b in range(n_boot):
            ii = stationary_bootstrap_indices(len(x), float(L), rng)
            acfs[b] = _acf(x[ii], nlags)
        m = acfs.mean(axis=0)
        boot_means[L] = m
        diff = m[1:] - target[1:]
        if distance == "l1":
            score = float(np.mean(np.abs(diff)))
        elif distance == "l2":
            score = float(np.sqrt(np.mean(diff ** 2)))
        elif distance == "weighted":
            w = 1.0 / np.arange(1, nlags + 1)
            score = float(np.sqrt(np.mean(diff ** 2 * w)))
        else:
            raise ValueError("distance must be 'l1', 'l2', or 'weighted'")
        scores[L] = score
    scores = pd.Series(scores).sort_index()
    return {"best_L": int(scores.idxmin()), "scores": scores,
            "target_acf": target, "boot_acf_mean": boot_means}

# ============================================================
# ALTERNATIVE WEIGHTING (risk-based: inverse-volatility)
# ============================================================

def _trailing_vol_at_signals(r, sig_index, lookback=63):
    """Daily stdev over a trailing window, sampled at the signal dates."""
    vol = r.rolling(lookback, min_periods=max(20, lookback // 3)).std()
    return vol.reindex(sig_index).bfill()


def w_topk_inverse_vol(sig_m, r, k=1, lookback=63):
    """
    Select the top-k factors by momentum and weight them by INVERSE VOLATILITY
    (equal-risk proxy), with zero in the rest. Removes the arbitrary 80/20 (or
    35/35) concentration so that *selection* is separated from *concentration*.
    """
    vol = _trailing_vol_at_signals(r, sig_m.index, lookback=lookback)
    arr = np.zeros((len(sig_m.index), sig_m.shape[1]), dtype=float)
    cols = list(sig_m.columns)
    for j, dt in enumerate(sig_m.index):
        top = sig_m.loc[dt].nlargest(k).index
        iv = 1.0 / vol.loc[dt, top].replace(0.0, np.nan)
        iv = iv / iv.sum()
        for name, wv in iv.items():
            arr[j, cols.index(name)] = float(wv)
    w = pd.DataFrame(arr, index=sig_m.index, columns=cols)
    return w.div(w.sum(axis=1), axis=0)


def w_inverse_vol_all(sig_m, r, lookback=63):
    """Inverse-volatility across ALL factors: a more neutral (risk-parity-like)
    benchmark than equal weight, which ignores the very different factor vols."""
    vol = _trailing_vol_at_signals(r, sig_m.index, lookback=lookback)
    iv = 1.0 / vol.reindex(sig_m.index)
    w = iv.div(iv.sum(axis=1), axis=0)
    return w.reindex(columns=sig_m.columns).fillna(0.0)


def run_named_strategy(r, weight_matrix, cost_oneway_daily=None, cost_lookback_days=21,
                       cost_agg="median", charge_initial_trade=True, implementation_lag=1):
    """Backtest a single arbitrary monthly weight matrix; returns (gross, net) series."""
    g, n, _, _, _ = backtest_monthly_rebalance_with_drift(
        r, weight_matrix, cost_oneway_daily=cost_oneway_daily,
        cost_lookback_days=cost_lookback_days, cost_agg=cost_agg,
        charge_initial_trade=charge_initial_trade, implementation_lag=implementation_lag)
    return g, n


# ============================================================
# SERIAL-DEPENDENCE DIAGNOSTICS (Ljung-Box, ARCH-LM)
# ============================================================

def ljung_box(x, lags=10):
    from scipy import stats
    x = np.asarray(pd.Series(x).dropna(), float)
    x = x - x.mean()
    T = len(x)
    denom = np.dot(x, x)
    Q = 0.0
    for k in range(1, lags + 1):
        rho = np.dot(x[:-k], x[k:]) / denom
        Q += rho * rho / (T - k)
    Q *= T * (T + 2)
    p = float(stats.chi2.sf(Q, lags))
    return {"stat": float(Q), "lags": int(lags), "pval": p}


def arch_lm(x, lags=10):
    """Engle's ARCH-LM test for conditional heteroskedasticity."""
    from scipy import stats
    e = np.asarray(pd.Series(x).dropna(), float)
    e = e - e.mean()
    e2 = e ** 2
    T = len(e2)
    Y = e2[lags:]
    X = np.column_stack([np.ones(T - lags)] + [e2[lags - j: T - j] for j in range(1, lags + 1)])
    b, *_ = np.linalg.lstsq(X, Y, rcond=None)
    resid = Y - X @ b
    ss_tot = np.sum((Y - Y.mean()) ** 2)
    r2 = 1.0 - np.sum(resid ** 2) / ss_tot if ss_tot > 0 else 0.0
    lm = (T - lags) * r2
    p = float(stats.chi2.sf(lm, lags))
    return {"stat": float(lm), "lags": int(lags), "pval": p}


def dependence_diagnostics(series_dict, lags=10):
    """Table of Ljung-Box (levels & squares) and ARCH-LM p-values per series."""
    rows = {}
    for name, s in series_dict.items():
        s = pd.Series(s).dropna()
        lb = ljung_box(s, lags)
        lb2 = ljung_box(s ** 2, lags)
        al = arch_lm(s, lags)
        rows[name] = {
            "LB_levels_stat": lb["stat"], "LB_levels_p": lb["pval"],
            "LB_squares_stat": lb2["stat"], "LB_squares_p": lb2["pval"],
            "ARCH_LM_stat": al["stat"], "ARCH_LM_p": al["pval"], "lags": lags,
        }
    return pd.DataFrame(rows).T


# ============================================================
# SPANNING REGRESSION (OLS + Newey-West HAC)
# ============================================================

def newey_west_ols(y, X, lags=None):
    y = np.asarray(y, float)
    X = np.asarray(X, float)
    T, k = X.shape
    XtX = X.T @ X
    XtX_inv = np.linalg.inv(XtX)
    b = XtX_inv @ (X.T @ y)
    e = y - X @ b
    if lags is None:
        lags = int(np.floor(4 * (T / 100.0) ** (2.0 / 9.0)))
    Xe = X * e[:, None]
    S = Xe.T @ Xe
    for l in range(1, lags + 1):
        w = 1.0 - l / (lags + 1.0)
        G = Xe[l:].T @ Xe[:-l]
        S += w * (G + G.T)
    cov = XtX_inv @ S @ XtX_inv
    se = np.sqrt(np.diag(cov))
    tstat = b / se
    ss_res = float(e @ e)
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan
    return {"beta": b, "se": se, "t": tstat, "r2": r2, "lags": lags, "n": T, "cov": cov}


def spanning_regression(strat_returns, factor_returns, rf_daily=None,
                        extra_returns=None, lags=None, ann=252):
    """
    Regress the strategy's EXCESS return on the factor ETFs' excess returns (and any
    extra benchmark, e.g. SPY). A Newey-West alpha that is statistically zero means
    the strategy is 'spanned' by static factor exposure -- the timing/selection adds
    nothing beyond a fixed combination of the factors.
    """
    from scipy import stats
    s = pd.Series(strat_returns).dropna()
    F = pd.DataFrame(factor_returns).reindex(s.index)
    if extra_returns is not None:
        extra = pd.DataFrame(extra_returns)
        if isinstance(extra_returns, pd.Series):
            extra = extra_returns.to_frame()
        F = pd.concat([F, extra.reindex(s.index)], axis=1)
    idx = s.index.intersection(F.dropna().index)
    s, F = s.loc[idx], F.loc[idx]
    rf = _align_rf_to_returns(s, rf_daily=rf_daily)
    y = (s - rf).values
    Xf = (F.sub(rf, axis=0)).values
    X = np.column_stack([np.ones(len(y)), Xf])
    res = newey_west_ols(y, X, lags=lags)
    names = ["alpha"] + list(F.columns)
    coefs = pd.DataFrame({"coef": res["beta"], "se": res["se"], "t": res["t"]}, index=names)
    coefs["pval"] = 2 * stats.norm.sf(np.abs(coefs["t"]))
    out = {
        "alpha_daily": float(res["beta"][0]),
        "alpha_annual": float(res["beta"][0] * ann),
        "alpha_t": float(res["t"][0]),
        "alpha_p": float(coefs.loc["alpha", "pval"]),
        "r2": float(res["r2"]), "n": int(res["n"]), "nw_lags": int(res["lags"]),
        "coefficients": coefs,
    }
    return out


# ============================================================
# SHARPE-RATIO INFERENCE (Ledoit-Wolf 2008; PSR / Deflated Sharpe)
# ============================================================

def _bartlett_lrv(Y, bw):
    T = Y.shape[0]
    Yc = Y - Y.mean(axis=0, keepdims=True)
    Omega = (Yc.T @ Yc) / T
    for l in range(1, bw + 1):
        w = 1.0 - l / (bw + 1.0)
        G = (Yc[l:].T @ Yc[:-l]) / T
        Omega += w * (G + G.T)
    return Omega


def _andrews_bw_bartlett(Y):
    """Andrews (1991) automatic bandwidth for the Bartlett kernel via AR(1) plug-in."""
    T = Y.shape[0]
    num = 0.0
    den = 0.0
    for j in range(Y.shape[1]):
        x = Y[:, j] - Y[:, j].mean()
        x0, x1 = x[:-1], x[1:]
        rho = float(np.dot(x0, x1) / np.dot(x0, x0)) if np.dot(x0, x0) > 0 else 0.0
        rho = np.clip(rho, -0.97, 0.97)
        s2 = np.var(x, ddof=0)
        num += 4 * rho ** 2 * s2 ** 2 / ((1 - rho) ** 6 * (1 + rho) ** 2)
        den += s2 ** 2 / (1 - rho) ** 4
    alpha1 = num / den if den > 0 else 0.0
    bw = 1.1447 * (alpha1 * T) ** (1.0 / 3.0)
    return max(1, int(np.ceil(bw)))


def _sharpe_diff_and_se(r1, r2, bw=None):
    r1 = np.asarray(r1, float); r2 = np.asarray(r2, float)
    mu1, mu2 = r1.mean(), r2.mean()
    g1, g2 = (r1 ** 2).mean(), (r2 ** 2).mean()
    v1, v2 = g1 - mu1 ** 2, g2 - mu2 ** 2
    sr1, sr2 = mu1 / np.sqrt(v1), mu2 / np.sqrt(v2)
    delta = sr1 - sr2
    grad = np.array([
        g1 / v1 ** 1.5,
        -g2 / v2 ** 1.5,
        -0.5 * mu1 / v1 ** 1.5,
        0.5 * mu2 / v2 ** 1.5,
    ])
    Y = np.column_stack([r1, r2, r1 ** 2, r2 ** 2])
    if bw is None:
        bw = _andrews_bw_bartlett(Y)
    Omega = _bartlett_lrv(Y, bw)
    var_delta = float(grad @ Omega @ grad) / len(r1)
    se = np.sqrt(var_delta) if var_delta > 0 else np.nan
    return delta, se, bw


def circular_block_indices(T, block_size, rng):
    block_size = max(1, int(block_size))
    n_blocks = int(np.ceil(T / block_size))
    starts = rng.integers(0, T, size=n_blocks)
    idx = np.concatenate([(np.arange(s, s + block_size) % T) for s in starts])[:T]
    return idx


def sharpe_diff_test(r1, r2, block_size=None, n_boot=999, seed=0, ann=252):
    """
    Ledoit-Wolf (2008) test for the difference of two Sharpe ratios under non-iid
    returns: HAC standard error (Bartlett kernel, Andrews bandwidth) + studentized
    circular-block bootstrap p-value. Pass returns in the SAME units (e.g. both
    excess). Two-sided H0: SR1 == SR2.
    """
    s1 = pd.Series(r1).dropna()
    s2 = pd.Series(r2).dropna()
    idx = s1.index.intersection(s2.index)
    a = s1.loc[idx].values; b = s2.loc[idx].values
    T = len(a)
    delta, se, bw = _sharpe_diff_and_se(a, b)
    stat = delta / se if (se and np.isfinite(se)) else np.nan
    if block_size is None:
        block_size = max(1, bw)
    rng = np.random.default_rng(seed)
    count = 0
    valid = 0
    for _ in range(n_boot):
        ii = circular_block_indices(T, block_size, rng)
        db, seb, _ = _sharpe_diff_and_se(a[ii], b[ii], bw=bw)
        if seb and np.isfinite(seb):
            valid += 1
            if abs((db - delta) / seb) >= abs(stat):
                count += 1
    pval = (count + 1) / (valid + 1) if valid > 0 else np.nan
    return {
        "sharpe1_ann": float(a.mean() / a.std(ddof=0) * np.sqrt(ann)),
        "sharpe2_ann": float(b.mean() / b.std(ddof=0) * np.sqrt(ann)),
        "delta_daily": float(delta), "delta_ann": float(delta * np.sqrt(ann)),
        "se_daily": float(se), "tstat": float(stat), "pval": float(pval),
        "block_size": int(block_size), "hac_bw": int(bw), "n": int(T), "n_boot": int(valid),
    }


def probabilistic_sharpe_ratio(returns, sr_benchmark=0.0, ann=252):
    """PSR: probability the true (non-annualised) Sharpe exceeds a benchmark,
    accounting for skewness and kurtosis of the returns (Bailey & Lopez de Prado)."""
    from scipy import stats
    r = np.asarray(pd.Series(returns).dropna(), float)
    T = len(r)
    mu, sd = r.mean(), r.std(ddof=1)
    sr = mu / sd
    g3 = stats.skew(r, bias=False)
    g4 = stats.kurtosis(r, fisher=False, bias=False)  # non-excess kurtosis
    denom = np.sqrt(1 - g3 * sr + (g4 - 1) / 4.0 * sr ** 2)
    z = (sr - sr_benchmark) * np.sqrt(T - 1) / denom
    return {"sharpe_per_obs": float(sr), "sharpe_ann": float(sr * np.sqrt(ann)),
            "skew": float(g3), "kurtosis": float(g4),
            "psr": float(stats.norm.cdf(z)), "T": int(T)}


def deflated_sharpe_ratio(returns, sr_trials, ann=252):
    """
    Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014): PSR evaluated against the
    Sharpe expected from the BEST of N independent trials, where N and the dispersion
    of trial Sharpes come from the specification search. `sr_trials` = per-observation
    Sharpe ratios of all specifications tried.
    """
    from scipy import stats
    sr_trials = np.asarray([s for s in sr_trials if np.isfinite(s)], float)
    N = len(sr_trials)
    var_sr = np.var(sr_trials, ddof=1) if N > 1 else 0.0
    gamma = 0.5772156649
    e1 = stats.norm.ppf(1 - 1.0 / N) if N > 1 else 0.0
    e2 = stats.norm.ppf(1 - 1.0 / (N * np.e)) if N > 1 else 0.0
    sr0 = np.sqrt(var_sr) * ((1 - gamma) * e1 + gamma * e2)
    psr = probabilistic_sharpe_ratio(returns, sr_benchmark=sr0, ann=ann)
    return {"n_trials": int(N), "sr0_threshold_per_obs": float(sr0),
            "sr0_threshold_ann": float(sr0 * np.sqrt(ann)),
            "dsr": float(psr["psr"]), "sharpe_ann": float(psr["sharpe_ann"]),
            "trial_sharpe_std_per_obs": float(np.sqrt(var_sr))}


# ============================================================
# BREAK-EVEN TRANSACTION COST
# ============================================================

def _sharpe_ann(series, rf_daily=None, ann=252):
    s = pd.Series(series).dropna()
    rf = _align_rf_to_returns(s, rf_daily=rf_daily)
    ex = (s - rf)
    sd = ex.std(ddof=1)
    return float(ex.mean() / sd * np.sqrt(ann)) if sd > 0 else np.nan


def breakeven_cost_bps(r, variant="6-1", strat="MomTop1_80_20", mode="cagr_vs_ew",
                       bench_returns=None, rf_daily=None, ann=252, c_max_bps=100.0,
                       implementation_lag=1, cost_lookback_days=21, cost_agg="median",
                       charge_initial_trade=True):
    """
    One-way cost (bps) that drives the strategy's edge to zero. Modes:
      'cagr_vs_ew'      : CAGR(strat) - CAGR(EW), both charged the same flat cost
      'sharpe_vs_ew'    : Sharpe(strat) - Sharpe(EW), same flat cost on both
      'cagr_vs_spy'     : CAGR(strat at cost) - CAGR(SPY buy&hold)
      'excess_cagr_rf'  : CAGR(strat at cost) - annualised risk-free
    """
    from scipy.optimize import brentq
    r_common = r.dropna(how="any")
    cols = list(r_common.columns)

    def run_at(c_bps):
        cp = constant_one_way_cost_panel(r_common.index, cols, c_bps) if c_bps > 0 else None
        return run_factor_mom_from_returns(
            r, variant=variant, cost_oneway_daily=cp, cost_lookback_days=cost_lookback_days,
            cost_agg=cost_agg, charge_initial_trade=charge_initial_trade,
            implementation_lag=implementation_lag)

    def g(c_bps):
        out = run_at(c_bps)
        s = out["rets_net"][strat]
        if mode == "cagr_vs_ew":
            return cagr(s, ann) - cagr(out["rets_net"]["EW"], ann)
        if mode == "sharpe_vs_ew":
            return _sharpe_ann(s, rf_daily, ann) - _sharpe_ann(out["rets_net"]["EW"], rf_daily, ann)
        if mode == "cagr_vs_spy":
            if bench_returns is None:
                raise ValueError("bench_returns required for cagr_vs_spy")
            bench = pd.Series(bench_returns).reindex(s.index).dropna()
            return cagr(s.reindex(bench.index), ann) - cagr(bench, ann)
        if mode == "excess_cagr_rf":
            rf = _align_rf_to_returns(s, rf_daily=rf_daily)
            return cagr(s, ann) - _annualized_rf_from_series(rf, ann)
        raise ValueError("unknown mode")

    g0 = g(0.0)
    if not np.isfinite(g0) or g0 <= 0:
        return {"breakeven_bps": 0.0, "edge_at_zero": float(g0), "mode": mode,
                "note": "no positive edge even at zero cost"}
    gmax = g(c_max_bps)
    if gmax > 0:
        return {"breakeven_bps": float("inf"), "edge_at_zero": float(g0),
                "edge_at_cmax": float(gmax), "c_max_bps": c_max_bps, "mode": mode,
                "note": f"edge survives beyond {c_max_bps} bps one-way"}
    c_star = brentq(g, 0.0, c_max_bps, xtol=1e-3)
    return {"breakeven_bps": float(c_star), "edge_at_zero": float(g0), "mode": mode}


# ============================================================
# AUTOMATIC BLOCK LENGTH (Politis-White 2004 / PPW 2009)
# ============================================================

def optimal_block_length_ppw(series):
    """Patton-Politis-White optimal block length (via the `arch` implementation)."""
    from arch.bootstrap import optimal_block_length
    s = pd.Series(series).dropna()
    ob = optimal_block_length(s.values)
    if isinstance(ob, pd.DataFrame):
        row = ob.iloc[0]
        return {"stationary": float(row.get("stationary", np.nan)),
                "circular": float(row.get("circular", np.nan))}
    return {"stationary": float(ob[0]), "circular": float(ob[1])}


# ============================================================
# BCa INTERVALS (P&L circular-block bootstrap + block jackknife)
# ============================================================

def _metric_sharpe(series, ann=252):
    s = np.asarray(series, float)
    sd = s.std(ddof=1)
    return float(s.mean() / sd * np.sqrt(ann)) if sd > 0 else np.nan


def _metric_cagr(series, ann=252):
    return cagr(pd.Series(series), ann=ann)


def block_bootstrap_pnl_dist(series, metric_fn, block_size, n_boot=1000, seed=0):
    s = np.asarray(pd.Series(series).dropna(), float)
    T = len(s)
    rng = np.random.default_rng(seed)
    out = np.empty(n_boot)
    for b in range(n_boot):
        ii = circular_block_indices(T, block_size, rng)
        out[b] = metric_fn(s[ii])
    return out


def _block_jackknife_values(series, metric_fn, block_size):
    s = np.asarray(pd.Series(series).dropna(), float)
    T = len(s)
    nb = int(np.ceil(T / block_size))
    vals = []
    for k in range(nb):
        lo, hi = k * block_size, min((k + 1) * block_size, T)
        keep = np.concatenate([s[:lo], s[hi:]])
        if len(keep) > 5:
            vals.append(metric_fn(keep))
    return np.asarray(vals, float)


def bca_interval(series, metric_fn, block_size, n_boot=1000, alpha=0.05, seed=0):
    """BCa confidence interval for a return-series functional, using a circular-block
    P&L bootstrap and a delete-block jackknife (note: this resamples the realised P&L,
    distinct from the strategy-rebuild bootstrap)."""
    from scipy import stats
    theta = metric_fn(np.asarray(pd.Series(series).dropna(), float))
    boot = block_bootstrap_pnl_dist(series, metric_fn, block_size, n_boot=n_boot, seed=seed)
    boot = boot[np.isfinite(boot)]
    jack = _block_jackknife_values(series, metric_fn, block_size)
    z0 = stats.norm.ppf(np.mean(boot < theta)) if 0 < np.mean(boot < theta) < 1 else 0.0
    jbar = jack.mean()
    num = np.sum((jbar - jack) ** 3)
    den = 6.0 * (np.sum((jbar - jack) ** 2) ** 1.5)
    a = num / den if den != 0 else 0.0
    zl, zu = stats.norm.ppf(alpha / 2), stats.norm.ppf(1 - alpha / 2)
    def adj(z):
        return stats.norm.cdf(z0 + (z0 + z) / (1 - a * (z0 + z)))
    lo, hi = adj(zl), adj(zu)
    return {"theta": float(theta),
            "lo": float(np.quantile(boot, lo)), "hi": float(np.quantile(boot, hi)),
            "alpha": alpha, "z0": float(z0), "acceleration": float(a),
            "block_size": int(block_size), "n_boot": int(len(boot))}

# ============================================================
# REGIME / SUBSAMPLE STABILITY
# ============================================================

def metrics_by_calendar_year(series, rf_daily=None, ann=252):
    s = pd.Series(series).dropna()
    rows = {}
    for y, grp in s.groupby(s.index.year):
        if len(grp) >= 20:
            rf = None if rf_daily is None else pd.Series(rf_daily).reindex(grp.index)
            rows[int(y)] = perf_metrics(grp, rf_daily=rf, ann=ann)
    return pd.DataFrame(rows).T


def metrics_two_halves(series, rf_daily=None, ann=252):
    s = pd.Series(series).dropna()
    mid = len(s) // 2
    out = {}
    for label, sub in [("first_half", s.iloc[:mid]), ("second_half", s.iloc[mid:])]:
        rf = None if rf_daily is None else pd.Series(rf_daily).reindex(sub.index)
        out[label] = perf_metrics(sub, rf_daily=rf, ann=ann)
    return pd.DataFrame(out).T


def metrics_by_vol_regime(series, market_returns, lookback=21, n_regimes=2,
                          rf_daily=None, ann=252):
    """Split performance by the trailing realised volatility of the market series
    (terciles/halves). No extra data needed beyond the benchmark."""
    s = pd.Series(series).dropna()
    mkt = pd.Series(market_returns).reindex(s.index)
    rv = mkt.rolling(lookback, min_periods=lookback // 2).std()
    labels = (["low", "high"] if n_regimes == 2 else ["low", "mid", "high"])
    q = pd.qcut(rv.reindex(s.index), n_regimes, labels=labels)
    out = {}
    for lab in labels:
        sub = s[q == lab]
        if len(sub) >= 20:
            rf = None if rf_daily is None else pd.Series(rf_daily).reindex(sub.index)
            out[f"{lab}_vol"] = perf_metrics(sub, rf_daily=rf, ann=ann)
    return pd.DataFrame(out).T


# ============================================================
# SOPHISTICATED BOOTSTRAP ENGINES (FHS AR-GJR-GARCH; VAR-sieve)
# ============================================================

def _fit_argjr_garch(series, ar_lags=1):
    """Fit AR(p)-GJR-GARCH(1,1) (Gaussian QMLE) on a single return series.
    Returns mean/vol params, standardized residuals and the unconditional variance.
    Internals work in PERCENT for numerical stability."""
    from arch.univariate import arch_model
    y = pd.Series(series).dropna().astype(float) * 100.0
    mean = "AR" if ar_lags and ar_lags > 0 else "Constant"
    am = arch_model(y, mean=mean, lags=ar_lags if ar_lags else 0,
                    vol="GARCH", p=1, o=1, q=1, dist="normal", rescale=False)
    res = am.fit(disp="off", show_warning=False)
    p = res.params
    const = float(p.get("Const", 0.0))
    phi = np.array([float(p.get(f"y[{j}]", p.get(f"{y.name}[{j}]", 0.0)))
                    for j in range(1, (ar_lags or 0) + 1)], dtype=float)
    omega = float(p["omega"]); alpha = float(p["alpha[1]"])
    gamma = float(p.get("gamma[1]", 0.0)); beta = float(p["beta[1]"])
    z = res.std_resid.dropna().values
    persist = alpha + beta + 0.5 * gamma
    uncond_var = omega / (1 - persist) if 0 < persist < 1 else float(np.var(res.resid.dropna()))
    return {"const": const, "phi": phi, "omega": omega, "alpha": alpha,
            "gamma": gamma, "beta": beta, "z": z, "uncond_var": uncond_var,
            "p": int(ar_lags or 0)}


def _reinflate_argjr(fit, z_path, burnin=300):
    """Re-inflate one series from a path of standardized residuals via the AR-GJR
    recursion. z_path length must be >= T_target + burnin; returns last T_target
    simple returns (de-scaled from percent)."""
    const, phi = fit["const"], fit["phi"]
    omega, alpha, gamma, beta = fit["omega"], fit["alpha"], fit["gamma"], fit["beta"]
    p = fit["p"]
    n = len(z_path)
    h = np.empty(n); eps = np.empty(n); y = np.empty(n)
    h0 = max(fit["uncond_var"], 1e-12)
    h_cap = 1e4 * h0          # cap conditional variance to stop explosive runaway -> inf/nan
    mu0 = const / (1 - phi.sum()) if (p and abs(1 - phi.sum()) > 1e-6) else const
    prev_y = np.full(max(p, 1), mu0)
    eps_prev = 0.0; h_prev = h0
    for t in range(n):
        h[t] = omega + (alpha + (gamma if eps_prev < 0 else 0.0)) * eps_prev ** 2 + beta * h_prev
        if not np.isfinite(h[t]) or h[t] > h_cap:
            h[t] = h_cap
        eps[t] = np.sqrt(max(h[t], 1e-16)) * z_path[t]
        mu = const + (np.dot(phi, prev_y[:p][::-1]) if p else 0.0)
        y[t] = mu + eps[t]
        if p:
            prev_y = np.concatenate([prev_y[1:], [y[t]]])
        eps_prev, h_prev = eps[t], h[t]
    # sanitize then clip simulated simple returns to [-99%, +100%]: the AR-GJR recursion with
    # fat-tailed residuals (and near-unit estimated persistence) can occasionally draw an extreme
    # day that would make (1+r) <= 0 (breaking log1p/CAGR) or overflow cumprod. Non-binding on
    # real ETF data; only trims pathological simulated draws.
    out = np.nan_to_num(y[burnin:] / 100.0, nan=0.0, posinf=1.0, neginf=-0.99)
    return np.clip(out, -0.99, 1.0)


def fhs_simulate_panel(R, ar_lags=1, resid_block=None, n_sims=500, seed=1, burnin=300):
    """
    Filtered Historical Simulation for a panel. Each column is filtered with its own
    AR(p)-GJR-GARCH(1,1); the matrix of standardized residuals is resampled BY ROW
    (preserving contemporaneous cross-sectional correlation) and re-inflated through
    each column's recursion. `resid_block`=None -> iid rows; int -> circular blocks.
    Yields simulated panels (same shape/columns as R).
    """
    R = R.dropna(how="any")
    cols = list(R.columns)
    T = len(R)
    fits = {c: _fit_argjr_garch(R[c], ar_lags=ar_lags) for c in cols}
    Z = np.column_stack([fits[c]["z"][-(min(len(fits[c]["z"]) for c in cols)):] for c in cols])
    nZ = Z.shape[0]
    rng = np.random.default_rng(seed)
    need = T + burnin
    for _ in range(n_sims):
        if resid_block is None:
            ridx = rng.integers(0, nZ, size=need)
        else:
            ridx = circular_block_indices(nZ, resid_block, rng)
            while len(ridx) < need:
                ridx = np.concatenate([ridx, circular_block_indices(nZ, resid_block, rng)])
            ridx = ridx[:need]
        sim = {c: _reinflate_argjr(fits[c], Z[ridx, j], burnin=burnin)
               for j, c in enumerate(cols)}
        yield pd.DataFrame(sim, index=R.index, columns=cols)


def _fit_var(R, p=1):
    Y = R.values
    T, k = Y.shape
    Xrows = []
    for t in range(p, T):
        lagvec = np.concatenate([Y[t - j] for j in range(1, p + 1)])
        Xrows.append(np.concatenate([[1.0], lagvec]))
    X = np.array(Xrows)
    Yt = Y[p:]
    B, *_ = np.linalg.lstsq(X, Yt, rcond=None)   # ( (1+kp) x k )
    resid = Yt - X @ B
    return {"B": B, "resid": resid, "p": p, "k": k, "Y0": Y[:p].copy(), "index": R.index, "cols": list(R.columns)}


def _var_spectral_radius(B, p, k):
    A = [B[1 + j * k: 1 + (j + 1) * k, :].T for j in range(p)]   # each k x k
    top = np.hstack(A)
    if p == 1:
        comp = top
    else:
        comp = np.vstack([top, np.hstack([np.eye(k * (p - 1)), np.zeros((k * (p - 1), k))])])
    return float(np.max(np.abs(np.linalg.eigvals(comp))))


def var_sieve_simulate_panel(R, p=1, n_sims=500, seed=1):
    """VAR(p) sieve with a recursive-design WILD bootstrap (Rademacher), robust to
    conditional heteroskedasticity; preserves contemporaneous cross-sectional
    correlation (whole residual rows are sign-flipped together)."""
    R = R.dropna(how="any")
    fit = _fit_var(R, p=p)
    B, resid, k, cols = fit["B"], fit["resid"], fit["k"], fit["cols"]
    radius = _var_spectral_radius(B, p, k)
    if radius >= 1.0:
        scale = 0.99 / radius
        for j in range(p):
            B[1 + j * k: 1 + (j + 1) * k, :] *= scale
    T = len(R); nE = resid.shape[0]
    rng = np.random.default_rng(seed)
    for _ in range(n_sims):
        w = rng.choice([-1.0, 1.0], size=nE)
        estar = resid * w[:, None]
        Y = np.empty((T, k))
        Y[:p] = fit["Y0"]
        for t in range(p, T):
            lagvec = np.concatenate([Y[t - j] for j in range(1, p + 1)])
            x = np.concatenate([[1.0], lagvec])
            Y[t] = x @ B + estar[t - p]
        yield pd.DataFrame(Y, index=R.index, columns=cols)


def bootstrap_metrics_via_engine(
    r_factors, engine="fhs", variant="6-1", bench_returns=None, bench_name="SPY",
    flat_cost_oneway_bps=None, ar_lags=1, var_lags=1, resid_block=None,
    metrics=("CAGR", "AnnVol", "ShR", "SoR", "Calmar", "Martin", "MxDD"),
    n_sims=500, seed=1, rf_daily=None, ann=252, implementation_lag=1,
    cost_lookback_days=21, cost_agg="median", charge_initial_trade=True):
    """
    Dependence-aware bootstrap that GENERATES new panels with a chosen engine
    ('fhs' or 'var_sieve'), rebuilding the whole strategy inside each replica.
    Returns / benchmark are simulated jointly. Because simulated panels carry no
    OHLC, costs use a flat one-way bps panel (`flat_cost_oneway_bps`), or gross if None.
    Output mirrors bootstrap_factor_mom_metrics so paired_difference_summary applies.
    """
    rf = r_factors.dropna(how="any")
    cols = list(rf.columns)
    if bench_returns is not None:
        b = pd.Series(bench_returns).reindex(rf.index)
        R = pd.concat([rf, b.rename(bench_name)], axis=1).dropna(how="any")
    else:
        R = rf.copy()
    fac_cols = cols
    strategies = ["MomTop1_80_20", "MomTop2_35_35", "EW"] + ([bench_name] if bench_returns is not None else [])

    if engine == "fhs":
        gen = fhs_simulate_panel(R, ar_lags=ar_lags, resid_block=resid_block, n_sims=n_sims, seed=seed)
    elif engine == "var_sieve":
        gen = var_sieve_simulate_panel(R, p=var_lags, n_sims=n_sims, seed=seed)
    else:
        raise ValueError("engine must be 'fhs' or 'var_sieve'")

    mats_net = {(m, s): np.full(n_sims, np.nan) for m in metrics for s in strategies}
    for i, sim_full in enumerate(gen):
        sim_fac = sim_full[fac_cols]
        cp = (constant_one_way_cost_panel(sim_fac.index, fac_cols, flat_cost_oneway_bps)
              if flat_cost_oneway_bps else None)
        sim_out = run_factor_mom_from_returns(
            sim_fac, variant=variant, cost_oneway_daily=cp,
            cost_lookback_days=cost_lookback_days, cost_agg=cost_agg,
            charge_initial_trade=charge_initial_trade, implementation_lag=implementation_lag)
        tab = perf_table(sim_out["rets_net"], rf_daily=rf_daily, ann=ann)
        if bench_returns is not None:
            mb = perf_metrics(sim_full[bench_name], rf_daily=rf_daily, ann=ann)
        for m in metrics:
            for s in ["MomTop1_80_20", "MomTop2_35_35", "EW"]:
                mats_net[(m, s)][i] = tab.loc[s, m] if m in tab.columns else np.nan
            if bench_returns is not None:
                mats_net[(m, bench_name)][i] = mb.get(m, np.nan)
    return {
        "engine": engine,
        "bootstrap_tables_net": _metric_tables_from_vectors(mats_net, metrics, strategies),
        "simulated_metric_vectors_net": mats_net,
        "strategies": strategies, "n_sims": int(n_sims),
    }


# ============================================================
# MULTIPLE TESTING UNDER SPECIFICATION SEARCH
# ============================================================

def build_spec_return_matrix(r, variants=("6-1", "12-1"),
                             concentrations=("top1", "top2"),
                             cost_panels=None, rf_daily=None, implementation_lag=1,
                             cost_lookback_days=21, cost_agg="median",
                             charge_initial_trade=True, ann=252):
    """
    Net daily returns for every specification in the grid
    (variant x concentration x cost-estimator). Returns (matrix, sharpe_trials)
    where columns are 'variant|conc|cost' and sharpe_trials are the per-observation
    Sharpe ratios of each spec (input to the Deflated Sharpe Ratio).
    """
    if cost_panels is None:
        cost_panels = {"GROSS": None}
    conc_col = {"top1": "MomTop1_80_20", "top2": "MomTop2_35_35"}
    cols = {}
    sharpe_trials = {}
    for v in variants:
        for cname, cpanel in cost_panels.items():
            out = run_factor_mom_from_returns(
                r, variant=v, cost_oneway_daily=cpanel, cost_lookback_days=cost_lookback_days,
                cost_agg=cost_agg, charge_initial_trade=charge_initial_trade,
                implementation_lag=implementation_lag)
            for conc in concentrations:
                key = f"{v}|{conc}|{cname}"
                s = out["rets_net"][conc_col[conc]]
                cols[key] = s
                rf = _align_rf_to_returns(s, rf_daily=rf_daily)
                ex = (s - rf)
                sd = ex.std(ddof=1)
                sharpe_trials[key] = float(ex.mean() / sd) if sd > 0 else np.nan
    mat = pd.concat(cols, axis=1)
    mat.columns = list(cols.keys())
    return mat, sharpe_trials


def reality_check_white(spec_matrix, bench_returns, block_size=10, n_boot=1000, seed=0):
    """
    White's (2000) Reality Check. H0: the best specification does not outperform the
    benchmark once the full search is accounted for. Works on excess-over-benchmark
    daily returns; circular-block bootstrap, recentred max statistic.
    """
    M = pd.DataFrame(spec_matrix)
    b = pd.Series(bench_returns).reindex(M.index)
    idx = M.dropna().index.intersection(b.dropna().index)
    D = M.loc[idx].sub(b.loc[idx], axis=0).values
    T, K = D.shape
    fbar = D.mean(axis=0)
    V = np.sqrt(T) * np.max(fbar)
    rng = np.random.default_rng(seed)
    Vstar = np.empty(n_boot)
    for bnum in range(n_boot):
        ii = circular_block_indices(T, block_size, rng)
        fstar = D[ii].mean(axis=0)
        Vstar[bnum] = np.sqrt(T) * np.max(fstar - fbar)
    p = float((np.sum(Vstar >= V) + 1) / (n_boot + 1))
    best = M.columns[int(np.argmax(fbar))]
    return {"pvalue": p, "stat": float(V), "best_spec": best,
            "mean_excess_ann": pd.Series(fbar * 252, index=M.columns).sort_values(ascending=False),
            "block_size": int(block_size), "n_boot": int(n_boot), "n": int(T), "K": int(K)}


def spa_test_hansen(spec_matrix, bench_returns, block_size=10, reps=1000, seed=0):
    """
    Hansen's (2005) Superior Predictive Ability test via the `arch` implementation.
    Returns lower / consistent / upper p-values (consistent is recommended; the
    upper bound is the conservative White-Reality-Check-style configuration).
    Operates on losses = -returns, benchmark = the EW (or chosen) series.
    """
    from arch.bootstrap import SPA
    M = pd.DataFrame(spec_matrix)
    b = pd.Series(bench_returns).reindex(M.index)
    idx = M.dropna().index.intersection(b.dropna().index)
    losses_models = (-M.loc[idx]).values
    losses_bench = (-b.loc[idx]).values
    spa = SPA(losses_bench, losses_models, block_size=block_size, reps=reps,
              bootstrap="circular", seed=seed)
    spa.compute()
    pv = spa.pvalues
    return {"pvalues": {k: float(pv[k]) for k in pv.index},
            "block_size": int(block_size), "reps": int(reps), "n": int(len(idx)),
            "K": int(M.shape[1])}

# ============================================================
# EXTENSIONS 2: long-short factors, walk-forward, quantile/rank weights, conditional spanning, static replication, selection mechanism
# ============================================================

def download_famafrench_factors(start="2000-01-01"):
    """Daily LONG-SHORT academic factor returns from Kenneth French's data library via
    pandas_datareader: Size=SMB, Value=HML, Quality=RMW, Investment=CMA, Momentum=Mom.
    Returns (factor_rets [decimal], rf_daily [decimal], mkt_excess [decimal]).
    Requires network access to French's library (mba.tuck.dartmouth.edu)."""
    from pandas_datareader import data as _pdr
    ff5 = _pdr.DataReader("F-F_Research_Data_5_Factors_2x3_daily", "famafrench", start=start)[0]
    mom = _pdr.DataReader("F-F_Momentum_Factor_daily", "famafrench", start=start)[0]
    ff5 = ff5.copy(); ff5.columns = [c.strip() for c in ff5.columns]
    mom = mom.copy(); mom.columns = [c.strip() for c in mom.columns]
    mom_col = [c for c in mom.columns if c.lower().startswith("mom")][0]
    df = ff5.join(mom, how="inner") / 100.0
    df.index = pd.to_datetime(df.index)
    rets = pd.DataFrame({"Size": df["SMB"], "Value": df["HML"], "Quality": df["RMW"],
                         "Investment": df["CMA"], "Momentum": df[mom_col]}).dropna()
    return rets, df["RF"].reindex(rets.index).rename("rf_daily"), df["Mkt-RF"].reindex(rets.index).rename("Mkt-RF")


def load_factor_returns_csv(path, rf_col=None, mkt_col=None):
    """Fallback loader: a CSV of daily factor returns (decimal) indexed by date."""
    df = pd.read_csv(path, index_col=0, parse_dates=True).sort_index()
    rf = df.pop(rf_col).rename("rf_daily") if (rf_col and rf_col in df.columns) else None
    mkt = df.pop(mkt_col).rename("Mkt-RF") if (mkt_col and mkt_col in df.columns) else None
    return df.astype(float), rf, mkt


def backtest_returns_panel_monthly(rets, w_m, implementation_lag=1, cost_oneway_bps=0.0):
    """Monthly-rebalanced portfolio on a RETURN panel (e.g. long-short factor returns):
    FIXED weights within each month (no price drift, which is the right convention for
    zero-investment factor returns), next-day implementation via `implementation_lag`,
    optional flat one-way cost charged additively on |Delta w| at each rebalance."""
    rets = rets.dropna(how="any").copy()
    entries, keep = _entry_dates_from_signal_dates(rets.index, w_m.index)
    if len(entries) == 0:
        return pd.Series(dtype=float, name="port")
    w_sched = w_m.loc[keep].copy(); w_sched.index = entries
    w_sched = w_sched[~w_sched.index.duplicated(keep="first")]; entries = w_sched.index
    n_days = len(rets.index)
    base = np.array([rets.index.get_loc(dt) for dt in entries], dtype=int)
    eff = base + int(implementation_lag)
    valid = eff < n_days
    eff = eff[valid]; w_sched = w_sched.iloc[np.where(valid)[0]]
    if len(eff) == 0:
        return pd.Series(dtype=float, name="port")
    port = pd.Series(index=rets.index, dtype=float, name="port")
    R = rets.values
    c = float(cost_oneway_bps) / 1e4
    prev_w = np.zeros(rets.shape[1])
    for i, s in enumerate(eff):
        e = eff[i + 1] - 1 if i + 1 < len(eff) else n_days - 1
        w = w_sched.iloc[i].astype(float).values
        cost = c * float(np.sum(np.abs(w - prev_w))) if c > 0 else 0.0
        for pos in range(s, e + 1):
            rp = float(np.dot(w, R[pos]))
            if pos == s and cost > 0:
                rp -= cost
            port.iloc[pos] = rp
        prev_w = w
    return port.loc[port.notna()]


def w_quantile_long(sig_m, top_frac=0.4):
    """Long-only, equal-weight the TOP fraction of factors by momentum (rank/quantile
    portfolio). For a large universe this is the natural construction; for N=5 with
    top_frac=0.4 it holds the top 2. Separates selection from fixed 80/20 concentration."""
    n = sig_m.shape[1]; k = max(1, int(round(top_frac * n)))
    cols = list(sig_m.columns); arr = np.zeros((len(sig_m), n))
    for j, dt in enumerate(sig_m.index):
        for c in sig_m.loc[dt].nlargest(k).index:
            arr[j, cols.index(c)] = 1.0 / k
    return pd.DataFrame(arr, index=sig_m.index, columns=cols)


def w_rank_proportional(sig_m):
    """Long-only weights proportional to the cross-sectional momentum RANK (1..N)."""
    r = sig_m.rank(axis=1, method="average")
    return r.div(r.sum(axis=1), axis=0)


def run_factor_mom_on_panel(rets, variant="6-1", implementation_lag=1, cost_oneway_bps=0.0,
                            weighting="concentrated"):
    """Cross-sectional factor momentum on a generic return panel (used for the long-short
    academic factors). Returns {'rets': DataFrame of strategy returns, 'signal': sig_m}."""
    rets = rets.dropna(how="any").copy()
    fd, sd = get_variant_params(variant)
    sig = cs_mom_signal_monthly(rets, fd, sd)
    if weighting == "concentrated":
        schemes = {"MomTop1": w_top1_80_20(sig), "MomTop2": w_top2_35_35(sig), "EW": w_equal(sig)}
    elif weighting == "quantile":
        schemes = {"MomQ_top40": w_quantile_long(sig, 0.4), "MomRank": w_rank_proportional(sig),
                   "EW": w_equal(sig)}
    else:
        raise ValueError("weighting must be 'concentrated' or 'quantile'")
    out = {k: backtest_returns_panel_monthly(rets, w, implementation_lag, cost_oneway_bps).rename(k)
           for k, w in schemes.items()}
    return {"rets": pd.concat(out.values(), axis=1), "signal": sig}


def walk_forward_select(spec_matrix, min_train_days=504, reselect_every_days=63,
                        rf_daily=None, ann=252):
    """True out-of-sample walk-forward: expanding window, re-pick the best specification by
    in-sample Sharpe every `reselect_every_days`, then bank that spec's OOS returns. The
    spec returns are causal, so selecting on the past and banking the future is valid. This
    answers the spec-search-overfit worry DIRECTLY (not just via the SPA p-value)."""
    M = pd.DataFrame(spec_matrix).dropna(how="any")
    idx = M.index; T = len(idx)
    oos = pd.Series(index=idx, dtype=float, name="OOS_selected")
    chosen = []
    t = int(min_train_days)
    while t < T:
        train = M.iloc[:t]
        rf = _align_rf_to_returns(train.iloc[:, 0], rf_daily=rf_daily).reindex(train.index)
        sh = {}
        for col in M.columns:
            ex = train[col] - rf
            sd = ex.std(ddof=1)
            sh[col] = float(ex.mean() / sd) if sd > 0 else -np.inf
        best = max(sh, key=sh.get)
        end = min(t + int(reselect_every_days), T)
        oos.iloc[t:end] = M[best].iloc[t:end].values
        chosen.append({"date": idx[t], "spec": best, "is_sharpe_ann": sh[best] * np.sqrt(ann)})
        t = end
    oos = oos.dropna()
    return {"oos_returns": oos, "chosen": pd.DataFrame(chosen).set_index("date"),
            "oos_metrics": perf_metrics(oos, rf_daily=rf_daily, ann=ann),
            "n_reselections": len(chosen)}


def vol_regime_dummy(market_returns, index, lookback=21, q=0.5):
    """1 = high-volatility day, by trailing realised vol of `market_returns` above its
    q-quantile; aligned to `index`."""
    m = pd.Series(market_returns)
    rv = m.rolling(lookback, min_periods=max(2, lookback // 2)).std()
    thr = rv.quantile(q)
    d = (rv > thr).astype(float).reindex(pd.DatetimeIndex(index)).ffill().bfill()
    return d.rename("high_vol")


def spanning_regression_conditional(strat, factors, regime, rf_daily=None, extra=None,
                                    lags=None, ann=252):
    """Conditional spanning: two alphas (low- and high-regime) via full interaction of the
    constant and factor loadings with a regime dummy, Newey-West HAC. Tests whether the
    zero full-sample alpha hides a non-zero alpha within a regime."""
    from scipy import stats
    s = pd.Series(strat).dropna()
    F = pd.DataFrame(factors).reindex(s.index)
    if extra is not None:
        ex = extra.to_frame() if isinstance(extra, pd.Series) else pd.DataFrame(extra)
        F = pd.concat([F, ex.reindex(s.index)], axis=1)
    D = pd.Series(regime).reindex(s.index).astype(float)
    idx = s.index.intersection(F.dropna().index).intersection(D.dropna().index)
    s, F, D = s.loc[idx], F.loc[idx], D.loc[idx]
    rf = _align_rf_to_returns(s, rf_daily=rf_daily)
    y = (s - rf).values
    Fx = F.sub(rf, axis=0).values
    Dv = D.values
    X = np.column_stack([np.ones(len(y)), Dv, Fx, Fx * Dv[:, None]])
    res = newey_west_ols(y, X, lags=lags)
    b, cov = res["beta"], res["cov"]
    a_low = b[0]; se_low = np.sqrt(cov[0, 0])
    a_high = b[0] + b[1]; se_high = np.sqrt(cov[0, 0] + cov[1, 1] + 2 * cov[0, 1])
    def _row(a, se):
        tt = a / se if se > 0 else np.nan
        return {"alpha_ann": float(a * ann), "t": float(tt), "p": float(2 * stats.norm.sf(abs(tt)))}
    return {"low_regime": _row(a_low, se_low), "high_regime": _row(a_high, se_high),
            "delta_high_minus_low": {"alpha_ann": float(b[1] * ann),
                                     "t": float(b[1] / np.sqrt(cov[1, 1]) if cov[1, 1] > 0 else np.nan)},
            "n": int(res["n"]), "nw_lags": int(res["lags"]),
            "n_high": int(D.sum()), "n_low": int((1 - D).sum())}


def rolling_spanning_alpha(strat, factors, rf_daily=None, window=504, extra=None, ann=252):
    """Rolling annualised OLS alpha of the strategy vs the factors (+ extra). Lets you SEE
    whether the alpha drifts / concentrates in episodes rather than being a single number."""
    s = pd.Series(strat).dropna()
    F = pd.DataFrame(factors).reindex(s.index)
    if extra is not None:
        ex = extra.to_frame() if isinstance(extra, pd.Series) else pd.DataFrame(extra)
        F = pd.concat([F, ex.reindex(s.index)], axis=1)
    idx = s.index.intersection(F.dropna().index)
    s, F = s.loc[idx], F.loc[idx]
    rf = _align_rf_to_returns(s, rf_daily=rf_daily)
    y = (s - rf).values
    X = np.column_stack([np.ones(len(y)), F.sub(rf, axis=0).values])
    out = {}
    for i in range(window, len(y) + 1):
        yy = y[i - window:i]; XX = X[i - window:i]
        bb, *_ = np.linalg.lstsq(XX, yy, rcond=None)
        out[idx[i - 1]] = float(bb[0] * ann)
    return pd.Series(out, name="rolling_alpha_ann")


def static_replication(strat, factors, rf_daily=None, extra=None, ann=252):
    """Show the strategy is a FIXED factor blend: fit the spanning betas, rebuild the static
    beta-weighted factor portfolio (alpha excluded) and report how well it tracks the
    strategy, plus the implied long-only weights for display."""
    sp = spanning_regression(strat, factors, rf_daily=rf_daily, extra_returns=extra)
    betas = sp["coefficients"]["coef"].drop("alpha")
    s = pd.Series(strat).dropna()
    F = pd.DataFrame(factors).reindex(s.index)
    if extra is not None:
        ex = extra.to_frame() if isinstance(extra, pd.Series) else pd.DataFrame(extra)
        F = pd.concat([F, ex.reindex(s.index)], axis=1)
    idx = s.index.intersection(F.dropna().index)
    s, F = s.loc[idx], F.loc[idx]
    rf = _align_rf_to_returns(s, rf_daily=rf_daily)
    Fx = F.sub(rf, axis=0)
    fitted = Fx[betas.index].mul(betas, axis=1).sum(axis=1)
    actual_ex = (s - rf).reindex(fitted.index)
    corr = float(np.corrcoef(fitted.values, actual_ex.values)[0, 1])
    wlong = betas.clip(lower=0)
    wlong = (wlong / wlong.sum()) if wlong.sum() > 0 else wlong
    return {"betas": betas, "implied_long_weights": wlong, "corr_static_vs_actual": corr,
            "r2": float(sp["r2"]), "alpha_ann": float(sp["alpha_annual"]),
            "static_sharpe_ann": _sharpe_ann(fitted, rf_daily=0.0, ann=ann),
            "actual_sharpe_ann": _sharpe_ann(actual_ex, rf_daily=0.0, ann=ann)}


def selection_quality_by_regime(sig_m, factor_rets, regime=None, k=1):
    """Mechanism for the positive finding: for each month, rank the forward holding-period
    return of the momentum-PICKED factor(s) among all factors (1=worst..N=best) and record
    whether the pick was the worst/best. Aggregated overall and by regime, vs the random
    benchmark. If momentum AVOIDS the worst factor (esp. in high-vol months), that explains
    why it beats the random null on drawdowns but not on the mean."""
    rets = factor_rets.dropna(how="any")
    entries, keep = _entry_dates_from_signal_dates(rets.index, sig_m.index)
    N = rets.shape[1]
    rows = []
    for i in range(len(entries)):
        e0 = rets.index.get_loc(entries[i])
        e1 = rets.index.get_loc(entries[i + 1]) if i + 1 < len(entries) else len(rets.index)
        if e1 <= e0:
            continue
        cum = (1 + rets.iloc[e0:e1]).prod() - 1
        ranks = cum.rank()  # 1=worst .. N=best
        pick = sig_m.loc[keep[i]].nlargest(k).index
        reg = np.nan if regime is None else float(pd.Series(regime).reindex([entries[i]]).ffill().iloc[0])
        rows.append({"date": entries[i], "pick_rank": float(ranks[pick].mean()),
                     "picked_worst": bool(cum.idxmin() in pick), "picked_best": bool(cum.idxmax() in pick),
                     "regime": reg})
    df = pd.DataFrame(rows)
    def _agg(d):
        return {"mean_rank": float(d["pick_rank"].mean()), "P_worst": float(d["picked_worst"].mean()),
                "P_best": float(d["picked_best"].mean()), "months": int(len(d))}
    summary = {"overall": _agg(df)}
    summary["overall"].update({"random_mean_rank": (N + 1) / 2, "random_P_worst": 1.0 / N})
    if regime is not None and df["regime"].notna().any():
        for lab, val in [("low_vol", 0.0), ("high_vol", 1.0)]:
            sub = df[df["regime"] == val]
            if len(sub):
                summary[lab] = _agg(sub)
    return {"per_month": df, "summary": pd.DataFrame(summary).T}
