"""
parameter_sweep.py
--------------------
Sweeps the strategy's two key parameters -- imbalance_ratio (how strict
the absorption filter is) and hold_candles (how long each trade is held)
-- across a grid, backtests each combination on the same tick data, and
reports which regions are robust vs. which look good only by chance.

This matters more than any single backtest number: a strategy whose
Sharpe collapses if imbalance_ratio moves from 3.0 to 3.2 is almost
certainly overfit to that one value. A strategy that stays reasonable
across a neighborhood of parameters is more likely to hold up
out-of-sample.

Uses the SAME simulated tick data for every cell in the grid (one
simulate_ticks() call, reused) so differences across cells come from the
parameters, not from re-randomized data.
"""

import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from data_simulator import simulate_ticks
from footprint_builder import build_footprint_candles
from absorption_detector import detect_absorption_events
from backtest import backtest_absorption_strategy, compute_performance_metrics


def run_sweep(
    ticks: pd.DataFrame,
    imbalance_ratios=(2.0, 2.5, 3.0, 3.5, 4.0),
    hold_candles_options=(1, 2, 3, 5, 8),
    ticks_per_candle: int = 500,
    tick_size: float = 0.05,
    level_size: float = 0.25,
) -> pd.DataFrame:
    """
    Run the full pipeline (footprint -> events -> backtest) once per
    (imbalance_ratio, hold_candles) combination.

    Returns a long-format DataFrame: one row per combination, with all
    compute_performance_metrics() fields as columns.
    """
    results = []

    for ratio in imbalance_ratios:
        # imbalance_ratio changes which levels get flagged, so candles
        # must be rebuilt for each ratio value
        candles = build_footprint_candles(
            ticks, ticks_per_candle=ticks_per_candle, tick_size=tick_size,
            imbalance_ratio=ratio, level_size=level_size,
        )
        events = detect_absorption_events(candles)

        for hold in hold_candles_options:
            trades = backtest_absorption_strategy(candles, events, hold_candles=hold)
            metrics = compute_performance_metrics(trades)
            results.append({"imbalance_ratio": ratio, "hold_candles": hold, **metrics})

    return pd.DataFrame(results)


def plot_sweep_heatmap(
    sweep_df: pd.DataFrame,
    metric: str = "sharpe_per_trade",
    save_path: str = "output/parameter_sweep_heatmap.png",
):
    """Render the sweep results as a heatmap: imbalance_ratio x hold_candles."""
    pivot = sweep_df.pivot(index="imbalance_ratio", columns="hold_candles", values=metric)

    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(pivot.values, cmap="RdYlGn", aspect="auto")

    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    ax.set_xlabel("hold_candles")
    ax.set_ylabel("imbalance_ratio")
    ax.set_title(f"Parameter Sweep: {metric}")

    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            val = pivot.values[i, j]
            label = "n/a" if pd.isna(val) else f"{val:.2f}"
            ax.text(j, i, label, ha="center", va="center", fontsize=9, color="black")

    fig.colorbar(im, ax=ax, label=metric)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close(fig)
    print(f"Saved heatmap to {save_path}")


if __name__ == "__main__":
    ticks = simulate_ticks(n_ticks=20000, start_price=100.00, tick_size=0.05)
    sweep_df = run_sweep(ticks)

    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
    os.makedirs(output_dir, exist_ok=True)
    sweep_df.to_csv(os.path.join(output_dir, "parameter_sweep_results.csv"), index=False)
    print(sweep_df.to_string(index=False))

    plot_sweep_heatmap(sweep_df, metric="sharpe_per_trade",
                        save_path=os.path.join(output_dir, "parameter_sweep_heatmap.png"))
    print(f"\nSaved full grid to output/parameter_sweep_results.csv")
