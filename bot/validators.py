"""
Input validation helpers for order parameters.
All validation raises ValueError with a user-friendly message on failure.
"""

from __future__ import annotations
from decimal import Decimal, InvalidOperation
from typing import Optional

from .logging_config import get_logger

logger = get_logger("validators")

SUPPORTED_SIDES        = {"BUY", "SELL"}
SUPPORTED_ORDER_TYPES  = {"MARKET", "LIMIT", "STOP_MARKET"}
MIN_QUANTITY           = Decimal("0.001")
MAX_QUANTITY           = Decimal("1_000_000")
MIN_PRICE              = Decimal("0.01")
MAX_PRICE              = Decimal("10_000_000")


def validate_symbol(symbol: str) -> str:
    """Uppercase and verify that symbol looks like a valid futures pair."""
    symbol = symbol.strip().upper()
    if len(symbol) < 5 or not symbol.isalnum():
        raise ValueError(
            f"Invalid symbol '{symbol}'. Expected format: BTCUSDT, ETHUSDT, …"
        )
    logger.debug("Symbol validated: %s", symbol)
    return symbol


def validate_side(side: str) -> str:
    """Validate order side (BUY / SELL)."""
    side = side.strip().upper()
    if side not in SUPPORTED_SIDES:
        raise ValueError(
            f"Invalid side '{side}'. Must be one of: {', '.join(SUPPORTED_SIDES)}"
        )
    logger.debug("Side validated: %s", side)
    return side


def validate_order_type(order_type: str) -> str:
    """Validate order type (MARKET / LIMIT / STOP_MARKET)."""
    order_type = order_type.strip().upper()
    if order_type not in SUPPORTED_ORDER_TYPES:
        raise ValueError(
            f"Invalid order type '{order_type}'. "
            f"Must be one of: {', '.join(SUPPORTED_ORDER_TYPES)}"
        )
    logger.debug("Order type validated: %s", order_type)
    return order_type


def validate_quantity(quantity: str | float) -> Decimal:
    """Parse and validate order quantity."""
    try:
        qty = Decimal(str(quantity))
    except InvalidOperation:
        raise ValueError(f"Quantity '{quantity}' is not a valid number.")
    if qty <= 0:
        raise ValueError("Quantity must be greater than zero.")
    if qty < MIN_QUANTITY:
        raise ValueError(f"Quantity {qty} is below minimum allowed ({MIN_QUANTITY}).")
    if qty > MAX_QUANTITY:
        raise ValueError(f"Quantity {qty} exceeds maximum allowed ({MAX_QUANTITY}).")
    logger.debug("Quantity validated: %s", qty)
    return qty


def validate_price(price: str | float | None, order_type: str) -> Optional[Decimal]:
    """
    Validate price field.
    - Required for LIMIT and STOP_MARKET orders.
    - Must be None / omitted for MARKET orders.
    """
    order_type = order_type.upper()

    if order_type == "MARKET":
        if price is not None:
            logger.warning("Price supplied for MARKET order; it will be ignored.")
        return None

    if price is None or str(price).strip() == "":
        raise ValueError(f"Price is required for {order_type} orders.")

    try:
        p = Decimal(str(price))
    except InvalidOperation:
        raise ValueError(f"Price '{price}' is not a valid number.")
    if p <= 0:
        raise ValueError("Price must be greater than zero.")
    if p < MIN_PRICE:
        raise ValueError(f"Price {p} is below minimum allowed ({MIN_PRICE}).")
    if p > MAX_PRICE:
        raise ValueError(f"Price {p} exceeds maximum allowed ({MAX_PRICE}).")

    logger.debug("Price validated: %s", p)
    return p


def validate_stop_price(stop_price: str | float | None, order_type: str) -> Optional[Decimal]:
    """Stop price is required only for STOP_MARKET orders."""
    if order_type.upper() != "STOP_MARKET":
        return None
    if stop_price is None or str(stop_price).strip() == "":
        raise ValueError("Stop price is required for STOP_MARKET orders.")
    try:
        sp = Decimal(str(stop_price))
    except InvalidOperation:
        raise ValueError(f"Stop price '{stop_price}' is not a valid number.")
    if sp <= 0:
        raise ValueError("Stop price must be greater than zero.")
    logger.debug("Stop price validated: %s", sp)
    return sp
