# Setup Guide

Steps for anyone cloning this repo to get it running from scratch,
regardless of OS.

## Prerequisites

- Python 3.10 or newer
- git

Check your Python version:

```bash
python3 --version
```

## 1. Clone the repo

```bash
git clone https://github.com/<username>/orderflow-footprint-chart.git
cd orderflow-footprint-chart
```

## 2. Create a virtual environment

Keeps this project's packages separate from anything else on your
machine.

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

You'll know it worked if your terminal prompt now starts with `(venv)`.

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

## 4. Run the pipeline

```bash
python src/main.py
```

This simulates a session of order-flow tick data, builds footprint
candles, and writes fresh charts + CSVs into `output/`, overwriting the
sample ones already in the repo.

Expected console output ends with:
```
Rendering footprint chart...
Saved chart to .../output/footprint_chart.png
Rendering cumulative delta chart...
Saved chart to .../output/cumulative_delta.png

Done. See the output/ directory for CSVs and PNG charts.
```

## 5. View the results

Open these two files in any image viewer:
- `output/footprint_chart.png`
- `output/cumulative_delta.png`

## When you're done

```bash
deactivate
```
exits the virtual environment.

## Troubleshooting

| problem | likely fix |
|---|---|
| `python3: command not found` | Install Python from [python.org](https://python.org) or via your OS package manager (`brew install python3` on macOS) |
| `ModuleNotFoundError: No module named 'pandas'` (or numpy/matplotlib) | The venv isn't activated, or step 3 was skipped — re-run steps 2 and 3 |
| `ImportError` inside `src/main.py` about relative imports | Run the script from the project root as `python src/main.py`, not from inside `src/` |
| Charts look cluttered / overlapping text | Lower `ticks_per_candle` or raise `level_size` in `src/main.py` — see the "Configuration knobs" table in `README.md` |
| `pip install` fails on an old Python version | Confirm `python3 --version` is 3.10+; upgrade Python if not |

## Customizing before you run it

All the knobs that change chart behavior live in `src/main.py`:
`ticks_per_candle`, `level_size`, `imbalance_ratio`, and `n_ticks`
(session length). See the "Configuration knobs" section of `README.md`
for what each one does.


same for mac just opt the terminal mac os 
