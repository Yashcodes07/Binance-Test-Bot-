"""
Order placement logic layer.

Sits between the CLI and the raw API client.
Responsible for:
  - Calling validators before touching the API
  - Formatting and returning a clean OrderResult
  - Logging the full order lifecycle
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, Optional

from .client import BinanceFuturesClient, BinanceAPIError
from .validators import (
    validate_symbol,
    validate_side,
    validate_order_type,
    validate_quantity,
    validate_price,
    validate_stop_price,
)
from .logging_config import get_logger

logger = get_logger("orders")


@dataclass
class OrderResult:
    """Structured representation of an order placement outcome."""

    success: bool
    order_id: Optional[int]        = None
    client_order_id: Optional[str] = None
    symbol: Optional[str]          = None
    side: Optional[str]            = None
    order_type: Optional[str]      = None
    orig_qty: Optional[str]        = None
    executed_qty: Optional[str]    = None
    avg_price: Optional[str]       = None
    status: Optional[str]          = None
    price: Optional[str]           = None
    stop_price: Optional[str]      = None
    time_in_force: Optional[str]   = None
    raw_response: Dict[str, Any]   = field(default_factory=dict)
    error_message: Optional[str]   = None

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "OrderResult":
        return cls(
            success        = True,
            order_id       = data.get("orderId"),
            client_order_id= data.get("clientOrderId"),
            symbol         = data.get("symbol"),
            side           = data.get("side"),
            order_type     = data.get("type"),
            orig_qty       = data.get("origQty"),
            executed_qty   = data.get("executedQty"),
            avg_price      = data.get("avgPrice"),
            status         = data.get("status"),
            price          = data.get("price"),
            stop_price     = data.get("stopPrice"),
            time_in_force  = data.get("timeInForce"),
            raw_response   = data,
        )

    @classmethod
    def from_error(cls, message: str) -> "OrderResult":
        return cls(success=False, error_message=message)

    def pretty_print(self) -> str:
        """Return a human-readable summary string."""
        if not self.success:
            return f"\n❌  Order FAILED\n   Reason : {self.error_message}\n"

        lines = [
            "",
            "✅  Order placed successfully",
            f"   Order ID      : {self.order_id}",
            f"   Client OID    : {self.client_order_id}",
            f"   Symbol        : {self.symbol}",
            f"   Side          : {self.side}",
            f"   Type          : {self.order_type}",
            f"   Status        : {self.status}",
            f"   Orig Qty      : {self.orig_qty}",
            f"   Executed Qty  : {self.executed_qty}",
        ]
        if self.avg_price and self.avg_price != "0":
            lines.append(f"   Avg Price     : {self.avg_price}")
        if self.price and self.price != "0":
            lines.append(f"   Limit Price   : {self.price}")
        if self.stop_price and self.stop_price != "0":
            lines.append(f"   Stop Price    : {self.stop_price}")
        if self.time_in_force:
            lines.append(f"   Time in Force : {self.time_in_force}")
        lines.append("")
        return "\n".join(lines)


class OrderManager:
    """
    High-level order manager that validates inputs and delegates to the API client.
    """

    def __init__(self, client: BinanceFuturesClient) -> None:
        self._client = client

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: str | float,
        price: Optional[str | float] = None,
        stop_price: Optional[str | float] = None,
        time_in_force: str = "GTC",
        reduce_only: bool = False,
    ) -> OrderResult:
        """
        Validate inputs, place an order, and return a structured OrderResult.

        All parameters accept raw user strings; validation normalises them.
        """
        # ---- Validation -----------------------------------------------
        try:
            v_symbol      = validate_symbol(symbol)
            v_side        = validate_side(side)
            v_order_type  = validate_order_type(order_type)
            v_quantity    = validate_quantity(quantity)
            v_price       = validate_price(price, v_order_type)
            v_stop_price  = validate_stop_price(stop_price, v_order_type)
        except ValueError as exc:
            logger.warning("Validation failed: %s", exc)
            return OrderResult.from_error(str(exc))

        logger.info(
            "Order request | symbol=%s side=%s type=%s qty=%s price=%s stop=%s",
            v_symbol, v_side, v_order_type, v_quantity,
            v_price or "N/A", v_stop_price or "N/A",
        )

        # ---- Placement ------------------------------------------------
        try:
            response = self._client.place_order(
                symbol        = v_symbol,
                side          = v_side,
                order_type    = v_order_type,
                quantity      = str(v_quantity),
                price         = str(v_price) if v_price else None,
                stop_price    = str(v_stop_price) if v_stop_price else None,
                time_in_force = time_in_force,
                reduce_only   = reduce_only,
            )
            result = OrderResult.from_api_response(response)
            logger.info(
                "Order result | orderId=%s status=%s execQty=%s",
                result.order_id, result.status, result.executed_qty,
            )
            return result

        except BinanceAPIError as exc:
            logger.error("Binance API error during order placement: %s", exc)
            return OrderResult.from_error(str(exc))
        except Exception as exc:
            logger.exception("Unexpected error during order placement: %s", exc)
            return OrderResult.from_error(f"Unexpected error: {exc}")
