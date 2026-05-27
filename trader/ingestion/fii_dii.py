"""
FII/DII daily flow data for the Indian equity market.

Primary source: nselib capital_market module.
Falls back to a zero-value placeholder on failure so the pipeline can continue —
the Portfolio Manager agent will note the data_staleness context accordingly.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone

logger = logging.getLogger(__name__)

_CACHE_TTL = 23 * 3600  # 23 hours — same day re-use

_EMPTY_FLOWS = {
    "fii_net_buy_cr": 0.0,
    "dii_net_buy_cr": 0.0,
    "date": "",
    "source": "unavailable",
}


def _redis():
    try:
        import redis as redis_lib
        from trader.config.settings import get_settings
        client = redis_lib.from_url(get_settings().redis_url, decode_responses=True)
        client.ping()
        return client
    except Exception:
        return None


def _cache_get(key: str) -> dict | None:
    r = _redis()
    if r is None:
        return None
    try:
        raw = r.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None


def _cache_set(key: str, value: dict) -> None:
    r = _redis()
    if r is None:
        return
    try:
        r.setex(key, _CACHE_TTL, json.dumps(value, default=str))
    except Exception:
        pass


def _try_nselib(trade_date: date) -> dict | None:
    """
    Attempt to fetch FII/DII data via nselib.
    Returns None on any failure so the caller can fall back.
    """
    try:
        from nselib import capital_market  # type: ignore

        date_str = trade_date.strftime("%d-%m-%Y")
        df = capital_market.fii_dii_trading_activity(from_date=date_str, to_date=date_str)

        if df is None or df.empty:
            return None

        # nselib column names vary; normalise common variants
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

        fii_net = dii_net = 0.0
        for col in df.columns:
            if "fii" in col and "net" in col:
                fii_net = float(df[col].iloc[-1])
            if "dii" in col and "net" in col:
                dii_net = float(df[col].iloc[-1])

        return {
            "fii_net_buy_cr": round(fii_net / 1e7, 2),  # nselib returns values in ₹; convert to crore
            "dii_net_buy_cr": round(dii_net / 1e7, 2),
            "date": trade_date.isoformat(),
            "source": "nselib",
        }
    except Exception as e:
        logger.warning("nselib FII/DII fetch failed for %s: %s", trade_date, e)
        return None


def _try_nse_direct(trade_date: date) -> dict | None:
    """
    Attempt to fetch FII/DII data from NSE's public JSON endpoint.
    """
    import httpx
    try:
        url = "https://www.nseindia.com/api/fiidiiTradeReact"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Referer": "https://www.nseindia.com/",
        }
        with httpx.Client(follow_redirects=True, timeout=20.0, headers=headers) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()

        if not data:
            return None

        # API returns a list; find the row matching trade_date
        date_str_formats = [
            trade_date.strftime("%d-%b-%Y").upper(),
            trade_date.strftime("%d-%m-%Y"),
        ]

        for row in data:
            row_date = str(row.get("date", row.get("Date", ""))).strip()
            if row_date in date_str_formats:
                fii_net = float(row.get("netFII", row.get("FII_NET", 0)) or 0)
                dii_net = float(row.get("netDII", row.get("DII_NET", 0)) or 0)
                return {
                    "fii_net_buy_cr": round(fii_net, 2),
                    "dii_net_buy_cr": round(dii_net, 2),
                    "date": trade_date.isoformat(),
                    "source": "nse_api",
                }

        # If exact date not found, use latest row as approximation
        if data:
            row = data[0]
            fii_net = float(row.get("netFII", row.get("FII_NET", 0)) or 0)
            dii_net = float(row.get("netDII", row.get("DII_NET", 0)) or 0)
            return {
                "fii_net_buy_cr": round(fii_net, 2),
                "dii_net_buy_cr": round(dii_net, 2),
                "date": trade_date.isoformat(),
                "source": "nse_api_latest",
            }
    except Exception as e:
        logger.warning("NSE direct FII/DII fetch failed for %s: %s", trade_date, e)

    return None


def fetch_fii_dii_flows(trade_date: date) -> dict:
    """
    Return FII/DII net buy/sell data for the given trading date.

    Result keys:
      fii_net_buy_cr (float): FII net buy in ₹ crore (negative = net sell)
      dii_net_buy_cr (float): DII net buy in ₹ crore
      date (str): ISO date string
      source (str): data source identifier

    Falls back to zeros if all sources fail — the caller should lower confidence.
    """
    cache_key = f"fii_dii:{trade_date.isoformat()}"
    cached = _cache_get(cache_key)
    if cached is not None:
        logger.debug("FII/DII cache hit for %s", trade_date)
        return cached

    result = _try_nselib(trade_date)
    if result is None:
        result = _try_nse_direct(trade_date)
    if result is None:
        logger.warning("All FII/DII sources failed for %s; using zero placeholder", trade_date)
        result = {**_EMPTY_FLOWS, "date": trade_date.isoformat()}

    _cache_set(cache_key, result)
    logger.info("FII/DII for %s: FII ₹%.0f cr, DII ₹%.0f cr (source: %s)",
                trade_date, result["fii_net_buy_cr"], result["dii_net_buy_cr"], result["source"])
    return result
