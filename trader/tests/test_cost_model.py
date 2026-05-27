"""
Tests for ledger/cost_model.py.
All charge rates verified against Zerodha's brokerage calculator (2025-2026).

Expected values for ₹50,000 delivery round-trip (both legs at same value):
  BUY: STT ₹50 + txn ₹1.49 + SEBI ₹0.05 + stamp ₹7.50 + GST ₹0.28 = ~₹59.31
  SELL: STT ₹50 + txn ₹1.49 + SEBI ₹0.05 + DP ₹15.93 + GST ₹0.28 = ~₹67.74
  Round-trip: ~₹127.05 = ~25.4 bps
"""
from decimal import Decimal

import pytest

from trader.ledger.cost_model import (
    TradeType,
    calculate_round_trip_cost,
    calculate_trade_cost,
    slippage_amount,
)


class TestDeliveryCosts:
    def test_delivery_buy_50k_total(self):
        """₹50,000 delivery BUY. Regulatory charges only, no slippage."""
        cost = calculate_trade_cost(50_000, TradeType.DELIVERY, "BUY")
        # STT 50 + txn ~1.49 + SEBI ~0.05 + stamp 7.50 + GST ~0.28 = ~59.31
        assert Decimal("55") <= cost.total <= Decimal("65"), (
            f"Expected ~₹59 for ₹50k delivery BUY, got ₹{cost.total}"
        )

    def test_delivery_buy_no_sell_side_charges(self):
        """DP charge must be ₹0 on BUY. Stamp duty must be > 0."""
        cost = calculate_trade_cost(50_000, TradeType.DELIVERY, "BUY")
        assert cost.dp_charges == Decimal("0"), "DP charges must not apply on BUY"
        assert cost.stamp_duty > Decimal("0"), "Stamp duty must apply on delivery BUY"

    def test_delivery_sell_dp_charge(self):
        """DP charge of ₹15.93 must appear on delivery SELL."""
        cost = calculate_trade_cost(50_000, TradeType.DELIVERY, "SELL")
        assert cost.dp_charges == Decimal("15.93"), (
            f"Expected DP ₹15.93 on SELL, got ₹{cost.dp_charges}"
        )

    def test_delivery_sell_no_stamp_duty(self):
        """Stamp duty applies to BUY only — must be ₹0 on SELL."""
        cost = calculate_trade_cost(50_000, TradeType.DELIVERY, "SELL")
        assert cost.stamp_duty == Decimal("0"), "Stamp duty must be ₹0 on SELL"

    def test_delivery_zero_brokerage(self):
        """Zerodha delivery brokerage is ₹0."""
        buy = calculate_trade_cost(50_000, TradeType.DELIVERY, "BUY")
        sell = calculate_trade_cost(50_000, TradeType.DELIVERY, "SELL")
        assert buy.brokerage == Decimal("0")
        assert sell.brokerage == Decimal("0")

    def test_delivery_stt_both_sides(self):
        """STT 0.1% applies on both BUY and SELL for delivery."""
        buy = calculate_trade_cost(50_000, TradeType.DELIVERY, "BUY")
        sell = calculate_trade_cost(50_000, TradeType.DELIVERY, "SELL")
        assert buy.stt == Decimal("50"), f"Expected STT ₹50, got ₹{buy.stt}"
        assert sell.stt == Decimal("50"), f"Expected STT ₹50, got ₹{sell.stt}"

    def test_delivery_round_trip_50k(self):
        """₹50,000 delivery BUY + SELL. Expected total ~₹127 (25–27 bps)."""
        buy, sell, rt_bps = calculate_round_trip_cost(50_000, TradeType.DELIVERY)
        round_trip_total = buy.total + sell.total
        assert Decimal("120") <= round_trip_total <= Decimal("140"), (
            f"Round-trip cost ₹{round_trip_total} outside expected ₹120–140"
        )
        assert Decimal("24") <= rt_bps <= Decimal("28"), (
            f"Round-trip {rt_bps} bps outside expected 24–28 bps"
        )

    def test_delivery_stamp_duty_rate(self):
        """Stamp duty is 0.015% of trade value on delivery BUY."""
        cost = calculate_trade_cost(100_000, TradeType.DELIVERY, "BUY")
        expected_stamp = Decimal("15.00")  # 0.015% of 100_000
        assert abs(cost.stamp_duty - expected_stamp) < Decimal("0.05"), (
            f"Stamp duty ₹{cost.stamp_duty} ≠ expected ₹{expected_stamp}"
        )


class TestIntradayCosts:
    def test_intraday_stt_sell_only(self):
        """Intraday STT (0.025%) applies on SELL only."""
        buy = calculate_trade_cost(50_000, TradeType.INTRADAY, "BUY")
        sell = calculate_trade_cost(50_000, TradeType.INTRADAY, "SELL")
        assert buy.stt == Decimal("0"), "No STT on intraday BUY"
        expected_stt = Decimal("12.50")  # 0.025% of 50_000
        assert sell.stt == expected_stt, (
            f"Intraday SELL STT ₹{sell.stt} ≠ expected ₹{expected_stt}"
        )

    def test_intraday_no_dp_charges(self):
        """No DP charges for intraday trades (no actual delivery)."""
        buy = calculate_trade_cost(50_000, TradeType.INTRADAY, "BUY")
        sell = calculate_trade_cost(50_000, TradeType.INTRADAY, "SELL")
        assert buy.dp_charges == Decimal("0")
        assert sell.dp_charges == Decimal("0")

    def test_intraday_brokerage_below_cap(self):
        """Trade value where 0.03% < ₹20: brokerage = 0.03% × value."""
        # 0.03% of ₹50,000 = ₹15 < ₹20 cap
        cost = calculate_trade_cost(50_000, TradeType.INTRADAY, "BUY")
        assert cost.brokerage == Decimal("15"), (
            f"Expected brokerage ₹15, got ₹{cost.brokerage}"
        )

    def test_intraday_brokerage_capped_at_20(self):
        """₹5,00,000 intraday: 0.03% = ₹150 → capped at ₹20."""
        cost = calculate_trade_cost(500_000, TradeType.INTRADAY, "BUY")
        assert cost.brokerage == Decimal("20"), (
            f"Brokerage should be capped at ₹20, got ₹{cost.brokerage}"
        )

    def test_intraday_round_trip_50k(self):
        """₹50,000 intraday BUY + SELL. Expected ~₹53 (10–12 bps)."""
        buy, sell, rt_bps = calculate_round_trip_cost(50_000, TradeType.INTRADAY)
        round_trip_total = buy.total + sell.total
        assert Decimal("45") <= round_trip_total <= Decimal("65"), (
            f"Intraday round-trip ₹{round_trip_total} outside expected ₹45–65"
        )
        assert Decimal("9") <= rt_bps <= Decimal("14"), (
            f"Intraday round-trip {rt_bps} bps outside expected 9–14 bps"
        )

    def test_intraday_stamp_duty_buy_only(self):
        """Intraday stamp duty (0.003%) applies on BUY only."""
        buy = calculate_trade_cost(50_000, TradeType.INTRADAY, "BUY")
        sell = calculate_trade_cost(50_000, TradeType.INTRADAY, "SELL")
        expected = Decimal("1.50")  # 0.003% of 50_000
        assert buy.stamp_duty == expected, (
            f"Expected stamp ₹{expected}, got ₹{buy.stamp_duty}"
        )
        assert sell.stamp_duty == Decimal("0"), "No stamp duty on SELL"


class TestGST:
    def test_gst_applies_to_brokerage_txn_sebi_only(self):
        """GST base = brokerage + exchange_txn + sebi_fee (NOT on STT or stamp)."""
        cost = calculate_trade_cost(50_000, TradeType.INTRADAY, "BUY")
        expected_gst_base = cost.brokerage + cost.exchange_txn + cost.sebi_fee
        expected_gst = (expected_gst_base * Decimal("0.18")).quantize(Decimal("0.01"))
        # Allow ₹0.01 rounding tolerance
        assert abs(cost.gst - expected_gst) <= Decimal("0.01"), (
            f"GST ₹{cost.gst} ≠ expected ₹{expected_gst}"
        )

    def test_delivery_gst_zero_brokerage_base(self):
        """Delivery brokerage is ₹0, so GST is only on txn + SEBI (tiny amount)."""
        cost = calculate_trade_cost(50_000, TradeType.DELIVERY, "BUY")
        # GST base = 0 + ~1.49 + ~0.05 = ~1.54 → GST ~0.28
        assert Decimal("0.20") <= cost.gst <= Decimal("0.40"), (
            f"Delivery BUY GST ₹{cost.gst} outside expected range"
        )


class TestEdgeCases:
    def test_invalid_side_raises(self):
        with pytest.raises(ValueError, match="side must be"):
            calculate_trade_cost(50_000, TradeType.DELIVERY, "HOLD")

    def test_zero_trade_value_raises(self):
        with pytest.raises(ValueError, match="positive"):
            calculate_trade_cost(0, TradeType.DELIVERY, "BUY")

    def test_negative_trade_value_raises(self):
        with pytest.raises(ValueError, match="positive"):
            calculate_trade_cost(-1000, TradeType.DELIVERY, "BUY")

    def test_large_trade_value(self):
        """₹1 crore delivery round-trip. DP charge (₹15.93) becomes negligible → ~22 bps."""
        _, _, rt_bps = calculate_round_trip_cost(10_000_000, TradeType.DELIVERY)
        # STT dominates (0.2% RT = 20 bps) + exchange fees ~2 bps → ~22 bps
        assert Decimal("20") <= rt_bps <= Decimal("26")


class TestSlippage:
    def test_slippage_3bps(self):
        """3 bps slippage on ₹50,000 = ₹15."""
        slip = slippage_amount(50_000, bps=3)
        assert slip == Decimal("15.00")

    def test_slippage_default_is_3bps(self):
        assert slippage_amount(100_000) == Decimal("30.00")


class TestBenchmarks:
    """Verify our model matches published Zerodha round-trip benchmarks."""

    def test_delivery_rt_bps_in_published_range(self):
        """Zerodha docs: delivery round-trip ~25.5–28 bps (at typical trade sizes)."""
        _, _, rt_bps = calculate_round_trip_cost(200_000, TradeType.DELIVERY)
        assert Decimal("23") <= rt_bps <= Decimal("29"), (
            f"Delivery RT {rt_bps} bps outside Zerodha published range 23–29"
        )

    def test_intraday_rt_bps_in_published_range(self):
        """Zerodha docs: intraday round-trip ~10.6 bps applies when brokerage < ₹20 cap.
        The cap kicks in above ~₹66,667. Use ₹50,000 to stay in the uncapped regime."""
        _, _, rt_bps = calculate_round_trip_cost(50_000, TradeType.INTRADAY)
        assert Decimal("9") <= rt_bps <= Decimal("14"), (
            f"Intraday RT {rt_bps} bps outside Zerodha published range 9–14"
        )
