"""Damped mean-reversion BTC forecaster for make.fun btc-cent-forecast-01.

Forecasts the cbBTC/USDC price 240 minutes after each checkpoint from the
4,320 one-minute closes up to the checkpoint (72 hours, one market).

Model (chosen by backtest, not by gut feel)
--------------------------------------------
For a 4-hour horizon the honest point forecast under absolute-error scoring
is the median of the price 240 minutes out. A pure random walk says that
median is today's price (persistence), and every trend extrapolation we
tested made things *worse* on out-of-sample checkpoints: short-window
trend-following (EWMA log-return, half-life 30-120 min, any shrinkage)
and long-window drift (mean log-return over 12-72 h) both lost to
persistence on 65 four-hourly checkpoints of 14 days of Coinbase BTC/USD
minute closes (31 Oct - 14 Nov 2026) and on 60 internal checkpoints cut
from the six practice cases.

What did help, small but consistent, is short-horizon mean reversion:
the price tends to drift back toward its own mean of the last hour.
So the forecast is the checkpoint close pulled a fraction of the way
toward the mean log-price of the last 60 minutes:

    gap  = mean(log p over last 60 min) - log(last close)
    adj  = 0.5 * gap, clamped to +/-2% in log terms
    guess = last close * exp(adj)

Backtest results (mean absolute error, cents; lower is better):
  - 65 checkpoints, 14 days Coinbase BTC/USD minute closes:
      persistence 53,406 | this model 52,019  (-2.6%)
  - 60 internal checkpoints inside the six practice cases:
      persistence 40,521 | this model 38,030  (-6.1%)
  - practice checkpoints p00-p04 (only 5 points, strong downtrend):
      persistence 47,055 | this model 52,611  (worse - regime risk noted)
The pull is deliberately modest (0.5, one hour, +/-2% clamp) so the
worst case stays close to persistence instead of betting the house on
one regime. No trend term is used at all.

Deterministic: pure arithmetic over the input prices, no randomness,
no network, standard library only. Runs in well under a second a case.
"""

import json
import math
import os
from pathlib import Path

INPUT_DIR = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
OUTPUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")

# Mean-reversion window (minutes) and pull strength, fixed by backtest.
MR_WINDOW = 60
MR_STRENGTH = 0.5
# Largest log-move the model will ever predict (safety clamp).
MAX_LOG_MOVE = 0.02

MIN_PRICE = 0.00001
MAX_PRICE = 9_999_999.99999


def price5(x):
    """Keep a price on the grid's 5 decimals and inside (0, 10,000,000)."""
    return round(min(MAX_PRICE, max(MIN_PRICE, x)) * 1e5) / 1e5


def forecast(prices):
    """Forecast the close 240 minutes after the last price in `prices`."""
    if not prices:
        raise ValueError("market has no prices")
    last = prices[-1]
    if not isinstance(last, (int, float)) or not math.isfinite(last) or last <= 0:
        raise ValueError("last price is not a finite positive number")

    window = prices[-MR_WINDOW:]
    # Defensive: any bad value in the window falls back to persistence
    # (the checkpoint close) instead of crashing the whole case.
    if any(
        not isinstance(p, (int, float)) or not math.isfinite(p) or p <= 0
        for p in window
    ):
        return price5(last)
    mean_log = sum(math.log(p) for p in window) / len(window)
    gap = mean_log - math.log(last)
    adj = MR_STRENGTH * gap
    if adj > MAX_LOG_MOVE:
        adj = MAX_LOG_MOVE
    elif adj < -MAX_LOG_MOVE:
        adj = -MAX_LOG_MOVE
    return price5(last * math.exp(adj))


def main():
    in_dir = Path(INPUT_DIR)
    out_dir = Path(OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    # Every case file, in name order, so two runs write the same bytes.
    inputs = sorted(p for p in in_dir.iterdir() if p.name.endswith(".in"))
    for path in inputs:
        case_id = path.name[: -len(".in")]
        with path.open("r", encoding="utf-8") as f:
            case = json.load(f)
        markets = case.get("markets")
        if not isinstance(markets, list) or len(markets) != 1:
            raise ValueError(f"{path.name} does not hold exactly one market")
        guess = forecast(markets[0]["prices"])
        out = {"forecasts": [{"case": case_id, "price": guess}]}
        with (out_dir / f"{case_id}.out").open("w", encoding="utf-8") as f:
            f.write(json.dumps(out) + "\n")


if __name__ == "__main__":
    main()
