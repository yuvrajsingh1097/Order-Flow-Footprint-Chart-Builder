"""
footprint_builder.py
---------------------
Aggregates raw ticks into fixed-size candles, and within each candle,
buckets buy/sell volume by price level (tick_size resolution). This is
the core "footprint" data structure: for every candle you get a
price -> (buy_volume, sell_volume) map, plus per-candle OHLC and delta.

Definitions used throughout:
  delta            = total_buy_volume - total_sell_volume  (per candle)
  level imbalance  = buy_vol / sell_vol at a single price level
                      (or sell_vol / buy_vol, whichever >= imbalance_ratio)
  imbalance_ratio  = threshold above which a level is flagged as
                      significant one-sided aggression (default 3.0, i.e. 300%)
"""

from dataclasses import dataclass, field
import pandas as pd


@dataclass
class Candle:
    open_time: pd.Timestamp
    open: float
    high: float
    low: float
    close: float
    delta: float
    total_volume: float
    # price_level -> {"buy": vol, "sell": vol}
    levels: dict = field(default_factory=dict)
    # set of price levels flagged as significant imbalance
    imbalance_levels: set = field(default_factory=set)


def build_footprint_candles(
    ticks: pd.DataFrame,
    ticks_per_candle: int = 500,
    tick_size: float = 0.05,
    imbalance_ratio: float = 3.0,
    level_size: float | None = None,
) -> list[Candle]:
    """
    Group raw ticks into fixed-count candles and build the per-level
    buy/sell footprint for each.

    ticks_per_candle is used instead of a fixed time window so each
    candle contains comparable trade activity regardless of session
    volatility -- swap for time-based grouping (e.g. df.resample('1min'))
    if your use case needs wall-clock aligned candles instead.

    level_size controls the price resolution used to bucket the footprint
    rows, independent of the raw tick_size the data was recorded at. Real
    footprint charts usually aggregate to a coarser grid than the raw tick
    (e.g. every 0.25 instead of every 0.01) so each candle shows a readable
    ~10-25 rows instead of hundreds. Defaults to tick_size (no aggregation)
    if not given.
    """
    if level_size is None:
        level_size = tick_size

    candles = []
    n = len(ticks)

    for start in range(0, n, ticks_per_candle):
        chunk = ticks.iloc[start:start + ticks_per_candle]
        if chunk.empty:
            continue

        levels: dict[float, dict[str, float]] = {}
        for _, row in chunk.iterrows():
            bucketed_price = round(row["price"] / level_size) * level_size
            bucketed_price = round(bucketed_price, 6)
            lvl = levels.setdefault(bucketed_price, {"buy": 0.0, "sell": 0.0})
            lvl[row["side"]] += row["size"]

        buy_total = sum(v["buy"] for v in levels.values())
        sell_total = sum(v["sell"] for v in levels.values())

        imbalance_levels = set()
        for price, vol in levels.items():
            buy, sell = vol["buy"], vol["sell"]
            if sell > 0 and buy / sell >= imbalance_ratio:
                imbalance_levels.add(price)
            elif buy > 0 and sell / buy >= imbalance_ratio:
                imbalance_levels.add(price)

        candle = Candle(
            open_time=chunk["timestamp"].iloc[0],
            open=chunk["price"].iloc[0],
            high=chunk["price"].max(),
            low=chunk["price"].min(),
            close=chunk["price"].iloc[-1],
            delta=buy_total - sell_total,
            total_volume=buy_total + sell_total,
            levels=levels,
            imbalance_levels=imbalance_levels,
        )
        candles.append(candle)

    return candles


def candles_to_summary_df(candles: list[Candle]) -> pd.DataFrame:
    """Flatten candle list into a summary DataFrame (one row per candle)."""
    return pd.DataFrame([
        {
            "open_time": c.open_time,
            "open": c.open,
            "high": c.high,
            "low": c.low,
            "close": c.close,
            "delta": c.delta,
            "total_volume": c.total_volume,
            "num_imbalance_levels": len(c.imbalance_levels),
        }
        for c in candles
    ])


if __name__ == "__main__":
    from data_simulator import simulate_ticks

    ticks = simulate_ticks()
    candles = build_footprint_candles(ticks)
    summary = candles_to_summary_df(candles)
    print(summary.head(10))
    print(f"\nBuilt {len(candles)} footprint candles from {len(ticks)} ticks")
