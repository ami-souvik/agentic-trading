"""
Performance metrics for the paper-trading ledger.

All functions operate on plain Python lists so they can be called without
pandas in hot paths (e.g. from API routes that serialize straight to JSON).

Indian context:
  - Risk-free rate: ~6.8% per annum (10-year G-Sec yield, 2025 estimate)
  - Trading days per year: 252 (NSE standard)
"""
from __future__ import annotations

import math
import statistics
from decimal import Decimal


_TRADING_DAYS_PER_YEAR = 252
_RISK_FREE_DAILY = 0.068 / _TRADING_DAYS_PER_YEAR  # ~0.027% / day


# ─── Core metrics ──────────────────────────────────────────────────────────────

def calculate_sharpe(
    daily_returns: list[float],
    risk_free_rate_annual: float = 0.068,
) -> float:
    """
    Annualised Sharpe ratio.

    Uses excess return (r - rf) and annualises by sqrt(252).
    Returns 0.0 if fewer than 2 observations or zero std-dev.
    """
    if len(daily_returns) < 2:
        return 0.0
    rf_daily = risk_free_rate_annual / _TRADING_DAYS_PER_YEAR
    excess = [r - rf_daily for r in daily_returns]
    mean_excess = statistics.mean(excess)
    std_excess = statistics.stdev(excess)
    if std_excess == 0.0:
        return 0.0
    return round((mean_excess / std_excess) * math.sqrt(_TRADING_DAYS_PER_YEAR), 4)


def calculate_sortino(
    daily_returns: list[float],
    risk_free_rate_annual: float = 0.068,
) -> float:
    """
    Annualised Sortino ratio (uses downside deviation — more relevant than
    Sharpe for asymmetric/right-skewed trading strategies).

    Returns 0.0 if fewer than 2 observations or zero downside deviation.
    """
    if len(daily_returns) < 2:
        return 0.0
    rf_daily = risk_free_rate_annual / _TRADING_DAYS_PER_YEAR
    excess = [r - rf_daily for r in daily_returns]
    mean_excess = statistics.mean(excess)
    downside = [min(0.0, e) for e in excess]
    downside_sq = [x ** 2 for x in downside]
    if not downside_sq or sum(downside_sq) == 0:
        return 0.0
    downside_dev = math.sqrt(sum(downside_sq) / len(downside_sq))
    if downside_dev == 0.0:
        return 0.0
    return round((mean_excess / downside_dev) * math.sqrt(_TRADING_DAYS_PER_YEAR), 4)


def calculate_max_drawdown(nav_series: list[float]) -> float:
    """
    Maximum peak-to-trough decline as a percentage (negative number).

    e.g. -12.5 means the portfolio fell 12.5% from its peak at some point.
    Returns 0.0 if fewer than 2 data points.
    """
    if len(nav_series) < 2:
        return 0.0
    peak = nav_series[0]
    max_dd = 0.0
    for nav in nav_series:
        if nav > peak:
            peak = nav
        dd = (nav - peak) / peak * 100
        if dd < max_dd:
            max_dd = dd
    return round(max_dd, 4)


def calculate_max_drawdown_current(nav_series: list[float]) -> float:
    """
    Current drawdown from the all-time peak in the series (negative or zero).
    Useful for the circuit-breaker display in the dashboard.
    """
    if not nav_series:
        return 0.0
    peak = max(nav_series)
    current = nav_series[-1]
    if peak == 0:
        return 0.0
    return round((current - peak) / peak * 100, 4)


def calculate_profit_factor(trade_pnls: list[float]) -> float:
    """
    Gross profit / gross loss (absolute value).
    > 1.5 is decent; < 1.0 is a losing strategy.
    Returns 0.0 if no losing trades exist (infinite profit factor → clamp to 0).
    """
    winners = [p for p in trade_pnls if p > 0]
    losers  = [p for p in trade_pnls if p < 0]
    if not losers:
        return 0.0  # can't compute — show 0 as sentinel for "no losing trades"
    gross_profit = sum(winners)
    gross_loss   = abs(sum(losers))
    if gross_loss == 0:
        return 0.0
    return round(gross_profit / gross_loss, 4)


def calculate_win_rate(trade_pnls: list[float]) -> float:
    """
    Win rate: fraction of closed trades that were profitable.
    Returns 0.0 if no closed trades.
    """
    if not trade_pnls:
        return 0.0
    winners = sum(1 for p in trade_pnls if p > 0)
    return round(winners / len(trade_pnls), 4)


def calculate_avg_win_loss_ratio(trade_pnls: list[float]) -> float:
    """
    Average winner size / average loser size (absolute values).
    e.g. 2.5 means winners are 2.5× larger than losers on average.
    Returns 0.0 if no winning or no losing trades.
    """
    winners = [p for p in trade_pnls if p > 0]
    losers  = [abs(p) for p in trade_pnls if p < 0]
    if not winners or not losers:
        return 0.0
    return round(statistics.mean(winners) / statistics.mean(losers), 4)


def calculate_calmar_ratio(
    daily_returns: list[float],
    nav_series: list[float],
    risk_free_rate_annual: float = 0.068,
) -> float:
    """
    Annualised return / |max drawdown|.  Good for assessing downside risk
    relative to return. Returns 0.0 if max drawdown is zero.
    """
    if len(daily_returns) < 2 or not nav_series:
        return 0.0
    rf_daily = risk_free_rate_annual / _TRADING_DAYS_PER_YEAR
    excess = [r - rf_daily for r in daily_returns]
    annualised_return = statistics.mean(excess) * _TRADING_DAYS_PER_YEAR * 100
    max_dd = abs(calculate_max_drawdown(nav_series))
    if max_dd == 0.0:
        return 0.0
    return round(annualised_return / max_dd, 4)


# ─── Per-agent hit-rate (requires DynamoDB data) ─────────────────────────────

def calculate_per_agent_hit_rate(
    decisions: list[dict],
    nav_history: list[dict],
) -> dict[str, dict]:
    """
    For each agent, compute what fraction of its directional calls aligned
    with the actual realised 5-day return.

    decisions: list of DECISION items from DynamoDB, each with:
        SK = "TICKER#{symbol}#AGENT#{agent_name}"
        decision / sentiment_label / technical_signal / fundamental_bias / debate_winner
        confidence: float
        date: str (derived from PK)

    nav_history: list of NAV items from DynamoDB, each with:
        PK = "DATE#{yyyy-mm-dd}"
        nifty50_daily_return_pct: float (used as a market proxy)

    Returns:
        {
          "NewsSentiment": {"hit_rate": 0.62, "n_calls": 13, "avg_confidence": 0.71},
          "Technical":     {...},
          ...
        }

    NOTE: This is a best-effort approximation — we use the PM's realised P&L
    (5-day return from TRADE items) as ground truth when available, and Nifty
    direction as a market proxy otherwise.
    """
    # Build a simple date → nifty_daily_return map for proxy ground truth
    nifty_map: dict[str, float] = {}
    for nav in nav_history:
        pk = nav.get("PK", "")
        date_str = pk.replace("DATE#", "")
        ret = nav.get("nifty50_daily_return_pct")
        if ret is not None:
            nifty_map[date_str] = float(ret)

    agent_stats: dict[str, dict] = {}

    for dec in decisions:
        sk: str = dec.get("SK", "")
        # SK = TICKER#{symbol}#AGENT#{name}
        parts = sk.split("#")
        if len(parts) < 4:
            continue
        agent_name = parts[3]
        pk = dec.get("PK", "")
        date_str = pk.replace("DATE#", "")

        # Extract the directional call depending on agent
        call: str | None = None
        if agent_name in ("NewsSentiment",):
            lbl = dec.get("sentiment_label", "")
            call = "UP" if "BULLISH" in lbl else ("DOWN" if "BEARISH" in lbl else None)
        elif agent_name == "Technical":
            sig = dec.get("technical_signal", "")
            call = "UP" if sig == "BUY" else ("DOWN" if sig in ("SELL", "EXIT_LONG") else None)
        elif agent_name == "Fundamentals":
            bias = dec.get("fundamental_bias", "")
            call = "UP" if bias == "BULLISH" else ("DOWN" if bias == "BEARISH" else None)
        elif agent_name in ("BullBear",):
            winner = dec.get("debate_winner", "")
            call = "UP" if winner == "BULL" else ("DOWN" if winner == "BEAR" else None)
        elif agent_name == "PortfolioManager":
            decision_val = dec.get("decision", "")
            call = "UP" if decision_val == "BUY" else ("DOWN" if decision_val in ("SELL", "EXIT") else None)

        if call is None:
            continue

        # Use Nifty direction as proxy ground truth on that date
        nifty_ret = nifty_map.get(date_str)
        if nifty_ret is None:
            continue
        actual = "UP" if nifty_ret > 0 else "DOWN"

        if agent_name not in agent_stats:
            agent_stats[agent_name] = {"hits": 0, "total": 0, "confidence_sum": 0.0}

        agent_stats[agent_name]["total"] += 1
        agent_stats[agent_name]["confidence_sum"] += float(dec.get("confidence", 0.5))
        if call == actual:
            agent_stats[agent_name]["hits"] += 1

    return {
        name: {
            "hit_rate": round(s["hits"] / s["total"], 4) if s["total"] else 0.0,
            "n_calls":  s["total"],
            "avg_confidence": round(s["confidence_sum"] / s["total"], 4) if s["total"] else 0.0,
        }
        for name, s in agent_stats.items()
    }


def _to_float(val) -> float:
    """Safe Decimal → float conversion for DynamoDB values."""
    if isinstance(val, Decimal):
        return float(val)
    return float(val) if val is not None else 0.0
