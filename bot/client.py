"""
Binance Futures REST API client wrapper.

Handles:
  - HMAC-SHA256 request signing
  - Server-time synchronisation
  - Structured request/response logging
  - Retry logic on transient network errors
  - Uniform BinanceAPIError for all non-2xx responses
"""

from __future__ import annotations

import hashlib
import hmac
import time
import urllib.parse
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .logging_config import get_logger

logger = get_logger("client")

TESTNET_BASE_URL = "https://testnet.binancefuture.com"
DEFAULT_RECV_WINDOW = 5000   # ms
REQUEST_TIMEOUT     = 10     # seconds


class BinanceAPIError(Exception):
    """Raised when the Binance API returns a non-2xx response."""

    def __init__(self, status_code: int, code: int, msg: str) -> None:
        self.status_code = status_code
        self.code = code
        self.msg = msg
        super().__init__(f"[HTTP {status_code}] Binance error {code}: {msg}")


def _build_session() -> requests.Session:
    """Create a requests session with automatic retry on transient failures."""
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist={429, 500, 502, 503, 504},
        allowed_methods={"GET", "POST", "DELETE"},
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


class BinanceFuturesClient:
    """
    Thin, authenticated wrapper around the Binance USDT-M Futures REST API.

    Usage::

        client = BinanceFuturesClient(api_key="...", api_secret="...")
        resp = client.place_order(symbol="BTCUSDT", side="BUY",
                                   order_type="MARKET", quantity="0.01")
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = TESTNET_BASE_URL,
        recv_window: int = DEFAULT_RECV_WINDOW,
    ) -> None:
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret must not be empty.")
        self._api_key    = api_key
        self._api_secret = api_secret.encode()
        self._base_url   = base_url.rstrip("/")
        self._recv_window = recv_window
        self._session    = _build_session()
        self._session.headers.update({"X-MBX-APIKEY": self._api_key})
        logger.info("BinanceFuturesClient initialised (base_url=%s)", self._base_url)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _timestamp(self) -> int:
        """Return current UTC timestamp in milliseconds."""
        return int(time.time() * 1000)

    def _sign(self, params: Dict[str, Any]) -> str:
        """Compute HMAC-SHA256 signature over URL-encoded params."""
        query_string = urllib.parse.urlencode(params)
        return hmac.new(self._api_secret, query_string.encode(), hashlib.sha256).hexdigest()

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute an HTTP request against the Binance Futures REST API.

        Args:
            method:   HTTP verb ("GET" or "POST").
            endpoint: API path, e.g. "/fapi/v1/order".
            params:   Query / body parameters.
            signed:   Whether to attach timestamp + signature.

        Returns:
            Parsed JSON response as a dict.

        Raises:
            BinanceAPIError: On non-2xx API responses.
            requests.RequestException: On network-level failures.
        """
        params = params or {}
        url = f"{self._base_url}{endpoint}"

        if signed:
            params["timestamp"]  = self._timestamp()
            params["recvWindow"] = self._recv_window
            params["signature"]  = self._sign(params)

        logger.debug("→ %s %s  params=%s", method, endpoint, {k: v for k, v in params.items() if k != "signature"})

        try:
            if method == "GET":
                response = self._session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            elif method == "POST":
                response = self._session.post(url, params=params, timeout=REQUEST_TIMEOUT)
            elif method == "DELETE":
                response = self._session.delete(url, params=params, timeout=REQUEST_TIMEOUT)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
        except requests.exceptions.ConnectionError as exc:
            logger.error("Network connection error: %s", exc)
            raise
        except requests.exceptions.Timeout as exc:
            logger.error("Request timed out: %s", exc)
            raise

        try:
            data = response.json()
        except ValueError:
            logger.error("Non-JSON response (HTTP %s): %s", response.status_code, response.text[:200])
            response.raise_for_status()
            return {}

        if not response.ok:
            code = data.get("code", response.status_code)
            msg  = data.get("msg", response.text)
            logger.error("API error (HTTP %s) code=%s msg=%s", response.status_code, code, msg)
            raise BinanceAPIError(response.status_code, code, msg)

        logger.debug("← HTTP %s  response=%s", response.status_code, data)
        return data

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_server_time(self) -> int:
        """Fetch Binance server time (ms). Useful to check connectivity."""
        data = self._request("GET", "/fapi/v1/time")
        return data["serverTime"]

    def get_exchange_info(self) -> Dict[str, Any]:
        """Return exchange info (symbol rules, filters, etc.)."""
        return self._request("GET", "/fapi/v1/exchangeInfo")

    def get_account(self) -> Dict[str, Any]:
        """Return account balance and position info."""
        return self._request("GET", "/fapi/v2/account", signed=True)

    def get_open_orders(self, symbol: Optional[str] = None) -> list:
        """Return list of open orders, optionally filtered by symbol."""
        params: Dict[str, Any] = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/fapi/v1/openOrders", params=params, signed=True)

    def get_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Query a single order by ID."""
        return self._request(
            "GET",
            "/fapi/v1/order",
            params={"symbol": symbol, "orderId": order_id},
            signed=True,
        )

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: str,
        price: Optional[str] = None,
        stop_price: Optional[str] = None,
        time_in_force: str = "GTC",
        reduce_only: bool = False,
    ) -> Dict[str, Any]:
        """
        Place a new order on Binance Futures Testnet.

        Args:
            symbol:        Trading pair, e.g. "BTCUSDT".
            side:          "BUY" or "SELL".
            order_type:    "MARKET", "LIMIT", or "STOP_MARKET".
            quantity:      Order size as a string to preserve precision.
            price:         Limit price (required for LIMIT orders).
            stop_price:    Stop trigger price (required for STOP_MARKET).
            time_in_force: "GTC" | "IOC" | "FOK" (ignored for MARKET).
            reduce_only:   If True, order can only reduce position.

        Returns:
            Raw API response dict.
        """
        params: Dict[str, Any] = {
            "symbol":   symbol,
            "side":     side,
            "type":     order_type,
            "quantity": quantity,
        }

        if order_type == "LIMIT":
            if not price:
                raise ValueError("price is required for LIMIT orders.")
            params["price"]       = price
            params["timeInForce"] = time_in_force

        elif order_type == "STOP_MARKET":
            if not stop_price:
                raise ValueError("stopPrice is required for STOP_MARKET orders.")
            params["stopPrice"] = stop_price

        if reduce_only:
            params["reduceOnly"] = "true"

        logger.info(
            "Placing %s %s order | symbol=%s qty=%s price=%s stopPrice=%s",
            side, order_type, symbol, quantity, price or "N/A", stop_price or "N/A",
        )

        response = self._request("POST", "/fapi/v1/order", params=params, signed=True)
        logger.info(
            "Order placed | orderId=%s status=%s executedQty=%s avgPrice=%s",
            response.get("orderId"),
            response.get("status"),
            response.get("executedQty"),
            response.get("avgPrice"),
        )
        return response

    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Cancel an existing open order."""
        logger.info("Cancelling order %s on %s", order_id, symbol)
        return self._request(
            "DELETE",
            "/fapi/v1/order",
            params={"symbol": symbol, "orderId": order_id},
            signed=True,
        )
