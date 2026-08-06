"""
tests/test_backtest.py
------------------------
Tests build Candle and AbsorptionEvent objects directly so trade outcomes
are known in advance and metrics can be checked exactly.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pandas as pd
import pytest

from footprint_builder import Candle
from absorption_detector import AbsorptionEvent
from backtest import backtest_absorption_strategy, compute_performance_metrics


def make_candle(open_time, open_, close):
    return Candle(
        open_time=open_time, open=open_, high=max(open_, close),
        low=min(open_, close), close=close, delta=0, total_volume=0,
        levels={}, imbalance_levels=set(),
    )


def make_event(candle_index, event_type="selling absorbed near lows (bullish signal)"):
    return AbsorptionEvent(
        candle_index=candle_index, open_time=f"t{candle_index}", price_level=100.0,
        aggressor_side="sell", buy_volume=10, sell_volume=100,
        event_type=event_type, next_close=101, candle_close=100,
    )


def test_bullish_event_produces_long_trade_with_correct_return():
    # event at candle 0 -> enter at candle 1's open, exit at candle (1+hold)'s close
    candles = [
        make_candle("t0", 100, 100),   # event candle
        make_candle("t1", 100, 102),   # entry open = 100
        make_candle("t2", 102, 104),
        make_candle("t3", 104, 110),   # exit close = 110, hold_candles=2 -> exit_idx=3
    ]
    events = [make_event(candle_index=0, event_type="selling absorbed near lows (bullish signal)")]

    trades = backtest_absorption_strategy(candles, events, hold_candles=2)

    assert len(trades) == 1
    assert trades.iloc[0]["direction"] == "long"
    assert trades.iloc[0]["entry_price"] == pytest.approx(100.0)
    assert trades.iloc[0]["exit_price"] == pytest.approx(110.0)
    assert trades.iloc[0]["pct_return"] == pytest.approx(0.10)  # +10%


def test_bearish_event_produces_short_trade_with_inverted_return():
    candles = [
        make_candle("t0", 100, 100),
        make_candle("t1", 100, 95),
        make_candle("t2", 95, 90),   # exit close = 90, hold_candles=1 -> exit_idx=2
    ]
    events = [make_event(candle_index=0, event_type="buying absorbed near highs (bearish signal)")]

    trades = backtest_absorption_strategy(candles, events, hold_candles=1)

    assert trades.iloc[0]["direction"] == "short"
    # price fell from 100 -> 90, short direction inverts the raw -10% into +10%
    assert trades.iloc[0]["pct_return"] == pytest.approx(0.10)


def test_trade_skipped_when_not_enough_candles_remain():
    candles = [make_candle("t0", 100, 100), make_candle("t1", 100, 105)]
    events = [make_event(candle_index=0)]  # would need candle index 1+hold, hold=5 -> out of range

    trades = backtest_absorption_strategy(candles, events, hold_candles=5)
    assert trades.empty


def test_metrics_on_empty_trades():
    metrics = compute_performance_metrics(pd.DataFrame())
    assert metrics["num_trades"] == 0
    assert metrics["win_rate"] is None


def test_metrics_all_winning_trades():
    trades = pd.DataFrame({"pct_return": [0.02, 0.03, 0.01]})
    metrics = compute_performance_metrics(trades)

    assert metrics["num_trades"] == 3
    assert metrics["win_rate"] == pytest.approx(1.0)
    assert metrics["max_drawdown_pct"] == pytest.approx(0.0)


def test_metrics_total_return_compounds_correctly():
    trades = pd.DataFrame({"pct_return": [0.10, -0.10]})
    metrics = compute_performance_metrics(trades)

    # (1.10 * 0.90) - 1 = -0.01 -> -1%
    assert metrics["total_return_pct"] == pytest.approx(-1.0, abs=0.01)
