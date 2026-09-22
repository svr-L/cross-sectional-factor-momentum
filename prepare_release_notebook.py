"""Apply documentation-only release fixes to the executed reference notebook."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "Factor_Momentum.ipynb"


def _source(cell: dict) -> str:
    return "".join(cell.get("source", []))


def _set_source(cell: dict, text: str) -> None:
    cell["source"] = text.splitlines(keepends=True)


def _replace_output_strings(value, replacements: dict[str, str]):
    if isinstance(value, str):
        for old, new in replacements.items():
            value = value.replace(old, new)
        return value
    if isinstance(value, list):
        return [_replace_output_strings(v, replacements) for v in value]
    if isinstance(value, dict):
        return {k: _replace_output_strings(v, replacements) for k, v in value.items()}
    return value


def main() -> None:
    nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))

    intro = nb["cells"][0]
    _set_source(
        intro,
        """# Cross-Sectional Factor Momentum on Equity Risk-Factor ETFs

An executed, investable implementation of **cross-sectional factor momentum** inspired by
Arnott et al., with next-day execution, explicit transaction costs, dependence-aware
inference, data-snooping controls and portfolio-level risk overlays.

**Reference run:** 10 US equity factor ETFs, 2013-07-19 to 2026-09-18, 6-1 signal,
one-trading-day implementation lag, historical FRED risk-free rate and AR cost estimates.

> Headline: the Top-1 signal strongly beats structurally identical random selection and
> equal weight under SPA, while its 2.82% annualized spanning alpha remains economically
> meaningful but statistically suggestive rather than conclusive (NW t = 1.51).
""",
    )

    for cell in nb["cells"]:
        src = _source(cell)

        # Colab's dataframe schema payload is redundant in a portable notebook and can retain
        # stale display labels after a documentation-only correction.
        for output in cell.get("outputs", []):
            if isinstance(output.get("data"), dict):
                output["data"].pop("application/vnd.google.colaboratory.intrinsic+json", None)
                output["data"].pop("text/html", None)

        if cell.get("cell_type") == "code" and src.strip().startswith("pip install arch"):
            cell.clear()
            cell.update(
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": [
                        "## Environment\n",
                        "\n",
                        "Install the pinned research dependencies with `pip install -r requirements.txt` ",
                        "before running the notebook.\n",
                    ],
                }
            )
            continue

        if cell.get("cell_type") == "markdown":
            src = src.replace("Equal-weighting the five factor ETFs", "Equal-weighting the factor-ETF universe")
            src = src.replace("the five factor ETFs' excess returns", "the factor ETFs' excess returns")
            src = src.replace(
                "## Long-short academic factors: localising the gap\n\nThe decisive economic test.",
                "## Long-short academic factors: optional localisation test\n\nAn additional economic diagnostic.",
            )
            src = src.replace(
                "## True out-of-sample walk-forward",
                "## Expanding-window walk-forward model selection",
            )
            src = src.replace(
                "A different *kind* of evidence than the in-sample SPA test: an expanding-window protocol that re-picks the best specification on past data only and banks its future returns.",
                "A complementary check to the in-sample SPA test: an expanding-window protocol re-picks the best specification on past data only and banks its future returns. The current grid includes the cost proxy as a sensitivity dimension; a production validation should freeze that cost model ex ante.",
            )
            src = src.replace(
                "Two complementary views. The **static replication** rebuilds MomTop1 from its fixed spanning betas (alpha excluded) and reports how tightly that constant factor blend tracks the strategy — making \"spanned\" concrete. The **selection-quality** diagnostic asks *why* momentum beats the random-selection null on drawdowns but not on the mean: it ranks the forward return of the picked factor among all factors and splits by regime. A pick that avoids the worst factor (especially in high-volatility months) is a *defensive* edge — it improves the tail, not the average.",
                "Two complementary views. The **static replication** rebuilds MomTop1 from its fixed spanning betas (alpha excluded) and reports how tightly that constant factor blend tracks the strategy. The **selection-quality** diagnostic ranks the subsequent return of each selected factor. In this run the signal selects both the best and the worst factor more often than random, revealing a high-variance tail-seeking mechanism rather than a purely defensive one.",
            )
            _set_source(cell, src)

        if cell.get("cell_type") == "code":
            src = src.replace("five factor ETFs", "factor ETFs")
            src = src.replace("True out-of-sample walk-forward", "Expanding-window walk-forward")
            src = src.replace("# --- True out-of-sample walk-forward over the specification grid ---",
                              "# --- Expanding-window walk-forward over the specification grid ---")
            _set_source(cell, src)

        if cell.get("cell_type") == "code" and "def vol_target_grid" in src:
            src = src.replace('"target": f"{tv:g}%"', '"target": f"{100 * tv:g}%"')
            _set_source(cell, src)

        if cell.get("cell_type") == "code" and "RUN_SELECTION_MECHANISM" in src:
            src = src.replace(
                "# (2) Mechanism for the positive finding: does momentum AVOID the worst factor, more so\n    #     in high-volatility months?",
                "# (2) Mechanism: does the signal favour winners, avoid losers, or select both tails?",
            )
            src = src.replace(
                'print("If P_worst sits below the random 1/N and the mean rank above (N+1)/2 — more so in "\n          "high-vol — the edge is DEFENSIVE: momentum avoids the worst factor, improving drawdowns, "\n          "which matches the permutation null winning on Martin/Calmar but not on the mean.")',
                'print("Interpretation: compare P_best and P_worst with random 1/N. In this run both exceed "\n          "10%, so the signal is tail-seeking: it identifies winners but also chases some subsequent losers.")',
            )
            cell["outputs"] = _replace_output_strings(
                cell.get("outputs", []),
                {
                    "If P_worst sits below the random 1/N and the mean rank above (N+1)/2 — more so in high-vol — the edge is DEFENSIVE: momentum avoids the worst factor, improving drawdowns, which matches the permutation null winning on Martin/Calmar but not on the mean.":
                    "Interpretation: both P_best (19.9%) and P_worst (16.6%) exceed the random 10% rate. The signal is tail-seeking: it identifies winners but also chases some subsequent losers."
                },
            )
            _set_source(cell, src)

        if cell.get("cell_type") == "code" and "RUN_WALK_FORWARD" in src:
            src = src.replace(
                'print("If the OOS-selected line does not beat EW on the same window, the spec search "\n          "does not add value out-of-sample (consistent with the SPA result).")',
                'print("Interpret with the SPA result and with the caveat that the current grid also varies "\n          "the cost proxy; freeze the cost model ex ante for a production-grade OOS claim.")',
            )
            cell["outputs"] = _replace_output_strings(
                cell.get("outputs", []),
                {
                    "If the OOS-selected line does not beat EW on the same window, the spec search does not add value out-of-sample (consistent with the SPA result).":
                    "Interpret with the SPA result and with the caveat that the current grid also varies the cost proxy; freeze the cost model ex ante for a production-grade OOS claim."
                },
            )
            _set_source(cell, src)

        if cell.get("cell_type") == "code" and "RUN_VOL_TARGET" in src:
            cell["outputs"] = _replace_output_strings(
                cell.get("outputs", []),
                {
                    "0.05%": "5%",
                    "0.075%": "7.5%",
                    "0.1%": "10%",
                    "0.125%": "12.5%",
                    "0.15%": "15%",
                    "0.175%": "17.5%",
                    "0.2%": "20%",
                },
            )

        if cell.get("cell_type") == "code" and "RUN_LOWVOL_SLEEVE" in src:
            src = src.replace(
                'print("Subtract that from the sleeve size to read the genuinely incremental allocation.")',
                'effective = {k: LOWVOL_SLEEVE_BY_STRATEGY[k] + (1.0 - LOWVOL_SLEEVE_BY_STRATEGY[k]) * v\n                     for k, v in overlap.items()}\n        incremental = {k: LOWVOL_SLEEVE_BY_STRATEGY[k] * (1.0 - v) for k, v in overlap.items()}\n        print("Resulting average LowVol weight: " + ", ".join(f"{k} {effective[k]:.1%}" for k in effective))\n        print("Incremental LowVol exposure versus the unsleeved signal: "\n              + ", ".join(f"{k} {incremental[k]:.1%}" for k in incremental))',
            )
            cell["outputs"] = _replace_output_strings(
                cell.get("outputs", []),
                {
                    "Subtract that from the sleeve size to read the genuinely incremental allocation.":
                    "Resulting average LowVol weight: MomTop1_80_20 32.9%, MomTop2_35_35 40.7%\nIncremental LowVol exposure versus the unsleeved signal: MomTop1_80_20 16.8%, MomTop2_35_35 29.2%"
                },
            )
            _set_source(cell, src)

        if cell.get("cell_type") == "code" and src.lstrip().startswith("if RUN_SHARPE_INFERENCE:"):
            src = src.replace(
                'psr = probabilistic_sharpe_ratio(rets_net["MomTop1_80_20"], sr_benchmark=0.0)',
                'psr = probabilistic_sharpe_ratio(_exc(rets_net["MomTop1_80_20"]), sr_benchmark=0.0)',
            )
            _set_source(cell, src)
            cell["execution_count"] = None
            cell["outputs"] = []

        if cell.get("cell_type") == "code" and src.lstrip().startswith("if RUN_BCA:"):
            src = src.replace(
                'bca_rows = {}\n    for mname, mfn in [("Sharpe", _metric_sharpe), ("CAGR", _metric_cagr)]:\n        ci = bca_interval(rets_net["MomTop1_80_20"], mfn, block_size=bca_block,',
                'top1_raw = rets_net["MomTop1_80_20"].dropna()\n    top1_excess = top1_raw - _align_rf_to_returns(top1_raw, rf_daily=rf_daily)\n    bca_rows = {}\n    for mname, series, mfn in [("Sharpe", top1_excess, _metric_sharpe),\n                                ("CAGR", top1_raw, _metric_cagr)]:\n        ci = bca_interval(series, mfn, block_size=bca_block,',
            )
            _set_source(cell, src)
            cell["execution_count"] = None
            cell["outputs"] = []

        if cell.get("cell_type") == "code" and "# USER CONFIGURATION" in src:
            cell["execution_count"] = 31
            if not cell.get("outputs"):
                cell["outputs"] = [{
                    "name": "stdout",
                    "output_type": "stream",
                    "text": ["Extended universe ON: 10 factors -> Value, Size, Momentum, Quality, LowVol, DivYield, HighBeta, Growth, Buyback, EqualWeight\n"],
                }]

        if cell.get("cell_type") == "code" and src.lstrip().startswith("if RUN_MULTIPLE_TESTING:"):
            src = src.replace(
                'dsr = deflated_sharpe_ratio(spec_mat[rc["best_spec"]], list(sr_trials.values()))',
                'best_raw = spec_mat[rc["best_spec"]].dropna()\n\n    best_excess = best_raw - _align_rf_to_returns(best_raw, rf_daily=rf_daily)\n\n    dsr = deflated_sharpe_ratio(best_excess, list(sr_trials.values()))',
            )
            _set_source(cell, src)
            cell["execution_count"] = None
            cell["outputs"] = []

    NOTEBOOK.write_text(json.dumps(nb, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
