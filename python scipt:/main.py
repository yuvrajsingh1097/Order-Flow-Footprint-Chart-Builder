"""
main.py
-------
Entry point: simulate ticks -> build footprint candles -> render charts.

Run from the project root:
    python src/main.py
"""

import os
from data_simulator import simulate_ticks
from footprint_builder import build_footprint_candles, candles_to_summary_df
from visualizer import plot_footprint, plot_cumulative_delta

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Simulating tick data...")
    ticks = simulate_ticks(n_ticks=20000, start_price=100.00, tick_size=0.05)
    ticks.to_csv(os.path.join(OUTPUT_DIR, "sample_ticks.csv"), index=False)

    print("Building footprint candles...")
    candles = build_footprint_candles(
        ticks, ticks_per_candle=500, tick_size=0.05, imbalance_ratio=3.0, level_size=0.25
    )
    summary = candles_to_summary_df(candles)
    summary.to_csv(os.path.join(OUTPUT_DIR, "candle_summary.csv"), index=False)
    print(summary.tail())

    print("\nRendering footprint chart...")
    plot_footprint(candles, max_candles=12, save_path=os.path.join(OUTPUT_DIR, "footprint_chart.png"))

    print("Rendering cumulative delta chart...")
    plot_cumulative_delta(candles, save_path=os.path.join(OUTPUT_DIR, "cumulative_delta.png"))

    print("\nDone. See the output/ directory for CSVs and PNG charts.")


if __name__ == "__main__":
    main()
