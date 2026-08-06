"""
backtest.py
------------
Turns absorption_detector's events into an actual (simplified) trading
strategy and backtests it: enter at the open of the candle right after
an event, in the direction the event implies (bullish absorption -> long,
bearish absorption -> short), hold for a fixed number of candles, exit
at close.

This is intentionally simple -- no position sizing, slippage, fees, or
overlapping trades -- but it's enough to produce real performance
metrics (win rate, Sharpe, max drawdown) instead of just "the signal
looks interesting on the chart", which is what separates a backtested
idea from a plotted one.

Swap `hold_candles` or the entry/exit rule for something more realistic
(e.g. exit on a stop/target instead of a fixed hold) without touching
absorption_detector.py or footprint_builder.py.
"""

import os

import numpy as np
import pandas as pd

from footprint_builder import Candle
from absorption_detector import AbsorptionEvent


def backtest_absorption_strategy(
    candles: list[Candle],
    events: list[AbsorptionEvent],
    hold_candles: int = 3,
) -> pd.DataFrame:
    """
    Simulate one trade per absorption event: enter at the next candle's
    open, exit `hold_candles` candles later at that candle's close.

    Returns a DataFrame with one row per trade (empty if no events).
    """
    trades = []

    for event in events:
        entry_idx = event.candle_index + 1
        exit_idx = entry_idx + hold_candles

        if entry_idx >= len(candles) or exit_idx >= len(candles):
            continue  # not enough candles left to complete this trade

        direction = 1 if "bullish" in event.event_type else -1
        entry_price = candles[entry_idx].open
        exit_price = candles[exit_idx].close
        pct_return = direction * (exit_price - entry_price) / entry_price

        trades.append({
            "entry_time": candles[entry_idx].open_time,
            "exit_time": candles[exit_idx].open_time,
            "direction": "long" if direction == 1 else "short",
            "entry_price": entry_price,
            "exit_price": exit_price,
            "pct_return": pct_return,
            "event_type": event.event_type,
        })

    return pd.DataFrame(trades)


def compute_performance_metrics(trades: pd.DataFrame) -> dict:
    """
    Compute standard backtest metrics from a trades DataFrame.
    Sharpe here is a per-trade Sharpe (not annualized) since trades
    aren't evenly spaced in time -- treat it as a relative comparison
    tool between strategy variants, not a literal annualized figure.
    """
    if trades.empty:
        return {
            "num_trades": 0, "win_rate": None, "total_return_pct": None,
            "avg_return_pct": None, "sharpe_per_trade": None, "max_drawdown_pct": None,
        }

    returns = trades["pct_return"]
    equity_curve = (1 + returns).cumprod()
    running_max = equity_curve.cummax()
    drawdown = (equity_curve - running_max) / running_max

    return {
        "num_trades": len(trades),
        "win_rate": round((returns > 0).mean(), 4),
        "total_return_pct": round((equity_curve.iloc[-1] - 1) * 100, 3),
        "avg_return_pct": round(returns.mean() * 100, 4),
        "sharpe_per_trade": round(returns.mean() / returns.std(), 3) if returns.std() > 0 else None,
        "max_drawdown_pct": round(drawdown.min() * 100, 3),
    }


def metrics_to_report(metrics: dict) -> str:
    if metrics["num_trades"] == 0:
        return "No trades to evaluate (no absorption events, or not enough candles to complete a trade)."

    return (
        f"Trades:            {metrics['num_trades']}\n"
        f"Win rate:          {metrics['win_rate']:.1%}\n"
        f"Total return:      {metrics['total_return_pct']:.3f}%\n"
        f"Avg return/trade:  {metrics['avg_return_pct']:.4f}%\n"
        f"Sharpe per trade:  {metrics['sharpe_per_trade']}\n"
        f"Max drawdown:      {metrics['max_drawdown_pct']:.3f}%"
    )


if __name__ == "__main__":
    from data_simulator import simulate_ticks
    from footprint_builder import build_footprint_candles
    from absorption_detector import detect_absorption_events
    import matplotlib.pyplot as plt

    ticks = simulate_ticks(n_ticks=20000, start_price=100.00, tick_size=0.05)
    candles = build_footprint_candles(
        ticks, ticks_per_candle=500, tick_size=0.05, imbalance_ratio=3.0, level_size=0.25
    )
    events = detect_absorption_events(candles)
    trades = backtest_absorption_strategy(candles, events, hold_candles=3)
    metrics = compute_performance_metrics(trades)

    print(metrics_to_report(metrics))

    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
    os.makedirs(output_dir, exist_ok=True)
    trades.to_csv(os.path.join(output_dir, "backtest_trades.csv"), index=False)

    if not trades.empty:
        equity_curve = (1 + trades["pct_return"]).cumprod()
        fig, ax = plt.subplots(figsize=(12, 5))
        ax.plot(range(1, len(equity_curve) + 1), equity_curve.values, color="#0969da", linewidth=1.5, marker="o", markersize=3)
        ax.axhline(1.0, color="black", linewidth=0.8, linestyle="--")
        ax.set_xlabel("Trade #")
        ax.set_ylabel("Equity (starting = 1.0)")
        ax.set_title("Absorption Strategy -- Equity Curve")
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "backtest_equity_curve.png"), dpi=150)
        plt.close(fig)
        print(f"\nSaved trade log to output/backtest_trades.csv")
        print(f"Saved equity curve to output/backtest_equity_curve.png")
