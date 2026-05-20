"""Unit tests for the OrderManager / OrderResult."""

import pytest
from unittest.mock import MagicMock, patch
from bot.orders import OrderManager, OrderResult
from bot.client import BinanceAPIError


MOCK_FILLED_RESPONSE = {
    "orderId": 123456,
    "clientOrderId": "test-001",
    "symbol": "BTCUSDT",
    "side": "BUY",
    "type": "MARKET",
    "origQty": "0.01",
    "executedQty": "0.01",
    "avgPrice": "67000.00",
    "status": "FILLED",
    "price": "0",
    "stopPrice": "0",
    "timeInForce": "GTC",
}


@pytest.fixture()
def mock_client():
    client = MagicMock()
    client.place_order.return_value = MOCK_FILLED_RESPONSE
    return client


class TestOrderManager:
    def test_successful_market_order(self, mock_client):
        mgr = OrderManager(mock_client)
        result = mgr.place_order(
            symbol="BTCUSDT", side="BUY", order_type="MARKET", quantity="0.01"
        )
        assert result.success is True
        assert result.order_id == 123456
        assert result.status == "FILLED"

    def test_validation_failure_returns_error(self, mock_client):
        mgr = OrderManager(mock_client)
        result = mgr.place_order(
            symbol="BTCUSDT", side="INVALID", order_type="MARKET", quantity="0.01"
        )
        assert result.success is False
        assert "Invalid side" in result.error_message
        mock_client.place_order.assert_not_called()

    def test_api_error_returns_error_result(self, mock_client):
        mock_client.place_order.side_effect = BinanceAPIError(400, -2019, "Margin is insufficient.")
        mgr = OrderManager(mock_client)
        result = mgr.place_order(
            symbol="BTCUSDT", side="BUY", order_type="MARKET", quantity="0.01"
        )
        assert result.success is False
        assert "Margin is insufficient" in result.error_message

    def test_limit_order_missing_price_fails(self, mock_client):
        mgr = OrderManager(mock_client)
        result = mgr.place_order(
            symbol="BTCUSDT", side="BUY", order_type="LIMIT", quantity="0.01"
        )
        assert result.success is False
        assert "required" in result.error_message.lower()


class TestOrderResult:
    def test_pretty_print_success(self):
        result = OrderResult.from_api_response(MOCK_FILLED_RESPONSE)
        output = result.pretty_print()
        assert "✅" in output
        assert "123456" in output
        assert "FILLED" in output

    def test_pretty_print_failure(self):
        result = OrderResult.from_error("Something went wrong")
        output = result.pretty_print()
        assert "❌" in output
        assert "Something went wrong" in output
