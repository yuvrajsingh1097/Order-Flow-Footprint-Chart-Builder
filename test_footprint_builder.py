"""
tests/test_footprint_builder.py
--------------------------------
Unit tests for footprint_builder.py -- the only module in this repo with
real business logic worth testing (data_simulator.py is a synthetic data
generator, visualizer.py is plotting code).

Run with:
    pytest tests/
"""

import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from footprint_builder import build_footprint_candles, candles_to_summary_df


def make_ticks(rows):
    """
    Helper: build a minimal ticks DataFrame from a list of
    (timestamp_str, price, size, side) tuples.
    """
    return pd.DataFrame(
        rows, columns=["timestamp", "price", "size", "side"]
    ).assign(timestamp=lambda df: pd.to_datetime(df["timestamp"]))


def test_single_candle_delta_is_buy_minus_sell():
    ticks = make_ticks([
        ("2026-01-01 09:00:00", 100.0, 10, "buy"),
        ("2026-01-01 09:00:01", 100.0, 4, "sell"),
        ("2026-01-01 09:00:02", 100.0, 6, "buy"),
    ])
    candles = build_footprint_candles(ticks, ticks_per_candle=10, tick_size=0.05)

    assert len(candles) == 1
    # buy total = 16, sell total = 4 -> delta = 12
    assert candles[0].delta == pytest.approx(12.0)
    assert candles[0].total_volume == pytest.approx(20.0)


def test_ticks_split_across_multiple_candles():
    ticks = make_ticks([
        ("2026-01-01 09:00:00", 100.0, 5, "buy"),
        ("2026-01-01 09:00:01", 100.0, 5, "buy"),
        ("2026-01-01 09:00:02", 101.0, 5, "sell"),
        ("2026-01-01 09:00:03", 101.0, 5, "sell"),
    ])
    candles = build_footprint_candles(ticks, ticks_per_candle=2, tick_size=0.05)

    assert len(candles) == 2
    assert candles[0].delta == pytest.approx(10.0)   # both buys
    assert candles[1].delta == pytest.approx(-10.0)  # both sells


def test_level_size_buckets_prices_coarser_than_tick_size():
    ticks = make_ticks([
        ("2026-01-01 09:00:00", 100.01, 1, "buy"),
        ("2026-01-01 09:00:01", 100.04, 1, "buy"),
        ("2026-01-01 09:00:02", 100.24, 1, "sell"),
    ])
    candles = build_footprint_candles(
        ticks, ticks_per_candle=10, tick_size=0.01, level_size=0.25
    )

    # first two prices should collapse into a single bucketed level
    # (100.01 and 100.04 both round to 100.0 at level_size=0.25)
    assert len(candles[0].levels) == 2


def test_imbalance_flagged_above_ratio_threshold():
    # buy:sell = 4:1 at this level, ratio threshold is 3.0 -> should flag
    ticks = make_ticks([
        ("2026-01-01 09:00:00", 100.0, 40, "buy"),
        ("2026-01-01 09:00:01", 100.0, 10, "sell"),
    ])
    candles = build_footprint_candles(
        ticks, ticks_per_candle=10, tick_size=0.05, imbalance_ratio=3.0
    )

    assert 100.0 in candles[0].imbalance_levels


def test_imbalance_not_flagged_below_ratio_threshold():
    # buy:sell = 2:1, below the 3.0 threshold -> should NOT flag
    ticks = make_ticks([
        ("2026-01-01 09:00:00", 100.0, 20, "buy"),
        ("2026-01-01 09:00:01", 100.0, 10, "sell"),
    ])
    candles = build_footprint_candles(
        ticks, ticks_per_candle=10, tick_size=0.05, imbalance_ratio=3.0
    )

    assert 100.0 not in candles[0].imbalance_levels


def test_empty_ticks_produce_no_candles():
    ticks = make_ticks([])
    candles = build_footprint_candles(ticks, ticks_per_candle=10, tick_size=0.05)
    assert candles == []


def test_summary_df_has_one_row_per_candle():
    ticks = make_ticks([
        ("2026-01-01 09:00:00", 100.0, 5, "buy"),
        ("2026-01-01 09:00:01", 101.0, 5, "sell"),
    ])
    candles = build_footprint_candles(ticks, ticks_per_candle=1, tick_size=0.05)
    summary = candles_to_summary_df(candles)

    assert len(summary) == len(candles) == 2
    assert list(summary.columns) == [
        "open_time", "open", "high", "low", "close",
        "delta", "total_volume", "num_imbalance_levels",
    ]
