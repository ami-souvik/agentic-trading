"""
Indian equity transaction cost calculator (NSE, 2025-2026).
All charges verified against Zerodha's published brokerage calculator.

Key references:
- STT: Budget 2024 (eff. Oct 2024): delivery 0.1%/0.1%, intraday SELL 0.025%
- NSE txn charge: 0.00297% (both sides)
- SEBI fee: ₹10 per crore = 0.0001%
- Stamp duty: Finance Act 2019 rates
- DP charge: ₹15.93 per scrip per day (CDSL + depository participant fee)
- GST: 18% on brokerage + exchange txn + SEBI fee

Round-trip benchmarks (pure regulatory charges, no slippage):
  Delivery (CNC): ~25–26 bps
  Intraday (MIS): ~10–11 bps
Add 3 bps slippage per leg for realistic large-cap NSE fill modeling.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum


class TradeType(Enum):
    DELIVERY = "CNC"
    INTRADAY = "MIS"


# ─── Charge rates (as Decimal for precision) ────────────────────────────────

# STT rates
_STT_DELIVERY = Decimal("0.001")      # 0.1% on both buy and sell
_STT_INTRADAY_SELL = Decimal("0.00025")  # 0.025% on sell only

# NSE exchange transaction charge
_NSE_TXN = Decimal("0.0000297")       # 0.00297% on turnover

# SEBI fee
_SEBI_FEE = Decimal("0.000001")       # ₹10/crore = 0.0001% = 0.000001

# Stamp duty
_STAMP_DELIVERY_BUY = Decimal("0.00015")   # 0.015% on buy
_STAMP_INTRADAY_BUY = Decimal("0.00003")   # 0.003% on buy

# GST on (brokerage + exchange txn + SEBI)
_GST = Decimal("0.18")

# Zerodha intraday brokerage
_ZERODHA_INTRADAY_RATE = Decimal("0.0003")  # 0.03% per order
_ZERODHA_INTRADAY_MAX = Decimal("20")        # capped at ₹20

# DP charge: fixed per scrip per day on SELL (delivery only)
_DP_CHARGE = Decimal("15.93")

# Slippage allowance for large-cap NSE stocks (per leg)
SLIPPAGE_BPS = Decimal("3")


@dataclass(frozen=True)
class CostBreakdown:
    brokerage: Decimal
    stt: Decimal
    exchange_txn: Decimal
    gst: Decimal
    sebi_fee: Decimal
    stamp_duty: Decimal
    dp_charges: Decimal
    total: Decimal        # sum of all regulatory charges (no slippage)
    total_bps: Decimal   # total / trade_value × 10000


def _d(value: float | int | str) -> Decimal:
    return Decimal(str(value))


def calculate_trade_cost(
    trade_value_inr: float,
    trade_type: TradeType,
    side: str,
    broker: str = "zerodha",
) -> CostBreakdown:
    """
    Compute the full cost breakdown for a single equity leg on NSE (2025-2026).

    Args:
        trade_value_inr: Gross trade value in INR (price × quantity).
        trade_type:      TradeType.DELIVERY (CNC) or TradeType.INTRADAY (MIS).
        side:            "BUY" or "SELL".
        broker:          Currently only "zerodha" is modelled.

    Returns:
        CostBreakdown with all components in INR and total_bps (10 000ths of trade value).

    Note:
        Does NOT include slippage. Add SLIPPAGE_BPS (3 bps) per leg for realistic fills.
        See ledger/paper_trade.py for combined cost + slippage simulation.
    """
    if side not in ("BUY", "SELL"):
        raise ValueError(f"side must be 'BUY' or 'SELL', got: {side!r}")
    if trade_value_inr <= 0:
        raise ValueError("trade_value_inr must be positive")

    tv = _d(trade_value_inr)
    is_buy = side == "BUY"

    if trade_type == TradeType.DELIVERY:
        brokerage = Decimal("0")  # Zerodha delivery is free
        stt = tv * _STT_DELIVERY  # 0.1% on both buy and sell
        stamp_duty = (tv * _STAMP_DELIVERY_BUY) if is_buy else Decimal("0")
        dp_charges = Decimal("0") if is_buy else _DP_CHARGE

    elif trade_type == TradeType.INTRADAY:
        raw_brokerage = tv * _ZERODHA_INTRADAY_RATE
        brokerage = min(raw_brokerage, _ZERODHA_INTRADAY_MAX)
        stt = (tv * _STT_INTRADAY_SELL) if not is_buy else Decimal("0")
        stamp_duty = (tv * _STAMP_INTRADAY_BUY) if is_buy else Decimal("0")
        dp_charges = Decimal("0")  # no DP charge for intraday
    else:
        raise ValueError(f"Unknown trade_type: {trade_type}")

    exchange_txn = tv * _NSE_TXN
    sebi_fee = tv * _SEBI_FEE
    gst = (brokerage + exchange_txn + sebi_fee) * _GST

    total = brokerage + stt + exchange_txn + gst + sebi_fee + stamp_duty + dp_charges
    total_bps = (total / tv * Decimal("10000")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    return CostBreakdown(
        brokerage=brokerage.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        stt=stt.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        exchange_txn=exchange_txn.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
        gst=gst.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        sebi_fee=sebi_fee.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
        stamp_duty=stamp_duty.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        dp_charges=dp_charges.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        total=total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        total_bps=total_bps,
    )


def calculate_round_trip_cost(
    trade_value_inr: float,
    trade_type: TradeType,
    broker: str = "zerodha",
) -> tuple[CostBreakdown, CostBreakdown, Decimal]:
    """
    Convenience helper: returns (buy_cost, sell_cost, round_trip_bps).
    Assumes same trade_value for both legs (ignores P&L on the position).
    """
    buy_cost = calculate_trade_cost(trade_value_inr, trade_type, "BUY", broker)
    sell_cost = calculate_trade_cost(trade_value_inr, trade_type, "SELL", broker)
    total = buy_cost.total + sell_cost.total
    tv = _d(trade_value_inr)
    round_trip_bps = (total / tv * Decimal("10000")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return buy_cost, sell_cost, round_trip_bps


def slippage_amount(trade_value_inr: float, bps: int = 3) -> Decimal:
    """Return the INR slippage cost at the given bps rate."""
    return (_d(trade_value_inr) * _d(bps) / Decimal("10000")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
