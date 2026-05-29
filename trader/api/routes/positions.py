"""
GET /api/positions — open paper-trading positions.

Returns all currently open positions with unrealised P&L computed
against today's last-known close price (from DynamoDB or cache).
"""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, HTTPException

from trader.api.schemas import PositionResponse, PositionsResponse
from trader.config.settings import get_settings
from trader.config.tickers import UNIVERSE
from trader.storage import dynamo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["positions"])

# Ticker → company name lookup for enrichment
_TICKER_META: dict[str, dict] = {
    t.symbol: {"name": t.name, "sector": t.sector}
    for t in UNIVERSE
}


def _to_float(val) -> float:
    if isinstance(val, Decimal):
        return float(val)
    return float(val) if val is not None else 0.0


@router.get("/positions", response_model=PositionsResponse)
def get_positions() -> PositionsResponse:
    """
    Return all open positions as of today's trading date.

    Queries DynamoDB for the most recent POSITION item for each ticker
    in our 15-stock universe. Positions with qty=0 are filtered out.
    Unrealised P&L is computed against avg_price only (current_price
    requires live market data which may not be available after hours).
    """
    today = date.today().isoformat()
    settings = get_settings()

    positions: list[PositionResponse] = []
    cash_inr: float = 0.0
    equity_value: float = 0.0

    # Pull today's NAV for cash balance
    try:
        nav_item = dynamo.get_nav(today)
        if nav_item:
            cash_inr = _to_float(nav_item.get("cash_inr", settings.initial_capital_inr))
            equity_value = _to_float(nav_item.get("equity_value_inr", 0.0))
    except Exception as exc:
        logger.warning("Could not fetch NAV from DynamoDB: %s", exc)
        cash_inr = _to_float(settings.initial_capital_inr)

    # Pull position for each ticker
    for ticker_obj in UNIVERSE:
        sym = ticker_obj.symbol
        sector = ticker_obj.sector
        try:
            item = dynamo.get_position(sym, today)
        except Exception as exc:
            logger.warning("Could not fetch position for %s: %s", sym, exc)
            continue

        if item is None:
            continue

        qty = int(_to_float(item.get("qty", 0)))
        if qty == 0:
            continue

        avg_price = _to_float(item.get("avg_price", 0.0))

        # We don't have live prices post-market — leave current_price as None
        # The dashboard will show "—" for unrealised P&L until next run
        current_price: float | None = None
        unrealised_pnl_inr: float | None = None
        unrealised_pnl_pct: float | None = None

        if current_price is not None and avg_price > 0:
            unrealised_pnl_inr = (current_price - avg_price) * qty
            unrealised_pnl_pct = (current_price - avg_price) / avg_price * 100

        positions.append(
            PositionResponse(
                ticker=sym,
                qty=qty,
                avg_price=avg_price,
                days_held=int(_to_float(item.get("days_held", 0))),
                current_price=current_price,
                unrealized_pnl_inr=unrealised_pnl_inr,
                unrealized_pnl_pct=unrealised_pnl_pct,
                stop_loss_price=_to_float(item.get("stop_loss_price", 0.0)),
                target_price=_to_float(item.get("target_price", 0.0)),
                kill_conditions=item.get("kill_conditions", []),
                entry_date=item.get("entry_date", today),
                horizon_days=int(_to_float(item.get("horizon_days", 3))),
                sector=sector,
            )
        )

    nav_inr = cash_inr + equity_value

    return PositionsResponse(
        positions=positions,
        open_count=len(positions),
        cash_inr=cash_inr,
        equity_value_inr=equity_value,
        nav_inr=nav_inr,
    )
