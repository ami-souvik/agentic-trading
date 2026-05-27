"""
NSE corporate actions: results calendar, board meetings, dividends, bonus/splits.

Fetches from NSE's public API. Returns structured announcements per ticker
for the next/recent 7 days to surface results-season risk in agents.
"""
from __future__ import annotations

import json
import logging
from datetime import date, timedelta

import httpx

logger = logging.getLogger(__name__)

_CACHE_TTL = 6 * 3600  # 6 hours — corporate calendars update infrequently

_NSE_CORP_ACTIONS_URL = "https://www.nseindia.com/api/corporates-corporateActions"


def _redis():
    try:
        import redis as redis_lib
        from trader.config.settings import get_settings
        client = redis_lib.from_url(get_settings().redis_url, decode_responses=True)
        client.ping()
        return client
    except Exception:
        return None


def _cache_get(key: str) -> list | None:
    r = _redis()
    if r is None:
        return None
    try:
        raw = r.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None


def _cache_set(key: str, value: list) -> None:
    r = _redis()
    if r is None:
        return
    try:
        r.setex(key, _CACHE_TTL, json.dumps(value, default=str))
    except Exception:
        pass


def fetch_corporate_actions(ticker: str, days_window: int = 7) -> list[dict]:
    """
    Return upcoming or recent corporate actions for `ticker` within ±days_window days.

    Each action dict: {type, headline, date, ex_date}
    Returns empty list on failure — agents treat this as no known catalyst.
    """
    cache_key = f"corp_actions:{ticker}:{days_window}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    today = date.today()
    from_date = (today - timedelta(days=days_window)).strftime("%d-%m-%Y")
    to_date   = (today + timedelta(days=days_window)).strftime("%d-%m-%Y")

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Referer": "https://www.nseindia.com/",
    }

    try:
        with httpx.Client(follow_redirects=True, timeout=20.0, headers=headers) as client:
            resp = client.get(
                _NSE_CORP_ACTIONS_URL,
                params={"index": "equities", "from_date": from_date, "to_date": to_date},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.warning("Corporate actions fetch failed for %s: %s", ticker, e)
        return []

    actions = []
    for row in data:
        symbol = str(row.get("symbol", "")).strip().upper()
        if symbol != ticker.upper():
            continue
        actions.append({
            "type":     str(row.get("subject", row.get("type", "UNKNOWN"))).strip(),
            "headline": str(row.get("subject", row.get("purpose", ""))).strip(),
            "date":     str(row.get("exDate", row.get("record_date", ""))).strip(),
            "ex_date":  str(row.get("exDate", "")).strip(),
        })

    _cache_set(cache_key, actions)
    if actions:
        logger.info("Found %d corporate actions for %s", len(actions), ticker)
    return actions
