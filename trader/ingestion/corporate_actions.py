"""
NSE corporate actions: results calendar, board meetings, dividends, bonus/splits.

Fetches from NSE's public API. Returns structured announcements per ticker
for the next/recent 7 days to surface results-season risk in agents.
"""
from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from .cache import Cache

import httpx

logger = logging.getLogger(__name__)

_CACHE_TTL = 6 * 3600  # 6 hours — corporate calendars update infrequently
C = Cache(_CACHE_TTL)

_NSE_CORP_ACTIONS_URL = "https://www.nseindia.com/api/corporates-corporateActions"


def fetch_corporate_actions(ticker: str, days_window: int = 7) -> list[dict]:
    """
    Return upcoming or recent corporate actions for `ticker` within ±days_window days.

    Each action dict: {type, headline, date, ex_date}
    Returns empty list on failure — agents treat this as no known catalyst.
    """
    cache_key = f"corp_actions:{ticker}:{days_window}"
    cached = C._get(cache_key)
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

    C._set(cache_key, actions)
    if actions:
        logger.info("Found %d corporate actions for %s", len(actions), ticker)
    return actions
