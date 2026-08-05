"""
absorption_detector.py
------------------------
Bonus module: flags "absorption" events using the same Candle objects
footprint_builder.py already produces -- no new data pipeline needed.

Absorption, in order-flow terms, is when a large amount of aggressive
volume trades into a price level (usually at the high or low of a
candle) but fails to move price through it -- i.e. a passive player is
"absorbing" the aggression. It's a classic reversal signal on prop desks:
heavy buying at the highs that doesn't follow through often precedes a
pullback, and heavy selling at the lows that doesn't follow through often
precedes a bounce.

This module looks at:
  1. Which price level in a candle carries the flagged imbalance
     (already computed by footprint_builder.build_footprint_candles)
  2. Whether that level sits near the candle's high or low
  3. Whether the following candle's close moves *against* the
     direction the imbalance would suggest

If all three line up, it's flagged as an absorption event.
"""

from dataclasses import dataclass

from footprint_builder import Candle


@dataclass
class AbsorptionEvent:
    candle_index: int
    open_time: object
    price_level: float
    aggressor_side: str      # 'buy' or 'sell' -- the side doing the absorbed aggression
    buy_volume: float
    sell_volume: float
    event_type: str          # human-readable description
    next_close: float
    candle_close: float


def detect_absorption_events(
    candles: list[Candle],
    edge_zone_pct: float = 0.15,
    lookahead: int = 1,
) -> list[AbsorptionEvent]:
    """
    Scan candles for absorption at imbalance levels near the high/low.

    edge_zone_pct: how close to the candle's high/low (as a fraction of
        the candle's total range) a price level must be to count as
        "near the edge". 0.15 means within the top/bottom 15% of the range.
    lookahead: how many candles ahead to check for the follow-through
        failure that confirms absorption.
    """
    events = []

    for i in range(len(candles) - lookahead):
        candle = candles[i]
        future = candles[i + lookahead]

        if not candle.imbalance_levels or candle.high == candle.low:
            continue

        candle_range = candle.high - candle.low

        for price in candle.imbalance_levels:
            vol = candle.levels[price]
            buy, sell = vol["buy"], vol["sell"]
            aggressor_side = "buy" if buy > sell else "sell"

            near_high = (candle.high - price) <= candle_range * edge_zone_pct
            near_low = (price - candle.low) <= candle_range * edge_zone_pct

            if aggressor_side == "buy" and near_high and future.close < candle.close:
                events.append(AbsorptionEvent(
                    candle_index=i,
                    open_time=candle.open_time,
                    price_level=price,
                    aggressor_side=aggressor_side,
                    buy_volume=buy,
                    sell_volume=sell,
                    event_type="buying absorbed near highs (bearish signal)",
                    next_close=future.close,
                    candle_close=candle.close,
                ))
            elif aggressor_side == "sell" and near_low and future.close > candle.close:
                events.append(AbsorptionEvent(
                    candle_index=i,
                    open_time=candle.open_time,
                    price_level=price,
                    aggressor_side=aggressor_side,
                    buy_volume=buy,
                    sell_volume=sell,
                    event_type="selling absorbed near lows (bullish signal)",
                    next_close=future.close,
                    candle_close=candle.close,
                ))

    return events


def events_to_report(events: list[AbsorptionEvent]) -> str:
    """Human-readable summary, e.g. for printing to console or a log."""
    if not events:
        return "No absorption events detected."

    lines = [f"{len(events)} absorption event(s) detected:\n"]
    for e in events:
        lines.append(
            f"  [{e.open_time}] candle #{e.candle_index} @ {e.price_level:.2f} -- "
            f"{e.event_type} (sell {e.sell_volume:.0f} x buy {e.buy_volume:.0f}, "
            f"close {e.candle_close:.2f} -> next close {e.next_close:.2f})"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    import os
    import pandas as pd
    from data_simulator import simulate_ticks
    from footprint_builder import build_footprint_candles

    ticks = simulate_ticks(n_ticks=20000, start_price=100.00, tick_size=0.05)
    candles = build_footprint_candles(
        ticks, ticks_per_candle=500, tick_size=0.05, imbalance_ratio=3.0, level_size=0.25
    )
    events = detect_absorption_events(candles)
    print(events_to_report(events))

    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
    os.makedirs(output_dir, exist_ok=True)
    pd.DataFrame([vars(e) for e in events]).to_csv(
        os.path.join(output_dir, "absorption_events.csv"), index=False
    )
    print(f"\nSaved {len(events)} events to output/absorption_events.csv")
