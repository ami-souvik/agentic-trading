"""
LangGraph TypedDict state definitions for the NSE trader pipeline.

TickerState: per-ticker state that flows through the agent graph.
DailyRunState: top-level state managed by runner.py across all 15 tickers.
"""
from __future__ import annotations

from typing import TypedDict


class TickerState(TypedDict):
    # Identity
    ticker: str
    company_name: str
    sector: str

    # Ingestion data (populated before the graph runs)
    market_data: dict          # OHLCV rows + computed technical indicators
    news_articles: list[dict]  # up to 8 articles from RSS feeds
    corporate_actions: list[dict]
    fii_dii: dict              # {fii_net_buy_cr, dii_net_buy_cr, date, source}

    # Portfolio snapshot BEFORE processing this ticker
    portfolio_snapshot: dict   # {cash_inr, open_positions, nav_inr, drawdown_pct}

    # Current position for THIS ticker (empty dict if no open position)
    current_position: dict     # {qty, avg_price, entry_date, days_held, stop_loss, target}

    # ASM/GSM/T2T flag — set by runner before graph starts
    is_restricted: bool

    # Agent outputs (None until the node runs)
    news_output: dict | None
    technical_output: dict | None
    fundamentals_output: dict | None
    bull_bear_output: dict | None
    pm_output: dict | None

    # Ledger result (populated by ledger_execute node)
    simulated_fill: dict | None  # SimulatedFill as dict, or None if no fill

    # Pipeline control
    skip_reason: str | None    # "QUIET" | "RESTRICTED" | "DRAWDOWN" | None

    # Observability
    tokens_used: dict          # {agent_name: {input, output, cached, cost_usd}}
    errors: list[str]
    processing_time_ms: int


class DailyRunState(TypedDict):
    run_date: str                           # "yyyy-mm-dd"
    tickers: list[str]                      # The 15 symbols to process
    ticker_states: dict[str, TickerState]   # Results keyed by symbol
    portfolio: dict                         # Running portfolio (cash, positions, nav)
    total_cost_usd: float                   # Cumulative LLM spend for today's run
    completed_at: str | None               # ISO timestamp when run finished


def empty_ticker_state(ticker: str, company_name: str, sector: str) -> TickerState:
    """Return a zeroed TickerState ready to be populated by the ingestion step."""
    return TickerState(
        ticker=ticker,
        company_name=company_name,
        sector=sector,
        market_data={},
        news_articles=[],
        corporate_actions=[],
        fii_dii={},
        portfolio_snapshot={},
        current_position={},
        is_restricted=False,
        news_output=None,
        technical_output=None,
        fundamentals_output=None,
        bull_bear_output=None,
        pm_output=None,
        simulated_fill=None,
        skip_reason=None,
        tokens_used={},
        errors=[],
        processing_time_ms=0,
    )
