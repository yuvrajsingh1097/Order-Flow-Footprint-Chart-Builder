"""
tests/test_absorption_detector.py
-----------------------------------
Tests build Candle objects directly (bypassing the tick pipeline) so each
scenario is deterministic and isolated.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from footprint_builder import Candle
from absorption_detector import detect_absorption_events


def make_candle(open_time, open_, high, low, close, levels, imbalance_levels):
    return Candle(
        open_time=open_time, open=open_, high=high, low=low, close=close,
        delta=0, total_volume=0, levels=levels, imbalance_levels=imbalance_levels,
    )


def test_buying_absorbed_near_highs_is_flagged():
    # heavy buying right at the high, but next candle closes lower -> bearish absorption
    c0 = make_candle(
        "t0", open_=100, high=105, low=99, close=104,
        levels={105.0: {"buy": 200, "sell": 20}},
        imbalance_levels={105.0},
    )
    c1 = make_candle(
        "t1", open_=104, high=104, low=100, close=101,
        levels={}, imbalance_levels=set(),
    )
    events = detect_absorption_events([c0, c1])

    assert len(events) == 1
    assert events[0].aggressor_side == "buy"
    assert "bearish" in events[0].event_type


def test_selling_absorbed_near_lows_is_flagged():
    # heavy selling right at the low, but next candle closes higher -> bullish absorption
    c0 = make_candle(
        "t0", open_=100, high=101, low=95, close=96,
        levels={95.0: {"buy": 10, "sell": 180}},
        imbalance_levels={95.0},
    )
    c1 = make_candle(
        "t1", open_=96, high=99, low=96, close=98,
        levels={}, imbalance_levels=set(),
    )
    events = detect_absorption_events([c0, c1])

    assert len(events) == 1
    assert events[0].aggressor_side == "sell"
    assert "bullish" in events[0].event_type


def test_no_event_when_price_continues_in_aggressor_direction():
    # heavy buying at the high AND next candle continues higher -> no absorption,
    # this is just normal continuation, not a failed breakout
    c0 = make_candle(
        "t0", open_=100, high=105, low=99, close=104,
        levels={105.0: {"buy": 200, "sell": 20}},
        imbalance_levels={105.0},
    )
    c1 = make_candle(
        "t1", open_=105, high=110, low=104, close=109,
        levels={}, imbalance_levels=set(),
    )
    events = detect_absorption_events([c0, c1])
    assert events == []


def test_no_event_when_imbalance_level_is_mid_range_not_at_edge():
    # imbalance sits in the middle of the candle's range, not near the high/low
    c0 = make_candle(
        "t0", open_=100, high=110, low=90, close=105,
        levels={100.0: {"buy": 200, "sell": 20}},
        imbalance_levels={100.0},
    )
    c1 = make_candle(
        "t1", open_=105, high=105, low=95, close=96,
        levels={}, imbalance_levels=set(),
    )
    events = detect_absorption_events([c0, c1])
    assert events == []


def test_no_event_when_no_imbalance_levels_flagged():
    c0 = make_candle(
        "t0", open_=100, high=105, low=99, close=104,
        levels={105.0: {"buy": 30, "sell": 25}},
        imbalance_levels=set(),
    )
    c1 = make_candle(
        "t1", open_=104, high=104, low=100, close=101,
        levels={}, imbalance_levels=set(),
    )
    events = detect_absorption_events([c0, c1])
    assert events == []


def test_last_candle_has_no_lookahead_and_is_skipped():
    # a single candle can't be evaluated since there's no "next candle" to check
    c0 = make_candle(
        "t0", open_=100, high=105, low=99, close=104,
        levels={105.0: {"buy": 200, "sell": 20}},
        imbalance_levels={105.0},
    )
    events = detect_absorption_events([c0])
    assert events == []
