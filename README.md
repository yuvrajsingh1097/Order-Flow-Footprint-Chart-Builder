# Order Flow Footprint Chart Builder

Reconstructs order-flow footprint charts from tick-level trade data: for
every candle, it shows how much volume traded at the **bid** vs the
**ask** at each price level, flags price levels with significant
buy/sell **imbalance**, and tracks cumulative **delta** (buy volume minus
sell volume) to reveal order-flow trend independent of price.

This is the same core technique used on prop trading desks and by retail
order-flow platforms (Bookmap, ATAS, Sierra Chart) to read where
aggressive buyers/sellers are active and where large passive orders are
absorbing flow.

## What's in a footprint chart

Each cell in the grid corresponds to one price level within one candle,
formatted as:

```
sell_volume x buy_volume
```

- **Green, buy-dominant** cells: more aggressive buying than selling at
  that price
- **Red, sell-dominant** cells: more aggressive selling
- **Highlighted (bold, shaded) cells**: flagged as significant imbalance
  — buy or sell volume at that level exceeds the other side by a
  configurable ratio (default 3:1), which often marks absorption or
  exhaustion points

The panel below the price ladder shows per-candle **delta** (buy − sell
volume) as bars, and a separate chart plots **cumulative delta** against
price to spot divergence — e.g. price grinding to a new high while
cumulative delta fails to confirm.

## Example output

**Footprint chart** (12 most recent candles):

![Footprint chart](output/footprint_chart.png)

**Price vs. cumulative delta:**

![Cumulative delta](output/cumulative_delta.png)

## How it works

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full data flow diagram.
In short: raw ticks → grouped into candles → volume bucketed by price
level and aggressor side → imbalance levels flagged → rendered as a
price-ladder chart + delta panel.

## Project structure

```
orderflow-footprint-chart/
├── README.md
├── ARCHITECTURE.md
├── requirements.txt
├── src/
│   ├── data_simulator.py     # generates sample tick data (swap for a real feed)
│   ├── footprint_builder.py  # core aggregation: ticks -> footprint candles
│   ├── visualizer.py         # matplotlib rendering
│   └── main.py                # pipeline entry point
└── output/                    # generated charts + CSVs land here
```

## Running it

```bash
pip install -r requirements.txt
python src/main.py
```

This simulates a session of tick data, builds footprint candles, and
writes two PNGs plus two CSVs (raw ticks and per-candle summary) to
`output/`.

## Using real market data instead of simulated data

`data_simulator.py` is a stand-in — swap it for any tick feed as long as
you produce a DataFrame with the same schema:

| column    | type      | description                     |
|-----------|-----------|----------------------------------|
| timestamp | datetime  | trade time                       |
| price     | float     | trade price                      |
| size      | float     | trade size                       |
| side      | 'buy'/'sell' | aggressor side (taker side)   |

Real sources to plug in:
- **Crypto**: Binance/Bybit WebSocket trade streams give aggressor side
  directly (`isBuyerMaker` on Binance, inverted to get the taker/aggressor
  side)
- **Equities/options**: most broker tick APIs (Databento, Polygon.io,
  IBKR) include trade-condition flags you can use to infer aggressor side
  when it isn't given directly (compare trade price to prevailing
  bid/ask)

Nothing in `footprint_builder.py` or `visualizer.py` needs to change —
they only depend on the four-column schema above.

## Configuration knobs (in `main.py`)

| parameter | what it controls |
|---|---|
| `ticks_per_candle` | how many ticks make up one candle (volume-based candles instead of time-based, so activity per candle stays comparable) |
| `level_size` | price resolution for footprint rows — coarser than the raw tick size so each candle renders a readable ~10-25 rows instead of hundreds |
| `imbalance_ratio` | threshold (default 3.0 = 300%) above which a price level is flagged as significant one-sided aggression |

## Notes / limitations

- The bundled data is **simulated**, not real market data — it's built
  to produce realistic-looking imbalance/absorption patterns for
  demonstration, but isn't a substitute for backtesting on real ticks.
- Footprint charts are inherently a zoomed-in tool (`plot_footprint`)
  only renders the most recent N candles) — they're meant for reading a
  specific moment of price action, not scanning a whole session.
