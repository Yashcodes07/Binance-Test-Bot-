"""Unit tests for the validators module."""

import pytest
from decimal import Decimal
from bot.validators import (
    validate_symbol,
    validate_side,
    validate_order_type,
    validate_quantity,
    validate_price,
    validate_stop_price,
)


class TestValidateSymbol:
    def test_valid_symbol(self):
        assert validate_symbol("btcusdt") == "BTCUSDT"

    def test_strips_whitespace(self):
        assert validate_symbol("  ETHUSDT  ") == "ETHUSDT"

    def test_short_symbol_raises(self):
        with pytest.raises(ValueError, match="Invalid symbol"):
            validate_symbol("BTC")

    def test_special_chars_raise(self):
        with pytest.raises(ValueError):
            validate_symbol("BTC-USD")


class TestValidateSide:
    def test_buy(self):
        assert validate_side("buy") == "BUY"

    def test_sell(self):
        assert validate_side("SELL") == "SELL"

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="Invalid side"):
            validate_side("LONG")


class TestValidateOrderType:
    def test_market(self):
        assert validate_order_type("market") == "MARKET"

    def test_limit(self):
        assert validate_order_type("LIMIT") == "LIMIT"

    def test_stop_market(self):
        assert validate_order_type("stop_market") == "STOP_MARKET"

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Invalid order type"):
            validate_order_type("TWAP")


class TestValidateQuantity:
    def test_valid_decimal(self):
        assert validate_quantity("0.01") == Decimal("0.01")

    def test_valid_int(self):
        assert validate_quantity(1) == Decimal("1")

    def test_zero_raises(self):
        with pytest.raises(ValueError, match="greater than zero"):
            validate_quantity("0")

    def test_negative_raises(self):
        with pytest.raises(ValueError):
            validate_quantity("-1")

    def test_non_numeric_raises(self):
        with pytest.raises(ValueError, match="valid number"):
            validate_quantity("abc")


class TestValidatePrice:
    def test_market_ignores_price(self):
        assert validate_price("100", "MARKET") is None

    def test_limit_requires_price(self):
        with pytest.raises(ValueError, match="required"):
            validate_price(None, "LIMIT")

    def test_limit_valid_price(self):
        assert validate_price("70000", "LIMIT") == Decimal("70000")

    def test_negative_price_raises(self):
        with pytest.raises(ValueError, match="greater than zero"):
            validate_price("-50", "LIMIT")


class TestValidateStopPrice:
    def test_non_stop_returns_none(self):
        assert validate_stop_price("60000", "MARKET") is None
        assert validate_stop_price("60000", "LIMIT")  is None

    def test_stop_market_requires_stop_price(self):
        with pytest.raises(ValueError, match="required"):
            validate_stop_price(None, "STOP_MARKET")

    def test_stop_market_valid(self):
        assert validate_stop_price("60000", "STOP_MARKET") == Decimal("60000")
