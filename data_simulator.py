"""
data_simulator.py
------------------
Generates synthetic tick-level trade data that mimics real order-flow
characteristics: a random-walk mid-price, aggressor-side tagging (buy/sell),
and periodic "bursts" of one-sided aggression to create realistic
absorption / imbalance zones for the footprint chart to reveal.

Swap this module out for a real feed (Binance/Bybit WebSocket trade stream,
or a broker's tick API) without touching footprint_builder.py or
visualizer.py -- they only depend on the tick schema below:

    timestamp : pd.Timestamp
    price     : float
    size      : float
    side      : 'buy' | 'sell'   (aggressor side)
"""

import numpy as np
import pandas as pd


def simulate_ticks(
    n_ticks: int = 20000,
    start_price: float = 100.00,
    tick_size: float = 0.05,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Simulate a session of aggressor-tagged trades.

    Mechanics:
      - Price follows a random walk in tick-size increments.
      - Most ticks are small, evenly mixed buy/sell (noise trading).
      - At random intervals, a "burst" of one-sided aggression fires
        (simulating a large player working an order), which both moves
        price and skews the buy/sell volume at nearby levels -- this is
        what produces visible imbalance/absorption in the footprint.

    Returns
    -------
    pd.DataFrame with columns [timestamp, price, size, side]
    """
    rng = np.random.default_rng(seed)

    timestamps = pd.date_range("2026-01-01 09:15:00", periods=n_ticks, freq="s")
    prices = np.zeros(n_ticks)
    sizes = np.zeros(n_ticks)
    sides = np.empty(n_ticks, dtype=object)

    price = start_price
    burst_remaining = 0
    burst_side = "buy"

    for i in range(n_ticks):
        # occasionally trigger a new burst of one-sided aggression
        if burst_remaining == 0 and rng.random() < 0.01:
            burst_remaining = rng.integers(15, 60)
            burst_side = rng.choice(["buy", "sell"])

        if burst_remaining > 0:
            side = burst_side if rng.random() < 0.75 else rng.choice(["buy", "sell"])
            size = rng.gamma(shape=2.0, scale=8.0)  # larger size during bursts
            drift = tick_size if burst_side == "buy" else -tick_size
            price += drift * (rng.random() < 0.5)
            burst_remaining -= 1
        else:
            side = rng.choice(["buy", "sell"])
            size = rng.gamma(shape=1.5, scale=2.0)  # smaller noise-trade size
            price += tick_size * rng.choice([-1, 0, 1])

        prices[i] = round(price / tick_size) * tick_size
        sizes[i] = max(round(size, 2), 0.01)
        sides[i] = side

    return pd.DataFrame(
        {"timestamp": timestamps, "price": prices, "size": sizes, "side": sides}
    )


if __name__ == "__main__":
    df = simulate_ticks()
    df.to_csv("output/sample_ticks.csv", index=False)
    print(f"Simulated {len(df)} ticks, price range "
          f"[{df.price.min():.2f}, {df.price.max():.2f}]")
