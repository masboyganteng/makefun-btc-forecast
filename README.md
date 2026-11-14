# Damped-trend BTC forecaster

Entry for make.fun competition **btc-cent-forecast-01**: forecast Bitcoin's
US-dollar price (cbBTC/USDC Orca pool) 240 minutes after each checkpoint,
from the 4,320 one-minute closes of the 72 hours up to that checkpoint.

## How it works

`main.py` (Python 3.13, standard library only, no network) reads every
`*.in` case in `$MAKEFUN_INPUT_DIR` (else `/input`) and writes one
`{"forecasts": [{"case": <id>, "price": <guess>}]}` JSON file per case to
`$MAKEFUN_OUTPUT_DIR` (else `/output`).

The forecast is the checkpoint close pulled halfway toward the mean
log-price of the last 60 minutes, with the predicted log-move clamped to
±2%:

```
gap   = mean(log p, last 60 min) - log(last close)
guess = last close * exp(0.5 * gap)      # clamped to ±2%
```

## Why this, and not trend-following

Backtested on 65 four-hourly checkpoints over 14 days of Coinbase BTC/USD
minute closes (31 Oct – 14 Nov 2026) and on 60 internal checkpoints cut
from the six practice cases:

| model | 14-day MAE (cents) | practice-internal MAE (cents) |
|---|---|---|
| persistence (guess = last close) | 53,406 | 40,521 |
| **this model** | **52,019** | **38,030** |
| trend extrapolation (EWMA / long drift) | 55,000–73,000 | 43,000–64,000 |

Trend extrapolation lost everywhere, so the model uses no trend term at
all. The mean-reversion pull is deliberately modest (0.5 over one hour)
so the worst case stays close to persistence. Honest caveat: on the five
practice checkpoints themselves (p00–p04, a strong downtrend) this model
scored worse than persistence (52,611 vs 47,055 cents) — the edge is
small and regime-dependent, and the practice is no guide to the final.

## Run it

```sh
mkdir -p out
MAKEFUN_INPUT_DIR=<kit>/input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Deterministic: two runs on the same case write byte-identical output.
Runs in well under a second per case (limit: 8 s).

## License

MIT — see `LICENSE`.
