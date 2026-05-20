from __future__ import annotations
import os
import sys
import json
import argparse
from typing import Optional

from dotenv import load_dotenv

from bot.logging_config import setup_logging, get_logger
from bot.client import BinanceFuturesClient, BinanceAPIError
from bot.orders import OrderManager

# Load .env before anything else
load_dotenv()

def _c(code: str, text: str) -> str:
    if sys.stdout.isatty():
        return f"\033[{code}m{text}\033[0m"
    return text

GREEN  = lambda t: _c("32", t)
RED    = lambda t: _c("31", t)
YELLOW = lambda t: _c("33", t)
CYAN   = lambda t: _c("36", t)
BOLD   = lambda t: _c("1",  t)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description=BOLD("Binance Futures Testnet Trading Bot"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py place --symbol BTCUSDT --side BUY  --type MARKET --quantity 0.01
  python cli.py place --symbol ETHUSDT --side SELL --type LIMIT  --quantity 0.1 --price 3500
  python cli.py place --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.01 --stop-price 60000
  python cli.py orders --symbol BTCUSDT
  python cli.py account
  python cli.py ping
        """,
    )
    parser.add_argument("--api-key",    default=None, help="Binance API key (overrides .env)")
    parser.add_argument("--api-secret", default=None, help="Binance API secret (overrides .env)")
    parser.add_argument("--log-level",  default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="Console log verbosity (default: INFO)")
    parser.add_argument("--base-url",   default=None,
                        help="Override testnet base URL")

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    p_place = sub.add_parser("place", help="Place a new order")
    p_place.add_argument("--symbol",     required=True,  help="e.g. BTCUSDT")
    p_place.add_argument("--side",       required=True,  choices=["BUY", "SELL"])
    p_place.add_argument("--type",       required=True,  dest="order_type",
                         choices=["MARKET", "LIMIT", "STOP_MARKET"],
                         help="Order type")
    p_place.add_argument("--quantity",   required=True,  help="Order quantity")
    p_place.add_argument("--price",      default=None,   help="Limit price (required for LIMIT)")
    p_place.add_argument("--stop-price", default=None,   dest="stop_price",
                         help="Stop trigger price (required for STOP_MARKET)")
    p_place.add_argument("--tif",        default="GTC",
                         choices=["GTC", "IOC", "FOK"],
                         help="Time-in-force for LIMIT orders (default: GTC)")
    p_place.add_argument("--reduce-only", action="store_true",
                         help="Reduce-only flag")

    p_orders = sub.add_parser("orders", help="List open orders")
    p_orders.add_argument("--symbol", default=None, help="Filter by symbol")

    p_cancel = sub.add_parser("cancel", help="Cancel an open order")
    p_cancel.add_argument("--symbol",   required=True)
    p_cancel.add_argument("--order-id", required=True, type=int, dest="order_id")

    sub.add_parser("account", help="Show account balances")

    sub.add_parser("ping", help="Test connectivity to Binance server")

    return parser


def cmd_place(client: BinanceFuturesClient, args: argparse.Namespace) -> int:
    manager = OrderManager(client)

    print(BOLD("\n─── Order Request ───────────────────────────────────"))
    print(f"  Symbol     : {CYAN(args.symbol.upper())}")
    print(f"  Side       : {GREEN(args.side) if args.side == 'BUY' else RED(args.side)}")
    print(f"  Type       : {args.order_type}")
    print(f"  Quantity   : {args.quantity}")
    if args.price:
        print(f"  Price      : {args.price}")
    if args.stop_price:
        print(f"  Stop Price : {args.stop_price}")
    print(BOLD("─────────────────────────────────────────────────────\n"))

    result = manager.place_order(
        symbol       = args.symbol,
        side         = args.side,
        order_type   = args.order_type,
        quantity     = args.quantity,
        price        = args.price,
        stop_price   = args.stop_price,
        time_in_force= args.tif,
        reduce_only  = args.reduce_only,
    )

    print(result.pretty_print())

    if result.success:
        print(GREEN("✅  Order submitted successfully."))
        return 0
    else:
        print(RED(f"❌  Order failed: {result.error_message}"))
        return 1


def cmd_orders(client: BinanceFuturesClient, args: argparse.Namespace) -> int:
    logger = get_logger("cli")
    try:
        orders = client.get_open_orders(symbol=args.symbol)
    except BinanceAPIError as exc:
        print(RED(f"API error: {exc}"))
        return 1
    except Exception as exc:
        print(RED(f"Error: {exc}"))
        return 1

    if not orders:
        print(YELLOW("No open orders found."))
        return 0

    print(BOLD(f"\n─── Open Orders ({len(orders)}) ───────────────────────────────"))
    for o in orders:
        print(
            f"  {o.get('orderId')} | {o.get('symbol')} | {o.get('side')} "
            f"{o.get('type')} | qty={o.get('origQty')} | price={o.get('price')} "
            f"| status={o.get('status')}"
        )
    print()
    return 0


def cmd_cancel(client: BinanceFuturesClient, args: argparse.Namespace) -> int:
    try:
        resp = client.cancel_order(symbol=args.symbol, order_id=args.order_id)
        print(GREEN(f"\n✅  Order {resp.get('orderId')} cancelled (status={resp.get('status')}).\n"))
        return 0
    except BinanceAPIError as exc:
        print(RED(f"API error: {exc}"))
        return 1
    except Exception as exc:
        print(RED(f"Error: {exc}"))
        return 1


def cmd_account(client: BinanceFuturesClient, _args: argparse.Namespace) -> int:
    try:
        account = client.get_account()
    except BinanceAPIError as exc:
        print(RED(f"API error: {exc}"))
        return 1
    except Exception as exc:
        print(RED(f"Error: {exc}"))
        return 1

    assets = [a for a in account.get("assets", []) if float(a.get("walletBalance", 0)) > 0]
    print(BOLD("\n─── Account Balances ─────────────────────────────────"))
    if not assets:
        print(YELLOW("  No non-zero balances found."))
    for a in assets:
        print(
            f"  {a['asset']:<10} wallet={a['walletBalance']:<16} "
            f"available={a['availableBalance']}"
        )
    print()
    return 0


def cmd_ping(client: BinanceFuturesClient, _args: argparse.Namespace) -> int:
    try:
        server_time = client.get_server_time()
        import datetime
        dt = datetime.datetime.utcfromtimestamp(server_time / 1000).strftime("%Y-%m-%d %H:%M:%S")
        print(GREEN(f"\n✅  Connected to Binance Futures Testnet  (server time: {dt} UTC)\n"))
        return 0
    except Exception as exc:
        print(RED(f"\n❌  Connection failed: {exc}\n"))
        return 1


# ── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = build_parser()
    args   = parser.parse_args()

    setup_logging(args.log_level)
    logger = get_logger("cli")
 
    api_key    = args.api_key    or os.getenv("BINANCE_API_KEY",    "")
    api_secret = args.api_secret or os.getenv("BINANCE_API_SECRET", "")
    base_url   = args.base_url   or os.getenv("BINANCE_BASE_URL",   "https://testnet.binancefuture.com")

    if not api_key or not api_secret:
        parser.error(
            "API credentials not found. Provide --api-key / --api-secret flags "
            "or set BINANCE_API_KEY / BINANCE_API_SECRET in .env"
        )

    try:
        client = BinanceFuturesClient(
            api_key    = api_key,
            api_secret = api_secret,
            base_url   = base_url,
        )
    except ValueError as exc:
        parser.error(str(exc))

    dispatch = {
        "place":   cmd_place,
        "orders":  cmd_orders,
        "cancel":  cmd_cancel,
        "account": cmd_account,
        "ping":    cmd_ping,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)

    exit_code = handler(client, args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
