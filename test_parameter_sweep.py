"""
tests/test_parameter_sweep.py
-------------------------------
Uses a small simulated tick set (not the full 20k-tick session) so the
test suite stays fast -- this module's job is to check the sweep grid
is built correctly, not to validate strategy performance (that's
test_backtest.py's job).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from data_simulator import simulate_ticks
from parameter_sweep import run_sweep, plot_sweep_heatmap


def test_sweep_produces_one_row_per_combination():
    ticks = simulate_ticks(n_ticks=3000, start_price=100.0, tick_size=0.05, seed=1)
    ratios = (2.0, 3.0)
    holds = (1, 2, 3)

    sweep_df = run_sweep(
        ticks, imbalance_ratios=ratios, hold_candles_options=holds, ticks_per_candle=300
    )

    assert len(sweep_df) == len(ratios) * len(holds)
    assert set(sweep_df["imbalance_ratio"].unique()) == set(ratios)
    assert set(sweep_df["hold_candles"].unique()) == set(holds)


def test_sweep_output_has_expected_metric_columns():
    ticks = simulate_ticks(n_ticks=3000, start_price=100.0, tick_size=0.05, seed=1)
    sweep_df = run_sweep(
        ticks, imbalance_ratios=(3.0,), hold_candles_options=(2,), ticks_per_candle=300
    )

    expected_cols = {
        "imbalance_ratio", "hold_candles", "num_trades", "win_rate",
        "total_return_pct", "avg_return_pct", "sharpe_per_trade", "max_drawdown_pct",
    }
    assert expected_cols.issubset(set(sweep_df.columns))


def test_heatmap_renders_without_error(tmp_path):
    ticks = simulate_ticks(n_ticks=3000, start_price=100.0, tick_size=0.05, seed=1)
    sweep_df = run_sweep(
        ticks, imbalance_ratios=(2.0, 3.0), hold_candles_options=(1, 2), ticks_per_candle=300
    )

    save_path = tmp_path / "heatmap.png"
    plot_sweep_heatmap(sweep_df, metric="win_rate", save_path=str(save_path))

    assert save_path.exists()
    assert save_path.stat().st_size > 0
