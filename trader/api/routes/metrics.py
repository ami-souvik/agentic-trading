"""
GET /api/metrics/* — performance analytics endpoints.

/api/metrics/summary  — key stats: Sharpe, Sortino, drawdown, win rate, etc.
/api/metrics/daily    — time series of NAV vs Nifty (for charts)
/api/metrics/analytics — per-agent hit rates + cost breakdown
"""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Query

from trader.api.schemas import (
    AgentCostBreakdown,
    AgentHitRate,
    BenchmarkComparison,
    BenchmarkPoint,
    DailyNavPoint,
    DailyNavResponse,
    MetricsSummaryResponse,
    PerformanceAnalyticsResponse,
)
from trader.config.settings import get_settings
from trader.metrics.benchmarks import compute_nifty_tri_benchmark
from trader.metrics.performance import (
    calculate_max_drawdown,
    calculate_max_drawdown_current,
    calculate_per_agent_hit_rate,
    calculate_profit_factor,
    calculate_sharpe,
    calculate_sortino,
    calculate_win_rate,
    calculate_avg_win_loss_ratio,
    _to_float,
)
from trader.storage import dynamo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

_MIN_OBS_FOR_RELIABLE_STATS = 30


def _fetch_nav_history(from_date: str | None = None, to_date: str | None = None) -> list[dict]:
    """
    Fetch all NAV items from DynamoDB within the given date range.
    If dates are not provided, returns all available history.
    """
    # DynamoDB single-table: NAV items have PK=DATE#{yyyy-mm-dd}, SK=PORTFOLIO.
    # We scan a date range by querying each known date — since we don't have a GSI
    # and we're in Phase 1 (at most ~30 days of data), we iterate known dates.
    # For production with >60 days, a GSI on SK='PORTFOLIO' would be better.
    from datetime import date as _date, timedelta

    start = _date.fromisoformat(from_date) if from_date else _date(2026, 1, 1)
    end   = _date.fromisoformat(to_date)   if to_date   else _date.today()

    nav_items: list[dict] = []
    current = start
    while current <= end:
        ds = current.isoformat()
        try:
            item = dynamo.get_nav(ds)
            if item:
                nav_items.append(item)
        except Exception:
            pass
        current += timedelta(days=1)

    return sorted(nav_items, key=lambda x: x.get("PK", ""))


def _fetch_all_trades() -> list[dict]:
    """Return all trade records across all dates (expensive — only for analytics)."""
    # Query all dates seen in nav history and collect their trades
    nav_items = _fetch_nav_history()
    trades: list[dict] = []
    for nav in nav_items:
        ds = nav.get("PK", "").replace("DATE#", "")
        try:
            day_trades = dynamo.get_trades_for_date(ds)
            trades.extend(day_trades)
        except Exception:
            pass
    return trades


def _compute_trade_pnls(trades: list[dict]) -> list[float]:
    """
    Convert a list of TRADE items into realised P&L values (INR).
    Only SELL/EXIT trades have realised P&L — matched against BUY fills
    using FIFO logic is complex; for the dashboard we use a simple
    trade_value * (side multiplier) approach as an approximation.
    """
    # Simplified: sum fill values by ticker, netting BUYs and EXITs
    # {ticker: [fill_value]}
    pnls: list[float] = []
    from collections import defaultdict
    buy_values: dict[str, list[float]] = defaultdict(list)

    for trade in sorted(trades, key=lambda t: t.get("PK", "")):
        sym = trade.get("ticker", "")
        side = trade.get("side", "")
        fill_price = _to_float(trade.get("fill_price", 0))
        qty = int(_to_float(trade.get("qty", 0)))
        cost_inr = _to_float(trade.get("simulated_cost_inr", 0))

        if side == "BUY":
            buy_values[sym].append(fill_price * qty + cost_inr)
        elif side in ("EXIT", "SELL"):
            exit_value = fill_price * qty - cost_inr
            if buy_values[sym]:
                entry_value = buy_values[sym].pop(0)  # FIFO
                pnls.append(exit_value - entry_value)

    return pnls


@router.get("/summary", response_model=MetricsSummaryResponse)
def get_metrics_summary() -> MetricsSummaryResponse:
    """
    Return key performance statistics for the entire trading history.

    Requires at least 2 NAV records. Returns zeros for metrics when
    insufficient data is available.
    """
    settings = get_settings()
    nav_history = _fetch_nav_history()

    if not nav_history:
        return MetricsSummaryResponse(
            nav=settings.initial_capital_inr,
            cumulative_return_pct=0.0,
            daily_return_pct=0.0,
            sharpe=0.0,
            sortino=0.0,
            max_drawdown_pct=0.0,
            current_drawdown_pct=0.0,
            win_rate=0.0,
            profit_factor=0.0,
            avg_win_loss_ratio=0.0,
            total_trades=0,
            total_llm_cost_usd=0.0,
            days_running=0,
            data_warning="No trading data available yet.",
        )

    daily_returns = [
        _to_float(nav.get("daily_return_pct", 0)) / 100
        for nav in nav_history
    ]
    nav_series = [_to_float(nav.get("nav_inr", settings.initial_capital_inr)) for nav in nav_history]
    current_nav = nav_series[-1] if nav_series else settings.initial_capital_inr
    last_nav = nav_history[-1]

    # Trades for P&L metrics
    trades = _fetch_all_trades()
    trade_pnls = _compute_trade_pnls(trades)

    # Nifty benchmark
    nifty_benchmark = compute_nifty_tri_benchmark(nav_history)

    n_obs = len(daily_returns)
    data_warning = (
        f"Only {n_obs} trading-day observations — statistics are not yet reliable. "
        f"Revisit after {_MIN_OBS_FOR_RELIABLE_STATS} days."
    ) if n_obs < _MIN_OBS_FOR_RELIABLE_STATS else None

    return MetricsSummaryResponse(
        nav=current_nav,
        cumulative_return_pct=round(
            (current_nav / settings.initial_capital_inr - 1) * 100, 4
        ),
        daily_return_pct=_to_float(last_nav.get("daily_return_pct", 0)),
        sharpe=calculate_sharpe(daily_returns),
        sortino=calculate_sortino(daily_returns),
        max_drawdown_pct=calculate_max_drawdown(nav_series),
        current_drawdown_pct=calculate_max_drawdown_current(nav_series),
        win_rate=calculate_win_rate(trade_pnls),
        profit_factor=calculate_profit_factor(trade_pnls),
        avg_win_loss_ratio=calculate_avg_win_loss_ratio(trade_pnls),
        total_trades=len(trades),
        total_llm_cost_usd=sum(
            _to_float(nav.get("total_llm_cost_usd_today", 0)) for nav in nav_history
        ),
        days_running=n_obs,
        data_warning=data_warning,
        benchmark_comparison=BenchmarkComparison(
            nifty50_tri=[BenchmarkPoint(**pt) for pt in nifty_benchmark],
        ),
    )


@router.get("/daily", response_model=DailyNavResponse)
def get_daily_nav(
    from_date: str = Query(default=None, description="Start date yyyy-mm-dd"),
    to_date:   str = Query(default=None, description="End date yyyy-mm-dd"),
) -> DailyNavResponse:
    """
    Return the daily NAV time series for the given date range.
    Used by the NAV chart component in the dashboard.
    """
    nav_history = _fetch_nav_history(from_date, to_date)

    points = [
        DailyNavPoint(
            date=nav.get("PK", "").replace("DATE#", ""),
            nav=_to_float(nav.get("nav_inr", 0)),
            daily_return_pct=_to_float(nav.get("daily_return_pct", 0)),
            nifty_return_pct=_to_float(nav.get("nifty50_daily_return_pct", 0)),
            drawdown_pct=_to_float(nav.get("drawdown_pct", 0)),
            llm_cost_usd=_to_float(nav.get("total_llm_cost_usd_today", 0)),
            open_positions=int(_to_float(nav.get("open_positions", 0))),
        )
        for nav in nav_history
    ]

    return DailyNavResponse(
        points=points,
        from_date=from_date,
        to_date=to_date or date.today().isoformat(),
    )


@router.get("/analytics", response_model=PerformanceAnalyticsResponse)
def get_performance_analytics() -> PerformanceAnalyticsResponse:
    """
    Return detailed analytics: per-agent hit rates, LLM cost breakdown,
    and benchmark comparison.

    This is slower than /summary — it queries decisions for all dates.
    Called only from the dedicated Metrics page, not the main dashboard.
    """
    nav_history = _fetch_nav_history()

    daily_returns = [
        _to_float(nav.get("daily_return_pct", 0)) / 100
        for nav in nav_history
    ]
    nav_series = [
        _to_float(nav.get("nav_inr", get_settings().initial_capital_inr))
        for nav in nav_history
    ]

    # Fetch all decisions for hit-rate computation
    all_decisions: list[dict] = []
    for nav in nav_history:
        ds = nav.get("PK", "").replace("DATE#", "")
        try:
            all_decisions.extend(dynamo.get_decisions_for_date(ds))
        except Exception:
            pass

    hit_rates = calculate_per_agent_hit_rate(all_decisions, nav_history)
    agent_hit_rates = [
        AgentHitRate(
            agent=name,
            hit_rate=stats["hit_rate"],
            n_calls=stats["n_calls"],
            avg_confidence=stats["avg_confidence"],
        )
        for name, stats in hit_rates.items()
    ]

    # Build LLM cost breakdown from decision items
    cost_map: dict[tuple[str, str], dict] = {}
    for dec in all_decisions:
        sk = dec.get("SK", "")
        parts = sk.split("#")
        agent_name = parts[3] if len(parts) >= 4 else "Unknown"
        model = dec.get("model", "unknown")
        key = (agent_name, model)
        if key not in cost_map:
            cost_map[key] = {
                "total_cost_usd": 0.0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "call_count": 0,
            }
        cost_map[key]["total_cost_usd"] += _to_float(dec.get("cost_usd", 0))
        cost_map[key]["total_input_tokens"] += int(_to_float(dec.get("input_tokens", 0)))
        cost_map[key]["total_output_tokens"] += int(_to_float(dec.get("output_tokens", 0)))
        cost_map[key]["call_count"] += 1

    agent_costs = [
        AgentCostBreakdown(
            agent=agent,
            model=model,
            total_cost_usd=round(stats["total_cost_usd"], 6),
            total_input_tokens=stats["total_input_tokens"],
            total_output_tokens=stats["total_output_tokens"],
            call_count=stats["call_count"],
        )
        for (agent, model), stats in sorted(cost_map.items())
    ]

    nifty_benchmark = compute_nifty_tri_benchmark(nav_history)

    n_obs = len(daily_returns)
    trades = _fetch_all_trades()
    trade_pnls = _compute_trade_pnls(trades)

    return PerformanceAnalyticsResponse(
        sharpe=calculate_sharpe(daily_returns),
        sortino=calculate_sortino(daily_returns),
        max_drawdown_pct=calculate_max_drawdown(nav_series),
        win_rate=calculate_win_rate(trade_pnls),
        profit_factor=calculate_profit_factor(trade_pnls),
        agent_hit_rates=agent_hit_rates,
        agent_cost_breakdown=agent_costs,
        benchmark_comparison=BenchmarkComparison(
            nifty50_tri=[BenchmarkPoint(**pt) for pt in nifty_benchmark],
        ),
        statistical_warning=(
            f"Only {n_obs} trading-day observations — statistics are not yet reliable. "
            f"Revisit after {_MIN_OBS_FOR_RELIABLE_STATS} days of live paper data."
        ) if n_obs < _MIN_OBS_FOR_RELIABLE_STATS else (
            "Statistics are based on sufficient observations."
        ),
    )
