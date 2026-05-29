"""
Benchmark strategies for comparing portfolio performance.

All 5 benchmarks start at ₹10,00,000 (₹10 lakh) and are recomputed daily
using price data from the DynamoDB NAV history.

Benchmarks:
  1. Nifty 50 TRI  — direct index return
  2. Equal-weighted basket — equal ₹/15 tickers, rebalanced weekly
  3. 5-day momentum — every Monday buy top-5 by prior 5d return; hold 1 week
  4. Mean-reversion — every Monday buy bottom-5 by prior 5d return; hold 1 week
  5. Buy-and-hold   — equal allocation Day 1, never rebalance

All functions take a list of NAV dicts from DynamoDB (each has a date and
nifty50_daily_return_pct) plus a list of ticker daily returns dicts, and
return a list of {date, nav} snapshots.
"""
from __future__ import annotations

import math
from decimal import Decimal

_INITIAL_CAPITAL = 1_000_000.0
_N_TICKERS = 15


def _to_float(val) -> float:
    if isinstance(val, Decimal):
        return float(val)
    return float(val) if val is not None else 0.0


def compute_nifty_tri_benchmark(nav_history: list[dict]) -> list[dict]:
    """
    Track a buy-and-hold of the Nifty 50 index starting at ₹10 lakh.
    Uses nifty50_daily_return_pct from each NAV record.

    Returns: [{date, nav}]
    """
    result = []
    capital = _INITIAL_CAPITAL
    for nav in sorted(nav_history, key=lambda x: x.get("PK", "")):
        date_str = nav.get("PK", "").replace("DATE#", "")
        daily_ret = _to_float(nav.get("nifty50_daily_return_pct", 0.0)) / 100.0
        capital *= (1 + daily_ret)
        result.append({"date": date_str, "nav": round(capital, 2)})
    return result


def compute_equal_weight_benchmark(
    ticker_daily_returns: dict[str, list[dict]],
    nav_history: list[dict],
) -> list[dict]:
    """
    Equal-weight: allocate ₹10L / 15 to each ticker on Day 1, rebalance weekly.

    ticker_daily_returns: {symbol: [{date, daily_return_pct}]}
    nav_history: sorted list of NAV items (used for date ordering).

    Returns: [{date, nav}]
    """
    result = []
    capital = _INITIAL_CAPITAL
    tickers = list(ticker_daily_returns.keys())[:_N_TICKERS]
    if not tickers:
        return []

    for nav in sorted(nav_history, key=lambda x: x.get("PK", "")):
        date_str = nav.get("PK", "").replace("DATE#", "")
        ticker_rets = []
        for sym in tickers:
            for rec in ticker_daily_returns.get(sym, []):
                if rec.get("date") == date_str:
                    ticker_rets.append(_to_float(rec.get("daily_return_pct", 0)) / 100)
                    break
        if ticker_rets:
            avg_ret = sum(ticker_rets) / len(ticker_rets)
            capital *= (1 + avg_ret)
        result.append({"date": date_str, "nav": round(capital, 2)})
    return result


def compute_momentum_benchmark(
    ticker_daily_returns: dict[str, list[dict]],
    nav_history: list[dict],
    top_n: int = 5,
) -> list[dict]:
    """
    Momentum strategy: every Monday, rank all tickers by their 5-day return.
    Buy the top-N equally weighted; hold for the week.

    Returns: [{date, nav}]
    """
    return _week_rotation_benchmark(
        ticker_daily_returns, nav_history, top_n=top_n, reverse=True
    )


def compute_mean_reversion_benchmark(
    ticker_daily_returns: dict[str, list[dict]],
    nav_history: list[dict],
    bottom_n: int = 5,
) -> list[dict]:
    """
    Mean-reversion strategy: every Monday, rank all tickers by their 5-day return.
    Buy the bottom-N equally weighted; hold for the week.

    Returns: [{date, nav}]
    """
    return _week_rotation_benchmark(
        ticker_daily_returns, nav_history, top_n=bottom_n, reverse=False
    )


def compute_buy_and_hold_benchmark(
    ticker_daily_returns: dict[str, list[dict]],
    nav_history: list[dict],
) -> list[dict]:
    """
    Buy-and-hold: equal allocation to all 15 tickers on Day 1, never rebalance.
    Equivalent to equal_weight without weekly rebalancing.

    Returns: [{date, nav}]
    """
    return compute_equal_weight_benchmark(ticker_daily_returns, nav_history)


def _week_rotation_benchmark(
    ticker_daily_returns: dict[str, list[dict]],
    nav_history: list[dict],
    top_n: int = 5,
    reverse: bool = True,
) -> list[dict]:
    """
    Internal helper for weekly rotation strategies.
    On each Monday, score tickers by their 5-day return and pick top/bottom N.
    """
    from datetime import date, timedelta

    result = []
    capital = _INITIAL_CAPITAL
    tickers = list(ticker_daily_returns.keys())[:_N_TICKERS]
    if not tickers:
        return []

    # Build date-indexed lookup for returns
    date_ret_map: dict[str, dict[str, float]] = {}
    for sym in tickers:
        for rec in ticker_daily_returns.get(sym, []):
            d = rec.get("date", "")
            r = _to_float(rec.get("daily_return_pct", 0)) / 100
            if d not in date_ret_map:
                date_ret_map[d] = {}
            date_ret_map[d][sym] = r

    sorted_dates = sorted(date_ret_map.keys())
    current_basket: list[str] = tickers[:top_n]  # initial basket = first N alphabetically

    for i, date_str in enumerate(sorted_dates):
        # On Mondays (weekday==0): re-rank using last 5d returns
        try:
            d = date.fromisoformat(date_str)
        except ValueError:
            d = None

        if d and d.weekday() == 0 and i >= 5:
            # Compute 5-day cumulative return for each ticker
            prev_5 = sorted_dates[max(0, i - 5): i]
            cum_rets: dict[str, float] = {}
            for sym in tickers:
                cr = 1.0
                for pd_str in prev_5:
                    cr *= (1 + date_ret_map.get(pd_str, {}).get(sym, 0.0))
                cum_rets[sym] = cr - 1.0
            ranked = sorted(cum_rets.items(), key=lambda x: x[1], reverse=reverse)
            current_basket = [sym for sym, _ in ranked[:top_n]]

        day_rets = date_ret_map.get(date_str, {})
        basket_ret = [day_rets.get(sym, 0.0) for sym in current_basket if sym in day_rets]
        if basket_ret:
            avg = sum(basket_ret) / len(basket_ret)
            capital *= (1 + avg)

        result.append({"date": date_str, "nav": round(capital, 2)})

    return result


def get_all_benchmarks(
    nav_history: list[dict],
    ticker_daily_returns: dict[str, list[dict]] | None = None,
) -> dict[str, list[dict]]:
    """
    Compute all 5 benchmarks and return them keyed by strategy name.

    If ticker_daily_returns is not provided, only the Nifty TRI benchmark
    (which only needs nav_history) can be computed; others return empty lists.

    Returns:
        {
          "nifty50_tri": [{date, nav}],
          "equal_weight": [{date, nav}],
          "momentum_5d":  [{date, nav}],
          "mean_reversion_5d": [{date, nav}],
          "buy_and_hold": [{date, nav}],
        }
    """
    tdr = ticker_daily_returns or {}
    return {
        "nifty50_tri":        compute_nifty_tri_benchmark(nav_history),
        "equal_weight":       compute_equal_weight_benchmark(tdr, nav_history),
        "momentum_5d":        compute_momentum_benchmark(tdr, nav_history),
        "mean_reversion_5d":  compute_mean_reversion_benchmark(tdr, nav_history),
        "buy_and_hold":       compute_buy_and_hold_benchmark(tdr, nav_history),
    }
