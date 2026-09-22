"""Build the static figures used by README.md from the frozen run summary."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "run_2026-09-18.json"
ASSETS = ROOT / "assets"

COLORS = {
    "Top-1 80/20": "#146C94",
    "Top-2 35/35": "#19A7CE",
    "Equal weight": "#9AA0A6",
    "SPY": "#333333",
}


def _style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.grid.axis": "y",
            "grid.alpha": 0.22,
            "font.size": 10,
            "axes.titleweight": "semibold",
        }
    )


def performance_overview(data: dict) -> None:
    perf = data["performance"]
    names = list(perf)
    colors = [COLORS[n] for n in names]
    specs = [
        ("CAGR", "Net CAGR", 100.0, "%", False),
        ("Sharpe", "Sharpe ratio", 1.0, "", False),
        ("MaxDD", "Maximum drawdown", 100.0, "%", True),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(12.6, 3.8))
    for ax, (key, title, scale, suffix, use_abs) in zip(axes, specs):
        values = [perf[n][key] * scale for n in names]
        if use_abs:
            values = [abs(v) for v in values]
        bars = ax.bar(range(len(names)), values, color=colors, width=0.68)
        ax.set_title(title)
        ax.set_xticks(range(len(names)), ["Top-1", "Top-2", "EW", "SPY"])
        ax.set_axisbelow(True)
        if key == "MaxDD":
            ax.set_ylabel("Drawdown magnitude")
        for bar, value in zip(bars, values):
            label = f"{value:.1f}{suffix}" if suffix else f"{value:.2f}"
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), label,
                    ha="center", va="bottom", fontsize=9)
        ax.margins(y=0.16)
    fig.suptitle("Latest executed run — net of AR transaction-cost estimates", fontsize=13, fontweight="bold")
    fig.text(0.5, 0.01, "2013-07-19 to 2026-09-18 · 6-1 signal · one-day implementation lag",
             ha="center", color="#555555")
    fig.tight_layout(rect=(0, 0.05, 1, 0.92))
    fig.savefig(ASSETS / "performance_overview.png", dpi=190, bbox_inches="tight")
    plt.close(fig)


def signal_pvalues(data: dict) -> None:
    pvals = data["signal_permutation"]
    metrics = ["CAGR", "Sharpe", "Sortino", "Calmar", "Martin", "MaxDD"]
    x = np.arange(len(metrics))
    width = 0.34
    fig, ax = plt.subplots(figsize=(10.2, 4.4))
    for shift, name, color in [(-width / 2, "Top-1 80/20", COLORS["Top-1 80/20"]),
                               (width / 2, "Top-2 35/35", COLORS["Top-2 35/35"])]:
        values = [max(float(pvals[name][m]), 0.0005) for m in metrics]
        bars = ax.bar(x + shift, values, width, label=name, color=color)
        for bar, raw in zip(bars, [pvals[name][m] for m in metrics]):
            label = "<.001" if raw == 0 else f"{raw:.3f}"
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.002,
                    label, ha="center", va="bottom", fontsize=8, rotation=90)
    ax.axhline(0.05, color="#B3261E", linestyle="--", linewidth=1.2, label="5% threshold")
    ax.set_xticks(x, metrics)
    ax.set_ylim(0, 0.105)
    ax.set_ylabel("One-sided permutation p-value")
    ax.set_title("Momentum selection versus structurally identical random portfolios")
    ax.legend(frameon=False, ncol=3, loc="upper left")
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(ASSETS / "signal_permutation_pvalues.png", dpi=190, bbox_inches="tight")
    plt.close(fig)


def breadth_gradient(data: dict) -> None:
    rows = data["breadth"]
    n = np.array([r["factors"] for r in rows])
    mean = np.array([r["gap_mean"] for r in rows])
    lo = np.array([r["gap_p05"] for r in rows])
    hi = np.array([r["gap_p95"] for r in rows])
    fig, ax = plt.subplots(figsize=(8.8, 4.5))
    ax.fill_between(n, lo, hi, color="#B9E3F5", alpha=0.75, label="5th–95th percentile across subsets")
    ax.plot(n, mean, marker="o", linewidth=2.4, color=COLORS["Top-1 80/20"],
            label="Mean Top-1 minus EW Sharpe")
    ax.axhline(0, color="#555555", linewidth=1)
    ax.set_xticks(n)
    ax.set_xlabel("Number of factor ETFs")
    ax.set_ylabel("Net Sharpe gap")
    ax.set_title("The signal strengthens as the opportunity set broadens")
    ax.legend(frameon=False, loc="upper left")
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(ASSETS / "breadth_gradient.png", dpi=190, bbox_inches="tight")
    plt.close(fig)


def volatility_targeting(data: dict) -> None:
    rows = data["vol_target_top1"]
    achieved = np.array([r["AnnVol"] * 100 for r in rows])
    cagr = np.array([r["CAGR"] * 100 for r in rows])
    drawdown = np.array([abs(r["MaxDD"]) * 100 for r in rows])
    targets = [r["target"] for r in rows]
    gap_spy = np.array([r["sharpe_gap_spy"] for r in rows])
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.1))
    axes[0].plot(achieved, cagr, marker="o", color=COLORS["Top-1 80/20"], linewidth=2.2)
    for x, y, target in zip(achieved, cagr, targets):
        axes[0].annotate(f"{target:g}%", (x, y), xytext=(4, 5), textcoords="offset points", fontsize=8)
    axes[0].set_xlabel("Achieved annualized volatility (%)")
    axes[0].set_ylabel("Net CAGR (%)")
    axes[0].set_title("Return–risk path")
    axes[1].plot(targets, gap_spy, marker="o", color="#7B1FA2", linewidth=2.2)
    axes[1].axhline(0, color="#555555", linewidth=1)
    axes[1].set_xlabel("Volatility target (%)")
    axes[1].set_ylabel("Sharpe gap vs same-target SPY")
    axes[1].set_title("Relative edge fades at high targets")
    for ax in axes:
        ax.set_axisbelow(True)
    fig.suptitle("Deterministic volatility targeting manages the path more than the signal", fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(ASSETS / "volatility_targeting.png", dpi=190, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    _style()
    performance_overview(data)
    signal_pvalues(data)
    breadth_gradient(data)
    volatility_targeting(data)


if __name__ == "__main__":
    main()
