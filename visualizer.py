"""
visualizer.py
--------------
Renders footprint candles as a matplotlib chart:
  - top panel: per-candle price ladder with buy x sell volume printed at
    each traded price level; cells flagged as significant imbalance are
    highlighted; a thin candlestick wick/body is drawn behind the text
  - bottom panel: cumulative delta line + per-candle delta bars, so you
    can see order-flow trend independent of price
"""

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from footprint_builder import Candle


def plot_footprint(
    candles: list[Candle],
    max_candles: int = 12,
    save_path: str = "output/footprint_chart.png",
):
    """
    Plot the last `max_candles` footprint candles. Limited to a small
    window because footprint charts are read level-by-level -- this is
    a zoomed-in tool, not an overview chart.
    """
    candles = candles[-max_candles:]

    fig, (ax_price, ax_delta) = plt.subplots(
        2, 1, figsize=(max(14, len(candles) * 1.8), 12),
        gridspec_kw={"height_ratios": [4, 1]}, sharex=False
    )

    candle_width = 1.0
    all_levels = sorted({lvl for c in candles for lvl in c.levels})
    level_spacing = (all_levels[1] - all_levels[0]) if len(all_levels) > 1 else 0.05

    for i, candle in enumerate(candles):
        x = i * (candle_width + 1.2)

        # candle body outline (open/close range) as light backdrop
        body_low, body_high = min(candle.open, candle.close), max(candle.open, candle.close)
        ax_price.add_patch(Rectangle(
            (x - 0.05, body_low - level_spacing / 2),
            candle_width + 0.1, (body_high - body_low) + level_spacing,
            facecolor="#dddddd", edgecolor="none", zorder=1
        ))
        # wick
        ax_price.plot([x + candle_width / 2] * 2, [candle.low, candle.high],
                      color="#888888", linewidth=1, zorder=1)

        for price, vol in sorted(candle.levels.items()):
            buy, sell = vol["buy"], vol["sell"]
            is_imbalance = price in candle.imbalance_levels
            color = "#1a7f37" if buy >= sell else "#d1242f"
            weight = "bold" if is_imbalance else "normal"
            bgcolor = "#fff3b0" if is_imbalance else "none"

            label = f"{sell:>5.0f} x {buy:<5.0f}"
            ax_price.text(
                x + candle_width / 2, price, label,
                ha="center", va="center", fontsize=7.5,
                color=color, fontweight=weight,
                bbox=dict(boxstyle="round,pad=0.15", fc=bgcolor, ec="none") if is_imbalance else None,
                zorder=3, family="monospace",
            )

        ax_price.text(
            x + candle_width / 2, candle.high + level_spacing * 1.5,
            candle.open_time.strftime("%H:%M:%S"),
            ha="center", fontsize=8, color="#555555"
        )

    ax_price.set_ylabel("Price")
    ax_price.set_title(
        "Order Flow Footprint Chart\n(cell format: sell volume x buy volume, "
        "highlighted = significant imbalance)", fontsize=12
    )
    ax_price.set_xticks([])
    ax_price.margins(y=0.08)

    # delta subpanel
    deltas = [c.delta for c in candles]
    colors = ["#1a7f37" if d >= 0 else "#d1242f" for d in deltas]
    xs = [i * (candle_width + 1.2) + candle_width / 2 for i in range(len(candles))]
    ax_delta.bar(xs, deltas, width=candle_width, color=colors)
    ax_delta.axhline(0, color="black", linewidth=0.8)
    ax_delta.set_ylabel("Delta")
    ax_delta.set_xticks(xs)
    ax_delta.set_xticklabels([c.open_time.strftime("%H:%M:%S") for c in candles], rotation=45, fontsize=8)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close(fig)
    print(f"Saved chart to {save_path}")


def plot_absorption_events(candles: list[Candle], events, save_path: str = "output/absorption_events_chart.png"):
    """
    Plot session close price with markers at each detected absorption
    event: red down-triangle for bearish (buying absorbed near highs),
    green up-triangle for bullish (selling absorbed near lows).

    `events` is the list[AbsorptionEvent] returned by
    absorption_detector.detect_absorption_events().
    """
    times = [c.open_time for c in candles]
    closes = [c.close for c in candles]

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(times, closes, color="#57606a", linewidth=1.2, zorder=1, label="Close price")

    bearish = [e for e in events if "bearish" in e.event_type]
    bullish = [e for e in events if "bullish" in e.event_type]

    if bearish:
        ax.scatter(
            [e.open_time for e in bearish], [e.candle_close for e in bearish],
            marker="v", s=140, color="#d1242f", edgecolor="black", zorder=3,
            label="Buying absorbed (bearish)",
        )
    if bullish:
        ax.scatter(
            [e.open_time for e in bullish], [e.candle_close for e in bullish],
            marker="^", s=140, color="#1a7f37", edgecolor="black", zorder=3,
            label="Selling absorbed (bullish)",
        )

    ax.set_ylabel("Price")
    ax.set_title("Price with Detected Absorption Events")
    ax.legend(loc="best")
    fig.autofmt_xdate()

    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close(fig)
    print(f"Saved chart to {save_path}")


def plot_cumulative_delta(candles: list[Candle], save_path: str = "output/cumulative_delta.png"):
    """
    Plot cumulative delta over the full session against closing price --
    useful for spotting divergence (price up, cumulative delta flat/down).
    """
    times = [c.open_time for c in candles]
    closes = [c.close for c in candles]
    cum_delta = []
    running = 0
    for c in candles:
        running += c.delta
        cum_delta.append(running)

    fig, ax1 = plt.subplots(figsize=(14, 6))
    ax2 = ax1.twinx()

    ax1.plot(times, closes, color="#0969da", linewidth=1.5, label="Close price")
    ax2.plot(times, cum_delta, color="#bf3989", linewidth=1.5, label="Cumulative delta")

    ax1.set_ylabel("Price", color="#0969da")
    ax2.set_ylabel("Cumulative Delta", color="#bf3989")
    ax1.set_title("Price vs. Cumulative Order Flow Delta")
    fig.autofmt_xdate()

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close(fig)
    print(f"Saved chart to {save_path}")
