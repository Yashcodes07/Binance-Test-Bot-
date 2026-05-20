# Binance Futures Testnet Trading Bot

A clean, production-style Python CLI application that places orders on
**Binance USDT-M Futures Testnet** with proper input validation, structured
logging, and robust error handling.

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py          # Package exports
│   ├── client.py            # Binance Futures REST API client (signing, retry, error handling)
│   ├── orders.py            # Order placement logic + OrderResult dataclass
│   ├── validators.py        # Input validation (symbol, side, price, qty, …)
│   └── logging_config.py    # Rotating file + console logging setup
├── logs/
│   └── trading_bot.log      # Auto-created; rotates at 5 MB
├── cli.py                   # CLI entry point (argparse)
├── .env.example             # Credentials template
├── requirements.txt
└── README.md
```

---

## Setup

### 1 — Register on Binance Futures Testnet

1. Visit <https://testnet.binancefuture.com>
2. Click **Register** → log in with GitHub / email.
3. Go to **API Management** → **Create API Key**.
4. Copy your **API Key** and **API Secret**.

### 2 — Clone & install

```bash
git clone https://github.com/<you>/trading_bot.git
cd trading_bot

python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows
.venv\Scripts\activate

pip install -r requirements.txt
```

### 3 — Configure credentials

```bash
cp .env.example .env
# Edit .env and paste your testnet key & secret
```

`.env` contents:

```env
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_api_secret_here
BINANCE_BASE_URL=https://testnet.binancefuture.com
```

> ⚠️ **Never commit `.env` to version control.**

---

## Running the Bot

### Test connectivity

```bash
python cli.py ping
```

Expected output:
```
✅  Connected to Binance Futures Testnet  (server time: 2025-06-10 14:22:01 UTC)
```

### Place a MARKET order

```bash
python cli.py place \
  --symbol BTCUSDT \
  --side BUY \
  --type MARKET \
  --quantity 0.01
```

### Place a LIMIT order

```bash
python cli.py place \
  --symbol ETHUSDT \
  --side SELL \
  --type LIMIT \
  --quantity 0.1 \
  --price 3500
```

### Place a STOP_MARKET order (bonus order type)

```bash
python cli.py place \
  --symbol BTCUSDT \
  --side SELL \
  --type STOP_MARKET \
  --quantity 0.01 \
  --stop-price 60000
```

### View open orders

```bash
python cli.py orders                    # all symbols
python cli.py orders --symbol BTCUSDT  # filtered
```

### Cancel an order

```bash
python cli.py cancel --symbol BTCUSDT --order-id 3865139210
```

### Check account balances

```bash
python cli.py account
```

### Verbose debug logging to console

```bash
python cli.py --log-level DEBUG place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
```

---

## CLI Reference

```
usage: trading_bot [-h] [--api-key KEY] [--api-secret SECRET]
                   [--log-level {DEBUG,INFO,WARNING,ERROR}]
                   [--base-url URL]
                   COMMAND ...

COMMAND:
  place    Place a new order
  orders   List open orders
  cancel   Cancel an open order
  account  Show account balances
  ping     Test connectivity

place options:
  --symbol SYMBOL          Trading pair, e.g. BTCUSDT           (required)
  --side {BUY,SELL}                                              (required)
  --type {MARKET,LIMIT,STOP_MARKET}                             (required)
  --quantity QUANTITY      Order size                            (required)
  --price PRICE            Limit price      (required for LIMIT)
  --stop-price STOP_PRICE  Stop trigger     (required for STOP_MARKET)
  --tif {GTC,IOC,FOK}      Time-in-force for LIMIT (default GTC)
  --reduce-only            Set reduce-only flag
```

---

## Logging

All activity is written to **`logs/trading_bot.log`** (rotating, max 5 MB,
3 backups) with `DEBUG` granularity. The console shows `INFO` and above by
default; pass `--log-level DEBUG` to see full request/response details.

Log format:
```
2025-06-10 14:22:02 | INFO     | trading_bot.orders | Placing BUY MARKET order | symbol=BTCUSDT qty=0.01 …
```

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Missing/invalid argument | `argparse` prints usage and exits 1 |
| Validation failure (bad symbol, negative qty, …) | Error printed; logged as WARNING; exits 1 |
| Binance API error (e.g. -2019 insufficient margin) | `BinanceAPIError` caught; message printed & logged |
| Network timeout / connection failure | Retried 3× with backoff; error printed & logged |
| Non-JSON response | Logged as ERROR; exception propagated cleanly |

---

## Assumptions

- The bot targets the **USDT-M Futures Testnet** only (`/fapi/v1/` endpoints).
- **Hedge-mode** is not supported — all orders use `positionSide=BOTH` (default).
- Quantity / price precision is passed through as entered; for production use,
  exchange `LOT_SIZE` / `TICK_SIZE` filters should be applied automatically.
- Python **3.9+** required.

---

## Bonus Features Implemented

- ✅ **STOP_MARKET** as a third order type (triggered stop, market execution)
- ✅ Colour-coded terminal output (degrades gracefully on non-TTY)
- ✅ `ping` and `account` utility sub-commands
- ✅ `cancel` sub-command
- ✅ `--reduce-only` and `--tif` flags

---

## Running Tests (optional)

```bash
pip install pytest pytest-mock
pytest tests/ -v
```

---

## License

MIT
